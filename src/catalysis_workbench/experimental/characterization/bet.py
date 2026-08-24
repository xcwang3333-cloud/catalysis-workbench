"""Explicit quantitative BET analysis on reviewed gas-sorption state."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite, sqrt
from numbers import Real

import numpy as np
from numpy.typing import NDArray
from scipy.constants import Avogadro, R
from scipy.stats import linregress

from catalysis_workbench.core import Series

from .sorption import SorptionError, SorptionWindow, validate_sorption_series

_CANONICAL_LOADING_UNITS = frozenset(
    {"mmol/g", "mol/kg", "mg/g", "cm^3(STP)/g"}
)
_ALLOWED_BET_PROCESSING_OPERATIONS = frozenset(
    {
        "sorption.prepare",
        "crop",
        "sorption.convert_relative_pressure",
    }
)


class BETError(SorptionError):
    """Raised when a quantitative BET request violates the scientific contract."""


def _finite_float(value: object, *, name: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise BETError(f"{name} must be a finite real numeric value")
    number = float(value)
    if not isfinite(number):
        raise BETError(f"{name} must be a finite real numeric value")
    return number


def _positive_float(value: object, *, name: str) -> float:
    number = _finite_float(value, name=name)
    if number <= 0.0:
        raise BETError(f"{name} must be greater than zero")
    return number


def _optional_positive_float(value: object | None, *, name: str) -> float | None:
    if value is None:
        return None
    return _positive_float(value, name=name)


def _immutable_float_array(values: object, *, name: str) -> NDArray[np.float64]:
    try:
        source = np.asarray(values)
    except (TypeError, ValueError) as exc:
        raise BETError(f"{name} must contain real numeric values") from exc
    if source.ndim != 1:
        raise BETError(f"{name} must be one-dimensional")
    if source.size == 0:
        raise BETError(f"{name} must not be empty")
    if np.iscomplexobj(source) or source.dtype.kind not in "iuf":
        raise BETError(f"{name} must contain real numeric values")
    normalized = np.ascontiguousarray(source, dtype=np.float64)
    if not np.isfinite(normalized).all():
        raise BETError(f"{name} must contain only finite values")
    buffer = normalized.tobytes(order="C")
    result = np.frombuffer(buffer, dtype=np.float64, count=normalized.size)
    result.setflags(write=False)
    return result


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


def _direction(values: np.ndarray) -> str:
    delta = np.diff(values)
    if np.all(delta > 0.0):
        return "ascending"
    if np.all(delta < 0.0):
        return "descending"
    raise BETError("BET relative-pressure values must remain strictly monotonic")


def _validate_bet_processing_history(series: Series) -> None:
    history = series.metadata.get("processing_history", ())
    if history is None:
        return
    if not isinstance(history, (list, tuple)):
        raise BETError("BET processing_history metadata must be an ordered list/tuple")
    unsupported: list[str] = []
    for entry in history:
        if not isinstance(entry, Mapping):
            raise BETError("BET processing_history entries must be mappings")
        operation = str(entry.get("operation", "")).strip()
        if operation not in _ALLOWED_BET_PROCESSING_OPERATIONS:
            unsupported.append(operation or "<missing operation>")
    if unsupported:
        names = ", ".join(sorted(set(unsupported)))
        raise BETError(
            "quantitative BET accepts only prepared measured data, explicit measured-point "
            f"crop, and explicit relative-pressure conversion; unsupported processing: {names}"
        )


def _same_float(actual: float, expected: float) -> bool:
    return bool(np.isclose(actual, expected, rtol=1.0e-11, atol=1.0e-13))


def _same_optional(actual: float | None, expected: float | None) -> bool:
    if actual is None or expected is None:
        return actual is None and expected is None
    return _same_float(actual, expected)


def _derived_parameters(
    slope: float,
    intercept: float,
) -> tuple[float | None, float | None, float | None]:
    c_constant: float | None = None
    n_monolayer: float | None = None
    p_monolayer: float | None = None
    if intercept != 0.0:
        candidate_c = slope / intercept + 1.0
        if isfinite(candidate_c):
            c_constant = candidate_c
    denominator = slope + intercept
    if denominator != 0.0:
        candidate_n = 1.0 / denominator
        if isfinite(candidate_n):
            n_monolayer = candidate_n
    if c_constant is not None and c_constant > 0.0:
        candidate_p = 1.0 / (sqrt(c_constant) + 1.0)
        if isfinite(candidate_p):
            p_monolayer = candidate_p
    return c_constant, n_monolayer, p_monolayer


def _consistency(
    *,
    pressure: np.ndarray,
    loading: np.ndarray,
    rouquerol: np.ndarray,
    intercept: float,
    c_constant: float | None,
    n_monolayer: float | None,
) -> BETConsistencyResult:
    positive = bool(
        intercept > 0.0
        and c_constant is not None
        and c_constant > 0.0
        and n_monolayer is not None
        and n_monolayer > 0.0
    )
    order = np.argsort(pressure, kind="stable")
    rouquerol_increasing = bool(np.all(np.diff(rouquerol[order]) > 0.0))
    monolayer_inside = bool(
        n_monolayer is not None
        and float(np.min(loading)) < n_monolayer < float(np.max(loading))
    )
    return BETConsistencyResult(
        positive_parameter_state=positive,
        rouquerol_transform_increasing=rouquerol_increasing,
        monolayer_loading_inside_region=monolayer_inside,
    )


@dataclass(frozen=True, slots=True)
class BETConsistencyResult:
    """Independent pass/fail state for the first reviewed BET consistency checks."""

    positive_parameter_state: bool
    rouquerol_transform_increasing: bool
    monolayer_loading_inside_region: bool

    def __post_init__(self) -> None:
        for name in (
            "positive_parameter_state",
            "rouquerol_transform_increasing",
            "monolayer_loading_inside_region",
        ):
            if not isinstance(getattr(self, name), (bool, np.bool_)):
                raise TypeError(f"{name} must be boolean")
            object.__setattr__(self, name, bool(getattr(self, name)))

    @property
    def all_passed(self) -> bool:
        return bool(
            self.positive_parameter_state
            and self.rouquerol_transform_increasing
            and self.monolayer_loading_inside_region
        )

    @property
    def failed_checks(self) -> tuple[str, ...]:
        failed: list[str] = []
        if not self.positive_parameter_state:
            failed.append("positive_parameter_state")
        if not self.rouquerol_transform_increasing:
            failed.append("rouquerol_transform_increasing")
        if not self.monolayer_loading_inside_region:
            failed.append("monolayer_loading_inside_region")
        return tuple(failed)


@dataclass(frozen=True, slots=True)
class BETRegionEvaluation:
    """Auditable regression and consistency state for one explicit measured BET region."""

    source_key: str
    source_label: str
    source_sha256: str
    source_direction: str
    adsorbate: str
    measurement_temperature_k: float
    branch: str
    pressure_unit: str
    loading_unit: str
    standard_temperature_k: float | None
    standard_pressure_kpa: float | None
    window: SorptionWindow
    source_indices: tuple[int, ...]
    pressure_fraction: NDArray[np.float64]
    loading: NDArray[np.float64]
    rouquerol_transform: NDArray[np.float64]
    bet_transform: NDArray[np.float64]
    best_fit_bet_transform: NDArray[np.float64]
    slope: float
    intercept: float
    r_value: float
    r_squared: float
    c_constant: float | None
    n_monolayer_source: float | None
    p_monolayer: float | None
    consistency: BETConsistencyResult

    def __post_init__(self) -> None:
        pressure = _immutable_float_array(self.pressure_fraction, name="pressure_fraction")
        loading = _immutable_float_array(self.loading, name="loading")
        rouquerol = _immutable_float_array(
            self.rouquerol_transform,
            name="rouquerol_transform",
        )
        bet_values = _immutable_float_array(self.bet_transform, name="bet_transform")
        best_fit = _immutable_float_array(
            self.best_fit_bet_transform,
            name="best_fit_bet_transform",
        )
        size = pressure.size
        if size < 3:
            raise BETError("BETRegionEvaluation requires at least three selected points")
        if any(array.size != size for array in (loading, rouquerol, bet_values, best_fit)):
            raise BETError("BETRegionEvaluation arrays must have identical lengths")
        indices = tuple(int(index) for index in self.source_indices)
        if len(indices) != size or len(set(indices)) != size or any(index < 0 for index in indices):
            raise BETError("BET source_indices must be unique non-negative indices matching arrays")
        if tuple(sorted(indices)) != indices:
            raise BETError("BET source_indices must retain increasing source-storage positions")
        if not isinstance(self.window, SorptionWindow):
            raise TypeError("window must be a SorptionWindow")
        if self.pressure_unit != "1":
            raise BETError("BETRegionEvaluation pressure_unit must be canonical fraction '1'")
        if self.loading_unit not in _CANONICAL_LOADING_UNITS:
            raise BETError(f"unsupported canonical BET loading unit {self.loading_unit!r}")
        if self.branch != "adsorption":
            raise BETError("BETRegionEvaluation branch must be 'adsorption'")
        if not str(self.adsorbate).strip():
            raise BETError("BET adsorbate must not be empty")
        measurement_temperature = _positive_float(
            self.measurement_temperature_k,
            name="measurement_temperature_k",
        )
        standard_temperature = _optional_positive_float(
            self.standard_temperature_k,
            name="standard_temperature_k",
        )
        standard_pressure = _optional_positive_float(
            self.standard_pressure_kpa,
            name="standard_pressure_kpa",
        )
        if (standard_temperature is None) != (standard_pressure is None):
            raise BETError("BET standard temperature and pressure must be supplied together")
        if self.loading_unit == "cm^3(STP)/g" and standard_temperature is None:
            raise BETError("BET volumetric loading requires explicit standard gas conditions")
        if np.any((pressure <= 0.0) | (pressure >= 1.0)):
            raise BETError("BET selected relative pressures must satisfy 0 < P/P0 < 1")
        if np.any(loading <= 0.0):
            raise BETError("BET selected adsorbed quantities must be strictly positive")
        direction = _direction(pressure)
        if self.source_direction != direction:
            raise BETError("BET source_direction contradicts retained selected pressure order")
        if np.any((pressure < self.window.low) | (pressure > self.window.high)):
            raise BETError("BET retained pressure points contradict the declared SorptionWindow")

        expected_rouquerol = loading * (1.0 - pressure)
        expected_bet = pressure / expected_rouquerol
        if not np.allclose(rouquerol, expected_rouquerol, rtol=1e-12, atol=1e-14):
            raise BETError("BET retained Rouquerol transform contradicts pressure/loading data")
        if not np.allclose(bet_values, expected_bet, rtol=1e-12, atol=1e-14):
            raise BETError("BET retained linear transform contradicts pressure/loading data")
        regression = linregress(pressure, expected_bet)
        expected_slope = float(regression.slope)
        expected_intercept = float(regression.intercept)
        expected_r = float(regression.rvalue)
        expected_r_squared = expected_r**2
        for name, actual, expected in (
            ("slope", self.slope, expected_slope),
            ("intercept", self.intercept, expected_intercept),
            ("r_value", self.r_value, expected_r),
            ("r_squared", self.r_squared, expected_r_squared),
        ):
            numeric = _finite_float(actual, name=name)
            if not _same_float(numeric, expected):
                raise BETError(f"BET retained {name} contradicts exact OLS regression")
        expected_best_fit = expected_intercept + expected_slope * pressure
        if not np.allclose(best_fit, expected_best_fit, rtol=1e-12, atol=1e-14):
            raise BETError("BET retained fitted transform contradicts exact OLS regression")
        expected_c, expected_n, expected_p = _derived_parameters(
            expected_slope,
            expected_intercept,
        )
        if not _same_optional(self.c_constant, expected_c):
            raise BETError("BET retained C constant contradicts slope/intercept")
        if not _same_optional(self.n_monolayer_source, expected_n):
            raise BETError("BET retained monolayer loading contradicts slope/intercept")
        if not _same_optional(self.p_monolayer, expected_p):
            raise BETError("BET retained monolayer pressure contradicts C constant")
        expected_consistency = _consistency(
            pressure=pressure,
            loading=loading,
            rouquerol=expected_rouquerol,
            intercept=expected_intercept,
            c_constant=expected_c,
            n_monolayer=expected_n,
        )
        if self.consistency != expected_consistency:
            raise BETError("BET retained consistency state contradicts numerical result")
        source_sha = str(self.source_sha256).strip().casefold()
        if len(source_sha) != 64 or any(ch not in "0123456789abcdef" for ch in source_sha):
            raise BETError("source_sha256 must be a 64-character hexadecimal digest")

        object.__setattr__(self, "source_key", str(self.source_key))
        object.__setattr__(self, "source_label", str(self.source_label))
        object.__setattr__(self, "source_sha256", source_sha)
        object.__setattr__(self, "adsorbate", str(self.adsorbate).strip())
        object.__setattr__(self, "measurement_temperature_k", measurement_temperature)
        object.__setattr__(self, "standard_temperature_k", standard_temperature)
        object.__setattr__(self, "standard_pressure_kpa", standard_pressure)
        object.__setattr__(self, "source_indices", indices)
        object.__setattr__(self, "pressure_fraction", pressure)
        object.__setattr__(self, "loading", loading)
        object.__setattr__(self, "rouquerol_transform", rouquerol)
        object.__setattr__(self, "bet_transform", bet_values)
        object.__setattr__(self, "best_fit_bet_transform", best_fit)
        object.__setattr__(self, "slope", expected_slope)
        object.__setattr__(self, "intercept", expected_intercept)
        object.__setattr__(self, "r_value", expected_r)
        object.__setattr__(self, "r_squared", expected_r_squared)
        object.__setattr__(self, "c_constant", expected_c)
        object.__setattr__(self, "n_monolayer_source", expected_n)
        object.__setattr__(self, "p_monolayer", expected_p)
        object.__setattr__(self, "consistency", expected_consistency)


def evaluate_bet_region(series: Series, window: SorptionWindow) -> BETRegionEvaluation:
    """Evaluate one explicit measured BET region without accepting/rejecting it silently."""
    if not isinstance(series, Series):
        raise TypeError("series must be a Series")
    if not isinstance(window, SorptionWindow):
        raise TypeError("window must be a SorptionWindow")
    validate_sorption_series(series)
    _validate_bet_processing_history(series)
    if str(series.metadata.get("sorption_branch", "")) != "adsorption":
        raise BETError("quantitative BET requires an explicitly declared adsorption branch")
    if str(series.x_axis.unit).strip() != "1":
        raise BETError(
            "quantitative BET requires relative-pressure fraction unit '1'; "
            "convert percent explicitly with convert_relative_pressure() first"
        )
    loading_unit = str(series.y_axis.unit).strip()
    if loading_unit not in _CANONICAL_LOADING_UNITS:
        raise BETError(
            "quantitative BET requires a canonical prepared loading unit: "
            "mmol/g, mol/kg, mg/g, or cm^3(STP)/g"
        )

    pressure_all = np.asarray(series.x, dtype=np.float64)
    loading_all = np.asarray(series.y, dtype=np.float64)
    direction = _direction(pressure_all)
    declared_direction = str(series.metadata.get("sorption_source_direction", "")).strip()
    if declared_direction and declared_direction != direction:
        raise BETError("sorption_source_direction metadata contradicts numerical pressure order")
    if window.low < float(np.min(pressure_all)) or window.high > float(np.max(pressure_all)):
        raise BETError("BET SorptionWindow must be fully contained in the measured pressure range")
    indices_array = np.flatnonzero(
        (pressure_all >= window.low) & (pressure_all <= window.high)
    )
    if indices_array.size < 3:
        raise BETError("BET SorptionWindow must contain at least three measured points")
    pressure = pressure_all[indices_array]
    loading = loading_all[indices_array]
    if np.any((pressure <= 0.0) | (pressure >= 1.0)):
        raise BETError("all selected BET points must satisfy 0 < P/P0 < 1")
    if np.any(loading <= 0.0):
        raise BETError("all selected BET adsorbed quantities must be strictly positive")

    rouquerol = loading * (1.0 - pressure)
    bet_values = pressure / rouquerol
    if not np.isfinite(bet_values).all():
        raise BETError("BET transform produced non-finite values")
    regression = linregress(pressure, bet_values)
    slope = float(regression.slope)
    intercept = float(regression.intercept)
    r_value = float(regression.rvalue)
    if not all(isfinite(value) for value in (slope, intercept, r_value)):
        raise BETError("BET ordinary least-squares regression produced non-finite state")
    r_squared = r_value**2
    c_constant, n_monolayer, p_monolayer = _derived_parameters(slope, intercept)
    consistency = _consistency(
        pressure=pressure,
        loading=loading,
        rouquerol=rouquerol,
        intercept=intercept,
        c_constant=c_constant,
        n_monolayer=n_monolayer,
    )
    standard_temperature = series.metadata.get("sorption_standard_temperature_k")
    standard_pressure = series.metadata.get("sorption_standard_pressure_kpa")

    return BETRegionEvaluation(
        source_key=series.key,
        source_label=series.label,
        source_sha256=_series_data_digest(series),
        source_direction=direction,
        adsorbate=str(series.metadata["sorption_adsorbate"]),
        measurement_temperature_k=float(series.metadata["sorption_temperature_k"]),
        branch="adsorption",
        pressure_unit="1",
        loading_unit=loading_unit,
        standard_temperature_k=(
            None if standard_temperature is None else float(standard_temperature)
        ),
        standard_pressure_kpa=(
            None if standard_pressure is None else float(standard_pressure)
        ),
        window=window,
        source_indices=tuple(int(index) for index in indices_array),
        pressure_fraction=pressure,
        loading=loading,
        rouquerol_transform=rouquerol,
        bet_transform=bet_values,
        best_fit_bet_transform=intercept + slope * pressure,
        slope=slope,
        intercept=intercept,
        r_value=r_value,
        r_squared=r_squared,
        c_constant=c_constant,
        n_monolayer_source=n_monolayer,
        p_monolayer=p_monolayer,
        consistency=consistency,
    )


def _n_monolayer_to_mol_g(
    evaluation: BETRegionEvaluation,
    *,
    adsorbate_molar_mass_g_mol: float | None,
) -> float:
    n_source = evaluation.n_monolayer_source
    if n_source is None or n_source <= 0.0:
        raise BETError("BET monolayer loading must be finite and positive before area conversion")
    unit = evaluation.loading_unit
    if unit in {"mmol/g", "mol/kg"}:
        return n_source * 1.0e-3
    if unit == "mg/g":
        molar_mass = _optional_positive_float(
            adsorbate_molar_mass_g_mol,
            name="adsorbate_molar_mass_g_mol",
        )
        if molar_mass is None:
            raise BETError("mg/g BET loading requires explicit adsorbate_molar_mass_g_mol")
        return n_source * 1.0e-3 / molar_mass
    if unit == "cm^3(STP)/g":
        temperature = evaluation.standard_temperature_k
        pressure = evaluation.standard_pressure_kpa
        if temperature is None or pressure is None:
            raise BETError("cm^3(STP)/g BET loading requires explicit standard gas conditions")
        return n_source * 1.0e-3 * pressure / (R * temperature)
    raise BETError(f"unsupported BET loading unit {unit!r}")


@dataclass(frozen=True, slots=True)
class BETFitResult:
    """Accepted, physically consistent quantitative BET result."""

    evaluation: BETRegionEvaluation
    cross_section_nm2: float
    adsorbate_molar_mass_g_mol: float | None
    n_monolayer_mol_g: float
    surface_area_m2_g: float

    def __post_init__(self) -> None:
        if not isinstance(self.evaluation, BETRegionEvaluation):
            raise TypeError("evaluation must be a BETRegionEvaluation")
        if not self.evaluation.consistency.all_passed:
            raise BETError("BETFitResult requires a region passing all required consistency checks")
        cross_section = _positive_float(self.cross_section_nm2, name="cross_section_nm2")
        molar_mass = _optional_positive_float(
            self.adsorbate_molar_mass_g_mol,
            name="adsorbate_molar_mass_g_mol",
        )
        expected_n = _n_monolayer_to_mol_g(
            self.evaluation,
            adsorbate_molar_mass_g_mol=molar_mass,
        )
        expected_area = expected_n * Avogadro * cross_section * 1.0e-18
        supplied_n = _positive_float(self.n_monolayer_mol_g, name="n_monolayer_mol_g")
        supplied_area = _positive_float(self.surface_area_m2_g, name="surface_area_m2_g")
        if not _same_float(supplied_n, expected_n):
            raise BETError(
                "BET retained molar monolayer loading contradicts source-unit conversion"
            )
        if not _same_float(supplied_area, expected_area):
            raise BETError("BET retained surface area contradicts monolayer loading/cross-section")
        object.__setattr__(self, "cross_section_nm2", cross_section)
        object.__setattr__(self, "adsorbate_molar_mass_g_mol", molar_mass)
        object.__setattr__(self, "n_monolayer_mol_g", expected_n)
        object.__setattr__(self, "surface_area_m2_g", expected_area)

    @property
    def c_constant(self) -> float:
        value = self.evaluation.c_constant
        if value is None:
            raise BETError("accepted BET result unexpectedly lacks C constant")
        return value

    @property
    def n_monolayer_source(self) -> float:
        value = self.evaluation.n_monolayer_source
        if value is None:
            raise BETError("accepted BET result unexpectedly lacks monolayer loading")
        return value

    @property
    def p_monolayer(self) -> float:
        value = self.evaluation.p_monolayer
        if value is None:
            raise BETError("accepted BET result unexpectedly lacks monolayer pressure")
        return value


def fit_bet(
    series: Series,
    window: SorptionWindow,
    *,
    cross_section_nm2: float,
    adsorbate_molar_mass_g_mol: float | None = None,
) -> BETFitResult:
    """Fit one caller-selected BET region and fail closed on physical inconsistency."""
    evaluation = evaluate_bet_region(series, window)
    if not evaluation.consistency.all_passed:
        failed = ", ".join(evaluation.consistency.failed_checks)
        raise BETError(f"BET region failed required consistency checks: {failed}")
    cross_section = _positive_float(cross_section_nm2, name="cross_section_nm2")
    molar_mass = _optional_positive_float(
        adsorbate_molar_mass_g_mol,
        name="adsorbate_molar_mass_g_mol",
    )
    n_mol_g = _n_monolayer_to_mol_g(
        evaluation,
        adsorbate_molar_mass_g_mol=molar_mass,
    )
    area = n_mol_g * Avogadro * cross_section * 1.0e-18
    return BETFitResult(
        evaluation=evaluation,
        cross_section_nm2=cross_section,
        adsorbate_molar_mass_g_mol=molar_mass,
        n_monolayer_mol_g=n_mol_g,
        surface_area_m2_g=area,
    )


@dataclass(frozen=True, slots=True)
class BETFitDiagnostics:
    """Value-oriented summary copied from an already accepted BET fit."""

    source_key: str
    source_direction: str
    adsorbate: str
    window: SorptionWindow
    n_points: int
    loading_unit: str
    slope: float
    intercept: float
    r_squared: float
    c_constant: float
    n_monolayer_source: float
    n_monolayer_mol_g: float
    p_monolayer: float
    surface_area_m2_g: float
    cross_section_nm2: float
    consistency: BETConsistencyResult


def summarize_bet_fit(result: BETFitResult) -> BETFitDiagnostics:
    """Return diagnostics that mirror an already computed accepted BET fit."""
    if not isinstance(result, BETFitResult):
        raise TypeError("result must be a BETFitResult")
    evaluation = result.evaluation
    return BETFitDiagnostics(
        source_key=evaluation.source_key,
        source_direction=evaluation.source_direction,
        adsorbate=evaluation.adsorbate,
        window=evaluation.window,
        n_points=len(evaluation.source_indices),
        loading_unit=evaluation.loading_unit,
        slope=evaluation.slope,
        intercept=evaluation.intercept,
        r_squared=evaluation.r_squared,
        c_constant=result.c_constant,
        n_monolayer_source=result.n_monolayer_source,
        n_monolayer_mol_g=result.n_monolayer_mol_g,
        p_monolayer=result.p_monolayer,
        surface_area_m2_g=result.surface_area_m2_g,
        cross_section_nm2=result.cross_section_nm2,
        consistency=evaluation.consistency,
    )


__all__ = [
    "BETConsistencyResult",
    "BETError",
    "BETFitDiagnostics",
    "BETFitResult",
    "BETRegionEvaluation",
    "evaluate_bet_region",
    "fit_bet",
    "summarize_bet_fit",
]
