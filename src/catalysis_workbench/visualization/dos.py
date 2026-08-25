"""Passive publication rendering for retained DOS/PDOS traces."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from catalysis_workbench.computation.dos import DOSTrace
from catalysis_workbench.core import Axis, Dataset, Series

from .curves import render_curves
from .specs import FigureSpec, VisualizationError


class DOSVisualizationError(VisualizationError):
    """Raised when retained DOS traces cannot be rendered together safely."""


def _trace_tuple(traces: DOSTrace | Sequence[DOSTrace]) -> tuple[DOSTrace, ...]:
    if isinstance(traces, DOSTrace):
        return (traces,)
    retained = tuple(traces)
    if not retained or not all(isinstance(trace, DOSTrace) for trace in retained):
        raise DOSVisualizationError("traces must contain at least one DOSTrace")
    return retained


def _validate_trace_compatibility(traces: Sequence[DOSTrace]) -> None:
    first = traces[0]
    signature = (
        first.energy.reference_kind,
        first.density_unit,
        first.normalization_basis,
    )
    for trace in traces[1:]:
        other = (
            trace.energy.reference_kind,
            trace.density_unit,
            trace.normalization_basis,
        )
        if other != signature:
            raise DOSVisualizationError(
                "DOS overlays require matching energy-reference, density-unit, and "
                "normalization-basis semantics"
            )
    if first.energy.reference_kind == "source-native" and any(
        trace.source_dos_digest != first.source_dos_digest for trace in traces[1:]
    ):
        raise DOSVisualizationError(
            "source-native DOS overlays must come from the same ElectronicDOS source; "
            "cross-source comparison requires an explicit common energy reference"
        )


def _fermi_position(trace: DOSTrace) -> float:
    if trace.energy.source_fermi_ev is None:
        raise DOSVisualizationError("Fermi marker requires retained source_fermi_ev")
    return float(trace.energy.source_fermi_ev + trace.energy.applied_shift_ev)


def _shared_fermi_position(traces: Sequence[DOSTrace]) -> float:
    positions = tuple(_fermi_position(trace) for trace in traces)
    first_position = positions[0]
    if not all(
        np.isclose(value, first_position, rtol=0.0, atol=1e-12)
        for value in positions[1:]
    ):
        raise DOSVisualizationError(
            "one Fermi marker cannot represent traces with different retained positions"
        )
    return first_position


def plot_dos(
    traces: DOSTrace | Sequence[DOSTrace],
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
    mirror_spin_down: bool = False,
    show_fermi: bool = False,
) -> tuple[Figure, Axes]:
    """Render retained DOS traces without changing scientific processing state."""
    retained = _trace_tuple(traces)
    _validate_trace_compatibility(retained)
    fermi_position = _shared_fermi_position(retained) if show_fermi else None
    before_energy = tuple(np.array(trace.energy.values_ev, copy=True) for trace in retained)
    before_density = tuple(np.array(trace.density, copy=True) for trace in retained)

    x_axis = Axis(
        "energy",
        unit="eV",
        label="Energy",
        metadata={"reference": retained[0].energy.reference_kind},
    )
    y_axis = Axis(
        "dos",
        unit=retained[0].density_unit,
        label="DOS",
        metadata={"normalization": retained[0].normalization_basis},
    )
    series: list[Series] = []
    for trace in retained:
        density = np.array(trace.density, copy=True)
        if mirror_spin_down and all(spin == "down" for spin in trace.source_spins):
            density = -density
        series.append(
            Series(
                np.array(trace.energy.values_ev, copy=True),
                density,
                label=trace.label or trace.key,
                key=trace.key,
                x_axis=x_axis,
                y_axis=y_axis,
                metadata={
                    "trace_digest": trace.digest,
                    "source_dos_digest": trace.source_dos_digest,
                    "source_spins": tuple(trace.source_spins),
                },
            )
        )

    figure, ax = render_curves(
        Dataset(tuple(series), name="dos"),
        spec,
        preset=preset,
    )

    if fermi_position is not None:
        ax.axvline(fermi_position, linestyle="--", linewidth=1.0, label="_nolegend_")

    for trace, energy_before, density_before in zip(
        retained,
        before_energy,
        before_density,
        strict=True,
    ):
        if not np.array_equal(trace.energy.values_ev, energy_before):
            raise RuntimeError("DOS plotting mutated retained energy state")
        if not np.array_equal(trace.density, density_before):
            raise RuntimeError("DOS plotting mutated retained density state")
    return figure, ax


__all__ = ["DOSVisualizationError", "plot_dos"]
