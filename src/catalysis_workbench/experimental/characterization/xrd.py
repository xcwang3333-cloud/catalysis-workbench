"""Scientific processing models for powder X-ray diffraction patterns."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Any, Literal

import numpy as np
from numpy.typing import ArrayLike

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.processing import crop, normalize, offset, subtract_baseline

XRDNormalization = Literal["max", "max_abs", "minmax", "area"]
XRDAreaMode = Literal["absolute", "net"]
BaselineInput = Series | ArrayLike | float | complex

_TWO_THETA_NAMES = {"twotheta", "2theta"}
_INTENSITY_NAMES = {"intensity", "normalizedintensity"}
_DEGREE_UNITS = {"deg", "degree", "degrees", "°"}


class XRDError(ValueError):
    """Raised when XRD data or a requested XRD operation is scientifically invalid."""


def _finite_float(value: Any, *, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a real numeric value") from exc
    if not isfinite(result):
        raise XRDError(f"{name} must be finite")
    return result


def _semantic_token(value: str) -> str:
    token = str(value).strip().casefold().replace("θ", "theta")
    return "".join(character for character in token if character.isalnum())


def _degree_unit(unit: str | None) -> str:
    if unit is None or not str(unit).strip():
        raise XRDError("XRD 2theta axis requires an explicit degree unit")
    normalized = str(unit).strip().casefold()
    if normalized not in _DEGREE_UNITS:
        raise XRDError(
            f"unsupported XRD 2theta unit {unit!r}; use deg, degree(s), or °"
        )
    return normalized


def validate_xrd_series(series: Series) -> None:
    """Validate one experimental XRD pattern without modifying it."""
    if not isinstance(series, Series):
        raise TypeError("series must be a Series")

    if _semantic_token(series.x_axis.name) not in _TWO_THETA_NAMES:
        raise XRDError(
            "XRD requires x_axis.name to identify 2theta "
            "(for example 'two_theta', '2theta', or '2θ')"
        )
    _degree_unit(series.x_axis.unit)

    if _semantic_token(series.y_axis.name) not in _INTENSITY_NAMES:
        raise XRDError(
            "XRD requires y_axis.name='intensity' or 'normalized_intensity'"
        )

    x = np.asarray(series.x)
    if np.iscomplexobj(x):
        raise XRDError("XRD 2theta values must be real")
    x = x.astype(np.float64, copy=False)
    if x.size < 2:
        raise XRDError("XRD requires at least two 2theta points")
    if np.isnan(x).any() or np.isinf(x).any():
        raise XRDError("XRD 2theta values must be finite")
    if not np.all(np.diff(x) > 0):
        raise XRDError("XRD 2theta values must be strictly increasing without duplicates")

    y = np.asarray(series.y)
    if np.iscomplexobj(y):
        raise XRDError("XRD intensity values must be real")
    if np.isinf(y).any():
        raise XRDError("XRD intensity values must not contain +/-inf")


def _with_normalized_intensity_axis(
    series: Series,
    *,
    method: XRDNormalization,
    target: float,
    area_mode: XRDAreaMode,
) -> Series:
    metadata = series.y_axis.metadata_dict()
    metadata.update(
        {
            "normalization": "xrd_normalized",
            "normalization_method": method,
            "normalization_target": target,
        }
    )
    if method == "area":
        metadata["normalization_area_mode"] = area_mode
    y_axis = Axis(
        name="normalized_intensity",
        unit="a.u.",
        label="Normalized intensity",
        metadata=metadata,
    )
    return Series(
        x=series.x,
        y=series.y,
        label=series.label,
        x_axis=series.x_axis,
        y_axis=y_axis,
        metadata=series.metadata_dict(),
        key=series.key,
    )


@dataclass(frozen=True, slots=True)
class XRDProcessingConfig:
    """Serializable processing recipe for one XRD pattern.

    An explicitly supplied baseline is passed separately to :func:`process_xrd` so
    large numerical baseline arrays do not become hidden state inside the config.
    """

    x_min_deg: float | None = None
    x_max_deg: float | None = None
    normalization: XRDNormalization | None = None
    normalization_target: float = 1.0
    normalization_area_mode: XRDAreaMode = "absolute"
    vertical_offset: float = 0.0

    def __post_init__(self) -> None:
        if self.x_min_deg is not None:
            object.__setattr__(
                self,
                "x_min_deg",
                _finite_float(self.x_min_deg, name="x_min_deg"),
            )
        if self.x_max_deg is not None:
            object.__setattr__(
                self,
                "x_max_deg",
                _finite_float(self.x_max_deg, name="x_max_deg"),
            )
        if (
            self.x_min_deg is not None
            and self.x_max_deg is not None
            and self.x_min_deg > self.x_max_deg
        ):
            raise XRDError("x_min_deg must be less than or equal to x_max_deg")

        if self.normalization not in {None, "max", "max_abs", "minmax", "area"}:
            raise XRDError(f"unsupported XRD normalization {self.normalization!r}")
        if self.normalization_area_mode not in {"absolute", "net"}:
            raise XRDError("normalization_area_mode must be 'absolute' or 'net'")
        object.__setattr__(
            self,
            "normalization_target",
            _finite_float(self.normalization_target, name="normalization_target"),
        )
        object.__setattr__(
            self,
            "vertical_offset",
            _finite_float(self.vertical_offset, name="vertical_offset"),
        )


def process_xrd(
    series: Series,
    config: XRDProcessingConfig,
    *,
    baseline: BaselineInput | None = None,
) -> Series:
    """Apply deterministic baseline -> crop -> normalize -> offset processing."""
    if not isinstance(config, XRDProcessingConfig):
        raise TypeError("config must be an XRDProcessingConfig")
    validate_xrd_series(series)

    result = series
    if baseline is not None:
        if isinstance(baseline, Series):
            validate_xrd_series(baseline)
        result = subtract_baseline(result, baseline)

    if config.x_min_deg is not None or config.x_max_deg is not None:
        result = crop(
            result,
            x_min=config.x_min_deg,
            x_max=config.x_max_deg,
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

    validate_xrd_series(result)
    return result


def _validate_keyed_mapping(
    dataset: Dataset,
    mapping: Mapping[str, Any],
    *,
    description: str,
) -> dict[str, Any]:
    copied = {str(key).strip(): value for key, value in dict(mapping).items()}
    if any(not key for key in copied):
        raise XRDError(f"{description} keys must be non-empty stable Series.key values")
    available = {item.key for item in dataset if item.key}
    unknown = set(copied) - available
    if unknown:
        raise XRDError(f"{description} keys not present in Dataset: {sorted(unknown)!r}")
    return copied


def process_xrd_dataset(
    dataset: Dataset,
    config: XRDProcessingConfig,
    *,
    overrides: Mapping[str, XRDProcessingConfig] | None = None,
    baselines: Mapping[str, BaselineInput] | None = None,
) -> Dataset:
    """Process several patterns with optional stable-key-specific recipes/baselines."""
    if not isinstance(dataset, Dataset):
        raise TypeError("dataset must be a Dataset")
    if len(dataset) == 0:
        raise XRDError("cannot process an empty XRD Dataset")
    if not isinstance(config, XRDProcessingConfig):
        raise TypeError("config must be an XRDProcessingConfig")

    per_series = _validate_keyed_mapping(
        dataset,
        {} if overrides is None else overrides,
        description="override",
    )
    if not all(isinstance(value, XRDProcessingConfig) for value in per_series.values()):
        raise TypeError("all overrides must be XRDProcessingConfig instances")
    baseline_map = _validate_keyed_mapping(
        dataset,
        {} if baselines is None else baselines,
        description="baseline",
    )

    transformed = tuple(
        process_xrd(
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


def stack_xrd_dataset(
    dataset: Dataset,
    *,
    step: float,
    start: float = 0.0,
) -> Dataset:
    """Return an ordered vertically offset XRD Dataset using the shared offset primitive."""
    if not isinstance(dataset, Dataset):
        raise TypeError("dataset must be a Dataset")
    if len(dataset) == 0:
        raise XRDError("cannot stack an empty XRD Dataset")
    step_value = _finite_float(step, name="step")
    start_value = _finite_float(start, name="start")
    for item in dataset:
        validate_xrd_series(item)

    stacked = tuple(
        offset(item, start_value + index * step_value)
        for index, item in enumerate(dataset)
    )
    metadata = dataset.metadata_dict()
    history = list(metadata.get("xrd_stack_history", []))
    history.append(
        {
            "step": step_value,
            "start": start_value,
            "n_patterns": len(dataset),
        }
    )
    metadata["xrd_stack_history"] = history
    return Dataset(series=stacked, name=dataset.name, metadata=metadata)


@dataclass(frozen=True, slots=True)
class PeakAnnotation:
    """One explicit XRD peak label anchored at a 2theta position."""

    two_theta_deg: float
    text: str
    series_key: str | None = None
    text_offset_points: float = 4.0
    rotation: float = 90.0
    font_size: float | None = None
    color: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "two_theta_deg",
            _finite_float(self.two_theta_deg, name="two_theta_deg"),
        )
        label = str(self.text).strip()
        if not label:
            raise XRDError("peak annotation text must not be empty")
        object.__setattr__(self, "text", label)
        if self.series_key is not None:
            stable_key = str(self.series_key).strip()
            if not stable_key:
                raise XRDError("series_key must not be empty when supplied")
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
                raise XRDError("font_size must be non-negative")
            object.__setattr__(self, "font_size", size)
        if self.color is not None:
            color = str(self.color).strip()
            if not color:
                raise XRDError("color must not be empty when supplied")
            object.__setattr__(self, "color", color)


@dataclass(frozen=True, slots=True)
class XRDReferencePattern:
    """Reference diffraction-stick data independent of an experimental intensity axis."""

    positions_deg: Sequence[float]
    intensities: Sequence[float] | None = None
    label: str = ""
    color: str | None = None
    line_width: float = 0.8

    def __post_init__(self) -> None:
        positions = tuple(
            _finite_float(value, name="reference 2theta")
            for value in self.positions_deg
        )
        if not positions:
            raise XRDError("reference pattern requires at least one 2theta position")
        if any(value < 0 or value > 180 for value in positions):
            raise XRDError("reference 2theta positions must lie between 0 and 180 degrees")
        object.__setattr__(self, "positions_deg", positions)

        if self.intensities is not None:
            intensities = tuple(
                _finite_float(value, name="reference intensity")
                for value in self.intensities
            )
            if len(intensities) != len(positions):
                raise XRDError("reference intensities must match reference positions length")
            if any(value < 0 for value in intensities):
                raise XRDError("reference intensities must be non-negative")
            if max(intensities) <= 0:
                raise XRDError("reference intensities must contain at least one positive value")
            object.__setattr__(self, "intensities", intensities)

        object.__setattr__(self, "label", str(self.label).strip())
        if self.color is not None:
            color = str(self.color).strip()
            if not color:
                raise XRDError("reference color must not be empty when supplied")
            object.__setattr__(self, "color", color)
        width = _finite_float(self.line_width, name="line_width")
        if width <= 0:
            raise XRDError("reference line_width must be greater than zero")
        object.__setattr__(self, "line_width", width)
