"""Explicit electrochemical stability metrics over caller-declared time windows."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from numbers import Real
from types import MappingProxyType
from typing import Literal

import numpy as np
from numpy.typing import NDArray

from catalysis_workbench.core import Dataset, Series

from .provenance import (
    AnalysisProvenance,
    FitWindow,
    SourceDataRef,
    make_analysis_provenance,
)
from .quantities import EchemQuantityError, time_to_s

StabilityYKind = Literal[
    "current",
    "current_density",
    "potential",
    "faradaic_efficiency",
    "activity",
]
StabilityRetentionMode = Literal["signed", "magnitude"]
StabilityMissingPolicy = Literal["reject", "omit"]

_ALLOWED_Y_KINDS = {
    "current",
    "current_density",
    "potential",
    "faradaic_efficiency",
    "activity",
}
_ACTIVITY_BASES = {"catalyst_mass", "metal_mass", "ecsa"}
_FE_UNITS = {"fraction", "%"}


class StabilityError(ValueError):
    """Raised when a stability calculation violates the scientific contract."""


def _finite_scalar(value: object, *, name: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise StabilityError(f"{name} must be a real numeric scalar")
    numeric = float(value)
    if not isfinite(numeric):
        raise StabilityError(f"{name} must be finite")
    return numeric


def _positive_int(value: object, *, name: str, minimum: int = 1) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise StabilityError(f"{name} must be an integer >= {minimum}")
    numeric = float(value)
    if not isfinite(numeric) or not numeric.is_integer():
        raise StabilityError(f"{name} must be an integer >= {minimum}")
    integer = int(numeric)
    if integer < minimum:
        raise StabilityError(f"{name} must be an integer >= {minimum}")
    return integer


def _nonnegative_int(value: object, *, name: str) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise StabilityError(f"{name} must be a non-negative integer")
    numeric = float(value)
    if not isfinite(numeric) or not numeric.is_integer() or numeric < 0:
        raise StabilityError(f"{name} must be a non-negative integer")
    return int(numeric)


def _required_text(value: object, *, name: str) -> str:
    if not isinstance(value, str):
        raise StabilityError(f"{name} must be a string")
    text = value.strip()
    if not text:
        raise StabilityError(f"{name} must not be empty")
    return text


def _retention_mode(value: object) -> StabilityRetentionMode:
    if isinstance(value, str):
        if value == "signed":
            return "signed"
        if value == "magnitude":
            return "magnitude"
    raise StabilityError("retention_mode must be 'signed' or 'magnitude'")


def _missing_policy(value: object) -> StabilityMissingPolicy:
    if isinstance(value, str):
        if value == "reject":
            return "reject"
        if value == "omit":
            return "omit"
    raise StabilityError("missing_policy must be 'reject' or 'omit'")


def _time_scalar_to_s(value: object, unit: object, *, name: str) -> float:
    numeric = _finite_scalar(value, name=name)
    if not isinstance(unit, str) or not unit.strip():
        raise StabilityError("stability window unit must be a non-empty string")
    try:
        converted = time_to_s(numeric, unit, allow_nan=False)
    except EchemQuantityError as exc:
        raise StabilityError(str(exc)) from exc
    return _finite_scalar(float(np.asarray(converted).item()), name=f"{name}_seconds")


def _metadata_text(series: Series, key: str) -> str | None:
    value = series.y_axis.metadata.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise StabilityError(f"y-axis {key} metadata must be a string when present")
    text = " ".join(value.split())
    return text or None


def _y_kind(series: Series) -> StabilityYKind:
    name = series.y_axis.name.strip().casefold()
    if name not in _ALLOWED_Y_KINDS:
        raise StabilityError(
            "stability y-axis name must be current, current_density, potential, "
            "faradaic_efficiency, or activity"
        )
    return name  # type: ignore[return-value]


def _validate_y_semantics(series: Series) -> tuple[StabilityYKind, str, str | None, str | None]:
    kind = _y_kind(series)
    unit = _required_text(series.y_axis.unit, name="stability y-axis unit")
    reference = _metadata_text(series, "reference")
    normalization = _metadata_text(series, "normalization")

    if kind == "current" and normalization is not None:
        raise StabilityError("total-current stability source must not declare normalization")
    if kind == "current_density" and normalization is None:
        raise StabilityError(
            "current-density stability source requires explicit normalization metadata"
        )
    if kind == "potential" and reference is None:
        raise StabilityError(
            "potential stability source requires explicit reference metadata"
        )
    if kind == "faradaic_efficiency" and unit not in _FE_UNITS:
        raise StabilityError(
            "faradaic-efficiency stability unit must be 'fraction' or '%'"
        )
    if kind == "activity":
        normalized = normalization.casefold().replace(" ", "_") if normalization else None
        if normalized not in _ACTIVITY_BASES:
            raise StabilityError(
                "activity stability source normalization must identify catalyst_mass, "
                "metal_mass, or ecsa"
            )
        normalization = normalized
    return kind, unit, reference, normalization


def _time_values_s(series: Series) -> NDArray[np.float64]:
    if series.x_axis.name.strip().casefold() != "time":
        raise StabilityError("stability x-axis name must be 'time'")
    if not isinstance(series.x_axis.unit, str) or not series.x_axis.unit.strip():
        raise StabilityError("stability time axis requires an explicit unit")
    try:
        converted = time_to_s(series.x, series.x_axis.unit, allow_nan=False)
    except EchemQuantityError as exc:
        raise StabilityError(str(exc)) from exc
    values = np.asarray(converted)
    if values.ndim != 1 or values.size == 0 or np.iscomplexobj(values):
        raise StabilityError("stability time axis must be a non-empty real 1-D array")
    normalized = np.asarray(values, dtype=np.float64)
    if not np.isfinite(normalized).all():
        raise StabilityError("stability time axis must contain only finite values")
    if normalized.size < 2 or not np.all(np.diff(normalized) > 0):
        raise StabilityError("stability time axis must be strictly increasing")
    return normalized


def _y_values(series: Series) -> NDArray[np.float64]:
    source = np.asarray(series.y)
    if source.ndim != 1 or source.size == 0:
        raise StabilityError("stability y data must be a non-empty 1-D array")
    if np.iscomplexobj(source) or source.dtype.kind not in "iuf":
        raise StabilityError("stability y data must contain real numeric values")
    values = np.asarray(source, dtype=np.float64)
    if np.isinf(values).any():
        raise StabilityError("stability y data must not contain +/-inf")
    return values


def validate_stability_series(series: Series) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Validate one stability source without changing its numerical data."""
    if not isinstance(series, Series):
        raise TypeError("series must be a Series")
    if not series.key:
        raise StabilityError("stability source requires a non-empty stable Series.key")
    time_s = _time_values_s(series)
    values = _y_values(series)
    if values.shape != time_s.shape:
        raise StabilityError("stability time and y arrays must have matching shapes")
    _validate_y_semantics(series)
    return time_s, values


