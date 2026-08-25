"""Experimental characterization processing and publication adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .bet import (
    BETConsistencyResult,
    BETError,
    BETFitDiagnostics,
    BETFitResult,
    BETRegionEvaluation,
    evaluate_bet_region,
    fit_bet,
    summarize_bet_fit,
)
from .composition import (
    BulkMassFractionUnit,
    CompositionBasis,
    CompositionError,
    CompositionMeasurement,
    CompositionSummary,
    CompositionSummaryTable,
    CompositionTable,
    SolutionConcentrationUnit,
    convert_composition_table,
    convert_composition_unit,
    read_composition_csv,
    read_composition_excel,
    select_composition,
    solution_concentration_to_bulk_mass_fraction,
    summarize_composition_replicates,
)
from .exafs import (
    EXAFSDirection,
    EXAFSError,
    EXAFSFTComponent,
    EXAFSFTResult,
    EXAFSFTSpec,
    EXAFSKSpaceResult,
    EXAFSKSpaceSpec,
    forward_ft_exafs,
    ft_exafs_component,
    prepare_exafs_kspace,
    validate_exafs_series,
)
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
from .wt_exafs import (
    EXAFSWTComponent,
    EXAFSWTResult,
    EXAFSWTSpec,
    cauchy_wt_exafs,
)
from .xas import (
    XANESNormalizationResult,
    XANESNormalizationSpec,
    XASError,
    XASWindow,
    normalize_xanes,
    shift_xas_energy,
    validate_xas_series,
    xanes_relative_energy,
)
from .xps import (
    XPSBackgroundMethod,
    XPSBackgroundResult,
    XPSDirection,
    XPSError,
    linear_xps_background,
    prepare_xps_region,
    shift_xps_binding_energy,
    shirley_xps_background,
    validate_xps_series,
)
from .xps_diagnostics import XPSFitDiagnostics, summarize_xps_fit
from .xps_fitting import (
    XPSDoubletSpec,
    XPSPeakFitResult,
    XPSProcessingStep,
    fit_xps_peaks,
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


def plot_ft_exafs(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Lazily render retained FT-EXAFS real-valued components."""
    from .exafs_plotting import plot_ft_exafs as _plot_ft_exafs

    return _plot_ft_exafs(data, spec, preset=preset)


