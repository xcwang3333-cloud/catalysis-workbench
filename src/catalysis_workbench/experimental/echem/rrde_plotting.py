"""Thin publication adapter for already-calculated RRDE metrics."""

from __future__ import annotations

from collections.abc import Sequence

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from catalysis_workbench.core import Dataset
from catalysis_workbench.visualization import FigureSpec, render_curves

from .rrde import RRDEError, RRDEMetric, RRDEResult, rrde_result_series


def _result_tuple(
    results: RRDEResult | Sequence[RRDEResult],
) -> tuple[RRDEResult, ...]:
    if isinstance(results, RRDEResult):
        return (results,)
    if isinstance(results, (str, bytes)) or not isinstance(results, Sequence):
        raise TypeError("results must be an RRDEResult or sequence of RRDEResult")
    normalized = tuple(results)
    if not normalized:
        raise RRDEError("cannot plot an empty RRDE result sequence")
    if not all(isinstance(item, RRDEResult) for item in normalized):
        raise TypeError("results must contain only RRDEResult instances")
    keys = tuple(
        (item.disk_source.key, item.ring_source.key)
        for item in normalized
    )
    if len(keys) != len(set(keys)):
        raise RRDEError("multi-result RRDE plotting requires unique disk/ring source pairs")
    return normalized


def plot_rrde_metric(
    results: RRDEResult | Sequence[RRDEResult],
    spec: FigureSpec | None = None,
    *,
    metric: RRDEMetric = "electron_number",
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Render one stored RRDE metric without recalculation or realignment."""
    normalized = _result_tuple(results)
    series = tuple(rrde_result_series(result, metric) for result in normalized)
    data = series[0] if len(series) == 1 else Dataset(series)
    return render_curves(data, spec, preset=preset)


__all__ = ["plot_rrde_metric"]