@dataclass(frozen=True, slots=True)
class StabilityWindowSpec:
    """Caller-declared inclusive physical time window."""

    lower: float
    upper: float
    unit: str

    def __post_init__(self) -> None:
        lower = _finite_scalar(self.lower, name="window lower")
        upper = _finite_scalar(self.upper, name="window upper")
        unit = _required_text(self.unit, name="window unit")
        lower_s = _time_scalar_to_s(lower, unit, name="window lower")
        upper_s = _time_scalar_to_s(upper, unit, name="window upper")
        if lower_s > upper_s:
            raise StabilityError("stability window lower bound must not exceed upper bound")
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)
        object.__setattr__(self, "unit", unit)

    @property
    def lower_s(self) -> float:
        return _time_scalar_to_s(self.lower, self.unit, name="window lower")

    @property
    def upper_s(self) -> float:
        return _time_scalar_to_s(self.upper, self.unit, name="window upper")


@dataclass(frozen=True, slots=True)
class StabilityWindow:
    """Resolved stability window with the number of usable measured points."""

    spec: StabilityWindowSpec
    n_points: int
    n_missing: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.spec, StabilityWindowSpec):
            raise TypeError("spec must be a StabilityWindowSpec")
        points = _positive_int(self.n_points, name="window n_points")
        missing = _nonnegative_int(self.n_missing, name="window n_missing")
        object.__setattr__(self, "n_points", points)
        object.__setattr__(self, "n_missing", missing)


