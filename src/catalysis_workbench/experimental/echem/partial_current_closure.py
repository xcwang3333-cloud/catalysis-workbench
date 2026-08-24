"""Closure QA for partial current density calculations.

This module reports agreement between measured total current density and the
sum of product partial currents. It never rescales, normalizes, or corrects
experimental values.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


class PartialCurrentClosureError(ValueError):
    """Raised when closure inputs violate the scientific contract."""


@dataclass(frozen=True)
class PartialCurrentClosureResult:
    """Immutable result of partial current closure evaluation."""

    total_current_density: np.ndarray
    summed_partial_current_density: np.ndarray
    absolute_error: np.ndarray
    relative_error: np.ndarray
    tolerance: float
    passed: np.ndarray


def partial_current_closure(
    total_current_density: object,
    partial_current_densities: object,
    *,
    tolerance: float = 0.05,
) -> PartialCurrentClosureResult:
    """Evaluate partial-current closure without modifying input values.

    Parameters
    ----------
    total_current_density:
        Experimental total current density.
    partial_current_densities:
        Product partial current densities. The first axis is interpreted as
        products and remaining axes must match ``total_current_density``.
    tolerance:
        Relative error threshold used only for pass/fail reporting.
    """

    if isinstance(tolerance, bool) or tolerance < 0:
        raise PartialCurrentClosureError("tolerance must be a non-negative number")

    total = np.asarray(total_current_density, dtype=float)
    partial = np.asarray(partial_current_densities, dtype=float)

    if total.ndim == 0:
        total = total.reshape(1)
    if partial.ndim < 2:
        raise PartialCurrentClosureError(
            "partial_current_densities must contain a product axis"
        )
    if partial.shape[1:] != total.shape:
        raise PartialCurrentClosureError("incompatible closure shapes")

    summed = np.sum(partial, axis=0)
    absolute = summed - total
    denominator = np.where(np.abs(total) > 0, np.abs(total), np.nan)
    relative = np.abs(absolute) / denominator
    passed = np.nan_to_num(relative, nan=np.inf) <= tolerance

    return PartialCurrentClosureResult(
        total_current_density=total,
        summed_partial_current_density=summed,
        absolute_error=absolute,
        relative_error=relative,
        tolerance=float(tolerance),
        passed=passed,
    )


__all__ = [
    "PartialCurrentClosureError",
    "PartialCurrentClosureResult",
    "partial_current_closure",
]
