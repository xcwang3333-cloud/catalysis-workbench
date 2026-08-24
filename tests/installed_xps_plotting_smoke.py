"""Smoke XPS publication plotting and diagnostics from an installed wheel."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.characterization import (
    XPSDoubletSpec,
    fit_xps_peaks,
    linear_xps_background,
    plot_xps_fit,
    summarize_xps_fit,
)
from catalysis_workbench.processing import FitParameterSpec, PeakComponentSpec
from catalysis_workbench.visualization import FigureSpec, export_figure


def _gaussian(x: np.ndarray, amplitude: float, center: float, sigma: float) -> np.ndarray:
    return amplitude / (sigma * np.sqrt(2.0 * np.pi)) * np.exp(
        -((x - center) ** 2) / (2.0 * sigma**2)
    )


x = np.linspace(280.0, 290.0, 241)
y = 1.5 + _gaussian(x, 7.0, 284.5, 0.65) + _gaussian(x, 3.5, 287.3, 0.65)
y[0] = y[-1] = 1.5
source = Series(
    x=x,
    y=y,
    key="installed-xps-plot",
    label="Installed XPS plot",
    x_axis=Axis("binding_energy", unit="eV"),
    y_axis=Axis("intensity", unit="counts"),
)
primary = PeakComponentSpec(
    key="main",
    model="gaussian",
    label="Main",
    parameters={
        "amplitude": FitParameterSpec(6.5, lower=0.0),
        "center": FitParameterSpec(284.4, lower=283.0, upper=286.0),
        "sigma": FitParameterSpec(0.7, lower=0.2, upper=1.5),
    },
)
doublet = XPSDoubletSpec(
    primary=primary,
    secondary_key="partner",
    separation_ev=2.8,
    amplitude_ratio=0.5,
    parameter_ratios={"sigma": 1.0},
    secondary_label="Partner",
)
background = linear_xps_background(source)
result = fit_xps_peaks(
    source,
    x_min_ev=280.0,
    x_max_ev=290.0,
    doublets=(doublet,),
    background=background,
)
figure, axes = plot_xps_fit(
    result,
    FigureSpec().with_layout(figure_width_in=4.0, figure_height_in=3.0),
    show_residual=True,
)
assert len(axes) == 2
assert axes[0].get_xlim()[0] > axes[0].get_xlim()[1]
assert axes[1].get_xlim() == axes[0].get_xlim()
residual_lines = [line for line in axes[1].get_lines() if line.get_label() == "Residual"]
assert len(residual_lines) == 1
np.testing.assert_array_equal(residual_lines[0].get_ydata(), result.fit.residual)

diagnostics = summarize_xps_fit(result)
assert diagnostics.component_keys == ("main", "partner")
assert diagnostics.background_method == "linear"
assert diagnostics.n_points == result.fit.n_points

with tempfile.TemporaryDirectory() as directory:
    output = Path(directory) / "xps-fit.svg"
    export_figure(figure, output, spec=FigureSpec().with_layout(figure_width_in=4.0, figure_height_in=3.0))
    assert output.exists()
    assert output.stat().st_size > 0