@dataclass(frozen=True, slots=True)
class StabilityAnalysisConfig:
    """Explicit metric recipe for one stability trace."""

    analysis_window: StabilityWindowSpec
    baseline_window: StabilityWindowSpec
    final_window: StabilityWindowSpec
    retention_mode: StabilityRetentionMode = "signed"
    missing_policy: StabilityMissingPolicy = "reject"

    def __post_init__(self) -> None:
        if not isinstance(self.analysis_window, StabilityWindowSpec):
            raise TypeError("analysis_window must be a StabilityWindowSpec")
        if not isinstance(self.baseline_window, StabilityWindowSpec):
            raise TypeError("baseline_window must be a StabilityWindowSpec")
        if not isinstance(self.final_window, StabilityWindowSpec):
            raise TypeError("final_window must be a StabilityWindowSpec")
        mode = _retention_mode(self.retention_mode)
        policy = _missing_policy(self.missing_policy)

        analysis = self.analysis_window
        baseline = self.baseline_window
        final = self.final_window
        tolerance = 1e-12
        if analysis.lower_s >= analysis.upper_s:
            raise StabilityError("analysis_window must have positive duration")
        if baseline.lower_s < analysis.lower_s - tolerance or baseline.upper_s > analysis.upper_s + tolerance:
            raise StabilityError("baseline_window must lie inside analysis_window")
        if final.lower_s < analysis.lower_s - tolerance or final.upper_s > analysis.upper_s + tolerance:
            raise StabilityError("final_window must lie inside analysis_window")
        if baseline.upper_s > final.lower_s + tolerance:
            raise StabilityError("baseline_window must not overlap or occur after final_window")
        object.__setattr__(self, "retention_mode", mode)
        object.__setattr__(self, "missing_policy", policy)


