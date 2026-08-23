"""Publication-quality visualization for CatalysisWorkbench results."""

from .bars import BarCategory, BarData, BarSeries, render_bars
from .curves import format_axis_label, render_curves
from .export import export_figure
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

__all__ = [
    "AnnotationSpec",
    "BarCategory",
    "BarData",
    "BarSeries",
    "CategoryStyle",
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
    "register_preset",
    "render_bars",
    "render_curves",
    "render_scatter",
]
