"""Publication plotting for already-computed constrained XPS fit results."""

from __future__ import annotations

from math import isfinite
from typing import Literal, TypeAlias

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from catalysis_workbench.core import Axis
from catalysis_workbench.visualization import FigureSpec, format_axis_label, get_preset
from catalysis_workbench.visualization._rendering import figure_context, finalize_axes

from .xps import XPSError
from .xps_fitting import XPSPeakFitResult

XPSBindingEnergyDisplay: TypeAlias = Literal["descending", "ascending", "source"]
_RESERVED_LAYER_KEYS = frozenset(
    {"xps_observed", "xps_background", "xps_best_fit", "xps_residual"}
)


def _fraction(value: float, *, name: str, allow_zero: bool = False) -> float:
    number = float(value)
    lower_ok = number >= 0.0 if allow_zero else number > 0.0
    if not isfinite(number) or not lower_ok or number >= 1.0:
        comparison = "[0, 1)" if allow_zero else "(0, 1)"
        raise XPSError(f"{name} must be finite and in {comparison}")
    return number


def _validate_result(result: XPSPeakFitResult) -> None:
    if not isinstance(result, XPSPeakFitResult):
        raise TypeError("result must be an XPSPeakFitResult")
    collisions = sorted(_RESERVED_LAYER_KEYS.intersection(result.component_keys))
    if collisions:
        raise XPSError(
            f"XPS component keys collide with reserved plotting-layer keys: {collisions}"
        )


def _available_style_keys(result: XPSPeakFitResult) -> set[str]:
    return set(_RESERVED_LAYER_KEYS).union(result.component_keys)


def _validate_style_keys(result: XPSPeakFitResult, spec: FigureSpec) -> None:
    unknown = set(spec.series_styles) - _available_style_keys(result)
    if unknown:
        raise XPSError(f"XPS plot series style keys are not available: {sorted(unknown)!r}")


def _line_kwargs(
    *,
    key: str,
    label: str,
    index: int,
    spec: FigureSpec,
    default_line_style: str | None = None,
    default_marker: str | None = None,
) -> tuple[dict[str, object], bool]:
    style = spec.style
    override = spec.series_styles.get(key)
    visible = True if override is None else override.visible
    color = (
        override.color
        if override is not None and override.color is not None
        else style.color_cycle[index % len(style.color_cycle)]
    )
    resolved_label = label
    if override is not None and override.label is not None:
        resolved_label = override.label
    kwargs: dict[str, object] = {
        "color": color,
        "linewidth": (
            override.line_width
            if override is not None and override.line_width is not None
            else style.line_width
        ),
        "linestyle": (
            override.line_style
            if override is not None and override.line_style is not None
            else (style.line_style if default_line_style is None else default_line_style)
        ),
        "marker": (
            override.marker
            if override is not None and override.marker is not None
            else (style.marker if default_marker is None else default_marker)
        ),
        "markersize": (
            override.marker_size
            if override is not None and override.marker_size is not None
            else style.marker_size
        ),
        "markeredgewidth": (
            override.marker_edge_width
            if override is not None and override.marker_edge_width is not None
            else style.marker_edge_width
        ),
        "label": resolved_label if resolved_label else "_nolegend_",
    }
    if override is not None and override.alpha is not None:
        kwargs["alpha"] = override.alpha
    if override is not None and override.zorder is not None:
        kwargs["zorder"] = override.zorder
    return kwargs, visible


def _binding_energy_label(spec: FigureSpec) -> str:
    if spec.xlabel is not None:
        return spec.xlabel
    return format_axis_label(
        Axis("binding_energy", unit="eV", label="Binding energy"),
        unit_format=spec.style.axis_unit_format,
    )


def _intensity_label(result: XPSPeakFitResult, spec: FigureSpec) -> str:
    if spec.ylabel is not None:
        return spec.ylabel
    return format_axis_label(
        Axis("intensity", unit=result.fit.y_unit, label="Intensity"),
        unit_format=spec.style.axis_unit_format,
    )


def _apply_x_direction(
    axes: tuple[Axes, ...],
    *,
    result: XPSPeakFitResult,
    display: XPSBindingEnergyDisplay,
) -> None:
    if display not in {"descending", "ascending", "source"}:
        raise XPSError(
            "binding_energy_display must be 'descending', 'ascending', or 'source'"
        )
    resolved = result.source_direction if display == "source" else display
    left, right = axes[0].get_xlim()
    low = min(left, right)
    high = max(left, right)
    target = (high, low) if resolved == "descending" else (low, high)
    for ax in axes:
        ax.set_xlim(*target)


