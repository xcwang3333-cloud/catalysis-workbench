from __future__ import annotations

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.operando import (
    FrameCoordinate,
    OperandoStack,
    OperandoStackError,
    build_operando_stack,
    series_array_digest,
)


def _frames(*, decreasing: bool = False, basis: str = "raw") -> tuple[Series, ...]:
    signal = [1200.0, 1100.0, 1000.0] if decreasing else [1000.0, 1100.0, 1200.0]
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
        metadata={"processing_basis": basis},
    )
    return tuple(
        Series(
            signal,
            [float(index + 1), float(index + 2), float(index + 3)],
            key=f"frame-{index}",
            x_axis=signal_axis,
            y_axis=value_axis,
        )
        for index in range(3)
    )


def _coordinates() -> tuple[FrameCoordinate, ...]:
    return (
        FrameCoordinate(
            "time",
            Axis("time", unit="s", label="Time"),
            [0.0, 10.0, 20.0],
        ),
        FrameCoordinate(
            "potential",
            Axis(
                "potential",
                unit="V",
                label="Potential",
                metadata={"reference": "RHE"},
            ),
            [-0.5, -0.7, -0.5],
            metadata={"program": ["forward", "turn", "return"]},
        ),
    )


def _stack(*, decreasing: bool = False) -> OperandoStack:
    return build_operando_stack(
        _frames(decreasing=decreasing),
        frame_coordinates=_coordinates(),
        primary_coordinate_key="time",
        metadata={"modality": "test-spectrum"},
    )


def test_frame_coordinate_detaches_arrays_and_deep_freezes_metadata():
    source_values = np.array([-0.5, -0.7, -0.5])
    source_metadata = {"program": ["forward", "turn", "return"]}
    coordinate = FrameCoordinate(
        "potential",
        Axis("potential", unit="V", metadata={"reference": "RHE"}),
        source_values,
        metadata=source_metadata,
    )

    source_values[0] = 99.0
    source_metadata["program"].append("mutated")

    np.testing.assert_array_equal(coordinate.values, [-0.5, -0.7, -0.5])
    assert coordinate.metadata["program"] == ("forward", "turn", "return")
    assert not coordinate.values.flags.writeable
    with pytest.raises(ValueError):
        coordinate.values.setflags(write=True)
    with pytest.raises(TypeError):
        coordinate.metadata["new"] = "value"


def test_frame_coordinate_preserves_repeated_nonmonotonic_values():
    coordinate = _coordinates()[1]
    np.testing.assert_array_equal(coordinate.values, [-0.5, -0.7, -0.5])


def test_build_stack_preserves_exact_frame_signal_and_coordinate_order():
    stack = _stack()

    assert stack.frame_keys == ("frame-0", "frame-1", "frame-2")
    assert stack.source_keys == stack.frame_keys
    np.testing.assert_array_equal(stack.signal, [1000.0, 1100.0, 1200.0])
    np.testing.assert_array_equal(
        stack.values,
        [[1.0, 2.0, 3.0], [2.0, 3.0, 4.0], [3.0, 4.0, 5.0]],
    )
    assert tuple(item.key for item in stack.frame_coordinates) == (
        "time",
        "potential",
    )
    assert stack.primary_coordinate.key == "time"
    assert stack.signal_direction == "increasing"
    assert stack.n_frames == 3
    assert stack.n_signal_points == 3


def test_build_stack_accepts_decreasing_signal_grid_without_reordering():
    stack = _stack(decreasing=True)

    np.testing.assert_array_equal(stack.signal, [1200.0, 1100.0, 1000.0])
    assert stack.signal_direction == "decreasing"


def test_stack_arrays_are_immutable_even_via_setflags():
    stack = _stack()

    assert not stack.signal.flags.writeable
    assert not stack.values.flags.writeable
    with pytest.raises(ValueError):
        stack.signal.setflags(write=True)
    with pytest.raises(ValueError):
        stack.values.setflags(write=True)


