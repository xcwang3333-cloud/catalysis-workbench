"""Passive Matplotlib rendering for renderer-neutral atomistic structure scenes."""

from __future__ import annotations

from math import isfinite, pi
from typing import TYPE_CHECKING

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from catalysis_workbench.computation.structure_scene import (
    StructureScene,
    StructureSceneError,
)

from ._rendering import figure_context
from .presets import get_preset
from .specs import FigureSpec

if TYPE_CHECKING:
    from mpl_toolkits.mplot3d.axes3d import Axes3D


def _positive(value: float, *, name: str) -> float:
    number = float(value)
    if not isfinite(number) or number <= 0.0:
        raise StructureSceneError(f"{name} must be finite and positive")
    return number


def _scene_positions(scene: StructureScene) -> np.ndarray:
    positions = [np.asarray(atom.position_angstrom, dtype=np.float64) for atom in scene.atoms]
    for edge in scene.cell_edges_angstrom:
        positions.extend(np.asarray(point, dtype=np.float64) for point in edge)
    return np.asarray(positions, dtype=np.float64)


def _set_equal_limits(ax: Axes3D, positions: np.ndarray, *, padding_fraction: float) -> None:
    low = np.min(positions, axis=0)
    high = np.max(positions, axis=0)
    center = (low + high) / 2.0
    span = float(np.max(high - low))
    if span <= 0.0:
        span = 1.0
    half = 0.5 * span * (1.0 + 2.0 * padding_fraction)
    ax.set_xlim(center[0] - half, center[0] + half)
    ax.set_ylim(center[1] - half, center[1] + half)
    ax.set_zlim(center[2] - half, center[2] + half)
    ax.set_box_aspect((1.0, 1.0, 1.0))


def plot_structure(
    scene: StructureScene,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
    points_per_angstrom: float = 18.0,
    padding_fraction: float = 0.08,
    show_axes: bool = False,
) -> tuple[Figure, Axes]:
    """Render one immutable structure scene without recomputing scientific geometry."""
    if not isinstance(scene, StructureScene):
        raise TypeError("scene must be a StructureScene")
    marker_scale = _positive(points_per_angstrom, name="points_per_angstrom")
    padding = float(padding_fraction)
    if not isfinite(padding) or padding < 0.0:
        raise StructureSceneError("padding_fraction must be finite and non-negative")
    resolved_spec = get_preset(preset) if spec is None else spec
    if not isinstance(resolved_spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")

    atom_positions_before = [np.array(atom.position_angstrom, copy=True) for atom in scene.atoms]
    with figure_context(resolved_spec) as figure:
        ax = figure.add_axes(
            resolved_spec.layout.axes_bounds_fraction(),
            projection="3d",
        )
        figure.patch.set_facecolor(scene.background)
        ax.set_facecolor(scene.background)
        ax.set_proj_type("ortho" if scene.camera.projection == "orthographic" else "persp")
        ax.view_init(
            elev=scene.camera.elevation_degrees,
            azim=scene.camera.azimuth_degrees,
            roll=scene.camera.roll_degrees,
        )

        if scene.cell_style.visible:
            for first, second in scene.cell_edges_angstrom:
                coordinates = np.vstack((first, second))
                ax.plot(
                    coordinates[:, 0],
                    coordinates[:, 1],
                    coordinates[:, 2],
                    color=scene.cell_style.color,
                    linewidth=scene.cell_style.linewidth,
                    alpha=scene.cell_style.alpha,
                )

        for bond in scene.bonds:
            coordinates = np.vstack(
                (bond.first_position_angstrom, bond.second_position_angstrom)
            )
            ax.plot(
                coordinates[:, 0],
                coordinates[:, 1],
                coordinates[:, 2],
                color=bond.style.color,
                linewidth=bond.style.linewidth,
                alpha=bond.style.alpha,
                solid_capstyle="round",
            )

        for atom in scene.atoms:
            position = np.asarray(atom.position_angstrom, dtype=np.float64)
            radius_points = atom.style.radius_angstrom * marker_scale
            marker_area = pi * radius_points**2
            ax.scatter(
                [position[0]],
                [position[1]],
                [position[2]],
                s=marker_area,
                c=[atom.style.color],
                alpha=atom.style.alpha,
                depthshade=True,
                edgecolors="none",
            )
            if atom.label is not None:
                ax.text(
                    position[0],
                    position[1],
                    position[2],
                    atom.label,
                    fontsize=resolved_spec.style.font_size,
                    ha="center",
                    va="bottom",
                )

        positions = _scene_positions(scene)
        _set_equal_limits(ax, positions, padding_fraction=padding)
        if show_axes:
            ax.set_xlabel(resolved_spec.xlabel or "x (Å)")
            ax.set_ylabel(resolved_spec.ylabel or "y (Å)")
            ax.set_zlabel("z (Å)")
            ax.tick_params(labelsize=resolved_spec.style.tick_label_size)
        else:
            ax.set_axis_off()
        if resolved_spec.title:
            ax.set_title(resolved_spec.title, fontsize=resolved_spec.style.title_size)

        for atom, before in zip(scene.atoms, atom_positions_before, strict=True):
            if not np.array_equal(atom.position_angstrom, before):
                raise RuntimeError("structure rendering mutated retained scene state")
        return figure, ax


__all__ = ["plot_structure"]
