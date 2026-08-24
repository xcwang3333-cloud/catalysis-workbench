"""Publication-adapter tests for already calculated TOF/TOFapp data."""

from __future__ import annotations

import pytest

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.experimental.echem import (
    TurnoverFrequencyError,
    plot_turnover_frequency,
    turnover_frequency_from_rate_series,
)
from catalysis_workbench.visualization import ScatterError, VisualizationError


def _rate(key: str, value: float = 1.0) -> Series:
    return Series(
        x=(-0.7,),
        y=(value,),
        key=key,
        label=key,
        x_axis=Axis("potential", unit="V", metadata={"reference": "RHE"}),
        y_axis=Axis("molar_rate", unit="umol/s"),
    )


def _tof(key: str, basis: str) -> Series:
    return turnover_frequency_from_rate_series(
        _rate(key),
        inventory_basis=basis,  # type: ignore[arg-type]
        inventory_value=1.0,
        inventory_unit="umol",
    )


def test_tof_scatter_and_curve_delegate_to_shared_renderers():
    data = Dataset([_tof("a", "active_sites"), _tof("b", "active_sites")])
    fig_scatter, ax_scatter = plot_turnover_frequency(data)
    fig_curve, ax_curve = plot_turnover_frequency(data, kind="curve")
    assert fig_scatter is ax_scatter.figure
    assert fig_curve is ax_curve.figure
    assert len(ax_scatter.collections) >= 2
    assert len(ax_curve.lines) == 2


def test_intrinsic_tof_and_tofapp_cannot_silently_overlay():
    intrinsic = _tof("intrinsic", "active_sites")
    apparent = _tof("apparent", "total_metal")
    assert intrinsic.y_axis.unit == apparent.y_axis.unit == "s^-1"
    with pytest.raises(VisualizationError):
        plot_turnover_frequency(Dataset([intrinsic, apparent]), kind="curve")


def test_different_apparent_inventory_bases_cannot_silently_overlay():
    total = _tof("total", "total_metal")
    bulk = _tof("bulk", "bulk_inventory")
    with pytest.raises(VisualizationError, match="normalization"):
        plot_turnover_frequency(Dataset([total, bulk]), kind="curve")


def test_curve_rejects_scatter_errors_and_malformed_semantics():
    data = _tof("a", "active_sites")
    with pytest.raises(TurnoverFrequencyError, match="kind='scatter'"):
        plot_turnover_frequency(
            data,
            kind="curve",
            errors=ScatterError(yerr=(0.1,)),
        )
    malformed = Series(
        x=data.x,
        y=data.y,
        key="bad",
        x_axis=data.x_axis,
        y_axis=Axis(
            "turnover_frequency",
            unit="s^-1",
            metadata={"normalization": "total_metal"},
        ),
    )
    with pytest.raises(TurnoverFrequencyError, match="inconsistent"):
        plot_turnover_frequency(malformed)


def test_plotter_rejects_unhashable_or_missing_inventory_basis_metadata():
    malformed = Series(
        x=(-0.7,),
        y=(1.0,),
        key="bad",
        x_axis=Axis("potential", unit="V"),
        y_axis=Axis(
            "turnover_frequency",
            unit="s^-1",
            metadata={"normalization": {"basis": "active_sites"}},
        ),
    )
    with pytest.raises(TurnoverFrequencyError, match="normalization metadata"):
        plot_turnover_frequency(malformed)
