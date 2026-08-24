"""Thin publication adapter for condition-resolved Faradaic-efficiency Series."""

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

from .fe import FaradaicEfficiencyError

FaradaicEfficiencyPlotKind = Literal["scatter", "curve"]


def _series_tuple(data: Series | Dataset) -> tuple[Series, ...]:
    if isinstance(data, Series):
        return (data,)
    if isinstance(data, Dataset):
        if len(data) == 0:
            raise FaradaicEfficiencyError("cannot plot an empty FE Dataset")
        return tuple(data)
    raise TypeError("data must be a Series or Dataset")


def _validate_fe_series(data: Series | Dataset) -> None:
    series = _series_tuple(data)
    for item in series:
        if item.y_axis.name.casefold() != "faradaic_efficiency":
            raise FaradaicEfficiencyError(
                "FE plotting requires y_axis.name='faradaic_efficiency'"
            )
        if item.y_axis.unit not in {"fraction", "%"}:
            raise FaradaicEfficiencyError(
                "FE plotting requires y-axis unit 'fraction' or '%'"
            )


def plot_faradaic_efficiency(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    kind: FaradaicEfficiencyPlotKind = "scatter",
    errors: ScatterError | Mapping[str, ScatterError] | None = None,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Render already calculated FE data through the shared publication renderer."""
    _validate_fe_series(data)
    if kind == "scatter":
        return render_scatter(data, spec, errors=errors, preset=preset)
    if kind == "curve":
        if errors is not None:
            raise FaradaicEfficiencyError(
                "explicit errors are supported only with kind='scatter'"
            )
        return render_curves(data, spec, preset=preset)
    raise FaradaicEfficiencyError("kind must be 'scatter' or 'curve'")
