"""Passive publication rendering for retained DFT relative-energy results."""

from __future__ import annotations

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from catalysis_workbench.computation import RelativeEnergyResult
from catalysis_workbench.core import Axis

from .bars import BarCategory, BarData, BarSeries, render_bars
from .specs import FigureSpec


def plot_relative_energies(
    result: RelativeEnergyResult,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Render retained relative energies without recomputing energetic arithmetic."""
    if not isinstance(result, RelativeEnergyResult):
        raise TypeError("result must be a RelativeEnergyResult")
    before = np.array(result.delta_energy_ev, copy=True)
    data = BarData(
        categories=tuple(
            BarCategory(key, label)
            for key, label in zip(
                result.entry_keys,
                result.entry_labels,
                strict=True,
            )
        ),
        series=(
            BarSeries(
                "delta_energy",
                result.delta_energy_ev,
                label="Relative energy",
            ),
        ),
        x_axis=Axis("state", label="State"),
        y_axis=Axis("relative_energy", unit="eV", label="Relative energy"),
    )
    figure, ax = render_bars(data, spec, preset=preset)
    if not np.array_equal(before, result.delta_energy_ev):
        raise RuntimeError("relative-energy plotting mutated retained energetic state")
    return figure, ax


__all__ = ["plot_relative_energies"]
