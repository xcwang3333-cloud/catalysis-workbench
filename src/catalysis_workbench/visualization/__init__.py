"""Publication-quality visualization for CatalysisWorkbench results."""

from .band_structure import BandVisualizationError, plot_band_structure
from .bars import BarCategory, BarData, BarSeries, render_bars
from .curves import format_axis_label, render_curves
from .dft import plot_relative_energies
from .dos import DOSVisualizationError, plot_dos
from .export import export_figure
from .free_energy import plot_free_energy_diagram
from .neb import NEBVisualizationError, plot_neb_path
from .presets import get_preset, list_presets, register_preset
from .projected_bands import ProjectedBandVisualizationError, plot_fat_band
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
from .volumetric import (
    IsosurfaceLayerSpec,
    SliceLayerSpec,
    VolumetricLayerSpec,
    VolumetricScene,
    VolumetricSceneError,
)
from .volumetric_techniques import (
    build_charge_density_difference_scene,
    build_electron_density_scene,
    build_elf_scene,
    build_symmetric_charge_density_difference_scene,
    plot_scalar_field_slice,
)
from .work_function import WorkFunctionVisualizationError, plot_planar_potential

__all__ = [
    "AnnotationSpec",
    "BandVisualizationError",
    "BarCategory",
    "BarData",
    "BarSeries",
    "CategoryStyle",
    "DOSVisualizationError",
    "ExportSpec",
    "FigureSpec",
    "IsosurfaceLayerSpec",
    "LayoutSpec",
    "NEBVisualizationError",
    "PlotStyle",
    "ProjectedBandVisualizationError",
    "ScatterError",
    "SeriesStyle",
    "SliceLayerSpec",
    "VisualizationError",
    "VolumetricLayerSpec",
    "VolumetricScene",
    "VolumetricSceneError",
    "WorkFunctionVisualizationError",
    "build_charge_density_difference_scene",
    "build_electron_density_scene",
    "build_elf_scene",
    "build_symmetric_charge_density_difference_scene",
    "export_figure",
    "format_axis_label",
    "get_preset",
    "list_presets",
    "plot_band_structure",
    "plot_dos",
    "plot_fat_band",
    "plot_free_energy_diagram",
    "plot_neb_path",
    "plot_planar_potential",
    "plot_relative_energies",
    "plot_scalar_field_slice",
    "plot_structure",
    "register_preset",
    "render_bars",
    "render_curves",
    "render_scatter",
]
