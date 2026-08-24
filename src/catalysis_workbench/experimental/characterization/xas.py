"""Explicit XAS/XANES validation, energy shifting, and normalization."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from math import isfinite
from typing import Any

import numpy as np
from numpy.typing import NDArray

from catalysis_workbench.core import Axis, Series

_ENERGY_NAMES = {"energy"}
_RELATIVE_ENERGY_NAMES = {"energyrelativetoe0", "energye0"}
_MU_NAMES = {"mu", "absorption"}
_NORMALIZED_MU_NAMES = {"normalizedmu", "munormalized"}
_EV_UNITS = {"ev", "electronvolt", "electronvolts"}
_DIMENSIONLESS_UNITS = {"1", "dimensionless", "a.u.", "a.u", "au"}


class XASError(ValueError):
    """Raised when XAS state or a requested XAS operation is invalid."""


def _semantic_token(value: str) -> str:
    token = str(value).strip().casefold()
    return "".join(character for character in token if character.isalnum())


def _compact_unit(unit: str | None) -> str:
    if unit is None:
        return ""
    return "".join(str(unit).strip().casefold().split())


def _finite_float(value: Any, *, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a real numeric value") from exc
    if not isfinite(result):
        raise XASError(f"{name} must be finite")
    return result


def _immutable_float_array(values: Any, *, name: str) -> NDArray[np.float64]:
    array = np.asarray(values)
    if array.ndim != 1:
        raise XASError(f"{name} must be one-dimensional")
    if np.iscomplexobj(array):
        raise XASError(f"{name} must be real-valued")
    result = np.ascontiguousarray(array, dtype=np.float64)
    if result.size == 0 or not np.isfinite(result).all():
        raise XASError(f"{name} must contain finite values")
    frozen = np.frombuffer(result.tobytes(order="C"), dtype=np.float64)
    frozen.setflags(write=False)
    return frozen


def _source_digest(
    source_key: str,
    energy: NDArray[np.float64],
    mu: NDArray[np.float64],
) -> str:
    """Return a digest independently reconstructible from retained XAS source state."""
    digest = hashlib.sha256()
    digest.update(str(source_key).encode("utf-8"))
    digest.update(b"\0")
    digest.update(np.ascontiguousarray(energy, dtype=np.float64).tobytes())
    digest.update(np.ascontiguousarray(mu, dtype=np.float64).tobytes())
    return digest.hexdigest()


def _processing_history(metadata: dict[str, Any]) -> list[Any]:
    history = metadata.get("processing_history", ())
    if not isinstance(history, (list, tuple)):
        raise XASError("processing_history metadata must be a list/tuple when present")
    return list(history)


def _validate_numeric_series(
    series: Series,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    if not isinstance(series, Series):
        raise TypeError("series must be a Series")
    if np.iscomplexobj(series.x) or np.iscomplexobj(series.y):
        raise XASError("XAS energy and absorption data must be real-valued")
    energy = np.asarray(series.x, dtype=np.float64)
    mu = np.asarray(series.y, dtype=np.float64)
    if np.isnan(energy).any() or np.isnan(mu).any():
        raise XASError("XAS data must not contain missing values")
    if not np.isfinite(energy).all() or not np.isfinite(mu).all():
        raise XASError("XAS data must contain only finite values")
    if energy.size < 2:
        raise XASError("XAS data require at least two measured points")
    differences = np.diff(energy)
    if not (np.all(differences > 0.0) or np.all(differences < 0.0)):
        raise XASError("XAS energy must be strictly monotonic with no duplicates")
    return energy, mu


def validate_xas_series(series: Series, *, allow_relative_energy: bool = False) -> None:
    """Validate explicit one-dimensional XAS energy/absorption semantics."""
    _validate_numeric_series(series)
    x_name = _semantic_token(series.x_axis.name)
    allowed_x = set(_ENERGY_NAMES)
    if allow_relative_energy:
        allowed_x |= _RELATIVE_ENERGY_NAMES
    if x_name not in allowed_x:
        expected = (
            "energy or energy_relative_to_e0" if allow_relative_energy else "energy"
        )
        raise XASError(f"XAS x axis must identify {expected}")
    if _compact_unit(series.x_axis.unit) not in _EV_UNITS:
        raise XASError("XAS energy requires an explicit eV unit")

    y_name = _semantic_token(series.y_axis.name)
    if y_name not in (_MU_NAMES | _NORMALIZED_MU_NAMES):
        raise XASError("XAS y axis must identify mu/absorption or normalized_mu")
    if y_name in _NORMALIZED_MU_NAMES:
        unit = _compact_unit(series.y_axis.unit)
        if unit and unit not in _DIMENSIONLESS_UNITS:
            raise XASError("normalized XAS absorption must be dimensionless")


@dataclass(frozen=True, slots=True)
class XASWindow:
    """Inclusive measured-energy window in eV."""

    start_ev: float
    end_ev: float

    def __post_init__(self) -> None:
        start = _finite_float(self.start_ev, name="start_ev")
        end = _finite_float(self.end_ev, name="end_ev")
        if not start < end:
            raise XASError("XASWindow requires start_ev < end_ev")
        object.__setattr__(self, "start_ev", start)
        object.__setattr__(self, "end_ev", end)


@dataclass(frozen=True, slots=True)
class XANESNormalizationSpec:
    """Caller-visible pre/post-edge polynomial normalization specification."""

    e0_ev: float
    pre_edge: XASWindow
    post_edge: XASWindow
    pre_edge_order: int = 1
    post_edge_order: int = 1

    def __post_init__(self) -> None:
        e0 = _finite_float(self.e0_ev, name="e0_ev")
        if not isinstance(self.pre_edge, XASWindow):
            raise TypeError("pre_edge must be an XASWindow")
        if not isinstance(self.post_edge, XASWindow):
            raise TypeError("post_edge must be an XASWindow")
        for name, order in (
            ("pre_edge_order", self.pre_edge_order),
            ("post_edge_order", self.post_edge_order),
        ):
            if isinstance(order, bool) or not isinstance(order, int):
                raise TypeError(f"{name} must be an integer")
            if order < 0 or order > 4:
                raise XASError(f"{name} must be between 0 and 4")
        if not self.pre_edge.end_ev < e0:
            raise XASError("pre-edge window must lie strictly below E0")
        if not self.post_edge.start_ev > e0:
            raise XASError("post-edge window must lie strictly above E0")
        object.__setattr__(self, "e0_ev", e0)


def _evaluate_polynomial(
    coefficients: NDArray[np.float64],
    delta_energy: NDArray[np.float64],
) -> NDArray[np.float64]:
    return np.polynomial.polynomial.polyval(delta_energy, coefficients)


def _fit_centered_polynomial(
    energy: NDArray[np.float64],
    mu: NDArray[np.float64],
    *,
    window: XASWindow,
    e0_ev: float,
    order: int,
    name: str,
) -> NDArray[np.float64]:
    mask = (energy >= window.start_ev) & (energy <= window.end_ev)
    selected_energy = energy[mask]
    selected_mu = mu[mask]
    if selected_energy.size < order + 1:
        raise XASError(f"{name} window needs at least {order + 1} measured points")
    delta = selected_energy - e0_ev
    if np.unique(delta).size < order + 1:
        raise XASError(f"{name} window does not contain enough distinct energies")
    design = np.vander(delta, N=order + 1, increasing=True)
    coefficients, _, rank, _ = np.linalg.lstsq(design, selected_mu, rcond=None)
    if rank != order + 1:
        raise XASError(f"{name} polynomial fit is rank-deficient")
    coefficients = np.asarray(coefficients, dtype=np.float64)
    if not np.isfinite(coefficients).all():
        raise XASError(f"{name} polynomial fit produced non-finite coefficients")
    return coefficients


@dataclass(frozen=True, slots=True, eq=False)
class XANESNormalizationResult:
    """Immutable retained state for one explicit XANES normalization."""

    source_key: str
    source_digest: str
    source_energy_ev: Any
    source_mu: Any
    e0_ev: float
    pre_edge: XASWindow
    post_edge: XASWindow
    pre_edge_order: int
    post_edge_order: int
    pre_edge_coefficients: Any
    post_edge_coefficients: Any
    pre_edge_curve: Any
    post_edge_curve: Any
    edge_step: float
    normalized: Series

    def __post_init__(self) -> None:
        source_key = str(self.source_key)
        source_digest = str(self.source_digest)
        energy = _immutable_float_array(self.source_energy_ev, name="source_energy_ev")
        mu = _immutable_float_array(self.source_mu, name="source_mu")
        expected_digest = _source_digest(source_key, energy, mu)
        if source_digest != expected_digest:
            raise XASError("source_digest contradicts retained XANES source data")

        pre_coeff = _immutable_float_array(
            self.pre_edge_coefficients,
            name="pre_edge_coefficients",
        )
        post_coeff = _immutable_float_array(
            self.post_edge_coefficients,
            name="post_edge_coefficients",
        )
        pre_curve = _immutable_float_array(self.pre_edge_curve, name="pre_edge_curve")
        post_curve = _immutable_float_array(
            self.post_edge_curve,
            name="post_edge_curve",
        )
        if not (energy.size == mu.size == pre_curve.size == post_curve.size):
            raise XASError("retained XANES arrays must have identical lengths")
        if not isinstance(self.normalized, Series):
            raise TypeError("normalized must be a Series")

        spec = XANESNormalizationSpec(
            self.e0_ev,
            self.pre_edge,
            self.post_edge,
            self.pre_edge_order,
            self.post_edge_order,
        )
        edge_step = _finite_float(self.edge_step, name="edge_step")
        if edge_step <= 0.0:
            raise XASError("retained XANES edge_step must be positive")
        if pre_coeff.size != spec.pre_edge_order + 1:
            raise XASError("pre-edge coefficient count does not match polynomial order")
        if post_coeff.size != spec.post_edge_order + 1:
            raise XASError("post-edge coefficient count does not match polynomial order")

        expected_pre = _evaluate_polynomial(pre_coeff, energy - spec.e0_ev)
        expected_post = _evaluate_polynomial(post_coeff, energy - spec.e0_ev)
        if not np.allclose(pre_curve, expected_pre, rtol=1e-12, atol=1e-12):
            raise XASError("retained pre-edge curve contradicts coefficients/source energy")
        if not np.allclose(post_curve, expected_post, rtol=1e-12, atol=1e-12):
            raise XASError("retained post-edge curve contradicts coefficients/source energy")
        expected_step = float(post_coeff[0] - pre_coeff[0])
        if not np.isclose(edge_step, expected_step, rtol=1e-12, atol=1e-12):
            raise XASError("retained edge_step contradicts polynomial intercepts")

        expected_norm = (mu - pre_curve) / edge_step
        validate_xas_series(self.normalized)
        if self.normalized.key != source_key:
            raise XASError("normalized XANES key contradicts source_key")
        if not np.array_equal(np.asarray(self.normalized.x), energy):
            raise XASError("normalized XANES energy contradicts retained source energy")
        if not np.allclose(
            np.asarray(self.normalized.y),
            expected_norm,
            rtol=1e-12,
            atol=1e-12,
        ):
            raise XASError("normalized XANES values contradict retained fit state")
        if _semantic_token(self.normalized.y_axis.name) not in _NORMALIZED_MU_NAMES:
            raise XASError("normalized result must use normalized_mu semantics")
        if self.normalized.metadata.get("xas_source_digest") != source_digest:
            raise XASError("normalized XANES provenance contradicts source_digest")

        object.__setattr__(self, "source_key", source_key)
        object.__setattr__(self, "source_digest", source_digest)
        object.__setattr__(self, "source_energy_ev", energy)
        object.__setattr__(self, "source_mu", mu)
        object.__setattr__(self, "e0_ev", spec.e0_ev)
        object.__setattr__(self, "pre_edge_coefficients", pre_coeff)
        object.__setattr__(self, "post_edge_coefficients", post_coeff)
        object.__setattr__(self, "pre_edge_curve", pre_curve)
        object.__setattr__(self, "post_edge_curve", post_curve)
        object.__setattr__(self, "edge_step", edge_step)

    def equals(self, other: object) -> bool:
        return (
            isinstance(other, XANESNormalizationResult)
            and self.source_key == other.source_key
            and self.source_digest == other.source_digest
            and np.array_equal(self.source_energy_ev, other.source_energy_ev)
            and np.array_equal(self.source_mu, other.source_mu)
            and self.e0_ev == other.e0_ev
            and self.pre_edge == other.pre_edge
            and self.post_edge == other.post_edge
            and self.pre_edge_order == other.pre_edge_order
            and self.post_edge_order == other.post_edge_order
            and np.array_equal(
                self.pre_edge_coefficients,
                other.pre_edge_coefficients,
            )
            and np.array_equal(
                self.post_edge_coefficients,
                other.post_edge_coefficients,
            )
            and np.array_equal(self.pre_edge_curve, other.pre_edge_curve)
            and np.array_equal(self.post_edge_curve, other.post_edge_curve)
            and self.edge_step == other.edge_step
            and self.normalized.equals(other.normalized)
        )

    def __eq__(self, other: object) -> bool:
        return self.equals(other)


def shift_xas_energy(
    series: Series,
    shift_ev: float,
    *,
    reference: str | None = None,
) -> Series:
    """Apply the explicit additive correction ``E_corrected = E_source + shift_ev``."""
    validate_xas_series(series)
    shift = _finite_float(shift_ev, name="shift_ev")
    metadata = series.metadata_dict()
    history = _processing_history(metadata)
    step: dict[str, Any] = {"operation": "xas.energy_shift", "shift_ev": shift}
    if reference is not None:
        reference_text = str(reference).strip()
        if not reference_text:
            raise XASError("reference must not be blank when supplied")
        step["reference"] = reference_text
        metadata["energy_reference"] = reference_text
    history.append(step)
    metadata["processing_history"] = history
    cumulative = _finite_float(
        metadata.get("xas_energy_shift_ev", 0.0),
        name="existing xas_energy_shift_ev",
    )
    metadata["xas_energy_shift_ev"] = cumulative + shift
    return Series(
        x=np.asarray(series.x, dtype=np.float64) + shift,
        y=series.y,
        label=series.label,
        key=series.key,
        x_axis=Axis(
            "energy",
            unit="eV",
            label=series.x_axis.label,
            metadata=series.x_axis.metadata_dict(),
        ),
        y_axis=series.y_axis,
        metadata=metadata,
    )


def normalize_xanes(
    series: Series,
    spec: XANESNormalizationSpec,
) -> XANESNormalizationResult:
    """Normalize XANES using explicit centered pre/post-edge polynomial fits."""
    if not isinstance(spec, XANESNormalizationSpec):
        raise TypeError("spec must be a XANESNormalizationSpec")
    validate_xas_series(series)
    if _semantic_token(series.y_axis.name) not in _MU_NAMES:
        raise XASError("normalize_xanes requires unnormalized mu/absorption input")
    energy, mu = _validate_numeric_series(series)
    low = float(np.min(energy))
    high = float(np.max(energy))
    if not low < spec.e0_ev < high:
        raise XASError("E0 must lie strictly inside the measured energy range")
    for name, window in (("pre-edge", spec.pre_edge), ("post-edge", spec.post_edge)):
        if window.start_ev < low or window.end_ev > high:
            raise XASError(f"{name} window must lie inside the measured energy range")

    pre_coeff = _fit_centered_polynomial(
        energy,
        mu,
        window=spec.pre_edge,
        e0_ev=spec.e0_ev,
        order=spec.pre_edge_order,
        name="pre-edge",
    )
    post_coeff = _fit_centered_polynomial(
        energy,
        mu,
        window=spec.post_edge,
        e0_ev=spec.e0_ev,
        order=spec.post_edge_order,
        name="post-edge",
    )
    delta_energy = energy - spec.e0_ev
    pre_curve = _evaluate_polynomial(pre_coeff, delta_energy)
    post_curve = _evaluate_polynomial(post_coeff, delta_energy)
    edge_step = float(post_coeff[0] - pre_coeff[0])
    if not isfinite(edge_step) or edge_step <= 0.0:
        raise XASError("XANES edge step must be positive and finite")
    normalized_y = (mu - pre_curve) / edge_step
    if not np.isfinite(normalized_y).all():
        raise XASError("XANES normalization produced non-finite values")

    source_digest = _source_digest(series.key, energy, mu)
    metadata = series.metadata_dict()
    history = _processing_history(metadata)
    history.append(
        {
            "operation": "xas.xanes_normalize",
            "e0_ev": spec.e0_ev,
            "pre_edge_ev": [spec.pre_edge.start_ev, spec.pre_edge.end_ev],
            "post_edge_ev": [spec.post_edge.start_ev, spec.post_edge.end_ev],
            "pre_edge_order": spec.pre_edge_order,
            "post_edge_order": spec.post_edge_order,
            "edge_step": edge_step,
        }
    )
    metadata["processing_history"] = history
    metadata["xas_e0_ev"] = spec.e0_ev
    metadata["xas_source_digest"] = source_digest
    normalized = Series(
        x=energy,
        y=normalized_y,
        label=series.label,
        key=series.key,
        x_axis=Axis(
            "energy",
            unit="eV",
            label=series.x_axis.label,
            metadata=series.x_axis.metadata_dict(),
        ),
        y_axis=Axis("normalized_mu", unit="1", label="Normalized absorption"),
        metadata=metadata,
    )
    return XANESNormalizationResult(
        source_key=series.key,
        source_digest=source_digest,
        source_energy_ev=energy,
        source_mu=mu,
        e0_ev=spec.e0_ev,
        pre_edge=spec.pre_edge,
        post_edge=spec.post_edge,
        pre_edge_order=spec.pre_edge_order,
        post_edge_order=spec.post_edge_order,
        pre_edge_coefficients=pre_coeff,
        post_edge_coefficients=post_coeff,
        pre_edge_curve=pre_curve,
        post_edge_curve=post_curve,
        edge_step=edge_step,
        normalized=normalized,
    )


def xanes_relative_energy(result: XANESNormalizationResult) -> Series:
    """Return an explicit normalized XANES trace on ``E - E0`` in eV."""
    if not isinstance(result, XANESNormalizationResult):
        raise TypeError("result must be a XANESNormalizationResult")
    metadata = result.normalized.metadata_dict()
    history = _processing_history(metadata)
    history.append({"operation": "xas.relative_energy", "e0_ev": result.e0_ev})
    metadata["processing_history"] = history
    return Series(
        x=np.asarray(result.source_energy_ev) - result.e0_ev,
        y=result.normalized.y,
        label=result.normalized.label,
        key=result.normalized.key,
        x_axis=Axis(
            "energy_relative_to_e0",
            unit="eV",
            label="Energy - E0",
            metadata={"reference": "E0", "e0_ev": result.e0_ev},
        ),
        y_axis=result.normalized.y_axis,
        metadata=metadata,
    )


__all__ = [
    "XANESNormalizationResult",
    "XANESNormalizationSpec",
    "XASError",
    "XASWindow",
    "normalize_xanes",
    "shift_xas_energy",
    "validate_xas_series",
    "xanes_relative_energy",
]
