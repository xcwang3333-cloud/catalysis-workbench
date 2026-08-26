from __future__ import annotations

import matplotlib.image as mpimg
import numpy as np
import pytest

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.operando import (
    FrameCoordinate,
    OperandoVisualizationError,
    build_operando_stack,
    frame_cut,
    plot_operando_frame_cut,
    plot_operando_heatmap,
    plot_operando_trace,
    plot_operando_waterfall,
    signal_position_cut,
)
from catalysis_workbench.visualization import (
    FigureSpec,
    LayoutSpec,
    export_figure,
    symmetric_color_limits,
)


def _stack(*, decreasing_signal: bool = False, time_values=(0.0, 10.0, 20.0)):
    signal = (
        [1300.0, 1200.0, 1100.0, 1000.0]
        if decreasing_signal
        else [1000.0, 1100.0, 1200.0, 1300.0]
    )
    signal_axis = Axis("wavenumber", unit="cm^-1", label="Wavenumber")
    value_axis = Axis(
        "intensity",
        unit="a.u.",
        label="Intensity",
        metadata={"processing_basis": "raw"},
    )
    rows = (
        [1.0, 2.0, 3.0, 4.0],
        [2.0, 4.0, 6.0, 8.0],
        [3.0, 6.0, 9.0, 12.0],
    )
    frames = tuple(
        Series(
            signal,
            row,
            key=f"frame-{index}",
            x_axis=signal_axis,
            y_axis=value_axis,
        )
        for index, row in enumerate(rows)
    )
    return build_operando_stack(
        frames,
        frame_coordinates=[
            FrameCoordinate("time", Axis("time", unit="s", label="Time"), time_values),
            FrameCoordinate(
                "potential",
                Axis(
                    "potential",
                    unit="V",
                    label="Potential",
                    metadata={"reference": "RHE"},
                ),
                [-0.5, -0.7, -0.5],
            ),
        ],
        primary_coordinate_key="time",
    )


def _snapshot(stack):
    return (
        stack.digest,
        np.array(stack.signal, copy=True),
        np.array(stack.values, copy=True),
        tuple(np.array(item.values, copy=True) for item in stack.frame_coordinates),
    )


def _assert_unchanged(stack, snapshot):
    assert stack.digest == snapshot[0]
    np.testing.assert_array_equal(stack.signal, snapshot[1])
    np.testing.assert_array_equal(stack.values, snapshot[2])
    for coordinate, before in zip(stack.frame_coordinates, snapshot[3], strict=True):
        np.testing.assert_array_equal(coordinate.values, before)


def test_waterfall_preserves_order_and_applies_only_display_offsets():
    stack = _stack()
    before = _snapshot(stack)

    figure, ax = plot_operando_waterfall(stack, offset_step=5.0)

    assert figure.canvas is not None
    assert [line.get_label() for line in ax.lines] == list(stack.frame_keys)
    for index, line in enumerate(ax.lines):
        np.testing.assert_array_equal(line.get_xdata(), stack.signal)
        np.testing.assert_array_equal(
            line.get_ydata(),
            stack.values[index] + index * 5.0,
        )
    _assert_unchanged(stack, before)


def test_waterfall_accepts_finite_signed_offset_and_rejects_omission_or_nonfinite():
    stack = _stack(decreasing_signal=True)
    _, ax = plot_operando_waterfall(
        stack,
        FigureSpec().with_series_style("frame-0", line_width=2.0),
        offset_step=-2.0,
        reverse_signal=True,
    )
    assert ax.xaxis_inverted()
    assert ax.lines[0].get_linewidth() == pytest.approx(2.0)

    with pytest.raises(OperandoVisualizationError, match="trace omission"):
        plot_operando_waterfall(
            stack,
            FigureSpec().with_series_style("frame-1", visible=False),
            offset_step=1.0,
        )
    with pytest.raises(OperandoVisualizationError, match="retained frame keys"):
        plot_operando_waterfall(
            stack,
            FigureSpec().with_series_style("missing", line_width=2.0),
            offset_step=1.0,
        )
    with pytest.raises(OperandoVisualizationError, match="finite"):
        plot_operando_waterfall(stack, offset_step=np.inf)


