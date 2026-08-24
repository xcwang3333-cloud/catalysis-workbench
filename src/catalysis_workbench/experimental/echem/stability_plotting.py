"""Thin publication adapters for stability curves and calculated summaries."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.visualization import (
    BarCategory,
    BarData,
    BarSeries,
    FigureSpec,
    render_bars,
    render_curves,
)

from .stability import (
    StabilityError,
    StabilityResult,
    StabilityResultCollection,
    validate_stability_series,
)

StabilitySummaryMetric = Literal[
    "retention_percent",
    "relative_change_percent",
    "absolute_change",
    "drift_slope_per_s",
    "baseline_mean",
    "final_mean",
]


def _series_tuple(data: Series | Dataset) -> tuple[Series, ...]:
    if isinstance(data, Series):
        return (data,)
    if isinstance(data, Dataset):
        if len(data) == 0:
            raise StabilityError("cannot plot an empty stability Dataset")
        return tuple(data)
    raise TypeError("data must be a Series or Dataset")


def plot_stability(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Render validated stability traces without calculating stability metrics."""
    for series in _series_tuple(data):
        validate_stability_series(series)
    return render_curves(data, spec, preset=preset)


def _result_tuple(
    results: StabilityResultCollection | Sequence[StabilityResult],
) -> tuple[StabilityResult, ...]:
    if isinstance(results, StabilityResultCollection):
        resolved = tuple(result for _, result in results.items)
    elif isinstance(results, Sequence) and not isinstance(results, (str, bytes)):
        resolved = tuple(results)
    else:
        raise TypeError(
            "results must be a StabilityResultCollection or sequence of StabilityResult"
        )
    if not resolved:
        raise StabilityError("stability summary requires at least one result")
    if not all(isinstance(result, StabilityResult) for result in resolved):
        raise TypeError("stability summary requires only StabilityResult values")
    keys = tuple(result.source.key for result in resolved)
    if any(not key for key in keys):
        raise StabilityError("stability summary results require stable source keys")
    if len(keys) != len(set(keys)):
        raise StabilityError("stability summary source keys must be unique")
    return resolved


def _summary_metric(value: object) -> StabilitySummaryMetric:
    supported = {
        "retention_percent",
        "relative_change_percent",
        "absolute_change",
        "drift_slope_per_s",
        "baseline_mean",
        "final_mean",
    }
    if isinstance(value, str) and value in supported:
        return value  # type: ignore[return-value]
    raise StabilityError(
        "metric must be retention_percent, relative_change_percent, absolute_change, "
        "drift_slope_per_s, baseline_mean, or final_mean"
    )


def _validate_summary_compatibility(
    results: tuple[StabilityResult, ...],
    metric: StabilitySummaryMetric,
) -> None:
    first = results[0]
    for result in results[1:]:
        if result.y_kind != first.y_kind:
            raise StabilityError("stability summary requires matching y semantics")
        if result.reference != first.reference:
            raise StabilityError("stability summary requires matching reference metadata")
        if result.normalization != first.normalization:
            raise StabilityError(
                "stability summary requires matching normalization metadata"
            )
        if metric not in {"retention_percent", "relative_change_percent"}:
            if result.y_unit != first.y_unit:
                raise StabilityError(
                    "stability summary requires matching y units for this metric"
                )
        else:
            if result.config.retention_mode != first.config.retention_mode:
                raise StabilityError(
                    "retention summaries require matching signed/magnitude modes"
                )


def _metric_unit(result: StabilityResult, metric: StabilitySummaryMetric) -> str:
    if metric in {"retention_percent", "relative_change_percent"}:
        return "%"
    if metric == "drift_slope_per_s":
        return result.drift_unit
    return result.y_unit


def _metric_label(metric: StabilitySummaryMetric) -> str:
    return {
        "retention_percent": "Retention",
        "relative_change_percent": "Relative change",
        "absolute_change": "Absolute change",
        "drift_slope_per_s": "Linear drift",
        "baseline_mean": "Baseline mean",
        "final_mean": "Final mean",
    }[metric]


def plot_stability_summary(
    results: StabilityResultCollection | Sequence[StabilityResult],
    spec: FigureSpec | None = None,
    *,
    metric: StabilitySummaryMetric = "retention_percent",
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Render one already-calculated scalar stability metric as categorical bars."""
    resolved = _result_tuple(results)
    selected = _summary_metric(metric)
    _validate_summary_compatibility(resolved, selected)

    categories = tuple(
        BarCategory(
            key=result.source.key,
            label=result.source.label or result.source.key,
        )
        for result in resolved
    )
    values = tuple(float(getattr(result, selected)) for result in resolved)
    data = BarData(
        categories=categories,
        series=(BarSeries(key=selected, values=values, label=_metric_label(selected)),),
        x_axis=Axis("sample", label="Sample"),
        y_axis=Axis(
            selected,
            unit=_metric_unit(resolved[0], selected),
            label=_metric_label(selected),
            metadata={
                "reference": resolved[0].reference,
                "normalization": resolved[0].normalization,
            },
        ),
    )
    return render_bars(data, spec, preset=preset)


__all__ = ["StabilitySummaryMetric", "plot_stability", "plot_stability_summary"]
