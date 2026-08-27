from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError

import pytest

import catalysis_workbench.visualization.presets as runtime_presets
from catalysis_workbench._canonical_json import canonical_json_bytes
from catalysis_workbench.visualization import FigureSpec
from catalysis_workbench.visualization.publication_presets import (
    get_publication_preset,
    list_publication_presets,
    publication_preset_manifest,
)

PRESET_NAMES = (
    "catalysis.publication.standard.v1",
    "catalysis.publication.compact.v1",
    "catalysis.publication.wide.v1",
)
FIGURE_SPEC_SHA256 = {
    PRESET_NAMES[0]: "9022ff993c9ad8c8f7c0ea80111dda2fe9d31006c4f98bffdbb724dc165a0d5f",
    PRESET_NAMES[1]: "15daf234e7662e4af13bb7cbd61c51b1559001e7ed11d291a01b0aa26965edc6",
    PRESET_NAMES[2]: "f86f76fdd962c906a629f75a0c84b006ebbbdf7aa0f0bd3b687f5cac79882257",
}
EXPECTED_STANDARD = {
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
EXPECTED_COMPACT = deepcopy(EXPECTED_STANDARD)
EXPECTED_COMPACT["layout"].update(
    {
        "figure_width_in": 3.35,
        "figure_height_in": 2.30,
        "left_margin_in": 0.52,
        "right_margin_in": 0.12,
        "bottom_margin_in": 0.43,
        "top_margin_in": 0.12,
    }
)
EXPECTED_COMPACT["style"].update(
    {
        "font_size": 7.5,
        "axis_label_size": 7.5,
        "tick_label_size": 6.8,
        "title_size": 7.5,
        "line_width": 1.1,
        "spine_width": 0.7,
        "tick_length": 2.8,
        "tick_width": 0.7,
        "legend_font_size": 6.8,
    }
)
EXPECTED_WIDE = deepcopy(EXPECTED_STANDARD)
EXPECTED_WIDE["layout"].update(
    {
        "figure_width_in": 7.0,
        "figure_height_in": 3.5,
        "left_margin_in": 0.65,
        "right_margin_in": 0.20,
        "bottom_margin_in": 0.55,
        "top_margin_in": 0.18,
    }
)
EXPECTED_WIDE["style"].update(
    {
        "font_size": 9.0,
        "axis_label_size": 9.0,
        "tick_label_size": 8.0,
        "title_size": 9.0,
        "line_width": 1.4,
        "spine_width": 0.9,
        "tick_length": 3.5,
        "tick_width": 0.9,
        "legend_font_size": 8.0,
    }
)
EXPECTED_SPECS = {
    PRESET_NAMES[0]: EXPECTED_STANDARD,
    PRESET_NAMES[1]: EXPECTED_COMPACT,
    PRESET_NAMES[2]: EXPECTED_WIDE,
}


def test_publication_preset_bundle_contents_are_exact() -> None:
    assert list_publication_presets() == PRESET_NAMES
    for name in PRESET_NAMES:
        preset = get_publication_preset(name)
        assert isinstance(preset, FigureSpec)
        assert preset.to_dict() == EXPECTED_SPECS[name]


def test_publication_presets_are_immutable() -> None:
    for name in PRESET_NAMES:
        preset = get_publication_preset(name)
        with pytest.raises(FrozenInstanceError):
            preset.xlabel = "changed"  # type: ignore[misc]


def test_publication_preset_lookup_fails_closed() -> None:
    for name in (
        "",
        f" {PRESET_NAMES[0]}",
        f"{PRESET_NAMES[0]} ",
        PRESET_NAMES[0].upper(),
        "catalysis.publication.standard",
        "standard.v1",
        "publication",
        "compact",
        "wide",
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


def test_publication_preset_manifests_are_exact_and_deterministic() -> None:
    for name in PRESET_NAMES:
        expected = {
            "manifest_schema_version": 1,
            "preset_name": name,
            "asset_version": 1,
            "figure_spec": EXPECTED_SPECS[name],
            "figure_spec_sha256": FIGURE_SPEC_SHA256[name],
        }
        first = publication_preset_manifest(name)
        second = publication_preset_manifest(name)
        assert first == expected
        assert second == expected
        assert first is not second
        assert canonical_json_bytes(first) == canonical_json_bytes(second)


def test_publication_preset_manifests_are_detached() -> None:
    for name in PRESET_NAMES:
        first = publication_preset_manifest(name)
        figure_spec = first["figure_spec"]
        assert isinstance(figure_spec, dict)
        figure_spec["xlabel"] = "mutated"
        style = figure_spec["style"]
        assert isinstance(style, dict)
        style["font_size"] = 99.0

        second = publication_preset_manifest(name)
        assert second["figure_spec"] == EXPECTED_SPECS[name]
        assert second["figure_spec_sha256"] == FIGURE_SPEC_SHA256[name]


def test_publication_bundle_is_isolated_from_mutable_runtime_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime_presets, "_PRESETS", dict(runtime_presets._PRESETS))
    for name in PRESET_NAMES:
        runtime_presets.register_preset(
            name,
            FigureSpec().with_style(font_size=99.0),
            overwrite=True,
        )
        assert runtime_presets.get_preset(name).style.font_size == 99.0
        assert get_publication_preset(name).to_dict() == EXPECTED_SPECS[name]
        assert publication_preset_manifest(name)["figure_spec"] == EXPECTED_SPECS[name]
