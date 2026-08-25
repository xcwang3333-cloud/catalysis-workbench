"""Passive plotting for retained discrete NEB image-energy paths."""

from __future__ import annotations

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import NullLocator

from catalysis_workbench.computation import (
    NEBBarrierResult,
    NEBPath,
    validate_neb_barrier_path,
)

from ._rendering import figure_axes_context, finalize_axes
from .presets import get_preset
from .specs import FigureSpec, VisualizationError


class NEBVisualizationError(VisualizationError):
    """Raised when retained NEB state cannot be rendered without ambiguity."""


def plot_neb_path(
    path: NEBPath,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
    barrier: NEBBarrierResult | None = None,
    show_saddle: bool = True,
    saddle_marker: str = "s",
) -> tuple[Figure, Axes]:
    """Plot retained NEB images with straight source-order segments only."""
    if not isinstance(path, NEBPath):
        raise TypeError("path must be an NEBPath")
    if barrier is not None:
        try:
            validate_neb_barrier_path(path, barrier)
        except ValueError as exc:
            raise NEBVisualizationError(str(exc)) from exc

    resolved_spec = get_preset(preset) if spec is None else spec
    if not isinstance(resolved_spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")
    if resolved_spec.xscale != "linear" or resolved_spec.yscale != "linear":
        raise NEBVisualizationError("NEB path plotting requires linear x and y scales")

    unknown_series = set(resolved_spec.series_styles) - {path.key}
    if unknown_series:
        raise NEBVisualizationError(
            f"series style keys are not present in the NEB path: {sorted(unknown_series)!r}"
        )
    unknown_categories = set(resolved_spec.category_styles) - set(path.image_keys)
    if unknown_categories:
        raise NEBVisualizationError(
            "category style keys are not retained NEB images: "
            f"{sorted(unknown_categories)!r}"
        )
    hidden_images = [
        key
        for key, style in resolved_spec.category_styles.items()
        if not style.visible
    ]
    if hidden_images:
        raise NEBVisualizationError(
            f"NEB rendering cannot hide retained path images: {hidden_images!r}"
        )

    series_style = resolved_spec.series_styles.get(path.key)
    if series_style is not None and not series_style.visible:
        raise NEBVisualizationError("the retained NEB path is hidden by its series style")
    marker = (
        "o"
        if series_style is None and resolved_spec.style.marker is None
        else (
            resolved_spec.style.marker
            if series_style is None or series_style.marker is None
            else series_style.marker
        )
    )
    if marker is None:
        marker = "o"
    saddle_marker_text = str(saddle_marker)
    if not saddle_marker_text:
        raise NEBVisualizationError("saddle_marker must not be empty")

    color = (
        resolved_spec.style.color_cycle[0]
        if series_style is None or series_style.color is None
        else series_style.color
    )
    line_width = (
        resolved_spec.style.line_width
        if series_style is None or series_style.line_width is None
        else series_style.line_width
    )
    line_style = (
        resolved_spec.style.line_style
        if series_style is None or series_style.line_style is None
        else series_style.line_style
    )
    marker_size = (
        resolved_spec.style.marker_size
        if series_style is None or series_style.marker_size is None
        else series_style.marker_size
    )
    marker_edge_width = (
        resolved_spec.style.marker_edge_width
        if series_style is None or series_style.marker_edge_width is None
        else series_style.marker_edge_width
    )
    alpha = None if series_style is None else series_style.alpha
    zorder = None if series_style is None else series_style.zorder
    display_label = path.label or path.key
    if series_style is not None and series_style.label is not None:
        display_label = series_style.label

    x_before = np.array(path.reaction_coordinates, copy=True)
    y_before = np.array(path.plotted_energy_ev, copy=True)
    path_digest_before = path.digest
    x_values = path.reaction_coordinates
    y_values = path.plotted_energy_ev

    line_kwargs: dict[str, object] = {
        "color": color,
        "linewidth": line_width,
        "linestyle": line_style,
        "marker": marker,
        "markersize": marker_size,
        "markeredgewidth": marker_edge_width,
        "alpha": alpha,
        "label": display_label,
    }
    if zorder is not None:
        line_kwargs["zorder"] = zorder

    with figure_axes_context(resolved_spec) as (figure, ax):
        ax.plot(x_values, y_values, **line_kwargs)
        if barrier is not None and show_saddle:
            saddle_index = barrier.saddle_image_index
            ax.scatter(
                [float(x_values[saddle_index])],
                [float(y_values[saddle_index])],
                color=color,
                marker=saddle_marker_text,
                s=max(marker_size, 1.0) ** 2 * 2.25,
                alpha=alpha,
                zorder=(3.0 if zorder is None else zorder + 1.0),
                label="_nolegend_",
            )

        tick_labels: list[str] = []
        for image in path.images:
            category_style = resolved_spec.category_styles.get(image.key)
            tick_labels.append(
                category_style.label
                if category_style is not None and category_style.label is not None
                else (image.label or image.key)
            )
        ax.set_xticks(x_values)
        ax.set_xticklabels(tick_labels)
        ax.xaxis.set_minor_locator(NullLocator())

        xlabel = (
            "NEB image index"
            if path.reaction_coordinate_mode == "ordinal"
            else "Reaction coordinate"
        )
        ylabel = (
            "Energy (eV)"
            if path.energy_mode == "absolute"
            else "Relative energy (eV)"
        )
        finalize_axes(
            ax,
            resolved_spec,
            xlabel=xlabel if resolved_spec.xlabel is None else resolved_spec.xlabel,
            ylabel=ylabel if resolved_spec.ylabel is None else resolved_spec.ylabel,
            labeled_count=1 if display_label else 0,
            apply_xscale=False,
        )

    if not np.array_equal(path.reaction_coordinates, x_before):
        raise RuntimeError("NEB plotting mutated retained reaction coordinates")
    if not np.array_equal(path.plotted_energy_ev, y_before):
        raise RuntimeError("NEB plotting mutated retained energetic state")
    if path.digest != path_digest_before:
        raise RuntimeError("NEB plotting mutated retained path identity")
    return figure, ax


__all__ = ["NEBVisualizationError", "plot_neb_path"]
