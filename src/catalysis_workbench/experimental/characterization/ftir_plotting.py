"""Publication rendering adapter for FTIR / ATR-FTIR spectra."""

from __future__ import annotations

from collections.abc import Sequence
from math import isfinite
from typing import Literal

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

from .ftir import (
    FTIRError,
    FTIRPeakAnnotation,
    _canonicalize_ftir_series,
    _monotonic_direction,
    stack_ftir_dataset,
    validate_ftir_overlay,
    validate_ftir_series,
)

FTIRDisplayDirection = Literal["descending", "ascending", "source"]


def _series_tuple(data: Series | Dataset) -> tuple[Series, ...]:
    if isinstance(data, Series):
        return (data,)
    if isinstance(data, Dataset):
        if len(data) == 0:
            raise FTIRError("cannot plot an empty FTIR Dataset")
        return tuple(data)
    raise TypeError("data must be a Series or Dataset")


def _canonicalize_data(data: Series | Dataset) -> Series | Dataset:
    if isinstance(data, Series):
        return _canonicalize_ftir_series(data)
    if isinstance(data, Dataset):
        return Dataset(
            series=tuple(_canonicalize_ftir_series(item) for item in data),
            name=data.name,
            metadata=data.metadata_dict(),
        )
    raise TypeError("data must be a Series or Dataset")


def _ftir_x_label(unit_format: str) -> str:
    if unit_format == "parentheses":
        return "Wavenumber (cm⁻¹)"
    if unit_format == "slash":
        return "Wavenumber / cm⁻¹"
    if unit_format == "none":
        return "Wavenumber"
    raise FTIRError("unsupported axis unit-label format")


def _resolve_annotation_series(
    series: Sequence[Series],
    annotation: FTIRPeakAnnotation,
) -> Series:
    if len(series) == 1:
        item = series[0]
        if annotation.series_key is not None and item.key != annotation.series_key:
            raise FTIRError(
                f"FTIR annotation series_key {annotation.series_key!r} does not match "
                f"the plotted Series key {item.key!r}"
            )
        return item
    if annotation.series_key is None:
        raise FTIRError("FTIR annotations on multi-spectrum data require an explicit series_key")
    matches = [item for item in series if item.key == annotation.series_key]
    if not matches:
        raise FTIRError(f"FTIR annotation series_key {annotation.series_key!r} is not present")
    return matches[0]


def _interpolated_y(item: Series, position: float) -> float:
    x = np.asarray(item.x, dtype=np.float64)
    y = np.asarray(item.y, dtype=np.float64)
    direction = _monotonic_direction(x)
    xp = x if direction == "ascending" else x[::-1]
    fp = y if direction == "ascending" else y[::-1]
    if position < xp[0] or position > xp[-1]:
        raise FTIRError(
            f"FTIR annotation at {position:g} cm^-1 lies outside the spectrum range"
        )
    anchor = float(np.interp(position, xp, fp))
    if not isfinite(anchor):
        raise FTIRError(
            "FTIR annotation falls on/through missing data; clean or move it explicitly"
        )
    return anchor


def _draw_annotations(
    ax: Axes,
    series: Sequence[Series],
    annotations: Sequence[FTIRPeakAnnotation],
    *,
    default_font_size: float,
) -> None:
    for annotation in annotations:
        if not isinstance(annotation, FTIRPeakAnnotation):
            raise TypeError("peak_annotations must contain FTIRPeakAnnotation instances")
        item = _resolve_annotation_series(series, annotation)
        position = annotation.wavenumber_cm1
        anchor = _interpolated_y(item, position)
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


def _apply_display_direction(
    ax: Axes,
    rendered_series: Sequence[Series],
    direction: FTIRDisplayDirection,
) -> None:
    if direction not in {"descending", "ascending", "source"}:
        raise FTIRError("wavenumber_direction must be 'descending', 'ascending', or 'source'")

    current_left, current_right = ax.get_xlim()
    lower = min(float(current_left), float(current_right))
    upper = max(float(current_left), float(current_right))
    if direction == "descending":
        ax.set_xlim(upper, lower)
        return
    if direction == "ascending":
        ax.set_xlim(lower, upper)
        return

    source_directions = {
        _monotonic_direction(np.asarray(item.x, dtype=np.float64))
        for item in rendered_series
    }
    if len(source_directions) != 1:
        raise FTIRError(
            "wavenumber_direction='source' requires all plotted spectra to share source direction"
        )
    source_direction = next(iter(source_directions))
    ax.set_xlim((upper, lower) if source_direction == "descending" else (lower, upper))


def plot_ftir(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
    stack_step: float | None = None,
    stack_start: float = 0.0,
    peak_annotations: Sequence[FTIRPeakAnnotation] = (),
    wavenumber_direction: FTIRDisplayDirection = "descending",
) -> tuple[Figure, Axes]:
    """Render FTIR spectra through the shared publication curve renderer."""
    source_series = _series_tuple(data)
    for item in source_series:
        validate_ftir_series(item)
    validate_ftir_overlay(data)

    render_source: Series | Dataset = data
    if stack_step is not None:
        if not isinstance(data, Dataset):
            raise FTIRError("stack_step requires a multi-spectrum Dataset")
        render_source = stack_ftir_dataset(data, step=stack_step, start=stack_start)

    canonical_data = _canonicalize_data(render_source)
    rendered_series = _series_tuple(canonical_data)
    resolved_spec = get_preset(preset) if spec is None else spec
    if not isinstance(resolved_spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")

    xlabel = resolved_spec.xlabel
    if xlabel is None:
        xlabel = _ftir_x_label(resolved_spec.style.axis_unit_format)
    ylabel = resolved_spec.ylabel
    if ylabel is None:
        ylabel = format_axis_label(
            rendered_series[0].y_axis,
            unit_format=resolved_spec.style.axis_unit_format,
        )
    render_spec = resolved_spec.updated(xlabel=xlabel, ylabel=ylabel)
    figure, ax = render_curves(canonical_data, render_spec)

    y_limits = ax.get_ylim()
    _apply_display_direction(ax, rendered_series, wavenumber_direction)
    x_limits = ax.get_xlim()
    _draw_annotations(
        ax,
        rendered_series,
        tuple(peak_annotations),
        default_font_size=render_spec.style.font_size,
    )
    ax.set_xlim(*x_limits)
    ax.set_ylim(*y_limits)
    return figure, ax
