"""Smoke the shared constrained peak-fitting API from an installed wheel."""

from __future__ import annotations

import numpy as np

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.processing import (
    FitParameterSpec,
    PeakComponentSpec,
    PeakFitSpec,
    fit_peaks,
)


def _gaussian(x: np.ndarray, *, amplitude: float, center: float, sigma: float) -> np.ndarray:
    return amplitude / (sigma * np.sqrt(2.0 * np.pi)) * np.exp(
        -((x - center) ** 2) / (2.0 * sigma**2)
    )


x = np.linspace(-4.0, 4.0, 321)
y = 1.25 + _gaussian(x, amplitude=10.0, center=0.6, sigma=0.75)
source = Series(
    x=x,
    y=y,
    key="installed-peak-fit",
    label="Installed peak fitting smoke",
    x_axis=Axis("energy", unit="eV"),
    y_axis=Axis("intensity", unit="counts"),
)
component = PeakComponentSpec(
    key="peak_a",
    model="gaussian",
    parameters={
        "amplitude": FitParameterSpec(8.0, lower=0.0),
        "center": FitParameterSpec(0.4, lower=-1.0, upper=1.5),
        "sigma": FitParameterSpec(0.9, lower=0.2, upper=2.0),
    },
)
result = fit_peaks(
    source,
    PeakFitSpec(
        x_min=-3.0,
        x_max=3.0,
        components=(component,),
        background=np.full(source.n_points, 1.25),
    ),
)

assert result.success, result.message
assert result.source_key == "installed-peak-fit"
np.testing.assert_allclose(result.parameters["peak_a.amplitude"].value, 10.0, rtol=1e-5)
np.testing.assert_allclose(result.parameters["peak_a.center"].value, 0.6, atol=1e-6)
np.testing.assert_allclose(result.parameters["peak_a.sigma"].value, 0.75, rtol=1e-5)
np.testing.assert_allclose(result.background, 1.25)
assert np.max(np.abs(result.residual)) < 1e-7
