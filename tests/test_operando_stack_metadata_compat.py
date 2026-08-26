from __future__ import annotations

import numpy as np

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.operando import FrameCoordinate, build_operando_stack


def _stack_with_axis_metadata(metadata):
    signal_axis = Axis("wavenumber", unit="cm^-1", metadata=metadata)
    value_axis = Axis("intensity", unit="a.u.", metadata={"processing_basis": "raw"})
    frames = tuple(
        Series(
            [1000.0, 1100.0, 1200.0],
            [1.0 + index, 2.0 + index, 3.0 + index],
            key=f"frame-{index}",
            x_axis=signal_axis,
            y_axis=value_axis,
        )
        for index in range(2)
    )
    return build_operando_stack(
        frames,
        frame_coordinates=[FrameCoordinate("time", Axis("time", unit="s"), [0.0, 1.0])],
        primary_coordinate_key="time",
    )


def test_numpy_scalar_axis_metadata_canonicalizes_like_python_scalars():
    python_stack = _stack_with_axis_metadata(
        {"index": 7, "factor": 1.25, "calibrated": True}
    )
    numpy_stack = _stack_with_axis_metadata(
        {
            "index": np.int64(7),
            "factor": np.float64(1.25),
            "calibrated": np.bool_(True),
        }
    )

    assert python_stack.digest == numpy_stack.digest
