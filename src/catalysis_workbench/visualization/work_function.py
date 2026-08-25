"""Passive publication rendering for retained planar-potential state."""

from __future__ import annotations

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from catalysis_workbench.computation.work_function import (
    FermiLevelSource,
    PlanarPotentialProfile,
    VacuumLevelResult,
    WorkFunctionResult,
)

from ._rendering import figure_axes_context, finalize_axes
from .presets import get_preset
from .specs import FigureSpec, VisualizationError


class WorkFunctionVisualizationError(VisualizationError):
    """Raised when retained work-function state cannot be rendered passively."""


def _validate_overlays(
    profile: PlanarPotentialProfile,
    vacuum_level: VacuumLevelResult | None,
    fermi_source: FermiLevelSource | None,
    work_function: WorkFunctionResult | None,
) -> None:
    if vacuum_level is not None:
        if not isinstance(vacuum_level, VacuumLevelResult):
            raise TypeError("vacuum_level must be a VacuumLevelResult")
        if vacuum_level.profile_digest != profile.digest:
            raise WorkFunctionVisualizationError(
                "vacuum_level must originate from the rendered planar profile"
            )
    if fermi_source is not None:
        if not isinstance(fermi_source, FermiLevelSource):
            raise TypeError("fermi_source must be a FermiLevelSource")
        if (
            profile.calculation_id is not None
            and fermi_source.calculation_id != profile.calculation_id
        ):
            raise WorkFunctionVisualizationError(
                "Fermi source calculation_id does not match the rendered profile"
            )
    if work_function is not None:
        if not isinstance(work_function, WorkFunctionResult):
            raise TypeError("work_function must be a WorkFunctionResult")
        if work_function.vacuum_profile_digest != profile.digest:
            raise WorkFunctionVisualizationError(
                "work_function must originate from the rendered planar profile"
            )
        if fermi_source is not None and work_function.fermi_source_digest != fermi_source.digest:
            raise WorkFunctionVisualizationError(
                "work_function does not reference the supplied Fermi source"
            )
        if vacuum_level is not None and work_function.vacuum_result_digest != vacuum_level.digest:
            raise WorkFunctionVisualizationError(
                "work_function does not reference the supplied vacuum level"
            )


def plot_planar_potential(
    profile: PlanarPotentialProfile,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
    vacuum_level: VacuumLevelResult | None = None,
    fermi_source: FermiLevelSource | None = None,
    work_function: WorkFunctionResult | None = None,
    show_vacuum_window: bool = True,
    annotate_work_function: bool = True,
) -> tuple[Figure, Axes]:
    """Render exact retained planar potential and optional precomputed references."""
    if not isinstance(profile, PlanarPotentialProfile):
        raise TypeError("profile must be a PlanarPotentialProfile")
    _validate_overlays(profile, vacuum_level, fermi_source, work_function)
    if not isinstance(show_vacuum_window, bool):
        raise TypeError("show_vacuum_window must be bool")
    if not isinstance(annotate_work_function, bool):
        raise TypeError("annotate_work_function must be bool")

    resolved_spec = get_preset(preset) if spec is None else spec
    if not isinstance(resolved_spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")
    if resolved_spec.xscale != "linear" or resolved_spec.yscale != "linear":
        raise WorkFunctionVisualizationError(
            "planar-potential plotting requires linear x and y scales"
        )

    coordinates_before = np.array(profile.normal_coordinates_angstrom, copy=True)
    potential_before = np.array(profile.potential_ev, copy=True)
    profile_digest_before = profile.digest
    vacuum_digest_before = vacuum_level.digest if vacuum_level is not None else None
    fermi_digest_before = fermi_source.digest if fermi_source is not None else None
    work_digest_before = work_function.digest if work_function is not None else None

    with figure_axes_context(resolved_spec) as (figure, ax):
        ax.plot(
            profile.normal_coordinates_angstrom,
            profile.potential_ev,
            linewidth=resolved_spec.style.line_width,
            label="planar potential",
        )
        if vacuum_level is not None:
            if show_vacuum_window:
                ax.axvspan(
                    vacuum_level.normal_start_angstrom,
                    vacuum_level.normal_stop_angstrom,
                    alpha=0.15,
                    label="vacuum window",
                )
            ax.axhline(
                vacuum_level.vacuum_ev,
                linestyle="--",
                linewidth=1.0,
                label="vacuum level",
            )
        if fermi_source is not None:
            ax.axhline(
                fermi_source.fermi_ev,
                linestyle=":",
                linewidth=1.0,
                label="Fermi level",
            )
        if work_function is not None and annotate_work_function:
            ax.text(
                0.98,
                0.98,
                f"Phi = {work_function.work_function_ev:.3f} eV",
                transform=ax.transAxes,
                ha="right",
                va="top",
            )

        labeled_count = 1
        if vacuum_level is not None:
            labeled_count += 1 + int(show_vacuum_window)
        if fermi_source is not None:
            labeled_count += 1
        finalize_axes(
            ax,
            resolved_spec,
            xlabel="Normal coordinate (angstrom)",
            ylabel="Planar potential (eV)",
            labeled_count=labeled_count,
        )

    if not np.array_equal(profile.normal_coordinates_angstrom, coordinates_before):
        raise RuntimeError("planar-potential plotting mutated retained coordinates")
    if not np.array_equal(profile.potential_ev, potential_before):
        raise RuntimeError("planar-potential plotting mutated retained potential")
    if profile.digest != profile_digest_before:
        raise RuntimeError("planar-potential plotting mutated retained profile identity")
    if vacuum_level is not None and vacuum_level.digest != vacuum_digest_before:
        raise RuntimeError("planar-potential plotting mutated retained vacuum identity")
    if fermi_source is not None and fermi_source.digest != fermi_digest_before:
        raise RuntimeError("planar-potential plotting mutated retained Fermi identity")
    if work_function is not None and work_function.digest != work_digest_before:
        raise RuntimeError("planar-potential plotting mutated retained work-function identity")
    return figure, ax


__all__ = ["WorkFunctionVisualizationError", "plot_planar_potential"]
