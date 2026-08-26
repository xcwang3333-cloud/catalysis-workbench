"""Installed-wheel smoke for the frozen v0.8 Block-1 operando foundation."""

from __future__ import annotations

import numpy as np

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.operando import (
    FrameCoordinate,
    OperandoStack,
    build_operando_stack,
    series_array_digest,
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
            [1200.0, 1100.0, 1000.0],
            [1.0 + index, 2.0 + index, 3.0 + index],
            key=f"frame-{index}",
            x_axis=signal_axis,
            y_axis=value_axis,
        )
        for index in range(3)
    )
    time = FrameCoordinate("time", Axis("time", unit="s"), [0.0, 10.0, 20.0])
    potential = FrameCoordinate(
        "potential",
        Axis("potential", unit="V", metadata={"reference": "RHE"}),
        [-0.5, -0.7, -0.5],
    )

    stack = build_operando_stack(
        frames,
        frame_coordinates=[time, potential],
        primary_coordinate_key="potential",
        expected_source_digests=[series_array_digest(frame) for frame in frames],
        metadata={"modality": "installed-smoke"},
    )

    assert isinstance(stack, OperandoStack)
    assert stack.frame_keys == ("frame-0", "frame-1", "frame-2")
    assert stack.signal_direction == "decreasing"
    assert stack.primary_coordinate.key == "potential"
    np.testing.assert_array_equal(stack.primary_coordinate.values, [-0.5, -0.7, -0.5])
    assert stack.reconstructed_source_digests() == stack.source_digests
    assert len(stack.digest) == 64
    assert not stack.signal.flags.writeable
    assert not stack.values.flags.writeable
    print("installed v0.8 Block-1 operando stack smoke: ok")


if __name__ == "__main__":
    main()
