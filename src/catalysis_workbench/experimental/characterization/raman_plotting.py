"""Publication rendering adapter for Raman spectra."""

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

from .raman import (
    RamanError,
    RamanPeakAnnotation,
    _canonicalize_raman_series,
    stack_raman_dataset,
    validate_raman_series,
)


def _series_tuple(data: Series | Dataset) -> tuple[Series, ...]:
    if isinstance(data, Series):
        return (data,)
    if isinstance(data, Dataset):
        if len(data) == 0:
            raise RamanError("cannot plot an empty Raman Dataset")
        return tuple(data)
    raise TypeError("data must be a Series or Dataset")


def _canonicalize_data(data: Series | Dataset) -> Series | Dataset:
    if isinstance(data, Series):
        return _canonicalize_raman_series(data)
    if isinstance(data, Dataset):
        return Dataset(
            series=tuple(_canonicalize_raman_series(item) for item in data),
            name=data.name,
            metadata=data.metadata_dict(),
        )
    raise TypeError("data must be a Series or Dataset")


def _raman_x_label(unit_format: str) -> str:
    if unit_format == "parentheses":
        return "Raman shift (cm⁻¹)"
    if unit_format == "slash":
        return "Raman shift / cm⁻¹"
    if unit_format == "none":
        return "Raman shift"
    raise RamanError("unsupported axis unit-label format")


def _resolve_annotation_series(
    series: Sequence[Series],
    annotation: RamanPeakAnnotation,
) -> Series:
    if len(series) == 1:
        item = series[0]
        if annotation.series_key is not None and item.key != annotation.series_key:
            raise RamanError(
                f"Raman peak annotation series_key {annotation.series_key!r} does not "
                f"match the plotted Series key {item.key!r}"
            )
        return item

    if annotation.series_key is None:
        raise RamanError(
            "Raman peak annotations on multi-spectrum data require an explicit series_key"
        )
    matches = [item for item in series if item.key == annotation.series_key]
    if not matches:
        raise RamanError(
            f"Raman peak annotation series_key {annotation.series_key!r} is not present"
        )
    return matches[0]


def _draw_peak_annotations(
    ax: Axes,
    series: Sequence[Series],
    annotations: Sequence[RamanPeakAnnotation],
    *,
    default_font_size: float,
) -> None:
    for annotation in annotations:
        if not isinstance(annotation, RamanPeakAnnotation):
            raise TypeError(
                "peak_annotations must contain RamanPeakAnnotation instances"
            )
        item = _resolve_annotation_series(series, annotation)
        position = annotation.shift_cm1
        x = np.asarray(item.x, dtype=np.float64)
        if position < x[0] or position > x[-1]:
            raise RamanError(
                f"Raman peak annotation at {position:g} cm^-1 lies outside the spectrum range"
            )
        y = np.asarray(item.y, dtype=np.float64)
        anchor = float(np.interp(position, x, y))
        if not isfinite(anchor):
            raise RamanError(
                "Raman peak annotation falls on/through missing intensity data; "
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


def plot_raman(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
    stack_step: float | None = None,
    stack_start: float = 0.0,
    peak_annotations: Sequence[RamanPeakAnnotation] = (),
) -> tuple[Figure, Axes]:
    """Render Raman spectra through the shared publication curve renderer."""
    source_series = _series_tuple(data)
    for item in source_series:
        validate_raman_series(item)

    render_source: Series | Dataset = data
    if stack_step is not None:
        if not isinstance(data, Dataset):
            raise RamanError("stack_step requires a multi-spectrum Dataset")
        render_source = stack_raman_dataset(data, step=stack_step, start=stack_start)

    canonical_data = _canonicalize_data(render_source)
    rendered_series = _series_tuple(canonical_data)
    resolved_spec = get_preset(preset) if spec is None else spec
    if not isinstance(resolved_spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")

    xlabel = resolved_spec.xlabel
    ylabel = resolved_spec.ylabel
    if xlabel is None:
        xlabel = _raman_x_label(resolved_spec.style.axis_unit_format)
    if ylabel is None:
        ylabel = format_axis_label(
            rendered_series[0].y_axis,
            unit_format=resolved_spec.style.axis_unit_format,
        )
    render_spec = resolved_spec.updated(xlabel=xlabel, ylabel=ylabel)
    figure, ax = render_curves(canonical_data, render_spec)

    x_limits = ax.get_xlim()
    y_limits = ax.get_ylim()
    _draw_peak_annotations(
        ax,
        rendered_series,
        tuple(peak_annotations),
        default_font_size=render_spec.style.font_size,
    )
    ax.set_xlim(*x_limits)
    ax.set_ylim(*y_limits)
    return figure, ax
