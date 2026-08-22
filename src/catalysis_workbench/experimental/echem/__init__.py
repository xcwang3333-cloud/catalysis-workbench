"""Electrochemical data processing and analysis."""

from .lsv import (
    LSVError,
    LSVProcessingConfig,
    convert_potential_to_rhe,
    correct_ir_drop,
    process_lsv,
    process_lsv_dataset,
    rhe_offset_from_she,
    to_current_density,
)

__all__ = [
    "LSVError",
    "LSVProcessingConfig",
    "convert_potential_to_rhe",
    "correct_ir_drop",
    "process_lsv",
    "process_lsv_dataset",
    "rhe_offset_from_she",
    "to_current_density",
]
