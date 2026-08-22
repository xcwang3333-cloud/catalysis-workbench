"""Reusable, non-mutating processing primitives for one-dimensional scientific data."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
from numpy.typing import ArrayLike
from scipy.signal import savgol_filter

from catalysis_workbench.core import Dataset, Series

NormalizationMethod = Literal["max", "max_abs", "minmax", "area"]
AreaMode = Literal["absolute", "net"]


class ProcessingError(ValueError):
    """Raised when an XY processing operation is scientifically or numerically invalid."""


@dataclass(frozen=True, slots=True)
class IntegrationResult:
    """Traceable scalar result from trapezoidal integration of one Series."""

    value: float | complex
    method: str
    absolute: bool
    source_key: str
    source_label: str
    source_sha256: str
    n_points: int
    x_start: float
    x_end: float
    x_min: float
    x_max: float
    x_axis_name: str
    y_axis_name: str
    x_unit: str | None
    y_unit: str | None


def _record(series: Series, operation: str, parameters: Mapping[str, Any]) -> Series:
    metadata = series.metadata_dict()
    history = list(metadata.get("processing_history", []))
    history.append({"operation": operation, "parameters": dict(parameters)})
    metadata["processing_history"] = history
    return Series(
        x=series.x,
        y=series.y,
        label=series.label,
        x_axis=series.x_axis,
        y_axis=series.y_axis,
        metadata=metadata,
        key=series.key,
    )


def _with_data_and_record(
    series: Series,
    *,
    x: ArrayLike | None = None,
    y: ArrayLike | None = None,
    operation: str,
    parameters: Mapping[str, Any],
) -> Series:
    transformed = series.with_data(
        x=series.x if x is None else x,
        y=series.y if y is None else y,
    )
    return _record(transformed, operation, parameters)


def _numeric_scalar(value: Any, *, name: str) -> float | complex:
    array = np.asarray(value)
    if array.ndim != 0 or array.dtype.kind not in "biufc":
        raise TypeError(f"{name} must be a numeric scalar")
    scalar = array.item()
    if not np.isfinite(scalar):
        raise ProcessingError(f"{name} must be finite")
    return scalar


def _real_numeric_scalar(value: Any, *, name: str) -> float:
    scalar = _numeric_scalar(value, name=name)
    if isinstance(scalar, complex):
        if scalar.imag != 0:
            raise ProcessingError(f"{name} must be real-valued")
        scalar = scalar.real
    return float(scalar)


def _require_real_finite_x(series: Series, *, operation: str) -> np.ndarray:
    x = np.asarray(series.x)
    if np.iscomplexobj(x):
        raise ProcessingError(f"{operation} requires a real-valued x axis")
    if np.isnan(x).any() or np.isinf(x).any():
        raise ProcessingError(f"{operation} requires finite x values without NaN")
    return x.astype(np.float64, copy=False)


def _monotonic_direction(x: np.ndarray, *, operation: str) -> int:
    if x.size < 2:
        raise ProcessingError(f"{operation} requires at least two x points")
    delta = np.diff(x)
    if np.all(delta > 0):
        return 1
    if np.all(delta < 0):
        return -1
    raise ProcessingError(
        f"{operation} requires strictly monotonic x values without duplicates"
    )


def _require_uniform_spacing(x: np.ndarray, *, operation: str) -> float:
    _monotonic_direction(x, operation=operation)
    spacing = np.diff(x)
    reference = float(spacing[0])
    tolerance = max(abs(reference) * 1e-6, np.finfo(np.float64).eps * 32)
    if not np.allclose(spacing, reference, rtol=1e-6, atol=tolerance):
        raise ProcessingError(
            f"{operation} requires approximately uniform x spacing; interpolate first"
        )
    return reference


def _require_complete_y(series: Series, *, operation: str) -> np.ndarray:
    y = np.asarray(series.y)
    if np.isnan(y).any():
        raise ProcessingError(
            f"{operation} does not silently discard missing y values; clean them explicitly first"
        )
    return y


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


def _require_baseline_axis_compatibility(series: Series, baseline: Series) -> None:
    checks = (
        ("x-axis name", series.x_axis.name, baseline.x_axis.name),
        ("x-axis unit", series.x_axis.unit, baseline.x_axis.unit),
        ("y-axis name", series.y_axis.name, baseline.y_axis.name),
        ("y-axis unit", series.y_axis.unit, baseline.y_axis.unit),
    )
    for description, source_value, baseline_value in checks:
        if source_value != baseline_value:
            raise ProcessingError(
                "baseline Series is incompatible with source "
                f"{description}: {source_value!r} != {baseline_value!r}"
            )


def crop(
    series: Series,
    *,
    x_min: float | None = None,
    x_max: float | None = None,
    inclusive: bool = True,
) -> Series:
    """Return points inside an explicit x range while preserving their original order."""
    if x_min is None and x_max is None:
        raise ProcessingError("crop requires x_min, x_max, or both")
    if x_min is not None and x_max is not None and x_min > x_max:
        raise ProcessingError("x_min must be less than or equal to x_max")

    x = _require_real_finite_x(series, operation="crop")
    mask = np.ones(x.size, dtype=bool)
    if x_min is not None:
        mask &= x >= x_min if inclusive else x > x_min
    if x_max is not None:
        mask &= x <= x_max if inclusive else x < x_max
    if not mask.any():
        raise ProcessingError("crop selected no points")

    return _with_data_and_record(
        series,
        x=series.x[mask],
        y=series.y[mask],
        operation="crop",
        parameters={"x_min": x_min, "x_max": x_max, "inclusive": inclusive},
    )


def offset(series: Series, value: float | complex) -> Series:
    """Add a finite constant vertical offset to y."""
    numeric_value = _numeric_scalar(value, name="offset value")
    return _with_data_and_record(
        series,
        y=np.asarray(series.y) + numeric_value,
        operation="offset",
        parameters={"value": numeric_value},
    )


def normalize(
    series: Series,
    *,
    method: NormalizationMethod = "max",
    target: float = 1.0,
    area_mode: AreaMode = "absolute",
) -> Series:
    """Normalize y using an explicit, reproducible scaling rule.

    For ``method='area'``, ``area_mode='absolute'`` uses the positive L1-like
    trapezoidal area ``integral(abs(y), x)`` and is the default. ``area_mode='net'``
    uses the magnitude of the signed/complex net integral and can therefore cancel
    across sign changes.
    """
    y = _require_complete_y(series, operation="normalize")
    target_value = _real_numeric_scalar(target, name="normalize target")

    if method == "max":
        if np.iscomplexobj(y):
            raise ProcessingError(
                "normalize(method='max') is undefined for complex y; use 'max_abs'"
            )
        denominator = float(np.max(y))
        if denominator <= 0:
            raise ProcessingError(
                "normalize(method='max') requires a positive maximum; use 'max_abs' "
                "for sign-preserving scaling of non-positive data"
            )
        output = y / denominator * target_value
        parameters: dict[str, Any] = {"method": method, "target": target_value}
    elif method == "max_abs":
        denominator = float(np.max(np.abs(y)))
        if denominator == 0:
            raise ProcessingError("normalize denominator is zero")
        output = y / denominator * target_value
        parameters = {"method": method, "target": target_value}
    elif method == "minmax":
        if np.iscomplexobj(y):
            raise ProcessingError("normalize(method='minmax') is undefined for complex y")
        minimum = float(np.min(y))
        span = float(np.max(y) - minimum)
        if span == 0:
            raise ProcessingError("normalize min-max span is zero")
        output = (y - minimum) / span * target_value
        parameters = {"method": method, "target": target_value}
    elif method == "area":
        x = _require_real_finite_x(series, operation="normalize(method='area')")
        _monotonic_direction(x, operation="normalize(method='area')")
        if area_mode == "absolute":
            denominator = float(abs(np.trapezoid(np.abs(y), x=x)))
        elif area_mode == "net":
            denominator = float(abs(np.trapezoid(y, x=x)))
        else:
            raise ProcessingError(f"Unknown area_mode {area_mode!r}")
        if denominator == 0:
            raise ProcessingError(
                f"normalize area denominator is zero for area_mode={area_mode!r}"
            )
        output = y / denominator * target_value
        parameters = {
            "method": method,
            "target": target_value,
            "area_mode": area_mode,
        }
    else:
        raise ProcessingError(f"Unknown normalization method {method!r}")

    return _with_data_and_record(
        series,
        y=output,
        operation="normalize",
        parameters=parameters,
    )


def savgol(
    series: Series,
    *,
    window_length: int,
    polyorder: int,
    mode: str = "interp",
    cval: float = 0.0,
) -> Series:
    """Smooth uniformly sampled y data with SciPy's Savitzky-Golay filter."""
    x = _require_real_finite_x(series, operation="savgol")
    spacing = _require_uniform_spacing(x, operation="savgol")
    y = _require_complete_y(series, operation="savgol")
    try:
        if np.iscomplexobj(y):
            filtered = savgol_filter(
                np.real(y), window_length, polyorder, mode=mode, cval=cval
            ) + 1j * savgol_filter(
                np.imag(y), window_length, polyorder, mode=mode, cval=cval
            )
        else:
            filtered = savgol_filter(
                y,
                window_length,
                polyorder,
                mode=mode,
                cval=cval,
            )
    except (TypeError, ValueError) as exc:
        raise ProcessingError(str(exc)) from exc

    return _with_data_and_record(
        series,
        y=filtered,
        operation="savgol",
        parameters={
            "window_length": int(window_length),
            "polyorder": int(polyorder),
            "mode": mode,
            "cval": float(cval),
            "x_spacing": spacing,
        },
    )


