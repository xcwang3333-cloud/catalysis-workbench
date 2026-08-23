from __future__ import annotations

import pytest
from matplotlib.collections import PathCollection
from matplotlib.container import ErrorbarContainer

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.visualization import (
    BarCategory,
    BarData,
    BarSeries,
    CategoryStyle,
    FigureSpec,
    ScatterError,
    SeriesStyle,
    VisualizationError,
    render_bars,
    render_scatter,
)


def _series(*, key: str, y=(1.0, 2.0, 3.0)) -> Series:
    return Series(
        x=(0.1, 0.2, 0.3),
        y=y,
        key=key,
        label=key,
        x_axis=Axis("potential", unit="V", metadata={"reference": "RHE"}),
        y_axis=Axis(
            "current_density",
            unit="mA/cm^2",
            metadata={"normalization": "geometric_area"},
        ),
    )


def _bars() -> BarData:
    return BarData(
        categories=(
            BarCategory("a", "A"),
            BarCategory("b", "B"),
            BarCategory("c", "C"),
        ),
        series=(BarSeries("metric", (1.0, 2.0, 3.0), "Metric"),),
        x_axis=Axis("catalyst", label="Catalyst"),
        y_axis=Axis("metric", unit="a.u.", label="Metric"),
    )


def test_hidden_scatter_series_still_requires_aligned_explicit_error_vectors():
    data = Dataset([_series(key="a"), _series(key="b")])
    spec = FigureSpec().with_series_style("b", visible=False)

    with pytest.raises(VisualizationError, match="contain 3 values"):
        render_scatter(
            data,
            spec,
            errors={"b": ScatterError(yerr=(0.1, 0.2))},
        )


def test_figure_spec_rejects_normalized_style_key_collisions():
    with pytest.raises(VisualizationError, match="series style keys.*unique"):
        FigureSpec(
            series_styles={
                1: SeriesStyle(color="#111111"),
                "1": SeriesStyle(color="#222222"),
            }
        )

    with pytest.raises(VisualizationError, match="category style keys.*unique"):
        FigureSpec(
            category_styles={
                "pb3": CategoryStyle(color="#111111"),
                " pb3 ": CategoryStyle(color="#222222"),
            }
        )


def test_figure_spec_from_dict_preserves_collision_detection_until_validation():
    payload = FigureSpec().to_dict()
    payload["series_styles"] = {1: {}, "1": {}}

    with pytest.raises(VisualizationError, match="series style keys.*unique"):
        FigureSpec.from_dict(payload)


def test_categorical_bar_axis_has_no_minor_x_ticks_but_keeps_numeric_y_minors():
    _, ax = render_bars(_bars())

    assert len(ax.xaxis.get_minorticklocs()) == 0
    assert len(ax.yaxis.get_minorticklocs()) > 0


def test_scatter_error_artists_inherit_series_alpha_and_zorder():
    spec = FigureSpec().with_series_style(
        "a",
        color="#222222",
        alpha=0.35,
        zorder=4.0,
    )
    _, ax = render_scatter(
        _series(key="a"),
        spec,
        errors=ScatterError(yerr=(0.1, 0.2, 0.3)),
    )

    marker = next(item for item in ax.collections if isinstance(item, PathCollection))
    error = next(item for item in ax.containers if isinstance(item, ErrorbarContainer))
    error_collections = error.lines[2]

    assert marker.get_alpha() == pytest.approx(0.35)
    assert marker.get_zorder() == pytest.approx(4.0)
    assert error_collections
    assert all(item.get_alpha() == pytest.approx(0.35) for item in error_collections)
    assert all(item.get_zorder() == pytest.approx(4.0) for item in error_collections)
