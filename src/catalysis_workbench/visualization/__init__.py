"""Publication-quality visualization for CatalysisWorkbench results."""

from .bars import BarCategory, BarData, BarSeries, render_bars
from .curves import format_axis_label, render_curves
from .dft import plot_relative_energies
from .dos import DOSVisualizationError, plot_dos
from .export import export_figure
from .free_energy import plot_free_energy_diagram
from .presets import get_preset, list_presets, register_preset
from .scatter import ScatterError, render_scatter
from .specs import (
    AnnotationSpec,
    CategoryStyle,
    ExportSpec,
    FigureSpec,
    LayoutSpec,
    PlotStyle,
    SeriesStyle,
    VisualizationError,
)
from .structure import plot_structure

__all__ = [
    "AnnotationSpec",
    "BarCategory",
    "BarData",
    "BarSeries",
    "CategoryStyle",
    "DOSVisualizationError",
    "ExportSpec",
    "FigureSpec",
    "LayoutSpec",
    "PlotStyle",
    "ScatterError",
    "SeriesStyle",
    "VisualizationError",
    "export_figure",
    "format_axis_label",
    "get_preset",
    "list_presets",
    "plot_dos",
    "plot_free_energy_diagram",
    "plot_relative_energies",
    "plot_structure",
    "register_preset",
    "render_bars",
    "render_curves",
    "render_scatter",
]