def _panel_bounds(
    spec: FigureSpec,
    *,
    show_residual: bool,
    residual_height_fraction: float,
    residual_gap_fraction: float,
) -> tuple[tuple[float, float, float, float], tuple[float, float, float, float] | None]:
    left, bottom, width, height = spec.layout.axes_bounds_fraction()
    if not show_residual:
        return (left, bottom, width, height), None

    residual_fraction = _fraction(
        residual_height_fraction,
        name="residual_height_fraction",
    )
    gap_fraction = _fraction(
        residual_gap_fraction,
        name="residual_gap_fraction",
        allow_zero=True,
    )
    main_fraction = 1.0 - residual_fraction - gap_fraction
    if main_fraction <= 0.0:
        raise XPSError(
            "residual_height_fraction + residual_gap_fraction must be < 1"
        )
    residual_bounds = (left, bottom, width, height * residual_fraction)
    main_bounds = (
        left,
        bottom + height * (residual_fraction + gap_fraction),
        width,
        height * main_fraction,
    )
    return main_bounds, residual_bounds


def _component_label(result: XPSPeakFitResult, key: str) -> str:
    for component in result.fit.spec.components:
        if component.key == key:
            return component.label or component.key
    return key


def plot_xps_fit(
    result: XPSPeakFitResult,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
    show_background: bool = True,
    show_components: bool = True,
    show_residual: bool = False,
    binding_energy_display: XPSBindingEnergyDisplay = "descending",
    residual_height_fraction: float = 0.22,
    residual_gap_fraction: float = 0.05,
) -> tuple[Figure, tuple[Axes, ...]]:
    """Render an already-computed constrained XPS fit without numerical recomputation."""
    _validate_result(result)
    resolved_spec = get_preset(preset) if spec is None else spec
    if not isinstance(resolved_spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")
    _validate_style_keys(result, resolved_spec)

    main_bounds, residual_bounds = _panel_bounds(
        resolved_spec,
        show_residual=show_residual,
        residual_height_fraction=residual_height_fraction,
        residual_gap_fraction=residual_gap_fraction,
    )
    fit = result.fit
    x = fit.x
    xlabel = _binding_energy_label(resolved_spec)
    ylabel = _intensity_label(result, resolved_spec)

    with figure_context(resolved_spec) as figure:
        main_ax = figure.add_axes(main_bounds)
        labeled_count = 0
        color_index = 0

        observed_kwargs, observed_visible = _line_kwargs(
            key="xps_observed",
            label=fit.source_label or "Observed",
            index=color_index,
            spec=resolved_spec,
            default_line_style="none",
            default_marker="o",
        )
        color_index += 1
        if observed_visible:
            main_ax.plot(x, fit.observed_y, **observed_kwargs)
            if observed_kwargs["label"] != "_nolegend_":
                labeled_count += 1

        if show_background:
            background_kwargs, background_visible = _line_kwargs(
                key="xps_background",
                label="Background",
                index=color_index,
                spec=resolved_spec,
                default_line_style="--",
            )
            color_index += 1
            if background_visible:
                main_ax.plot(x, fit.background, **background_kwargs)
                if background_kwargs["label"] != "_nolegend_":
                    labeled_count += 1

        if show_components:
            for component in fit.spec.components:
                key = component.key
                component_kwargs, component_visible = _line_kwargs(
                    key=key,
                    label=_component_label(result, key),
                    index=color_index,
                    spec=resolved_spec,
                    default_line_style="--",
                )
                color_index += 1
                if not component_visible:
                    continue
                main_ax.plot(x, fit.component_curves[key], **component_kwargs)
                if component_kwargs["label"] != "_nolegend_":
                    labeled_count += 1

        best_kwargs, best_visible = _line_kwargs(
            key="xps_best_fit",
            label="Best fit",
            index=color_index,
            spec=resolved_spec,
        )
        if best_visible:
            main_ax.plot(x, fit.best_fit_y, **best_kwargs)
            if best_kwargs["label"] != "_nolegend_":
                labeled_count += 1

        main_xlabel = "" if show_residual else xlabel
        finalize_axes(
            main_ax,
            resolved_spec,
            xlabel=main_xlabel,
            ylabel=ylabel,
            labeled_count=labeled_count,
        )

        axes: tuple[Axes, ...]
        if residual_bounds is None:
            axes = (main_ax,)
        else:
            residual_ax = figure.add_axes(residual_bounds)
            residual_kwargs, residual_visible = _line_kwargs(
                key="xps_residual",
                label="Residual",
                index=color_index + 1,
                spec=resolved_spec,
            )
            if residual_visible:
                residual_ax.plot(x, fit.residual, **residual_kwargs)
            residual_ax.axhline(
                0.0,
                color="black",
                linewidth=max(0.5, resolved_spec.style.spine_width),
                linestyle=":",
                label="_nolegend_",
            )
            residual_spec = resolved_spec.updated(
                title=None,
                ylabel=None,
                ylim=None,
                yscale="linear",
                show_legend=False,
                annotations=(),
            )
            finalize_axes(
                residual_ax,
                residual_spec,
                xlabel=xlabel,
                ylabel="Residual",
                labeled_count=0,
            )
            main_ax.tick_params(labelbottom=False)
            axes = (main_ax, residual_ax)

        _apply_x_direction(
            axes,
            result=result,
            display=binding_energy_display,
        )
        return figure, axes


__all__ = ["XPSBindingEnergyDisplay", "plot_xps_fit"]