def test_ordinal_heatmap_supports_repeated_nonmonotonic_coordinate_exactly():
    stack = _stack()
    before = _snapshot(stack)

    figure, ax = plot_operando_heatmap(
        stack,
        coordinate_key="potential",
        frame_geometry="ordinal",
        value_limits=(0.0, 12.0),
        colormap="viridis",
        rasterized=True,
        show_colorbar=False,
    )

    assert figure.canvas is not None
    mesh = ax.collections[0]
    np.testing.assert_array_equal(
        np.asarray(mesh.get_array()).reshape(stack.values.shape),
        stack.values,
    )
    coordinates = mesh.get_coordinates()
    np.testing.assert_allclose(coordinates[:, 0, 1], [-0.5, 0.5, 1.5, 2.5])
    assert [item.get_text() for item in ax.get_yticklabels()] == ["-0.5", "-0.7", "-0.5"]
    assert "ordinal frame geometry" in ax.get_ylabel()
    assert mesh.get_rasterized()
    _assert_unchanged(stack, before)


def test_coordinate_heatmap_uses_presentation_edges_without_resampling():
    stack = _stack(decreasing_signal=True)
    before = _snapshot(stack)

    _, ax = plot_operando_heatmap(
        stack,
        coordinate_key="time",
        frame_geometry="coordinate",
        value_limits=(0.0, 15.0),
        colormap="plasma",
        show_colorbar=False,
    )

    mesh = ax.collections[0]
    coordinates = mesh.get_coordinates()
    np.testing.assert_allclose(
        coordinates[0, :, 0],
        [1350.0, 1250.0, 1150.0, 1050.0, 950.0],
    )
    np.testing.assert_allclose(coordinates[:, 0, 1], [-5.0, 5.0, 15.0, 25.0])
    np.testing.assert_array_equal(
        np.asarray(mesh.get_array()).reshape(stack.values.shape),
        stack.values,
    )
    assert mesh.get_clim() == pytest.approx((0.0, 15.0))
    _assert_unchanged(stack, before)


def test_coordinate_heatmap_supports_strictly_decreasing_retained_coordinate():
    stack = _stack(time_values=(20.0, 10.0, 0.0))

    _, ax = plot_operando_heatmap(
        stack,
        coordinate_key="time",
        frame_geometry="coordinate",
        value_limits=(0.0, 12.0),
        colormap="magma",
        show_colorbar=False,
    )

    coordinates = ax.collections[0].get_coordinates()
    np.testing.assert_allclose(coordinates[:, 0, 1], [25.0, 15.0, 5.0, -5.0])


def test_coordinate_heatmap_fails_closed_for_repeated_or_nonmonotonic_coordinate():
    stack = _stack()

    with pytest.raises(OperandoVisualizationError, match="strictly monotonic"):
        plot_operando_heatmap(
            stack,
            coordinate_key="potential",
            frame_geometry="coordinate",
            value_limits=(0.0, 12.0),
            colormap="viridis",
        )
    with pytest.raises(OperandoVisualizationError, match="ordinal.*coordinate"):
        plot_operando_heatmap(
            stack,
            coordinate_key="time",
            frame_geometry="sorted",
            value_limits=(0.0, 12.0),
            colormap="viridis",
        )


