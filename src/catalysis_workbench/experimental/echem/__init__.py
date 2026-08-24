"""Electrochemical data processing, analysis, and publication adapters."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

from .activity import (
    ActivityBasis,
    ActivityCurrentBasis,
    ActivityNormalizationError,
    ActivityNormalizationResult,
    normalize_activity,
    normalize_activity_dataset,
    normalize_activity_series,
)
from .cv_cdl import (
    CdlCurrentBasis,
    CdlDifferenceMode,
    CdlError,
    CdlFitCollection,
    CdlFitResult,
    CdlPairProvenance,
    CVSamplingMethod,
    CVSweepPair,
    ECSAResult,
    ecsa_from_cdl,
    fit_cdl,
    fit_cdl_groups,
    sample_cv_current,
)
from .fe import (
    FaradaicEfficiencyClosure,
    FaradaicEfficiencyError,
    FaradaicEfficiencyMode,
    FaradaicEfficiencyOutputUnit,
    FaradaicEfficiencyResult,
    faradaic_efficiency_closure,
    faradaic_efficiency_dataset,
    faradaic_efficiency_from_amount,
    faradaic_efficiency_from_rate,
    faradaic_efficiency_series,
)
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
from .partial_current import (
    FaradaicEfficiencyInputUnit,
    PartialCurrentDensityError,
    PartialCurrentDensityResult,
    SignMode,
    partial_current_density,
)
from .partial_current_closure import (
    ClosureComparisonMode,
    PartialCurrentClosureError,
    PartialCurrentClosureResult,
    partial_current_closure,
    partial_current_closure_dataset,
)
from .partial_current_series import (
    partial_current_density_dataset,
    partial_current_density_series,
)
from .provenance import (
    AnalysisProvenance,
    FitWindow,
    SourceDataRef,
    make_analysis_provenance,
    series_data_sha256,
    source_data_ref,
)
from .quantities import (
    FARADAY_CONSTANT_C_MOL,
    GAS_CONSTANT_J_MOL_K,
    EchemQuantityError,
    amount_to_mol,
    area_to_cm2,
    charge_to_c,
    current_density_to_a_cm2,
    current_to_a,
    electron_number,
    loading_to_g_cm2,
    mass_to_g,
    molar_rate_to_mol_s,
    normalize_reference_name,
    potential_to_v,
    rotation_rate_to_rad_s,
    same_reference,
    scan_rate_to_v_s,
    time_to_s,
)
from .tafel import (
    CurrentSign,
    TafelBranch,
    TafelError,
    TafelFitResult,
    fit_tafel,
    fit_tafel_dataset,
)
from .tof import (
    AVOGADRO_CONSTANT_MOL_INV,
    TurnoverCurrentMode,
    TurnoverFrequencyError,
    TurnoverFrequencyResult,
    TurnoverInventoryBasis,
    TurnoverSourceKind,
    turnover_frequency_from_partial_current,
    turnover_frequency_from_partial_current_dataset,
    turnover_frequency_from_partial_current_series,
    turnover_frequency_from_rate,
    turnover_frequency_from_rate_dataset,
    turnover_frequency_from_rate_series,
)

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from catalysis_workbench.core import Dataset, Series
    from catalysis_workbench.visualization import FigureSpec, ScatterError


def plot_lsv(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Lazily dispatch to the publication LSV adapter."""
    from .plotting import plot_lsv as _plot_lsv

    return _plot_lsv(data, spec, preset=preset)


