"""Passive publication rendering for retained band-structure state."""

from __future__ import annotations

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from catalysis_workbench.computation import (
    BandPathCoordinates,
    BandStructureError,
    BandStructureState,
    band_path_coordinates,
)

from ._rendering import figure_axes_context, finalize_axes
from .presets import get_preset
from .specs import FigureSpec, VisualizationError


class BandVisualizationError(VisualizationError):
    """Raised when retained band state cannot be rendered without inference."""


def _path_ticks(path: BandPathCoordinates) -> tuple[list[float], list[str]]:
    positions: list[float] = []
    labels: list[str] = []

    def add(position: float, label: str | None) -> None:
        if label is None:
            return
        for index, retained_position in enumerate(positions):
            if np.isclose(position, retained_position, rtol=0.0, atol=1e-12):
                existing = labels[index].split(" | ")
                if label not in existing:
                    labels[index] = labels[index] + " | " + label
                return
        positions.append(float(position))
        labels.append(label)

    for segment in path.segments:
        add(float(segment.distances[0]), segment.start_label)
        add(float(segment.distances[-1]), segment.end_label)
    return positions, labels


def _fermi_marker_position(state: BandStructureState) -> float:
    if state.reference_kind == "fermi":
        return 0.0
    if state.source_fermi_ev is None:
        raise BandVisualizationError(
            "Fermi marker requires retained source_fermi_ev"
        )
    return float(state.source_fermi_ev)


def plot_band_structure(
    state: BandStructureState,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
    show_fermi: bool = False,
) -> tuple[Figure, Axes]:
    """Render exact retained bands as segment-separated lines."""
    if not isinstance(state, BandStructureState):
        raise TypeError("state must be a BandStructureState")
    try:
        path = band_path_coordinates(state)
    except BandStructureError as exc:
        raise BandVisualizationError(str(exc)) from exc

    resolved_spec = get_preset(preset) if spec is None else spec
    if not isinstance(resolved_spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")
    if resolved_spec.xscale != "linear" or resolved_spec.yscale != "linear":
        raise BandVisualizationError(
            "band-structure plotting requires linear x and y scales"
        )

    kpoints_before = np.array(state.kpoints_fractional, copy=True)
    energies_before = tuple(
        np.array(channel.energies_ev, copy=True) for channel in state.channels
    )
    fermi_position = _fermi_marker_position(state) if show_fermi else None

    with figure_axes_context(resolved_spec) as (figure, ax):
        for channel_index, channel in enumerate(state.channels):
            color = f"C{channel_index}"
            labeled = False
            for segment in path.segments:
                indices = np.asarray(segment.source_indices, dtype=np.int64)
                x = segment.distances
                for band in channel.energies_ev:
                    label = channel.spin if not labeled else "_nolegend_"
                    ax.plot(
                        x,
                        band[indices],
                        color=color,
                        linewidth=resolved_spec.style.line_width,
                        label=label,
                    )
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
            labeled_count=len(state.channels) if len(state.channels) > 1 else 0,
        )
        positions, labels = _path_ticks(path)
        if positions:
            ax.set_xticks(positions, labels)

    if not np.array_equal(state.kpoints_fractional, kpoints_before):
        raise RuntimeError("band plotting mutated retained k-point state")
    for channel, before in zip(state.channels, energies_before, strict=True):
        if not np.array_equal(channel.energies_ev, before):
            raise RuntimeError("band plotting mutated retained energy state")
    return figure, ax


__all__ = ["BandVisualizationError", "plot_band_structure"]
