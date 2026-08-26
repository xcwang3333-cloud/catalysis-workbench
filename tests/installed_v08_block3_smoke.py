"""Installed-wheel smoke for v0.8 Block-3 passive operando visualization."""

from __future__ import annotations

import numpy as np

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.operando import (
    FrameCoordinate,
    build_operando_stack,
    frame_cut,
    plot_operando_frame_cut,
    plot_operando_heatmap,
    plot_operando_trace,
    plot_operando_waterfall,
    signal_position_cut,
)
from catalysis_workbench.visualization import FigureSpec, symmetric_color_limits


def main() -> None:
    signal_axis = Axis("wavenumber", unit="cm^-1", label="Wavenumber")
    value_axis = Axis("intensity", unit="a.u.", metadata={"processing_basis": "raw"})
    frames = tuple(
        Series(
            [1300.0, 1200.0, 1100.0, 1000.0],
            [4.0 * scale, 3.0 * scale, 2.0 * scale, 1.0 * scale],
            key=f"frame-{index}",
            x_axis=signal_axis,
            y_axis=value_axis,
        )
        for index, scale in enumerate((1.0, 2.0, 3.0))
    )
    stack = build_operando_stack(
        frames,
        frame_coordinates=[
            FrameCoordinate("time", Axis("time", unit="s"), [0.0, 10.0, 20.0]),
            FrameCoordinate(
                "potential",
                Axis("potential", unit="V", metadata={"reference": "RHE"}),
                [-0.5, -0.7, -0.5],
            ),
        ],
        primary_coordinate_key="time",
    )
    before_digest = stack.digest
    before_signal = np.array(stack.signal, copy=True)
    before_values = np.array(stack.values, copy=True)

    waterfall, waterfall_ax = plot_operando_waterfall(stack, offset_step=2.0)
    assert waterfall.canvas is not None
    assert len(waterfall_ax.lines) == 3

    limits = symmetric_color_limits(stack.values)
    ordinal, ordinal_ax = plot_operando_heatmap(
        stack,
        coordinate_key="potential",
        frame_geometry="ordinal",
        value_limits=limits,
        colormap="coolwarm",
        show_colorbar=False,
    )
    assert ordinal.canvas is not None
    np.testing.assert_array_equal(
        np.asarray(ordinal_ax.collections[0].get_array()).reshape(stack.values.shape),
        stack.values,
    )

    coordinate, coordinate_ax = plot_operando_heatmap(
        stack,
        coordinate_key="time",
        frame_geometry="coordinate",
        value_limits=(0.0, 12.0),
        colormap="viridis",
        reverse_signal=True,
        show_colorbar=False,
    )
    assert coordinate.canvas is not None
    assert coordinate_ax.xaxis_inverted()

    cut = frame_cut(stack, frame_key="frame-1")
    cut_figure, cut_ax = plot_operando_frame_cut(cut, reverse_signal=True)
    assert cut_figure.canvas is not None
    np.testing.assert_array_equal(cut_ax.lines[0].get_ydata(), cut.y)

    trace = signal_position_cut(stack, position=1200.0, coordinate_key="potential")
    trace_digest = trace.digest
    trace_figure, trace_ax = plot_operando_trace(trace)
    assert trace_figure.canvas is not None
    np.testing.assert_array_equal(trace_ax.lines[0].get_xdata(), trace.coordinate.values)
    np.testing.assert_array_equal(trace_ax.lines[0].get_ydata(), trace.values)
    assert trace.digest == trace_digest

    assert stack.digest == before_digest
    np.testing.assert_array_equal(stack.signal, before_signal)
    np.testing.assert_array_equal(stack.values, before_values)

    print("installed v0.8 Block-3 passive operando visualization smoke: ok")


if __name__ == "__main__":
    main()