@dataclass(frozen=True, slots=True)
class StabilityResult:
    """Immutable quantitative stability summary with deterministic provenance."""

    config: StabilityAnalysisConfig
    analysis_window: StabilityWindow
    baseline_window: StabilityWindow
    final_window: StabilityWindow
    y_kind: StabilityYKind
    y_unit: str
    reference: str | None
    normalization: str | None
    initial_value: float
    final_value: float
    baseline_mean: float
    final_mean: float
    absolute_change: float
    retention_fraction: float
    retention_percent: float
    relative_change_fraction: float
    relative_change_percent: float
    drift_slope_per_s: float
    drift_intercept: float
    drift_r_squared: float
    n_missing_omitted: int
    provenance: AnalysisProvenance

    def __post_init__(self) -> None:
        if not isinstance(self.config, StabilityAnalysisConfig):
            raise TypeError("config must be a StabilityAnalysisConfig")
        for name, window in (
            ("analysis_window", self.analysis_window),
            ("baseline_window", self.baseline_window),
            ("final_window", self.final_window),
        ):
            if not isinstance(window, StabilityWindow):
                raise TypeError(f"{name} must be a StabilityWindow")
        if self.analysis_window.spec != self.config.analysis_window:
            raise StabilityError("resolved analysis window does not match config")
        if self.baseline_window.spec != self.config.baseline_window:
            raise StabilityError("resolved baseline window does not match config")
        if self.final_window.spec != self.config.final_window:
            raise StabilityError("resolved final window does not match config")
        if self.analysis_window.n_points < 2:
            raise StabilityError("analysis window requires at least two usable points")

        kind = self.y_kind
        if kind not in _ALLOWED_Y_KINDS:
            raise StabilityError("invalid stability y_kind")
        unit = _required_text(self.y_unit, name="stability y_unit")
        reference = self.reference
        normalization = self.normalization
        if reference is not None:
            reference = _required_text(reference, name="stability reference")
        if normalization is not None:
            normalization = _required_text(normalization, name="stability normalization")
        if kind == "potential" and reference is None:
            raise StabilityError("potential StabilityResult requires reference")
        if kind in {"current_density", "activity"} and normalization is None:
            raise StabilityError(f"{kind} StabilityResult requires normalization")

        initial = _finite_scalar(self.initial_value, name="initial_value")
        final = _finite_scalar(self.final_value, name="final_value")
        baseline = _finite_scalar(self.baseline_mean, name="baseline_mean")
        final_mean = _finite_scalar(self.final_mean, name="final_mean")
        change = _finite_scalar(self.absolute_change, name="absolute_change")
        retention = _finite_scalar(self.retention_fraction, name="retention_fraction")
        retention_percent = _finite_scalar(self.retention_percent, name="retention_percent")
        relative = _finite_scalar(self.relative_change_fraction, name="relative_change_fraction")
        relative_percent = _finite_scalar(self.relative_change_percent, name="relative_change_percent")
        slope = _finite_scalar(self.drift_slope_per_s, name="drift_slope_per_s")
        intercept = _finite_scalar(self.drift_intercept, name="drift_intercept")
        r_squared = _finite_scalar(self.drift_r_squared, name="drift_r_squared")
        if r_squared < -1e-12 or r_squared > 1.0 + 1e-12:
            raise StabilityError("drift_r_squared must lie between 0 and 1")
        r_squared = min(1.0, max(0.0, r_squared))
        omitted = _nonnegative_int(self.n_missing_omitted, name="n_missing_omitted")

        if not np.isclose(change, final_mean - baseline, rtol=1e-12, atol=1e-15):
            raise StabilityError("absolute_change is inconsistent with window means")
        denominator = baseline if self.config.retention_mode == "signed" else abs(baseline)
        numerator = final_mean if self.config.retention_mode == "signed" else abs(final_mean)
        if denominator == 0.0:
            raise StabilityError("retention baseline denominator must be non-zero")
        expected_retention = numerator / denominator
        if not np.isclose(retention, expected_retention, rtol=1e-12, atol=1e-15):
            raise StabilityError("retention_fraction is inconsistent with window means")
        if not np.isclose(retention_percent, retention * 100.0, rtol=1e-12, atol=1e-12):
            raise StabilityError("retention_percent is inconsistent with retention_fraction")
        if not np.isclose(relative, retention - 1.0, rtol=1e-12, atol=1e-15):
            raise StabilityError("relative_change_fraction is inconsistent with retention")
        if not np.isclose(relative_percent, relative * 100.0, rtol=1e-12, atol=1e-12):
            raise StabilityError("relative_change_percent is inconsistent with retention")
        if not isinstance(self.provenance, AnalysisProvenance):
            raise TypeError("provenance must be AnalysisProvenance")
        if self.provenance.fit_window is None:
            raise StabilityError("stability provenance requires the analysis fit window")
        if self.provenance.fit_window.n_points != self.analysis_window.n_points:
            raise StabilityError("provenance point count does not match analysis window")

        object.__setattr__(self, "y_kind", kind)
        object.__setattr__(self, "y_unit", unit)
        object.__setattr__(self, "reference", reference)
        object.__setattr__(self, "normalization", normalization)
        object.__setattr__(self, "initial_value", initial)
        object.__setattr__(self, "final_value", final)
        object.__setattr__(self, "baseline_mean", baseline)
        object.__setattr__(self, "final_mean", final_mean)
        object.__setattr__(self, "absolute_change", change)
        object.__setattr__(self, "retention_fraction", retention)
        object.__setattr__(self, "retention_percent", retention_percent)
        object.__setattr__(self, "relative_change_fraction", relative)
        object.__setattr__(self, "relative_change_percent", relative_percent)
        object.__setattr__(self, "drift_slope_per_s", slope)
        object.__setattr__(self, "drift_intercept", intercept)
        object.__setattr__(self, "drift_r_squared", r_squared)
        object.__setattr__(self, "n_missing_omitted", omitted)

    @property
    def source(self) -> SourceDataRef:
        return self.provenance.source

    @property
    def drift_unit(self) -> str:
        return f"{self.y_unit}/s"


@dataclass(frozen=True, slots=True)
class StabilityResultCollection:
    """Ordered stable-key collection of stability results."""

    items: tuple[tuple[str, StabilityResult], ...]

    def __post_init__(self) -> None:
        normalized: list[tuple[str, StabilityResult]] = []
        for item in tuple(self.items):
            if not isinstance(item, tuple) or len(item) != 2:
                raise StabilityError("collection items must be (key, result) pairs")
            key, result = item
            stable_key = _required_text(key, name="stability collection key")
            if not isinstance(result, StabilityResult):
                raise TypeError("collection values must be StabilityResult instances")
            if result.source.key != stable_key:
                raise StabilityError("collection key must match result source stable key")
            normalized.append((stable_key, result))
        keys = tuple(key for key, _ in normalized)
        if len(keys) != len(set(keys)):
            raise StabilityError("stability collection keys must be unique")
        object.__setattr__(self, "items", tuple(normalized))

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(key for key, _ in self.items)

    @property
    def mapping(self) -> Mapping[str, StabilityResult]:
        return MappingProxyType(dict(self.items))

    def __getitem__(self, key: str) -> StabilityResult:
        return self.mapping[key]

    def __len__(self) -> int:
        return len(self.items)


