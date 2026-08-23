"""Explicit, provenance-rich Tafel fitting for processed electrochemical data.

The numerical layer deliberately contains no plotting code. Tafel-region selection,
physical branch, numeric current-sign convention, potential reference, and
current-density normalization basis all remain explicit inputs/metadata.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from numbers import Real
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.stats import linregress

from catalysis_workbench.core import Dataset, Series

from .provenance import AnalysisProvenance, FitWindow, make_analysis_provenance
from .quantities import (
    EchemQuantityError,
    current_density_to_a_cm2,
    normalize_reference_name,
    potential_to_v,
)

TafelBranch = Literal["cathodic", "anodic"]
CurrentSign = Literal["negative", "positive"]

_TAFEL_INPUT_BASIS = "potential_vs_log10_absolute_current_density"
_TAFEL_BRANCHES = frozenset({"cathodic", "anodic"})
_CURRENT_SIGNS = frozenset({"negative", "positive"})
_CANONICAL_TAFEL_UNITS = {
    "current_density": "A/cm^2",
    "intercept": "V",
    "potential": "V",
    "slope": "V/dec",
    "slope_display": "mV/dec",
}


class TafelError(ValueError):
    """Raised when a Tafel fit is scientifically or numerically invalid."""


def _required_text(value: object, *, name: str) -> str:
    if not isinstance(value, str):
        raise TafelError(f"{name} must be a string")
    text = value.strip()
    if not text:
        raise TafelError(f"{name} must not be empty")
    return text


def _normalize_reference(value: object) -> str:
    if not isinstance(value, str):
        raise TafelError("potential reference metadata must be a non-empty string")
    try:
        return normalize_reference_name(value)
    except EchemQuantityError as exc:
        raise TafelError(
            "potential reference metadata must be a non-empty string"
        ) from exc


def _required_choice(
    value: object,
    *,
    name: str,
    allowed: frozenset[str],
) -> str:
    choices = " or ".join(repr(item) for item in sorted(allowed))
    if not isinstance(value, str):
        raise TafelError(f"{name} must be {choices}")
    normalized = value.strip()
    if normalized not in allowed:
        raise TafelError(f"{name} must be {choices}")
    return normalized


def _normalize_branch(value: object) -> str:
    return _required_choice(value, name="branch", allowed=_TAFEL_BRANCHES)


def _normalize_current_sign(value: object) -> str:
    return _required_choice(value, name="current_sign", allowed=_CURRENT_SIGNS)


def _immutable_float_array(values: ArrayLike, *, name: str) -> NDArray[np.float64]:
    try:
        source = np.asarray(values)
    except (TypeError, ValueError) as exc:
        raise TafelError(f"{name} must contain real numeric values") from exc
    if source.ndim != 1:
        raise TafelError(f"{name} must be one-dimensional")
    if source.size == 0:
        raise TafelError(f"{name} must contain at least one value")
    if np.iscomplexobj(source) or source.dtype.kind not in "iuf":
        raise TafelError(f"{name} must contain real numeric values")
    normalized = np.ascontiguousarray(source, dtype=np.float64)
    if not np.isfinite(normalized).all():
        raise TafelError(f"{name} must contain only finite values")
    immutable_buffer = normalized.tobytes(order="C")
    result = np.frombuffer(immutable_buffer, dtype=np.float64, count=normalized.size)
    result.setflags(write=False)
    return result


def _finite_scalar(value: object, *, name: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise TafelError(f"{name} must be a finite real numeric value")
    numeric = float(value)
    if not isfinite(numeric):
        raise TafelError(f"{name} must be a finite real numeric value")
    return numeric


def _validate_source_semantics(provenance: AnalysisProvenance) -> None:
    source = provenance.source
    if source.x_name.casefold() != "potential":
        raise TafelError("Tafel provenance source x axis must be 'potential'")
    if source.y_name.casefold() != "current_density":
        raise TafelError("Tafel provenance source y axis must be 'current_density'")
    try:
        potential_to_v([0.0], source.x_unit, allow_nan=False)
    except EchemQuantityError as exc:
        raise TafelError(
            "Tafel provenance source must declare a supported potential unit"
        ) from exc
    try:
        current_density_to_a_cm2([1.0], source.y_unit, allow_nan=False)
    except EchemQuantityError as exc:
        raise TafelError(
            "Tafel provenance source must declare a supported current-density unit"
        ) from exc


def _validate_provenance_contract(
    provenance: AnalysisProvenance,
    *,
    branch: str,
    current_sign: str,
    current_basis: str,
    potential_reference: str,
    n_points: int,
) -> FitWindow:
    if provenance.input_basis != _TAFEL_INPUT_BASIS:
        raise TafelError(
            f"Tafel provenance input_basis must be {_TAFEL_INPUT_BASIS!r}"
        )
    _validate_source_semantics(provenance)

    fit_window = provenance.fit_window
    if fit_window is None:
        raise TafelError("Tafel provenance requires an explicit fit window")
    if fit_window.unit != "V":
        raise TafelError("Tafel provenance fit window must use canonical unit 'V'")
    if fit_window.n_points != n_points:
        raise TafelError(
            "Tafel provenance fit-window point count must match result arrays"
        )

    units = dict(provenance.units)
    for key, expected in _CANONICAL_TAFEL_UNITS.items():
        if units.get(key) != expected:
            raise TafelError(
                f"Tafel provenance unit {key!r} must be canonical {expected!r}"
            )
    fit_window_input_unit = units.get("fit_window_input")
    if fit_window_input_unit is None:
        raise TafelError("Tafel provenance must record fit_window_input unit")
    try:
        potential_to_v([0.0], fit_window_input_unit, allow_nan=False)
    except EchemQuantityError as exc:
        raise TafelError(
            "Tafel provenance fit_window_input must be a supported potential unit"
        ) from exc

    parameters = dict(provenance.parameters)
    provenance_branch = _normalize_branch(parameters.get("branch"))
    provenance_sign = _normalize_current_sign(parameters.get("current_sign"))
    provenance_basis = _required_text(
        parameters.get("current_density_basis"),
        name="Tafel provenance current_density_basis",
    )
    provenance_reference = _normalize_reference(parameters.get("potential_reference"))

    if provenance_branch != branch:
        raise TafelError("Tafel provenance branch contradicts result branch")
    if provenance_sign != current_sign:
        raise TafelError("Tafel provenance current_sign contradicts result current_sign")
    if provenance_basis.casefold() != current_basis.casefold():
        raise TafelError(
            "Tafel provenance current-density basis contradicts result current_basis"
        )
    if provenance_reference.casefold() != potential_reference.casefold():
        raise TafelError(
            "Tafel provenance potential reference contradicts result reference"
        )
    return fit_window


def _validate_regression_consistency(
    *,
    log_current: NDArray[np.float64],
    potential: NDArray[np.float64],
    fitted: NDArray[np.float64],
    slope: float,
    intercept: float,
    r_squared: float,
    fit_window: FitWindow,
) -> None:
    if np.unique(log_current).size < 2:
        raise TafelError(
            "TafelFitResult requires at least two distinct log-current values"
        )

    tolerance = 1e-12 * max(
        1.0,
        abs(fit_window.lower),
        abs(fit_window.upper),
    )
    if (
        (potential < fit_window.lower - tolerance).any()
        or (potential > fit_window.upper + tolerance).any()
    ):
        raise TafelError(
            "Tafel result potentials must lie inside the provenance fit window"
        )

    expected_fitted = intercept + slope * log_current
    if not np.allclose(
        fitted,
        expected_fitted,
        rtol=1e-10,
        atol=1e-12,
    ):
        raise TafelError(
            "Tafel fitted-potential data contradict slope/intercept and log-current data"
        )

    regression = linregress(log_current, potential)
    expected_slope = float(regression.slope)
    expected_intercept = float(regression.intercept)
    expected_r_squared = float(regression.rvalue**2)
    if not all(
        isfinite(value)
        for value in (expected_slope, expected_intercept, expected_r_squared)
    ):
        raise TafelError("Tafel result arrays produce non-finite regression statistics")
    if not np.isclose(slope, expected_slope, rtol=1e-10, atol=1e-12):
        raise TafelError("Tafel slope contradicts the stored selected data")
    if not np.isclose(intercept, expected_intercept, rtol=1e-10, atol=1e-12):
        raise TafelError("Tafel intercept contradicts the stored selected data")
    if not np.isclose(r_squared, expected_r_squared, rtol=1e-10, atol=1e-12):
        raise TafelError("Tafel R^2 contradicts the stored selected data")


@dataclass(frozen=True, slots=True, eq=False)
class TafelFitResult:
    """Immutable result of one explicit Tafel linear regression.

    ``slope_v_dec`` is the signed coefficient in
    ``E = intercept + slope * log10(|j| / (1 A cm^-2))``. The conventional positive
    magnitude is available through :attr:`slope_magnitude_mv_dec` without discarding
    the signed fitted coefficient.
    """

    slope_v_dec: float
    intercept_v: float
    r_squared: float
    branch: TafelBranch
    current_sign: CurrentSign
    current_basis: str
    potential_reference: str
    log_current_density_a_cm2: ArrayLike
    potential_v: ArrayLike
    fitted_potential_v: ArrayLike
    provenance: AnalysisProvenance

    def __post_init__(self) -> None:
        slope = _finite_scalar(self.slope_v_dec, name="Tafel slope")
        intercept = _finite_scalar(self.intercept_v, name="Tafel intercept")
        r_squared = _finite_scalar(self.r_squared, name="Tafel R^2")
        if not 0.0 <= r_squared <= 1.0:
            raise TafelError("Tafel R^2 must be between 0 and 1")
        branch = _normalize_branch(self.branch)
        current_sign = _normalize_current_sign(self.current_sign)
        basis = _required_text(self.current_basis, name="current_basis")
        reference = _normalize_reference(self.potential_reference)

        log_current = _immutable_float_array(
            self.log_current_density_a_cm2,
            name="Tafel log-current data",
        )
        potential = _immutable_float_array(
            self.potential_v,
            name="Tafel potential data",
        )
        fitted = _immutable_float_array(
            self.fitted_potential_v,
            name="Tafel fitted-potential data",
        )
        if len(log_current) < 3:
            raise TafelError("TafelFitResult requires at least three selected points")
        if len(log_current) != len(potential) or len(log_current) != len(fitted):
            raise TafelError("Tafel result arrays must have the same length")
        if not isinstance(self.provenance, AnalysisProvenance):
            raise TypeError("provenance must be an AnalysisProvenance")

        fit_window = _validate_provenance_contract(
            self.provenance,
            branch=branch,
            current_sign=current_sign,
            current_basis=basis,
            potential_reference=reference,
            n_points=len(log_current),
        )
        _validate_regression_consistency(
            log_current=log_current,
            potential=potential,
            fitted=fitted,
            slope=slope,
            intercept=intercept,
            r_squared=r_squared,
            fit_window=fit_window,
        )

        object.__setattr__(self, "slope_v_dec", slope)
        object.__setattr__(self, "intercept_v", intercept)
        object.__setattr__(self, "r_squared", r_squared)
        object.__setattr__(self, "branch", branch)
        object.__setattr__(self, "current_sign", current_sign)
        object.__setattr__(self, "current_basis", basis)
        object.__setattr__(self, "potential_reference", reference)
        object.__setattr__(self, "log_current_density_a_cm2", log_current)
        object.__setattr__(self, "potential_v", potential)
        object.__setattr__(self, "fitted_potential_v", fitted)

    @property
    def slope_mv_dec(self) -> float:
        """Return the signed fitted Tafel slope in mV dec^-1."""
        return self.slope_v_dec * 1000.0

    @property
    def slope_magnitude_mv_dec(self) -> float:
        """Return the conventional positive magnitude in mV dec^-1."""
        return abs(self.slope_mv_dec)

    @property
    def n_points(self) -> int:
        """Return the number of explicitly selected fit points."""
        return len(self.log_current_density_a_cm2)

    @property
    def fit_window(self) -> FitWindow:
        """Return the canonical potential fit window in volts."""
        fit_window = self.provenance.fit_window
        if fit_window is None:  # guarded by __post_init__; retained for type narrowing
            raise TafelError("Tafel provenance requires an explicit fit window")
        return fit_window


def _validate_series_semantics(
    series: Series,
) -> tuple[NDArray[np.float64], NDArray[np.float64], str, str]:
    if not isinstance(series, Series):
        raise TypeError("series must be a Series")
    if series.x_axis.name.casefold() != "potential":
        raise TafelError("Tafel fitting requires x_axis.name='potential'")
    if series.y_axis.name.casefold() != "current_density":
        raise TafelError("Tafel fitting requires y_axis.name='current_density'")

    try:
        potential_v = potential_to_v(series.x, series.x_axis.unit, allow_nan=True)
        current_density = current_density_to_a_cm2(
            series.y,
            series.y_axis.unit,
            allow_nan=True,
        )
    except EchemQuantityError as exc:
        raise TafelError(str(exc)) from exc

    reference_raw = series.x_axis.metadata.get("reference")
    if reference_raw is None:
        raise TafelError("Tafel fitting requires explicit potential reference metadata")
    reference = _normalize_reference(reference_raw)

    basis_raw = series.y_axis.metadata.get("normalization")
    if basis_raw is None:
        raise TafelError(
            "Tafel fitting requires explicit current-density normalization metadata"
        )
    basis = _required_text(basis_raw, name="current-density normalization metadata")
    return potential_v, current_density, reference, basis


def _canonical_fit_window(
    fit_window: Sequence[float],
    fit_window_unit: str,
) -> tuple[float, float]:
    if isinstance(fit_window, (str, bytes)) or not isinstance(fit_window, Sequence):
        raise TafelError("fit_window must contain exactly two potential bounds")
    if len(fit_window) != 2:
        raise TafelError("fit_window must contain exactly two potential bounds")
    try:
        converted = potential_to_v(
            [fit_window[0], fit_window[1]],
            fit_window_unit,
            allow_nan=False,
        )
    except (EchemQuantityError, TypeError, ValueError) as exc:
        raise TafelError(f"invalid Tafel fit window: {exc}") from exc
    lower, upper = float(converted[0]), float(converted[1])
    if lower >= upper:
        raise TafelError("fit_window lower bound must be smaller than upper bound")
    return lower, upper


def fit_tafel(
    series: Series,
    fit_window: Sequence[float],
    *,
    fit_window_unit: str,
    branch: TafelBranch,
    current_sign: CurrentSign,
) -> TafelFitResult:
    """Fit one explicit Tafel region and return an immutable traceable result.

    The fit is performed as ``E(V)`` versus
    ``log10(abs(j / (1 A cm^-2)))``. Both electrochemical branch and numeric current
    sign must be declared explicitly; no sign inversion or region selection is inferred.
    """
    normalized_branch = _normalize_branch(branch)
    normalized_sign = _normalize_current_sign(current_sign)

    potential_v, current_density, reference, basis = _validate_series_semantics(series)
    lower_v, upper_v = _canonical_fit_window(fit_window, fit_window_unit)
    selected_mask = (
        np.isfinite(potential_v)
        & (potential_v >= lower_v)
        & (potential_v <= upper_v)
    )
    n_points = int(np.count_nonzero(selected_mask))
    if n_points < 3:
        raise TafelError("Tafel fitting requires at least three points in the fit window")

    selected_potential = np.asarray(potential_v[selected_mask], dtype=np.float64)
    selected_current = np.asarray(current_density[selected_mask], dtype=np.float64)
    if np.isnan(selected_current).any():
        raise TafelError("selected Tafel current-density points must not contain NaN")
    if (selected_current == 0.0).any():
        raise TafelError("selected Tafel current-density points must be non-zero")
    if normalized_sign == "positive" and (selected_current <= 0.0).any():
        raise TafelError(
            "selected Tafel currents contradict current_sign='positive'"
        )
    if normalized_sign == "negative" and (selected_current >= 0.0).any():
        raise TafelError(
            "selected Tafel currents contradict current_sign='negative'"
        )

    log_current = np.log10(np.abs(selected_current))
    if np.unique(log_current).size < 2:
        raise TafelError(
            "selected Tafel points require at least two distinct current values"
        )

    regression = linregress(log_current, selected_potential)
    slope = float(regression.slope)
    intercept = float(regression.intercept)
    r_squared = float(regression.rvalue**2)
    if not all(isfinite(value) for value in (slope, intercept, r_squared)):
        raise TafelError("Tafel linear regression returned non-finite fit statistics")
    fitted = intercept + slope * log_current

    canonical_window = FitWindow(
        lower=lower_v,
        upper=upper_v,
        unit="V",
        n_points=n_points,
    )
    provenance = make_analysis_provenance(
        series,
        input_basis=_TAFEL_INPUT_BASIS,
        fit_window=canonical_window,
        units={
            **_CANONICAL_TAFEL_UNITS,
            "fit_window_input": fit_window_unit,
        },
        parameters={
            "branch": normalized_branch,
            "current_density_basis": basis,
            "current_sign": normalized_sign,
            "potential_reference": reference,
        },
    )
    return TafelFitResult(
        slope_v_dec=slope,
        intercept_v=intercept,
        r_squared=r_squared,
        branch=normalized_branch,
        current_sign=normalized_sign,
        current_basis=basis,
        potential_reference=reference,
        log_current_density_a_cm2=log_current,
        potential_v=selected_potential,
        fitted_potential_v=fitted,
        provenance=provenance,
    )


def _normalize_key_mapping(
    mapping: Mapping[str, object],
    *,
    name: str,
) -> dict[str, object]:
    if not isinstance(mapping, Mapping):
        raise TypeError(f"{name} must be a mapping addressed by Series.key")
    normalized: dict[str, object] = {}
    for raw_key, value in mapping.items():
        if not isinstance(raw_key, str):
            raise TafelError(f"{name} keys must be strings")
        key = raw_key.strip()
        if not key:
            raise TafelError(f"{name} keys must not be empty")
        if key in normalized:
            raise TafelError(f"{name} keys must be unique after normalization")
        normalized[key] = value
    return normalized


def _require_exact_keys(
    mapping: Mapping[str, object],
    *,
    keys: tuple[str, ...],
    name: str,
) -> dict[str, object]:
    normalized = _normalize_key_mapping(mapping, name=name)
    expected = set(keys)
    supplied = set(normalized)
    missing = expected - supplied
    unknown = supplied - expected
    if missing:
        raise TafelError(f"{name} is missing Series.key values: {sorted(missing)!r}")
    if unknown:
        raise TafelError(f"{name} contains unknown Series.key values: {sorted(unknown)!r}")
    return normalized


def _resolve_parameter(
    value: str | Mapping[str, str],
    *,
    keys: tuple[str, ...],
    name: str,
) -> dict[str, str]:
    if isinstance(value, str):
        return {key: value for key in keys}
    resolved = _require_exact_keys(value, keys=keys, name=name)
    normalized: dict[str, str] = {}
    for key, item in resolved.items():
        if not isinstance(item, str):
            raise TafelError(f"{name} values must be strings")
        normalized[key] = item
    return normalized


def fit_tafel_dataset(
    dataset: Dataset,
    fit_windows: Mapping[str, Sequence[float]],
    *,
    fit_window_unit: str | Mapping[str, str],
    branch: TafelBranch | Mapping[str, TafelBranch],
    current_sign: CurrentSign | Mapping[str, CurrentSign],
) -> tuple[TafelFitResult, ...]:
    """Fit an ordered Dataset using explicit stable-key-addressed Tafel windows."""
    if not isinstance(dataset, Dataset):
        raise TypeError("dataset must be a Dataset")
    if len(dataset) == 0:
        raise TafelError("cannot fit an empty Tafel Dataset")
    keys = tuple(item.key for item in dataset)
    if any(not key for key in keys):
        raise TafelError("Dataset Tafel fitting requires non-empty Series.key values")

    windows = _require_exact_keys(fit_windows, keys=keys, name="fit_windows")
    units = _resolve_parameter(
        fit_window_unit,
        keys=keys,
        name="fit_window_unit",
    )
    branches = _resolve_parameter(branch, keys=keys, name="branch")
    signs = _resolve_parameter(current_sign, keys=keys, name="current_sign")

    results: list[TafelFitResult] = []
    for series in dataset:
        window = windows[series.key]
        if isinstance(window, (str, bytes)) or not isinstance(window, Sequence):
            raise TafelError("fit_windows values must be two-value sequences")
        results.append(
            fit_tafel(
                series,
                window,
                fit_window_unit=units[series.key],
                branch=branches[series.key],  # type: ignore[arg-type]
                current_sign=signs[series.key],  # type: ignore[arg-type]
            )
        )
    return tuple(results)