def test_heatmap_requires_explicit_valid_limits_colormap_and_linear_scales():
    stack = _stack()

    with pytest.raises(OperandoVisualizationError, match="exactly two"):
        plot_operando_heatmap(
            stack,
            coordinate_key="time",
            frame_geometry="ordinal",
            value_limits=(0.0,),
            colormap="viridis",
        )
    with pytest.raises(OperandoVisualizationError, match="less than"):
        plot_operando_heatmap(
            stack,
            coordinate_key="time",
            frame_geometry="ordinal",
            value_limits=(2.0, 2.0),
            colormap="viridis",
        )
    with pytest.raises(OperandoVisualizationError, match="colormap"):
        plot_operando_heatmap(
            stack,
            coordinate_key="time",
            frame_geometry="ordinal",
            value_limits=(0.0, 12.0),
            colormap=" ",
        )
    with pytest.raises(OperandoVisualizationError, match="linear"):
        plot_operando_heatmap(
            stack,
            FigureSpec(xscale="log"),
            coordinate_key="time",
            frame_geometry="ordinal",
            value_limits=(0.0, 12.0),
            colormap="viridis",
        )


def test_heatmap_accepts_explicit_symmetric_limits_and_display_reversal_only():
    stack = _stack()
    before = _snapshot(stack)
    limits = symmetric_color_limits(stack.values)

    _, ax = plot_operando_heatmap(
        stack,
        coordinate_key="potential",
        frame_geometry="ordinal",
        value_limits=limits,
        colormap="coolwarm",
        reverse_signal=True,
        reverse_condition=True,
        show_colorbar=False,
    )

    assert ax.xaxis_inverted()
    assert ax.yaxis_inverted()
    assert ax.collections[0].get_clim() == pytest.approx(limits)
    _assert_unchanged(stack, before)


def test_frame_cut_plot_requires_exact_operando_cut_and_preserves_values():
    stack = _stack(decreasing_signal=True)
    cut = frame_cut(stack, frame_key="frame-1")
    before_x = np.array(cut.x, copy=True)
    before_y = np.array(cut.y, copy=True)

    _, ax = plot_operando_frame_cut(cut, reverse_signal=True)

    assert ax.xaxis_inverted()
    np.testing.assert_array_equal(ax.lines[0].get_xdata(), cut.x)
    np.testing.assert_array_equal(ax.lines[0].get_ydata(), cut.y)
    np.testing.assert_array_equal(cut.x, before_x)
    np.testing.assert_array_equal(cut.y, before_y)

    plain = Series([0.0, 1.0], [1.0, 2.0], key="plain")
    with pytest.raises(OperandoVisualizationError, match="frame_cut"):
        plot_operando_frame_cut(plain)


def test_trace_plot_preserves_repeated_nonmonotonic_coordinate_and_digest():
    stack = _stack()
    trace = signal_position_cut(
        stack,
        position=1200.0,
        coordinate_key="potential",
    )
    before_digest = trace.digest
    before_coordinate = np.array(trace.coordinate.values, copy=True)
    before_values = np.array(trace.values, copy=True)

    _, ax = plot_operando_trace(trace, reverse_condition=True)

    np.testing.assert_array_equal(ax.lines[0].get_xdata(), [-0.5, -0.7, -0.5])
    np.testing.assert_array_equal(ax.lines[0].get_ydata(), trace.values)
    assert ax.xaxis_inverted()
    assert trace.digest == before_digest
    np.testing.assert_array_equal(trace.coordinate.values, before_coordinate)
    np.testing.assert_array_equal(trace.values, before_values)


def test_operando_heatmap_exact_size_png_export(tmp_path):
    stack = _stack()
    spec = FigureSpec(
        layout=LayoutSpec(figure_width_in=4.0, figure_height_in=3.0),
    ).with_export(dpi=100)
    figure, _ = plot_operando_heatmap(
        stack,
        spec,
        coordinate_key="time",
        frame_geometry="ordinal",
        value_limits=(0.0, 12.0),
        colormap="viridis",
        show_colorbar=False,
    )
    output = tmp_path / "operando-heatmap.png"

    export_figure(figure, output, spec=spec)
    image = mpimg.imread(output)

    assert image.shape[0] == 300
    assert image.shape[1] == 400
