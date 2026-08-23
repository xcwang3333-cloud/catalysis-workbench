"""Generic publication scatter rendering for core Series and Dataset objects."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from numpy.typing import ArrayLike, NDArray

from catalysis_workbench.core import Dataset, Series

from ._rendering import figure_axes_context, finalize_axes
from .curves import (
    _series_tuple,
    _validate_axis_compatibility,
    _validate_style_keys,
    format_axis_label,
)
from .presets import get_preset
from .specs import FigureSpec, SeriesStyle, VisualizationError


def _immutable_error(values: ArrayLike, *, name: str) -> NDArray[np.float64]:
    try:
        source = np.asarray(values)
    except (TypeError, ValueError) as exc:
        raise VisualizationError(f"{name} must contain real numeric values") from exc
    if source.ndim != 1:
        raise VisualizationError(f"{name} must be one-dimensional")
    if source.size == 0:
        raise VisualizationError(f"{name} must contain at least one value")
    if np.iscomplexobj(source) or source.dtype.kind not in "biuf":
        raise VisualizationError(f"{name} must contain real numeric values")
    normalized = np.ascontiguousarray(source, dtype=np.float64)
    if np.isinf(normalized).any():
        raise VisualizationError(f"{name} must not contain +/-inf")
    finite = normalized[~np.isnan(normalized)]
    if (finite < 0).any():
        raise VisualizationError(f"{name} must be non-negative where finite")
    immutable_buffer = normalized.tobytes(order="C")
    result = np.frombuffer(immutable_buffer, dtype=np.float64, count=normalized.size)
    result.setflags(write=False)
    return result


@dataclass(frozen=True, slots=True)
class ScatterError:
    """Explicit per-point scatter uncertainty; no uncertainty is inferred."""

    xerr: ArrayLike | None = None
    yerr: ArrayLike | None = None

    def __post_init__(self) -> None:
        if self.xerr is None and self.yerr is None:
            raise VisualizationError("ScatterError requires xerr and/or yerr")
        if self.xerr is not None:
            object.__setattr__(
                self,
                "xerr",
                _immutable_error(self.xerr, name="scatter xerr"),
            )
        if self.yerr is not None:
            object.__setattr__(
                self,
                "yerr",
                _immutable_error(self.yerr, name="scatter yerr"),
            )


def _validate_real_scatter(series: Sequence[Series]) -> None:
    for item in series:
        if np.iscomplexobj(item.x) or np.iscomplexobj(item.y):
            raise VisualizationError(
                "generic scatter rendering requires real x/y data; use a domain-specific "
                "complex-data renderer instead of silently discarding a component"
            )


def _validate_error_length(item: Series, error: ScatterError) -> None:
    for name, values in (("xerr", error.xerr), ("yerr", error.yerr)):
        if values is not None and len(values) != item.n_points:
            raise VisualizationError(
                f"scatter {name} for series {item.key or item.label!r} must "
                f"contain {item.n_points} values"
            )


def _normalize_error_mapping(
    series: Sequence[Series],
    errors: ScatterError | Mapping[str, ScatterError] | None,
) -> dict[int, ScatterError]:
    if errors is None:
        return {}
    if isinstance(errors, ScatterError):
        if len(series) != 1:
            raise VisualizationError(
                "a single ScatterError can only be used with one Series; "
                "use a stable-key mapping for Dataset input"
            )
        _validate_error_length(series[0], errors)
        return {0: errors}
    if not isinstance(errors, Mapping):
        raise TypeError("errors must be a ScatterError, mapping, or None")

    normalized: dict[str, ScatterError] = {}
    for raw_key, value in errors.items():
        key = str(raw_key).strip()
        if not key:
            raise VisualizationError("scatter error mapping keys must not be empty")
        if key in normalized:
            raise VisualizationError(
                "scatter error mapping keys must be unique after normalization"
            )
        if not isinstance(value, ScatterError):
            raise TypeError("scatter error mapping values must be ScatterError instances")
        normalized[key] = value

    available = {item.key for item in series if item.key}
    unknown = set(normalized) - available
    if unknown:
        raise VisualizationError(
            f"scatter error keys are not present in the rendered data: {sorted(unknown)!r}"
        )

    resolved: dict[int, ScatterError] = {}
    for index, item in enumerate(series):
        if item.key and item.key in normalized:
            error = normalized[item.key]
            _validate_error_length(item, error)
            resolved[index] = error
    return resolved


def _scatter_kwargs(
    item: Series,
    *,
    index: int,
    spec: FigureSpec,
) -> tuple[dict[str, object], SeriesStyle | None, float, str, float, float | None]:
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
    marker = (
        override.marker
        if override is not None and override.marker is not None
        else style.marker
    )
    marker = "o" if marker is None else marker
    marker_size = (
        override.marker_size
        if override is not None and override.marker_size is not None
        else style.marker_size
    )
    edge_width = (
        override.marker_edge_width
        if override is not None and override.marker_edge_width is not None
        else style.marker_edge_width
    )
    error_line_width = (
        override.line_width
        if override is not None and override.line_width is not None
        else style.line_width
    )
    alpha = override.alpha if override is not None else None
    zorder = (
        override.zorder
        if override is not None and override.zorder is not None
        else 1.0
    )
    kwargs: dict[str, object] = {
        "color": color,
        "marker": marker,
        "s": marker_size**2,
        "linewidths": edge_width,
        "label": label if label else "_nolegend_",
        "zorder": zorder,
    }
    if alpha is not None:
        kwargs["alpha"] = alpha
    return kwargs, override, error_line_width, color, zorder, alpha


def render_scatter(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    errors: ScatterError | Mapping[str, ScatterError] | None = None,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Render compatible XY data as scatter points and return ``(figure, axes)``.

    Error bars are drawn only when explicit :class:`ScatterError` data are supplied.
    Dataset uncertainty mappings are addressed by stable ``Series.key`` values, never
    display labels.
    """
    resolved_spec = get_preset(preset) if spec is None else spec
    if not isinstance(resolved_spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")

    series = _series_tuple(data)
    _validate_real_scatter(series)
    _validate_axis_compatibility(series)
    _validate_style_keys(series, resolved_spec)
    error_by_index = _normalize_error_mapping(series, errors)

    visible_count = 0
    labeled_count = 0
    with figure_axes_context(resolved_spec) as (figure, ax):
        for index, item in enumerate(series):
            (
                kwargs,
                override,
                error_line_width,
                color,
                zorder,
                alpha,
            ) = _scatter_kwargs(
                item,
                index=index,
                spec=resolved_spec,
            )
            if override is not None and not override.visible:
                continue

            error = error_by_index.get(index)
            if error is not None:
                error_kwargs: dict[str, object] = {
                    "fmt": "none",
                    "ecolor": color,
                    "elinewidth": error_line_width,
                    "capsize": resolved_spec.style.errorbar_capsize,
                    "label": "_nolegend_",
                    "zorder": zorder,
                }
                if alpha is not None:
                    error_kwargs["alpha"] = alpha
                ax.errorbar(
                    item.x,
                    item.y,
                    xerr=error.xerr,
                    yerr=error.yerr,
                    **error_kwargs,
                )

            ax.scatter(item.x, item.y, **kwargs)
            visible_count += 1
            if kwargs["label"] != "_nolegend_":
                labeled_count += 1

        if visible_count == 0:
            raise VisualizationError(
                "all scatter series are hidden by SeriesStyle overrides"
            )

        xlabel = (
            format_axis_label(
                series[0].x_axis,
                unit_format=resolved_spec.style.axis_unit_format,
            )
            if resolved_spec.xlabel is None
            else resolved_spec.xlabel
        )
        ylabel = (
            format_axis_label(
                series[0].y_axis,
                unit_format=resolved_spec.style.axis_unit_format,
            )
            if resolved_spec.ylabel is None
            else resolved_spec.ylabel
        )
        finalize_axes(
            ax,
            resolved_spec,
            xlabel=xlabel,
            ylabel=ylabel,
            labeled_count=labeled_count,
        )

    return figure, ax
