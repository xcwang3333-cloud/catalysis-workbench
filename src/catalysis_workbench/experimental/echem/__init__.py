"""Electrochemical data processing, analysis, and publication adapters."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

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
    """Lazily dispatch to the publication LSV adapter.

    Keeping the visualization import inside the call preserves the architecture rule
    that numerical electrochemistry can be imported and used without importing
    Matplotlib/the visualization package.
    """
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


__all__ = [
    "AnalysisProvenance",
    "CurrentSign",
    "EchemQuantityError",
    "FARADAY_CONSTANT_C_MOL",
    "FaradaicEfficiencyClosure",
    "FaradaicEfficiencyError",
    "FaradaicEfficiencyMode",
    "FaradaicEfficiencyOutputUnit",
    "FaradaicEfficiencyResult",
    "FitWindow",
    "GAS_CONSTANT_J_MOL_K",
    "LSVError",
    "LSVProcessingConfig",
    "SourceDataRef",
    "TafelBranch",
    "TafelError",
    "TafelFitResult",
    "amount_to_mol",
    "area_to_cm2",
    "charge_to_c",
    "convert_potential_to_rhe",
    "correct_ir_drop",
    "current_density_to_a_cm2",
    "current_to_a",
    "electron_number",
    "faradaic_efficiency_closure",
    "faradaic_efficiency_dataset",
    "faradaic_efficiency_from_amount",
    "faradaic_efficiency_from_rate",
    "faradaic_efficiency_series",
    "fit_tafel",
    "fit_tafel_dataset",
    "loading_to_g_cm2",
    "make_analysis_provenance",
    "mass_to_g",
    "molar_rate_to_mol_s",
    "normalize_reference_name",
    "plot_faradaic_efficiency",
    "plot_lsv",
    "plot_tafel",
    "potential_to_v",
    "process_lsv",
    "process_lsv_dataset",
    "rhe_offset_from_she",
    "rotation_rate_to_rad_s",
    "same_reference",
    "scan_rate_to_v_s",
    "series_data_sha256",
    "source_data_ref",
    "time_to_s",
    "to_current_density",
]