def interpolate(series: Series, x_new: ArrayLike) -> Series:
    """Linearly interpolate y onto a finite monotonic target grid without extrapolation."""
    x = _require_real_finite_x(series, operation="interpolate")
    direction = _monotonic_direction(x, operation="interpolate")
    y = _require_complete_y(series, operation="interpolate")

    target = np.asarray(x_new)
    if target.ndim != 1 or target.size == 0:
        raise ProcessingError("interpolate x_new must be a non-empty one-dimensional array")
    if np.iscomplexobj(target):
        raise ProcessingError("interpolate x_new must be real-valued")
    try:
        target = target.astype(np.float64, copy=False)
    except (TypeError, ValueError) as exc:
        raise ProcessingError("interpolate x_new must contain numeric values") from exc
    if np.isnan(target).any() or np.isinf(target).any():
        raise ProcessingError("interpolate x_new must contain only finite values")
    if target.size > 1:
        target_direction = _monotonic_direction(target, operation="interpolate target grid")
    else:
        target_direction = 0

    lower = float(np.min(x))
    upper = float(np.max(x))
    if np.any(target < lower) or np.any(target > upper):
        raise ProcessingError("interpolate does not extrapolate beyond the source x range")

    xp = x if direction > 0 else x[::-1]
    fp = y if direction > 0 else y[::-1]
    if np.iscomplexobj(fp):
        output = np.interp(target, xp, np.real(fp)) + 1j * np.interp(
            target,
            xp,
            np.imag(fp),
        )
    else:
        output = np.interp(target, xp, fp)

    return _with_data_and_record(
        series,
        x=target,
        y=output,
        operation="interpolate",
        parameters={
            "method": "linear",
            "n_points": int(target.size),
            "x_min": float(np.min(target)),
            "x_max": float(np.max(target)),
            "target_direction": target_direction,
            "grid_sha256": _array_digest(target),
            "extrapolation": False,
        },
    )


