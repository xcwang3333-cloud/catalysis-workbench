"""Publication rendering adapter for TGA / DTG / TPR / TPD curves."""

from __future__ import annotations

from collections.abc import Sequence
from math import isfinite

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from catalysis_workbench.core import Dataset, Series
from catalysis_workbench.visualization import FigureSpec, get_preset, render_curves

from .thermal import (
    ThermalAnnotation,
    ThermalError,
    ThermalTechnique,
    _canonicalize_thermal_series,
    _monotonic_direction,
    stack_thermal_dataset,
    validate_thermal_overlay,
)


def _series_tuple(data: Series | Dataset) -> tuple[Series, ...]:
    if isinstance(data, Series):
        return (data,)
    if isinstance(data, Dataset):
        if len(data) == 0:
            raise ThermalError("cannot plot an empty thermal Dataset")
        return tuple(data)
    raise TypeError("data must be a Series or Dataset")


def _canonicalize_data(
    data: Series | Dataset,
    technique: ThermalTechnique,
) -> Series | Dataset:
    if isinstance(data, Series):
        return _canonicalize_thermal_series(data, technique)
    if isinstance(data, Dataset):
        return Dataset(
            series=tuple(_canonicalize_thermal_series(item, technique) for item in data),
            name=data.name,
            metadata=data.metadata_dict(),
        )
    raise TypeError("data must be a Series or Dataset")


def _resolve_annotation_series(
    series: Sequence[Series],
    annotation: ThermalAnnotation,
) -> Series:
    if len(series) == 1:
        item = series[0]
        if annotation.series_key is not None and annotation.series_key != item.key:
            raise ThermalError(
                f"thermal annotation series_key {annotation.series_key!r} does not match "
                f"the plotted Series key {item.key!r}"
            )
        return item
    if annotation.series_key is None:
        raise ThermalError(
            "thermal annotations on multi-curve data require an explicit series_key"
        )
    matches = [item for item in series if item.key == annotation.series_key]
    if not matches:
        raise ThermalError(
            f"thermal annotation series_key {annotation.series_key!r} is not present"
        )
    return matches[0]


def _interpolated_y(item: Series, temperature: float) -> float:
    x = np.asarray(item.x, dtype=np.float64)
    y = np.asarray(item.y, dtype=np.float64)
    direction = _monotonic_direction(x)
    xp = x if direction == "ascending" else x[::-1]
    fp = y if direction == "ascending" else y[::-1]
    if temperature < xp[0] or temperature > xp[-1]:
        raise ThermalError(
            f"thermal annotation at {temperature:g} lies outside the measured range"
        )
    exact = np.flatnonzero(xp == temperature)
    if exact.size:
        anchor = float(fp[int(exact[0])])
    else:
        right = int(np.searchsorted(xp, temperature, side="right"))
        left = right - 1
        if left < 0 or right >= xp.size:
            raise ThermalError("thermal annotation cannot be bracketed")
        if not isfinite(float(fp[left])) or not isfinite(float(fp[right])):
            raise ThermalError(
                "thermal annotation interpolation requires finite bracketing y values"
            )
        anchor = float(np.interp(temperature, xp, fp))
    if not isfinite(anchor):
        raise ThermalError("thermal annotation falls on missing y data")
    return anchor


def _draw_annotations(
    ax: Axes,
    series: Sequence[Series],
    annotations: Sequence[ThermalAnnotation],
    *,
    default_font_size: float,
) -> None:
    for annotation in annotations:
        if not isinstance(annotation, ThermalAnnotation):
            raise TypeError("annotations must contain ThermalAnnotation instances")
        item = _resolve_annotation_series(series, annotation)
        anchor = _interpolated_y(item, annotation.temperature)
        ax.annotate(
            annotation.text,
            xy=(annotation.temperature, anchor),
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


def plot_thermal(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    technique: ThermalTechnique,
    preset: str = "publication",
    stack_step: float | None = None,
    stack_start: float = 0.0,
    annotations: Sequence[ThermalAnnotation] = (),
) -> tuple[Figure, Axes]:
    """Render compatible thermal curves through the shared publication renderer."""
    validate_thermal_overlay(data, technique=technique)
    render_source: Series | Dataset = data
    if stack_step is not None:
        if not isinstance(data, Dataset):
            raise ThermalError("stack_step requires a multi-curve Dataset")
        render_source = stack_thermal_dataset(
            data,
            technique=technique,
            step=stack_step,
            start=stack_start,
        )

    canonical_data = _canonicalize_data(render_source, technique)
    rendered_series = _series_tuple(canonical_data)
    resolved_spec = get_preset(preset) if spec is None else spec
    if not isinstance(resolved_spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")

    figure, ax = render_curves(canonical_data, resolved_spec)
    x_limits = ax.get_xlim()
    y_limits = ax.get_ylim()
    _draw_annotations(
        ax,
        rendered_series,
        tuple(annotations),
        default_font_size=resolved_spec.style.font_size,
    )
    ax.set_xlim(*x_limits)
    ax.set_ylim(*y_limits)
    return figure, ax
