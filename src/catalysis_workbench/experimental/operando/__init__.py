"""Shared immutable operando/time-resolved analysis state and exact operations."""

from . import operations as _operations
from .comparison import (
    PearsonCorrelationResult,
    TracePair,
    pair_traces,
    pearson_correlation,
)
from .operations import (
    OperandoOperationError,
    OperandoTrace,
    build_operando_trace,
    crop_signal,
    frame_cut,
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

# Keep direct imports from the implementation submodule on the same fail-closed
# public comparison state after package initialization.
_operations.TracePair = TracePair
_operations.PearsonCorrelationResult = PearsonCorrelationResult
_operations.pair_traces = pair_traces
_operations.pearson_correlation = pearson_correlation

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
