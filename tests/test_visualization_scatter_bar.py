from __future__ import annotations

import matplotlib as mpl
import matplotlib.image as mpimg
import numpy as np
import pytest
from matplotlib.colors import to_rgba
from matplotlib.container import BarContainer, ErrorbarContainer

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.visualization import (
    BarCategory,
    BarData,
    BarSeries,
    CategoryStyle,
    ExportSpec,
    FigureSpec,
    LayoutSpec,
    PlotStyle,
    ScatterError,
    VisualizationError,
    export_figure,
    render_bars,
    render_scatter,
)


def _xy(
    *,
    key: str = "a",
    label: str = "Catalyst",
    x=(0.1, 0.2, 0.3),
    y=(1.0, 2.0, 3.0),
    reference: str = "RHE",
    normalization: str = "geometric_area",
) -> Series:
    return Series(
        x=x,
        y=y,
        key=key,
        label=label,
        x_axis=Axis(
            "potential",
            unit="V",
            label="Potential",
            metadata={"reference": reference},
        ),
        y_axis=Axis(
            "current_density",
            unit="mA/cm^2",
            label="Current density",
            metadata={"normalization": normalization},
        ),
    )


def _bar_data(*, errors: bool = False) -> BarData:
    categories = (
        BarCategory("pb1", "Pb1-N/C"),
        BarCategory("pb2", "Pb2-N/C"),
        BarCategory("pb3", "Pb3-N/C"),
    )
    first_errors = (0.2, 0.3, 0.4) if errors else None
    second_errors = (0.1, 0.2, 0.2) if errors else None
    return BarData(
        categories=categories,
        series=(
            BarSeries("co", (10.0, 20.0, 30.0), "CO", first_errors),
            BarSeries("h2", (5.0, 4.0, 3.0), "H2", second_errors),
        ),
        x_axis=Axis("catalyst", label="Catalyst"),
        y_axis=Axis("faradaic_efficiency", unit="%", label="FE"),
    )


def test_figure_spec_round_trip_includes_bar_and_category_controls():
    spec = FigureSpec(
        style=PlotStyle(bar_group_width=0.7, errorbar_capsize=3.5)
    ).with_category_style(
        "pb3",
        CategoryStyle(color="#222222", alpha=0.8, label="", visible=True),
    )

    payload = spec.to_dict()
    restored = FigureSpec.from_dict(payload)

    assert restored.to_dict() == payload
    assert restored.style.bar_group_width == pytest.approx(0.7)
    assert restored.style.errorbar_capsize == pytest.approx(3.5)
    assert restored.category_styles["pb3"].label == ""


def test_scatter_preserves_order_and_uses_stable_key_styles():
    first = _xy(key="rep-1", label="same", y=(1.0, 2.0, 3.0))
    second = _xy(key="rep-2", label="same", y=(3.0, 2.0, 1.0))
    spec = (
        FigureSpec()
        .with_series_style("rep-1", color="#111111", marker="s", marker_size=5.0)
        .with_series_style("rep-2", color="#999999", marker="^", marker_size=6.0)
    )

    _, ax = render_scatter(Dataset([first, second]), spec)

    assert len(ax.collections) == 2
    np.testing.assert_allclose(ax.collections[0].get_offsets()[:, 1], first.y)
    np.testing.assert_allclose(ax.collections[1].get_offsets()[:, 1], second.y)
    assert ax.collections[0].get_sizes()[0] == pytest.approx(25.0)
    assert ax.collections[1].get_sizes()[0] == pytest.approx(36.0)
    assert ax.collections[0].get_facecolors()[0] == pytest.approx(to_rgba("#111111"))
    assert ax.collections[1].get_facecolors()[0] == pytest.approx(to_rgba("#999999"))


def test_scatter_draws_only_explicit_error_bars_and_supports_stable_key_mapping():
    first = _xy(key="a", y=(1.0, 2.0, 3.0))
    second = _xy(key="b", y=(2.0, 3.0, 4.0))
    dataset = Dataset([first, second])

    _, plain_ax = render_scatter(dataset)
    assert not any(isinstance(item, ErrorbarContainer) for item in plain_ax.containers)

    _, error_ax = render_scatter(
        dataset,
        errors={"b": ScatterError(yerr=(0.1, 0.2, 0.3))},
    )
    error_containers = [
        item for item in error_ax.containers if isinstance(item, ErrorbarContainer)
    ]
    assert len(error_containers) == 1

    with pytest.raises(VisualizationError, match="not present"):
        render_scatter(dataset, errors={"missing": ScatterError(yerr=(0.1, 0.2, 0.3))})


