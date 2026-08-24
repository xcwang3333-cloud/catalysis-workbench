"""Reusable numerical processing primitives for scientific data."""

from __future__ import annotations

from importlib import import_module
from typing import Any

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

_PEAK_FITTING_EXPORTS = frozenset(
    {
        "FitParameterSpec",
        "FittedParameter",
        "PeakComponentSpec",
        "PeakFitResult",
        "PeakFitSpec",
        "PeakFittingError",
        "fit_peaks",
    }
)


def __getattr__(name: str) -> Any:
    """Lazily expose the lmfit-backed API without loading it for XY consumers."""
    if name not in _PEAK_FITTING_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(".peak_fitting", __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | _PEAK_FITTING_EXPORTS)


__all__ = [
    "FitParameterSpec",
    "FittedParameter",
    "IntegrationResult",
    "PeakComponentSpec",
    "PeakFitResult",
    "PeakFitSpec",
    "PeakFittingError",
    "ProcessingError",
    "crop",
    "fit_peaks",
    "integrate",
    "interpolate",
    "map_dataset",
    "normalize",
    "offset",
    "savgol",
    "subtract_baseline",
]
