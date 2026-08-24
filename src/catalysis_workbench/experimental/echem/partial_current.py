"""Product partial-current calculations with explicit FE and sign conventions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray


class PartialCurrentDensityError(ValueError):
    """Raised when partial-current inputs violate the scientific contract."""


SignMode = Literal["signed", "magnitude"]
FaradaicEfficiencyInputUnit = Literal["fraction", "%"]


def _immutable_float_array(values: ArrayLike, *, name: str) -> NDArray[np.float64]:
    try:
        source = np.asarray(values)
    except (TypeError, ValueError) as exc:
        raise PartialCurrentDensityError(f"{name} must contain real numeric values") from exc
    if source.size == 0:
        raise PartialCurrentDensityError(f"{name} must contain at least one value")
    if np.iscomplexobj(source) or source.dtype.kind not in "iuf":
        raise PartialCurrentDensityError(f"{name} must contain real numeric values")
    normalized = np.ascontiguousarray(source, dtype=np.float64)
    if not np.isfinite(normalized).all():
        raise PartialCurrentDensityError(f"{name} must contain only finite values")
    buffer = normalized.tobytes(order="C")
    result = np.frombuffer(buffer, dtype=np.float64, count=normalized.size)
    result = result.reshape(normalized.shape)
    result.setflags(write=False)
    return result


def _normalize_fe_unit(unit: object) -> FaradaicEfficiencyInputUnit:
    if unit == "fraction":
        return "fraction"
    if unit == "%":
        return "%"
    raise PartialCurrentDensityError("fe_unit must be 'fraction' or '%'")


def _normalize_sign_mode(mode: object) -> SignMode:
    if mode == "signed":
        return "signed"
    if mode == "magnitude":
        return "magnitude"
    raise PartialCurrentDensityError("sign_mode must be 'signed' or 'magnitude'")


@dataclass(frozen=True, slots=True, eq=False)
class PartialCurrentDensityResult:
    """Immutable canonical inputs for ``j_product = FE * j_total``.

    ``total_current_density`` retains the caller's current-density numeric basis and
    signed values. ``fe_fraction`` is dimensionless and is never clipped at unity.
    ``values`` is derived from those two arrays according to ``sign_mode``.
    """

    total_current_density: ArrayLike
    fe_fraction: ArrayLike
    sign_mode: SignMode = "signed"

    def __post_init__(self) -> None:
        current = _immutable_float_array(
            self.total_current_density,
            name="total current density",
        )
        efficiency = _immutable_float_array(
            self.fe_fraction,
            name="Faradaic efficiency fraction",
        )
        if current.shape != efficiency.shape:
            raise PartialCurrentDensityError(
                "total current density and FE fraction must have matching shapes"
            )
        if (efficiency < 0.0).any():
            raise PartialCurrentDensityError("Faradaic efficiency cannot be negative")
        mode = _normalize_sign_mode(self.sign_mode)
        object.__setattr__(self, "total_current_density", current)
        object.__setattr__(self, "fe_fraction", efficiency)
        object.__setattr__(self, "sign_mode", mode)

    @property
    def values(self) -> NDArray[np.float64]:
        """Return product partial current density without clipping or renormalization."""
        values = self.total_current_density * self.fe_fraction
        if self.sign_mode == "magnitude":
            values = np.abs(values)
        return _immutable_float_array(values, name="partial current density")

    @property
    def fe_exceeds_unity(self) -> NDArray[np.bool_]:
        """Return a point-wise QA mask; values above 100% remain visible."""
        mask = np.ascontiguousarray(self.fe_fraction > 1.0, dtype=np.bool_)
        buffer = mask.tobytes(order="C")
        result = np.frombuffer(buffer, dtype=np.bool_, count=mask.size).reshape(mask.shape)
        result.setflags(write=False)
        return result


def partial_current_density(
    total_current_density: ArrayLike | float,
    fe: ArrayLike | float,
    *,
    fe_unit: FaradaicEfficiencyInputUnit = "fraction",
    sign_mode: SignMode = "signed",
) -> PartialCurrentDensityResult:
    """Calculate product partial current density from total current density and FE.

    The numerical relation is ``j_product = FE_fraction * j_total``. The function is
    deliberately unit-agnostic because multiplication by a dimensionless FE preserves
    the caller's current-density unit. Series-level adapters validate that the unit is
    an explicitly supported current-density unit.
    """
    current = _immutable_float_array(
        total_current_density,
        name="total current density",
    )
    efficiency = _immutable_float_array(fe, name="Faradaic efficiency")
    resolved_unit = _normalize_fe_unit(fe_unit)
    mode = _normalize_sign_mode(sign_mode)
    if resolved_unit == "%":
        efficiency = _immutable_float_array(
            efficiency / 100.0,
            name="Faradaic efficiency fraction",
        )
    if (efficiency < 0.0).any():
        raise PartialCurrentDensityError("Faradaic efficiency cannot be negative")

    try:
        current_broadcast, efficiency_broadcast = np.broadcast_arrays(current, efficiency)
    except ValueError as exc:
        raise PartialCurrentDensityError(
            "total current density and FE must have broadcast-compatible shapes"
        ) from exc

    return PartialCurrentDensityResult(
        total_current_density=current_broadcast,
        fe_fraction=efficiency_broadcast,
        sign_mode=mode,
    )


__all__ = [
    "FaradaicEfficiencyInputUnit",
    "PartialCurrentDensityError",
    "PartialCurrentDensityResult",
    "SignMode",
    "partial_current_density",
]
