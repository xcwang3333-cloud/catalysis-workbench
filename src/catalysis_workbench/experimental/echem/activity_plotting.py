"""Thin publication adapter for already normalized electrochemical activity."""

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

from .activity import ActivityNormalizationError

ActivityPlotKind = Literal["scatter", "curve"]
_ACTIVITY_BASES = {"catalyst_mass", "metal_mass", "ecsa"}


def _series_tuple(data: Series | Dataset) -> tuple[Series, ...]:
    if isinstance(data, Series):
        return (data,)
    if isinstance(data, Dataset):
        if len(data) == 0:
            raise ActivityNormalizationError("cannot plot an empty activity Dataset")
        return tuple(data)
    raise TypeError("data must be a Series or Dataset")


def _validate_activity_series(data: Series | Dataset) -> None:
    for item in _series_tuple(data):
        if item.y_axis.name.casefold() != "activity":
            raise ActivityNormalizationError(
                "activity plotting requires y_axis.name='activity'"
            )
        raw_normalization = item.y_axis.metadata.get("normalization")
        normalization = (
            raw_normalization.strip().casefold()
            if isinstance(raw_normalization, str)
            else None
        )
        if normalization not in _ACTIVITY_BASES:
            raise ActivityNormalizationError(
                "activity y-axis normalization metadata must identify "
                "catalyst_mass, metal_mass, or ecsa"
            )


def plot_activity(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    kind: ActivityPlotKind = "scatter",
    errors: ScatterError | Mapping[str, ScatterError] | None = None,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Render already normalized activity without further scientific processing."""
    _validate_activity_series(data)

    if kind == "scatter":
        return render_scatter(data, spec, errors=errors, preset=preset)
    if kind == "curve":
        if errors is not None:
            raise ActivityNormalizationError(
                "explicit errors are supported only with kind='scatter'"
            )
        return render_curves(data, spec, preset=preset)
    raise ActivityNormalizationError("kind must be 'scatter' or 'curve'")


__all__ = ["ActivityPlotKind", "plot_activity"]
