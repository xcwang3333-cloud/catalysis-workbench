"""Reusable numerical processing primitives for scientific data."""

from .xy import (
    IntegrationResult,
    ProcessingError,
    crop,
    integrate,
    interpolate,
    map_dataset,
    normalize,
    offset,
    savgol,
    subtract_baseline,
)

__all__ = [
    "IntegrationResult",
    "ProcessingError",
    "crop",
    "integrate",
    "interpolate",
    "map_dataset",
    "normalize",
    "offset",
    "savgol",
    "subtract_baseline",
]
