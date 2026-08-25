"""Passive publication rendering for retained free-energy diagram series."""

from __future__ import annotations

from collections.abc import Sequence
from math import isfinite

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import NullLocator

from catalysis_workbench.computation import (
    FreeEnergyDiagramSeries,
    validate_free_energy_diagram_series_compatibility,
)

from ._rendering import figure_axes_context, finalize_axes
from .presets import get_preset
from .specs import FigureSpec, VisualizationError


def _normalize_series(
    series: FreeEnergyDiagramSeries | Sequence[FreeEnergyDiagramSeries],
) -> tuple[FreeEnergyDiagramSeries, ...]:
    if isinstance(series, FreeEnergyDiagramSeries):
        retained = (series,)
    else:
        retained = tuple(series)
    return validate_free_energy_diagram_series_compatibility(retained)


def _context_label(series: FreeEnergyDiagramSeries) -> str | None:
    context = series.context
    if context is None:
        return None
    return (
        f"U = {context.input_potential_v:g} V vs "
        f"{context.input_potential_reference}; pH = {context.ph:g}; "
        f"T = {context.temperature_k:g} K"
    )


def plot_free_energy_diagram(
    series: FreeEnergyDiagramSeries | Sequence[FreeEnergyDiagramSeries],
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
    level_width: float = 0.5,
    show_context: bool = True,
) -> tuple[Figure, Axes]:
    """Render retained free-energy levels without recomputing thermodynamic state."""
    retained = _normalize_series(series)
    resolved_spec = get_preset(preset) if spec is None else spec
    if not isinstance(resolved_spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")
    if resolved_spec.xscale != "linear" or resolved_spec.yscale != "linear":
        raise VisualizationError("free-energy diagrams require linear x and y scales")

    width = float(level_width)
    if not isfinite(width) or not 0 < width <= 1:
        raise VisualizationError("level_width must be finite and in (0, 1]")

    series_keys = {item.key for item in retained}
    unknown_series = set(resolved_spec.series_styles) - series_keys
    if unknown_series:
        raise VisualizationError(
            "series style keys are not present in the free-energy diagram: "
            f"{sorted(unknown_series)!r}"
        )
    state_keys = set(retained[0].state_keys)
    unknown_categories = set(resolved_spec.category_styles) - state_keys
    if unknown_categories:
        raise VisualizationError(
            "category style keys are not present in the free-energy diagram: "
            f"{sorted(unknown_categories)!r}"
        )
    hidden_states = [
        key
        for key, style in resolved_spec.category_styles.items()
        if not style.visible
    ]
    if hidden_states:
        raise VisualizationError(
            "free-energy diagram rendering cannot hide retained pathway states: "
            f"{hidden_states!r}"
        )

    visible: list[tuple[int, FreeEnergyDiagramSeries]] = []
    for index, item in enumerate(retained):
        override = resolved_spec.series_styles.get(item.key)
        if override is None or override.visible:
            visible.append((index, item))
    if not visible:
        raise VisualizationError("all free-energy diagram series are hidden")

    before = tuple(np.array(item.plotted_energy_ev, copy=True) for item in retained)
    positions = np.arange(len(retained[0].states), dtype=np.float64)
    half_width = width / 2.0
    labeled_count = 0

    with figure_axes_context(resolved_spec) as (figure, ax):
        for source_index, item in visible:
            override = resolved_spec.series_styles.get(item.key)
            color = (
                override.color
                if override is not None and override.color is not None
                else resolved_spec.style.color_cycle[
                    source_index % len(resolved_spec.style.color_cycle)
                ]
            )
            line_width = (
                override.line_width
                if override is not None and override.line_width is not None
                else resolved_spec.style.line_width
            )
            line_style = (
                override.line_style
                if override is not None and override.line_style is not None
                else resolved_spec.style.line_style
            )
            alpha = None if override is None else override.alpha
            zorder = None if override is None else override.zorder
            display_label = item.label or item.key
            if override is not None and override.label is not None:
                display_label = override.label
            if display_label:
                labeled_count += 1

            values = item.plotted_energy_ev
            for state_index, (x_value, y_value) in enumerate(
                zip(positions, values, strict=True)
            ):
                level_kwargs: dict[str, object] = {
                    "color": color,
                    "linewidth": line_width,
                    "linestyle": line_style,
                    "alpha": alpha,
                    "label": display_label if state_index == 0 else "_nolegend_",
                }
                if zorder is not None:
                    level_kwargs["zorder"] = zorder
                ax.plot(
                    [x_value - half_width, x_value + half_width],
                    [float(y_value), float(y_value)],
                    **level_kwargs,
                )
                if state_index < len(values) - 1:
                    connector_kwargs = dict(level_kwargs)
                    connector_kwargs["label"] = "_nolegend_"
                    ax.plot(
                        [x_value + half_width, positions[state_index + 1] - half_width],
                        [float(y_value), float(values[state_index + 1])],
                        **connector_kwargs,
                    )

        tick_labels: list[str] = []
        for state in retained[0].states:
            category_style = resolved_spec.category_styles.get(state.key)
            tick_labels.append(
                category_style.label
                if category_style is not None and category_style.label is not None
                else (state.label or state.key)
            )
        ax.set_xticks(positions)
        ax.set_xticklabels(tick_labels)
        if resolved_spec.xlim is None:
            ax.set_xlim(-0.5 - half_width, len(positions) - 0.5 + half_width)

        ylabel = (
            "Free energy (eV)"
            if retained[0].energy_mode == "absolute"
            else "Relative free energy (eV)"
        )
        finalize_axes(
            ax,
            resolved_spec,
            xlabel="Pathway state" if resolved_spec.xlabel is None else resolved_spec.xlabel,
            ylabel=ylabel if resolved_spec.ylabel is None else resolved_spec.ylabel,
            labeled_count=labeled_count,
            apply_xscale=False,
        )
        ax.xaxis.set_minor_locator(NullLocator())

        if show_context and (label := _context_label(retained[0])) is not None:
            ax.text(
                0.98,
                0.98,
                label,
                transform=ax.transAxes,
                fontsize=resolved_spec.style.font_size,
                ha="right",
                va="top",
            )

    for item, snapshot in zip(retained, before, strict=True):
        if not np.array_equal(item.plotted_energy_ev, snapshot):
            raise RuntimeError("free-energy diagram plotting mutated retained energetic state")
    return figure, ax


__all__ = ["plot_free_energy_diagram"]
