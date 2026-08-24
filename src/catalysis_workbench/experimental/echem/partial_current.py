"""Partial current density calculations built on FE and quantity contracts.

This module intentionally keeps sign handling explicit. It does not infer
reaction products, interpolate condition grids, or renormalize partial currents.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np


class PartialCurrentDensityError(ValueError):
    """Raised when partial-current inputs violate scientific contracts."""


SignMode = Literal["signed", "magnitude"]


@dataclass(frozen=True)
class PartialCurrentDensityResult:
    """Immutable result of partial current density conversion.

    Parameters
    ----------
    values:
        Partial current density values in the requested sign convention.
    fe_fraction:
        FE values represented as fractions.
    total_current_density:
        Original total current density before sign transformation.
    sign_mode:
        Whether the output preserves sign or reports magnitude.
    """

    values: np.ndarray
    fe_fraction: np.ndarray
    total_current_density: np.ndarray
    sign_mode: SignMode


def _as_numeric_array(value: object, name: str) -> np.ndarray:
    if isinstance(value, (str, bytes, bool)):
        raise PartialCurrentDensityError(f"{name} must be numeric")
    array = np.asarray(value)
    if not np.issubdtype(array.dtype, np.number):
        raise PartialCurrentDensityError(f"{name} must be numeric")
    if not np.all(np.isfinite(array)):
        raise PartialCurrentDensityError(f"{name} contains non-finite values")
    return array.astype(float)


def partial_current_density(
    total_current_density: object,
    fe: object,
    *,
    fe_unit: Literal["fraction", "%"] = "fraction",
    sign_mode: SignMode = "signed",
) -> PartialCurrentDensityResult:
    """Calculate product partial current density from FE and total current.

    The core relation is ``j_product = FE_fraction * j_total``.
    No sign inversion, interpolation, clipping, or normalization is performed.
    """

    if sign_mode not in {"signed", "magnitude"}:
        raise PartialCurrentDensityError("unsupported sign_mode")

    current = _as_numeric_array(total_current_density, "total_current_density")
    efficiency = _as_numeric_array(fe, "fe")

    if fe_unit == "%":
        efficiency = efficiency / 100.0
    elif fe_unit != "fraction":
        raise PartialCurrentDensityError("unsupported FE unit")

    if np.any(efficiency < 0):
        raise PartialCurrentDensityError("FE cannot be negative")

    try:
        current, efficiency = np.broadcast_arrays(current, efficiency)
    except ValueError as exc:
        raise PartialCurrentDensityError("incompatible input shapes") from exc

    result = current * efficiency
    if sign_mode == "magnitude":
        result = np.abs(result)

    return PartialCurrentDensityResult(
        values=result,
        fe_fraction=efficiency,
        total_current_density=current,
        sign_mode=sign_mode,
    )


__all__ = [
    "PartialCurrentDensityError",
    "PartialCurrentDensityResult",
    "partial_current_density",
]
