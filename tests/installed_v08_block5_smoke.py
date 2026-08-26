from __future__ import annotations

import matplotlib
import numpy as np

matplotlib.use("Agg")

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.characterization import (
    XANESNormalizationSpec,
    XASWindow,
    normalize_xanes,
)
from catalysis_workbench.experimental.operando import (
    FrameCoordinate,
    build_xanes_operando_stack,
    build_xas_operando_stack,
    plot_operando_heatmap,
    plot_operando_trace,
    xanes_edge_position_trace,
    xanes_white_line_intensity_trace,
    xas_window_integral_trace,
)


def raw_series(key: str, energy: np.ndarray, transition: np.ndarray) -> Series:
    return Series(
        energy,
        0.02 * energy + transition,
        key=key,
        x_axis=Axis("energy", unit="eV"),
        y_axis=Axis("mu", unit="a.u."),
        metadata={"energy_reference": "caller-reference"},
    )


def normalized_result(key: str, transition: np.ndarray):
    energy = np.arange(0.0, 11.0, 1.0)
    return normalize_xanes(
        raw_series(key, energy, transition),
        XANESNormalizationSpec(
            e0_ev=5.0,
            pre_edge=XASWindow(0.0, 3.0),
            post_edge=XASWindow(7.0, 10.0),
            pre_edge_order=1,
            post_edge_order=1,
        ),
    )


def transition(a: float, b: float, c: float) -> np.ndarray:
    values = np.zeros(11, dtype=float)
    values[7:] = 1.0
    values[4] = a
    values[5] = b
    values[6] = c
    return values


coordinate = FrameCoordinate(
    "potential",
    Axis("potential", unit="V", metadata={"reference": "RHE"}),
    [-0.4, -0.6],
)

raw_energy = np.arange(0.0, 11.0, 1.0)
raw_stack = build_xas_operando_stack(
    [
        raw_series("raw-0", raw_energy, transition(0.10, 0.60, 0.90)),
        raw_series("raw-1", raw_energy, transition(0.05, 0.30, 1.20)),
    ],
    frame_coordinates=[coordinate],
    primary_coordinate_key="potential",
)
raw_integral = xas_window_integral_trace(
    raw_stack,
    XASWindow(4.0, 6.0),
    coordinate_key="potential",
)
assert raw_stack.frame_keys == ("raw-0", "raw-1")
assert raw_stack.reconstructed_source_digests() == raw_stack.source_digests
assert raw_integral.n_frames == 2

result0 = normalized_result("xanes-0", transition(0.10, 0.60, 0.90))
result1 = normalized_result("xanes-1", transition(0.05, 0.30, 1.20))
xanes_stack = build_xanes_operando_stack(
    [result0, result1],
    frame_coordinates=[coordinate],
    primary_coordinate_key="potential",
)
white_line = xanes_white_line_intensity_trace(
    xanes_stack,
    XASWindow(4.0, 6.0),
    coordinate_key="potential",
)
edge = xanes_edge_position_trace(
    xanes_stack,
    XASWindow(3.0, 7.0),
    coordinate_key="potential",
)
np.testing.assert_allclose(white_line.values, [0.9, 1.2], atol=1e-12)
np.testing.assert_allclose(edge.values, [4.5, 5.5], atol=1e-12)
assert white_line.reconstructed_result_digests() == white_line.source_result_digests
assert not xanes_stack.values.flags.writeable
assert not white_line.values.flags.writeable

figure, axes, _ = plot_operando_heatmap(
    xanes_stack,
    frame_geometry="ordinal",
    coordinate_key="potential",
    value_limits=(0.0, 1.3),
    cmap="viridis",
)
figure.canvas.draw()
figure.clf()

trace_figure, trace_axes = plot_operando_trace(white_line)
trace_figure.canvas.draw()
trace_figure.clf()
assert axes is not None
assert trace_axes is not None