def _select_window(
    time_s: NDArray[np.float64],
    usable: NDArray[np.bool_],
    missing: NDArray[np.bool_],
    spec: StabilityWindowSpec,
    *,
    name: str,
) -> tuple[NDArray[np.bool_], StabilityWindow]:
    tolerance = 1e-12
    measured_min = float(time_s[0])
    measured_max = float(time_s[-1])
    if spec.lower_s < measured_min - tolerance or spec.upper_s > measured_max + tolerance:
        raise StabilityError(f"{name} lies outside the measured time range")
    interval = (time_s >= spec.lower_s - tolerance) & (time_s <= spec.upper_s + tolerance)
    selected = interval & usable
    points = int(np.count_nonzero(selected))
    if points < 1:
        raise StabilityError(f"{name} contains no usable measured points")
    return selected, StabilityWindow(
        spec=spec,
        n_points=points,
        n_missing=int(np.count_nonzero(interval & missing)),
    )


def analyze_stability(series: Series, config: StabilityAnalysisConfig) -> StabilityResult:
    """Calculate explicit stability metrics from one already prepared time Series."""
    if not isinstance(series, Series):
        raise TypeError("series must be a Series")
    if not isinstance(config, StabilityAnalysisConfig):
        raise TypeError("config must be a StabilityAnalysisConfig")

    time_s, values = validate_stability_series(series)
    kind, y_unit, reference, normalization = _validate_y_semantics(series)
    tolerance = 1e-12
    analysis_spec = config.analysis_window
    measured_min = float(time_s[0])
    measured_max = float(time_s[-1])
    if analysis_spec.lower_s < measured_min - tolerance or analysis_spec.upper_s > measured_max + tolerance:
        raise StabilityError("analysis_window lies outside the measured time range")
    analysis_membership = (
        (time_s >= analysis_spec.lower_s - tolerance)
        & (time_s <= analysis_spec.upper_s + tolerance)
    )
    if not np.any(analysis_membership):
        raise StabilityError("analysis_window contains no measured points")

    missing = np.isnan(values)
    missing_in_analysis = analysis_membership & missing
    n_missing = int(np.count_nonzero(missing_in_analysis))
    if config.missing_policy == "reject" and n_missing:
        raise StabilityError(
            "analysis_window contains missing y values; use missing_policy='omit' "
            "explicitly to omit them"
        )
    usable = ~missing
    analysis_mask = analysis_membership & usable
    n_analysis = int(np.count_nonzero(analysis_mask))
    if n_analysis < 2:
        raise StabilityError("analysis_window requires at least two usable measured points")

    baseline_mask, baseline_window = _select_window(
        time_s,
        usable,
        missing,
        config.baseline_window,
        name="baseline_window",
    )
    final_mask, final_window = _select_window(
        time_s,
        usable,
        missing,
        config.final_window,
        name="final_window",
    )
    analysis_window = StabilityWindow(
        spec=analysis_spec,
        n_points=n_analysis,
        n_missing=n_missing,
    )

    analysis_indices = np.flatnonzero(analysis_mask)
    initial_value = float(values[int(analysis_indices[0])])
    final_value = float(values[int(analysis_indices[-1])])
    baseline_mean = float(np.mean(values[baseline_mask]))
    final_mean = float(np.mean(values[final_mask]))
    absolute_change = final_mean - baseline_mean

    if config.retention_mode == "signed":
        denominator = baseline_mean
        numerator = final_mean
    else:
        denominator = abs(baseline_mean)
        numerator = abs(final_mean)
    if denominator == 0.0:
        raise StabilityError("retention baseline denominator must be non-zero")
    retention_fraction = numerator / denominator
    relative_change_fraction = retention_fraction - 1.0

    x_fit = time_s[analysis_mask]
    y_fit = values[analysis_mask]
    slope, intercept = np.polyfit(x_fit, y_fit, deg=1)
    slope = float(slope)
    intercept = float(intercept)
    if not isfinite(slope) or not isfinite(intercept):
        raise StabilityError("stability drift fit produced non-finite parameters")
    fitted = slope * x_fit + intercept
    ss_res = float(np.sum((y_fit - fitted) ** 2))
    ss_tot = float(np.sum((y_fit - np.mean(y_fit)) ** 2))
    if ss_tot == 0.0:
        r_squared = 1.0 if np.allclose(y_fit, fitted, rtol=1e-12, atol=1e-15) else 0.0
    else:
        r_squared = 1.0 - ss_res / ss_tot

    fit_window = FitWindow(
        lower=analysis_spec.lower_s,
        upper=analysis_spec.upper_s,
        unit="s",
        n_points=n_analysis,
    )
    provenance = make_analysis_provenance(
        series,
        input_basis=kind,
        fit_window=fit_window,
        units={
            "source_time": series.x_axis.unit,
            "canonical_time": "s",
            "source_y": y_unit,
            "drift": f"{y_unit}/s",
            "retention": "fraction",
        },
        parameters={
            "retention_mode": config.retention_mode,
            "missing_policy": config.missing_policy,
            "baseline_lower_s": config.baseline_window.lower_s,
            "baseline_upper_s": config.baseline_window.upper_s,
            "final_lower_s": config.final_window.lower_s,
            "final_upper_s": config.final_window.upper_s,
            "n_missing_omitted": n_missing if config.missing_policy == "omit" else 0,
            "reference": reference,
            "normalization": normalization,
        },
    )

    return StabilityResult(
        config=config,
        analysis_window=analysis_window,
        baseline_window=baseline_window,
        final_window=final_window,
        y_kind=kind,
        y_unit=y_unit,
        reference=reference,
        normalization=normalization,
        initial_value=initial_value,
        final_value=final_value,
        baseline_mean=baseline_mean,
        final_mean=final_mean,
        absolute_change=absolute_change,
        retention_fraction=retention_fraction,
        retention_percent=retention_fraction * 100.0,
        relative_change_fraction=relative_change_fraction,
        relative_change_percent=relative_change_fraction * 100.0,
        drift_slope_per_s=slope,
        drift_intercept=intercept,
        drift_r_squared=r_squared,
        n_missing_omitted=n_missing if config.missing_policy == "omit" else 0,
        provenance=provenance,
    )


