from __future__ import annotations

import re

import matplotlib as mpl
import matplotlib.image as mpimg
import numpy as np
import pytest

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.visualization import (
    AnnotationSpec,
    ExportSpec,
    FigureSpec,
    LayoutSpec,
    PlotStyle,
    SeriesStyle,
    VisualizationError,
    export_figure,
    format_axis_label,
    get_preset,
    list_presets,
    render_curves,
)


def _curve(
    *,
    key="a",
    label="Catalyst A",
    x=(0.0, 1.0, 2.0),
    y=(1.0, 2.0, 3.0),
    x_name="potential",
    x_unit="V",
    y_name="current_density",
    y_unit="mA/cm^2",
):
    return Series(
        x=x,
        y=y,
        label=label,
        key=key,
        x_axis=Axis(x_name, unit=x_unit, label="Potential"),
        y_axis=Axis(y_name, unit=y_unit, label="Current density"),
    )


def test_layout_resolves_available_axes_size_from_physical_margins():
    layout = LayoutSpec(
        figure_width_in=4.0,
        figure_height_in=3.0,
        left_margin_in=0.5,
        right_margin_in=0.25,
        bottom_margin_in=0.4,
        top_margin_in=0.2,
    )

    assert layout.available_axes_size_in() == pytest.approx((3.25, 2.4))
    assert layout.resolved_axes_size_in() == pytest.approx((3.25, 2.4))


def test_layout_supports_explicit_axes_size_and_aspect_ratio():
    explicit = LayoutSpec(
        figure_width_in=4.0,
        figure_height_in=3.0,
        left_margin_in=0.5,
        right_margin_in=0.2,
        bottom_margin_in=0.4,
        top_margin_in=0.2,
        axes_width_in=2.4,
        axes_height_in=1.6,
        axes_aspect=1.5,
    )
    fitted = LayoutSpec(
        figure_width_in=4.0,
        figure_height_in=3.0,
        left_margin_in=0.5,
        right_margin_in=0.2,
        bottom_margin_in=0.4,
        top_margin_in=0.2,
        axes_aspect=2.0,
    )

    assert explicit.resolved_axes_size_in() == pytest.approx((2.4, 1.6))
    width, height = fitted.resolved_axes_size_in()
    assert width / height == pytest.approx(2.0)


def test_layout_rejects_conflicting_or_impossible_geometry():
    with pytest.raises(VisualizationError, match="conflicts"):
        LayoutSpec(axes_width_in=2.0, axes_height_in=2.0, axes_aspect=2.0)
    with pytest.raises(VisualizationError, match="do not fit"):
        LayoutSpec(figure_width_in=3.0, axes_width_in=4.0)
    with pytest.raises(VisualizationError, match="no positive axes"):
        LayoutSpec(
            figure_width_in=1.0,
            left_margin_in=0.6,
            right_margin_in=0.4,
        )


def test_figure_spec_round_trips_through_plain_dictionary():
    spec = (
        FigureSpec(
            layout=LayoutSpec(axes_aspect=1.4),
            style=PlotStyle(axis_unit_format="slash"),
            export=ExportSpec(dpi=450),
            xlim=(-0.2, 1.0),
            ylim=(-10, 5),
            annotations=(AnnotationSpec("a", 0.03, 0.95),),
        )
        .with_series_style("pb3", color="#222222", line_width=1.8, marker="o")
        .updated(title="Comparison")
    )

    payload = spec.to_dict()
    restored = FigureSpec.from_dict(payload)

    assert restored.to_dict() == payload
    assert restored.series_styles["pb3"].line_width == pytest.approx(1.8)


def test_presets_are_starting_templates_and_overrides_do_not_mutate_them():
    assert {"publication", "compact", "wide"}.issubset(set(list_presets()))
    base = get_preset("publication")
    customized = base.with_style(line_width=2.2).with_layout(axes_width_in=2.5)

    assert customized.style.line_width == pytest.approx(2.2)
    assert customized.layout.axes_width_in == pytest.approx(2.5)
    assert base.style.line_width != customized.style.line_width
    assert base.layout.axes_width_in is None


