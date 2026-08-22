"""Publication rendering adapter for powder XRD patterns."""

from __future__ import annotations

from collections.abc import Sequence
from math import isfinite

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from catalysis_workbench.core import Dataset, Series
from catalysis_workbench.visualization import (
    FigureSpec,
    format_axis_label,
    get_preset,
    render_curves,
)

from .xrd import (
    PeakAnnotation,
    XRDError,
    XRDReferencePattern,
    stack_xrd_dataset,
    validate_xrd_series,
)


def _series_tuple(data: Series | Dataset) -> tuple[Series, ...]:
    if isinstance(data, Series):
        return (data,)
    if isinstance(data, Dataset):
        if len(data) == 0:
            raise XRDError("cannot plot an empty XRD Dataset")
        return tuple(data)
    raise TypeError("data must be a Series or Dataset")


def _xrd_x_label(unit_format: str) -> str:
    if unit_format == "parentheses":
        return "2θ (°)"
    if unit_format == "slash":
        return "2θ / °"
    if unit_format == "none":
        return "2θ"
    raise XRDError("unsupported axis unit-label format")


def _resolve_annotation_series(
    series: Sequence[Series],
    annotation: PeakAnnotation,
) -> Series:
    if len(series) == 1:
        item = series[0]
        if annotation.series_key is not None and item.key != annotation.series_key:
            raise XRDError(
                f"peak annotation series_key {annotation.series_key!r} does not match "
                f"the plotted Series key {item.key!r}"
            )
        return item

    if annotation.series_key is None:
        raise XRDError(
            "peak annotations on multi-pattern XRD data require an explicit series_key"
        )
    matches = [item for item in series if item.key == annotation.series_key]
    if not matches:
        raise XRDError(
            f"peak annotation series_key {annotation.series_key!r} is not present"
        )
    return matches[0]


def _draw_peak_annotations(
    ax: Axes,
    series: Sequence[Series],
    annotations: Sequence[PeakAnnotation],
    *,
    default_font_size: float,
) -> None:
    for annotation in annotations:
        if not isinstance(annotation, PeakAnnotation):
            raise TypeError("peak_annotations must contain PeakAnnotation instances")
        item = _resolve_annotation_series(series, annotation)
        position = annotation.two_theta_deg
        x = np.asarray(item.x, dtype=np.float64)
        if position < x[0] or position > x[-1]:
            raise XRDError(
                f"peak annotation at {position:g}° lies outside the selected pattern range"
            )
        y = np.asarray(item.y, dtype=np.float64)
        anchor = float(np.interp(position, x, y))
        if not isfinite(anchor):
            raise XRDError(
                "peak annotation falls on/through missing intensity data; "
                "clean or move the annotation explicitly"
            )
        ax.annotate(
            annotation.text,
            xy=(position, anchor),
            xytext=(0.0, annotation.text_offset_points),
            textcoords="offset points",
            horizontalalignment="center",
            verticalalignment="bottom",
            rotation=annotation.rotation,
            fontsize=(
                default_font_size
                if annotation.font_size is None
                else annotation.font_size
            ),
            color=annotation.color,
            clip_on=True,
        )


def _reference_layout(
    *,
    count: int,
    base: float,
    height: float,
    gap: float,
) -> tuple[float, ...]:
    values = (float(base), float(height), float(gap))
    if any(not isfinite(value) for value in values):
        raise XRDError("reference_base, reference_height, and reference_gap must be finite")
    if base < 0 or height <= 0 or gap < 0:
        raise XRDError(
            "reference_base/gap must be non-negative and reference_height positive"
        )
    rows = tuple(base + index * (height + gap) for index in range(count))
    if rows and rows[-1] + height > 1:
        raise XRDError("reference stick bands do not fit inside the axes height")
    return rows


