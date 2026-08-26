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
from .plotting import (
    OperandoVisualizationError,
    plot_operando_frame_cut,
    plot_operando_heatmap,
    plot_operando_trace,
    plot_operando_waterfall,
)
from .spectroscopy import (
    OperandoSpectroscopyError,
    build_ftir_operando_stack,
    build_raman_operando_stack,
    fit_component_center_trace,
    fit_component_fwhm_trace,
    ftir_band_area_trace,
    ftir_peak_position_trace,
    raman_band_area_trace,
    raman_peak_position_trace,
)
from .stack import (
    FrameCoordinate,
    OperandoStack,
    OperandoStackError,
    build_operando_stack,
    series_array_digest,
)
from .xas import (
    OperandoXASError,
    build_xanes_operando_stack,
    build_xas_operando_stack,
    xanes_edge_position_trace,
    xanes_white_line_intensity_trace,
    xas_window_integral_trace,
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
    "OperandoSpectroscopyError",
    "OperandoStack",
    "OperandoStackError",
    "OperandoTrace",
    "OperandoVisualizationError",
    "OperandoXASError",
    "PearsonCorrelationResult",
    "TracePair",
    "build_ftir_operando_stack",
    "build_operando_stack",
    "build_operando_trace",
    "build_raman_operando_stack",
    "build_xanes_operando_stack",
    "build_xas_operando_stack",
    "crop_signal",
    "fit_component_center_trace",
    "fit_component_fwhm_trace",
    "frame_cut",
    "ftir_band_area_trace",
    "ftir_peak_position_trace",
    "pair_traces",
    "pearson_correlation",
    "plot_operando_frame_cut",
    "plot_operando_heatmap",
    "plot_operando_trace",
    "plot_operando_waterfall",
    "raman_band_area_trace",
    "raman_peak_position_trace",
    "select_frames",
    "select_frames_by_coordinate",
    "series_array_digest",
    "signal_position_cut",
    "xanes_edge_position_trace",
    "xanes_white_line_intensity_trace",
    "xas_window_integral_trace",
]
