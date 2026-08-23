"""Generic publication scatter rendering for core Series and Dataset objects."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from catalysis_workbench.core import Dataset, Series

from ._shared import figure_axes_context, finish_axes
from .curves import (
    _series_tuple,
    _validate_axis_compatibility,
    _validate_real_curves,
    _validate_style_keys,
    format_axis_label,
)
from .presets import get_preset
from .specs import FigureSpec, VisualizationError


def _error_values(
    values: Sequence[float] | np.ndarray | None,
    *,
    name: str,
) -> tuple[float, ...] | None:
    if values is None:
        return None
    array = np.asarray(values)
    if np.iscomplexobj(array):
        raise VisualizationError(f"{name} must contain real non-negative values")
    try:
        numeric = array.astype(np.float64, copy=False)
    except (TypeError, ValueError) as exc:
        raise VisualizationError(f"{name} must contain real non-negative values") from exc
    if numeric.ndim != 1:
        raise VisualizationError(f"{name} must be one-dimensional")
    if numeric.size == 0:
        raise VisualizationError(f"{name} must not be empty")
    if not np.all(np.isfinite(numeric)) or np.any(numeric < 0):
        raise VisualizationError(f"{name} must contain finite non-negative values")
    return tuple(float(value) for value in numeric)


@dataclass(frozen=True, slots=True)
class ScatterErrorBars:
    """Explicit symmetric x/y uncertainties for one scatter series."""

    x: tuple[float, ...] | Sequence[float] | np.ndarray | None = None
    y: tuple[float, ...] | Sequence[float] | np.ndarray | None = None

    def __post_init__(self) -> None:
        x = _error_values(self.x, name="scatter x error")
        y = _error_values(self.y, name="scatter y error")
        if x is None and y is None:
            raise VisualizationError("ScatterErrorBars requires x and/or y uncertainties")
        object.__setattr__(self, "x", x)
        object.__setattr__(self, "y", y)


def _validated_errors(
    series: Sequence[Series],
    errors: Mapping[str, ScatterErrorBars] | None,
) -> dict[str, ScatterErrorBars]:
    if errors is None:
        return {}
    resolved: dict[str, ScatterErrorBars] = {}
    available = {item.key for item in series if item.key}
    for key, value in dict(errors).items():
        stable_key = str(key).strip()
        if not stable_key:
            raise VisualizationError("scatter error-bar keys must not be empty")
        if stable_key not in available:
            raise VisualizationError(
                f"scatter error-bar key is not present in the rendered data: {stable_key!r}"
            )
        if not isinstance(value, ScatterErrorBars):
            raise TypeError("scatter error-bar values must be ScatterErrorBars instances")
        resolved[stable_key] = value

    for item in series:
        if not item.key or item.key not in resolved:
            continue
        error = resolved[item.key]
        for name, values in (("x", error.x), ("y", error.y)):
            if values is not None and len(values) != len(item.x):
                raise VisualizationError(
                    f"scatter {name} error length for series {item.key!r} must match data length"
                )
    return resolved


def render_scatter(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    errors: Mapping[str, ScatterErrorBars] | None = None,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Render one or several compatible scatter series and return ``(figure, axes)``.

    Error bars are drawn only when explicitly supplied in ``errors`` and are addressed
    by stable ``Series.key`` rather than display labels. The renderer does not call
    ``show()`` and does not mutate scientific input objects.
    """
    resolved_spec = get_preset(preset) if spec is None else spec
    if not isinstance(resolved_spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")

    series = _series_tuple(data)
    _validate_real_curves(series)
    _validate_axis_compatibility(series)
    _validate_style_keys(series, resolved_spec)
    resolved_errors = _validated_errors(series, errors)

    style = resolved_spec.style
    with figure_axes_context(resolved_spec) as (figure, ax):
        visible_count = 0
        labeled_count = 0
        for index, item in enumerate(series):
            override = resolved_spec.series_styles.get(item.key) if item.key else None
            if override is not None and not override.visible:
                continue

            color = (
                override.color
                if override is not None and override.color is not None
                else style.color_cycle[index % len(style.color_cycle)]
            )
            edge_color = (
                override.edge_color
                if override is not None and override.edge_color is not None
                else color
            )
            marker = (
                override.marker
                if override is not None and override.marker is not None
                else (style.marker or "o")
            )
            marker_size = (
                override.marker_size
                if override is not None and override.marker_size is not None
                else style.marker_size
            )
            marker_edge_width = (
                override.marker_edge_width
                if override is not None and override.marker_edge_width is not None
                else style.marker_edge_width
            )
            label = item.label
            if override is not None and override.label is not None:
                label = override.label
            rendered_label = label if label else "_nolegend_"

            scatter_kwargs: dict[str, object] = {
                "s": marker_size**2,
                "marker": marker,
                "color": color,
                "edgecolors": edge_color,
                "linewidths": marker_edge_width,
                "label": rendered_label,
            }
            if override is not None and override.alpha is not None:
                scatter_kwargs["alpha"] = override.alpha
            if override is not None and override.zorder is not None:
                scatter_kwargs["zorder"] = override.zorder
            ax.scatter(item.x, item.y, **scatter_kwargs)

            error = resolved_errors.get(item.key) if item.key else None
            if error is not None:
                ax.errorbar(
                    item.x,
                    item.y,
                    xerr=error.x,
                    yerr=error.y,
                    fmt="none",
                    ecolor=style.errorbar_color or color,
                    elinewidth=style.errorbar_line_width,
                    capsize=style.errorbar_cap_size,
                    zorder=(
                        None
                        if override is None or override.zorder is None
                        else override.zorder
                    ),
                )

            visible_count += 1
            if rendered_label != "_nolegend_":
                labeled_count += 1

        if visible_count == 0:
            raise VisualizationError("all scatter series are hidden by SeriesStyle overrides")

        xlabel = (
            format_axis_label(series[0].x_axis, unit_format=style.axis_unit_format)
            if resolved_spec.xlabel is None
            else resolved_spec.xlabel
        )
        ylabel = (
            format_axis_label(series[0].y_axis, unit_format=style.axis_unit_format)
            if resolved_spec.ylabel is None
            else resolved_spec.ylabel
        )
        finish_axes(
            ax,
            resolved_spec,
            xlabel=xlabel,
            ylabel=ylabel,
            labeled_count=labeled_count,
        )

    return figure, ax
