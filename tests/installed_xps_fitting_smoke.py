"""Smoke constrained XPS fitting from an installed wheel."""

from __future__ import annotations

import numpy as np

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.characterization import (
    XPSDoubletSpec,
    fit_xps_peaks,
    shirley_xps_background,
)
from catalysis_workbench.processing import FitParameterSpec, PeakComponentSpec


def gaussian(x: np.ndarray, *, amplitude: float, center: float, sigma: float) -> np.ndarray:
    return amplitude / (sigma * np.sqrt(2.0 * np.pi)) * np.exp(
        -((x - center) ** 2) / (2.0 * sigma**2)
    )


x = np.linspace(280.0, 292.0, 601)
primary_y = gaussian(x, amplitude=12.0, center=284.0, sigma=0.6)
secondary_y = gaussian(x, amplitude=6.0, center=287.2, sigma=0.6)
y = 2.0 + primary_y + secondary_y
y[0] = 2.0
y[-1] = 2.0
source = Series(
    x=x[::-1],
    y=y[::-1],
    key="installed-xps-doublet",
    label="Installed constrained XPS smoke",
    x_axis=Axis("binding_energy", unit="eV", label="Binding energy"),
    y_axis=Axis("intensity", unit="counts", label="Intensity"),
)
background = shirley_xps_background(source)

primary = PeakComponentSpec(
    key="main",
    model="gaussian",
    parameters={
        "amplitude": FitParameterSpec(10.0, lower=0.0),
        "center": FitParameterSpec(283.8),
        "sigma": FitParameterSpec(0.7, lower=0.05),
    },
)
doublet = XPSDoubletSpec(
    primary=primary,
    secondary_key="partner",
    separation_ev=3.2,
    amplitude_ratio=0.5,
    parameter_ratios={"sigma": 1.0},
)
result = fit_xps_peaks(
    source,
    x_min_ev=280.0,
    x_max_ev=292.0,
    doublets=(doublet,),
    background=background,
)

assert result.fit.success
assert result.source_direction == "descending"
assert result.background_method == "shirley"
assert result.component_keys == ("main", "partner")
params = result.fit.parameters
assert abs(params["main.center"].value - 284.0) < 1e-5
assert abs(params["partner.center"].value - (params["main.center"].value + 3.2)) < 1e-10
assert abs(params["partner.amplitude"].value - params["main.amplitude"].value * 0.5) < 1e-10
assert abs(params["partner.sigma"].value - params["main.sigma"].value) < 1e-10