def test_single_scatter_error_does_not_require_a_series_key():
    source = _xy(key="").with_data(key="")
    _, ax = render_scatter(source, errors=ScatterError(yerr=(0.1, 0.2, 0.3)))
    assert any(isinstance(item, ErrorbarContainer) for item in ax.containers)


def test_scatter_error_validation_is_explicit():
    with pytest.raises(VisualizationError, match="requires"):
        ScatterError()
    with pytest.raises(VisualizationError, match="non-negative"):
        ScatterError(yerr=(0.1, -0.2, 0.3))
    with pytest.raises(VisualizationError, match="contain 3 values"):
        render_scatter(_xy(), errors=ScatterError(yerr=(0.1, 0.2)))
    with pytest.raises(VisualizationError, match="one Series"):
        render_scatter(
            Dataset([_xy(key="a"), _xy(key="b")]),
            errors=ScatterError(yerr=(0.1, 0.2, 0.3)),
        )


def test_scatter_reuses_curve_axis_compatibility_guards():
    incompatible = Dataset(
        [
            _xy(key="rhe", reference="RHE"),
            _xy(key="agcl", reference="Ag/AgCl"),
        ]
    )
    with pytest.raises(VisualizationError, match="reference"):
        render_scatter(incompatible)

    complex_series = _xy(y=np.array([1 + 1j, 2 + 0j, 3 - 1j]))
    with pytest.raises(VisualizationError, match="complex-data"):
        render_scatter(complex_series)


def test_bar_data_requires_stable_unique_keys_and_aligned_values():
    with pytest.raises(VisualizationError, match="key must not be empty"):
        BarCategory("", "A")
    with pytest.raises(VisualizationError, match="unique"):
        BarData(
            categories=(BarCategory("a", "A"), BarCategory("a", "A2")),
            series=(BarSeries("s", (1.0, 2.0)),),
        )
    with pytest.raises(VisualizationError, match="one value per category"):
        BarData(
            categories=(BarCategory("a", "A"), BarCategory("b", "B")),
            series=(BarSeries("s", (1.0,)),),
        )
    with pytest.raises(VisualizationError, match="non-negative"):
        BarSeries("s", (1.0, 2.0), errors=(0.1, -0.1))
    with pytest.raises(VisualizationError, match="real numeric"):
        BarSeries("s", np.array([1 + 1j, 2 + 0j]))


def test_grouped_bars_preserve_category_and_series_order():
    data = _bar_data()
    spec = FigureSpec(style=PlotStyle(bar_group_width=0.8))

    _, ax = render_bars(data, spec)
    containers = [item for item in ax.containers if isinstance(item, BarContainer)]

    assert len(containers) == 2
    first_centers = [patch.get_x() + patch.get_width() / 2 for patch in containers[0]]
    second_centers = [patch.get_x() + patch.get_width() / 2 for patch in containers[1]]
    assert first_centers == pytest.approx((-0.2, 0.8, 1.8))
    assert second_centers == pytest.approx((0.2, 1.2, 2.2))
    assert [patch.get_height() for patch in containers[0]] == pytest.approx((10, 20, 30))
    assert [patch.get_height() for patch in containers[1]] == pytest.approx((5, 4, 3))
    assert [tick.get_text() for tick in ax.get_xticklabels()] == [
        "Pb1-N/C",
        "Pb2-N/C",
        "Pb3-N/C",
    ]


def test_bar_series_and_category_styles_use_stable_keys_not_labels():
    data = BarData(
        categories=(
            BarCategory("a", "same"),
            BarCategory("b", "same"),
            BarCategory("c", "same"),
        ),
        series=(BarSeries("metric", (1.0, 2.0, 3.0), "Metric"),),
        y_axis=Axis("metric", unit="a.u."),
    )
    spec = (
        FigureSpec(show_legend=True)
        .with_series_style("metric", color="#111111", label="Rendered metric")
        .with_category_style("b", color="#999999", label="")
        .with_category_style("c", visible=False)
    )

    _, ax = render_bars(data, spec)
    container = next(item for item in ax.containers if isinstance(item, BarContainer))

    assert len(container.patches) == 2
    assert container.patches[0].get_facecolor() == pytest.approx(to_rgba("#111111"))
    assert container.patches[1].get_facecolor() == pytest.approx(to_rgba("#999999"))
    assert [tick.get_text() for tick in ax.get_xticklabels()] == ["same", ""]
    assert ax.get_legend() is not None
    assert [text.get_text() for text in ax.get_legend().get_texts()] == ["Rendered metric"]