def plot_tafel(
    results: TafelFitResult | Sequence[TafelFitResult],
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Lazily dispatch immutable Tafel fit results to the publication adapter."""
    from .tafel_plotting import plot_tafel as _plot_tafel

    return _plot_tafel(results, spec, preset=preset)


def plot_faradaic_efficiency(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    kind: str = "scatter",
    errors: ScatterError | Mapping[str, ScatterError] | None = None,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Lazily dispatch already calculated FE data to shared publication rendering."""
    from .fe_plotting import plot_faradaic_efficiency as _plot_faradaic_efficiency

    return _plot_faradaic_efficiency(
        data,
        spec,
        kind=kind,  # type: ignore[arg-type]
        errors=errors,
        preset=preset,
    )


def plot_partial_current_density(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    kind: str = "scatter",
    errors: ScatterError | Mapping[str, ScatterError] | None = None,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Lazily render already calculated product partial-current data."""
    from .partial_current_plotting import (
        plot_partial_current_density as _plot_partial_current_density,
    )

    return _plot_partial_current_density(
        data,
        spec,
        kind=kind,  # type: ignore[arg-type]
        errors=errors,
        preset=preset,
    )


def plot_activity(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    kind: str = "scatter",
    errors: ScatterError | Mapping[str, ScatterError] | None = None,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Lazily render already normalized activity data."""
    from .activity_plotting import plot_activity as _plot_activity

    return _plot_activity(
        data,
        spec,
        kind=kind,  # type: ignore[arg-type]
        errors=errors,
        preset=preset,
    )


def plot_turnover_frequency(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    kind: str = "scatter",
    errors: ScatterError | Mapping[str, ScatterError] | None = None,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Lazily render already calculated TOF/TOFapp data."""
    from .tof_plotting import plot_turnover_frequency as _plot_turnover_frequency

    return _plot_turnover_frequency(
        data,
        spec,
        kind=kind,  # type: ignore[arg-type]
        errors=errors,
        preset=preset,
    )


def plot_cv(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Lazily render already prepared cyclic-voltammetry sweeps."""
    from .cv_cdl_plotting import plot_cv as _plot_cv

    return _plot_cv(data, spec, preset=preset)


def plot_cdl_fit(
    result: CdlFitResult,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Lazily render an already calculated Cdl fit."""
    from .cv_cdl_plotting import plot_cdl_fit as _plot_cdl_fit

    return _plot_cdl_fit(result, spec, preset=preset)


__all__ = [
    "AVOGADRO_CONSTANT_MOL_INV",
    "ActivityBasis",
    "ActivityCurrentBasis",
    "ActivityNormalizationError",
    "ActivityNormalizationResult",
    "AnalysisProvenance",
    "CVSamplingMethod",
    "CVSweepPair",
    "CdlCurrentBasis",
    "CdlDifferenceMode",
    "CdlError",
    "CdlFitCollection",
    "CdlFitResult",
    "CdlPairProvenance",
    "ClosureComparisonMode",
    "CurrentSign",
    "ECSAResult",
    "EchemQuantityError",
    "FARADAY_CONSTANT_C_MOL",
    "FaradaicEfficiencyClosure",
    "FaradaicEfficiencyError",
    "FaradaicEfficiencyInputUnit",
    "FaradaicEfficiencyMode",
    "FaradaicEfficiencyOutputUnit",
    "FaradaicEfficiencyResult",
    "FitWindow",
    "GAS_CONSTANT_J_MOL_K",
    "LSVError",
    "LSVProcessingConfig",
    "PartialCurrentClosureError",
    "PartialCurrentClosureResult",
    "PartialCurrentDensityError",
    "PartialCurrentDensityResult",
    "SignMode",
    "SourceDataRef",
    "TafelBranch",
    "TafelError",
    "TafelFitResult",
    "TurnoverCurrentMode",
    "TurnoverFrequencyError",
    "TurnoverFrequencyResult",
    "TurnoverInventoryBasis",
    "TurnoverSourceKind",
    "amount_to_mol",
    "area_to_cm2",
    "charge_to_c",
    "convert_potential_to_rhe",
    "correct_ir_drop",
    "current_density_to_a_cm2",
    "current_to_a",
    "ecsa_from_cdl",
    "electron_number",
    "faradaic_efficiency_closure",
    "faradaic_efficiency_dataset",
    "faradaic_efficiency_from_amount",
    "faradaic_efficiency_from_rate",
    "faradaic_efficiency_series",
    "fit_cdl",
    "fit_cdl_groups",
    "fit_tafel",
    "fit_tafel_dataset",
    "loading_to_g_cm2",
    "make_analysis_provenance",
    "mass_to_g",
    "molar_rate_to_mol_s",
    "normalize_activity",
    "normalize_activity_dataset",
    "normalize_activity_series",
    "normalize_reference_name",
    "partial_current_closure",
    "partial_current_closure_dataset",
    "partial_current_density",
    "partial_current_density_dataset",
    "partial_current_density_series",
    "plot_activity",
    "plot_cdl_fit",
    "plot_cv",
    "plot_faradaic_efficiency",
    "plot_lsv",
    "plot_partial_current_density",
    "plot_tafel",
    "plot_turnover_frequency",
    "potential_to_v",
    "process_lsv",
    "process_lsv_dataset",
    "rhe_offset_from_she",
    "rotation_rate_to_rad_s",
    "same_reference",
    "sample_cv_current",
    "scan_rate_to_v_s",
    "series_data_sha256",
    "source_data_ref",
    "time_to_s",
    "to_current_density",
    "turnover_frequency_from_partial_current",
    "turnover_frequency_from_partial_current_dataset",
    "turnover_frequency_from_partial_current_series",
    "turnover_frequency_from_rate",
    "turnover_frequency_from_rate_dataset",
    "turnover_frequency_from_rate_series",
]
