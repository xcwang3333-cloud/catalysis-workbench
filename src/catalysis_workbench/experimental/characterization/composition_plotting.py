"""Publication plotting adapter for explicit ICP/composition summaries."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import numpy as np

from catalysis_workbench.core import Axis
from catalysis_workbench.visualization import (
    BarCategory,
    BarData,
    BarSeries,
    FigureSpec,
    render_bars,
)

from .composition import (
    CompositionError,
    CompositionSummary,
    CompositionSummaryTable,
    CompositionTable,
)

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

CompositionErrorBar = Literal["none", "sd"]


def _sample_order(
    data: CompositionTable | CompositionSummaryTable,
) -> tuple[str, ...]:
    if isinstance(data, CompositionTable):
        return data.sample_keys
    return data.sample_keys


def _element_order(
    data: CompositionTable | CompositionSummaryTable,
) -> tuple[str, ...]:
    if isinstance(data, CompositionTable):
        return data.elements
    return data.elements


def _validate_basis_unit(
    data: CompositionTable | CompositionSummaryTable,
) -> tuple[str, str]:
    items = tuple(data)
    bases = {item.basis for item in items}
    units = {item.unit for item in items}
    if len(bases) != 1 or len(units) != 1:
        raise CompositionError(
            "composition plotting requires one explicit compatible basis and unit; "
            "convert or split data before plotting"
        )
    return next(iter(bases)), next(iter(units))


def _sample_labels(
    data: CompositionTable | CompositionSummaryTable,
    sample_keys: tuple[str, ...],
) -> dict[str, str]:
    labels: dict[str, set[str]] = {key: set() for key in sample_keys}
    for item in data:
        if item.sample_label:
            labels[item.sample_key].add(item.sample_label)
    resolved: dict[str, str] = {}
    for sample_key in sample_keys:
        values = labels[sample_key]
        if len(values) > 1:
            raise CompositionError(
                f"sample_key {sample_key!r} has conflicting display labels"
            )
        resolved[sample_key] = next(iter(values), sample_key)
    return resolved


def _raw_lookup(
    table: CompositionTable,
) -> dict[tuple[str, str], float]:
    lookup: dict[tuple[str, str], float] = {}
    for item in table:
        pair = (item.sample_key, item.element)
        if pair in lookup:
            raise CompositionError(
                "raw composition plotting requires exactly one measurement per "
                "sample_key/element pair; summarize replicates explicitly first"
            )
        lookup[pair] = item.value
    return lookup


def _summary_lookup(
    table: CompositionSummaryTable,
) -> dict[tuple[str, str], CompositionSummary]:
    return {(item.sample_key, item.element): item for item in table}


def _require_complete_matrix(
    sample_keys: tuple[str, ...],
    elements: tuple[str, ...],
    present: set[tuple[str, str]],
) -> None:
    missing = [
        pair
        for pair in (
            (sample_key, element)
            for sample_key in sample_keys
            for element in elements
        )
        if pair not in present
    ]
    if missing:
        raise CompositionError(
            "composition plotting requires a complete sample×element matrix; "
            f"missing combinations: {missing!r}"
        )


def _y_axis(basis: str, unit: str) -> Axis:
    if basis == "bulk_mass_fraction":
        label = "Elemental composition"
    elif basis == "solution_concentration":
        label = "Solution concentration"
    else:  # defensive: scientific objects validate the basis earlier
        raise CompositionError(f"unsupported composition basis {basis!r}")
    return Axis(
        "composition",
        unit=unit,
        label=label,
        metadata={"normalization": basis},
    )


def composition_bar_data(
    data: CompositionTable | CompositionSummaryTable,
    *,
    error: CompositionErrorBar = "none",
) -> BarData:
    """Build shared-renderer grouped bars without hidden aggregation or closure."""
    if not isinstance(data, (CompositionTable, CompositionSummaryTable)):
        raise TypeError("data must be a CompositionTable or CompositionSummaryTable")
    if error not in {"none", "sd"}:
        raise CompositionError("error must be 'none' or 'sd'")
    if isinstance(data, CompositionTable) and error != "none":
        raise CompositionError(
            "raw CompositionTable has no aggregate uncertainty; summarize replicates "
            "explicitly before requesting SD error bars"
        )

    basis, unit = _validate_basis_unit(data)
    sample_keys = _sample_order(data)
    elements = _element_order(data)
    labels = _sample_labels(data, sample_keys)
    categories = tuple(
        BarCategory(key=sample_key, label=labels[sample_key])
        for sample_key in sample_keys
    )

    bar_series: list[BarSeries] = []
    if isinstance(data, CompositionTable):
        lookup = _raw_lookup(data)
        _require_complete_matrix(sample_keys, elements, set(lookup))
        for element in elements:
            values = [lookup[(sample_key, element)] for sample_key in sample_keys]
            bar_series.append(
                BarSeries(
                    key=f"element:{element}",
                    label=element,
                    values=values,
                )
            )
    else:
        lookup = _summary_lookup(data)
        _require_complete_matrix(sample_keys, elements, set(lookup))
        for element in elements:
            summaries = [lookup[(sample_key, element)] for sample_key in sample_keys]
            values = [item.mean for item in summaries]
            errors = None
            if error == "sd":
                errors = [
                    np.nan if item.standard_deviation is None else item.standard_deviation
                    for item in summaries
                ]
            bar_series.append(
                BarSeries(
                    key=f"element:{element}",
                    label=element,
                    values=values,
                    errors=errors,
                )
            )

    return BarData(
        categories=categories,
        series=tuple(bar_series),
        x_axis=Axis("sample", label="Sample"),
        y_axis=_y_axis(basis, unit),
    )


def plot_composition(
    data: CompositionTable | CompositionSummaryTable,
    spec: FigureSpec | None = None,
    *,
    error: CompositionErrorBar = "none",
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Render composition bars through the shared deterministic bar renderer."""
    bar_data = composition_bar_data(data, error=error)
    return render_bars(bar_data, spec, preset=preset)