def _draw_reference_patterns(
    ax: Axes,
    references: Sequence[XRDReferencePattern],
    *,
    series_count: int,
    color_cycle: Sequence[str],
    label_font_size: float,
    base: float,
    height: float,
    gap: float,
) -> None:
    for item in references:
        if not isinstance(item, XRDReferencePattern):
            raise TypeError("reference_patterns must contain XRDReferencePattern instances")
    rows = _reference_layout(count=len(references), base=base, height=height, gap=gap)
    if not references:
        return

    x_limits = ax.get_xlim()
    y_limits = ax.get_ylim()
    x_lower, x_upper = sorted(x_limits)
    blended = ax.get_xaxis_transform()

    for index, (reference, row_base) in enumerate(zip(references, rows, strict=True)):
        positions = np.asarray(reference.positions_deg, dtype=np.float64)
        mask = (positions >= x_lower) & (positions <= x_upper)
        if not np.any(mask):
            continue
        visible_positions = positions[mask]
        if reference.intensities is None:
            scaled = np.ones(visible_positions.size, dtype=np.float64)
        else:
            intensities = np.asarray(reference.intensities, dtype=np.float64)
            scaled = intensities[mask] / float(np.max(intensities))

        color = (
            reference.color
            if reference.color is not None
            else color_cycle[(series_count + index) % len(color_cycle)]
        )
        ax.vlines(
            visible_positions,
            row_base,
            row_base + height * scaled,
            transform=blended,
            color=color,
            linewidth=reference.line_width,
            clip_on=True,
            zorder=3,
        )
        if reference.label:
            ax.text(
                0.995,
                row_base + height,
                reference.label,
                transform=ax.transAxes,
                horizontalalignment="right",
                verticalalignment="top",
                fontsize=label_font_size,
                color=color,
            )

    # Domain overlays must not expand or rescale the experimental data rectangle.
    ax.set_xlim(*x_limits)
    ax.set_ylim(*y_limits)


def plot_xrd(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
    stack_step: float | None = None,
    stack_start: float = 0.0,
    peak_annotations: Sequence[PeakAnnotation] = (),
    reference_patterns: Sequence[XRDReferencePattern] = (),
    reference_base: float = 0.02,
    reference_height: float = 0.08,
    reference_gap: float = 0.03,
) -> tuple[Figure, Axes]:
    """Render experimental XRD data through the shared publication renderer.

    ``stack_step`` is a deterministic non-mutating display convenience implemented by
    :func:`stack_xrd_dataset`. Call that processing function directly when the stacked
    Dataset and its provenance should be retained outside the figure.
    """
    source_series = _series_tuple(data)
    for item in source_series:
        validate_xrd_series(item)

    render_data: Series | Dataset = data
    if stack_step is not None:
        if not isinstance(data, Dataset):
            raise XRDError("stack_step requires a multi-pattern Dataset")
        render_data = stack_xrd_dataset(data, step=stack_step, start=stack_start)

    rendered_series = _series_tuple(render_data)
    resolved_spec = get_preset(preset) if spec is None else spec
    if not isinstance(resolved_spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")

    xlabel = resolved_spec.xlabel
    ylabel = resolved_spec.ylabel
    if xlabel is None:
        xlabel = _xrd_x_label(resolved_spec.style.axis_unit_format)
    if ylabel is None:
        ylabel = format_axis_label(
            rendered_series[0].y_axis,
            unit_format=resolved_spec.style.axis_unit_format,
        )
    render_spec = resolved_spec.updated(xlabel=xlabel, ylabel=ylabel)
    figure, ax = render_curves(render_data, render_spec)

    x_limits = ax.get_xlim()
    y_limits = ax.get_ylim()
    _draw_peak_annotations(
        ax,
        rendered_series,
        tuple(peak_annotations),
        default_font_size=render_spec.style.font_size,
    )
    _draw_reference_patterns(
        ax,
        tuple(reference_patterns),
        series_count=len(rendered_series),
        color_cycle=render_spec.style.color_cycle,
        label_font_size=render_spec.style.legend_font_size,
        base=reference_base,
        height=reference_height,
        gap=reference_gap,
    )
    # Text annotations should likewise not change the scientific limits.
    ax.set_xlim(*x_limits)
    ax.set_ylim(*y_limits)
    return figure, ax