def test_stack_is_detached_from_caller_owned_series_and_coordinate_arrays():
    signal = np.array([1000.0, 1100.0, 1200.0])
    values = [
        np.array([1.0, 2.0, 3.0]),
        np.array([2.0, 3.0, 4.0]),
    ]
    frames = tuple(
        Series(
            signal,
            row,
            key=f"f-{index}",
            x_axis=Axis("wavenumber", unit="cm^-1"),
            y_axis=Axis("intensity", unit="a.u."),
        )
        for index, row in enumerate(values)
    )
    times = np.array([0.0, 5.0])
    coordinate = FrameCoordinate("time", Axis("time", unit="s"), times)
    stack = build_operando_stack(
        frames,
        frame_coordinates=[coordinate],
        primary_coordinate_key="time",
    )
    digest = stack.digest

    signal[:] = -1
    values[0][:] = -2
    times[:] = -3

    np.testing.assert_array_equal(stack.signal, [1000.0, 1100.0, 1200.0])
    np.testing.assert_array_equal(stack.values[0], [1.0, 2.0, 3.0])
    np.testing.assert_array_equal(stack.primary_coordinate.values, [0.0, 5.0])
    assert stack.digest == digest


def test_source_array_digests_reconstruct_exactly_from_retained_stack():
    frames = _frames()
    stack = build_operando_stack(
        frames,
        frame_coordinates=_coordinates(),
        primary_coordinate_key="time",
    )

    assert stack.source_digests == tuple(series_array_digest(frame) for frame in frames)
    assert stack.reconstructed_source_digests() == stack.source_digests
    assert all(len(item) == 64 for item in stack.source_digests)


def test_expected_source_digest_contradiction_fails_closed():
    frames = _frames()
    expected = [series_array_digest(frame) for frame in frames]
    expected[1] = "0" * 64

    with pytest.raises(OperandoStackError, match="contradict"):
        build_operando_stack(
            frames,
            frame_coordinates=_coordinates(),
            primary_coordinate_key="time",
            expected_source_digests=expected,
        )


def test_direct_stack_rejects_source_digest_contradiction():
    good = _stack()
    bad = list(good.source_digests)
    bad[0] = "0" * 64

    with pytest.raises(OperandoStackError, match="contradict"):
        OperandoStack(
            frame_keys=good.frame_keys,
            signal=good.signal,
            signal_axis=good.signal_axis,
            value_axis=good.value_axis,
            values=good.values,
            frame_coordinates=good.frame_coordinates,
            primary_coordinate_key=good.primary_coordinate_key,
            source_keys=good.source_keys,
            source_digests=bad,
            metadata=good.metadata,
        )


def test_equivalent_inputs_produce_deterministic_stack_digest():
    first = _stack()
    second = build_operando_stack(
        _frames(),
        frame_coordinates=_coordinates(),
        primary_coordinate_key="time",
        metadata={"modality": "test-spectrum"},
    )

    assert first.digest == second.digest
    assert len(first.digest) == 64
    assert first == second


@pytest.mark.parametrize(
    "bad_signal",
    [
        [1000.0, 1000.0, 1200.0],
        [1000.0, 1200.0, 1100.0],
        [1000.0, np.nan, 1200.0],
        [1000.0, np.inf, 1200.0],
    ],
)
def test_signal_grid_must_be_finite_and_strictly_monotonic(bad_signal):
    frames = (
        Series(
            bad_signal,
            [1.0, 2.0, 3.0],
            key="f0",
            x_axis=Axis("wavenumber", unit="cm^-1"),
            y_axis=Axis("intensity", unit="a.u."),
        ),
    )

    with pytest.raises((OperandoStackError, ValueError)):
        build_operando_stack(
            frames,
            frame_coordinates=[
                FrameCoordinate("time", Axis("time", unit="s"), [0.0])
            ],
            primary_coordinate_key="time",
        )


