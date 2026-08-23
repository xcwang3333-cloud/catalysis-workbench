"""Generic publication bar rendering for categorical scalar summaries."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from catalysis_workbench.core import Axis

from ._shared import figure_axes_context, finish_axes
from .curves import format_axis_label
from .presets import get_preset
from .specs import FigureSpec, SeriesStyle, VisualizationError


def _finite_values(values: object, *, name: str) -> tuple[float, ...]:
    array = np.asarray(values)
    if np.iscomplexobj(array):
        raise VisualizationError(f"{name} must contain real finite values")
    try:
        numeric = array.astype(np.float64, copy=False)
    except (TypeError, ValueError) as exc:
        raise VisualizationError(f"{name} must contain real finite values") from exc
    if numeric.ndim != 1 or numeric.size == 0:
        raise VisualizationError(f"{name} must be a non-empty one-dimensional sequence")
    if not np.all(np.isfinite(numeric)):
        raise VisualizationError(f"{name} must contain real finite values")
    return tuple(float(value) for value in numeric)


def _nonnegative_errors(values: object, *, name: str) -> tuple[float, ...]:
    result = _finite_values(values, name=name)
    if any(value < 0 for value in result):
        raise VisualizationError(f"{name} must contain non-negative values")
    return result


@dataclass(frozen=True, slots=True)
class BarCategory:
    """One categorical bar position addressed by a stable non-display key."""

    key: str
    label: str

    def __post_init__(self) -> None:
        key = str(self.key).strip()
        if not key:
            raise VisualizationError("bar category key must not be empty")
        if not isinstance(self.label, str):
            raise TypeError("bar category label must be a string")
        object.__setattr__(self, "key", key)


@dataclass(frozen=True, slots=True)
class BarSeries:
    """One ordered scalar series across a shared set of bar categories."""

    key: str
    values: tuple[float, ...] | object
    label: str = ""
    yerr: tuple[float, ...] | object | None = None

    def __post_init__(self) -> None:
        key = str(self.key).strip()
        if not key:
            raise VisualizationError("bar series key must not be empty")
        if not isinstance(self.label, str):
            raise TypeError("bar series label must be a string")
        object.__setattr__(self, "key", key)
        object.__setattr__(self, "values", _finite_values(self.values, name="bar values"))
        if self.yerr is not None:
            object.__setattr__(
                self,
                "yerr",
                _nonnegative_errors(self.yerr, name="bar y error"),
            )


@dataclass(frozen=True, slots=True)
class BarData:
    """Complete ordered categorical matrix for single or grouped bar rendering."""

    categories: tuple[BarCategory, ...] | object
    series: tuple[BarSeries, ...] | object
    x_axis: Axis
    y_axis: Axis

    def __post_init__(self) -> None:
        categories = tuple(self.categories)
        series = tuple(self.series)
        if not categories:
            raise VisualizationError("BarData requires at least one category")
        if not series:
            raise VisualizationError("BarData requires at least one series")
        if not all(isinstance(item, BarCategory) for item in categories):
            raise TypeError("categories must contain BarCategory instances")
        if not all(isinstance(item, BarSeries) for item in series):
            raise TypeError("series must contain BarSeries instances")
        if not isinstance(self.x_axis, Axis) or not isinstance(self.y_axis, Axis):
            raise TypeError("x_axis and y_axis must be Axis instances")

        category_keys = [item.key for item in categories]
        if len(set(category_keys)) != len(category_keys):
            raise VisualizationError("bar category keys must be unique")
        series_keys = [item.key for item in series]
        if len(set(series_keys)) != len(series_keys):
            raise VisualizationError("bar series keys must be unique")

        expected = len(categories)
        for item in series:
            if len(item.values) != expected:
                raise VisualizationError(
                    f"bar series {item.key!r} values must match the category count"
                )
            if item.yerr is not None and len(item.yerr) != expected:
                raise VisualizationError(
                    f"bar series {item.key!r} yerr must match the category count"
                )
        object.__setattr__(self, "categories", categories)
        object.__setattr__(self, "series", series)


def _validate_style_keys(data: BarData, spec: FigureSpec) -> None:
    series_keys = {item.key for item in data.series}
    unknown_series = set(spec.series_styles) - series_keys
    if unknown_series:
        raise VisualizationError(
            f"series style keys are not present in the rendered data: {sorted(unknown_series)!r}"
        )
    category_keys = {item.key for item in data.categories}
    unknown_categories = set(spec.category_styles) - category_keys
    if unknown_categories:
        raise VisualizationError(
            "category style keys are not present in the rendered data: "
            f"{sorted(unknown_categories)!r}"
        )


def _resolved_style(
    series_style: SeriesStyle | None,
    category_style: SeriesStyle | None,
    *,
    name: str,
    default: object,
) -> object:
    if category_style is not None:
        value = getattr(category_style, name)
        if value is not None:
            return value
    if series_style is not None:
        value = getattr(series_style, name)
        if value is not None:
            return value
    return default


def render_bars(
    data: BarData,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Render deterministic single/grouped bars and return ``(figure, axes)``.

    Category and series order come exclusively from ``BarData``. Optional uncertainty
    is drawn only from explicit ``BarSeries.yerr`` values. Stable keys, rather than
    display labels, address per-series and per-category visual overrides.
    """
    if not isinstance(data, BarData):
        raise TypeError("data must be a BarData")
    resolved_spec = get_preset(preset) if spec is None else spec
    if not isinstance(resolved_spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")
    if resolved_spec.xscale != "linear":
        raise VisualizationError("categorical bar rendering requires a linear xscale")
    _validate_style_keys(data, resolved_spec)

    visible_categories: list[tuple[int, BarCategory]] = []
    for index, category in enumerate(data.categories):
        override = resolved_spec.category_styles.get(category.key)
        if override is None or override.visible:
            visible_categories.append((index, category))
    if not visible_categories:
        raise VisualizationError("all bar categories are hidden by category style overrides")

    visible_series: list[tuple[int, BarSeries]] = []
    for index, item in enumerate(data.series):
        override = resolved_spec.series_styles.get(item.key)
        if override is None or override.visible:
            visible_series.append((index, item))
    if not visible_series:
        raise VisualizationError("all bar series are hidden by SeriesStyle overrides")

    style = resolved_spec.style
    category_indices = [index for index, _ in visible_categories]
    base_positions = np.arange(len(visible_categories), dtype=float)
    per_series_width = style.bar_group_width / len(visible_series)

    with figure_axes_context(resolved_spec) as (figure, ax):
        labeled_count = 0
        for visible_index, (source_index, item) in enumerate(visible_series):
            series_style = resolved_spec.series_styles.get(item.key)
            series_color = (
                series_style.color
                if series_style is not None and series_style.color is not None
                else style.color_cycle[source_index % len(style.color_cycle)]
            )
            label = item.label
            if series_style is not None and series_style.label is not None:
                label = series_style.label
            rendered_label = label if label else "_nolegend_"

            offset = (visible_index - (len(visible_series) - 1) / 2.0) * per_series_width
            positions = base_positions + offset
            values = np.asarray([item.values[index] for index in category_indices])
            yerr = (
                None
                if item.yerr is None
                else np.asarray([item.yerr[index] for index in category_indices])
            )

            facecolors: list[object] = []
            edgecolors: list[object] = []
            for _, category in visible_categories:
                category_style = resolved_spec.category_styles.get(category.key)
                face = _resolved_style(
                    series_style,
                    category_style,
                    name="color",
                    default=series_color,
                )
                edge = _resolved_style(
                    series_style,
                    category_style,
                    name="edge_color",
                    default=style.bar_edge_color or face,
                )
                facecolors.append(face)
                edgecolors.append(edge)

            error_kw = {
                "elinewidth": style.errorbar_line_width,
                "capsize": style.errorbar_cap_size,
                "ecolor": style.errorbar_color or series_color,
            }
            container = ax.bar(
                positions,
                values,
                width=per_series_width,
                color=facecolors,
                edgecolor=edgecolors,
                linewidth=style.bar_edge_width,
                yerr=yerr,
                error_kw=error_kw if yerr is not None else None,
                label=rendered_label,
            )

            for patch, (_, category) in zip(container.patches, visible_categories, strict=True):
                category_style = resolved_spec.category_styles.get(category.key)
                hatch = _resolved_style(
                    series_style,
                    category_style,
                    name="hatch",
                    default=None,
                )
                alpha = _resolved_style(
                    series_style,
                    category_style,
                    name="alpha",
                    default=None,
                )
                zorder = _resolved_style(
                    series_style,
                    category_style,
                    name="zorder",
                    default=None,
                )
                if hatch is not None:
                    patch.set_hatch(hatch)
                if alpha is not None:
                    patch.set_alpha(alpha)
                if zorder is not None:
                    patch.set_zorder(zorder)

            if rendered_label != "_nolegend_":
                labeled_count += 1

        tick_labels: list[str] = []
        for _, category in visible_categories:
            category_style = resolved_spec.category_styles.get(category.key)
            label = category.label
            if category_style is not None and category_style.label is not None:
                label = category_style.label
            tick_labels.append(label)
        ax.set_xticks(base_positions, labels=tick_labels)

        xlabel = (
            format_axis_label(data.x_axis, unit_format=style.axis_unit_format)
            if resolved_spec.xlabel is None
            else resolved_spec.xlabel
        )
        ylabel = (
            format_axis_label(data.y_axis, unit_format=style.axis_unit_format)
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
