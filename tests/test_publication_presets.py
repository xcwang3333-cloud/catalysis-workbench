from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from catalysis_workbench._canonical_json import canonical_json_bytes
from catalysis_workbench.visualization import FigureSpec
from catalysis_workbench.visualization.presets import (
    clear_presets,
    register_preset,
)
from catalysis_workbench.visualization.publication_presets import (
    get_publication_preset,
    list_publication_presets,
    publication_preset_manifest,
)

PRESET_NAME = "catalysis.publication.single-column.v1"
FIGURE_SPEC_SHA256 = "9022ff993c9ad8c8f7c0ea80111dda2fe9d31006c4f98bffdbb724dc165a0d5f"
EXPECTED_FIGURE_SPEC = {
    "layout": {
        "figure_width_in": 3.5,
        "figure_height_in": 2.625,
        "left_margin_in": 0.55,
        "right_margin_in": 0.15,
        "bottom_margin_in": 0.48,
        "top_margin_in": 0.15,
        "axes_width_in": None,
        "axes_height_in": None,
        "axes_aspect": None,
    },
    "style": {
        "font_family": "DejaVu Sans",
        "font_size": 8.0,
        "axis_label_size": 8.0,
        "tick_label_size": 7.0,
        "title_size": 8.0,
        "line_width": 1.2,
        "line_style": "-",
        "marker": None,
        "marker_size": 4.0,
        "marker_edge_width": 0.8,
        "bar_group_width": 0.8,
        "errorbar_capsize": 2.5,
        "spine_width": 0.8,
        "tick_length": 3.0,
        "tick_width": 0.8,
        "tick_direction": "in",
        "minor_ticks": True,
        "top_ticks": True,
        "right_ticks": True,
        "legend_font_size": 7.0,
        "legend_location": "best",
        "legend_frame": False,
        "axis_unit_format": "parentheses",
        "color_cycle": [
            "#0C5DA5",
            "#00B945",
            "#FF9500",
            "#FF2C00",
            "#845B97",
            "#474747",
        ],
    },
    "export": {
        "dpi": 600,
        "transparent": False,
        "svg_fonttype": "none",
        "pdf_fonttype": 42,
    },
    "xlabel": None,
    "ylabel": None,
    "title": None,
    "xlim": None,
    "ylim": None,
    "xscale": "linear",
    "yscale": "linear",
    "show_legend": None,
    "annotations": [],
    "series_styles": {},
    "category_styles": {},
}


def test_publication_preset_bundle_contents_are_exact() -> None:
    assert list_publication_presets() == (PRESET_NAME,)
    preset = get_publication_preset(PRESET_NAME)
    assert isinstance(preset, FigureSpec)
    assert preset.to_dict() == EXPECTED_FIGURE_SPEC


def test_publication_preset_is_immutable() -> None:
    preset = get_publication_preset(PRESET_NAME)
    with pytest.raises(FrozenInstanceError):
        preset.xlabel = "changed"  # type: ignore[misc]


def test_publication_preset_lookup_fails_closed() -> None:
    for name in (
        "",
        f" {PRESET_NAME}",
        f"{PRESET_NAME} ",
        PRESET_NAME.upper(),
        "catalysis.publication.single-column",
        "single-column.v1",
    ):
        with pytest.raises(KeyError):
            get_publication_preset(name)
        with pytest.raises(KeyError):
            publication_preset_manifest(name)

    for value in (None, 1, object()):
        with pytest.raises(TypeError):
            get_publication_preset(value)  # type: ignore[arg-type]
        with pytest.raises(TypeError):
            publication_preset_manifest(value)  # type: ignore[arg-type]


def test_publication_preset_manifest_is_exact_and_deterministic() -> None:
    expected = {
        "manifest_schema_version": 1,
        "preset_name": PRESET_NAME,
        "asset_version": 1,
        "figure_spec": EXPECTED_FIGURE_SPEC,
        "figure_spec_sha256": FIGURE_SPEC_SHA256,
    }
    first = publication_preset_manifest(PRESET_NAME)
    second = publication_preset_manifest(PRESET_NAME)
    assert first == expected
    assert second == expected
    assert first is not second
    assert canonical_json_bytes(first) == canonical_json_bytes(second)


def test_publication_preset_manifest_is_detached() -> None:
    first = publication_preset_manifest(PRESET_NAME)
    figure_spec = first["figure_spec"]
    assert isinstance(figure_spec, dict)
    figure_spec["xlabel"] = "mutated"
    style = figure_spec["style"]
    assert isinstance(style, dict)
    style["font_size"] = 99.0

    second = publication_preset_manifest(PRESET_NAME)
    assert second["figure_spec"] == EXPECTED_FIGURE_SPEC
    assert second["figure_spec_sha256"] == FIGURE_SPEC_SHA256


def test_publication_bundle_is_isolated_from_mutable_runtime_registry() -> None:
    clear_presets()
    try:
        register_preset(PRESET_NAME, FigureSpec().with_style(font_size=99.0))
        assert get_publication_preset(PRESET_NAME).to_dict() == EXPECTED_FIGURE_SPEC
        assert publication_preset_manifest(PRESET_NAME)["figure_spec"] == EXPECTED_FIGURE_SPEC
    finally:
        clear_presets()
