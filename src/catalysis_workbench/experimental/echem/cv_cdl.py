"""Explicit cyclic-voltammetry sampling, Cdl fitting, and ECSA conversion."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from numbers import Real
from types import MappingProxyType
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray

from catalysis_workbench.core import Series

from .provenance import SourceDataRef, source_data_ref
from .quantities import (
    EchemQuantityError,
    area_to_cm2,
    current_density_to_a_cm2,
    current_to_a,
    normalize_unit,
    potential_to_v,
    scan_rate_to_v_s,
)

CVSamplingMethod = Literal["exact", "linear"]
CdlDifferenceMode = Literal["signed", "magnitude"]
CdlCurrentBasis = Literal["current", "geometric_current_density"]

_GEOMETRIC = {"geometric", "geometric_area", "geometric_area_cm2"}
_CS_UNITS = {
    normalize_unit("F/cm^2"): (1.0, "F/cm^2"),
    normalize_unit("mF/cm^2"): (1e-3, "mF/cm^2"),
    normalize_unit("uF/cm^2"): (1e-6, "uF/cm^2"),
}


class CdlError(ValueError):
    """Raised when CV/Cdl/ECSA inputs violate the scientific contract."""


def _immutable(values: ArrayLike, *, name: str) -> NDArray[np.float64]:
    try:
        source = np.asarray(values)
    except (TypeError, ValueError) as exc:
        raise CdlError(f"{name} must contain real numeric values") from exc
    if source.size == 0 or np.iscomplexobj(source) or source.dtype.kind not in "iuf":
        raise CdlError(f"{name} must contain real numeric values")
    normalized = np.ascontiguousarray(source, dtype=np.float64)
    if not np.isfinite(normalized).all():
        raise CdlError(f"{name} must contain only finite values")
    result = np.frombuffer(normalized.tobytes(order="C"), dtype=np.float64)
    result = result.reshape(normalized.shape)
    result.setflags(write=False)
    return result


def _positive_scalar(value: object, *, name: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise CdlError(f"{name} must be a real numeric scalar")
    numeric = float(value)
    if not isfinite(numeric) or numeric <= 0:
        raise CdlError(f"{name} must be finite and greater than zero")
    return numeric


def _finite_scalar(value: object, *, name: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise CdlError(f"{name} must be a real numeric scalar")
    numeric = float(value)
    if not isfinite(numeric):
        raise CdlError(f"{name} must be finite")
    return numeric


def _required_text(value: object, *, name: str) -> str:
    if not isinstance(value, str):
        raise CdlError(f"{name} must be a string")
    text = value.strip()
    if not text:
        raise CdlError(f"{name} must not be empty")
    return text


def _sampling_method(value: object) -> CVSamplingMethod:
    if value == "exact":
        return "exact"
    if value == "linear":
        return "linear"
    raise CdlError("sampling_method must be 'exact' or 'linear'")


def _difference_mode(value: object) -> CdlDifferenceMode:
    if value == "signed":
        return "signed"
    if value == "magnitude":
        return "magnitude"
    raise CdlError("difference_mode must be 'signed' or 'magnitude'")


def _cdl_current_basis(value: object) -> CdlCurrentBasis:
    if value == "current":
        return "current"
    if value == "geometric_current_density":
        return "geometric_current_density"
    raise CdlError(
        "current_basis must be 'current' or 'geometric_current_density'"
    )


def _reference(series: Series) -> str:
    value = series.x_axis.metadata.get("reference")
    if not isinstance(value, str) or not value.strip():
        raise CdlError("CV potential axis requires explicit non-empty reference metadata")
    return " ".join(value.split())


def _normalization(series: Series) -> str | None:
    value = series.y_axis.metadata.get("normalization")
    if value is None:
        return None
    if not isinstance(value, str):
        raise CdlError("current normalization metadata must be a string when present")
    return value.strip().casefold().replace(" ", "_") or None


def _current_basis(series: Series) -> CdlCurrentBasis:
    name = series.y_axis.name.casefold()
    normalization = _normalization(series)
    if name == "current":
        if normalization is not None:
            raise CdlError(
                "total-current CV source must not already declare a normalization basis"
            )
        try:
            current_to_a(series.y, series.y_axis.unit, allow_nan=False)
        except EchemQuantityError as exc:
            raise CdlError(str(exc)) from exc
        return "current"
    if name == "current_density":
        if normalization not in _GEOMETRIC:
            raise CdlError(
                "current-density CV source must explicitly declare geometric-area "
                "normalization"
            )
        try:
            current_density_to_a_cm2(series.y, series.y_axis.unit, allow_nan=False)
        except EchemQuantityError as exc:
            raise CdlError(str(exc)) from exc
        return "geometric_current_density"
    raise CdlError("CV y-axis name must be 'current' or 'current_density'")


def _potential_values_v(series: Series) -> NDArray[np.float64]:
    if series.x_axis.name.casefold() != "potential":
        raise CdlError("CV x-axis name must be 'potential'")
    _reference(series)
    try:
        values = potential_to_v(series.x, series.x_axis.unit, allow_nan=False)
    except EchemQuantityError as exc:
        raise CdlError(str(exc)) from exc
    return _immutable(values, name="CV potential")


def _canonical_current(series: Series) -> NDArray[np.float64]:
    basis = _current_basis(series)
    try:
        values = (
            current_to_a(series.y, series.y_axis.unit, allow_nan=False)
            if basis == "current"
            else current_density_to_a_cm2(
                series.y,
                series.y_axis.unit,
                allow_nan=False,
            )
        )
    except EchemQuantityError as exc:
        raise CdlError(str(exc)) from exc
    return _immutable(values, name="CV current")


def _monotonic_direction(values: NDArray[np.float64]) -> int:
    if values.size < 2:
        raise CdlError("each CV sweep must contain at least two potential points")
    diff = np.diff(values)
    if np.all(diff > 0):
        return 1
    if np.all(diff < 0):
        return -1
    raise CdlError("each CV sweep potential grid must be strictly monotonic")


def _scan_rate_v_s(value: object, unit: object) -> float:
    numeric = _positive_scalar(value, name="scan_rate_value")
    if not isinstance(unit, str) or not unit.strip():
        raise CdlError("scan_rate_unit must be a non-empty string")
    try:
        converted = scan_rate_to_v_s(numeric, unit, allow_nan=False)
    except EchemQuantityError as exc:
        raise CdlError(str(exc)) from exc
    return _positive_scalar(float(np.asarray(converted).item()), name="scan_rate_v_s")


@dataclass(frozen=True, slots=True)
class CVSweepPair:
    """One explicit anodic/cathodic CV pair measured at one scan rate."""

    key: str
    anodic: Series
    cathodic: Series
    scan_rate_value: float
    scan_rate_unit: str

    def __post_init__(self) -> None:
        key = _required_text(self.key, name="CVSweepPair.key")
        if not isinstance(self.anodic, Series) or not isinstance(self.cathodic, Series):
            raise TypeError("anodic and cathodic must both be Series instances")

        anodic_v = _potential_values_v(self.anodic)
        cathodic_v = _potential_values_v(self.cathodic)
        if _monotonic_direction(anodic_v) != 1:
            raise CdlError("anodic CV sweep must have strictly increasing potential")
        if _monotonic_direction(cathodic_v) != -1:
            raise CdlError("cathodic CV sweep must have strictly decreasing potential")
        if anodic_v.shape != cathodic_v.shape or not np.allclose(
            anodic_v,
            cathodic_v[::-1],
            rtol=1e-12,
            atol=1e-12,
        ):
            raise CdlError(
                "anodic and cathodic potential grids must match after reversing the "
                "cathodic sweep; no hidden grid alignment is performed"
            )

        anodic_basis = _current_basis(self.anodic)
        cathodic_basis = _current_basis(self.cathodic)
        if anodic_basis != cathodic_basis:
            raise CdlError("anodic and cathodic sweeps must use the same current basis")
        _canonical_current(self.anodic)
        _canonical_current(self.cathodic)

        anodic_ref = _reference(self.anodic)
        cathodic_ref = _reference(self.cathodic)
        if anodic_ref.casefold() != cathodic_ref.casefold():
            raise CdlError("anodic and cathodic potential references must match")

        _scan_rate_v_s(self.scan_rate_value, self.scan_rate_unit)
        object.__setattr__(self, "key", key)
        object.__setattr__(self, "scan_rate_value", float(self.scan_rate_value))
        object.__setattr__(self, "scan_rate_unit", self.scan_rate_unit.strip())

    @property
    def scan_rate_v_s(self) -> float:
        return _scan_rate_v_s(self.scan_rate_value, self.scan_rate_unit)

    @property
    def current_basis(self) -> CdlCurrentBasis:
        return _current_basis(self.anodic)

    @property
    def reference(self) -> str:
        return _reference(self.anodic)


@dataclass(frozen=True, slots=True)
class CdlPairProvenance:
    """Traceable input identity for one scan-rate pair."""

    key: str
    scan_rate_value: float
    scan_rate_unit: str
    scan_rate_v_s: float
    anodic_source: SourceDataRef
    cathodic_source: SourceDataRef

    def __post_init__(self) -> None:
        key = _required_text(self.key, name="pair provenance key")
        rate = _scan_rate_v_s(self.scan_rate_value, self.scan_rate_unit)
        canonical = _positive_scalar(self.scan_rate_v_s, name="scan_rate_v_s")
        if not np.isclose(rate, canonical, rtol=1e-12, atol=0.0):
            raise CdlError("scan-rate provenance is internally inconsistent")
        if not isinstance(self.anodic_source, SourceDataRef) or not isinstance(
            self.cathodic_source,
            SourceDataRef,
        ):
            raise TypeError("pair provenance sources must be SourceDataRef instances")
        object.__setattr__(self, "key", key)
        object.__setattr__(self, "scan_rate_value", float(self.scan_rate_value))
        object.__setattr__(self, "scan_rate_unit", self.scan_rate_unit.strip())
        object.__setattr__(self, "scan_rate_v_s", canonical)


def sample_cv_current(
    series: Series,
    potential_value: float,
    *,
    potential_unit: str = "V",
    sampling_method: CVSamplingMethod = "linear",
) -> float:
    """Sample one monotonic CV sweep in canonical current units without extrapolation."""
    if not isinstance(series, Series):
        raise TypeError("series must be a Series")
    method = _sampling_method(sampling_method)
    potential_v = _potential_values_v(series)
    direction = _monotonic_direction(potential_v)
    current = _canonical_current(series)
    try:
        target_array = potential_to_v(
            _finite_scalar(potential_value, name="potential_value"),
            potential_unit,
            allow_nan=False,
        )
    except EchemQuantityError as exc:
        raise CdlError(str(exc)) from exc
    target = float(np.asarray(target_array).item())

    low = float(np.min(potential_v))
    high = float(np.max(potential_v))
    if target < low - 1e-12 or target > high + 1e-12:
        raise CdlError("target potential lies outside the measured sweep; no extrapolation")

    exact = np.flatnonzero(np.isclose(potential_v, target, rtol=1e-12, atol=1e-12))
    if exact.size:
        if exact.size != 1:
            raise CdlError("target potential matches multiple CV points")
        return float(current[int(exact[0])])
    if method == "exact":
        raise CdlError("target potential is not present on the measured grid")

    if direction < 0:
        x = potential_v[::-1]
        y = current[::-1]
    else:
        x = potential_v
        y = current
    upper = int(np.searchsorted(x, target, side="right"))
    lower = upper - 1
    if lower < 0 or upper >= x.size:
        raise CdlError("target potential cannot be bracketed; no extrapolation")
    x0 = float(x[lower])
    x1 = float(x[upper])
    y0 = float(y[lower])
    y1 = float(y[upper])
    fraction = (target - x0) / (x1 - x0)
    return y0 + fraction * (y1 - y0)


@dataclass(frozen=True, slots=True, eq=False)
class CdlFitResult:
    """Immutable free-intercept linear Cdl fit with full scan-rate provenance."""

    scan_rate_v_s: ArrayLike
    anodic_current: ArrayLike
    cathodic_current: ArrayLike
    delta_half: ArrayLike
    current_basis: CdlCurrentBasis
    target_potential_v: float
    reference: str
    sampling_method: CVSamplingMethod
    difference_mode: CdlDifferenceMode
    slope: float
    intercept: float
    r_squared: float
    pair_provenance: tuple[CdlPairProvenance, ...]

    def __post_init__(self) -> None:
        scan_rate = _immutable(self.scan_rate_v_s, name="scan rates")
        anodic = _immutable(self.anodic_current, name="anodic current")
        cathodic = _immutable(self.cathodic_current, name="cathodic current")
        delta = _immutable(self.delta_half, name="half-current differences")
        if scan_rate.ndim != 1:
            raise CdlError("scan rates must be one-dimensional")
        if not (scan_rate.shape == anodic.shape == cathodic.shape == delta.shape):
            raise CdlError("Cdl fit arrays must have matching shapes")
        if scan_rate.size < 3:
            raise CdlError("Cdl fitting requires at least three distinct scan rates")
        if np.any(scan_rate <= 0) or np.any(np.diff(scan_rate) <= 0):
            raise CdlError("canonical scan rates must be positive and strictly increasing")

        current_basis = _cdl_current_basis(self.current_basis)
        target = _finite_scalar(self.target_potential_v, name="target_potential_v")
        reference = _required_text(self.reference, name="reference")
        sampling = _sampling_method(self.sampling_method)
        difference = _difference_mode(self.difference_mode)
        slope = _positive_scalar(self.slope, name="Cdl slope")
        intercept = _finite_scalar(self.intercept, name="fit intercept")
        r_squared = _finite_scalar(self.r_squared, name="r_squared")
        if r_squared < -1e-12 or r_squared > 1.0 + 1e-12:
            raise CdlError("r_squared must lie between 0 and 1")
        r_squared = min(1.0, max(0.0, r_squared))

        expected_delta = (anodic - cathodic) / 2.0
        if difference == "magnitude":
            expected_delta = np.abs(expected_delta)
        if not np.allclose(delta, expected_delta, rtol=1e-12, atol=1e-15):
            raise CdlError(
                "delta_half is inconsistent with anodic/cathodic current and "
                "difference_mode"
            )

        provenance = tuple(self.pair_provenance)
        if len(provenance) != scan_rate.size:
            raise CdlError("pair provenance count must match scan-rate point count")
        if not all(isinstance(item, CdlPairProvenance) for item in provenance):
            raise TypeError("pair_provenance must contain CdlPairProvenance instances")
        keys = tuple(item.key for item in provenance)
        if len(keys) != len(set(keys)):
            raise CdlError("pair provenance keys must be unique")
        prov_rates = np.asarray([item.scan_rate_v_s for item in provenance])
        if not np.allclose(scan_rate, prov_rates, rtol=1e-12, atol=0.0):
            raise CdlError("pair provenance scan rates do not match fit scan rates")

        fitted = slope * scan_rate + intercept
        ss_res = float(np.sum((delta - fitted) ** 2))
        ss_tot = float(np.sum((delta - np.mean(delta)) ** 2))
        if ss_tot == 0.0:
            raise CdlError("Cdl response has zero variance and cannot define R-squared")
        expected_r2 = 1.0 - ss_res / ss_tot
        if not np.isclose(r_squared, expected_r2, rtol=1e-10, atol=1e-12):
            raise CdlError("r_squared is inconsistent with the supplied linear fit")

        object.__setattr__(self, "scan_rate_v_s", scan_rate)
        object.__setattr__(self, "anodic_current", anodic)
        object.__setattr__(self, "cathodic_current", cathodic)
        object.__setattr__(self, "delta_half", delta)
        object.__setattr__(self, "current_basis", current_basis)
        object.__setattr__(self, "target_potential_v", target)
        object.__setattr__(self, "reference", reference)
        object.__setattr__(self, "sampling_method", sampling)
        object.__setattr__(self, "difference_mode", difference)
        object.__setattr__(self, "slope", slope)
        object.__setattr__(self, "intercept", intercept)
        object.__setattr__(self, "r_squared", r_squared)
        object.__setattr__(self, "pair_provenance", provenance)

    @property
    def cdl_unit(self) -> str:
        return "F" if self.current_basis == "current" else "F/cm^2"

    @property
    def current_unit(self) -> str:
        return "A" if self.current_basis == "current" else "A/cm^2"

    @property
    def fit_values(self) -> NDArray[np.float64]:
        return _immutable(
            self.slope * self.scan_rate_v_s + self.intercept,
            name="Cdl fitted current",
        )

    @property
    def n_points(self) -> int:
        return int(self.scan_rate_v_s.size)

    @property
    def pair_keys(self) -> tuple[str, ...]:
        return tuple(item.key for item in self.pair_provenance)


def fit_cdl(
    pairs: Sequence[CVSweepPair],
    *,
    potential_value: float,
    potential_unit: str = "V",
    sampling_method: CVSamplingMethod = "linear",
    difference_mode: CdlDifferenceMode = "signed",
) -> CdlFitResult:
    """Fit free-intercept Cdl from explicit scan-rate CV sweep pairs."""
    if isinstance(pairs, (str, bytes)) or not isinstance(pairs, Sequence):
        raise TypeError("pairs must be a sequence of CVSweepPair instances")
    resolved = tuple(pairs)
    if len(resolved) < 3:
        raise CdlError("Cdl fitting requires at least three scan-rate pairs")
    if not all(isinstance(item, CVSweepPair) for item in resolved):
        raise TypeError("pairs must contain only CVSweepPair instances")
    keys = tuple(item.key for item in resolved)
    if len(keys) != len(set(keys)):
        raise CdlError("CVSweepPair keys must be unique")

    method = _sampling_method(sampling_method)
    mode = _difference_mode(difference_mode)
    try:
        target = float(
            np.asarray(
                potential_to_v(
                    _finite_scalar(potential_value, name="potential_value"),
                    potential_unit,
                    allow_nan=False,
                )
            ).item()
        )
    except EchemQuantityError as exc:
        raise CdlError(str(exc)) from exc

    ordered = tuple(sorted(resolved, key=lambda item: item.scan_rate_v_s))
    scan_rates = np.asarray([item.scan_rate_v_s for item in ordered], dtype=np.float64)
    if np.any(np.diff(scan_rates) <= 0):
        raise CdlError("scan rates must be distinct after unit conversion")

    basis = ordered[0].current_basis
    reference = ordered[0].reference
    for item in ordered[1:]:
        if item.current_basis != basis:
            raise CdlError("all scan-rate pairs must use the same current basis")
        if item.reference.casefold() != reference.casefold():
            raise CdlError("all scan-rate pairs must use the same potential reference")

    anodic_values: list[float] = []
    cathodic_values: list[float] = []
    provenance: list[CdlPairProvenance] = []
    for item in ordered:
        anodic = sample_cv_current(
            item.anodic,
            target,
            potential_unit="V",
            sampling_method=method,
        )
        cathodic = sample_cv_current(
            item.cathodic,
            target,
            potential_unit="V",
            sampling_method=method,
        )
        anodic_values.append(anodic)
        cathodic_values.append(cathodic)
        provenance.append(
            CdlPairProvenance(
                key=item.key,
                scan_rate_value=item.scan_rate_value,
                scan_rate_unit=item.scan_rate_unit,
                scan_rate_v_s=item.scan_rate_v_s,
                anodic_source=source_data_ref(item.anodic),
                cathodic_source=source_data_ref(item.cathodic),
            )
        )

    anodic_array = np.asarray(anodic_values, dtype=np.float64)
    cathodic_array = np.asarray(cathodic_values, dtype=np.float64)
    delta = (anodic_array - cathodic_array) / 2.0
    if mode == "magnitude":
        delta = np.abs(delta)

    slope, intercept = np.polyfit(scan_rates, delta, deg=1)
    if not isfinite(float(slope)) or not isfinite(float(intercept)):
        raise CdlError("Cdl regression produced non-finite fit parameters")
    if slope <= 0:
        raise CdlError(
            "fitted Cdl slope must be positive; no implicit absolute-value correction "
            "is applied to the fitted slope"
        )
    fitted = slope * scan_rates + intercept
    ss_res = float(np.sum((delta - fitted) ** 2))
    ss_tot = float(np.sum((delta - np.mean(delta)) ** 2))
    if ss_tot == 0.0:
        raise CdlError("Cdl response has zero variance and cannot define R-squared")
    r_squared = 1.0 - ss_res / ss_tot

    return CdlFitResult(
        scan_rate_v_s=scan_rates,
        anodic_current=anodic_array,
        cathodic_current=cathodic_array,
        delta_half=delta,
        current_basis=basis,
        target_potential_v=target,
        reference=reference,
        sampling_method=method,
        difference_mode=mode,
        slope=float(slope),
        intercept=float(intercept),
        r_squared=float(r_squared),
        pair_provenance=tuple(provenance),
    )


@dataclass(frozen=True, slots=True)
class CdlFitCollection:
    """Ordered stable-key collection of Cdl fits for catalysts or replicates."""

    items: tuple[tuple[str, CdlFitResult], ...]

    def __post_init__(self) -> None:
        raw_items = tuple(self.items)
        normalized: list[tuple[str, CdlFitResult]] = []
        for item in raw_items:
            if not isinstance(item, tuple) or len(item) != 2:
                raise CdlError("CdlFitCollection items must be (key, result) pairs")
            key, result = item
            stable_key = _required_text(key, name="CdlFitCollection key")
            if not isinstance(result, CdlFitResult):
                raise TypeError("CdlFitCollection values must be CdlFitResult instances")
            normalized.append((stable_key, result))
        keys = tuple(key for key, _ in normalized)
        if len(keys) != len(set(keys)):
            raise CdlError("CdlFitCollection keys must be unique")
        object.__setattr__(self, "items", tuple(normalized))

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(key for key, _ in self.items)

    @property
    def mapping(self) -> Mapping[str, CdlFitResult]:
        return MappingProxyType(dict(self.items))

    def __getitem__(self, key: str) -> CdlFitResult:
        return self.mapping[key]

    def __len__(self) -> int:
        return len(self.items)


def fit_cdl_groups(
    groups: Mapping[str, Sequence[CVSweepPair]],
    *,
    potential_value: float,
    potential_unit: str = "V",
    sampling_method: CVSamplingMethod = "linear",
    difference_mode: CdlDifferenceMode = "signed",
) -> CdlFitCollection:
    """Fit multiple catalysts/replicates addressed only by explicit stable keys."""
    if not isinstance(groups, Mapping):
        raise TypeError("groups must be a mapping keyed by stable catalyst/replicate key")
    if not groups:
        raise CdlError("groups must not be empty")
    output: list[tuple[str, CdlFitResult]] = []
    seen: set[str] = set()
    for raw_key, pairs in groups.items():
        key = _required_text(raw_key, name="group key")
        if key in seen:
            raise CdlError("group keys must be unique after whitespace normalization")
        seen.add(key)
        output.append(
            (
                key,
                fit_cdl(
                    pairs,
                    potential_value=potential_value,
                    potential_unit=potential_unit,
                    sampling_method=sampling_method,
                    difference_mode=difference_mode,
                ),
            )
        )
    return CdlFitCollection(tuple(output))


def _specific_capacitance_f_cm2(value: object, unit: object) -> tuple[float, str]:
    numeric = _positive_scalar(value, name="specific_capacitance_value")
    if not isinstance(unit, str) or not unit.strip():
        raise CdlError("specific_capacitance_unit must be a non-empty string")
    try:
        factor, canonical = _CS_UNITS[normalize_unit(unit)]
    except (EchemQuantityError, KeyError) as exc:
        raise CdlError(
            "specific_capacitance_unit must be F/cm^2, mF/cm^2, or uF/cm^2"
        ) from exc
    return numeric * factor, canonical


@dataclass(frozen=True, slots=True)
class ECSAResult:
    """Traceable ECSA obtained from Cdl and an explicit specific capacitance."""

    cdl_value: float
    cdl_unit: str
    cdl_current_basis: CdlCurrentBasis
    specific_capacitance_value: float
    specific_capacitance_unit: str
    specific_capacitance_f_cm2: float
    specific_capacitance_basis: str
    total_cdl_f: float
    ecsa_cm2: float
    geometric_area_cm2: float | None = None

    def __post_init__(self) -> None:
        cdl = _positive_scalar(self.cdl_value, name="cdl_value")
        current_basis = _cdl_current_basis(self.cdl_current_basis)
        expected_cdl_unit = "F" if current_basis == "current" else "F/cm^2"
        if self.cdl_unit != expected_cdl_unit:
            raise CdlError("cdl_unit is inconsistent with cdl_current_basis")
        specific = _positive_scalar(
            self.specific_capacitance_value,
            name="specific_capacitance_value",
        )
        canonical_specific, canonical_unit = _specific_capacitance_f_cm2(
            specific,
            self.specific_capacitance_unit,
        )
        supplied_specific = _positive_scalar(
            self.specific_capacitance_f_cm2,
            name="specific_capacitance_f_cm2",
        )
        if not np.isclose(
            canonical_specific,
            supplied_specific,
            rtol=1e-12,
            atol=0.0,
        ):
            raise CdlError("specific capacitance canonical value is inconsistent")
        basis = _required_text(
            self.specific_capacitance_basis,
            name="specific_capacitance_basis",
        )
        total = _positive_scalar(self.total_cdl_f, name="total_cdl_f")
        ecsa = _positive_scalar(self.ecsa_cm2, name="ecsa_cm2")
        area = self.geometric_area_cm2
        if current_basis == "current":
            if area is not None:
                raise CdlError(
                    "geometric_area_cm2 must be omitted for total-current-derived Cdl"
                )
            expected_total = cdl
        else:
            area = _positive_scalar(area, name="geometric_area_cm2")
            expected_total = cdl * area
        if not np.isclose(total, expected_total, rtol=1e-12, atol=0.0):
            raise CdlError("total_cdl_f is inconsistent with Cdl current basis")
        expected_ecsa = total / supplied_specific
        if not np.isclose(ecsa, expected_ecsa, rtol=1e-12, atol=0.0):
            raise CdlError("ecsa_cm2 is inconsistent with Cdl and specific capacitance")

        object.__setattr__(self, "cdl_value", cdl)
        object.__setattr__(self, "cdl_current_basis", current_basis)
        object.__setattr__(self, "specific_capacitance_value", specific)
        object.__setattr__(self, "specific_capacitance_unit", canonical_unit)
        object.__setattr__(self, "specific_capacitance_f_cm2", supplied_specific)
        object.__setattr__(self, "specific_capacitance_basis", basis)
        object.__setattr__(self, "total_cdl_f", total)
        object.__setattr__(self, "ecsa_cm2", ecsa)
        object.__setattr__(self, "geometric_area_cm2", area)

    @property
    def roughness_factor(self) -> float | None:
        if self.geometric_area_cm2 is None:
            return None
        return self.ecsa_cm2 / self.geometric_area_cm2


def ecsa_from_cdl(
    result: CdlFitResult,
    *,
    specific_capacitance_value: float,
    specific_capacitance_unit: str,
    specific_capacitance_basis: str,
    geometric_area_value: float | None = None,
    geometric_area_unit: str | None = None,
) -> ECSAResult:
    """Convert Cdl to ECSA without any universal Cs or hidden geometric area."""
    if not isinstance(result, CdlFitResult):
        raise TypeError("result must be a CdlFitResult")
    cs_f_cm2, canonical_cs_unit = _specific_capacitance_f_cm2(
        specific_capacitance_value,
        specific_capacitance_unit,
    )
    basis = _required_text(
        specific_capacitance_basis,
        name="specific_capacitance_basis",
    )

    if result.current_basis == "current":
        if geometric_area_value is not None or geometric_area_unit is not None:
            raise CdlError(
                "geometric area must be omitted for total-current-derived Cdl"
            )
        area_cm2 = None
        total_cdl_f = result.slope
    else:
        if geometric_area_value is None or geometric_area_unit is None:
            raise CdlError(
                "geometric_area_value and geometric_area_unit are required to convert "
                "geometric-area-normalized Cdl into an ECSA area"
            )
        area_numeric = _positive_scalar(
            geometric_area_value,
            name="geometric_area_value",
        )
        try:
            converted_area = area_to_cm2(
                area_numeric,
                geometric_area_unit,
                allow_nan=False,
            )
        except EchemQuantityError as exc:
            raise CdlError(str(exc)) from exc
        area_cm2 = _positive_scalar(
            float(np.asarray(converted_area).item()),
            name="geometric_area_cm2",
        )
        total_cdl_f = result.slope * area_cm2

    ecsa_cm2 = total_cdl_f / cs_f_cm2
    return ECSAResult(
        cdl_value=result.slope,
        cdl_unit=result.cdl_unit,
        cdl_current_basis=result.current_basis,
        specific_capacitance_value=specific_capacitance_value,
        specific_capacitance_unit=canonical_cs_unit,
        specific_capacitance_f_cm2=cs_f_cm2,
        specific_capacitance_basis=basis,
        total_cdl_f=total_cdl_f,
        ecsa_cm2=ecsa_cm2,
        geometric_area_cm2=area_cm2,
    )


__all__ = [
    "CVSamplingMethod",
    "CVSweepPair",
    "CdlCurrentBasis",
    "CdlDifferenceMode",
    "CdlError",
    "CdlFitCollection",
    "CdlFitResult",
    "CdlPairProvenance",
    "ECSAResult",
    "ecsa_from_cdl",
    "fit_cdl",
    "fit_cdl_groups",
    "sample_cv_current",
]
