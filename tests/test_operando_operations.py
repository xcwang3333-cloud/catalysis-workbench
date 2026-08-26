from __future__ import annotations

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.operando import (
    FrameCoordinate,
    OperandoOperationError,
    OperandoStack,
    OperandoTrace,
    PearsonCorrelationResult,
    TracePair,
    build_operando_stack,
    build_operando_trace,
    crop_signal,
    frame_cut,
    pair_traces,
    pearson_correlation,
    select_frames,
    select_frames_by_coordinate,
    signal_position_cut,
)


def _stack(*, decreasing: bool = False) -> OperandoStack:
    signal = (
        [1300.0, 1200.0, 1100.0, 1000.0]
        if decreasing
        else [1000.0, 1100.0, 1200.0, 1300.0]
    )
    signal_axis = Axis(
        "wavenumber",
        unit="cm^-1",
        label="Wavenumber",
        metadata={"calibration": "source-native"},
    )
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
        [4.0, 8.0, 12.0, 16.0],
    )
    if decreasing:
        rows = tuple(list(reversed(row)) for row in rows)
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
    coordinates = (
        FrameCoordinate("time", Axis("time", unit="s"), [0.0, 10.0, 20.0, 30.0]),
        FrameCoordinate(
            "potential",
            Axis("potential", unit="V", metadata={"reference": "RHE"}),
            [-0.5, -0.7, -0.5, -0.9],
            metadata={"program": "cyclic"},
        ),
    )
    return build_operando_stack(
        frames,
        frame_coordinates=coordinates,
        primary_coordinate_key="time",
        metadata={"modality": "test"},
    )


def test_select_frames_by_keys_and_indices_preserves_caller_order():
    stack = _stack()

    by_key = select_frames(stack, frame_keys=["frame-2", "frame-0"])
    assert by_key.frame_keys == ("frame-2", "frame-0")
    np.testing.assert_array_equal(by_key.values[:, 0], [3.0, 1.0])
    np.testing.assert_array_equal(by_key.primary_coordinate.values, [20.0, 0.0])
    np.testing.assert_array_equal(by_key.frame_coordinates[1].values, [-0.5, -0.5])

    by_index = select_frames(stack, indices=[3, 1])
    assert by_index.frame_keys == ("frame-3", "frame-1")
    np.testing.assert_array_equal(by_index.primary_coordinate.values, [30.0, 10.0])
    assert by_index.source_keys == ("frame-3", "frame-1")
    assert by_index.source_digests == (stack.source_digests[3], stack.source_digests[1])


def test_select_frames_rejects_ambiguous_duplicate_unknown_and_out_of_range_inputs():
    stack = _stack()
    with pytest.raises(OperandoOperationError, match="exactly one"):
        select_frames(stack)
    with pytest.raises(OperandoOperationError, match="exactly one"):
        select_frames(stack, frame_keys=["frame-0"], indices=[0])
    with pytest.raises(OperandoOperationError, match="duplicates"):
        select_frames(stack, frame_keys=["frame-0", "frame-0"])
    with pytest.raises(OperandoOperationError, match="unknown frame key"):
        select_frames(stack, frame_keys=["missing"])
    with pytest.raises(OperandoOperationError, match="duplicates"):
        select_frames(stack, indices=[1, 1])
    with pytest.raises(OperandoOperationError, match="out of range"):
        select_frames(stack, indices=[4])
    with pytest.raises(TypeError, match="integers"):
        select_frames(stack, indices=[True])


def test_coordinate_selection_is_explicit_exact_and_preserves_retained_order():
    stack = _stack()

    repeated = select_frames_by_coordinate(
        stack,
        coordinate_key="potential",
        comparison="==",
        value=-0.5,
    )
    assert repeated.frame_keys == ("frame-0", "frame-2")
    np.testing.assert_array_equal(repeated.frame_coordinates[1].values, [-0.5, -0.5])

    thresholded = select_frames_by_coordinate(
        stack,
        coordinate_key="potential",
        comparison="<=",
        value=-0.7,
    )
    assert thresholded.frame_keys == ("frame-1", "frame-3")
    np.testing.assert_array_equal(thresholded.frame_coordinates[1].values, [-0.7, -0.9])

    with pytest.raises(OperandoOperationError, match="unknown frame coordinate"):
        select_frames_by_coordinate(
            stack,
            coordinate_key="temperature",
            comparison="==",
            value=25.0,
        )
    with pytest.raises(OperandoOperationError, match="comparison must"):
        select_frames_by_coordinate(
            stack,
            coordinate_key="potential",
            comparison="approx",
            value=-0.5,
        )
    with pytest.raises(OperandoOperationError, match="selected no"):
        select_frames_by_coordinate(
            stack,
            coordinate_key="potential",
            comparison="==",
            value=-0.5000000001,
        )


