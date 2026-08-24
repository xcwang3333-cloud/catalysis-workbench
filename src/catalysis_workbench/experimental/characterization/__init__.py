"""Experimental characterization processing and publication adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .ftir import (
    FTIRBand,
    FTIRBandMeasurement,
    FTIRBaselineFit,
    FTIRBaselineWindow,
    FTIRError,
    FTIRPeakAnnotation,
    FTIRProcessingConfig,
    fit_ftir_baseline,
    measure_ftir_band,
    process_ftir,
    process_ftir_dataset,
    stack_ftir_dataset,
    subtract_ftir_baseline,
    transmittance_to_absorbance,
    validate_ftir_overlay,
    validate_ftir_series,
)
from .raman import (
    RamanBand,
    RamanBandMeasurement,
    RamanError,
    RamanPeakAnnotation,
    RamanProcessingConfig,
    RamanRatioResult,
    id_ig_ratio,
    measure_raman_band,
    process_raman,
    process_raman_dataset,
    raman_ratio,
    stack_raman_dataset,
    validate_raman_series,
)
from .sorption import (
    RelativePressureUnit,
    SorptionBranch,
    SorptionBranchSelection,
    SorptionCondition,
    SorptionDirection,
    SorptionError,
    SorptionLoadingFamily,
    SorptionProcessingConfig,
    SorptionWindow,
    SorptionWindowSummary,
    convert_relative_pressure,
    prepare_sorption_series,
    process_sorption,
    process_sorption_dataset,
    select_sorption_branch,
    summarize_sorption_window,
    validate_sorption_overlay,
    validate_sorption_series,
)
from .thermal import (
    DTGSignMode,
    TemperatureUnit,
    TGANormalization,
    ThermalAnnotation,
    ThermalAreaMode,
    ThermalDirection,
    ThermalError,
    ThermalExtremumMode,
    ThermalProcessingConfig,
    ThermalTechnique,
    ThermalWindow,
    ThermalWindowMeasurement,
    convert_temperature,
    derive_dtg,
    measure_thermal_window,
    normalize_tga_mass,
    process_thermal,
    process_thermal_dataset,
    stack_thermal_dataset,
    validate_dtg_series,
    validate_temperature_programmed_series,
    validate_tga_series,
    validate_thermal_overlay,
)
from .xrd import (
    PeakAnnotation,
    XRDError,
    XRDProcessingConfig,
    XRDReferencePattern,
    process_xrd,
    process_xrd_dataset,
    stack_xrd_dataset,
    validate_xrd_series,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from catalysis_workbench.core import Dataset, Series
    from catalysis_workbench.visualization import FigureSpec


def plot_xrd(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
    stack_step: float | None = None,
    stack_start: float = 0.0,
    peak_annotations: Sequence[PeakAnnotation] = (),
    reference_patterns: Sequence[XRDReferencePattern] = (),
    reference_base: float = 0.02,
    reference_height: float = 0.08,
    reference_gap: float = 0.03,
) -> tuple[Figure, Axes]:
    """Lazily dispatch to the shared-renderer XRD publication adapter."""
    from .plotting import plot_xrd as _plot_xrd

    return _plot_xrd(
        data,
        spec,
        preset=preset,
        stack_step=stack_step,
        stack_start=stack_start,
        peak_annotations=peak_annotations,
        reference_patterns=reference_patterns,
        reference_base=reference_base,
        reference_height=reference_height,
        reference_gap=reference_gap,
    )


def plot_raman(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
    stack_step: float | None = None,
    stack_start: float = 0.0,
    peak_annotations: Sequence[RamanPeakAnnotation] = (),
) -> tuple[Figure, Axes]:
    """Lazily dispatch to the shared-renderer Raman publication adapter."""
    from .raman_plotting import plot_raman as _plot_raman

    return _plot_raman(
        data,
        spec,
        preset=preset,
        stack_step=stack_step,
        stack_start=stack_start,
        peak_annotations=peak_annotations,
    )


def plot_ftir(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
    stack_step: float | None = None,
    stack_start: float = 0.0,
    peak_annotations: Sequence[FTIRPeakAnnotation] = (),
    wavenumber_direction: str = "descending",
) -> tuple[Figure, Axes]:
    """Lazily dispatch to the shared-renderer FTIR publication adapter."""
    from .ftir_plotting import plot_ftir as _plot_ftir

    return _plot_ftir(
        data,
        spec,
        preset=preset,
        stack_step=stack_step,
        stack_start=stack_start,
        peak_annotations=peak_annotations,
        wavenumber_direction=wavenumber_direction,
    )


def plot_thermal(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    technique: ThermalTechnique,
    preset: str = "publication",
    stack_step: float | None = None,
    stack_start: float = 0.0,
    annotations: Sequence[ThermalAnnotation] = (),
) -> tuple[Figure, Axes]:
    """Lazily dispatch to the shared-renderer thermal publication adapter."""
    from .thermal_plotting import plot_thermal as _plot_thermal

    return _plot_thermal(
        data,
        spec,
        technique=technique,
        preset=preset,
        stack_step=stack_step,
        stack_start=stack_start,
        annotations=annotations,
    )


def plot_sorption(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    branch: SorptionBranchSelection = "all",
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Lazily dispatch to the shared-renderer gas-sorption publication adapter."""
    from .sorption_plotting import plot_sorption as _plot_sorption

    return _plot_sorption(data, spec, branch=branch, preset=preset)


