"""Electrochemical data processing, analysis, and publication adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .lsv import (
    LSVError,
    LSVProcessingConfig,
    convert_potential_to_rhe,
    correct_ir_drop,
    process_lsv,
    process_lsv_dataset,
    rhe_offset_from_she,
    to_current_density,
)

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from catalysis_workbench.core import Dataset, Series
    from catalysis_workbench.visualization import FigureSpec


def plot_lsv(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Lazily dispatch to the publication LSV adapter.

    Keeping the visualization import inside the call preserves the architecture rule
    that numerical electrochemistry can be imported and used without importing
    Matplotlib/the visualization package.
    """
    from .plotting import plot_lsv as _plot_lsv

    return _plot_lsv(data, spec, preset=preset)


__all__ = [
    "LSVError",
    "LSVProcessingConfig",
    "convert_potential_to_rhe",
    "correct_ir_drop",
    "plot_lsv",
    "process_lsv",
    "process_lsv_dataset",
    "rhe_offset_from_she",
    "to_current_density",
]
