"""Scientific processing and quantitative helpers for FTIR / ATR-FTIR spectra."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Any, Literal

import numpy as np
from numpy.typing import ArrayLike

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.processing import (
    ProcessingError,
    crop,
    normalize,
    offset,
    subtract_baseline,
)

FTIRNormalization = Literal["max", "max_abs", "minmax", "area"]
FTIRAreaMode = Literal["absolute", "net"]
FTIRTransmittanceScale = Literal["fraction", "percent"]
FTIRWavenumberDirection = Literal["ascending", "descending"]

_WAVENUMBER_NAMES = {"wavenumber", "wn"}
_INVERSE_CM_UNITS = {"cm^-1", "cm-1", "1/cm", "cm**-1", "cm^(-1)"}
_ABSORBANCE_NAMES = {"absorbance"}
_NORMALIZED_ABSORBANCE_NAMES = {"normalizedabsorbance"}
_TRANSMITTANCE_NAMES = {"transmittance"}
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
_DIMENSIONLESS_UNITS = {"1", "dimensionless", "abs"}
_PERCENT_UNITS = {"%", "percent", "percentage"}
_FRACTION_UNITS = {"1", "fraction", "dimensionless"}


class FTIRError(ValueError):
    """Raised when FTIR data or a requested FTIR operation is invalid."""


def _finite_float(value: Any, *, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a real numeric value") from exc
    if not isfinite(result):
        raise FTIRError(f"{name} must be finite")
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


def _wavenumber_unit(unit: str | None) -> str:
    if unit is None or not str(unit).strip():
        raise FTIRError("FTIR wavenumber requires an explicit inverse-centimetre unit")
    compact = _compact_unit(str(unit))
    if compact not in _INVERSE_CM_UNITS:
        raise FTIRError(
            f"unsupported FTIR wavenumber unit {unit!r}; use cm^-1, cm-1, 1/cm, or cm⁻¹"
        )
    return "cm^-1"


def _y_kind(series: Series) -> Literal["absorbance", "normalized_absorbance", "transmittance"]:
    token = _semantic_token(series.y_axis.name)
    if token in _ABSORBANCE_NAMES:
        return "absorbance"
    if token in _NORMALIZED_ABSORBANCE_NAMES:
        return "normalized_absorbance"
    if token in _TRANSMITTANCE_NAMES:
        return "transmittance"
    raise FTIRError(
        "FTIR requires y_axis.name='absorbance', 'transmittance', "
        "or 'normalized_absorbance'"
    )


def _absorbance_unit(unit: str | None, *, normalized: bool) -> str | None:
    if unit is None or not str(unit).strip():
        return "a.u." if normalized else None
    compact = _compact_unit(str(unit))
    if compact in _ARBITRARY_UNITS:
        return "a.u."
    if compact in _DIMENSIONLESS_UNITS:
        return "a.u." if normalized else None
    raise FTIRError(
        f"unsupported FTIR absorbance unit {unit!r}; use dimensionless or arbitrary units"
    )


def _transmittance_scale_from_unit(unit: str | None) -> FTIRTransmittanceScale:
    if unit is None or not str(unit).strip():
        raise FTIRError("transmittance requires an explicit fraction or percent unit/scale")
    compact = _compact_unit(str(unit))
    if compact in _PERCENT_UNITS:
        return "percent"
    if compact in _FRACTION_UNITS:
        return "fraction"
    raise FTIRError(
        f"unsupported FTIR transmittance unit {unit!r}; use %, percent, 1, or fraction"
    )


def _array_digest(values: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(values)
    digest = hashlib.sha256()
    digest.update(str(contiguous.dtype).encode("ascii"))
    digest.update(str(contiguous.shape).encode("ascii"))
    digest.update(contiguous.tobytes(order="C"))
    return digest.hexdigest()


def _series_data_digest(series: Series) -> str:
    digest = hashlib.sha256()
    digest.update(_array_digest(np.asarray(series.x)).encode("ascii"))
    digest.update(_array_digest(np.asarray(series.y)).encode("ascii"))
    return digest.hexdigest()


def _monotonic_direction(x: np.ndarray) -> FTIRWavenumberDirection:
    delta = np.diff(x)
    if np.all(delta > 0):
        return "ascending"
    if np.all(delta < 0):
        return "descending"
    raise FTIRError("FTIR wavenumber values must be strictly monotonic without duplicates")


def validate_ftir_series(series: Series) -> None:
    """Validate one FTIR spectrum without modifying it."""
    if not isinstance(series, Series):
        raise TypeError("series must be a Series")
    if _semantic_token(series.x_axis.name) not in _WAVENUMBER_NAMES:
        raise FTIRError(
            "FTIR requires x_axis.name to identify wavenumber "
            "(for example 'wavenumber' or 'wn')"
        )
    _wavenumber_unit(series.x_axis.unit)

    kind = _y_kind(series)
    if kind == "transmittance":
        _transmittance_scale_from_unit(series.y_axis.unit)
    else:
        _absorbance_unit(series.y_axis.unit, normalized=kind == "normalized_absorbance")

    x = np.asarray(series.x)
    if np.iscomplexobj(x):
        raise FTIRError("FTIR wavenumber values must be real")
    x = x.astype(np.float64, copy=False)
    if x.size < 2:
        raise FTIRError("FTIR spectra require at least two wavenumber points")
    if np.isnan(x).any() or np.isinf(x).any():
        raise FTIRError("FTIR wavenumber values must be finite")
    _monotonic_direction(x)

    y = np.asarray(series.y)
    if np.iscomplexobj(y):
        raise FTIRError("FTIR y values must be real")
    if np.isinf(y).any():
        raise FTIRError("FTIR y values must not contain +/-inf")


def _canonicalize_ftir_series(series: Series) -> Series:
    validate_ftir_series(series)
    kind = _y_kind(series)
    if kind == "transmittance":
        scale = _transmittance_scale_from_unit(series.y_axis.unit)
        canonical_unit: str | None = "%" if scale == "percent" else "1"
        label = series.y_axis.label or "Transmittance"
    elif kind == "normalized_absorbance":
        canonical_unit = "a.u."
        label = series.y_axis.label or "Normalized absorbance"
    else:
        canonical_unit = _absorbance_unit(series.y_axis.unit, normalized=False)
        label = series.y_axis.label or "Absorbance"

    return Series(
        x=series.x,
        y=series.y,
        label=series.label,
        key=series.key,
        x_axis=Axis(
            "wavenumber",
            unit="cm^-1",
            label=series.x_axis.label or "Wavenumber",
            metadata=series.x_axis.metadata_dict(),
        ),
        y_axis=Axis(
            kind,
            unit=canonical_unit,
            label=label,
            metadata=series.y_axis.metadata_dict(),
        ),
        metadata=series.metadata_dict(),
    )


def _with_processing_record(
    series: Series,
    *,
    operation: str,
    parameters: Mapping[str, Any],
    y: ArrayLike | None = None,
    y_axis: Axis | None = None,
) -> Series:
    metadata = series.metadata_dict()
    history = list(metadata.get("processing_history", []))
    history.append({"operation": operation, "parameters": dict(parameters)})
    metadata["processing_history"] = history
    return Series(
        x=series.x,
        y=series.y if y is None else y,
        label=series.label,
        key=series.key,
        x_axis=series.x_axis,
        y_axis=series.y_axis if y_axis is None else y_axis,
        metadata=metadata,
    )


def transmittance_to_absorbance(
    series: Series,
    *,
    input_scale: FTIRTransmittanceScale,
) -> Series:
    """Convert explicit transmittance to absorbance using ``A = -log10(T)``."""
    canonical = _canonicalize_ftir_series(series)
    if _y_kind(canonical) != "transmittance":
        raise FTIRError("transmittance_to_absorbance requires transmittance data")
    if input_scale not in {"fraction", "percent"}:
        raise FTIRError("input_scale must be 'fraction' or 'percent'")

    declared = _transmittance_scale_from_unit(series.y_axis.unit)
    if declared != input_scale:
        raise FTIRError(
            f"input_scale={input_scale!r} conflicts with transmittance unit "
            f"{series.y_axis.unit!r} ({declared})"
        )

    values = np.asarray(canonical.y, dtype=np.float64)
    if np.isnan(values).any():
        raise FTIRError("transmittance_to_absorbance does not silently discard missing values")
    fraction = values / 100.0 if input_scale == "percent" else values
    if np.any(fraction <= 0.0) or np.any(fraction > 1.0):
        raise FTIRError(
            "transmittance must satisfy 0 < T <= 1 after explicit scale conversion; "
            "values are not clipped"
        )

    converted = -np.log10(fraction)
    source_sha256 = _series_data_digest(canonical)
    y_metadata = canonical.y_axis.metadata_dict()
    y_metadata.update(
        {
            "conversion": "transmittance_to_absorbance",
            "transmittance_input_scale": input_scale,
            "source_sha256": source_sha256,
        }
    )
    return _with_processing_record(
        canonical,
        operation="transmittance_to_absorbance",
        parameters={
            "formula": "A=-log10(T)",
            "input_scale": input_scale,
            "source_sha256": source_sha256,
        },
        y=converted,
        y_axis=Axis("absorbance", unit=None, label="Absorbance", metadata=y_metadata),
    )


@dataclass(frozen=True, slots=True)
class FTIRBaselineWindow:
    """Explicit wavenumber interval used to fit an FTIR baseline."""

    low_cm1: float
    high_cm1: float

    def __post_init__(self) -> None:
        low = _finite_float(self.low_cm1, name="low_cm1")
        high = _finite_float(self.high_cm1, name="high_cm1")
        if low >= high:
            raise FTIRError("baseline window requires low_cm1 < high_cm1")
        object.__setattr__(self, "low_cm1", low)
        object.__setattr__(self, "high_cm1", high)


@dataclass(frozen=True, slots=True)
class FTIRBaselineFit:
    """Traceable polynomial baseline fitted to explicit FTIR windows."""

    baseline: Series
    windows: tuple[FTIRBaselineWindow, ...]
    degree: int
    scaled_coefficients: tuple[float, ...]
    x_center_cm1: float
    x_scale_cm1: float
    n_fit_points: int
    source_key: str
    source_label: str
    source_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.baseline, Series):
            raise TypeError("baseline must be a Series")
        if self.degree < 0:
            raise FTIRError("degree must be non-negative")
        if self.n_fit_points <= self.degree:
            raise FTIRError("baseline fit requires more fit points than polynomial degree")


def _require_absorbance_like(series: Series, *, operation: str) -> str:
    kind = _y_kind(series)
    if kind == "transmittance":
        raise FTIRError(
            f"{operation} requires absorbance-like data; convert transmittance explicitly first"
        )
    return kind


def fit_ftir_baseline(
    series: Series,
    windows: Sequence[FTIRBaselineWindow | tuple[float, float]],
    *,
    degree: int = 1,
) -> FTIRBaselineFit:
    """Fit a polynomial baseline using only caller-supplied baseline windows."""
    source = _canonicalize_ftir_series(series)
    _require_absorbance_like(source, operation="fit_ftir_baseline")

    if isinstance(degree, bool) or not isinstance(degree, int):
        raise TypeError("degree must be an integer")
    if degree < 0:
        raise FTIRError("degree must be non-negative")

    resolved_windows: list[FTIRBaselineWindow] = []
    for item in windows:
        if isinstance(item, FTIRBaselineWindow):
            window = item
        else:
            try:
                low, high = item
            except (TypeError, ValueError) as exc:
                raise TypeError(
                    "windows must contain FTIRBaselineWindow or (low_cm1, high_cm1) pairs"
                ) from exc
            window = FTIRBaselineWindow(low, high)
        resolved_windows.append(window)
    if not resolved_windows:
        raise FTIRError("fit_ftir_baseline requires at least one baseline window")

    x = np.asarray(source.x, dtype=np.float64)
    y = np.asarray(source.y, dtype=np.float64)
    lower, upper = float(np.min(x)), float(np.max(x))
    mask = np.zeros(x.size, dtype=bool)
    for window in resolved_windows:
        if window.low_cm1 < lower or window.high_cm1 > upper:
            raise FTIRError(
                "every baseline window must be fully contained in the measured wavenumber range"
            )
        mask |= (x >= window.low_cm1) & (x <= window.high_cm1)

    x_fit = x[mask]
    y_fit = y[mask]
    if x_fit.size <= degree:
        raise FTIRError("baseline fit requires more selected fit points than polynomial degree")
    if np.isnan(y_fit).any():
        raise FTIRError(
            "baseline fit windows contain missing absorbance values; clean them explicitly"
        )

    center = float((np.min(x_fit) + np.max(x_fit)) / 2.0)
    scale = float((np.max(x_fit) - np.min(x_fit)) / 2.0)
    if scale == 0.0:
        raise FTIRError("baseline fit windows must span more than one wavenumber")
    z_fit = (x_fit - center) / scale
    design = np.vander(z_fit, N=degree + 1, increasing=True)
    coefficients, _, rank, _ = np.linalg.lstsq(design, y_fit, rcond=None)
    if int(rank) < degree + 1:
        raise FTIRError("baseline polynomial design is rank-deficient for the selected windows")

    z_all = (x - center) / scale
    baseline_values = np.polynomial.polynomial.polyval(z_all, coefficients)
    source_sha256 = _series_data_digest(source)
    fit_parameters = {
        "method": "polynomial_least_squares",
        "degree": degree,
        "windows_cm1": tuple((window.low_cm1, window.high_cm1) for window in resolved_windows),
        "n_fit_points": int(x_fit.size),
        "source_sha256": source_sha256,
        "x_center_cm1": center,
        "x_scale_cm1": scale,
    }
    baseline_metadata = source.metadata_dict()
    history = list(baseline_metadata.get("processing_history", []))
    history.append({"operation": "fit_ftir_baseline", "parameters": fit_parameters})
    baseline_metadata["processing_history"] = history
    baseline = Series(
        x=source.x,
        y=baseline_values,
        label=f"{source.label} baseline".strip(),
        key=f"{source.key}:baseline" if source.key else "",
        x_axis=source.x_axis,
        y_axis=source.y_axis,
        metadata=baseline_metadata,
    )
    return FTIRBaselineFit(
        baseline=baseline,
        windows=tuple(resolved_windows),
        degree=degree,
        scaled_coefficients=tuple(float(value) for value in coefficients),
        x_center_cm1=center,
        x_scale_cm1=scale,
        n_fit_points=int(x_fit.size),
        source_key=source.key,
        source_label=source.label,
        source_sha256=source_sha256,
    )


def _baseline_series_for_source(source: Series, baseline: Series) -> Series:
    canonical = _canonicalize_ftir_series(baseline)
    _require_absorbance_like(canonical, operation="baseline subtraction")
    if not np.array_equal(source.x, canonical.x, equal_nan=True):
        raise FTIRError("baseline Series must use exactly the same wavenumber grid")
    if _y_kind(source) != _y_kind(canonical):
        raise FTIRError("baseline Series must use the same absorbance semantic as source")
    if source.y_axis.unit != canonical.y_axis.unit:
        raise FTIRError("baseline Series must use the same absorbance unit as source")
    return canonical


def subtract_ftir_baseline(
    series: Series,
    baseline: FTIRBaselineFit | Series | ArrayLike | float,
) -> Series:
    """Subtract an explicitly supplied FTIR baseline on the exact source grid."""
    source = _canonicalize_ftir_series(series)
    _require_absorbance_like(source, operation="subtract_ftir_baseline")

    if isinstance(baseline, FTIRBaselineFit):
        if baseline.source_sha256 != _series_data_digest(source):
            raise FTIRError(
                "FTIRBaselineFit was fitted from different source data; refit on this spectrum"
            )
        resolved: Series | ArrayLike | float = _baseline_series_for_source(
            source, baseline.baseline
        )
    elif isinstance(baseline, Series):
        resolved = _baseline_series_for_source(source, baseline)
    else:
        resolved = baseline

    try:
        return subtract_baseline(source, resolved)
    except ProcessingError as exc:
        raise FTIRError(str(exc)) from exc


@dataclass(frozen=True, slots=True)
class FTIRProcessingConfig:
    """Explicit, non-automatic processing recipe for one FTIR spectrum."""

    wavenumber_min_cm1: float | None = None
    wavenumber_max_cm1: float | None = None
    normalization: FTIRNormalization | None = None
    normalization_target: float = 1.0
    normalization_area_mode: FTIRAreaMode = "absolute"
    vertical_offset: float = 0.0

    def __post_init__(self) -> None:
        minimum = (
            None
            if self.wavenumber_min_cm1 is None
            else _finite_float(self.wavenumber_min_cm1, name="wavenumber_min_cm1")
        )
        maximum = (
            None
            if self.wavenumber_max_cm1 is None
            else _finite_float(self.wavenumber_max_cm1, name="wavenumber_max_cm1")
        )
        if minimum is not None and maximum is not None and minimum > maximum:
            raise FTIRError("wavenumber_min_cm1 must be <= wavenumber_max_cm1")
        if self.normalization not in {None, "max", "max_abs", "minmax", "area"}:
            raise FTIRError(f"unsupported FTIR normalization {self.normalization!r}")
        target = _finite_float(self.normalization_target, name="normalization_target")
        if self.normalization is not None and target <= 0:
            raise FTIRError("normalization_target must be greater than zero")
        if self.normalization_area_mode not in {"absolute", "net"}:
            raise FTIRError("normalization_area_mode must be 'absolute' or 'net'")
        vertical = _finite_float(self.vertical_offset, name="vertical_offset")
        object.__setattr__(self, "wavenumber_min_cm1", minimum)
        object.__setattr__(self, "wavenumber_max_cm1", maximum)
        object.__setattr__(self, "normalization_target", target)
        object.__setattr__(self, "vertical_offset", vertical)


def _with_normalized_absorbance_axis(
    series: Series,
    *,
    method: FTIRNormalization,
    target: float,
    area_mode: FTIRAreaMode,
) -> Series:
    metadata = series.y_axis.metadata_dict()
    signature = f"ftir:{method}:target={float(target)!r}"
    if method == "area":
        signature += f":area_mode={area_mode}"
    metadata.update(
        {
            "normalization": signature,
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
        key=series.key,
        x_axis=series.x_axis,
        y_axis=Axis(
            "normalized_absorbance",
            unit="a.u.",
            label="Normalized absorbance",
            metadata=metadata,
        ),
        metadata=series.metadata_dict(),
    )


def process_ftir(
    series: Series,
    config: FTIRProcessingConfig | None = None,
    *,
    baseline: FTIRBaselineFit | Series | ArrayLike | float | None = None,
) -> Series:
    """Apply only explicitly requested FTIR processing operations."""
    resolved = FTIRProcessingConfig() if config is None else config
    if not isinstance(resolved, FTIRProcessingConfig):
        raise TypeError("config must be an FTIRProcessingConfig")

    result = _canonicalize_ftir_series(series)
    if baseline is not None:
        result = subtract_ftir_baseline(result, baseline)
    if resolved.wavenumber_min_cm1 is not None or resolved.wavenumber_max_cm1 is not None:
        result = crop(
            result,
            x_min=resolved.wavenumber_min_cm1,
            x_max=resolved.wavenumber_max_cm1,
        )
    if resolved.normalization is not None:
        _require_absorbance_like(result, operation="FTIR normalization")
        try:
            result = normalize(
                result,
                method=resolved.normalization,
                target=resolved.normalization_target,
                area_mode=resolved.normalization_area_mode,
            )
        except ProcessingError as exc:
            raise FTIRError(str(exc)) from exc
        result = _with_normalized_absorbance_axis(
            result,
            method=resolved.normalization,
            target=resolved.normalization_target,
            area_mode=resolved.normalization_area_mode,
        )
    if resolved.vertical_offset != 0.0:
        try:
            result = offset(result, resolved.vertical_offset)
        except ProcessingError as exc:
            raise FTIRError(str(exc)) from exc
    return result


def _require_keyed_dataset(dataset: Dataset, *, operation: str) -> None:
    if not isinstance(dataset, Dataset):
        raise TypeError("dataset must be a Dataset")
    if any(not key for key in dataset.keys):
        raise FTIRError(f"{operation} requires non-empty Series.key values")


def process_ftir_dataset(
    dataset: Dataset,
    config: FTIRProcessingConfig | None = None,
    *,
    overrides: Mapping[str, FTIRProcessingConfig] | None = None,
    baselines: Mapping[str, FTIRBaselineFit | Series | ArrayLike | float] | None = None,
) -> Dataset:
    """Process an FTIR Dataset with stable-key overrides and baselines."""
    _require_keyed_dataset(dataset, operation="process_ftir_dataset")
    default = FTIRProcessingConfig() if config is None else config
    if not isinstance(default, FTIRProcessingConfig):
        raise TypeError("config must be an FTIRProcessingConfig")

    override_map = {} if overrides is None else dict(overrides)
    baseline_map = {} if baselines is None else dict(baselines)
    known = set(dataset.keys)
    unknown_overrides = set(override_map) - known
    unknown_baselines = set(baseline_map) - known
    if unknown_overrides:
        raise FTIRError(f"override keys not present in Dataset: {sorted(unknown_overrides)!r}")
    if unknown_baselines:
        raise FTIRError(f"baseline keys not present in Dataset: {sorted(unknown_baselines)!r}")

    processed = tuple(
        process_ftir(
            item,
            override_map.get(item.key, default),
            baseline=baseline_map.get(item.key),
        )
        for item in dataset
    )
    return Dataset(series=processed, name=dataset.name, metadata=dataset.metadata_dict())


def _overlay_signature(series: Series) -> tuple[str, str | None, str | None]:
    canonical = _canonicalize_ftir_series(series)
    kind = _y_kind(canonical)
    normalization = canonical.y_axis.metadata.get("normalization")
    return kind, canonical.y_axis.unit, None if normalization is None else str(normalization)


def validate_ftir_overlay(data: Series | Dataset) -> None:
    """Reject overlays with mixed FTIR y semantics, units, or normalization state."""
    if isinstance(data, Series):
        validate_ftir_series(data)
        return
    if not isinstance(data, Dataset):
        raise TypeError("data must be a Series or Dataset")
    if len(data) == 0:
        raise FTIRError("cannot use an empty FTIR Dataset")
    signatures = [_overlay_signature(item) for item in data]
    first = signatures[0]
    for index, signature in enumerate(signatures[1:], start=1):
        if signature != first:
            raise FTIRError(
                "FTIR overlay requires matching y semantic/unit/normalization state; "
                f"Series index {index} has {signature!r}, expected {first!r}"
            )


def stack_ftir_dataset(dataset: Dataset, *, step: float, start: float = 0.0) -> Dataset:
    """Apply explicit vertical offsets to an FTIR Dataset in stable order."""
    _require_keyed_dataset(dataset, operation="stack_ftir_dataset")
    validate_ftir_overlay(dataset)
    step_value = _finite_float(step, name="step")
    start_value = _finite_float(start, name="start")
    stacked = tuple(
        offset(_canonicalize_ftir_series(item), start_value + index * step_value)
        for index, item in enumerate(dataset)
    )
    metadata = dataset.metadata_dict()
    history = list(metadata.get("ftir_stack_history", []))
    history.append({"step": step_value, "start": start_value, "keys": dataset.keys})
    metadata["ftir_stack_history"] = history
    return Dataset(series=stacked, name=dataset.name, metadata=metadata)


@dataclass(frozen=True, slots=True)
class FTIRBand:
    """Explicit FTIR band window."""

    low_cm1: float
    high_cm1: float
    label: str = ""

    def __post_init__(self) -> None:
        low = _finite_float(self.low_cm1, name="low_cm1")
        high = _finite_float(self.high_cm1, name="high_cm1")
        if low >= high:
            raise FTIRError("FTIRBand requires low_cm1 < high_cm1")
        object.__setattr__(self, "low_cm1", low)
        object.__setattr__(self, "high_cm1", high)
        object.__setattr__(self, "label", str(self.label).strip())


@dataclass(frozen=True, slots=True)
class FTIRBandMeasurement:
    """Traceable direct-window FTIR band measurement."""

    band: FTIRBand
    peak_position_cm1: float
    peak_absorbance: float
    area: float
    area_mode: FTIRAreaMode
    n_points: int
    integration_n_points: int
    integration_direction: str
    source_direction: FTIRWavenumberDirection
    source_key: str
    source_label: str
    source_sha256: str
    window_sha256: str
    wavenumber_unit: str
    absorbance_unit: str | None


def _ascending_xy(series: Series) -> tuple[np.ndarray, np.ndarray, FTIRWavenumberDirection]:
    x = np.asarray(series.x, dtype=np.float64)
    y = np.asarray(series.y, dtype=np.float64)
    direction = _monotonic_direction(x)
    if direction == "descending":
        return x[::-1], y[::-1], direction
    return x, y, direction


def measure_ftir_band(
    series: Series,
    band: FTIRBand,
    *,
    area_mode: FTIRAreaMode = "net",
) -> FTIRBandMeasurement:
    """Measure direct peak and low-to-high-wavenumber area in one explicit band."""
    source = _canonicalize_ftir_series(series)
    _require_absorbance_like(source, operation="measure_ftir_band")
    if not isinstance(band, FTIRBand):
        raise TypeError("band must be an FTIRBand")
    if area_mode not in {"net", "absolute"}:
        raise FTIRError("area_mode must be 'net' or 'absolute'")

    x_asc, y_asc, source_direction = _ascending_xy(source)
    if band.low_cm1 < x_asc[0] or band.high_cm1 > x_asc[-1]:
        raise FTIRError("FTIR band window must be fully contained in the measured range")

    measured_mask = (x_asc >= band.low_cm1) & (x_asc <= band.high_cm1)
    if not measured_mask.any():
        raise FTIRError("FTIR band contains no measured points")
    measured_y = y_asc[measured_mask]
    measured_x = x_asc[measured_mask]
    if np.isnan(measured_y).any():
        raise FTIRError("FTIR band contains missing absorbance values")

    interior_mask = (x_asc > band.low_cm1) & (x_asc < band.high_cm1)
    integration_x = np.concatenate(
        (np.array([band.low_cm1]), x_asc[interior_mask], np.array([band.high_cm1]))
    )
    integration_x = np.unique(integration_x)
    finite_mask = (x_asc >= band.low_cm1) & (x_asc <= band.high_cm1)
    if np.isnan(y_asc[finite_mask]).any():
        raise FTIRError("FTIR integration window contains missing absorbance values")
    integration_y = np.interp(integration_x, x_asc, y_asc)

    if area_mode == "absolute":
        area = float(np.trapezoid(np.abs(integration_y), x=integration_x))
    else:
        area = float(np.trapezoid(integration_y, x=integration_x))

    peak_index = int(np.argmax(measured_y))
    window_digest = hashlib.sha256()
    window_digest.update(_array_digest(integration_x).encode("ascii"))
    window_digest.update(_array_digest(integration_y).encode("ascii"))

    return FTIRBandMeasurement(
        band=band,
        peak_position_cm1=float(measured_x[peak_index]),
        peak_absorbance=float(measured_y[peak_index]),
        area=area,
        area_mode=area_mode,
        n_points=int(measured_x.size),
        integration_n_points=int(integration_x.size),
        integration_direction="low_to_high_wavenumber",
        source_direction=source_direction,
        source_key=source.key,
        source_label=source.label,
        source_sha256=_series_data_digest(source),
        window_sha256=window_digest.hexdigest(),
        wavenumber_unit="cm^-1",
        absorbance_unit=source.y_axis.unit,
    )


@dataclass(frozen=True, slots=True)
class FTIRPeakAnnotation:
    """One publication annotation at an explicit FTIR wavenumber."""

    wavenumber_cm1: float
    text: str
    series_key: str | None = None
    text_offset_points: float = 6.0
    rotation: float = 90.0
    font_size: float | None = None
    color: str | None = None

    def __post_init__(self) -> None:
        position = _finite_float(self.wavenumber_cm1, name="wavenumber_cm1")
        text = str(self.text).strip()
        if not text:
            raise FTIRError("FTIRPeakAnnotation.text must not be empty")
        key = None if self.series_key is None else str(self.series_key).strip()
        offset_points = _finite_float(self.text_offset_points, name="text_offset_points")
        rotation = _finite_float(self.rotation, name="rotation")
        font_size = (
            None
            if self.font_size is None
            else _finite_float(self.font_size, name="font_size")
        )
        if font_size is not None and font_size <= 0:
            raise FTIRError("font_size must be greater than zero")
        object.__setattr__(self, "wavenumber_cm1", position)
        object.__setattr__(self, "text", text)
        object.__setattr__(self, "series_key", key or None)
        object.__setattr__(self, "text_offset_points", offset_points)
        object.__setattr__(self, "rotation", rotation)
        object.__setattr__(self, "font_size", font_size)
