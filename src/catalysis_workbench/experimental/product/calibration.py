"""Explicit linear product calibration and inverse sample quantification."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from math import isfinite, sqrt
from numbers import Real
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.stats import linregress

from catalysis_workbench.core import Series

CalibrationInterceptPolicy = Literal["free", "zero"]


class ProductCalibrationError(ValueError):
    """Raised when product calibration or quantification is scientifically invalid."""


def _finite_float(value: object, *, name: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ProductCalibrationError(f"{name} must be a finite real numeric value")
    numeric = float(value)
    if not isfinite(numeric):
        raise ProductCalibrationError(f"{name} must be a finite real numeric value")
    return numeric


def _positive_float(value: object, *, name: str) -> float:
    numeric = _finite_float(value, name=name)
    if numeric <= 0.0:
        raise ProductCalibrationError(f"{name} must be greater than zero")
    return numeric


def _immutable_float_array(
    values: object,
    *,
    name: str,
    one_dimensional: bool = False,
) -> NDArray[np.float64]:
    try:
        source = np.asarray(values)
    except (TypeError, ValueError) as exc:
        raise ProductCalibrationError(f"{name} must contain real numeric values") from exc
    if one_dimensional and source.ndim != 1:
        raise ProductCalibrationError(f"{name} must be one-dimensional")
    if source.size == 0:
        raise ProductCalibrationError(f"{name} must not be empty")
    if np.iscomplexobj(source) or source.dtype.kind not in "iuf":
        raise ProductCalibrationError(f"{name} must contain real numeric values")
    normalized = np.array(source, dtype=np.float64, copy=True, order="C")
    if not np.isfinite(normalized).all():
        raise ProductCalibrationError(f"{name} must contain only finite values")
    buffer = normalized.tobytes(order="C")
    result = np.frombuffer(buffer, dtype=np.float64, count=normalized.size)
    result = result.reshape(normalized.shape)
    result.setflags(write=False)
    return result


def _immutable_bool_array(values: object, *, name: str) -> NDArray[np.bool_]:
    source = np.asarray(values)
    if source.size == 0:
        raise ProductCalibrationError(f"{name} must not be empty")
    if source.dtype.kind != "b":
        raise ProductCalibrationError(f"{name} must contain boolean values")
    normalized = np.ascontiguousarray(source, dtype=np.bool_)
    buffer = normalized.tobytes(order="C")
    result = np.frombuffer(buffer, dtype=np.bool_, count=normalized.size)
    result = result.reshape(normalized.shape)
    result.setflags(write=False)
    return result


def _unit(value: object, *, name: str) -> str:
    if not isinstance(value, str):
        raise ProductCalibrationError(f"{name} must be an explicit unit string")
    unit = value.strip()
    if not unit:
        raise ProductCalibrationError(f"{name} must be an explicit non-empty unit")
    return unit


def _axis_name(value: object, *, expected: str, name: str) -> str:
    if not isinstance(value, str) or value.strip() != expected:
        raise ProductCalibrationError(f"{name} must be {expected!r}")
    return expected


def _optional_label(value: object | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ProductCalibrationError("axis label must be a string or None")
    label = value.strip()
    return label or None


def _array_digest(values: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(values)
    digest = hashlib.sha256()
    digest.update(str(contiguous.dtype).encode("ascii"))
    digest.update(str(contiguous.shape).encode("ascii"))
    digest.update(contiguous.tobytes(order="C"))
    return digest.hexdigest()


def _source_digest(
    quantity: np.ndarray,
    response: np.ndarray,
    *,
    x_axis_name: str,
    x_unit: str,
    y_axis_name: str,
    y_unit: str,
) -> str:
    digest = hashlib.sha256()
    for token in (
        x_axis_name,
        x_unit,
        y_axis_name,
        y_unit,
        _array_digest(quantity),
        _array_digest(response),
    ):
        digest.update(token.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _series_source_digest(series: Series) -> str:
    return _source_digest(
        np.asarray(series.x, dtype=np.float64),
        np.asarray(series.y, dtype=np.float64),
        x_axis_name=series.x_axis.name,
        x_unit=str(series.x_axis.unit),
        y_axis_name=series.y_axis.name,
        y_unit=str(series.y_axis.unit),
    )


def _same_float(actual: float, expected: float) -> bool:
    return bool(np.isclose(actual, expected, rtol=1.0e-11, atol=1.0e-13))


def _same_optional(actual: float | None, expected: float | None) -> bool:
    if actual is None or expected is None:
        return actual is None and expected is None
    return _same_float(actual, expected)


def _centered_r_squared(observed: np.ndarray, residual: np.ndarray) -> float | None:
    centered = observed - float(np.mean(observed))
    total = float(np.dot(centered, centered))
    if total == 0.0:
        return None
    error = float(np.dot(residual, residual))
    value = 1.0 - error / total
    return value if isfinite(value) else None


def _linear_fit(
    quantity: np.ndarray,
    response: np.ndarray,
    *,
    intercept_policy: CalibrationInterceptPolicy,
) -> tuple[float, float, NDArray[np.float64], float | None, float | None, float | None]:
    if intercept_policy == "free":
        regression = linregress(quantity, response)
        slope = float(regression.slope)
        intercept = float(regression.intercept)
        slope_stderr = float(regression.stderr)
        intercept_stderr = float(regression.intercept_stderr)
    elif intercept_policy == "zero":
        denominator = float(np.dot(quantity, quantity))
        if denominator <= 0.0:
            raise ProductCalibrationError(
                "zero-intercept calibration requires at least one positive quantity"
            )
        slope = float(np.dot(quantity, response) / denominator)
        intercept = 0.0
        residual = response - slope * quantity
        degrees_of_freedom = quantity.size - 1
        variance = float(np.dot(residual, residual)) / degrees_of_freedom
        slope_stderr = sqrt(max(variance, 0.0) / denominator)
        intercept_stderr = None
    else:
        raise ProductCalibrationError("intercept_policy must be 'free' or 'zero'")

    if not isfinite(slope) or not isfinite(intercept):
        raise ProductCalibrationError("linear calibration produced non-finite coefficients")
    best_fit = intercept + slope * quantity
    residual = response - best_fit
    r_squared = _centered_r_squared(response, residual)
    if slope_stderr is not None and not isfinite(slope_stderr):
        slope_stderr = None
    if intercept_stderr is not None and not isfinite(intercept_stderr):
        intercept_stderr = None
    return slope, intercept, best_fit, r_squared, slope_stderr, intercept_stderr


@dataclass(frozen=True, slots=True)
class CalibrationRange:
    """Inclusive numerical range selecting measured calibration standards."""

    low: float
    high: float

    def __post_init__(self) -> None:
        low = _finite_float(self.low, name="CalibrationRange.low")
        high = _finite_float(self.high, name="CalibrationRange.high")
        if low < 0.0:
            raise ProductCalibrationError("CalibrationRange.low must be non-negative")
        if high <= low:
            raise ProductCalibrationError("CalibrationRange.high must be greater than low")
        object.__setattr__(self, "low", low)
        object.__setattr__(self, "high", high)


@dataclass(frozen=True, slots=True, eq=False)
class CalibrationFitResult:
    """Immutable reviewed state for one explicit linear calibration fit."""

    source_key: str
    source_label: str
    source_sha256: str
    x_axis_name: str
    x_unit: str
    x_axis_label: str | None
    y_axis_name: str
    y_unit: str
    y_axis_label: str | None
    source_quantity: ArrayLike
    source_response: ArrayLike
    calibration_range: CalibrationRange | None
    source_indices: tuple[int, ...]
    quantity: ArrayLike
    response: ArrayLike
    intercept_policy: CalibrationInterceptPolicy
    slope: float
    intercept: float
    best_fit_response: ArrayLike
    residual: ArrayLike
    r_squared: float | None
    slope_stderr: float | None
    intercept_stderr: float | None
    fit_line_quantity: ArrayLike
    fit_line_response: ArrayLike

    def __post_init__(self) -> None:
        x_axis_name = _axis_name(
            self.x_axis_name,
            expected="calibration_quantity",
            name="x_axis_name",
        )
        y_axis_name = _axis_name(
            self.y_axis_name,
            expected="response",
            name="y_axis_name",
        )
        x_unit = _unit(self.x_unit, name="x_unit")
        y_unit = _unit(self.y_unit, name="y_unit")
        x_axis_label = _optional_label(self.x_axis_label)
        y_axis_label = _optional_label(self.y_axis_label)
        source_quantity = _immutable_float_array(
            self.source_quantity,
            name="source_quantity",
            one_dimensional=True,
        )
        source_response = _immutable_float_array(
            self.source_response,
            name="source_response",
            one_dimensional=True,
        )
        if source_quantity.size != source_response.size:
            raise ProductCalibrationError(
                "source calibration quantity/response arrays must have matching lengths"
            )
        if source_quantity.size < 3:
            raise ProductCalibrationError(
                "calibration requires at least three standard observations"
            )
        if np.any(source_quantity < 0.0):
            raise ProductCalibrationError("calibration quantities must be non-negative")

        source_sha = str(self.source_sha256).strip().casefold()
        expected_source_sha = _source_digest(
            source_quantity,
            source_response,
            x_axis_name=x_axis_name,
            x_unit=x_unit,
            y_axis_name=y_axis_name,
            y_unit=y_unit,
        )
        if source_sha != expected_source_sha:
            raise ProductCalibrationError(
                "source_sha256 contradicts retained calibration data/axis semantics"
            )

        indices = tuple(int(index) for index in self.source_indices)
        if any(index < 0 or index >= source_quantity.size for index in indices):
            raise ProductCalibrationError("calibration source_indices are out of range")
        if len(indices) != len(set(indices)) or tuple(sorted(indices)) != indices:
            raise ProductCalibrationError(
                "calibration source_indices must be unique increasing source positions"
            )

        if self.calibration_range is not None and not isinstance(
            self.calibration_range, CalibrationRange
        ):
            raise TypeError("calibration_range must be a CalibrationRange or None")
        if self.calibration_range is None:
            expected_indices = tuple(range(source_quantity.size))
        else:
            mask = (
                (source_quantity >= self.calibration_range.low)
                & (source_quantity <= self.calibration_range.high)
            )
            expected_indices = tuple(int(index) for index in np.flatnonzero(mask))
        if indices != expected_indices:
            raise ProductCalibrationError(
                "source_indices contradict the declared calibration range/source data"
            )
        if len(indices) < 3:
            raise ProductCalibrationError(
                "selected calibration range requires at least three measured standards"
            )

        quantity = _immutable_float_array(
            self.quantity,
            name="quantity",
            one_dimensional=True,
        )
        response = _immutable_float_array(
            self.response,
            name="response",
            one_dimensional=True,
        )
        expected_quantity = source_quantity[np.asarray(indices, dtype=int)]
        expected_response = source_response[np.asarray(indices, dtype=int)]
        if not np.array_equal(quantity, expected_quantity):
            raise ProductCalibrationError(
                "retained calibration quantity contradicts source_indices/source data"
            )
        if not np.array_equal(response, expected_response):
            raise ProductCalibrationError(
                "retained calibration response contradicts source_indices/source data"
            )
        if np.unique(quantity).size < 2:
            raise ProductCalibrationError(
                "selected calibration standards require at least two distinct quantities"
            )

        if self.intercept_policy not in {"free", "zero"}:
            raise ProductCalibrationError("intercept_policy must be 'free' or 'zero'")
        (
            expected_slope,
            expected_intercept,
            expected_best_fit,
            expected_r_squared,
            expected_slope_stderr,
            expected_intercept_stderr,
        ) = _linear_fit(
            quantity,
            response,
            intercept_policy=self.intercept_policy,
        )
        slope = _finite_float(self.slope, name="slope")
        intercept = _finite_float(self.intercept, name="intercept")
        if not _same_float(slope, expected_slope):
            raise ProductCalibrationError(
                "retained slope contradicts exact calibration regression"
            )
        if not _same_float(intercept, expected_intercept):
            raise ProductCalibrationError(
                "retained intercept contradicts exact calibration regression"
            )

        best_fit = _immutable_float_array(
            self.best_fit_response,
            name="best_fit_response",
            one_dimensional=True,
        )
        residual = _immutable_float_array(
            self.residual,
            name="residual",
            one_dimensional=True,
        )
        if not np.allclose(best_fit, expected_best_fit, rtol=1e-12, atol=1e-14):
            raise ProductCalibrationError(
                "retained best-fit response contradicts exact calibration regression"
            )
        expected_residual = response - expected_best_fit
        if not np.allclose(residual, expected_residual, rtol=1e-12, atol=1e-14):
            raise ProductCalibrationError(
                "retained residual contradicts observed - best_fit"
            )
        if not _same_optional(self.r_squared, expected_r_squared):
            raise ProductCalibrationError("retained R² contradicts exact calibration state")
        if not _same_optional(self.slope_stderr, expected_slope_stderr):
            raise ProductCalibrationError(
                "retained slope_stderr contradicts exact calibration state"
            )
        if not _same_optional(self.intercept_stderr, expected_intercept_stderr):
            raise ProductCalibrationError(
                "retained intercept_stderr contradicts exact calibration state"
            )

        fit_line_quantity = _immutable_float_array(
            self.fit_line_quantity,
            name="fit_line_quantity",
            one_dimensional=True,
        )
        fit_line_response = _immutable_float_array(
            self.fit_line_response,
            name="fit_line_response",
            one_dimensional=True,
        )
        expected_line_quantity = np.array(
            [float(np.min(quantity)), float(np.max(quantity))],
            dtype=np.float64,
        )
        expected_line_response = expected_intercept + expected_slope * expected_line_quantity
        if fit_line_quantity.size != 2 or not np.array_equal(
            fit_line_quantity, expected_line_quantity
        ):
            raise ProductCalibrationError(
                "retained fit-line quantity must span exact selected min/max"
            )
        if fit_line_response.size != 2 or not np.allclose(
            fit_line_response, expected_line_response, rtol=1e-12, atol=1e-14
        ):
            raise ProductCalibrationError(
                "retained fit-line response contradicts calibration coefficients"
            )

        object.__setattr__(self, "source_key", str(self.source_key))
        object.__setattr__(self, "source_label", str(self.source_label))
        object.__setattr__(self, "source_sha256", expected_source_sha)
        object.__setattr__(self, "x_axis_name", x_axis_name)
        object.__setattr__(self, "x_unit", x_unit)
        object.__setattr__(self, "x_axis_label", x_axis_label)
        object.__setattr__(self, "y_axis_name", y_axis_name)
        object.__setattr__(self, "y_unit", y_unit)
        object.__setattr__(self, "y_axis_label", y_axis_label)
        object.__setattr__(self, "source_quantity", source_quantity)
        object.__setattr__(self, "source_response", source_response)
        object.__setattr__(self, "source_indices", indices)
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(self, "response", response)
        object.__setattr__(self, "slope", expected_slope)
        object.__setattr__(self, "intercept", expected_intercept)
        object.__setattr__(self, "best_fit_response", best_fit)
        object.__setattr__(self, "residual", residual)
        object.__setattr__(self, "r_squared", expected_r_squared)
        object.__setattr__(self, "slope_stderr", expected_slope_stderr)
        object.__setattr__(self, "intercept_stderr", expected_intercept_stderr)
        object.__setattr__(self, "fit_line_quantity", fit_line_quantity)
        object.__setattr__(self, "fit_line_response", fit_line_response)

    @property
    def n_points(self) -> int:
        return len(self.source_indices)

    @property
    def n_varying_parameters(self) -> int:
        return 2 if self.intercept_policy == "free" else 1

    @property
    def quantity_min(self) -> float:
        return float(np.min(self.quantity))

    @property
    def quantity_max(self) -> float:
        return float(np.max(self.quantity))


def _validate_calibration_series(series: Series) -> tuple[np.ndarray, np.ndarray]:
    if not isinstance(series, Series):
        raise TypeError("series must be a Series")
    if series.x_axis.name != "calibration_quantity":
        raise ProductCalibrationError(
            "calibration x axis must have semantic name 'calibration_quantity'"
        )
    if series.y_axis.name != "response":
        raise ProductCalibrationError("calibration y axis must have semantic name 'response'")
    _unit(series.x_axis.unit, name="calibration quantity unit")
    _unit(series.y_axis.unit, name="calibration response unit")
    quantity = _immutable_float_array(
        series.x,
        name="calibration quantity",
        one_dimensional=True,
    )
    response = _immutable_float_array(
        series.y,
        name="calibration response",
        one_dimensional=True,
    )
    if quantity.size < 3:
        raise ProductCalibrationError(
            "calibration requires at least three standard observations"
        )
    if np.any(quantity < 0.0):
        raise ProductCalibrationError("calibration quantities must be non-negative")
    if np.unique(quantity).size < 2:
        raise ProductCalibrationError(
            "calibration requires at least two distinct standard quantities"
        )
    history = series.metadata.get("processing_history", ())
    if history not in (None, (), []):
        raise ProductCalibrationError(
            "product calibration requires direct standard-response state; "
            "processing_history transformations are not accepted"
        )
    return quantity, response


def fit_calibration(
    series: Series,
    *,
    calibration_range: CalibrationRange | None = None,
    intercept_policy: CalibrationInterceptPolicy = "free",
) -> CalibrationFitResult:
    """Fit one explicit linear calibration without hidden selection or preprocessing."""
    quantity_all, response_all = _validate_calibration_series(series)
    if calibration_range is not None and not isinstance(calibration_range, CalibrationRange):
        raise TypeError("calibration_range must be a CalibrationRange or None")
    if calibration_range is None:
        indices_array = np.arange(quantity_all.size, dtype=int)
    else:
        indices_array = np.flatnonzero(
            (quantity_all >= calibration_range.low)
            & (quantity_all <= calibration_range.high)
        )
    if indices_array.size < 3:
        raise ProductCalibrationError(
            "selected calibration range requires at least three measured standards"
        )
    quantity = quantity_all[indices_array]
    response = response_all[indices_array]
    if np.unique(quantity).size < 2:
        raise ProductCalibrationError(
            "selected calibration standards require at least two distinct quantities"
        )
    (
        slope,
        intercept,
        best_fit,
        r_squared,
        slope_stderr,
        intercept_stderr,
    ) = _linear_fit(quantity, response, intercept_policy=intercept_policy)
    fit_line_quantity = np.array(
        [float(np.min(quantity)), float(np.max(quantity))],
        dtype=np.float64,
    )
    fit_line_response = intercept + slope * fit_line_quantity
    return CalibrationFitResult(
        source_key=series.key,
        source_label=series.label,
        source_sha256=_series_source_digest(series),
        x_axis_name=series.x_axis.name,
        x_unit=str(series.x_axis.unit),
        x_axis_label=series.x_axis.label,
        y_axis_name=series.y_axis.name,
        y_unit=str(series.y_axis.unit),
        y_axis_label=series.y_axis.label,
        source_quantity=quantity_all,
        source_response=response_all,
        calibration_range=calibration_range,
        source_indices=tuple(int(index) for index in indices_array),
        quantity=quantity,
        response=response,
        intercept_policy=intercept_policy,
        slope=slope,
        intercept=intercept,
        best_fit_response=best_fit,
        residual=response - best_fit,
        r_squared=r_squared,
        slope_stderr=slope_stderr,
        intercept_stderr=intercept_stderr,
        fit_line_quantity=fit_line_quantity,
        fit_line_response=fit_line_response,
    )


@dataclass(frozen=True, slots=True)
class QuantificationFactor:
    """One explicit positive dimensionless multiplier applied after calibration inversion."""

    key: str
    value: float

    def __post_init__(self) -> None:
        if not isinstance(self.key, str) or not self.key.strip():
            raise ProductCalibrationError("QuantificationFactor.key must not be empty")
        object.__setattr__(self, "key", self.key.strip())
        object.__setattr__(
            self,
            "value",
            _positive_float(self.value, name=f"factor {self.key!r}"),
        )


@dataclass(frozen=True, slots=True, eq=False)
class QuantificationResult:
    """Immutable inverse-calibration result for explicit analytical response values."""

    calibration: CalibrationFitResult
    response: ArrayLike
    response_unit: str
    factors: tuple[QuantificationFactor, ...]
    allow_extrapolation: bool
    raw_quantity: ArrayLike
    quantity: ArrayLike
    extrapolated: object

    def __post_init__(self) -> None:
        if not isinstance(self.calibration, CalibrationFitResult):
            raise TypeError("calibration must be a CalibrationFitResult")
        response_unit = _unit(self.response_unit, name="response_unit")
        if response_unit != self.calibration.y_unit:
            raise ProductCalibrationError(
                "response_unit must exactly match the calibration response unit"
            )
        response = _immutable_float_array(self.response, name="unknown response")
        if not isinstance(self.allow_extrapolation, (bool, np.bool_)):
            raise ProductCalibrationError("allow_extrapolation must be boolean")
        allow_extrapolation = bool(self.allow_extrapolation)
        factors = tuple(self.factors)
        keys: set[str] = set()
        for factor in factors:
            if not isinstance(factor, QuantificationFactor):
                raise TypeError("factors must contain QuantificationFactor values")
            if factor.key in keys:
                raise ProductCalibrationError(
                    f"duplicate quantification factor key {factor.key!r}"
                )
            keys.add(factor.key)

        slope = self.calibration.slope
        if not isfinite(slope) or slope == 0.0:
            raise ProductCalibrationError(
                "calibration slope must be finite and non-zero for inverse quantification"
            )
        expected_raw = (response - self.calibration.intercept) / slope
        if not np.isfinite(expected_raw).all():
            raise ProductCalibrationError(
                "inverse calibration produced non-finite quantity values"
            )
        if np.any(expected_raw < 0.0):
            raise ProductCalibrationError(
                "inverse calibration produced negative quantity; values are not clipped"
            )
        expected_extrapolated = (
            (expected_raw < self.calibration.quantity_min)
            | (expected_raw > self.calibration.quantity_max)
        )
        if np.any(expected_extrapolated) and not allow_extrapolation:
            raise ProductCalibrationError(
                "inverse calibration would extrapolate outside the selected calibration range"
            )
        multiplier = 1.0
        for factor in factors:
            multiplier *= factor.value
        expected_quantity = expected_raw * multiplier

        raw_quantity = _immutable_float_array(self.raw_quantity, name="raw_quantity")
        quantity = _immutable_float_array(self.quantity, name="quantity")
        extrapolated = _immutable_bool_array(self.extrapolated, name="extrapolated")
        if raw_quantity.shape != response.shape or not np.allclose(
            raw_quantity, expected_raw, rtol=1e-12, atol=1e-14
        ):
            raise ProductCalibrationError(
                "retained raw_quantity contradicts calibration inversion"
            )
        if quantity.shape != response.shape or not np.allclose(
            quantity, expected_quantity, rtol=1e-12, atol=1e-14
        ):
            raise ProductCalibrationError(
                "retained quantity contradicts calibration inversion/factors"
            )
        if extrapolated.shape != response.shape or not np.array_equal(
            extrapolated, expected_extrapolated
        ):
            raise ProductCalibrationError(
                "retained extrapolation state contradicts calibrated quantity"
            )

        object.__setattr__(self, "response", response)
        object.__setattr__(self, "response_unit", response_unit)
        object.__setattr__(self, "factors", factors)
        object.__setattr__(self, "allow_extrapolation", allow_extrapolation)
        object.__setattr__(self, "raw_quantity", raw_quantity)
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(self, "extrapolated", extrapolated)

    @property
    def quantity_unit(self) -> str:
        return self.calibration.x_unit

    @property
    def factor_multiplier(self) -> float:
        multiplier = 1.0
        for factor in self.factors:
            multiplier *= factor.value
        return multiplier


def quantify_response(
    calibration: CalibrationFitResult,
    response: ArrayLike | float,
    *,
    response_unit: str,
    factors: tuple[QuantificationFactor, ...] = (),
    allow_extrapolation: bool = False,
) -> QuantificationResult:
    """Invert one reviewed calibration and apply explicit dimensionless factors."""
    if not isinstance(calibration, CalibrationFitResult):
        raise TypeError("calibration must be a CalibrationFitResult")
    response_values = _immutable_float_array(response, name="unknown response")
    slope = calibration.slope
    if not isfinite(slope) or slope == 0.0:
        raise ProductCalibrationError(
            "calibration slope must be finite and non-zero for inverse quantification"
        )
    raw_quantity = (response_values - calibration.intercept) / slope
    factor_values = tuple(factors)
    multiplier = 1.0
    for factor in factor_values:
        if not isinstance(factor, QuantificationFactor):
            raise TypeError("factors must contain QuantificationFactor values")
        multiplier *= factor.value
    quantity = raw_quantity * multiplier
    extrapolated = (
        (raw_quantity < calibration.quantity_min)
        | (raw_quantity > calibration.quantity_max)
    )
    return QuantificationResult(
        calibration=calibration,
        response=response_values,
        response_unit=response_unit,
        factors=factor_values,
        allow_extrapolation=allow_extrapolation,
        raw_quantity=raw_quantity,
        quantity=quantity,
        extrapolated=extrapolated,
    )


@dataclass(frozen=True, slots=True, eq=False)
class QuantificationSummary:
    """Explicit replicate summary for one quantification result."""

    result: QuantificationResult
    n: int
    mean: float
    sample_std: float | None
    rsd_percent: float | None

    def __post_init__(self) -> None:
        if not isinstance(self.result, QuantificationResult):
            raise TypeError("result must be a QuantificationResult")
        values = np.asarray(self.result.quantity, dtype=np.float64).reshape(-1)
        expected_n = int(values.size)
        expected_mean = float(np.mean(values))
        expected_std = (
            None
            if expected_n < 2
            else float(np.std(values, ddof=1))
        )
        expected_rsd = (
            None
            if expected_std is None or expected_mean == 0.0
            else expected_std / abs(expected_mean) * 100.0
        )
        if isinstance(self.n, (bool, np.bool_)) or not isinstance(self.n, (int, np.integer)):
            raise ProductCalibrationError("summary n must be an integer")
        if int(self.n) != expected_n:
            raise ProductCalibrationError("summary n contradicts quantification values")
        if not _same_float(_finite_float(self.mean, name="mean"), expected_mean):
            raise ProductCalibrationError("summary mean contradicts quantification values")
        if not _same_optional(self.sample_std, expected_std):
            raise ProductCalibrationError(
                "summary sample_std contradicts quantification values"
            )
        if not _same_optional(self.rsd_percent, expected_rsd):
            raise ProductCalibrationError(
                "summary rsd_percent contradicts quantification values"
            )
        object.__setattr__(self, "n", expected_n)
        object.__setattr__(self, "mean", expected_mean)
        object.__setattr__(self, "sample_std", expected_std)
        object.__setattr__(self, "rsd_percent", expected_rsd)

    @property
    def quantity_unit(self) -> str:
        return self.result.quantity_unit


def summarize_quantification_replicates(
    result: QuantificationResult,
) -> QuantificationSummary:
    """Return an explicit arithmetic replicate summary without outlier rejection."""
    if not isinstance(result, QuantificationResult):
        raise TypeError("result must be a QuantificationResult")
    values = np.asarray(result.quantity, dtype=np.float64).reshape(-1)
    n = int(values.size)
    mean = float(np.mean(values))
    sample_std = None if n < 2 else float(np.std(values, ddof=1))
    rsd_percent = (
        None
        if sample_std is None or mean == 0.0
        else sample_std / abs(mean) * 100.0
    )
    return QuantificationSummary(
        result=result,
        n=n,
        mean=mean,
        sample_std=sample_std,
        rsd_percent=rsd_percent,
    )


__all__ = [
    "CalibrationFitResult",
    "CalibrationInterceptPolicy",
    "CalibrationRange",
    "ProductCalibrationError",
    "QuantificationFactor",
    "QuantificationResult",
    "QuantificationSummary",
    "fit_calibration",
    "quantify_response",
    "summarize_quantification_replicates",
]
