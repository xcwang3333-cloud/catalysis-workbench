"""Explicit, renderer-independent color-scale helpers."""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import ArrayLike

from .specs import VisualizationError


def _positive_finite(value: Any, *, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise TypeError(f"{name} must be a finite positive float") from exc
    if not np.isfinite(number) or number <= 0.0:
        raise VisualizationError(f"{name} must be finite and strictly positive")
    return number


def symmetric_color_limits(
    values: ArrayLike,
    *,
    zero_half_range: float = 1.0,
) -> tuple[float, float]:
    """Return explicit display limits symmetric around zero.

    Nonzero input uses the largest retained absolute value exactly. All-zero input
    uses the caller-visible ``zero_half_range`` so the returned interval remains
    non-degenerate.
    """
    fallback = _positive_finite(zero_half_range, name="zero_half_range")
    try:
        candidate = np.asarray(values)
    except (TypeError, ValueError, OverflowError) as exc:
        raise TypeError("values must be a real numeric array-like") from exc
    if np.iscomplexobj(candidate) or (
        candidate.dtype.kind == "O"
        and any(np.iscomplexobj(item) for item in candidate.flat)
    ):
        raise VisualizationError("values must be real, not complex")
    try:
        numeric = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        raise TypeError("values must be a real numeric array-like") from exc
    if numeric.size == 0:
        raise VisualizationError("values must not be empty")
    if not np.all(np.isfinite(numeric)):
        raise VisualizationError("values must contain only finite values")

    half_range = float(np.max(np.abs(numeric)))
    if half_range == 0.0:
        half_range = fallback
    return (-half_range, half_range)


__all__ = ["symmetric_color_limits"]
