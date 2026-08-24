"""Explicit Koutecky-Levich regression on canonical angular rotation rate."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite
from numbers import Real
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.stats import linregress

from catalysis_workbench.core import Series

from .provenance import AnalysisProvenance, FitWindow, make_analysis_provenance
from .quantities import (
    FARADAY_CONSTANT_C_MOL,
    EchemQuantityError,
    current_density_to_a_cm2,
    current_to_a,
    rotation_rate_to_rad_s,
)

KLCurrentBasis = Literal["current", "current_density"]
KLCurrentMode = Literal["signed", "nonnegative", "magnitude"]
_GEOMETRIC_NORMALIZATION_NAMES = {
    "geometric",
    "geometric_area",
    "geometric_area_cm2",
}
_KL_INPUT_BASIS = "inverse_current_vs_inverse_sqrt_angular_velocity"


class KouteckyLevichError(ValueError):
    """Raised when K-L inputs or derived quantities violate the contract."""


def _immutable_float_array(values: ArrayLike, *, name: str) -> NDArray[np.float64]:
    try:
        source = np.asarray(values)
    except (TypeError, ValueError) as exc:
        raise KouteckyLevichError(f"{name} must contain real numeric values") from exc
    if source.ndim != 1:
        raise KouteckyLevichError(f"{name} must be one-dimensional")
    if source.size == 0:
        raise KouteckyLevichError(f"{name} must contain at least one value")
    if np.iscomplexobj(source) or source.dtype.kind not in "iuf":
        raise KouteckyLevichError(f"{name} must contain real numeric values")
    normalized = np.ascontiguousarray(source, dtype=np.float64)
    if not np.isfinite(normalized).all():
        raise KouteckyLevichError(f"{name} must contain only finite values")
    buffer = normalized.tobytes(order="C")
    result = np.frombuffer(buffer, dtype=np.float64, count=normalized.size)
    result.setflags(write=False)
    return result


def _finite_scalar(value: object, *, name: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise KouteckyLevichError(f"{name} must be a finite real numeric value")
    numeric = float(value)
    if not isfinite(numeric):
        raise KouteckyLevichError(f"{name} must be a finite real numeric value")
    return numeric


def _positive_scalar(value: object, *, name: str) -> float:
    numeric = _finite_scalar(value, name=name)
    if numeric <= 0.0:
        raise KouteckyLevichError(f"{name} must be greater than zero")
    return numeric


def _required_text(value: object, *, name: str) -> str:
    if not isinstance(value, str):
        raise KouteckyLevichError(f"{name} must be a string")
    text = value.strip()
    if not text:
        raise KouteckyLevichError(f"{name} must not be empty")
    return text


def _current_mode(value: object) -> KLCurrentMode:
    if isinstance(value, str):
        if value == "signed":
            return "signed"
        if value == "nonnegative":
            return "nonnegative"
        if value == "magnitude":
            return "magnitude"
    raise KouteckyLevichError(
        "current_mode must be 'signed', 'nonnegative', or 'magnitude'"
    )


def _normalization(series: Series) -> str | None:
    value = series.y_axis.metadata.get("normalization")
    if value is None:
        return None
    return _required_text(value, name="current normalization metadata")


def _validate_series_semantics(
    series: Series,
) -> tuple[NDArray[np.float64], NDArray[np.float64], KLCurrentBasis, str | None, str]:
    if not isinstance(series, Series):
        raise TypeError("series must be a Series")
    if not series.key:
        raise KouteckyLevichError("K-L fitting requires a non-empty stable Series.key")
    if series.x_axis.name.casefold() != "rotation_rate":
        raise KouteckyLevichError("K-L fitting requires x_axis.name='rotation_rate'")
    try:
        rotation = rotation_rate_to_rad_s(
            series.x,
            series.x_axis.unit,
            allow_nan=False,
        )
    except EchemQuantityError as exc:
        raise KouteckyLevichError(str(exc)) from exc

    y_name = series.y_axis.name.casefold()
    normalization = _normalization(series)
    if y_name == "current":
        if normalization is not None:
            raise KouteckyLevichError(
                "total-current K-L input must not declare normalization metadata"
            )
        try:
            current = current_to_a(series.y, series.y_axis.unit, allow_nan=True)
        except EchemQuantityError as exc:
            raise KouteckyLevichError(str(exc)) from exc
        basis: KLCurrentBasis = "current"
        canonical_unit = "A"
    elif y_name == "current_density":
        if normalization is None:
            raise KouteckyLevichError(
                "current-density K-L input requires explicit geometric normalization"
            )
        normalized_basis = normalization.casefold().replace(" ", "_")
        if normalized_basis not in _GEOMETRIC_NORMALIZATION_NAMES:
            raise KouteckyLevichError(
                "current-density K-L input must use geometric-area normalization"
            )
        normalization = "geometric_area"
        try:
            current = current_density_to_a_cm2(
                series.y,
                series.y_axis.unit,
                allow_nan=True,
            )
        except EchemQuantityError as exc:
            raise KouteckyLevichError(str(exc)) from exc
        basis = "current_density"
        canonical_unit = "A/cm^2"
    else:
        raise KouteckyLevichError(
            "K-L y_axis.name must be 'current' or 'current_density'"
        )

    return (
        np.asarray(rotation, dtype=np.float64),
        np.asarray(current, dtype=np.float64),
        basis,
        normalization,
        canonical_unit,
    )


def _canonical_fit_window(
    fit_window: Sequence[float],
    fit_window_unit: str,
) -> tuple[float, float]:
    if isinstance(fit_window, (str, bytes)) or not isinstance(fit_window, Sequence):
        raise KouteckyLevichError(
            "fit_window must contain exactly two rotation-rate bounds"
        )
    if len(fit_window) != 2:
        raise KouteckyLevichError(
            "fit_window must contain exactly two rotation-rate bounds"
        )
    try:
        converted = rotation_rate_to_rad_s(
            [fit_window[0], fit_window[1]],
            fit_window_unit,
            allow_nan=False,
        )
    except (EchemQuantityError, TypeError, ValueError) as exc:
        raise KouteckyLevichError(f"invalid K-L fit window: {exc}") from exc
    lower, upper = float(converted[0]), float(converted[1])
    if lower <= 0.0:
        raise KouteckyLevichError("K-L fit-window lower bound must be greater than zero")
    if lower >= upper:
        raise KouteckyLevichError(
            "fit_window lower bound must be smaller than upper bound"
        )
    return lower, upper


def _fit_current(
    current: NDArray[np.float64],
    *,
    mode: KLCurrentMode,
) -> NDArray[np.float64]:
    if np.isnan(current).any():
        raise KouteckyLevichError("selected K-L current points must not contain NaN")
    if (current == 0.0).any():
        raise KouteckyLevichError("selected K-L current points must be non-zero")
    if mode == "nonnegative":
        if (current <= 0.0).any():
            raise KouteckyLevichError(
                "current_mode='nonnegative' requires selected currents > 0"
            )
        return current
    if mode == "magnitude":
        return np.abs(current)
    return current


def _reciprocal_unit(current_basis: KLCurrentBasis) -> str:
    return "A^-1" if current_basis == "current" else "cm^2/A"


def _slope_unit(current_basis: KLCurrentBasis) -> str:
    return f"{_reciprocal_unit(current_basis)} (rad/s)^1/2"


@dataclass(frozen=True, slots=True, eq=False)
class KouteckyLevichFitResult:
    """Immutable free-intercept K-L regression with deterministic provenance."""

    slope: float
    intercept: float
    r_squared: float
    current_basis: KLCurrentBasis
    current_mode: KLCurrentMode
    normalization: str | None
    rotation_rad_s: ArrayLike
    selected_current_canonical: ArrayLike
    reciprocal_sqrt_rotation: ArrayLike
    reciprocal_current: ArrayLike
    fitted_reciprocal_current: ArrayLike
    provenance: AnalysisProvenance

    def __post_init__(self) -> None:
        slope = _finite_scalar(self.slope, name="K-L slope")
        intercept = _finite_scalar(self.intercept, name="K-L intercept")
        r_squared = _finite_scalar(self.r_squared, name="K-L R^2")
        if r_squared < 0.0 or r_squared > 1.0:
            raise KouteckyLevichError("K-L R^2 must lie between 0 and 1")
        if not isinstance(self.current_basis, str):
            raise KouteckyLevichError(
                "current_basis must be 'current' or 'current_density'"
            )
        if self.current_basis == "current":
            basis: KLCurrentBasis = "current"
        elif self.current_basis == "current_density":
            basis = "current_density"
        else:
            raise KouteckyLevichError(
                "current_basis must be 'current' or 'current_density'"
            )
        mode = _current_mode(self.current_mode)
        normalization = self.normalization
        if basis == "current":
            if normalization is not None:
                raise KouteckyLevichError(
                    "total-current K-L result must not declare normalization"
                )
        else:
            normalized = _required_text(
                normalization,
                name="K-L current-density normalization",
            )
            if normalized.casefold().replace(" ", "_") not in {
                "geometric",
                "geometric_area",
                "geometric_area_cm2",
            }:
                raise KouteckyLevichError(
                    "K-L current-density normalization must be geometric area"
                )
            normalization = "geometric_area"

        rotation = _immutable_float_array(
            self.rotation_rad_s,
            name="K-L rotation data",
        )
        selected_current = _immutable_float_array(
            self.selected_current_canonical,
            name="K-L selected current data",
        )
        transformed_x = _immutable_float_array(
            self.reciprocal_sqrt_rotation,
            name="K-L reciprocal-sqrt rotation data",
        )
        transformed_y = _immutable_float_array(
            self.reciprocal_current,
            name="K-L reciprocal current data",
        )
        fitted = _immutable_float_array(
            self.fitted_reciprocal_current,
            name="K-L fitted reciprocal current data",
        )
        lengths = {
            len(rotation),
            len(selected_current),
            len(transformed_x),
            len(transformed_y),
            len(fitted),
        }
        if len(lengths) != 1:
            raise KouteckyLevichError("all K-L result arrays must have matching lengths")
        if len(rotation) < 3:
            raise KouteckyLevichError("K-L fit result requires at least three points")
        if (rotation <= 0.0).any():
            raise KouteckyLevichError("K-L rotation rates must be greater than zero")

        expected_x = rotation ** -0.5
        fit_current = _fit_current(selected_current, mode=mode)
        expected_y = 1.0 / fit_current
        expected_fitted = intercept + slope * transformed_x
        if not np.allclose(transformed_x, expected_x, rtol=1e-12, atol=1e-15):
            raise KouteckyLevichError(
                "K-L transformed rotation data contradict stored rotation rates"
            )
        if not np.allclose(transformed_y, expected_y, rtol=1e-12, atol=1e-15):
            raise KouteckyLevichError(
                "K-L reciprocal-current data contradict current values and mode"
            )
        if not np.allclose(fitted, expected_fitted, rtol=1e-10, atol=1e-12):
            raise KouteckyLevichError(
                "K-L fitted values contradict stored slope/intercept"
            )
        if np.unique(transformed_x).size < 2:
            raise KouteckyLevichError(
                "K-L fitting requires at least two distinct rotation rates"
            )
        regression = linregress(transformed_x, transformed_y)
        expected_slope = float(regression.slope)
        expected_intercept = float(regression.intercept)
        expected_r_squared = float(regression.rvalue**2)
        if not np.isclose(slope, expected_slope, rtol=1e-10, atol=1e-12):
            raise KouteckyLevichError("K-L slope contradicts stored selected data")
        if not np.isclose(intercept, expected_intercept, rtol=1e-10, atol=1e-12):
            raise KouteckyLevichError("K-L intercept contradicts stored selected data")
        if not np.isclose(r_squared, expected_r_squared, rtol=1e-10, atol=1e-12):
            raise KouteckyLevichError("K-L R^2 contradicts stored selected data")

        if not isinstance(self.provenance, AnalysisProvenance):
            raise TypeError("provenance must be an AnalysisProvenance")
        if self.provenance.input_basis != _KL_INPUT_BASIS:
            raise KouteckyLevichError("K-L provenance input basis is invalid")
        fit_window = self.provenance.fit_window
        if fit_window is None:
            raise KouteckyLevichError("K-L provenance requires an explicit fit window")
        if fit_window.unit != "rad/s" or fit_window.n_points != len(rotation):
            raise KouteckyLevichError(
                "K-L provenance fit window must use rad/s and match point count"
            )
        tolerance = 1e-12 * max(1.0, abs(fit_window.lower), abs(fit_window.upper))
        if (
            (rotation < fit_window.lower - tolerance).any()
            or (rotation > fit_window.upper + tolerance).any()
        ):
            raise KouteckyLevichError(
                "K-L selected rotation rates lie outside the provenance fit window"
            )
        source = self.provenance.source
        if source.x_name.casefold() != "rotation_rate":
            raise KouteckyLevichError("K-L provenance source x semantic is invalid")
        if source.y_name.casefold() != basis:
            raise KouteckyLevichError("K-L provenance source y semantic is invalid")
        parameters = dict(self.provenance.parameters)
        if parameters.get("current_mode") != mode:
            raise KouteckyLevichError(
                "K-L provenance current_mode contradicts result current_mode"
            )
        if parameters.get("current_basis") != basis:
            raise KouteckyLevichError(
                "K-L provenance current_basis contradicts result current_basis"
            )
        if parameters.get("normalization") != normalization:
            raise KouteckyLevichError(
                "K-L provenance normalization contradicts result normalization"
            )

        object.__setattr__(self, "slope", slope)
        object.__setattr__(self, "intercept", intercept)
        object.__setattr__(self, "r_squared", r_squared)
        object.__setattr__(self, "current_basis", basis)
        object.__setattr__(self, "current_mode", mode)
        object.__setattr__(self, "normalization", normalization)
        object.__setattr__(self, "rotation_rad_s", rotation)
        object.__setattr__(self, "selected_current_canonical", selected_current)
        object.__setattr__(self, "reciprocal_sqrt_rotation", transformed_x)
        object.__setattr__(self, "reciprocal_current", transformed_y)
        object.__setattr__(self, "fitted_reciprocal_current", fitted)

    @property
    def n_points(self) -> int:
        return len(self.rotation_rad_s)

    @property
    def fit_window(self) -> FitWindow:
        window = self.provenance.fit_window
        if window is None:
            raise KouteckyLevichError("K-L provenance requires an explicit fit window")
        return window

    @property
    def canonical_current_unit(self) -> str:
        return "A" if self.current_basis == "current" else "A/cm^2"

    @property
    def reciprocal_current_unit(self) -> str:
        return _reciprocal_unit(self.current_basis)

    @property
    def slope_unit(self) -> str:
        return _slope_unit(self.current_basis)


@dataclass(frozen=True, slots=True)
class KLElectronNumberResult:
    """Explicit apparent electron number derived from one positive K-L slope."""

    electron_number: float
    diffusion_coefficient_cm2_s: float
    kinematic_viscosity_cm2_s: float
    concentration_mol_cm3: float
    electrode_area_cm2: float | None
    faraday_constant_c_mol: float
    current_basis: KLCurrentBasis
    fit_source_sha256: str

    def __post_init__(self) -> None:
        electron_number = _positive_scalar(self.electron_number, name="electron_number")
        diffusion = _positive_scalar(
            self.diffusion_coefficient_cm2_s,
            name="diffusion_coefficient_cm2_s",
        )
        viscosity = _positive_scalar(
            self.kinematic_viscosity_cm2_s,
            name="kinematic_viscosity_cm2_s",
        )
        concentration = _positive_scalar(
            self.concentration_mol_cm3,
            name="concentration_mol_cm3",
        )
        faraday = _positive_scalar(
            self.faraday_constant_c_mol,
            name="faraday_constant_c_mol",
        )
        if self.current_basis == "current":
            basis: KLCurrentBasis = "current"
            area = _positive_scalar(self.electrode_area_cm2, name="electrode_area_cm2")
        elif self.current_basis == "current_density":
            basis = "current_density"
            if self.electrode_area_cm2 is not None:
                raise KouteckyLevichError(
                    "current-density K-L electron number must not use electrode area"
                )
            area = None
        else:
            raise KouteckyLevichError(
                "current_basis must be 'current' or 'current_density'"
            )
        sha = _required_text(self.fit_source_sha256, name="fit_source_sha256").lower()
        if len(sha) != 64 or any(character not in "0123456789abcdef" for character in sha):
            raise KouteckyLevichError(
                "fit_source_sha256 must contain exactly 64 hexadecimal characters"
            )

        object.__setattr__(self, "electron_number", electron_number)
        object.__setattr__(self, "diffusion_coefficient_cm2_s", diffusion)
        object.__setattr__(self, "kinematic_viscosity_cm2_s", viscosity)
        object.__setattr__(self, "concentration_mol_cm3", concentration)
        object.__setattr__(self, "electrode_area_cm2", area)
        object.__setattr__(self, "faraday_constant_c_mol", faraday)
        object.__setattr__(self, "current_basis", basis)
        object.__setattr__(self, "fit_source_sha256", sha)


def fit_koutecky_levich(
    series: Series,
    fit_window: Sequence[float],
    *,
    fit_window_unit: str,
    current_mode: KLCurrentMode,
) -> KouteckyLevichFitResult:
    """Fit reciprocal current against inverse square-root angular velocity."""
    mode = _current_mode(current_mode)
    rotation, current, basis, normalization, canonical_unit = _validate_series_semantics(
        series
    )
    lower, upper = _canonical_fit_window(fit_window, fit_window_unit)
    selected = (rotation >= lower) & (rotation <= upper)
    n_points = int(np.count_nonzero(selected))
    if n_points < 3:
        raise KouteckyLevichError(
            "K-L fitting requires at least three measured points in the fit window"
        )
    selected_rotation = np.asarray(rotation[selected], dtype=np.float64)
    if (selected_rotation <= 0.0).any():
        raise KouteckyLevichError("selected K-L rotation rates must be greater than zero")
    selected_current = np.asarray(current[selected], dtype=np.float64)
    fit_current = _fit_current(selected_current, mode=mode)
    transformed_x = selected_rotation ** -0.5
    if np.unique(transformed_x).size < 2:
        raise KouteckyLevichError(
            "K-L fitting requires at least two distinct selected rotation rates"
        )
    transformed_y = 1.0 / fit_current
    regression = linregress(transformed_x, transformed_y)
    slope = float(regression.slope)
    intercept = float(regression.intercept)
    r_squared = float(regression.rvalue**2)
    if not all(isfinite(value) for value in (slope, intercept, r_squared)):
        raise KouteckyLevichError("K-L regression returned non-finite statistics")
    fitted = intercept + slope * transformed_x

    fit_window_record = FitWindow(
        lower=lower,
        upper=upper,
        unit="rad/s",
        n_points=n_points,
    )
    provenance = make_analysis_provenance(
        series,
        input_basis=_KL_INPUT_BASIS,
        fit_window=fit_window_record,
        units={
            "rotation_source": _required_text(
                series.x_axis.unit,
                name="rotation source unit",
            ),
            "rotation": "rad/s",
            "current_source": _required_text(
                series.y_axis.unit,
                name="current source unit",
            ),
            "current": canonical_unit,
            "reciprocal_current": _reciprocal_unit(basis),
            "slope": _slope_unit(basis),
            "fit_window_input": fit_window_unit,
        },
        parameters={
            "current_basis": basis,
            "current_mode": mode,
            "normalization": normalization,
        },
    )
    return KouteckyLevichFitResult(
        slope=slope,
        intercept=intercept,
        r_squared=r_squared,
        current_basis=basis,
        current_mode=mode,
        normalization=normalization,
        rotation_rad_s=selected_rotation,
        selected_current_canonical=selected_current,
        reciprocal_sqrt_rotation=transformed_x,
        reciprocal_current=transformed_y,
        fitted_reciprocal_current=fitted,
        provenance=provenance,
    )


def kl_electron_number(
    result: KouteckyLevichFitResult,
    *,
    diffusion_coefficient_cm2_s: float,
    kinematic_viscosity_cm2_s: float,
    concentration_mol_cm3: float,
    electrode_area_cm2: float | None = None,
    faraday_constant_c_mol: float = FARADAY_CONSTANT_C_MOL,
) -> KLElectronNumberResult:
    """Derive apparent n from a K-L slope using only explicit transport constants."""
    if not isinstance(result, KouteckyLevichFitResult):
        raise TypeError("result must be a KouteckyLevichFitResult")
    if result.current_mode == "signed":
        raise KouteckyLevichError(
            "apparent electron number requires a magnitude or nonnegative K-L fit"
        )
    if result.slope <= 0.0:
        raise KouteckyLevichError(
            "apparent electron number requires a positive K-L slope"
        )
    diffusion = _positive_scalar(
        diffusion_coefficient_cm2_s,
        name="diffusion_coefficient_cm2_s",
    )
    viscosity = _positive_scalar(
        kinematic_viscosity_cm2_s,
        name="kinematic_viscosity_cm2_s",
    )
    concentration = _positive_scalar(
        concentration_mol_cm3,
        name="concentration_mol_cm3",
    )
    faraday = _positive_scalar(
        faraday_constant_c_mol,
        name="faraday_constant_c_mol",
    )
    transport = (
        0.62
        * faraday
        * diffusion ** (2.0 / 3.0)
        * viscosity ** (-1.0 / 6.0)
        * concentration
    )
    if result.current_basis == "current":
        area = _positive_scalar(electrode_area_cm2, name="electrode_area_cm2")
        transport *= area
    else:
        if electrode_area_cm2 is not None:
            raise KouteckyLevichError(
                "electrode_area_cm2 must be omitted for current-density K-L fits"
            )
        area = None
    electron_number = 1.0 / (result.slope * transport)
    if not isfinite(electron_number) or electron_number <= 0.0:
        raise KouteckyLevichError("derived K-L electron number is not positive and finite")
    return KLElectronNumberResult(
        electron_number=electron_number,
        diffusion_coefficient_cm2_s=diffusion,
        kinematic_viscosity_cm2_s=viscosity,
        concentration_mol_cm3=concentration,
        electrode_area_cm2=area,
        faraday_constant_c_mol=faraday,
        current_basis=result.current_basis,
        fit_source_sha256=result.provenance.source.sha256,
    )


__all__ = [
    "KLCurrentBasis",
    "KLCurrentMode",
    "KLElectronNumberResult",
    "KouteckyLevichError",
    "KouteckyLevichFitResult",
    "fit_koutecky_levich",
    "kl_electron_number",
]
