"""Generic categorical bar rendering for scalar scientific summaries."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from numpy.typing import ArrayLike, NDArray

from catalysis_workbench.core import Axis

from ._rendering import figure_axes_context, finalize_axes
from .curves import format_axis_label
from .presets import get_preset
from .specs import CategoryStyle, FigureSpec, SeriesStyle, VisualizationError


def _immutable_real_values(
    values: ArrayLike,
    *,
    name: str,
    nonnegative: bool = False,
) -> NDArray[np.float64]:
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
    if nonnegative and (finite < 0).any():
        raise VisualizationError(f"{name} must be non-negative where finite")
    immutable_buffer = normalized.tobytes(order="C")
    result = np.frombuffer(immutable_buffer, dtype=np.float64, count=normalized.size)
    result.setflags(write=False)
    return result


@dataclass(frozen=True, slots=True)
class BarCategory:
    """One categorical x position with a stable non-display key."""

    key: str
    label: str

    def __post_init__(self) -> None:
        key = str(self.key).strip()
        if not key:
            raise VisualizationError("BarCategory.key must not be empty")
        if not isinstance(self.label, str):
            raise TypeError("BarCategory.label must be a string")
        object.__setattr__(self, "key", key)
        object.__setattr__(self, "label", self.label.strip())


@dataclass(frozen=True, slots=True)
class BarSeries:
    """One ordered scalar summary series, optionally with explicit errors."""

    key: str
    values: ArrayLike
    label: str = ""
    errors: ArrayLike | None = None

    def __post_init__(self) -> None:
        key = str(self.key).strip()
        if not key:
            raise VisualizationError("BarSeries.key must not be empty")
        if not isinstance(self.label, str):
            raise TypeError("BarSeries.label must be a string")
        values = _immutable_real_values(self.values, name="bar values")
        errors = None
        if self.errors is not None:
            errors = _immutable_real_values(
                self.errors,
                name="bar errors",
                nonnegative=True,
            )
            if len(errors) != len(values):
                raise VisualizationError(
                    "bar errors must contain the same number of values as bar values"
                )
        object.__setattr__(self, "key", key)
        object.__setattr__(self, "label", self.label.strip())
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "errors", errors)


@dataclass(frozen=True, slots=True)
class BarData:
    """Categorical input for one single-series or grouped publication bar figure."""

    categories: Sequence[BarCategory]
    series: Sequence[BarSeries]
    x_axis: Axis = field(default_factory=lambda: Axis("category"))
    y_axis: Axis = field(default_factory=lambda: Axis("value"))

    def __post_init__(self) -> None:
        categories = tuple(self.categories)
        series = tuple(self.series)
        if not categories:
            raise VisualizationError("BarData requires at least one category")
        if not series:
            raise VisualizationError("BarData requires at least one series")
        if not all(isinstance(item, BarCategory) for item in categories):
            raise TypeError("BarData.categories must contain only BarCategory instances")
        if not all(isinstance(item, BarSeries) for item in series):
            raise TypeError("BarData.series must contain only BarSeries instances")
        if not isinstance(self.x_axis, Axis) or not isinstance(self.y_axis, Axis):
            raise TypeError("BarData x_axis and y_axis must be Axis instances")

        category_keys = [item.key for item in categories]
        if len(category_keys) != len(set(category_keys)):
            raise VisualizationError("BarCategory keys must be unique within BarData")
        series_keys = [item.key for item in series]
        if len(series_keys) != len(set(series_keys)):
            raise VisualizationError("BarSeries keys must be unique within BarData")
        for item in series:
            if len(item.values) != len(categories):
                raise VisualizationError(
                    f"BarSeries {item.key!r} must contain one value per category"
                )

        object.__setattr__(self, "categories", categories)
        object.__setattr__(self, "series", series)


def _validate_style_keys(data: BarData, spec: FigureSpec) -> None:
    series_keys = {item.key for item in data.series}
    unknown_series = set(spec.series_styles) - series_keys
    if unknown_series:
        raise VisualizationError(
            "series style keys are not present in the rendered bar data: "
            f"{sorted(unknown_series)!r}"
        )
    category_keys = {item.key for item in data.categories}
    unknown_categories = set(spec.category_styles) - category_keys
    if unknown_categories:
        raise VisualizationError(
            "category style keys are not present in the rendered bar data: "
            f"{sorted(unknown_categories)!r}"
        )


def _series_override(data: BarSeries, spec: FigureSpec) -> SeriesStyle | None:
    return spec.series_styles.get(data.key)


def _category_override(data: BarCategory, spec: FigureSpec) -> CategoryStyle | None:
    return spec.category_styles.get(data.key)


def render_bars(
    data: BarData,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Render deterministic single-series or grouped bars and return ``(fig, ax)``.

    Categorical order follows ``BarData.categories`` and grouped-series order follows
    ``BarData.series``. Error bars are drawn only from explicit ``BarSeries.errors``.
    """
    if not isinstance(data, BarData):
        raise TypeError("data must be a BarData")
    resolved_spec = get_preset(preset) if spec is None else spec
    if not isinstance(resolved_spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")
    if resolved_spec.xscale != "linear":
        raise VisualizationError("categorical bar rendering requires a linear xscale")
    _validate_style_keys(data, resolved_spec)

    visible_categories = [
        (index, category)
        for index, category in enumerate(data.categories)
        if not (
            (override := _category_override(category, resolved_spec)) is not None
            and not override.visible
        )
    ]
    if not visible_categories:
        raise VisualizationError(
            "all bar categories are hidden by CategoryStyle overrides"
        )

    visible_series = [
        (index, series)
        for index, series in enumerate(data.series)
        if not (
            (override := _series_override(series, resolved_spec)) is not None
            and not override.visible
        )
    ]
    if not visible_series:
        raise VisualizationError("all bar series are hidden by SeriesStyle overrides")

    positions = np.arange(len(visible_categories), dtype=np.float64)
    group_width = resolved_spec.style.bar_group_width
    bar_width = group_width / len(visible_series)
    labeled_count = 0

    with figure_axes_context(resolved_spec) as (figure, ax):
        for visible_series_index, (source_series_index, series) in enumerate(visible_series):
            override = _series_override(series, resolved_spec)
            base_color = (
                override.color
                if override is not None and override.color is not None
                else resolved_spec.style.color_cycle[
                    source_series_index % len(resolved_spec.style.color_cycle)
                ]
            )
            label = series.label
            if override is not None and override.label is not None:
                label = override.label
            rendered_label = label if label else "_nolegend_"
            if rendered_label != "_nolegend_":
                labeled_count += 1

            colors: list[str] = []
            values: list[float] = []
            errors: list[float] | None = [] if series.errors is not None else None
            category_alphas: list[float | None] = []
            for source_category_index, category in visible_categories:
                category_style = _category_override(category, resolved_spec)
                colors.append(
                    category_style.color
                    if category_style is not None and category_style.color is not None
                    else base_color
                )
                category_alphas.append(
                    category_style.alpha
                    if category_style is not None and category_style.alpha is not None
                    else (override.alpha if override is not None else None)
                )
                values.append(float(series.values[source_category_index]))
                if errors is not None:
                    errors.append(float(series.errors[source_category_index]))

            offset = (
                visible_series_index - (len(visible_series) - 1) / 2.0
            ) * bar_width
            linewidth = (
                override.line_width
                if override is not None and override.line_width is not None
                else resolved_spec.style.line_width
            )
            kwargs: dict[str, object] = {
                "width": bar_width,
                "color": colors,
                "edgecolor": colors,
                "linewidth": linewidth,
                "label": rendered_label,
            }
            if override is not None and override.zorder is not None:
                kwargs["zorder"] = override.zorder
            if errors is not None:
                kwargs["yerr"] = np.asarray(errors, dtype=np.float64)
                kwargs["capsize"] = resolved_spec.style.errorbar_capsize
                kwargs["error_kw"] = {"elinewidth": linewidth}

            container = ax.bar(positions + offset, values, **kwargs)
            for patch, alpha in zip(container.patches, category_alphas, strict=True):
                if alpha is not None:
                    patch.set_alpha(alpha)

        tick_labels: list[str] = []
        for _, category in visible_categories:
            override = _category_override(category, resolved_spec)
            tick_labels.append(
                override.label
                if override is not None and override.label is not None
                else category.label
            )
        ax.set_xticks(positions)
        ax.set_xticklabels(tick_labels)

        xlabel = (
            format_axis_label(
                data.x_axis,
                unit_format=resolved_spec.style.axis_unit_format,
            )
            if resolved_spec.xlabel is None
            else resolved_spec.xlabel
        )
        ylabel = (
            format_axis_label(
                data.y_axis,
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
            apply_xscale=False,
        )

    return figure, ax
