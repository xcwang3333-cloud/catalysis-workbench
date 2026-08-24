"""Explicit XPS binding-energy preparation and background calculations."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, field
from math import isfinite
from types import MappingProxyType
from typing import Any, Literal, TypeAlias

import numpy as np
from numpy.typing import ArrayLike, NDArray

from catalysis_workbench.core import Axis, Series

XPSDirection: TypeAlias = Literal["ascending", "descending"]
XPSBackgroundMethod: TypeAlias = Literal["linear", "shirley"]
ScalarMetadata: TypeAlias = str | int | float | bool | None

_BINDING_ENERGY_NAMES = {"bindingenergy", "bindinge", "be"}
_INTENSITY_NAMES = {"intensity"}
_EV_UNITS = {"ev", "electronvolt", "electronvolts"}


class XPSError(ValueError):
    """Raised when XPS data or a requested XPS operation is invalid."""


def _finite_float(value: Any, *, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a real numeric value") from exc
    if not isfinite(result):
        raise XPSError(f"{name} must be finite")
    return result


def _semantic_token(value: str) -> str:
    token = str(value).strip().casefold()
    return "".join(character for character in token if character.isalnum())


def _canonical_ev_unit(unit: str | None) -> str:
    if unit is None or not str(unit).strip():
        raise XPSError("XPS binding energy requires an explicit eV unit")
    if _semantic_token(str(unit)) not in _EV_UNITS:
        raise XPSError(f"unsupported XPS binding-energy unit {unit!r}; use eV")
    return "eV"


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


def _immutable_float_array(values: ArrayLike, *, name: str) -> NDArray[np.float64]:
    source = np.asarray(values)
    if source.ndim != 1:
        raise XPSError(f"{name} must be one-dimensional; got shape {source.shape}")
    if source.size == 0:
        raise XPSError(f"{name} must not be empty")
    if source.dtype.kind not in "biuf":
        raise TypeError(f"{name} must contain real numeric values")
    normalized = np.ascontiguousarray(source, dtype=np.float64)
    if not np.isfinite(normalized).all():
        raise XPSError(f"{name} must contain only finite values")
    frozen = np.frombuffer(normalized.tobytes(order="C"), dtype=np.float64)
    frozen.setflags(write=False)
    return frozen


def _freeze_scalar_metadata(
    metadata: Mapping[str, ScalarMetadata] | None,
) -> Mapping[str, ScalarMetadata]:
    if metadata is None:
        return MappingProxyType({})
    frozen: dict[str, ScalarMetadata] = {}
    for raw_key, value in metadata.items():
        key = str(raw_key).strip()
        if not key:
            raise XPSError("metadata keys must not be empty")
        if value is not None and not isinstance(value, (str, int, float, bool)):
            raise TypeError("metadata values must be deterministic scalar values")
        if isinstance(value, float) and not np.isfinite(value):
            raise XPSError("metadata float values must be finite")
        frozen[key] = value
    return MappingProxyType(dict(sorted(frozen.items())))


def _direction(x: np.ndarray) -> XPSDirection:
    if x.size < 2:
        raise XPSError("XPS spectra require at least two binding-energy points")
    delta = np.diff(x)
    if np.all(delta > 0):
        return "ascending"
    if np.all(delta < 0):
        return "descending"
    raise XPSError("XPS binding-energy values must be strictly monotonic without duplicates")


def validate_xps_series(series: Series) -> None:
    """Validate XPS axis semantics and numeric storage without modifying the source."""
    if not isinstance(series, Series):
        raise TypeError("series must be a Series")
    if _semantic_token(series.x_axis.name) not in _BINDING_ENERGY_NAMES:
        raise XPSError("XPS requires x_axis.name='binding_energy'")
    _canonical_ev_unit(series.x_axis.unit)
    if _semantic_token(series.y_axis.name) not in _INTENSITY_NAMES:
        raise XPSError("XPS requires y_axis.name='intensity'")

    x = np.asarray(series.x)
    y = np.asarray(series.y)
    if np.iscomplexobj(x) or np.iscomplexobj(y):
        raise XPSError("XPS binding-energy and intensity values must be real")
    x_real = x.astype(np.float64, copy=False)
    if not np.isfinite(x_real).all():
        raise XPSError("XPS binding-energy values must be finite")
    _direction(x_real)
    if np.isinf(y.astype(np.float64, copy=False)).any():
        raise XPSError("XPS intensity values must not contain +/-inf")


def _canonicalize_xps_series(series: Series) -> Series:
    validate_xps_series(series)
    return Series(
        x=series.x,
        y=series.y,
        key=series.key,
        label=series.label,
        x_axis=Axis(
            "binding_energy",
            unit="eV",
            label=series.x_axis.label or "Binding energy",
            metadata=series.x_axis.metadata_dict(),
        ),
        y_axis=Axis(
            "intensity",
            unit=series.y_axis.unit,
            label=series.y_axis.label or "Intensity",
            metadata=series.y_axis.metadata_dict(),
        ),
        metadata=series.metadata_dict(),
    )


def _with_history(
    series: Series,
    *,
    x: ArrayLike | None = None,
    y: ArrayLike | None = None,
    operation: str,
    parameters: Mapping[str, ScalarMetadata],
    x_axis: Axis | None = None,
) -> Series:
    metadata = series.metadata_dict()
    history = list(metadata.get("processing_history", []))
    history.append({"operation": operation, "parameters": dict(parameters)})
    metadata["processing_history"] = history
    return Series(
        x=series.x if x is None else x,
        y=series.y if y is None else y,
        key=series.key,
        label=series.label,
        x_axis=series.x_axis if x_axis is None else x_axis,
        y_axis=series.y_axis,
        metadata=metadata,
    )


def _has_energy_shift(series: Series) -> bool:
    for item in series.metadata.get("processing_history", ()):
        if isinstance(item, Mapping) and item.get("operation") == "xps.energy_shift":
            return True
    return False


def shift_xps_binding_energy(
    series: Series,
    shift_ev: float,
    *,
    reference: str | None = None,
    rationale: str | None = None,
) -> Series:
    """Apply one explicit additive binding-energy shift while preserving intensity."""
    canonical = _canonicalize_xps_series(series)
    if _has_energy_shift(canonical):
        raise XPSError("XPS binding energy has already been explicitly corrected")
    shift = _finite_float(shift_ev, name="shift_ev")
    reference_text = None if reference is None else str(reference).strip() or None
    rationale_text = None if rationale is None else str(rationale).strip() or None

    axis_metadata = canonical.x_axis.metadata_dict()
    axis_metadata["xps_energy_shift_ev"] = shift
    if reference_text is not None:
        axis_metadata["xps_energy_reference"] = reference_text
    if rationale_text is not None:
        axis_metadata["xps_energy_correction_rationale"] = rationale_text
    corrected_axis = Axis(
        "binding_energy",
        unit="eV",
        label=canonical.x_axis.label or "Binding energy",
        metadata=axis_metadata,
    )
    parameters: dict[str, ScalarMetadata] = {"shift_ev": shift}
    if reference_text is not None:
        parameters["reference"] = reference_text
    if rationale_text is not None:
        parameters["rationale"] = rationale_text
    return _with_history(
        canonical,
        x=np.asarray(canonical.x, dtype=np.float64) + shift,
        operation="xps.energy_shift",
        parameters=parameters,
        x_axis=corrected_axis,
    )


def prepare_xps_region(
    series: Series,
    x_min_ev: float,
    x_max_ev: float,
    *,
    minimum_points: int = 2,
) -> Series:
    """Select measured XPS points inside an explicit binding-energy region."""
    canonical = _canonicalize_xps_series(series)
    low = _finite_float(x_min_ev, name="x_min_ev")
    high = _finite_float(x_max_ev, name="x_max_ev")
    if low > high:
        raise XPSError("x_min_ev must be <= x_max_ev")
    if isinstance(minimum_points, bool) or not isinstance(minimum_points, int):
        raise TypeError("minimum_points must be an integer")
    if minimum_points < 2:
        raise XPSError("minimum_points must be >= 2")

    x = np.asarray(canonical.x, dtype=np.float64)
    y = np.asarray(canonical.y, dtype=np.float64)
    mask = (x >= low) & (x <= high)
    count = int(np.count_nonzero(mask))
    if count < minimum_points:
        raise XPSError(
            f"XPS region contains {count} measured points; at least {minimum_points} are required"
        )
    if not np.isfinite(y[mask]).all():
        raise XPSError("selected XPS region contains missing/non-finite intensity values")
    return _with_history(
        canonical,
        x=x[mask],
        y=y[mask],
        operation="xps.prepare_region",
        parameters={
            "x_min_ev": low,
            "x_max_ev": high,
            "minimum_points": minimum_points,
        },
    )


@dataclass(frozen=True, slots=True)
class XPSBackgroundResult:
    """Immutable, traceable XPS background on one measured binding-energy grid."""

    method: XPSBackgroundMethod
    source_key: str
    source_label: str
    source_sha256: str
    source_direction: XPSDirection
    x_unit: str
    y_unit: str | None
    x: NDArray[np.float64] = field(repr=False)
    observed_y: NDArray[np.float64] = field(repr=False)
    background_y: NDArray[np.float64] = field(repr=False)
    low_energy_ev: float
    high_energy_ev: float
    low_endpoint_intensity: float
    high_endpoint_intensity: float
    converged: bool = True
    iterations: int = 0
    relative_tolerance: float | None = None
    absolute_tolerance: float | None = None
    max_iterations: int | None = None
    settings: Mapping[str, ScalarMetadata] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.method not in ("linear", "shirley"):
            raise XPSError(f"unsupported XPS background method {self.method!r}")
        x = _immutable_float_array(self.x, name="background x")
        observed = _immutable_float_array(self.observed_y, name="background observed_y")
        background = _immutable_float_array(self.background_y, name="background_y")
        if x.size != observed.size or x.size != background.size:
            raise XPSError("XPS background arrays must have the same length")
        object.__setattr__(self, "x", x)
        object.__setattr__(self, "observed_y", observed)
        object.__setattr__(self, "background_y", background)
        object.__setattr__(self, "settings", _freeze_scalar_metadata(self.settings))


def _complete_background_input(series: Series) -> tuple[Series, np.ndarray, np.ndarray, XPSDirection]:
    canonical = _canonicalize_xps_series(series)
    x = np.asarray(canonical.x, dtype=np.float64)
    y = np.asarray(canonical.y, dtype=np.float64)
    if not np.isfinite(y).all():
        raise XPSError("XPS background calculation requires finite intensity values")
    if x.size < 2:
        raise XPSError("XPS background calculation requires at least two measured points")
    return canonical, x, y, _direction(x)


def _canonical_increasing(
    x: np.ndarray,
    y: np.ndarray,
    direction: XPSDirection,
) -> tuple[np.ndarray, np.ndarray]:
    if direction == "ascending":
        return x, y
    return x[::-1], y[::-1]


def _restore_order(values: np.ndarray, direction: XPSDirection) -> np.ndarray:
    return values if direction == "ascending" else values[::-1]


def linear_xps_background(series: Series) -> XPSBackgroundResult:
    """Return the line through measured low/high-energy endpoint intensities."""
    canonical, x, y, direction = _complete_background_input(series)
    x_inc, y_inc = _canonical_increasing(x, y, direction)
    low_x = float(x_inc[0])
    high_x = float(x_inc[-1])
    low_y = float(y_inc[0])
    high_y = float(y_inc[-1])
    span = high_x - low_x
    if span <= 0:
        raise XPSError("linear XPS background requires distinct binding-energy endpoints")
    background_inc = low_y + (high_y - low_y) * (x_inc - low_x) / span
    background_inc[0] = low_y
    background_inc[-1] = high_y
    background = _restore_order(background_inc, direction)
    return XPSBackgroundResult(
        method="linear",
        source_key=canonical.key,
        source_label=canonical.label,
        source_sha256=_series_data_digest(canonical),
        source_direction=direction,
        x_unit="eV",
        y_unit=canonical.y_axis.unit,
        x=x,
        observed_y=y,
        background_y=background,
        low_energy_ev=low_x,
        high_energy_ev=high_x,
        low_endpoint_intensity=low_y,
        high_endpoint_intensity=high_y,
        settings={"endpoint_policy": "measured_numeric_min_max"},
    )


def _integral_from_each_point_to_right(x: np.ndarray, values: np.ndarray) -> np.ndarray:
    increments = 0.5 * (values[:-1] + values[1:]) * np.diff(x)
    cumulative = np.empty_like(values, dtype=np.float64)
    cumulative[-1] = 0.0
    cumulative[:-1] = np.cumsum(increments[::-1])[::-1]
    return cumulative


def shirley_xps_background(
    series: Series,
    *,
    relative_tolerance: float = 1e-8,
    absolute_tolerance: float = 1e-10,
    max_iterations: int = 200,
) -> XPSBackgroundResult:
    """Solve the explicit Shirley fixed-point integral equation on the measured grid."""
    canonical, x, y, direction = _complete_background_input(series)
    if x.size < 3:
        raise XPSError("Shirley XPS background requires at least three measured points")
    rtol = _finite_float(relative_tolerance, name="relative_tolerance")
    atol = _finite_float(absolute_tolerance, name="absolute_tolerance")
    if rtol <= 0 or atol <= 0:
        raise XPSError("Shirley convergence tolerances must be positive")
    if isinstance(max_iterations, bool) or not isinstance(max_iterations, int):
        raise TypeError("max_iterations must be an integer")
    if max_iterations < 1:
        raise XPSError("max_iterations must be >= 1")

    x_inc, y_inc = _canonical_increasing(x, y, direction)
    low_x = float(x_inc[0])
    high_x = float(x_inc[-1])
    low_y = float(y_inc[0])
    high_y = float(y_inc[-1])
    span = high_x - low_x
    if span <= 0:
        raise XPSError("Shirley XPS background requires distinct energy endpoints")

    background = low_y + (high_y - low_y) * (x_inc - low_x) / span
    background[0] = low_y
    background[-1] = high_y
    scale = max(1.0, float(np.max(np.abs(y_inc))))
    denominator_floor = np.finfo(np.float64).eps * scale * max(1.0, span) * x_inc.size

    converged = False
    iterations = 0
    for iteration in range(1, max_iterations + 1):
        excess = y_inc - background
        cumulative = _integral_from_each_point_to_right(x_inc, excess)
        denominator = float(cumulative[0])
        if not np.isfinite(denominator) or abs(denominator) <= denominator_floor:
            raise XPSError(
                "Shirley background integral is numerically zero/invalid; "
                "the selected region does not support this background"
            )
        updated = high_y + (low_y - high_y) * cumulative / denominator
        updated[0] = low_y
        updated[-1] = high_y
        if not np.isfinite(updated).all():
            raise XPSError("Shirley background iteration produced non-finite values")
        delta = float(np.max(np.abs(updated - background)))
        threshold = atol + rtol * max(1.0, float(np.max(np.abs(updated))))
        background = updated
        iterations = iteration
        if delta <= threshold:
            converged = True
            break

    if not converged:
        raise XPSError(
            f"Shirley background did not converge within {max_iterations} iterations"
        )

    restored = _restore_order(background, direction)
    return XPSBackgroundResult(
        method="shirley",
        source_key=canonical.key,
        source_label=canonical.label,
        source_sha256=_series_data_digest(canonical),
        source_direction=direction,
        x_unit="eV",
        y_unit=canonical.y_axis.unit,
        x=x,
        observed_y=y,
        background_y=restored,
        low_energy_ev=low_x,
        high_energy_ev=high_x,
        low_endpoint_intensity=low_y,
        high_endpoint_intensity=high_y,
        converged=True,
        iterations=iterations,
        relative_tolerance=rtol,
        absolute_tolerance=atol,
        max_iterations=max_iterations,
        settings={
            "equation": "shirley_fixed_point_integral",
            "initial_background": "linear_measured_endpoints",
            "integration": "measured_grid_trapezoid",
            "endpoint_policy": "measured_numeric_min_max",
        },
    )


__all__ = [
    "XPSBackgroundMethod",
    "XPSBackgroundResult",
    "XPSDirection",
    "XPSError",
    "linear_xps_background",
    "prepare_xps_region",
    "shift_xps_binding_energy",
    "shirley_xps_background",
    "validate_xps_series",
]