def test_format_axis_label_is_owned_by_visualization_layer():
    axis = Axis("potential", label="Potential", unit="V")

    assert format_axis_label(axis) == "Potential (V)"
    assert format_axis_label(axis, unit_format="slash") == "Potential / V"
    assert format_axis_label(axis, unit_format="none") == "Potential"


def test_render_curves_respects_exact_figure_and_axes_physical_size():
    spec = FigureSpec(
        layout=LayoutSpec(
            figure_width_in=4.0,
            figure_height_in=3.0,
            left_margin_in=0.5,
            right_margin_in=0.2,
            bottom_margin_in=0.4,
            top_margin_in=0.2,
            axes_width_in=2.4,
            axes_height_in=1.6,
        )
    )

    figure, ax = render_curves(_curve(), spec)
    bounds = ax.get_position()

    assert figure.get_size_inches() == pytest.approx((4.0, 3.0))
    assert bounds.width * figure.get_figwidth() == pytest.approx(2.4)
    assert bounds.height * figure.get_figheight() == pytest.approx(1.6)
    assert bounds.x0 * figure.get_figwidth() == pytest.approx(0.5)
    assert bounds.y0 * figure.get_figheight() == pytest.approx(0.4)


def test_render_dataset_preserves_order_and_applies_stable_key_styles():
    first = _curve(key="rep-1", label="Pb3-N/C", y=(1, 2, 3))
    second = _curve(key="rep-2", label="Pb3-N/C", y=(3, 2, 1))
    dataset = Dataset([first, second])
    spec = (
        FigureSpec()
        .with_series_style("rep-1", color="#111111", line_width=2.0)
        .with_series_style("rep-2", color="#999999", marker="s")
    )

    _, ax = render_curves(dataset, spec)

    assert len(ax.lines) == 2
    np.testing.assert_allclose(ax.lines[0].get_ydata(), first.y)
    np.testing.assert_allclose(ax.lines[1].get_ydata(), second.y)
    assert ax.lines[0].get_color() == "#111111"
    assert ax.lines[0].get_linewidth() == pytest.approx(2.0)
    assert ax.lines[1].get_marker() == "s"


def test_render_rejects_incompatible_axes_units():
    dataset = Dataset(
        [
            _curve(key="a", x_unit="V"),
            _curve(key="b", x_unit="mV"),
        ]
    )
    with pytest.raises(VisualizationError, match="x-axis"):
        render_curves(dataset)


def test_render_rejects_complex_data_in_generic_curve_renderer():
    source = _curve(y=np.array([1 + 1j, 2 + 0j, 3 - 1j]))
    with pytest.raises(VisualizationError, match="complex-data"):
        render_curves(source)


def test_render_rejects_unknown_style_key_and_all_hidden_data():
    source = _curve(key="a")
    with pytest.raises(VisualizationError, match="not present"):
        render_curves(source, FigureSpec().with_series_style("missing", color="black"))
    with pytest.raises(VisualizationError, match="all curves are hidden"):
        render_curves(source, FigureSpec().with_series_style("a", visible=False))


def test_render_uses_axis_label_format_overrides_limits_and_annotation():
    spec = FigureSpec(
        style=PlotStyle(axis_unit_format="slash"),
        xlabel="E vs RHE (V)",
        ylabel="jCO (mA cm$^{-2}$)",
        xlim=(0.0, 1.0),
        ylim=(-5.0, 5.0),
        annotations=(AnnotationSpec("a", 0.04, 0.96, font_size=9),),
    )

    _, ax = render_curves(_curve(), spec)

    assert ax.get_xlabel() == "E vs RHE (V)"
    assert ax.get_ylabel() == "jCO (mA cm$^{-2}$)"
    assert ax.get_xlim() == pytest.approx((0.0, 1.0))
    assert ax.get_ylim() == pytest.approx((-5.0, 5.0))
    assert ax.texts[0].get_text() == "a"
    assert ax.texts[0].get_fontsize() == pytest.approx(9)


