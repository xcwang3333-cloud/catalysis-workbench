"""Versioned source-controlled publication figure presets."""

from __future__ import annotations

from dataclasses import dataclass

from catalysis_workbench._canonical_json import (
    canonical_json_bytes,
    canonical_json_sha256,
)

from .specs import ExportSpec, FigureSpec, LayoutSpec, PlotStyle


@dataclass(frozen=True, slots=True)
class _PublicationPresetAsset:
    name: str
    asset_version: int
    figure_spec: FigureSpec

    def __post_init__(self) -> None:
        if type(self.name) is not str or not self.name:
            raise TypeError("publication preset name must be a non-empty string")
        if self.name != self.name.strip():
            raise ValueError("publication preset name must not contain surrounding whitespace")
        if type(self.asset_version) is not int or self.asset_version <= 0:
            raise ValueError("publication preset asset_version must be a positive integer")
        if not self.name.endswith(f".v{self.asset_version}"):
            raise ValueError("publication preset name/version mismatch")
        if not isinstance(self.figure_spec, FigureSpec):
            raise TypeError("publication preset figure_spec must be a FigureSpec")


_STANDARD_V1 = FigureSpec(
    layout=LayoutSpec(
        figure_width_in=3.5,
        figure_height_in=2.625,
        left_margin_in=0.55,
        right_margin_in=0.15,
        bottom_margin_in=0.48,
        top_margin_in=0.15,
        axes_width_in=None,
        axes_height_in=None,
        axes_aspect=None,
    ),
    style=PlotStyle(
        font_family="DejaVu Sans",
        font_size=8.0,
        axis_label_size=8.0,
        tick_label_size=7.0,
        title_size=8.0,
        line_width=1.2,
        line_style="-",
        marker=None,
        marker_size=4.0,
        marker_edge_width=0.8,
        bar_group_width=0.8,
        errorbar_capsize=2.5,
        spine_width=0.8,
        tick_length=3.0,
        tick_width=0.8,
        tick_direction="in",
        minor_ticks=True,
        top_ticks=True,
        right_ticks=True,
        legend_font_size=7.0,
        legend_location="best",
        legend_frame=False,
        axis_unit_format="parentheses",
        color_cycle=(
            "#0C5DA5",
            "#00B945",
            "#FF9500",
            "#FF2C00",
            "#845B97",
            "#474747",
        ),
    ),
    export=ExportSpec(
        dpi=600,
        transparent=False,
        svg_fonttype="none",
        pdf_fonttype=42,
    ),
    xlabel=None,
    ylabel=None,
    title=None,
    xlim=None,
    ylim=None,
    xscale="linear",
    yscale="linear",
    show_legend=None,
    annotations=(),
    series_styles={},
    category_styles={},
)

_COMPACT_V1 = _STANDARD_V1.with_layout(
    figure_width_in=3.35,
    figure_height_in=2.30,
    left_margin_in=0.52,
    right_margin_in=0.12,
    bottom_margin_in=0.43,
    top_margin_in=0.12,
    axes_width_in=None,
    axes_height_in=None,
    axes_aspect=None,
).with_style(
    font_size=7.5,
    axis_label_size=7.5,
    tick_label_size=6.8,
    title_size=7.5,
    line_width=1.1,
    spine_width=0.7,
    tick_length=2.8,
    tick_width=0.7,
    legend_font_size=6.8,
)

_WIDE_V1 = _STANDARD_V1.with_layout(
    figure_width_in=7.0,
    figure_height_in=3.5,
    left_margin_in=0.65,
    right_margin_in=0.20,
    bottom_margin_in=0.55,
    top_margin_in=0.18,
    axes_width_in=None,
    axes_height_in=None,
    axes_aspect=None,
).with_style(
    font_size=9.0,
    axis_label_size=9.0,
    tick_label_size=8.0,
    title_size=9.0,
    line_width=1.4,
    spine_width=0.9,
    tick_length=3.5,
    tick_width=0.9,
    legend_font_size=8.0,
)

_PUBLICATION_PRESETS = (
    _PublicationPresetAsset(
        name="catalysis.publication.standard.v1",
        asset_version=1,
        figure_spec=_STANDARD_V1,
    ),
    _PublicationPresetAsset(
        name="catalysis.publication.compact.v1",
        asset_version=1,
        figure_spec=_COMPACT_V1,
    ),
    _PublicationPresetAsset(
        name="catalysis.publication.wide.v1",
        asset_version=1,
        figure_spec=_WIDE_V1,
    ),
)


def _get_asset(name: str) -> _PublicationPresetAsset:
    if type(name) is not str:
        raise TypeError("publication preset name must be a string")
    for asset in _PUBLICATION_PRESETS:
        if asset.name == name:
            return asset
    raise KeyError(name)


def list_publication_presets() -> tuple[str, ...]:
    """Return bundled publication preset names in source-controlled order."""

    return tuple(asset.name for asset in _PUBLICATION_PRESETS)


def get_publication_preset(name: str) -> FigureSpec:
    """Return one exact immutable bundled publication figure specification."""

    return _get_asset(name).figure_spec


def publication_preset_manifest(name: str) -> dict[str, object]:
    """Return a deterministic JSON-safe manifest suitable for supplementary information."""

    asset = _get_asset(name)
    figure_spec = asset.figure_spec.to_dict()
    manifest: dict[str, object] = {
        "manifest_schema_version": 1,
        "preset_name": asset.name,
        "asset_version": asset.asset_version,
        "figure_spec": figure_spec,
        "figure_spec_sha256": canonical_json_sha256(figure_spec),
    }
    canonical_json_bytes(manifest)
    return manifest
