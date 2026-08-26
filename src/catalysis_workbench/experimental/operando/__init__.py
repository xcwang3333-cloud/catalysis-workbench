"""Shared immutable operando/time-resolved data foundation."""

from .stack import (
    FrameCoordinate,
    OperandoStack,
    OperandoStackError,
    build_operando_stack,
    series_array_digest,
)

__all__ = [
    "FrameCoordinate",
    "OperandoStack",
    "OperandoStackError",
    "build_operando_stack",
    "series_array_digest",
]
