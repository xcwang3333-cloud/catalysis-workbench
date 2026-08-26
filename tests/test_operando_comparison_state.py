from __future__ import annotations

import pytest

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental import operando
from catalysis_workbench.experimental.operando import (
    FrameCoordinate,
    OperandoOperationError,
    PearsonCorrelationResult,
    TracePair,
    build_operando_stack,
    build_operando_trace,
    select_frames,
)


def _stack():
    frames = tuple(
        Series(
            [1000.0, 1100.0, 1200.0],
            [scale, 2.0 * scale, 3.0 * scale],
            key=f"frame-{index}",
            x_axis=Axis("wavenumber", unit="cm^-1"),
            y_axis=Axis(
                "intensity",
                unit="a.u.",
                metadata={"processing_basis": "raw"},
            ),
        )
        for index, scale in enumerate((1.0, 2.0, 3.0))
    )
    return build_operando_stack(
        frames,
        frame_coordinates=[
            FrameCoordinate("time", Axis("time", unit="s"), [0.0, 10.0, 20.0]),
        ],
        primary_coordinate_key="time",
    )


def _trace(stack, values):
    return build_operando_trace(
        stack,
        coordinate_key="time",
        values=values,
        value_axis=Axis("descriptor", unit="a.u."),
        method="caller_descriptor",
        parameters={"descriptor": "direct-constructor-test"},
    )


def test_direct_trace_pair_constructor_enforces_exact_compatibility():
    stack = _stack()
    left = _trace(stack, [1.0, 2.0, 3.0])
    right = _trace(stack, [2.0, 4.0, 6.0])

    pair = TracePair(left=left, right=right)
    assert pair.frame_keys == stack.frame_keys
    assert pair.left_trace_digest == left.digest
    assert pair.right_trace_digest == right.digest

    reordered_stack = select_frames(stack, indices=[1, 0, 2])
    reordered = _trace(reordered_stack, [4.0, 2.0, 6.0])
    with pytest.raises(OperandoOperationError, match="frame keys must match exactly"):
        TracePair(left=left, right=reordered)


def test_direct_pearson_result_computes_statistics_from_retained_pair():
    stack = _stack()
    left = _trace(stack, [1.0, 2.0, 3.0])
    right = _trace(stack, [2.0, 4.0, 6.0])
    pair = TracePair(left=left, right=right)

    result = PearsonCorrelationResult(pair=pair)
    assert result.coefficient == pytest.approx(1.0)
    assert result.p_value == pytest.approx(0.0)
    assert result.source_digests == (left.digest, right.digest)

    with pytest.raises(TypeError):
        PearsonCorrelationResult(pair=pair, coefficient=0.0)  # type: ignore[call-arg]


def test_direct_pearson_result_rejects_constant_trace():
    stack = _stack()
    pair = TracePair(
        left=_trace(stack, [1.0, 1.0, 1.0]),
        right=_trace(stack, [1.0, 2.0, 3.0]),
    )
    with pytest.raises(OperandoOperationError, match="constant"):
        PearsonCorrelationResult(pair=pair)


def test_implementation_submodule_exposes_same_hardened_comparison_state():
    assert operando._operations.TracePair is TracePair
    assert operando._operations.PearsonCorrelationResult is PearsonCorrelationResult
    assert operando._operations.pair_traces is operando.pair_traces
    assert operando._operations.pearson_correlation is operando.pearson_correlation
