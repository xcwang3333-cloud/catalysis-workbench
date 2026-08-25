"""Technique-level volumetric scenes and exact source-slice rendering."""

from __future__ import annotations

from math import isfinite

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from catalysis_workbench.computation import (
    ChargeDensityDifferenceResult,
    ScalarField,
    ScalarFieldSlice,
    VolumetricGrid,
    scalar_field_from_charge_density_difference,
    scalar_field_from_volumetric_grid,
)

from ._rendering import figure_axes_context, finalize_axes
from .presets import get_preset
from .specs import FigureSpec, VisualizationError
from .volumetric import (
    IsosurfaceLayerSpec,
    SliceLayerSpec,
    VolumetricScene,
    VolumetricSceneError,
)


def _finite(value: object, *, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a finite float") from exc
    if not isfinite(number):
        raise VolumetricSceneError(f"{name} must be finite")
    return number


def _positive(value: object, *, name: str) -> float:
    number = _finite(value, name=name)
    if number <= 0.0:
        raise VolumetricSceneError(f"{name} must be strictly positive")
    return number


def build_charge_density_difference_scene(
    result: ChargeDensityDifferenceResult,
    *,
    positive_threshold: float,
    negative_threshold: float,
    positive_color: str = "#D95F02",
    negative_color: str = "#1B9E77",
    opacity: float = 0.55,
) -> VolumetricScene:
    """Build explicit positive/negative layers from an existing difference result."""
    if not isinstance(result, ChargeDensityDifferenceResult):
        raise TypeError("result must be a ChargeDensityDifferenceResult")
    positive = _positive(positive_threshold, name="positive_threshold")
    negative = _finite(negative_threshold, name="negative_threshold")
    if negative >= 0.0:
        raise VolumetricSceneError("negative_threshold must be strictly negative")

    scalar_field = scalar_field_from_charge_density_difference(result)
    return VolumetricScene(
        layers=(
            IsosurfaceLayerSpec(
                scalar_field=scalar_field,
                threshold=positive,
                color=positive_color,
                opacity=opacity,
                label="charge accumulation",
            ),
            IsosurfaceLayerSpec(
                scalar_field=scalar_field,
                threshold=negative,
                color=negative_color,
                opacity=opacity,
                label="charge depletion",
            ),
        )
    )


def build_symmetric_charge_density_difference_scene(
    result: ChargeDensityDifferenceResult,
    *,
    magnitude: float,
    positive_color: str = "#D95F02",
    negative_color: str = "#1B9E77",
    opacity: float = 0.55,
) -> VolumetricScene:
    """Build signed layers from one explicit positive caller-supplied magnitude."""
    retained = _positive(magnitude, name="magnitude")
    return build_charge_density_difference_scene(
        result,
        positive_threshold=retained,
        negative_threshold=-retained,
        positive_color=positive_color,
        negative_color=negative_color,
        opacity=opacity,
    )


def build_electron_density_scene(
    grid: VolumetricGrid,
    *,
    threshold: float,
    registration_id: str | None = None,
    color: str = "#4C78A8",
    opacity: float = 0.55,
) -> VolumetricScene:
    """Build one explicit total-electron-density isosurface layer."""
    if not isinstance(grid, VolumetricGrid):
        raise TypeError("grid must be a VolumetricGrid")
    if "total" not in grid.components:
        raise VolumetricSceneError(
            "electron-density visualization requires the explicit 'total' component"
        )
    retained_threshold = _finite(threshold, name="threshold")
    scalar_field = scalar_field_from_volumetric_grid(
        grid,
        "total",
        field_kind="electron-density",
        registration_id=registration_id,
        source_key="electron-density:total",
    )
    return VolumetricScene(
        layers=(
            IsosurfaceLayerSpec(
                scalar_field=scalar_field,
                threshold=retained_threshold,
                color=color,
                opacity=opacity,
                label="electron density",
            ),
        )
    )


def build_elf_scene(
    scalar_field: ScalarField,
    *,
    threshold: float,
    color: str = "#7A5195",
    opacity: float = 0.55,
) -> VolumetricScene:
    """Build one explicit ELF isosurface layer from an already-selected channel."""
    if not isinstance(scalar_field, ScalarField):
        raise TypeError("scalar_field must be a ScalarField")
    if scalar_field.value_unit != "dimensionless":
        raise VolumetricSceneError("ELF visualization requires dimensionless values")
    if scalar_field.field_kind not in {"elf", "elf-spin-up", "elf-spin-down"}:
        raise VolumetricSceneError(
            "ELF visualization requires an explicit ELF field_kind"
        )
    retained_threshold = _finite(threshold, name="threshold")
    return VolumetricScene(
        layers=(
            IsosurfaceLayerSpec(
                scalar_field=scalar_field,
                threshold=retained_threshold,
                color=color,
                opacity=opacity,
                label="ELF",
            ),
        )
    )


def _slice_edge_grid_fractional(
    scalar_slice: ScalarFieldSlice,
) -> tuple[np.ndarray, np.ndarray]:
    first_axis, second_axis = scalar_slice.in_plane_axes
    first = np.arange(scalar_slice.grid_shape[first_axis] + 1, dtype=np.float64)
    second = np.arange(scalar_slice.grid_shape[second_axis] + 1, dtype=np.float64)
    first /= scalar_slice.grid_shape[first_axis]
    second /= scalar_slice.grid_shape[second_axis]
    return np.meshgrid(first, second, indexing="ij")


def _intrinsic_plane_edges_angstrom(
    scalar_slice: ScalarFieldSlice,
) -> tuple[np.ndarray, np.ndarray]:
    first_fractional, second_fractional = _slice_edge_grid_fractional(scalar_slice)
    first_axis, second_axis = scalar_slice.in_plane_axes
    lattice = np.asarray(scalar_slice.lattice_angstrom, dtype=np.float64)
    first_vector = lattice[first_axis]
    second_vector = lattice[second_axis]

    first_norm = float(np.linalg.norm(first_vector))
    if not isfinite(first_norm) or first_norm <= 0.0:
        raise VolumetricSceneError("first in-plane lattice vector must be nonzero")
    e1 = first_vector / first_norm
    second_x = float(np.dot(second_vector, e1))
    perpendicular = second_vector - second_x * e1
    second_y = float(np.linalg.norm(perpendicular))
    if not isfinite(second_y) or second_y <= 0.0:
        raise VolumetricSceneError(
            "in-plane lattice vectors must define a non-degenerate plane"
        )

    x = first_fractional * first_norm + second_fractional * second_x
    y = second_fractional * second_y
    return x, y


def _slice_plot_coordinates(
    scalar_slice: ScalarFieldSlice,
    *,
    coordinate_mode: str,
) -> tuple[np.ndarray, np.ndarray, str, str]:
    mode = str(coordinate_mode).strip().lower()
    if mode == "angstrom":
        x, y = _intrinsic_plane_edges_angstrom(scalar_slice)
        return x, y, "In-plane coordinate 1 (Å)", "In-plane coordinate 2 (Å)"
    if mode == "fractional":
        x, y = _slice_edge_grid_fractional(scalar_slice)
        return x, y, "In-plane fractional coordinate 1", "In-plane fractional coordinate 2"
    raise VisualizationError("coordinate_mode must be 'angstrom' or 'fractional'")


def plot_scalar_field_slice(
    layer: SliceLayerSpec,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
    coordinate_mode: str = "angstrom",
    show_colorbar: bool = True,
) -> tuple[Figure, Axes]:
    """Render exact retained slice values as flat source-grid cells."""
    if not isinstance(layer, SliceLayerSpec):
        raise TypeError("layer must be a SliceLayerSpec")
    if not layer.visible:
        raise VisualizationError("cannot render a SliceLayerSpec with visible=False")
    if layer.value_min is None or layer.value_max is None:
        raise VisualizationError(
            "slice rendering requires explicit value_min and value_max; "
            "automatic display-range inference is not performed"
        )

    resolved_spec = get_preset(preset) if spec is None else spec
    if not isinstance(resolved_spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")
    if resolved_spec.xscale != "linear" or resolved_spec.yscale != "linear":
        raise VisualizationError("scalar-field slices require linear x and y scales")

    scalar_slice = layer.scalar_slice
    before = np.array(scalar_slice.values, copy=True)
    x, y, default_xlabel, default_ylabel = _slice_plot_coordinates(
        scalar_slice,
        coordinate_mode=coordinate_mode,
    )

    with figure_axes_context(resolved_spec) as (figure, ax):
        mesh = ax.pcolormesh(
            x,
            y,
            scalar_slice.values,
            shading="flat",
            cmap=layer.colormap,
            vmin=layer.value_min,
            vmax=layer.value_max,
            alpha=layer.opacity,
        )
        ax.set_aspect("equal", adjustable="box")
        finalize_axes(
            ax,
            resolved_spec,
            xlabel=(
                default_xlabel
                if resolved_spec.xlabel is None
                else resolved_spec.xlabel
            ),
            ylabel=(
                default_ylabel
                if resolved_spec.ylabel is None
                else resolved_spec.ylabel
            ),
            labeled_count=0,
        )
        if show_colorbar:
            colorbar = figure.colorbar(mesh, ax=ax)
            label = layer.label or scalar_slice.field_kind
            colorbar.set_label(f"{label} ({scalar_slice.value_unit})")

    if not np.array_equal(scalar_slice.values, before):
        raise RuntimeError("slice plotting mutated retained scalar-field values")
    return figure, ax


__all__ = [
    "build_charge_density_difference_scene",
    "build_electron_density_scene",
    "build_elf_scene",
    "build_symmetric_charge_density_difference_scene",
    "plot_scalar_field_slice",
]