def test_signal_crop_retains_only_measured_points_and_source_direction():
    increasing = crop_signal(_stack(), lower=1050.0, upper=1250.0)
    np.testing.assert_array_equal(increasing.signal, [1100.0, 1200.0])
    np.testing.assert_array_equal(
        increasing.values,
        [[2.0, 3.0], [4.0, 6.0], [6.0, 9.0], [8.0, 12.0]],
    )
    assert increasing.signal_direction == "increasing"

    decreasing = crop_signal(_stack(decreasing=True), lower=1050.0, upper=1250.0)
    np.testing.assert_array_equal(decreasing.signal, [1200.0, 1100.0])
    np.testing.assert_array_equal(
        decreasing.values,
        [[3.0, 2.0], [6.0, 4.0], [9.0, 6.0], [12.0, 8.0]],
    )
    assert decreasing.signal_direction == "decreasing"

    with pytest.raises(OperandoOperationError, match="lower"):
        crop_signal(_stack(), lower=1200.0, upper=1100.0)
    with pytest.raises(OperandoOperationError, match="no measured points"):
        crop_signal(_stack(), lower=1400.0, upper=1500.0)
    with pytest.raises(OperandoOperationError, match="at least two"):
        crop_signal(_stack(), lower=1100.0, upper=1100.0)


def test_frame_cut_returns_exact_released_series_without_mutating_stack():
    stack = _stack()
    digest = stack.digest
    cut = frame_cut(stack, frame_key="frame-2")

    assert isinstance(cut, Series)
    assert cut.key == "frame-2"
    np.testing.assert_array_equal(cut.x, stack.signal)
    np.testing.assert_array_equal(cut.y, stack.values[2])
    assert cut.x_axis == stack.signal_axis
    assert cut.y_axis == stack.value_axis
    assert cut.metadata["catalysis_workbench.operando_cut"]["source_stack_digest"] == digest
    assert stack.digest == digest

    by_index = frame_cut(stack, index=1)
    assert by_index.key == "frame-1"
    with pytest.raises(OperandoOperationError, match="exactly one"):
        frame_cut(stack)
    with pytest.raises(OperandoOperationError, match="unknown frame key"):
        frame_cut(stack, frame_key="missing")


def test_signal_position_cut_requires_exact_retained_point_and_explicit_coordinate():
    stack = _stack()
    trace = signal_position_cut(stack, position=1200.0, coordinate_key="potential")

    assert isinstance(trace, OperandoTrace)
    assert trace.frame_keys == stack.frame_keys
    assert trace.coordinate.key == "potential"
    np.testing.assert_array_equal(trace.coordinate.values, [-0.5, -0.7, -0.5, -0.9])
    np.testing.assert_array_equal(trace.values, [3.0, 6.0, 9.0, 12.0])
    assert trace.method == "signal_position_cut"
    assert trace.parameters["signal_position"] == 1200.0
    assert trace.source_stack_digest == stack.digest
    assert trace.source_frame_digests == stack.source_digests
    assert trace.reconstructed_result_digests() == trace.source_result_digests

    with pytest.raises(OperandoOperationError, match="exactly one retained"):
        signal_position_cut(stack, position=1200.0000001, coordinate_key="time")
    with pytest.raises(OperandoOperationError, match="unknown frame coordinate"):
        signal_position_cut(stack, position=1200.0, coordinate_key="temperature")


def test_trace_detaches_values_freezes_parameters_and_reconstructs_digests():
    stack = _stack()
    source = np.array([1.0, 3.0, 2.0, 5.0])
    parameters = {"window": [1000.0, 1200.0]}
    trace = build_operando_trace(
        stack,
        coordinate_key="potential",
        values=source,
        value_axis=Axis("band_area", unit="a.u. cm^-1"),
        method="reviewed_band_area",
        parameters=parameters,
        metadata={"band_key": "band-a"},
    )
    digest = trace.digest

    source[:] = -10.0
    parameters["window"].append(1300.0)

    np.testing.assert_array_equal(trace.values, [1.0, 3.0, 2.0, 5.0])
    assert trace.parameters["window"] == (1000.0, 1200.0)
    assert not trace.values.flags.writeable
    with pytest.raises(ValueError):
        trace.values.setflags(write=True)
    assert trace.reconstructed_result_digests() == trace.source_result_digests
    assert trace.digest == digest

    tampered = list(trace.source_result_digests)
    tampered[0] = "0" * 64
    with pytest.raises(OperandoOperationError, match="contradict"):
        OperandoTrace(
            frame_keys=trace.frame_keys,
            coordinate=trace.coordinate,
            value_axis=trace.value_axis,
            values=trace.values,
            method=trace.method,
            parameters=trace.parameters,
            source_stack_digest=trace.source_stack_digest,
            source_frame_digests=trace.source_frame_digests,
            source_result_digests=tampered,
        )


def _trace(
    stack: OperandoStack,
    values: list[float],
    *,
    coordinate_key: str = "time",
    value_axis: Axis | None = None,
) -> OperandoTrace:
    return build_operando_trace(
        stack,
        coordinate_key=coordinate_key,
        values=values,
        value_axis=value_axis or Axis("descriptor", unit="a.u."),
        method="caller_descriptor",
        parameters={"descriptor": "test"},
    )


