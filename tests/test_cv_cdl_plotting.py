"""Publication-adapter regressions for CV overlays and calculated Cdl fits."""

from __future__ import annotations

import pytest

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.experimental.echem import (
    CdlError,
    CVSweepPair,
    fit_cdl,
    plot_cdl_fit,
    plot_cv,
)
from catalysis_workbench.visualization import VisualizationError


def _axis(reference: str = "RHE", unit: str = "V") -> Axis:
    return Axis("potential", unit=unit, metadata={"reference": reference})


def _sweep(key: str, *, density: bool = False, reference: str = "RHE") -> Series:
    if density:
        y_axis = Axis(
            "current_density",
            unit="mA/cm^2",
            metadata={"normalization": "geometric_area"},
        )
    else:
        y_axis = Axis("current", unit="mA")
    return Series(
        x=(0.4, 0.5, 0.6),
        y=(1.0, 2.0, 3.0),
        key=key,
        label=key,
        x_axis=_axis(reference),
        y_axis=y_axis,
    )


def _pair(rate: float) -> CVSweepPair:
    delta_a = 0.02 * (rate * 1e-3) + 1e-4
    delta_ma = delta_a * 1e3
    anodic = Series(
        x=(0.4, 0.5, 0.6),
        y=(delta_ma,) * 3,
        key=f"{rate}-a",
        x_axis=_axis(),
        y_axis=Axis("current", unit="mA"),
    )
    cathodic = Series(
        x=(0.6, 0.5, 0.4),
        y=(-delta_ma,) * 3,
        key=f"{rate}-c",
        x_axis=_axis(),
        y_axis=Axis("current", unit="mA"),
    )
    return CVSweepPair(f"{rate}", anodic, cathodic, rate, "mV/s")


def test_plot_cv_reuses_shared_curve_renderer_and_shows_reference():
    data = Dataset([_sweep("a"), _sweep("b")])
    fig, ax = plot_cv(data)
    assert fig is ax.figure
    assert len(ax.lines) == 2
    assert "RHE" in ax.get_xlabel()


def test_plot_cv_inherits_reference_compatibility_guard():
    data = Dataset([_sweep("a", reference="RHE"), _sweep("b", reference="SHE")])
    with pytest.raises(VisualizationError, match="reference"):
        plot_cv(data)


def test_plot_cv_rejects_non_geometric_density_semantics():
    source = _sweep("a", density=True)
    bad = Series(
        x=source.x,
        y=source.y,
        key=source.key,
        x_axis=source.x_axis,
        y_axis=Axis(
            "current_density",
            unit="mA/cm^2",
            metadata={"normalization": "ecsa"},
        ),
    )
    with pytest.raises(CdlError, match="geometric-area normalization"):
        plot_cv(bad)


def test_plot_cv_rejects_unsupported_potential_and_current_units():
    bad_potential = Series(
        x=(0.4, 0.5, 0.6),
        y=(1.0, 2.0, 3.0),
        key="bad-potential",
        x_axis=_axis(unit="eV"),
        y_axis=Axis("current", unit="mA"),
    )
    with pytest.raises(CdlError, match="potential units"):
        plot_cv(bad_potential)

    bad_current = Series(
        x=(0.4, 0.5, 0.6),
        y=(1.0, 2.0, 3.0),
        key="bad-current",
        x_axis=_axis(),
        y_axis=Axis("current", unit="mA/cm^2"),
    )
    with pytest.raises(CdlError, match="supported current unit"):
        plot_cv(bad_current)


def test_plot_cdl_fit_renders_measured_and_fitted_series():
    result = fit_cdl(
        tuple(_pair(rate) for rate in (10.0, 20.0, 50.0, 100.0)),
        potential_value=0.5,
    )
    fig, ax = plot_cdl_fit(result)
    assert fig is ax.figure
    assert len(ax.lines) == 2
    assert ax.get_xlabel()
    assert ax.get_ylabel()


def test_plot_cdl_fit_requires_calculated_result():
    with pytest.raises(TypeError, match="CdlFitResult"):
        plot_cdl_fit(object())  # type: ignore[arg-type]