def integrate(series: Series, *, absolute: bool = False) -> IntegrationResult:
    """Integrate y(x) with the trapezoidal rule.

    ``absolute=False`` returns the signed/complex net integral. ``absolute=True``
    returns the positive absolute area ``integral(abs(y), x)`` independent of x order.
    """
    x = _require_real_finite_x(series, operation="integrate")
    _monotonic_direction(x, operation="integrate")
    y = _require_complete_y(series, operation="integrate")
    if absolute:
        value = abs(np.trapezoid(np.abs(y), x=x))
    else:
        value = np.trapezoid(y, x=x)

    if np.iscomplexobj(value):
        result_value: float | complex = complex(value)
    else:
        result_value = float(value)

    return IntegrationResult(
        value=result_value,
        method="trapezoid",
        absolute=absolute,
        source_key=series.key,
        source_label=series.label,
        source_sha256=_series_data_digest(series),
        n_points=series.n_points,
        x_start=float(x[0]),
        x_end=float(x[-1]),
        x_min=float(np.min(x)),
        x_max=float(np.max(x)),
        x_axis_name=series.x_axis.name,
        y_axis_name=series.y_axis.name,
        x_unit=series.x_axis.unit,
        y_unit=series.y_axis.unit,
    )


def subtract_baseline(
    series: Series,
    baseline: Series | ArrayLike | float | complex,
) -> Series:
    """Subtract an explicitly supplied baseline without estimating it."""
    if isinstance(baseline, Series):
        if not np.array_equal(series.x, baseline.x, equal_nan=True):
            raise ProcessingError("baseline Series must use exactly the same x grid")
        _require_baseline_axis_compatibility(series, baseline)
        baseline_values = np.asarray(baseline.y)
        descriptor: dict[str, Any] = {
            "baseline_type": "series",
            "baseline_key": baseline.key,
            "baseline_label": baseline.label,
            "baseline_sha256": _series_data_digest(baseline),
        }
    elif np.isscalar(baseline):
        numeric_baseline = _numeric_scalar(baseline, name="baseline")
        baseline_values = np.asarray(numeric_baseline)
        descriptor = {"baseline_type": "scalar", "value": numeric_baseline}
    else:
        try:
            baseline_values = np.asarray(baseline)
        except (TypeError, ValueError) as exc:
            raise ProcessingError("baseline must be numeric") from exc
        if baseline_values.ndim != 1 or baseline_values.size != series.n_points:
            raise ProcessingError("baseline array must be one-dimensional and match Series length")
        if baseline_values.dtype.kind not in "biufc":
            raise ProcessingError("baseline must contain numeric values")
        if np.isinf(baseline_values).any():
            raise ProcessingError("baseline must not contain +/-inf")
        descriptor = {
            "baseline_type": "array",
            "n_points": int(baseline_values.size),
            "baseline_sha256": _array_digest(np.ascontiguousarray(baseline_values)),
        }

    output = np.asarray(series.y) - baseline_values
    return _with_data_and_record(
        series,
        y=output,
        operation="subtract_baseline",
        parameters=descriptor,
    )


def map_dataset(
    dataset: Dataset,
    transform: Callable[..., Series],
    /,
    *args: Any,
    **kwargs: Any,
) -> Dataset:
    """Apply one Series->Series transform to every item in a Dataset."""
    transformed: list[Series] = []
    for item in dataset:
        result = transform(item, *args, **kwargs)
        if not isinstance(result, Series):
            raise TypeError("map_dataset transform must return Series")
        transformed.append(result)
    return Dataset(
        series=tuple(transformed),
        name=dataset.name,
        metadata=dataset.metadata_dict(),
    )
