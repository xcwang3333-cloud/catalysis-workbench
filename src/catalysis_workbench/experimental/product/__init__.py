"""Technique-agnostic product calibration and sample quantification."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .calibration import (
    CalibrationFitResult,
    CalibrationInterceptPolicy,
    CalibrationRange,
    ProductCalibrationError,
    QuantificationFactor,
    QuantificationResult,
    QuantificationSummary,
    fit_calibration,
    quantify_response,
    summarize_quantification_replicates,
)

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from catalysis_workbench.visualization import FigureSpec


def plot_calibration(
    result: CalibrationFitResult,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Lazily render an already-computed product calibration fit."""
    from .plotting import plot_calibration as _plot_calibration

    return _plot_calibration(result, spec, preset=preset)


__all__ = [
    "CalibrationFitResult",
    "CalibrationInterceptPolicy",
    "CalibrationRange",
    "ProductCalibrationError",
    "QuantificationFactor",
    "QuantificationResult",
    "QuantificationSummary",
    "fit_calibration",
    "plot_calibration",
    "quantify_response",
    "summarize_quantification_replicates",
]
