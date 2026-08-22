"""Scientific processing and quantitative helpers for Raman spectra."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from typing import Any, Literal

import numpy as np
from numpy.typing import ArrayLike

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.processing import (
    ProcessingError,
    crop,
    integrate,
    normalize,
    offset,
    savgol,
    subtract_baseline,
)

RamanNormalization = Literal["max", "max_abs", "minmax", "area"]
RamanAreaMode = Literal["absolute", "net"]
RamanRatioMetric = Literal["height", "area"]
BaselineInput = Series | ArrayLike | float | complex

_RAMAN_SHIFT_NAMES = {"ramanshift", "shift"}
_INTENSITY_NAMES = {"intensity", "normalizedintensity"}
_INVERSE_CM_UNITS = {"cm^-1", "cm-1", "1/cm", "cm**-1", "cm^(-1)"}

_COUNT_UNITS = {"count", "counts", "ct", "cts"}
_COUNT_RATE_UNITS = {
    "cps",
    "count/s",
    "counts/s",
    "ct/s",
    "cts/s",
    "countpersecond",
    "countspersecond",
    "countss^-1",
    "countss-1",
    "counts^-1",
    "counts-1",
}
_ARBITRARY_UNITS = {
    "a.u.",
    "a.u",
    "au",
    "arb.u.",
    "arb.u",
    "arb.unit",
    "arb.units",
    "arbitraryunit",
    "arbitraryunits",
}
_DIMENSIONLESS_UNITS = {"1", "dimensionless"}


class RamanError(ValueError):
    """Raised when Raman data or a requested Raman operation is invalid."""


def _finite_float(value: Any, *, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a real numeric value") from exc
    if not isfinite(result):
        raise RamanError(f"{name} must be finite")
    return result


def _semantic_token(value: str) -> str:
    token = str(value).strip().casefold()
    return "".join(character for character in token if character.isalnum())


def _compact_unit(unit: str) -> str:
    return (
        "".join(str(unit).strip().casefold().split())
        .replace("−", "-")
        .replace("⁻", "-")
        .replace("¹", "1")
    )


def _raman_shift_unit(unit: str | None) -> str:
    if unit is None or not str(unit).strip():
        raise RamanError("Raman shift requires an explicit inverse-centimetre unit")
    compact = _compact_unit(str(unit))
    if compact not in _INVERSE_CM_UNITS:
        raise RamanError(
            f"unsupported Raman-shift unit {unit!r}; use cm^-1, cm-1, 1/cm, or cm⁻¹"
        )
    return compact


def _intensity_unit_signature(series: Series) -> tuple[str, str | None]:
    unit = series.y_axis.unit
    if unit is None or not str(unit).strip():
        kind = "dimensionless"
        canonical: str | None = None
    else:
        compact = _compact_unit(str(unit))
        if compact in _COUNT_UNITS:
            kind, canonical = "counts", "counts"
        elif compact in _COUNT_RATE_UNITS:
            kind, canonical = "count_rate", "cps"
        elif compact in _ARBITRARY_UNITS:
            kind, canonical = "arbitrary", "a.u."
        elif compact in _DIMENSIONLESS_UNITS:
            kind, canonical = "dimensionless", None
        else:
            raise RamanError(
                f"unsupported Raman intensity unit {unit!r}; use counts, cps, "
                "arbitrary units, or dimensionless intensity"
            )

    semantic_name = _semantic_token(series.y_axis.name)
    if semantic_name == "normalizedintensity" and kind not in {
        "arbitrary",
        "dimensionless",
    }:
        raise RamanError(
            "normalized_intensity must use arbitrary or dimensionless units, "
            f"not {unit!r}"
        )
    return kind, canonical


def validate_raman_series(series: Series) -> None:
    """Validate one Raman spectrum without modifying it."""
    if not isinstance(series, Series):
        raise TypeError("series must be a Series")
    if _semantic_token(series.x_axis.name) not in _RAMAN_SHIFT_NAMES:
        raise RamanError(
            "Raman requires x_axis.name to identify Raman shift "
            "(for example 'raman_shift' or 'shift')"
        )
    _raman_shift_unit(series.x_axis.unit)

    if _semantic_token(series.y_axis.name) not in _INTENSITY_NAMES:
        raise RamanError(
            "Raman requires y_axis.name='intensity' or 'normalized_intensity'"
        )
    _intensity_unit_signature(series)

    x = np.asarray(series.x)
    if np.iscomplexobj(x):
        raise RamanError("Raman-shift values must be real")
    x = x.astype(np.float64, copy=False)
    if x.size < 2:
        raise RamanError("Raman spectra require at least two Raman-shift points")
    if np.isnan(x).any() or np.isinf(x).any():
        raise RamanError("Raman-shift values must be finite")
    if not np.all(np.diff(x) > 0):
        raise RamanError(
            "Raman-shift values must be strictly increasing without duplicates"
        )

    y = np.asarray(series.y)
    if np.iscomplexobj(y):
        raise RamanError("Raman intensity values must be real")
    if np.isinf(y).any():
        raise RamanError("Raman intensity values must not contain +/-inf")


def _normalization_signature(
    method: RamanNormalization,
    target: float,
    area_mode: RamanAreaMode,
) -> str:
    signature = f"raman:{method}:target={float(target)!r}"
    if method == "area":
        signature += f":area_mode={area_mode}"
    return signature


def _with_normalized_intensity_axis(
    series: Series,
    *,
    method: RamanNormalization,
    target: float,
    area_mode: RamanAreaMode,
) -> Series:
    metadata = series.y_axis.metadata_dict()
    metadata.update(
        {
            "normalization": _normalization_signature(method, target, area_mode),
            "normalization_method": method,
            "normalization_target": target,
        }
    )
    if method == "area":
        metadata["normalization_area_mode"] = area_mode
    return Series(
        x=series.x,
        y=series.y,
        label=series.label,
        x_axis=series.x_axis,
        y_axis=Axis(
            name="normalized_intensity",
            unit="a.u.",
            label="Normalized intensity",
            metadata=metadata,
        ),
        metadata=series.metadata_dict(),
        key=series.key,
    )


def _canonicalize_raman_series(series: Series) -> Series:
    """Return a temporary copy with equivalent Raman semantics canonicalized."""
    validate_raman_series(series)
    _, canonical_y_unit = _intensity_unit_signature(series)
    y_name = (
        "normalized_intensity"
        if _semantic_token(series.y_axis.name) == "normalizedintensity"
        else "intensity"
    )
    return Series(
        x=series.x,
        y=series.y,
        label=series.label,
        x_axis=Axis(
            name="raman_shift",
            unit="cm^-1",
            label=series.x_axis.label,
            metadata=series.x_axis.metadata_dict(),
        ),
        y_axis=Axis(
            name=y_name,
            unit=canonical_y_unit,
            label=series.y_axis.label,
            metadata=series.y_axis.metadata_dict(),
        ),
        metadata=series.metadata_dict(),
        key=series.key,
    )


def _baseline_for_source(source: Series, baseline: Series) -> Series:
    validate_raman_series(baseline)
    source_name = _semantic_token(source.y_axis.name)
    baseline_name = _semantic_token(baseline.y_axis.name)
    if source_name != baseline_name:
        raise RamanError(
            "baseline Series intensity semantics must match the source "
            f"({source.y_axis.name!r} != {baseline.y_axis.name!r})"
        )
    source_kind, _ = _intensity_unit_signature(source)
    baseline_kind, _ = _intensity_unit_signature(baseline)
    if source_kind != baseline_kind:
        raise RamanError(
            "baseline Series intensity basis must match the source "
            f"({source.y_axis.unit!r} != {baseline.y_axis.unit!r})"
        )
    return Series(
        x=baseline.x,
        y=baseline.y,
        label=baseline.label,
        x_axis=source.x_axis,
        y_axis=source.y_axis,
        metadata=baseline.metadata_dict(),
        key=baseline.key,
    )


@dataclass(frozen=True, slots=True)
class RamanProcessingConfig:
    """Serializable processing recipe for one Raman spectrum."""

    shift_min_cm1: float | None = None
    shift_max_cm1: float | None = None
    savgol_window_length: int | None = None
    savgol_polyorder: int = 3
    savgol_mode: str = "interp"
    normalization: RamanNormalization | None = None
    normalization_target: float = 1.0
    normalization_area_mode: RamanAreaMode = "absolute"
    vertical_offset: float = 0.0

    def __post_init__(self) -> None:
        if self.shift_min_cm1 is not None:
            object.__setattr__(
                self,
                "shift_min_cm1",
                _finite_float(self.shift_min_cm1, name="shift_min_cm1"),
            )
        if self.shift_max_cm1 is not None:
            object.__setattr__(
                self,
                "shift_max_cm1",
                _finite_float(self.shift_max_cm1, name="shift_max_cm1"),
            )
        if (
            self.shift_min_cm1 is not None
            and self.shift_max_cm1 is not None
            and self.shift_min_cm1 > self.shift_max_cm1
        ):
            raise RamanError("shift_min_cm1 must be <= shift_max_cm1")

        if self.savgol_window_length is not None:
            if isinstance(self.savgol_window_length, bool):
                raise TypeError("savgol_window_length must be an integer")
            window = int(self.savgol_window_length)
            if window <= 0 or window != self.savgol_window_length:
                raise RamanError("savgol_window_length must be a positive integer")
            object.__setattr__(self, "savgol_window_length", window)
        if isinstance(self.savgol_polyorder, bool):
            raise TypeError("savgol_polyorder must be an integer")
        polyorder = int(self.savgol_polyorder)
        if polyorder < 0 or polyorder != self.savgol_polyorder:
            raise RamanError("savgol_polyorder must be a non-negative integer")
        object.__setattr__(self, "savgol_polyorder", polyorder)
        if self.savgol_window_length is not None and polyorder >= self.savgol_window_length:
            raise RamanError("savgol_polyorder must be smaller than savgol_window_length")
        mode = str(self.savgol_mode).strip()
        if not mode:
            raise RamanError("savgol_mode must not be empty")
        object.__setattr__(self, "savgol_mode", mode)

        if self.normalization not in {None, "max", "max_abs", "minmax", "area"}:
            raise RamanError(f"unsupported Raman normalization {self.normalization!r}")
        if self.normalization_area_mode not in {"absolute", "net"}:
            raise RamanError("normalization_area_mode must be 'absolute' or 'net'")
        target = _finite_float(self.normalization_target, name="normalization_target")
        if target <= 0:
            raise RamanError("normalization_target must be greater than zero for Raman")
        object.__setattr__(self, "normalization_target", target)
        object.__setattr__(
            self,
            "vertical_offset",
            _finite_float(self.vertical_offset, name="vertical_offset"),
        )


def process_raman(
    series: Series,
    config: RamanProcessingConfig,
    *,
    baseline: BaselineInput | None = None,
) -> Series:
    """Apply baseline -> crop -> Savitzky-Golay -> normalize -> offset."""
    if not isinstance(config, RamanProcessingConfig):
        raise TypeError("config must be a RamanProcessingConfig")
    validate_raman_series(series)

    result = series
    if baseline is not None:
        baseline_input = (
            _baseline_for_source(result, baseline)
            if isinstance(baseline, Series)
            else baseline
        )
        result = subtract_baseline(result, baseline_input)

    if config.shift_min_cm1 is not None or config.shift_max_cm1 is not None:
        result = crop(
            result,
            x_min=config.shift_min_cm1,
            x_max=config.shift_max_cm1,
        )

    if config.savgol_window_length is not None:
        result = savgol(
            result,
            window_length=config.savgol_window_length,
            polyorder=config.savgol_polyorder,
            mode=config.savgol_mode,
        )

    if config.normalization is not None:
        result = normalize(
            result,
            method=config.normalization,
            target=config.normalization_target,
            area_mode=config.normalization_area_mode,
        )
        result = _with_normalized_intensity_axis(
            result,
            method=config.normalization,
            target=config.normalization_target,
            area_mode=config.normalization_area_mode,
        )

    if config.vertical_offset != 0:
        result = offset(result, config.vertical_offset)

    validate_raman_series(result)
    return result


def _validate_keyed_mapping(
    dataset: Dataset,
    mapping: Mapping[str, Any],
    *,
    description: str,
) -> dict[str, Any]:
    copied = {str(key).strip(): value for key, value in dict(mapping).items()}
    if any(not key for key in copied):
        raise RamanError(f"{description} keys must be non-empty stable Series.key values")
    available = {item.key for item in dataset if item.key}
    unknown = set(copied) - available
    if unknown:
        raise RamanError(f"{description} keys not present in Dataset: {sorted(unknown)!r}")
    return copied


def process_raman_dataset(
    dataset: Dataset,
    config: RamanProcessingConfig,
    *,
    overrides: Mapping[str, RamanProcessingConfig] | None = None,
    baselines: Mapping[str, BaselineInput] | None = None,
) -> Dataset:
    """Process Raman spectra with optional stable-key-specific recipes."""
    if not isinstance(dataset, Dataset):
        raise TypeError("dataset must be a Dataset")
    if len(dataset) == 0:
        raise RamanError("cannot process an empty Raman Dataset")
    if not isinstance(config, RamanProcessingConfig):
        raise TypeError("config must be a RamanProcessingConfig")

    per_series = _validate_keyed_mapping(
        dataset,
        {} if overrides is None else overrides,
        description="override",
    )
    if not all(isinstance(value, RamanProcessingConfig) for value in per_series.values()):
        raise TypeError("all overrides must be RamanProcessingConfig instances")
    baseline_map = _validate_keyed_mapping(
        dataset,
        {} if baselines is None else baselines,
        description="baseline",
    )
    transformed = tuple(
        process_raman(
            item,
            per_series.get(item.key, config),
            baseline=baseline_map.get(item.key),
        )
        for item in dataset
    )
    return Dataset(
        series=transformed,
        name=dataset.name,
        metadata=dataset.metadata_dict(),
    )


def stack_raman_dataset(
    dataset: Dataset,
    *,
    step: float,
    start: float = 0.0,
) -> Dataset:
    """Return an ordered vertically offset Raman Dataset."""
    if not isinstance(dataset, Dataset):
        raise TypeError("dataset must be a Dataset")
    if len(dataset) == 0:
        raise RamanError("cannot stack an empty Raman Dataset")
    step_value = _finite_float(step, name="step")
    start_value = _finite_float(start, name="start")
    for item in dataset:
        validate_raman_series(item)

    stacked = tuple(
        offset(item, start_value + index * step_value)
        for index, item in enumerate(dataset)
    )
    metadata = dataset.metadata_dict()
    history = list(metadata.get("raman_stack_history", []))
    history.append(
        {
            "step": step_value,
            "start": start_value,
            "n_spectra": len(dataset),
        }
    )
    metadata["raman_stack_history"] = history
    return Dataset(series=stacked, name=dataset.name, metadata=metadata)


@dataclass(frozen=True, slots=True)
class RamanBand:
    """Explicit Raman-shift window used for direct band measurements."""

    x_min_cm1: float
    x_max_cm1: float
    label: str = ""

    def __post_init__(self) -> None:
        lower = _finite_float(self.x_min_cm1, name="band x_min_cm1")
        upper = _finite_float(self.x_max_cm1, name="band x_max_cm1")
        if lower >= upper:
            raise RamanError("RamanBand requires x_min_cm1 < x_max_cm1")
        object.__setattr__(self, "x_min_cm1", lower)
        object.__setattr__(self, "x_max_cm1", upper)
        object.__setattr__(self, "label", str(self.label).strip())


@dataclass(frozen=True, slots=True)
class RamanBandMeasurement:
    """Traceable direct window measurement for one Raman band."""

    band: RamanBand
    peak_position_cm1: float
    peak_intensity: float
    area: float
    area_mode: RamanAreaMode
    source_key: str
    source_label: str
    source_sha256: str
    n_points: int


@dataclass(frozen=True, slots=True)
class RamanRatioResult:
    """Traceable ratio between two explicit Raman-band measurements."""

    value: float
    metric: RamanRatioMetric
    numerator: RamanBandMeasurement
    denominator: RamanBandMeasurement


def _processing_history(series: Series) -> tuple[Mapping[str, Any], ...]:
    history = series.metadata.get("processing_history", ())
    return tuple(item for item in history if isinstance(item, Mapping))


def _require_quantitative_spectrum(series: Series) -> None:
    operations = [item.get("operation") for item in _processing_history(series)]
    if "offset" in operations:
        raise RamanError(
            "Raman band metrics cannot be computed after a vertical offset; "
            "measure the unstacked/pre-offset spectrum"
        )


def measure_raman_band(
    series: Series,
    band: RamanBand,
    *,
    area_mode: RamanAreaMode = "net",
) -> RamanBandMeasurement:
    """Measure direct peak height/position and trapezoidal area in an explicit window."""
    validate_raman_series(series)
    if not isinstance(band, RamanBand):
        raise TypeError("band must be a RamanBand")
    if area_mode not in {"absolute", "net"}:
        raise RamanError("area_mode must be 'absolute' or 'net'")
    _require_quantitative_spectrum(series)

    try:
        selected = crop(series, x_min=band.x_min_cm1, x_max=band.x_max_cm1)
        area_result = integrate(selected, absolute=area_mode == "absolute")
    except ProcessingError as exc:
        raise RamanError(f"cannot measure Raman band: {exc}") from exc

    y = np.asarray(selected.y, dtype=np.float64)
    peak_index = int(np.argmax(y))
    return RamanBandMeasurement(
        band=band,
        peak_position_cm1=float(selected.x[peak_index]),
        peak_intensity=float(y[peak_index]),
        area=float(area_result.value),
        area_mode=area_mode,
        source_key=series.key,
        source_label=series.label,
        source_sha256=area_result.source_sha256,
        n_points=selected.n_points,
    )


def raman_ratio(
    series: Series,
    numerator_band: RamanBand,
    denominator_band: RamanBand,
    *,
    metric: RamanRatioMetric = "height",
    area_mode: RamanAreaMode = "net",
) -> RamanRatioResult:
    """Return a peak-height or direct-band-area ratio for explicit windows."""
    if metric not in {"height", "area"}:
        raise RamanError("metric must be 'height' or 'area'")
    if series.y_axis.metadata.get("normalization_method") == "minmax":
        raise RamanError(
            "Raman ratios are not computed from min-max-normalized spectra because "
            "the additive shift changes peak-height and area ratios"
        )

    numerator = measure_raman_band(series, numerator_band, area_mode=area_mode)
    denominator = measure_raman_band(series, denominator_band, area_mode=area_mode)
    numerator_value = (
        numerator.peak_intensity if metric == "height" else numerator.area
    )
    denominator_value = (
        denominator.peak_intensity if metric == "height" else denominator.area
    )
    if not isfinite(numerator_value) or not isfinite(denominator_value):
        raise RamanError("Raman ratio metrics must be finite")
    if numerator_value < 0:
        raise RamanError("Raman ratio numerator metric must be non-negative")
    if denominator_value <= 0:
        raise RamanError("Raman ratio denominator metric must be greater than zero")

    return RamanRatioResult(
        value=float(numerator_value / denominator_value),
        metric=metric,
        numerator=numerator,
        denominator=denominator,
    )


def id_ig_ratio(
    series: Series,
    d_band: RamanBand,
    g_band: RamanBand,
    *,
    metric: RamanRatioMetric = "height",
    area_mode: RamanAreaMode = "net",
) -> RamanRatioResult:
    """Compute I_D/I_G or A_D/A_G using caller-supplied D and G windows."""
    return raman_ratio(
        series,
        d_band,
        g_band,
        metric=metric,
        area_mode=area_mode,
    )


@dataclass(frozen=True, slots=True)
class RamanPeakAnnotation:
    """One explicit Raman peak label anchored at a Raman-shift position."""

    shift_cm1: float
    text: str
    series_key: str | None = None
    text_offset_points: float = 4.0
    rotation: float = 90.0
    font_size: float | None = None
    color: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "shift_cm1",
            _finite_float(self.shift_cm1, name="shift_cm1"),
        )
        label = str(self.text).strip()
        if not label:
            raise RamanError("Raman peak annotation text must not be empty")
        object.__setattr__(self, "text", label)
        if self.series_key is not None:
            stable_key = str(self.series_key).strip()
            if not stable_key:
                raise RamanError("series_key must not be empty when supplied")
            object.__setattr__(self, "series_key", stable_key)
        object.__setattr__(
            self,
            "text_offset_points",
            _finite_float(self.text_offset_points, name="text_offset_points"),
        )
        object.__setattr__(
            self,
            "rotation",
            _finite_float(self.rotation, name="rotation"),
        )
        if self.font_size is not None:
            size = _finite_float(self.font_size, name="font_size")
            if size < 0:
                raise RamanError("font_size must be non-negative")
            object.__setattr__(self, "font_size", size)
        if self.color is not None:
            color = str(self.color).strip()
            if not color:
                raise RamanError("color must not be empty when supplied")
            object.__setattr__(self, "color", color)