def plot_wt_exafs(
    result: EXAFSWTResult,
    spec: FigureSpec | None = None,
    *,
    component: EXAFSWTComponent = "magnitude",
    preset: str = "publication",
    cmap: str | None = None,
    vmin: float | None = None,
    vmax: float | None = None,
    show_colorbar: bool = False,
) -> tuple[Figure, Axes]:
    """Lazily render one retained WT-EXAFS k-R map component."""
    from .wt_exafs_plotting import plot_wt_exafs as _plot_wt_exafs

    return _plot_wt_exafs(
        result,
        spec,
        component=component,
        preset=preset,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        show_colorbar=show_colorbar,
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


def plot_bet_fit(
    result: BETFitResult,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Lazily render an already-computed accepted quantitative BET fit."""
    from .bet_plotting import plot_bet_fit as _plot_bet_fit

    return _plot_bet_fit(result, spec, preset=preset)


def plot_composition(
    data: CompositionTable | CompositionSummaryTable,
    spec: FigureSpec | None = None,
    *,
    error: str = "none",
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Lazily dispatch to the shared-renderer composition publication adapter."""
    from .composition_plotting import plot_composition as _plot_composition

    return _plot_composition(data, spec, error=error, preset=preset)


def plot_xanes(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Lazily render already-prepared compatible XAS/XANES traces."""
    from .xas_plotting import plot_xanes as _plot_xanes

    return _plot_xanes(data, spec, preset=preset)


def plot_xps_fit(
    result: XPSPeakFitResult,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
    show_background: bool = True,
    show_components: bool = True,
    show_residual: bool = False,
    binding_energy_display: str = "descending",
    residual_height_fraction: float = 0.22,
    residual_gap_fraction: float = 0.05,
) -> tuple[Figure, tuple[Axes, ...]]:
    """Lazily render an already-computed constrained XPS fit."""
    from .xps_plotting import plot_xps_fit as _plot_xps_fit

    return _plot_xps_fit(
        result,
        spec,
        preset=preset,
        show_background=show_background,
        show_components=show_components,
        show_residual=show_residual,
        binding_energy_display=binding_energy_display,
        residual_height_fraction=residual_height_fraction,
        residual_gap_fraction=residual_gap_fraction,
    )


__all__ = [
    "BETConsistencyResult",
    "BETError",
    "BETFitDiagnostics",
    "BETFitResult",
    "BETRegionEvaluation",
    "BulkMassFractionUnit",
    "CompositionBasis",
    "CompositionError",
    "CompositionMeasurement",
    "CompositionSummary",
    "CompositionSummaryTable",
    "CompositionTable",
    "DTGSignMode",
    "EXAFSDirection",
    "EXAFSError",
    "EXAFSFTComponent",
    "EXAFSFTResult",
    "EXAFSFTSpec",
    "EXAFSKSpaceResult",
    "EXAFSKSpaceSpec",
    "EXAFSWTComponent",
    "EXAFSWTResult",
    "EXAFSWTSpec",
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
    "SolutionConcentrationUnit",
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
    "XANESNormalizationResult",
    "XANESNormalizationSpec",
    "XASError",
    "XASWindow",
    "XPSBackgroundMethod",
    "XPSBackgroundResult",
    "XPSDirection",
    "XPSDoubletSpec",
    "XPSError",
    "XPSFitDiagnostics",
    "XPSPeakFitResult",
    "XPSProcessingStep",
    "XRDError",
    "XRDProcessingConfig",
    "XRDReferencePattern",
    "cauchy_wt_exafs",
    "convert_composition_table",
    "convert_composition_unit",
    "convert_relative_pressure",
    "convert_temperature",
    "derive_dtg",
    "evaluate_bet_region",
    "fit_bet",
    "fit_ftir_baseline",
    "fit_xps_peaks",
    "forward_ft_exafs",
    "ft_exafs_component",
    "id_ig_ratio",
    "linear_xps_background",
    "measure_ftir_band",
    "measure_raman_band",
    "measure_thermal_window",
    "normalize_tga_mass",
    "normalize_xanes",
    "plot_bet_fit",
    "plot_composition",
    "plot_ft_exafs",
    "plot_ftir",
    "plot_raman",
    "plot_sorption",
    "plot_thermal",
    "plot_wt_exafs",
    "plot_xanes",
    "plot_xps_fit",
    "plot_xrd",
    "prepare_exafs_kspace",
    "prepare_sorption_series",
    "prepare_xps_region",
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
    "read_composition_csv",
    "read_composition_excel",
    "select_composition",
    "select_sorption_branch",
    "shift_xas_energy",
    "shift_xps_binding_energy",
    "shirley_xps_background",
    "solution_concentration_to_bulk_mass_fraction",
    "stack_ftir_dataset",
    "stack_raman_dataset",
    "stack_thermal_dataset",
    "stack_xrd_dataset",
    "subtract_ftir_baseline",
    "summarize_bet_fit",
    "summarize_composition_replicates",
    "summarize_sorption_window",
    "summarize_xps_fit",
    "transmittance_to_absorbance",
    "validate_dtg_series",
    "validate_exafs_series",
    "validate_ftir_overlay",
    "validate_ftir_series",
    "validate_raman_series",
    "validate_sorption_overlay",
    "validate_sorption_series",
    "validate_temperature_programmed_series",
    "validate_tga_series",
    "validate_thermal_overlay",
    "validate_xas_series",
    "validate_xps_series",
    "validate_xrd_series",
    "xanes_relative_energy",
]
