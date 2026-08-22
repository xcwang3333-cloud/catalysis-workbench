"""Experimental characterization processing and publication adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .xrd import (
    PeakAnnotation,
    XRDError,
    XRDProcessingConfig,
    XRDReferencePattern,
    process_xrd,
    process_xrd_dataset,
    stack_xrd_dataset,
    validate_xrd_series,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from catalysis_workbench.core import Dataset, Series
    from catalysis_workbench.visualization import FigureSpec


def plot_xrd(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
    stack_step: float | None = None,
    stack_start: float = 0.0,
    peak_annotations: Sequence[PeakAnnotation] = (),
    reference_patterns: Sequence[XRDReferencePattern] = (),
    reference_base: float = 0.02,
    reference_height: float = 0.08,
    reference_gap: float = 0.03,
) -> tuple[Figure, Axes]:
    """Lazily dispatch to the shared-renderer XRD publication adapter."""
    from .plotting import plot_xrd as _plot_xrd

    return _plot_xrd(
        data,
        spec,
        preset=preset,
        stack_step=stack_step,
        stack_start=stack_start,
        peak_annotations=peak_annotations,
        reference_patterns=reference_patterns,
        reference_base=reference_base,
        reference_height=reference_height,
        reference_gap=reference_gap,
    )


__all__ = [
    "PeakAnnotation",
    "XRDError",
    "XRDProcessingConfig",
    "XRDReferencePattern",
    "plot_xrd",
    "process_xrd",
    "process_xrd_dataset",
    "stack_xrd_dataset",
    "validate_xrd_series",
]
