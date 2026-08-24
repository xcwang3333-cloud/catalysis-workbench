"""Thin publication adapter for already calculated TOF/TOFapp data."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from catalysis_workbench.core import Dataset, Series
from catalysis_workbench.visualization import (
    FigureSpec,
    ScatterError,
    render_curves,
    render_scatter,
)

from .tof import TurnoverFrequencyError

TurnoverPlotKind = Literal["scatter", "curve"]
_VALID_NAMES = {"turnover_frequency", "apparent_turnover_frequency"}
_VALID_BASES = {"active_sites", "total_metal", "bulk_inventory"}


def _series_tuple(data: Series | Dataset) -> tuple[Series, ...]:
    if isinstance(data, Series):
        return (data,)
    if isinstance(data, Dataset):
        if len(data) == 0:
            raise TurnoverFrequencyError("cannot plot an empty TOF Dataset")
        return tuple(data)
    raise TypeError("data must be a Series or Dataset")


def _validate(data: Series | Dataset) -> None:
    for item in _series_tuple(data):
        if item.y_axis.name.casefold() not in _VALID_NAMES:
            raise TurnoverFrequencyError(
                "TOF plotting requires turnover_frequency or "
                "apparent_turnover_frequency y-axis semantics"
            )
        raw_basis = item.y_axis.metadata.get("normalization")
        basis = raw_basis.strip().casefold() if isinstance(raw_basis, str) else None
        if basis not in _VALID_BASES:
            raise TurnoverFrequencyError(
                "TOF y-axis normalization metadata must identify active_sites, "
                "total_metal, or bulk_inventory"
            )
        expected_name = (
            "turnover_frequency" if basis == "active_sites" else "apparent_turnover_frequency"
        )
        if item.y_axis.name.casefold() != expected_name:
            raise TurnoverFrequencyError(
                "TOF y-axis name is inconsistent with its inventory normalization basis"
            )


def plot_turnover_frequency(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    kind: TurnoverPlotKind = "scatter",
    errors: ScatterError | Mapping[str, ScatterError] | None = None,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Render already calculated TOF/TOFapp without scientific processing."""
    _validate(data)
    if kind == "scatter":
        return render_scatter(data, spec, errors=errors, preset=preset)
    if kind == "curve":
        if errors is not None:
            raise TurnoverFrequencyError(
                "explicit errors are supported only with kind='scatter'"
            )
        return render_curves(data, spec, preset=preset)
    raise TurnoverFrequencyError("kind must be 'scatter' or 'curve'")


__all__ = ["TurnoverPlotKind", "plot_turnover_frequency"]