def analyze_stability_dataset(
    dataset: Dataset,
    configs: Mapping[str, StabilityAnalysisConfig],
) -> StabilityResultCollection:
    """Analyze multiple stability traces using exact stable-key configuration mapping."""
    if not isinstance(dataset, Dataset):
        raise TypeError("dataset must be a Dataset")
    if len(dataset) == 0:
        raise StabilityError("stability Dataset must not be empty")
    if not isinstance(configs, Mapping):
        raise TypeError("configs must be a mapping keyed by stable Series.key")

    keys = tuple(series.key for series in dataset)
    if any(not key for key in keys):
        raise StabilityError("every stability Dataset Series requires a stable key")
    config_keys: list[str] = []
    for raw_key in configs:
        config_keys.append(_required_text(raw_key, name="stability config key"))
    if len(config_keys) != len(set(config_keys)):
        raise StabilityError("stability config keys must be unique after normalization")
    if set(config_keys) != set(keys):
        missing = sorted(set(keys) - set(config_keys))
        unknown = sorted(set(config_keys) - set(keys))
        raise StabilityError(
            f"configs must exactly match Dataset stable keys; missing={missing!r}, "
            f"unknown={unknown!r}"
        )

    normalized_configs = {
        _required_text(key, name="stability config key"): value
        for key, value in configs.items()
    }
    output: list[tuple[str, StabilityResult]] = []
    for series in dataset:
        config = normalized_configs[series.key]
        if not isinstance(config, StabilityAnalysisConfig):
            raise TypeError("all configs values must be StabilityAnalysisConfig instances")
        output.append((series.key, analyze_stability(series, config)))
    return StabilityResultCollection(tuple(output))


__all__ = [
    "StabilityAnalysisConfig",
    "StabilityError",
    "StabilityMissingPolicy",
    "StabilityResult",
    "StabilityResultCollection",
    "StabilityRetentionMode",
    "StabilityWindow",
    "StabilityWindowSpec",
    "StabilityYKind",
    "analyze_stability",
    "analyze_stability_dataset",
    "validate_stability_series",
]
