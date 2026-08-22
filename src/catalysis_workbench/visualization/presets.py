"""Generic publication presets for the shared visualization layer.

Presets are starting templates rather than locked themes.  They intentionally avoid
journal names in v0.1; journal-specific packages/configuration can register additional
specifications later.
"""

from __future__ import annotations

from .specs import FigureSpec, LayoutSpec, PlotStyle, VisualizationError

_PRESETS: dict[str, FigureSpec] = {
    "publication": FigureSpec(),
    "compact": FigureSpec(
        layout=LayoutSpec(
            figure_width_in=3.35,
            figure_height_in=2.30,
            left_margin_in=0.52,
            right_margin_in=0.12,
            bottom_margin_in=0.43,
            top_margin_in=0.12,
        ),
        style=PlotStyle(
            font_size=7.5,
            axis_label_size=7.5,
            tick_label_size=6.8,
            title_size=7.5,
            legend_font_size=6.8,
            line_width=1.1,
            spine_width=0.7,
            tick_width=0.7,
            tick_length=2.8,
        ),
    ),
    "wide": FigureSpec(
        layout=LayoutSpec(
            figure_width_in=7.0,
            figure_height_in=3.5,
            left_margin_in=0.65,
            right_margin_in=0.20,
            bottom_margin_in=0.55,
            top_margin_in=0.18,
        ),
        style=PlotStyle(
            font_size=9.0,
            axis_label_size=9.0,
            tick_label_size=8.0,
            title_size=9.0,
            legend_font_size=8.0,
            line_width=1.4,
            spine_width=0.9,
            tick_width=0.9,
            tick_length=3.5,
        ),
    ),
}


def list_presets() -> tuple[str, ...]:
    """Return registered preset names in deterministic insertion order."""
    return tuple(_PRESETS)


def get_preset(name: str = "publication") -> FigureSpec:
    """Return an immutable registered figure specification."""
    key = str(name).strip().lower()
    try:
        return _PRESETS[key]
    except KeyError as exc:
        raise VisualizationError(
            f"unknown visualization preset {name!r}; available presets: {list_presets()!r}"
        ) from exc


def register_preset(name: str, spec: FigureSpec, *, overwrite: bool = False) -> None:
    """Register a future project/journal preset without changing renderer internals."""
    key = str(name).strip().lower()
    if not key:
        raise VisualizationError("preset name must not be empty")
    if not isinstance(spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")
    if key in _PRESETS and not overwrite:
        raise VisualizationError(f"visualization preset {key!r} is already registered")
    _PRESETS[key] = spec
