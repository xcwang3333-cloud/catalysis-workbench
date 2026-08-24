"""Thin publication adapter for product partial current density."""

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

from .partial_current import PartialCurrentDensityError

PartialCurrentPlotKind = Literal["scatter", "curve"]


def _series_tuple(data: Series | Dataset) -> tuple[Series, ...]:
    if isinstance(data, Series):
        return (data,)
    if isinstance(data, Dataset):
        if len(data) == 0:
            raise PartialCurrentDensityError(
                "cannot plot an empty partial-current Dataset"
            )
        return tuple(data)
    raise TypeError("data must be a Series or Dataset")


def _validate_partial_current_series(data: Series | Dataset) -> None:
    for item in _series_tuple(data):
        if item.y_axis.name.casefold() != "partial_current_density":
            raise PartialCurrentDensityError(
                "partial-current plotting requires "
                "y_axis.name='partial_current_density'"
            )
        if item.y_axis.unit is None:
            raise PartialCurrentDensityError(
                "partial-current plotting requires an explicit current-density unit"
            )


def plot_partial_current_density(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    kind: PartialCurrentPlotKind = "scatter",
    errors: ScatterError | Mapping[str, ScatterError] | None = None,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Render already calculated partial-current data using shared renderers."""
    _validate_partial_current_series(data)

    if kind == "scatter":
        return render_scatter(data, spec, errors=errors, preset=preset)
    if kind == "curve":
        if errors is not None:
            raise PartialCurrentDensityError(
                "explicit errors are supported only with kind='scatter'"
            )
        return render_curves(data, spec, preset=preset)
    raise PartialCurrentDensityError("kind must be 'scatter' or 'curve'")


__all__ = ["PartialCurrentPlotKind", "plot_partial_current_density"]
