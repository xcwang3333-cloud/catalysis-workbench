"""Passive fat-band rendering for explicit aggregated projection state."""

from __future__ import annotations

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from catalysis_workbench.computation.band_structure import (
    BandStructureError,
    band_path_coordinates,
)
from catalysis_workbench.computation.projected_bands import AggregatedBandProjection

from ._rendering import figure_axes_context, finalize_axes
from .band_structure import _fermi_marker_position, _path_ticks
from .presets import get_preset
from .specs import FigureSpec, VisualizationError


class ProjectedBandVisualizationError(VisualizationError):
    """Raised when retained projected-band state cannot be rendered passively."""


def _finite_nonnegative(value: object, *, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a finite non-negative float") from exc
    if not np.isfinite(result) or result < 0.0:
        raise ProjectedBandVisualizationError(
            f"{name} must be a finite non-negative float"
        )
    return result


def plot_fat_band(
    projection: AggregatedBandProjection,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
    marker_area_scale: float = 36.0,
    marker: str = "o",
    alpha: float = 0.55,
    color: str | None = None,
    show_base_bands: bool = True,
    base_line_width: float = 0.7,
    show_fermi: bool = False,
    label: str | None = None,
) -> tuple[Figure, Axes]:
    """Render retained projection weight as presentation-only marker area."""
    if not isinstance(projection, AggregatedBandProjection):
        raise TypeError("projection must be an AggregatedBandProjection")

    scale = _finite_nonnegative(marker_area_scale, name="marker_area_scale")
    line_width = _finite_nonnegative(base_line_width, name="base_line_width")
    try:
        alpha_value = float(alpha)
    except (TypeError, ValueError) as exc:
        raise TypeError("alpha must be a finite float in [0, 1]") from exc
    if not np.isfinite(alpha_value) or not 0.0 <= alpha_value <= 1.0:
        raise ProjectedBandVisualizationError("alpha must be a finite float in [0, 1]")
    marker_value = str(marker).strip()
    if not marker_value:
        raise ProjectedBandVisualizationError("marker must not be blank")
    if label is not None and not str(label).strip():
        raise ProjectedBandVisualizationError("label must not be blank when supplied")

    state = projection.band_structure
    try:
        path = band_path_coordinates(state)
    except BandStructureError as exc:
        raise ProjectedBandVisualizationError(str(exc)) from exc
    resolved_spec = get_preset(preset) if spec is None else spec
    if not isinstance(resolved_spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")
    if resolved_spec.xscale != "linear" or resolved_spec.yscale != "linear":
        raise ProjectedBandVisualizationError(
            "fat-band plotting requires linear x and y scales"
        )

    channel = state.channel(projection.spin)
    if projection.weights.shape != channel.energies_ev.shape:
        raise ProjectedBandVisualizationError(
            "aggregated projection weights must align exactly with retained band energies"
        )

    kpoints_before = np.array(state.kpoints_fractional, copy=True)
    energies_before = np.array(channel.energies_ev, copy=True)
    weights_before = np.array(projection.weights, copy=True)
    state_digest_before = state.digest
    projection_digest_before = projection.digest
    fermi_position = _fermi_marker_position(state) if show_fermi else None
    render_color = "C0" if color is None else color

    with figure_axes_context(resolved_spec) as (figure, ax):
        labeled = False
        for segment in path.segments:
            indices = np.asarray(segment.source_indices, dtype=np.int64)
            x = segment.distances
            for band_index, energies in enumerate(channel.energies_ev):
                y = energies[indices]
                if show_base_bands:
                    ax.plot(
                        x,
                        y,
                        color=render_color,
                        linewidth=line_width,
                        label="_nolegend_",
                    )
                scatter_label = (
                    str(label)
                    if label is not None and not labeled
                    else "_nolegend_"
                )
                ax.scatter(
                    x,
                    y,
                    s=projection.weights[band_index, indices] * scale,
                    marker=marker_value,
                    alpha=alpha_value,
                    color=render_color,
                    label=scatter_label,
                )
                if label is not None:
                    labeled = True

        if fermi_position is not None:
            ax.axhline(
                fermi_position,
                linestyle="--",
                linewidth=1.0,
                label="_nolegend_",
            )

        xlabel = f"Reciprocal path distance ({path.reciprocal_unit})"
        ylabel = (
            "Energy - E_F (eV)"
            if state.reference_kind == "fermi"
            else "Energy (eV, source-native)"
        )
        finalize_axes(
            ax,
            resolved_spec,
            xlabel=xlabel,
            ylabel=ylabel,
            labeled_count=1 if label is not None else 0,
        )
        positions, labels = _path_ticks(path)
        if positions:
            ax.set_xticks(positions, labels)

    if not np.array_equal(state.kpoints_fractional, kpoints_before):
        raise RuntimeError("fat-band plotting mutated retained k-point state")
    if not np.array_equal(channel.energies_ev, energies_before):
        raise RuntimeError("fat-band plotting mutated retained band-energy state")
    if not np.array_equal(projection.weights, weights_before):
        raise RuntimeError("fat-band plotting mutated retained projection-weight state")
    if state.digest != state_digest_before or projection.digest != projection_digest_before:
        raise RuntimeError("fat-band plotting mutated retained scientific identity")
    return figure, ax


__all__ = ["ProjectedBandVisualizationError", "plot_fat_band"]
