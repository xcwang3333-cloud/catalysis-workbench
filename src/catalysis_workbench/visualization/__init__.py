"""Publication-quality visualization for CatalysisWorkbench results.

The top-level visualization namespace is intentionally lazy so importing numerical or
application layers does not initialize Matplotlib presentation backends. Public names
and ``__all__`` remain unchanged; each implementation module is loaded on first access.
"""

from __future__ import annotations

from importlib import import_module

_EXPORTS = {
    "AnnotationSpec": (".specs", "AnnotationSpec"),
    "AntiAliasingMode": (".volumetric_3d", "AntiAliasingMode"),
    "BandVisualizationError": (".band_structure", "BandVisualizationError"),
    "BarCategory": (".bars", "BarCategory"),
    "BarData": (".bars", "BarData"),
    "BarSeries": (".bars", "BarSeries"),
    "CategoryStyle": (".specs", "CategoryStyle"),
    "DOSVisualizationError": (".dos", "DOSVisualizationError"),
    "ExportSpec": (".specs", "ExportSpec"),
    "FigureEditorState": (".editor", "FigureEditorState"),
    "FigurePresetBundle": (".preset_bundles", "FigurePresetBundle"),
    "FigurePresetEntry": (".preset_bundles", "FigurePresetEntry"),
    "FigureSpec": (".specs", "FigureSpec"),
    "FigureSpecEditorController": (".editor", "FigureSpecEditorController"),
    "IsosurfaceLayerSpec": (".volumetric", "IsosurfaceLayerSpec"),
    "LayoutSpec": (".specs", "LayoutSpec"),
    "NEBVisualizationError": (".neb", "NEBVisualizationError"),
    "PlotStyle": (".specs", "PlotStyle"),
    "ProjectedBandVisualizationError": (
        ".projected_bands",
        "ProjectedBandVisualizationError",
    ),
    "ScatterError": (".scatter", "ScatterError"),
    "SeriesStyle": (".specs", "SeriesStyle"),
    "SliceLayerSpec": (".volumetric", "SliceLayerSpec"),
    "VisualizationError": (".specs", "VisualizationError"),
    "Volumetric3DBackendError": (".volumetric_3d", "Volumetric3DBackendError"),
    "Volumetric3DRenderResult": (".volumetric_3d", "Volumetric3DRenderResult"),
    "Volumetric3DRenderSpec": (".volumetric_3d", "Volumetric3DRenderSpec"),
    "Volumetric3DVisualizationError": (
        ".volumetric_3d",
        "Volumetric3DVisualizationError",
    ),
    "VolumetricLayerSpec": (".volumetric", "VolumetricLayerSpec"),
    "VolumetricScene": (".volumetric", "VolumetricScene"),
    "VolumetricSceneError": (".volumetric", "VolumetricSceneError"),
    "WorkFunctionVisualizationError": (
        ".work_function",
        "WorkFunctionVisualizationError",
    ),
    "build_charge_density_difference_scene": (
        ".volumetric_techniques",
        "build_charge_density_difference_scene",
    ),
    "build_electron_density_scene": (
        ".volumetric_techniques",
        "build_electron_density_scene",
    ),
    "build_elf_scene": (".volumetric_techniques", "build_elf_scene"),
    "build_symmetric_charge_density_difference_scene": (
        ".volumetric_techniques",
        "build_symmetric_charge_density_difference_scene",
    ),
    "export_figure": (".export", "export_figure"),
    "export_volumetric_scene_3d": (
        ".volumetric_3d",
        "export_volumetric_scene_3d",
    ),
    "format_axis_label": (".curves", "format_axis_label"),
    "get_preset": (".presets", "get_preset"),
    "install_preset_bundle": (".preset_bundles", "install_preset_bundle"),
    "list_presets": (".presets", "list_presets"),
    "load_preset_bundle": (".preset_bundles", "load_preset_bundle"),
    "open_figure_spec_editor": (".editor", "open_figure_spec_editor"),
    "plot_band_structure": (".band_structure", "plot_band_structure"),
    "plot_dos": (".dos", "plot_dos"),
    "plot_fat_band": (".projected_bands", "plot_fat_band"),
    "plot_free_energy_diagram": (".free_energy", "plot_free_energy_diagram"),
    "plot_neb_path": (".neb", "plot_neb_path"),
    "plot_planar_potential": (".work_function", "plot_planar_potential"),
    "plot_relative_energies": (".dft", "plot_relative_energies"),
    "plot_scalar_field_slice": (
        ".volumetric_techniques",
        "plot_scalar_field_slice",
    ),
    "plot_structure": (".structure", "plot_structure"),
    "register_preset": (".presets", "register_preset"),
    "render_bars": (".bars", "render_bars"),
    "render_curves": (".curves", "render_curves"),
    "render_scatter": (".scatter", "render_scatter"),
    "render_volumetric_scene_3d": (
        ".volumetric_3d",
        "render_volumetric_scene_3d",
    ),
    "save_preset_bundle": (".preset_bundles", "save_preset_bundle"),
    "symmetric_color_limits": (".color_scales", "symmetric_color_limits"),
}

__all__ = [
    "AnnotationSpec",
    "AntiAliasingMode",
    "BandVisualizationError",
    "BarCategory",
    "BarData",
    "BarSeries",
    "CategoryStyle",
    "DOSVisualizationError",
    "ExportSpec",
    "FigureEditorState",
    "FigurePresetBundle",
    "FigurePresetEntry",
    "FigureSpec",
    "FigureSpecEditorController",
    "IsosurfaceLayerSpec",
    "LayoutSpec",
    "NEBVisualizationError",
    "PlotStyle",
    "ProjectedBandVisualizationError",
    "ScatterError",
    "SeriesStyle",
    "SliceLayerSpec",
    "VisualizationError",
    "Volumetric3DBackendError",
    "Volumetric3DRenderResult",
    "Volumetric3DRenderSpec",
    "Volumetric3DVisualizationError",
    "VolumetricLayerSpec",
    "VolumetricScene",
    "VolumetricSceneError",
    "WorkFunctionVisualizationError",
    "build_charge_density_difference_scene",
    "build_electron_density_scene",
    "build_elf_scene",
    "build_symmetric_charge_density_difference_scene",
    "export_figure",
    "export_volumetric_scene_3d",
    "format_axis_label",
    "get_preset",
    "install_preset_bundle",
    "list_presets",
    "load_preset_bundle",
    "open_figure_spec_editor",
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
    "render_volumetric_scene_3d",
    "save_preset_bundle",
    "symmetric_color_limits",
]


def __getattr__(name: str):
    try:
        module_name, attribute = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    value = getattr(import_module(module_name, __name__), attribute)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