def test_builder_rejects_complex_signal_or_values():
    complex_signal = Series(
        [1000.0 + 0j, 1100.0 + 0j],
        [1.0, 2.0],
        key="complex-x",
        x_axis=Axis("wavenumber", unit="cm^-1"),
        y_axis=Axis("intensity", unit="a.u."),
    )
    complex_values = Series(
        [1000.0, 1100.0],
        [1.0 + 1j, 2.0],
        key="complex-y",
        x_axis=Axis("wavenumber", unit="cm^-1"),
        y_axis=Axis("intensity", unit="a.u."),
    )
    coordinate = [FrameCoordinate("time", Axis("time", unit="s"), [0.0])]

    with pytest.raises(OperandoStackError, match="real"):
        build_operando_stack(
            [complex_signal],
            frame_coordinates=coordinate,
            primary_coordinate_key="time",
        )
    with pytest.raises(OperandoStackError, match="real"):
        build_operando_stack(
            [complex_values],
            frame_coordinates=coordinate,
            primary_coordinate_key="time",
        )


def test_builder_rejects_literal_grid_mismatch():
    first, second, _ = _frames()
    mismatched = second.with_data(x=[1000.0, 1100.0, 1200.0000000001])

    with pytest.raises(OperandoStackError, match="literally identical"):
        build_operando_stack(
            [first, mismatched],
            frame_coordinates=[
                FrameCoordinate("time", Axis("time", unit="s"), [0.0, 1.0])
            ],
            primary_coordinate_key="time",
        )


def test_builder_rejects_mixed_signal_units():
    first, second, _ = _frames()
    second = Series(
        second.x,
        second.y,
        key=second.key,
        x_axis=Axis("wavenumber", unit="m^-1", metadata={"calibration": "source-native"}),
        y_axis=second.y_axis,
    )

    with pytest.raises(OperandoStackError, match="signal-axis"):
        build_operando_stack(
            [first, second],
            frame_coordinates=[
                FrameCoordinate("time", Axis("time", unit="s"), [0.0, 1.0])
            ],
            primary_coordinate_key="time",
        )


def test_builder_rejects_mixed_value_processing_basis():
    first, second, _ = _frames(basis="raw")
    second = Series(
        second.x,
        second.y,
        key=second.key,
        x_axis=second.x_axis,
        y_axis=Axis(
            "intensity",
            unit="a.u.",
            metadata={"processing_basis": "normalized-max"},
        ),
    )

    with pytest.raises(OperandoStackError, match="processing basis"):
        build_operando_stack(
            [first, second],
            frame_coordinates=[
                FrameCoordinate("time", Axis("time", unit="s"), [0.0, 1.0])
            ],
            primary_coordinate_key="time",
        )


def test_builder_requires_unique_nonempty_frame_keys():
    first, second, _ = _frames()
    duplicate = Series(
        second.x,
        second.y,
        key=first.key,
        x_axis=second.x_axis,
        y_axis=second.y_axis,
    )

    with pytest.raises(OperandoStackError, match="unique"):
        build_operando_stack(
            [first, duplicate],
            frame_coordinates=[
                FrameCoordinate("time", Axis("time", unit="s"), [0.0, 1.0])
            ],
            primary_coordinate_key="time",
        )

    blank = first.with_data(key="")
    with pytest.raises(OperandoStackError, match="Series.key"):
        build_operando_stack(
            [blank],
            frame_coordinates=[
                FrameCoordinate("time", Axis("time", unit="s"), [0.0])
            ],
            primary_coordinate_key="time",
        )


def test_stack_requires_coordinate_lengths_and_explicit_known_primary_key():
    frames = _frames()

    with pytest.raises(OperandoStackError, match="length"):
        build_operando_stack(
            frames,
            frame_coordinates=[
                FrameCoordinate("time", Axis("time", unit="s"), [0.0, 1.0])
            ],
            primary_coordinate_key="time",
        )

    with pytest.raises(OperandoStackError, match="primary_coordinate_key"):
        build_operando_stack(
            frames,
            frame_coordinates=_coordinates(),
            primary_coordinate_key="temperature",
        )


def test_frame_coordinate_rejects_nonfinite_or_complex_values():
    with pytest.raises(OperandoStackError, match="finite"):
        FrameCoordinate("time", Axis("time", unit="s"), [0.0, np.nan])
    with pytest.raises(OperandoStackError, match="real"):
        FrameCoordinate("time", Axis("time", unit="s"), [0.0 + 1j, 1.0])
