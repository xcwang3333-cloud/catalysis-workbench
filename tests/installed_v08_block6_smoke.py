from __future__ import annotations

import matplotlib
import numpy as np

matplotlib.use("Agg")

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.operando import (
    FrameCoordinate,
    build_xrd_operando_stack,
    plot_operando_heatmap,
    plot_operando_trace,
    xrd_fit_component_center_trace,
    xrd_fit_component_fwhm_trace,
    xrd_observed_peak_position_trace,
    xrd_window_integral_trace,
)
from catalysis_workbench.processing import (
    FitParameterSpec,
    PeakComponentSpec,
    PeakFitSpec,
    fit_peaks,
)


def gaussian(x: np.ndarray, amplitude: float, center: float, sigma: float) -> np.ndarray:
    return amplitude / (sigma * np.sqrt(2.0 * np.pi)) * np.exp(
        -((x - center) ** 2) / (2.0 * sigma**2)
    )


def pattern(key: str, x: np.ndarray, y: np.ndarray) -> Series:
    return Series(
        x,
        y,
        key=key,
        x_axis=Axis("two_theta", unit="deg"),
        y_axis=Axis("intensity", unit="counts"),
    )


x = np.linspace(20.0, 30.0, 201)
first = pattern("xrd-0", x, gaussian(x, 12.0, 24.0, 0.5))
second = pattern("xrd-1", x, gaussian(x, 16.0, 26.0, 0.7))
coordinate = FrameCoordinate(
    "potential",
    Axis("potential", unit="V", metadata={"reference": "RHE"}),
    [-0.4, -0.6],
)
stack = build_xrd_operando_stack(
    [first, second],
    frame_coordinates=[coordinate],
    primary_coordinate_key="potential",
)
assert stack.frame_keys == ("xrd-0", "xrd-1")
assert stack.reconstructed_source_digests() == stack.source_digests
assert not stack.values.flags.writeable

integral = xrd_window_integral_trace(
    stack,
    two_theta_min_deg=23.0,
    two_theta_max_deg=27.0,
    coordinate_key="potential",
)
observed = xrd_observed_peak_position_trace(
    stack,
    two_theta_min_deg=23.0,
    two_theta_max_deg=27.0,
    coordinate_key="potential",
)
np.testing.assert_allclose(observed.values, [24.0, 26.0])
assert integral.n_frames == 2

component = PeakComponentSpec(
    key="peak",
    model="gaussian",
    parameters={
        "amplitude": FitParameterSpec(10.0, lower=0.0),
        "center": FitParameterSpec(25.0, lower=22.0, upper=28.0),
        "sigma": FitParameterSpec(0.8, lower=0.1, upper=2.0),
    },
)
spec = PeakFitSpec(22.0, 28.0, (component,))
fits = [fit_peaks(first, spec), fit_peaks(second, spec)]
center = xrd_fit_component_center_trace(
    stack,
    fits,
    coordinate_key="potential",
    component_key="peak",
)
width = xrd_fit_component_fwhm_trace(
    stack,
    fits,
    coordinate_key="potential",
    component_key="peak",
)
np.testing.assert_allclose(center.values, [24.0, 26.0], atol=1e-6)
assert np.all(width.values > 0.0)

figure, axes = plot_operando_heatmap(
    stack,
    coordinate_key="potential",
    frame_geometry="ordinal",
    value_limits=(0.0, float(np.max(stack.values))),
    colormap="viridis",
)
figure.canvas.draw()
figure.clf()

trace_figure, trace_axes = plot_operando_trace(center)
trace_figure.canvas.draw()
trace_figure.clf()
assert axes is not None
assert trace_axes is not None