__all__ = [
    "DTGSignMode",
    "FTIRBand",
    "FTIRBandMeasurement",
    "FTIRBaselineFit",
    "FTIRBaselineWindow",
    "FTIRError",
    "FTIRPeakAnnotation",
    "FTIRProcessingConfig",
    "PeakAnnotation",
    "RamanBand",
    "RamanBandMeasurement",
    "RamanError",
    "RamanPeakAnnotation",
    "RamanProcessingConfig",
    "RamanRatioResult",
    "RelativePressureUnit",
    "SorptionBranch",
    "SorptionBranchSelection",
    "SorptionCondition",
    "SorptionDirection",
    "SorptionError",
    "SorptionLoadingFamily",
    "SorptionProcessingConfig",
    "SorptionWindow",
    "SorptionWindowSummary",
    "TGANormalization",
    "TemperatureUnit",
    "ThermalAnnotation",
    "ThermalAreaMode",
    "ThermalDirection",
    "ThermalError",
    "ThermalExtremumMode",
    "ThermalProcessingConfig",
    "ThermalTechnique",
    "ThermalWindow",
    "ThermalWindowMeasurement",
    "XRDError",
    "XRDProcessingConfig",
    "XRDReferencePattern",
    "convert_relative_pressure",
    "convert_temperature",
    "derive_dtg",
    "fit_ftir_baseline",
    "id_ig_ratio",
    "measure_ftir_band",
    "measure_raman_band",
    "measure_thermal_window",
    "normalize_tga_mass",
    "plot_ftir",
    "plot_raman",
    "plot_sorption",
    "plot_thermal",
    "plot_xrd",
    "prepare_sorption_series",
    "process_ftir",
    "process_ftir_dataset",
    "process_raman",
    "process_raman_dataset",
    "process_sorption",
    "process_sorption_dataset",
    "process_thermal",
    "process_thermal_dataset",
    "process_xrd",
    "process_xrd_dataset",
    "raman_ratio",
    "select_sorption_branch",
    "stack_ftir_dataset",
    "stack_raman_dataset",
    "stack_thermal_dataset",
    "stack_xrd_dataset",
    "subtract_ftir_baseline",
    "summarize_sorption_window",
    "transmittance_to_absorbance",
    "validate_dtg_series",
    "validate_ftir_overlay",
    "validate_ftir_series",
    "validate_raman_series",
    "validate_sorption_overlay",
    "validate_sorption_series",
    "validate_temperature_programmed_series",
    "validate_tga_series",
    "validate_thermal_overlay",
    "validate_xrd_series",
]