def test_render_auto_legend_for_multiple_labeled_curves_only():
    single_figure, single_ax = render_curves(_curve())
    multi = Dataset(
        [
            _curve(key="a", label="A"),
            _curve(key="b", label="B", y=(2, 3, 4)),
        ]
    )
    multi_figure, multi_ax = render_curves(multi)

    assert single_ax.get_legend() is None
    assert multi_ax.get_legend() is not None
    # Keep references alive until assertions finish; renderer does not auto-close them.
    assert single_figure.canvas is not None
    assert multi_figure.canvas is not None


def test_render_preserves_nan_as_line_gap_data():
    source = _curve(y=(1.0, np.nan, 3.0))
    _, ax = render_curves(source)

    assert np.isnan(ax.lines[0].get_ydata()[1])


def test_render_does_not_leak_rcparams():
    original_family = list(mpl.rcParams["font.family"])
    original_font_size = mpl.rcParams["font.size"]
    spec = FigureSpec(style=PlotStyle(font_family="DejaVu Serif", font_size=13.0))

    render_curves(_curve(), spec)

    assert list(mpl.rcParams["font.family"]) == original_family
    assert mpl.rcParams["font.size"] == original_font_size


def test_png_export_has_exact_pixel_dimensions(tmp_path):
    spec = FigureSpec(
        layout=LayoutSpec(
            figure_width_in=2.0,
            figure_height_in=1.0,
            left_margin_in=0.25,
            right_margin_in=0.10,
            bottom_margin_in=0.25,
            top_margin_in=0.10,
        ),
        export=ExportSpec(dpi=120),
    )
    figure, _ = render_curves(_curve(), spec)
    path = export_figure(figure, tmp_path / "figure.png", spec=spec)
    image = mpimg.imread(path)

    assert image.shape[:2] == (120, 240)
    assert figure.get_size_inches() == pytest.approx((2.0, 1.0))


def test_svg_and_pdf_export_succeed_without_tight_bbox_size_drift(tmp_path):
    spec = FigureSpec(
        layout=LayoutSpec(
            figure_width_in=2.0,
            figure_height_in=1.0,
            left_margin_in=0.25,
            right_margin_in=0.10,
            bottom_margin_in=0.25,
            top_margin_in=0.10,
        )
    )
    figure, _ = render_curves(_curve(), spec)
    svg_path = export_figure(figure, tmp_path / "figure.svg", spec=spec)
    pdf_path = export_figure(figure, tmp_path / "figure.pdf", spec=spec)

    svg = svg_path.read_text(encoding="utf-8")
    assert re.search(r'width="144(?:\.0+)?pt"', svg)
    assert re.search(r'height="72(?:\.0+)?pt"', svg)
    assert pdf_path.read_bytes().startswith(b"%PDF")
    assert figure.get_size_inches() == pytest.approx((2.0, 1.0))


def test_export_rejects_invalid_format_and_dpi(tmp_path):
    figure, _ = render_curves(_curve())
    with pytest.raises(VisualizationError, match="export format"):
        export_figure(figure, tmp_path / "figure.jpg")
    with pytest.raises(VisualizationError, match="dpi"):
        export_figure(figure, tmp_path / "figure.png", dpi=0)


def test_series_style_can_override_display_label_without_changing_series():
    source = _curve(key="a", label="Original")
    spec = FigureSpec(show_legend=True).with_series_style(
        "a",
        SeriesStyle(label="Rendered label", marker="o"),
    )

    _, ax = render_curves(source, spec)

    assert source.label == "Original"
    assert ax.lines[0].get_label() == "Rendered label"
    assert ax.get_legend() is not None