def test_pairing_requires_exact_ordered_keys_and_coordinate_compatibility():
    stack = _stack()
    left = _trace(stack, [1.0, 2.0, 3.0, 4.0])
    right = _trace(stack, [2.0, 4.0, 6.0, 8.0])
    pair = pair_traces(left, right)

    assert isinstance(pair, TracePair)
    assert pair.frame_keys == stack.frame_keys
    np.testing.assert_array_equal(pair.left_values, left.values)
    np.testing.assert_array_equal(pair.right_values, right.values)
    assert pair.sample_count == 4
    assert not pair.left_values.flags.writeable

    reordered_stack = select_frames(stack, indices=[1, 0, 2, 3])
    reordered = _trace(reordered_stack, [4.0, 2.0, 6.0, 8.0])
    with pytest.raises(OperandoOperationError, match="frame keys must match exactly"):
        pair_traces(left, reordered)

    subset_stack = select_frames(stack, indices=[0, 1, 2])
    subset = _trace(subset_stack, [2.0, 4.0, 6.0])
    with pytest.raises(OperandoOperationError, match="automatic intersection"):
        pair_traces(left, subset)

    potential_trace = _trace(
        stack,
        [2.0, 4.0, 6.0, 8.0],
        coordinate_key="potential",
    )
    with pytest.raises(OperandoOperationError, match="coordinates must match exactly"):
        pair_traces(left, potential_trace)


def test_pairing_ignores_presentation_label_but_rejects_axis_semantic_or_unit_changes():
    stack = _stack()
    left = _trace(stack, [1.0, 2.0, 3.0, 4.0])
    coordinate = FrameCoordinate(
        "time",
        Axis("time", unit="s", label="Elapsed time"),
        [0.0, 10.0, 20.0, 30.0],
        metadata={"different_caller_note": True},
    )
    right = OperandoTrace(
        frame_keys=left.frame_keys,
        coordinate=coordinate,
        value_axis=Axis("other", unit="a.u."),
        values=[2.0, 4.0, 6.0, 8.0],
        method="other",
        parameters={},
        source_stack_digest=stack.digest,
        source_frame_digests=stack.source_digests,
    )
    assert pair_traces(left, right).sample_count == 4

    wrong_unit_coordinate = FrameCoordinate(
        "time",
        Axis("time", unit="min"),
        [0.0, 10.0, 20.0, 30.0],
    )
    wrong_unit = OperandoTrace(
        frame_keys=left.frame_keys,
        coordinate=wrong_unit_coordinate,
        value_axis=Axis("other", unit="a.u."),
        values=[2.0, 4.0, 6.0, 8.0],
        method="other",
        parameters={},
        source_stack_digest=stack.digest,
        source_frame_digests=stack.source_digests,
    )
    with pytest.raises(OperandoOperationError, match="coordinates must match exactly"):
        pair_traces(left, wrong_unit)


def test_pearson_correlation_retains_exact_pair_and_source_digests():
    stack = _stack()
    left = _trace(stack, [1.0, 2.0, 3.0, 4.0])
    right = _trace(stack, [2.0, 4.0, 6.0, 8.0])
    result = pearson_correlation(left, right)

    assert isinstance(result, PearsonCorrelationResult)
    assert result.method == "pearson"
    assert result.sample_count == 4
    assert result.coefficient == pytest.approx(1.0)
    assert result.p_value == pytest.approx(0.0)
    assert result.source_digests == (left.digest, right.digest)
    np.testing.assert_array_equal(result.left_values, left.values)
    np.testing.assert_array_equal(result.right_values, right.values)
    assert len(result.digest) == 64


def test_pearson_fails_for_constant_or_insufficient_traces():
    stack = _stack()
    with pytest.raises(OperandoOperationError, match="constant"):
        pearson_correlation(
            _trace(stack, [1.0, 1.0, 1.0, 1.0]),
            _trace(stack, [1.0, 2.0, 3.0, 4.0]),
        )

    one = select_frames(stack, indices=[0])
    with pytest.raises(OperandoOperationError, match="at least two"):
        pearson_correlation(_trace(one, [1.0]), _trace(one, [2.0]))


def test_operations_do_not_mutate_source_stack_arrays_or_digest():
    stack = _stack()
    signal = stack.signal.copy()
    values = stack.values.copy()
    digest = stack.digest

    select_frames(stack, indices=[3, 0])
    select_frames_by_coordinate(
        stack,
        coordinate_key="potential",
        comparison="<=",
        value=-0.7,
    )
    crop_signal(stack, lower=1050.0, upper=1250.0)
    frame_cut(stack, index=0)
    signal_position_cut(stack, position=1100.0, coordinate_key="time")

    np.testing.assert_array_equal(stack.signal, signal)
    np.testing.assert_array_equal(stack.values, values)
    assert stack.digest == digest
