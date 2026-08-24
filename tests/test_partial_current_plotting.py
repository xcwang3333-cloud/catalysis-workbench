from __future__ import annotations

import pytest

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.experimental.echem import (
    PartialCurrentDensityError,
    partial_current_density_dataset,
    partial_current_density_series,
    plot_partial_current_density,
)
from catalysis_workbench.visualization import FigureSpec, ScatterError


def _total_current() -> Series:
    return Series(
        x=(-0.5, -0.6, -0.7),
        y=(-20.0, -50.0, -80.0),
        key="total",
        label="Total",
        x_axis=Axis(
            "potential",
            unit="V",
            label="Potential",
            metadata={"reference": "RHE"},
        ),
        y_axis=Axis(
            "current_density",
            unit="mA cm^-2",
            label="Current density",
            metadata={"normalization": "geometric_area"},
        ),
    )


def _fe(key: str, values: tuple[float, ...]) -> Series:
    return Series(
        x=(-0.5, -0.6, -0.7),
        y=values,
        key=key,
        label=key,
        x_axis=_total_current().x_axis,
        y_axis=Axis("faradaic_efficiency", unit="%"),
    )


def _fe_dataset() -> Dataset:
    return Dataset(
        [
            _fe("CO", (80.0, 90.0, 95.0)),
            _fe("H2", (20.0, 10.0, 5.0)),
        ]
    )


def test_scatter_and_curve_plotting_delegate_to_shared_renderers():
    data = partial_current_density_dataset(_total_current(), _fe_dataset())

    fig_scatter, ax_scatter = plot_partial_current_density(data)
    fig_curve, ax_curve = plot_partial_current_density(data, kind="curve")

    assert fig_scatter is ax_scatter.figure
    assert fig_curve is ax_curve.figure
    assert len(ax_scatter.collections) >= 2
    assert len(ax_curve.lines) >= 2


def test_curve_plot_rejects_scatter_error_input():
    data = partial_current_density_series(
        _total_current(),
        _fe("CO", (80.0, 90.0, 95.0)),
    )

    with pytest.raises(PartialCurrentDensityError, match="kind='scatter'"):
        plot_partial_current_density(
            data,
            FigureSpec(),
            kind="curve",
            errors=ScatterError(yerr=(1.0, 1.0, 1.0)),
        )


def test_plotting_rejects_wrong_semantics_and_bad_units():
    wrong_semantic = Series(
        x=(-0.5, -0.6),
        y=(-10.0, -20.0),
        x_axis=Axis("potential", unit="V"),
        y_axis=Axis("current_density", unit="mA cm^-2"),
    )
    with pytest.raises(PartialCurrentDensityError, match="partial_current_density"):
        plot_partial_current_density(wrong_semantic)

    missing_unit = Series(
        x=(-0.5, -0.6),
        y=(-10.0, -20.0),
        x_axis=Axis("potential", unit="V"),
        y_axis=Axis("partial_current_density"),
    )
    with pytest.raises(PartialCurrentDensityError, match="unit is required"):
        plot_partial_current_density(missing_unit)

    unsupported = Series(
        x=(-0.5, -0.6),
        y=(-10.0, -20.0),
        x_axis=Axis("potential", unit="V"),
        y_axis=Axis("partial_current_density", unit="A/m^2"),
    )
    with pytest.raises(PartialCurrentDensityError, match="unsupported current density unit"):
        plot_partial_current_density(unsupported)
