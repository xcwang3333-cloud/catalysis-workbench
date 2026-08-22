"""Shared 2-D curve renderer for Series and Dataset objects."""

from __future__ import annotations

from collections.abc import Sequence

import matplotlib as mpl
import numpy as np
from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from catalysis_workbench.core import Axis, Dataset, Series

from .presets import get_preset
from .specs import FigureSpec, SeriesStyle, VisualizationError

_COMPATIBILITY_METADATA_KEYS = ("reference", "normalization")


def format_axis_label(axis: Axis, *, unit_format: str = "parentheses") -> str:
    """Construct a rendered axis label from semantic core axis metadata."""
    if not isinstance(axis, Axis):
        raise TypeError("axis must be an Axis")
    base = axis.label or axis.name
    if not axis.unit or unit_format == "none":
        return base
    if unit_format == "parentheses":
        return f"{base} ({axis.unit})"
    if unit_format == "slash":
        return f"{base} / {axis.unit}"
    raise VisualizationError("unit_format must be 'parentheses', 'slash', or 'none'")


def _series_tuple(data: Series | Dataset) -> tuple[Series, ...]:
    if isinstance(data, Series):
        return (data,)
    if isinstance(data, Dataset):
        if len(data) == 0:
            raise VisualizationError("cannot render an empty Dataset")
        return tuple(data)
    raise TypeError("data must be a Series or Dataset")


def _validate_real_curves(series: Sequence[Series]) -> None:
    for item in series:
        if np.iscomplexobj(item.x) or np.iscomplexobj(item.y):
            raise VisualizationError(
                "generic curve rendering requires real x/y data; use a domain-specific "
                "complex-data renderer instead of silently discarding a component"
            )


def _semantic_metadata_value(axis: Axis, key: str) -> object:
    value = axis.metadata.get(key)
    if isinstance(value, str):
        return value.strip().casefold()
    return value


def _validate_semantic_axis_metadata(
    first_axis: Axis,
    other_axis: Axis,
    *,
    axis_name: str,
) -> None:
    for key in _COMPATIBILITY_METADATA_KEYS:
        first_value = _semantic_metadata_value(first_axis, key)
        other_value = _semantic_metadata_value(other_axis, key)
        if first_value != other_value:
            raise VisualizationError(
                f"all curves on one axes must have matching {axis_name}-axis "
                f"{key!r} metadata; got {first_axis.metadata.get(key)!r} and "
                f"{other_axis.metadata.get(key)!r}"
            )


def _validate_axis_compatibility(series: Sequence[Series]) -> None:
    first = series[0]
    x_signature = (first.x_axis.name, first.x_axis.unit)
    y_signature = (first.y_axis.name, first.y_axis.unit)
    for item in series[1:]:
        if (item.x_axis.name, item.x_axis.unit) != x_signature:
            raise VisualizationError(
                "all curves on one axes must have matching x-axis names and units"
            )
        if (item.y_axis.name, item.y_axis.unit) != y_signature:
            raise VisualizationError(
                "all curves on one axes must have matching y-axis names and units"
            )
        _validate_semantic_axis_metadata(
            first.x_axis,
            item.x_axis,
            axis_name="x",
        )
        _validate_semantic_axis_metadata(
            first.y_axis,
            item.y_axis,
            axis_name="y",
        )


def _validate_style_keys(series: Sequence[Series], spec: FigureSpec) -> None:
    available = {item.key for item in series if item.key}
    unknown = set(spec.series_styles) - available
    if unknown:
        raise VisualizationError(
            f"series style keys are not present in the rendered data: {sorted(unknown)!r}"
        )


def _line_kwargs(
    item: Series,
    *,
    index: int,
    spec: FigureSpec,
) -> tuple[dict[str, object], SeriesStyle | None]:
    style = spec.style
    override = spec.series_styles.get(item.key) if item.key else None
    color = (
        override.color
        if override is not None and override.color is not None
        else style.color_cycle[index % len(style.color_cycle)]
    )
    label = item.label
    if override is not None and override.label is not None:
        label = override.label
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
            else style.line_style
        ),
        "marker": (
            override.marker
            if override is not None and override.marker is not None
            else style.marker
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
        "label": label if label else "_nolegend_",
    }
    if override is not None and override.alpha is not None:
        kwargs["alpha"] = override.alpha
    if override is not None and override.zorder is not None:
        kwargs["zorder"] = override.zorder
    return kwargs, override


