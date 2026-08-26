"""Shared immutable operando/time-resolved analysis state and exact operations."""

from .operations import (
    OperandoOperationError,
    OperandoTrace,
    PearsonCorrelationResult,
    TracePair,
    build_operando_trace,
    crop_signal,
    frame_cut,
    pair_traces,
    pearson_correlation,
    select_frames,
    select_frames_by_coordinate,
    signal_position_cut,
)
from .stack import (
    FrameCoordinate,
    OperandoStack,
    OperandoStackError,
    build_operando_stack,
    series_array_digest,
)

__all__ = [
    "FrameCoordinate",
    "OperandoOperationError",
    "OperandoStack",
    "OperandoStackError",
    "OperandoTrace",
    "PearsonCorrelationResult",
    "TracePair",
    "build_operando_stack",
    "build_operando_trace",
    "crop_signal",
    "frame_cut",
    "pair_traces",
    "pearson_correlation",
    "select_frames",
    "select_frames_by_coordinate",
    "series_array_digest",
    "signal_position_cut",
]
