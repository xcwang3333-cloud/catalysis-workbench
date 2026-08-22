"""Publication-quality visualization for CatalysisWorkbench results."""

from .curves import format_axis_label, render_curves
from .export import export_figure
from .presets import get_preset, list_presets, register_preset
from .specs import (
    AnnotationSpec,
    ExportSpec,
    FigureSpec,
    LayoutSpec,
    PlotStyle,
    SeriesStyle,
    VisualizationError,
)

__all__ = [
    "AnnotationSpec",
    "ExportSpec",
    "FigureSpec",
    "LayoutSpec",
    "PlotStyle",
    "SeriesStyle",
    "VisualizationError",
    "export_figure",
    "format_axis_label",
    "get_preset",
    "list_presets",
    "register_preset",
    "render_curves",
]