def render_curves(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Render one or several compatible curves and return ``(figure, axes)``.

    The function does not import pyplot, register a GUI figure manager, call
    ``show()``, or mutate the scientific input objects.  ``spec`` is the complete
    redraw recipe; when omitted, a registered immutable preset is used. Rendering starts
    from Matplotlib defaults inside a local rc context so unrelated user rcParams do not
    alter the result and are restored after the figure is constructed.
    """
    resolved_spec = get_preset(preset) if spec is None else spec
    if not isinstance(resolved_spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")

    series = _series_tuple(data)
    _validate_real_curves(series)
    _validate_axis_compatibility(series)
    _validate_style_keys(series, resolved_spec)

    layout = resolved_spec.layout
    style = resolved_spec.style
    rc = {
        "font.family": style.font_family,
        "font.size": style.font_size,
        "axes.unicode_minus": True,
    }
    with mpl.rc_context():
        mpl.rcdefaults()
        mpl.rcParams.update(rc)
        figure = Figure(
            figsize=(layout.figure_width_in, layout.figure_height_in),
            dpi=100,
        )
        FigureCanvasAgg(figure)
        ax = figure.add_axes(layout.axes_bounds_fraction())

        visible_count = 0
        labeled_count = 0
        for index, item in enumerate(series):
            kwargs, override = _line_kwargs(item, index=index, spec=resolved_spec)
            if override is not None and not override.visible:
                continue
            ax.plot(item.x, item.y, **kwargs)
            visible_count += 1
            if kwargs["label"] != "_nolegend_":
                labeled_count += 1

        if visible_count == 0:
            raise VisualizationError("all curves are hidden by SeriesStyle overrides")

        ax.set_xscale(resolved_spec.xscale)
        ax.set_yscale(resolved_spec.yscale)
        if resolved_spec.xlim is not None:
            ax.set_xlim(*resolved_spec.xlim)
        if resolved_spec.ylim is not None:
            ax.set_ylim(*resolved_spec.ylim)

        xlabel = (
            format_axis_label(
                series[0].x_axis,
                unit_format=style.axis_unit_format,
            )
            if resolved_spec.xlabel is None
            else resolved_spec.xlabel
        )
        ylabel = (
            format_axis_label(
                series[0].y_axis,
                unit_format=style.axis_unit_format,
            )
            if resolved_spec.ylabel is None
            else resolved_spec.ylabel
        )
        ax.set_xlabel(xlabel, fontsize=style.axis_label_size)
        ax.set_ylabel(ylabel, fontsize=style.axis_label_size)
        if resolved_spec.title:
            ax.set_title(resolved_spec.title, fontsize=style.title_size)

        for spine in ax.spines.values():
            spine.set_linewidth(style.spine_width)
        ax.tick_params(
            axis="both",
            which="major",
            direction=style.tick_direction,
            length=style.tick_length,
            width=style.tick_width,
            labelsize=style.tick_label_size,
            top=style.top_ticks,
            right=style.right_ticks,
        )
        ax.tick_params(
            axis="both",
            which="minor",
            direction=style.tick_direction,
            length=style.tick_length * 0.55,
            width=style.tick_width,
            top=style.top_ticks,
            right=style.right_ticks,
        )
        if style.minor_ticks:
            ax.minorticks_on()
        else:
            ax.minorticks_off()

        show_legend = (
            labeled_count > 1
            if resolved_spec.show_legend is None
            else resolved_spec.show_legend
        )
        if show_legend and labeled_count:
            ax.legend(
                loc=style.legend_location,
                fontsize=style.legend_font_size,
                frameon=style.legend_frame,
            )

        for annotation in resolved_spec.annotations:
            transform = ax.transAxes if annotation.coordinates == "axes" else ax.transData
            ax.text(
                annotation.x,
                annotation.y,
                annotation.text,
                transform=transform,
                fontsize=(
                    style.font_size if annotation.font_size is None else annotation.font_size
                ),
                ha=annotation.horizontal_alignment,
                va=annotation.vertical_alignment,
                rotation=annotation.rotation,
                color=annotation.color,
            )

    return figure, ax
