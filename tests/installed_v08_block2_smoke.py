"""Installed-wheel smoke for v0.8 Block-2 exact operando operations."""

from __future__ import annotations

import numpy as np

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.operando import (
    FrameCoordinate,
    OperandoTrace,
    PearsonCorrelationResult,
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


def main() -> None:
    signal_axis = Axis("wavenumber", unit="cm^-1")
    value_axis = Axis(
        "intensity",
        unit="a.u.",
        metadata={"processing_basis": "raw"},
    )
    frames = tuple(
        Series(
            [1300.0, 1200.0, 1100.0, 1000.0],
            [4.0 * scale, 3.0 * scale, 2.0 * scale, 1.0 * scale],
            key=f"frame-{index}",
            x_axis=signal_axis,
            y_axis=value_axis,
        )
        for index, scale in enumerate((1.0, 2.0, 3.0, 4.0))
    )
    stack = build_operando_stack(
        frames,
        frame_coordinates=[
            FrameCoordinate("time", Axis("time", unit="s"), [0.0, 10.0, 20.0, 30.0]),
            FrameCoordinate(
                "potential",
                Axis("potential", unit="V", metadata={"reference": "RHE"}),
                [-0.5, -0.7, -0.5, -0.9],
            ),
        ],
        primary_coordinate_key="time",
    )

    selected = select_frames(stack, frame_keys=["frame-2", "frame-0"])
    assert selected.frame_keys == ("frame-2", "frame-0")
    repeated = select_frames_by_coordinate(
        stack,
        coordinate_key="potential",
        comparison="==",
        value=-0.5,
    )
    assert repeated.frame_keys == ("frame-0", "frame-2")

    cropped = crop_signal(stack, lower=1050.0, upper=1250.0)
    np.testing.assert_array_equal(cropped.signal, [1200.0, 1100.0])
    cut = frame_cut(stack, frame_key="frame-1")
    np.testing.assert_array_equal(cut.y, [8.0, 6.0, 4.0, 2.0])

    exact = signal_position_cut(stack, position=1200.0, coordinate_key="time")
    assert isinstance(exact, OperandoTrace)
    np.testing.assert_array_equal(exact.values, [3.0, 6.0, 9.0, 12.0])
    assert exact.reconstructed_result_digests() == exact.source_result_digests

    second = build_operando_trace(
        stack,
        coordinate_key="time",
        values=[2.0, 4.0, 6.0, 8.0],
        value_axis=Axis("descriptor", unit="a.u."),
        method="installed_smoke_descriptor",
        parameters={"source": "caller"},
    )
    pair = pair_traces(exact, second)
    assert pair.sample_count == 4
    result = pearson_correlation(exact, second)
    assert isinstance(result, PearsonCorrelationResult)
    assert result.sample_count == 4
    assert np.isclose(result.coefficient, 1.0)
    assert result.p_value >= 0.0
    assert result.source_digests == (exact.digest, second.digest)
    assert not result.left_values.flags.writeable

    print("installed v0.8 Block-2 operando operations smoke: ok")


if __name__ == "__main__":
    main()
