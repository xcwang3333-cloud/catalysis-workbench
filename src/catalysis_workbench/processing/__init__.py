"""Reusable numerical processing primitives for scientific data."""

from .peak_fitting import (
    FitParameterSpec,
    FittedParameter,
    PeakComponentSpec,
    PeakFitResult,
    PeakFitSpec,
    PeakFittingError,
    fit_peaks,
)
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
