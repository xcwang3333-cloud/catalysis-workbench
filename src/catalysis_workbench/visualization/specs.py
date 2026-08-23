"""Serializable specifications for publication-quality figures.

The specification layer intentionally contains no scientific analysis. A later GUI can
bind controls to these dataclasses and request a redraw from the same renderer used by
the Python API.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, replace
from math import isfinite
from types import MappingProxyType
from typing import Any, Literal


class VisualizationError(ValueError):
    """Raised when a figure specification or render request is invalid."""


def _positive(value: float, *, name: str) -> float:
    number = float(value)
    if not isfinite(number) or number <= 0:
        raise VisualizationError(f"{name} must be finite and greater than zero")
    return number


def _nonnegative(value: float, *, name: str) -> float:
    number = float(value)
    if not isfinite(number) or number < 0:
        raise VisualizationError(f"{name} must be finite and non-negative")
    return number


def _optional_limit(
    value: tuple[float, float] | list[float] | None,
    *,
    name: str,
) -> tuple[float, float] | None:
    if value is None:
        return None
    if len(value) != 2:
        raise VisualizationError(f"{name} must contain exactly two values")
    lower, upper = (float(value[0]), float(value[1]))
    if not isfinite(lower) or not isfinite(upper) or lower == upper:
        raise VisualizationError(f"{name} must contain two distinct finite values")
    return (lower, upper)


@dataclass(frozen=True, slots=True)
class LayoutSpec:
    """Physical figure and axes geometry in inches.

    Margins define the minimum space reserved around the axes. When explicit axes
    dimensions or an aspect ratio produce a smaller axes rectangle, any remaining
    horizontal/vertical space is left on the right/top side. This makes the physical
    left and bottom margins deterministic and keeps the geometry easy to reproduce.
    """

    figure_width_in: float = 3.5
    figure_height_in: float = 2.625
    left_margin_in: float = 0.55
    right_margin_in: float = 0.15
    bottom_margin_in: float = 0.48
    top_margin_in: float = 0.15
    axes_width_in: float | None = None
    axes_height_in: float | None = None
    axes_aspect: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "figure_width_in", _positive(self.figure_width_in, name="figure_width_in")
        )
        object.__setattr__(
            self,
            "figure_height_in",
            _positive(self.figure_height_in, name="figure_height_in"),
        )
        for name in (
            "left_margin_in",
            "right_margin_in",
            "bottom_margin_in",
            "top_margin_in",
        ):
            object.__setattr__(self, name, _nonnegative(getattr(self, name), name=name))
        if self.axes_width_in is not None:
            object.__setattr__(
                self, "axes_width_in", _positive(self.axes_width_in, name="axes_width_in")
            )
        if self.axes_height_in is not None:
            object.__setattr__(
                self,
                "axes_height_in",
                _positive(self.axes_height_in, name="axes_height_in"),
            )
        if self.axes_aspect is not None:
            object.__setattr__(
                self, "axes_aspect", _positive(self.axes_aspect, name="axes_aspect")
            )
        self.resolved_axes_size_in()

    def available_axes_size_in(self) -> tuple[float, float]:
        """Return the width/height available after reserving configured margins."""
        width = self.figure_width_in - self.left_margin_in - self.right_margin_in
        height = self.figure_height_in - self.bottom_margin_in - self.top_margin_in
        if width <= 0 or height <= 0:
            raise VisualizationError("figure margins leave no positive axes drawing area")
        return width, height

    def resolved_axes_size_in(self) -> tuple[float, float]:
        """Resolve the requested physical axes width and height in inches."""
        available_width, available_height = self.available_axes_size_in()
        width = self.axes_width_in
        height = self.axes_height_in
        aspect = self.axes_aspect

        if aspect is not None:
            if width is not None and height is not None:
                if not abs(width / height - aspect) <= 1e-9 * max(1.0, abs(aspect)):
                    raise VisualizationError(
                        "axes_width_in / axes_height_in conflicts with axes_aspect"
                    )
            elif width is not None:
                height = width / aspect
            elif height is not None:
                width = height * aspect
            elif available_width / available_height >= aspect:
                height = available_height
                width = height * aspect
            else:
                width = available_width
                height = width / aspect

        width = available_width if width is None else width
        height = available_height if height is None else height
        if width > available_width + 1e-12 or height > available_height + 1e-12:
            raise VisualizationError(
                "requested axes dimensions do not fit inside the figure and margins"
            )
        return float(width), float(height)

    def axes_bounds_fraction(self) -> tuple[float, float, float, float]:
        """Return Matplotlib ``add_axes`` bounds as figure fractions."""
        width, height = self.resolved_axes_size_in()
        return (
            self.left_margin_in / self.figure_width_in,
            self.bottom_margin_in / self.figure_height_in,
            width / self.figure_width_in,
            height / self.figure_height_in,
        )

    def updated(self, **changes: Any) -> LayoutSpec:
        """Return a validated copy with selected fields changed."""
        return replace(self, **changes)


@dataclass(frozen=True, slots=True)
class PlotStyle:
    """Global curve, scatter, bar, typography, axes, tick, and legend defaults."""

    font_family: str = "DejaVu Sans"
    font_size: float = 8.0
    axis_label_size: float = 8.0
    tick_label_size: float = 7.0
    title_size: float = 8.0
    line_width: float = 1.2
    line_style: str = "-"
    marker: str | None = None
    marker_size: float = 4.0
    marker_edge_width: float = 0.8
    bar_group_width: float = 0.8
    errorbar_capsize: float = 2.5
    spine_width: float = 0.8
    tick_length: float = 3.0
    tick_width: float = 0.8
    tick_direction: Literal["in", "out", "inout"] = "in"
    minor_ticks: bool = True
    top_ticks: bool = True
    right_ticks: bool = True
    legend_font_size: float = 7.0
    legend_location: str = "best"
    legend_frame: bool = False
    axis_unit_format: Literal["parentheses", "slash", "none"] = "parentheses"
    color_cycle: tuple[str, ...] = (
        "#0C5DA5",
        "#00B945",
        "#FF9500",
        "#FF2C00",
        "#845B97",
        "#474747",
    )

    def __post_init__(self) -> None:
        family = str(self.font_family).strip()
        if not family:
            raise VisualizationError("font_family must not be empty")
        object.__setattr__(self, "font_family", family)
        for name in (
            "font_size",
            "axis_label_size",
            "tick_label_size",
            "title_size",
            "line_width",
            "marker_size",
            "marker_edge_width",
            "errorbar_capsize",
            "spine_width",
            "tick_length",
            "tick_width",
            "legend_font_size",
        ):
            object.__setattr__(self, name, _nonnegative(getattr(self, name), name=name))
        group_width = float(self.bar_group_width)
        if not isfinite(group_width) or not 0 < group_width <= 1:
            raise VisualizationError("bar_group_width must be finite and in (0, 1]")
        object.__setattr__(self, "bar_group_width", group_width)
        if not str(self.line_style):
            raise VisualizationError("line_style must not be empty")
        if self.tick_direction not in {"in", "out", "inout"}:
            raise VisualizationError("tick_direction must be 'in', 'out', or 'inout'")
        if not str(self.legend_location).strip():
            raise VisualizationError("legend_location must not be empty")
        if self.axis_unit_format not in {"parentheses", "slash", "none"}:
            raise VisualizationError(
                "axis_unit_format must be 'parentheses', 'slash', or 'none'"
            )
        colors = tuple(str(color).strip() for color in self.color_cycle)
        if not colors or any(not color for color in colors):
            raise VisualizationError("color_cycle must contain at least one non-empty color")
        object.__setattr__(self, "color_cycle", colors)

    def updated(self, **changes: Any) -> PlotStyle:
        """Return a validated copy with selected fields changed."""
        return replace(self, **changes)


@dataclass(frozen=True, slots=True)
class SeriesStyle:
    """Per-series visual overrides addressed by a stable non-display key."""

    color: str | None = None
    line_width: float | None = None
    line_style: str | None = None
    marker: str | None = None
    marker_size: float | None = None
    marker_edge_width: float | None = None
    alpha: float | None = None
    zorder: float | None = None
    label: str | None = None
    visible: bool = True

    def __post_init__(self) -> None:
        for name in ("line_width", "marker_size", "marker_edge_width"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _nonnegative(value, name=name))
        if self.alpha is not None:
            alpha = float(self.alpha)
            if not isfinite(alpha) or not 0 <= alpha <= 1:
                raise VisualizationError("alpha must be finite and between 0 and 1")
            object.__setattr__(self, "alpha", alpha)
        if self.zorder is not None:
            zorder = float(self.zorder)
            if not isfinite(zorder):
                raise VisualizationError("zorder must be finite")
            object.__setattr__(self, "zorder", zorder)
        if self.color is not None and not str(self.color).strip():
            raise VisualizationError("color must not be empty when supplied")
        if self.line_style is not None and not str(self.line_style):
            raise VisualizationError("line_style must not be empty when supplied")

    def updated(self, **changes: Any) -> SeriesStyle:
        """Return a validated copy with selected fields changed."""
        return replace(self, **changes)


@dataclass(frozen=True, slots=True)
class CategoryStyle:
    """Per-category bar overrides addressed by stable ``BarCategory.key``."""

    color: str | None = None
    alpha: float | None = None
    label: str | None = None
    visible: bool = True

    def __post_init__(self) -> None:
        if self.color is not None and not str(self.color).strip():
            raise VisualizationError("category color must not be empty when supplied")
        if self.alpha is not None:
            alpha = float(self.alpha)
            if not isfinite(alpha) or not 0 <= alpha <= 1:
                raise VisualizationError(
                    "category alpha must be finite and between 0 and 1"
                )
            object.__setattr__(self, "alpha", alpha)

    def updated(self, **changes: Any) -> CategoryStyle:
        """Return a validated copy with selected fields changed."""
        return replace(self, **changes)


@dataclass(frozen=True, slots=True)
class AnnotationSpec:
    """One text annotation in data or normalized axes coordinates."""

    text: str
    x: float
    y: float
    coordinates: Literal["data", "axes"] = "axes"
    font_size: float | None = None
    horizontal_alignment: str = "left"
    vertical_alignment: str = "bottom"
    rotation: float = 0.0
    color: str | None = None

    def __post_init__(self) -> None:
        if not str(self.text):
            raise VisualizationError("annotation text must not be empty")
        for name in ("x", "y", "rotation"):
            value = float(getattr(self, name))
            if not isfinite(value):
                raise VisualizationError(f"annotation {name} must be finite")
            object.__setattr__(self, name, value)
        if self.coordinates not in {"data", "axes"}:
            raise VisualizationError("annotation coordinates must be 'data' or 'axes'")
        if self.font_size is not None:
            object.__setattr__(
                self, "font_size", _nonnegative(self.font_size, name="annotation font_size")
            )


@dataclass(frozen=True, slots=True)
class ExportSpec:
    """Exact-size export settings shared by PNG, SVG, and PDF output."""

    dpi: int = 600
    transparent: bool = False
    svg_fonttype: Literal["none", "path"] = "none"
    pdf_fonttype: Literal[3, 42] = 42

    def __post_init__(self) -> None:
        dpi = int(self.dpi)
        if dpi <= 0:
            raise VisualizationError("export dpi must be greater than zero")
        object.__setattr__(self, "dpi", dpi)
        if self.svg_fonttype not in {"none", "path"}:
            raise VisualizationError("svg_fonttype must be 'none' or 'path'")
        if self.pdf_fonttype not in {3, 42}:
            raise VisualizationError("pdf_fonttype must be 3 or 42")

    def updated(self, **changes: Any) -> ExportSpec:
        """Return a validated copy with selected fields changed."""
        return replace(self, **changes)


@dataclass(frozen=True, slots=True)
class FigureSpec:
    """Complete, serializable recipe for one publication figure."""

    layout: LayoutSpec = field(default_factory=LayoutSpec)
    style: PlotStyle = field(default_factory=PlotStyle)
    export: ExportSpec = field(default_factory=ExportSpec)
    xlabel: str | None = None
    ylabel: str | None = None
    title: str | None = None
    xlim: tuple[float, float] | None = None
    ylim: tuple[float, float] | None = None
    xscale: Literal["linear", "log", "symlog", "logit"] = "linear"
    yscale: Literal["linear", "log", "symlog", "logit"] = "linear"
    show_legend: bool | None = None
    annotations: tuple[AnnotationSpec, ...] = ()
    series_styles: Mapping[str, SeriesStyle] = field(default_factory=dict, repr=False)
    category_styles: Mapping[str, CategoryStyle] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.layout, LayoutSpec):
            raise TypeError("layout must be a LayoutSpec")
        if not isinstance(self.style, PlotStyle):
            raise TypeError("style must be a PlotStyle")
        if not isinstance(self.export, ExportSpec):
            raise TypeError("export must be an ExportSpec")
        object.__setattr__(self, "xlim", _optional_limit(self.xlim, name="xlim"))
        object.__setattr__(self, "ylim", _optional_limit(self.ylim, name="ylim"))
        if self.xscale not in {"linear", "log", "symlog", "logit"}:
            raise VisualizationError("unsupported xscale")
        if self.yscale not in {"linear", "log", "symlog", "logit"}:
            raise VisualizationError("unsupported yscale")

        annotations = tuple(self.annotations)
        if not all(isinstance(item, AnnotationSpec) for item in annotations):
            raise TypeError("annotations must contain AnnotationSpec instances")
        object.__setattr__(self, "annotations", annotations)

        frozen_series_styles: dict[str, SeriesStyle] = {}
        for key, value in dict(self.series_styles).items():
            stable_key = str(key).strip()
            if not stable_key:
                raise VisualizationError("series style keys must not be empty")
            if stable_key in frozen_series_styles:
                raise VisualizationError(
                    "series style keys must be unique after normalization"
                )
            if not isinstance(value, SeriesStyle):
                raise TypeError("series_styles values must be SeriesStyle instances")
            frozen_series_styles[stable_key] = value
        object.__setattr__(
            self, "series_styles", MappingProxyType(frozen_series_styles)
        )

        frozen_category_styles: dict[str, CategoryStyle] = {}
        for key, value in dict(self.category_styles).items():
            stable_key = str(key).strip()
            if not stable_key:
                raise VisualizationError("category style keys must not be empty")
            if stable_key in frozen_category_styles:
                raise VisualizationError(
                    "category style keys must be unique after normalization"
                )
            if not isinstance(value, CategoryStyle):
                raise TypeError("category_styles values must be CategoryStyle instances")
            frozen_category_styles[stable_key] = value
        object.__setattr__(
            self, "category_styles", MappingProxyType(frozen_category_styles)
        )

    def updated(self, **changes: Any) -> FigureSpec:
        """Return a validated copy with selected top-level fields changed."""
        return replace(self, **changes)

    def with_layout(self, **changes: Any) -> FigureSpec:
        """Return a copy with selected physical layout fields changed."""
        return replace(self, layout=self.layout.updated(**changes))

    def with_style(self, **changes: Any) -> FigureSpec:
        """Return a copy with selected global style fields changed."""
        return replace(self, style=self.style.updated(**changes))

    def with_export(self, **changes: Any) -> FigureSpec:
        """Return a copy with selected export fields changed."""
        return replace(self, export=self.export.updated(**changes))

    def with_series_style(
        self,
        key: str,
        style: SeriesStyle | None = None,
        **changes: Any,
    ) -> FigureSpec:
        """Return a copy with one stable-key-specific series style added or updated."""
        stable_key = str(key).strip()
        if not stable_key:
            raise VisualizationError("series style key must not be empty")
        current = self.series_styles.get(stable_key, SeriesStyle()) if style is None else style
        if not isinstance(current, SeriesStyle):
            raise TypeError("style must be a SeriesStyle")
        if changes:
            current = current.updated(**changes)
        styles = dict(self.series_styles)
        styles[stable_key] = current
        return replace(self, series_styles=styles)

    def without_series_style(self, key: str) -> FigureSpec:
        """Return a copy without the selected stable-key-specific series override."""
        styles = dict(self.series_styles)
        styles.pop(str(key).strip(), None)
        return replace(self, series_styles=styles)

    def with_category_style(
        self,
        key: str,
        style: CategoryStyle | None = None,
        **changes: Any,
    ) -> FigureSpec:
        """Return a copy with one stable-key-specific category style added or updated."""
        stable_key = str(key).strip()
        if not stable_key:
            raise VisualizationError("category style key must not be empty")
        current = (
            self.category_styles.get(stable_key, CategoryStyle())
            if style is None
            else style
        )
        if not isinstance(current, CategoryStyle):
            raise TypeError("style must be a CategoryStyle")
        if changes:
            current = current.updated(**changes)
        styles = dict(self.category_styles)
        styles[stable_key] = current
        return replace(self, category_styles=styles)

    def without_category_style(self, key: str) -> FigureSpec:
        """Return a copy without the selected stable-key-specific category override."""
        styles = dict(self.category_styles)
        styles.pop(str(key).strip(), None)
        return replace(self, category_styles=styles)

    def with_annotation(self, annotation: AnnotationSpec) -> FigureSpec:
        """Return a copy with one annotation appended."""
        if not isinstance(annotation, AnnotationSpec):
            raise TypeError("annotation must be an AnnotationSpec")
        return replace(self, annotations=(*self.annotations, annotation))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly plain dictionary for persistence or GUI state."""
        style = asdict(self.style)
        style["color_cycle"] = list(self.style.color_cycle)
        return {
            "layout": asdict(self.layout),
            "style": style,
            "export": asdict(self.export),
            "xlabel": self.xlabel,
            "ylabel": self.ylabel,
            "title": self.title,
            "xlim": None if self.xlim is None else list(self.xlim),
            "ylim": None if self.ylim is None else list(self.ylim),
            "xscale": self.xscale,
            "yscale": self.yscale,
            "show_legend": self.show_legend,
            "annotations": [asdict(item) for item in self.annotations],
            "series_styles": {
                key: asdict(value) for key, value in self.series_styles.items()
            },
            "category_styles": {
                key: asdict(value) for key, value in self.category_styles.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> FigureSpec:
        """Reconstruct a validated spec from :meth:`to_dict`-compatible data."""
        values = dict(data)
        layout = LayoutSpec(**dict(values.pop("layout", {})))
        style_values = dict(values.pop("style", {}))
        if "color_cycle" in style_values:
            style_values["color_cycle"] = tuple(style_values["color_cycle"])
        style = PlotStyle(**style_values)
        export = ExportSpec(**dict(values.pop("export", {})))
        annotations = tuple(
            AnnotationSpec(**dict(item)) for item in values.pop("annotations", ())
        )
        series_styles = {
            key: SeriesStyle(**dict(item))
            for key, item in dict(values.pop("series_styles", {})).items()
        }
        category_styles = {
            key: CategoryStyle(**dict(item))
            for key, item in dict(values.pop("category_styles", {})).items()
        }
        return cls(
            layout=layout,
            style=style,
            export=export,
            annotations=annotations,
            series_styles=series_styles,
            category_styles=category_styles,
            **values,
        )