def test_bar_error_bars_exist_only_when_explicitly_supplied():
    _, plain_ax = render_bars(_bar_data(errors=False))
    plain_bars = [item for item in plain_ax.containers if isinstance(item, BarContainer)]
    assert all(container.errorbar is None for container in plain_bars)

    _, error_ax = render_bars(_bar_data(errors=True))
    error_bars = [item for item in error_ax.containers if isinstance(item, BarContainer)]
    assert all(container.errorbar is not None for container in error_bars)


def test_bar_renderer_rejects_unknown_keys_nonlinear_xscale_and_all_hidden():
    data = _bar_data()
    with pytest.raises(VisualizationError, match="series style keys"):
        render_bars(data, FigureSpec().with_series_style("missing", color="black"))
    with pytest.raises(VisualizationError, match="category style keys"):
        render_bars(data, FigureSpec().with_category_style("missing", color="black"))
    with pytest.raises(VisualizationError, match="linear xscale"):
        render_bars(data, FigureSpec(xscale="log"))

    hidden_categories = FigureSpec()
    for category in data.categories:
        hidden_categories = hidden_categories.with_category_style(
            category.key, visible=False
        )
    with pytest.raises(VisualizationError, match="all bar categories"):
        render_bars(data, hidden_categories)

    hidden_series = FigureSpec()
    for series in data.series:
        hidden_series = hidden_series.with_series_style(series.key, visible=False)
    with pytest.raises(VisualizationError, match="all bar series"):
        render_bars(data, hidden_series)


def test_scatter_and_bars_share_physical_geometry_blank_labels_and_rc_isolation():
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
        ),
        xlabel="",
        ylabel="",
    )
    original_facecolor = mpl.rcParams["axes.facecolor"]
    original_grid = mpl.rcParams["axes.grid"]
    try:
        mpl.rcParams["axes.facecolor"] = "red"
        mpl.rcParams["axes.grid"] = True

        scatter_figure, scatter_ax = render_scatter(_xy(), spec)
        bar_figure, bar_ax = render_bars(_bar_data(), spec)

        for figure, ax in ((scatter_figure, scatter_ax), (bar_figure, bar_ax)):
            bounds = ax.get_position()
            assert figure.get_size_inches() == pytest.approx((4.0, 3.0))
            assert bounds.width * figure.get_figwidth() == pytest.approx(2.4)
            assert bounds.height * figure.get_figheight() == pytest.approx(1.6)
            assert bounds.x0 * figure.get_figwidth() == pytest.approx(0.5)
            assert bounds.y0 * figure.get_figheight() == pytest.approx(0.4)
            assert ax.get_xlabel() == ""
            assert ax.get_ylabel() == ""
            assert ax.get_facecolor() == pytest.approx((1.0, 1.0, 1.0, 1.0))
            assert not any(line.get_visible() for line in ax.get_xgridlines())
            assert not any(line.get_visible() for line in ax.get_ygridlines())

        assert mpl.rcParams["axes.facecolor"] == "red"
        assert mpl.rcParams["axes.grid"] is True
    finally:
        mpl.rcParams["axes.facecolor"] = original_facecolor
        mpl.rcParams["axes.grid"] = original_grid


def test_new_renderers_preserve_exact_png_export_size(tmp_path):
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

    scatter_figure, _ = render_scatter(_xy(), spec)
    scatter_path = export_figure(scatter_figure, tmp_path / "scatter.png", spec=spec)
    bar_figure, _ = render_bars(_bar_data(), spec)
    bar_path = export_figure(bar_figure, tmp_path / "bars.png", spec=spec)

    assert mpimg.imread(scatter_path).shape[:2] == (120, 240)
    assert mpimg.imread(bar_path).shape[:2] == (120, 240)
