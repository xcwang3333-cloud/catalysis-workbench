"""Publication-adapter tests for already normalized activity data."""

from __future__ import annotations

import pytest

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.experimental.echem import (
    ActivityNormalizationError,
    normalize_activity_series,
    plot_activity,
)
from catalysis_workbench.visualization import FigureSpec, ScatterError, VisualizationError


def _current(key: str, value: float = -2.0) -> Series:
    return Series(
        x=(-0.7,),
        y=(value,),
        key=key,
        label=key,
        x_axis=Axis("potential", unit="V", metadata={"reference": "RHE"}),
        y_axis=Axis("current", unit="mA"),
    )


def _activity(key: str, *, basis: str, denominator_mg: float) -> Series:
    return normalize_activity_series(
        _current(key),
        basis=basis,  # type: ignore[arg-type]
        denominator_value=denominator_mg,
        denominator_unit="mg",
        output_unit="A/g",
    )


def test_activity_scatter_and_curve_delegate_to_shared_renderers():
    data = Dataset(
        [
            _activity("a", basis="catalyst_mass", denominator_mg=1.0),
            _activity("b", basis="catalyst_mass", denominator_mg=2.0),
        ]
    )
    fig_scatter, ax_scatter = plot_activity(data)
    fig_curve, ax_curve = plot_activity(data, kind="curve")
    assert fig_scatter is ax_scatter.figure
    assert fig_curve is ax_curve.figure
    assert len(ax_scatter.collections) >= 2
    assert len(ax_curve.lines) >= 2


def test_same_basis_different_denominator_values_remain_plot_compatible():
    left = _activity("a", basis="catalyst_mass", denominator_mg=1.0)
    right = _activity("b", basis="catalyst_mass", denominator_mg=2.0)
    fig, ax = plot_activity(Dataset([left, right]), kind="curve")
    assert fig is ax.figure
    assert len(ax.lines) == 2


def test_different_mass_denominator_bases_cannot_silently_overlay():
    catalyst = _activity("cat", basis="catalyst_mass", denominator_mg=2.0)
    metal = _activity("metal", basis="metal_mass", denominator_mg=2.0)
    assert catalyst.y_axis.unit == metal.y_axis.unit == "A/g"
    with pytest.raises(VisualizationError, match="normalization"):
        plot_activity(Dataset([catalyst, metal]), kind="curve")


def test_curve_rejects_scatter_errors_and_wrong_semantics_or_basis():
    data = _activity("a", basis="catalyst_mass", denominator_mg=1.0)
    with pytest.raises(ActivityNormalizationError, match="kind='scatter'"):
        plot_activity(
            data,
            FigureSpec(),
            kind="curve",
            errors=ScatterError(yerr=(0.1,)),
        )

    wrong = Series(
        x=(-0.7,),
        y=(-1.0,),
        x_axis=data.x_axis,
        y_axis=Axis("current", unit="A"),
    )
    with pytest.raises(ActivityNormalizationError, match="y_axis.name='activity'"):
        plot_activity(wrong)

    bad_basis = Series(
        x=data.x,
        y=data.y,
        key=data.key,
        label=data.label,
        x_axis=data.x_axis,
        y_axis=Axis("activity", unit="A/g", metadata={"normalization": "generic"}),
    )
    with pytest.raises(ActivityNormalizationError, match="normalization metadata"):
        plot_activity(bad_basis)
