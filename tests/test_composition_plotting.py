"""Publication plotting regressions for explicit composition summaries."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pytest

from catalysis_workbench.experimental.characterization import (
    CompositionError,
    CompositionMeasurement,
    CompositionSummaryTable,
    CompositionTable,
    plot_composition,
    summarize_composition_replicates,
)
from catalysis_workbench.experimental.characterization.composition_plotting import (
    composition_bar_data,
)
from catalysis_workbench.visualization import FigureSpec, SeriesStyle


def _m(
    key: str,
    sample: str,
    element: str,
    value: float,
    *,
    unit: str = "wt%",
    basis: str = "bulk_mass_fraction",
    replicate: str = "",
) -> CompositionMeasurement:
    return CompositionMeasurement(
        key=key,
        sample_key=sample,
        sample_label=sample.upper(),
        element=element,
        value=value,
        unit=unit,
        basis=basis,
        replicate_key=replicate,
        analyte=element,
    )


def _complete_raw() -> CompositionTable:
    return CompositionTable(
        (
            _m("a-pb", "a", "Pb", 1.0),
            _m("a-fe", "a", "Fe", 2.0),
            _m("b-pb", "b", "Pb", 1.5),
            _m("b-fe", "b", "Fe", 2.5),
        )
    )


def test_bar_data_preserves_raw_values_without_closure_normalization() -> None:
    data = CompositionTable(
        (
            _m("a-pb", "a", "Pb", 10.0),
            _m("a-fe", "a", "Fe", 20.0),
        )
    )
    bars = composition_bar_data(data)
    assert bars.categories[0].key == "a"
    assert bars.series[0].key == "element:Pb"
    assert bars.series[0].values[0] == 10.0
    assert bars.series[1].values[0] == 20.0
    assert sum(series.values[0] for series in bars.series) == 30.0
    assert bars.y_axis.metadata["normalization"] == "bulk_mass_fraction"


def test_raw_replicates_must_be_summarized_explicitly_before_plotting() -> None:
    data = CompositionTable(
        (
            _m("r1", "a", "Pb", 1.0, replicate="1"),
            _m("r2", "a", "Pb", 1.1, replicate="2"),
        )
    )
    with pytest.raises(CompositionError, match="summarize replicates"):
        composition_bar_data(data)


def test_plot_requires_complete_sample_element_matrix() -> None:
    incomplete = CompositionTable(
        (
            _m("a-pb", "a", "Pb", 1.0),
            _m("a-fe", "a", "Fe", 2.0),
            _m("b-pb", "b", "Pb", 1.5),
        )
    )
    with pytest.raises(CompositionError, match="complete sample"):
        composition_bar_data(incomplete)


def test_plot_rejects_mixed_unit_or_basis_without_hidden_conversion() -> None:
    mixed_unit = CompositionTable(
        (
            _m("a", "a", "Pb", 1.0, unit="wt%"),
            _m("b", "b", "Pb", 10.0, unit="mg/g"),
        )
    )
    with pytest.raises(CompositionError, match="basis and unit"):
        composition_bar_data(mixed_unit)

    mixed_basis = CompositionTable(
        (
            _m("a", "a", "Pb", 1.0),
            _m(
                "b",
                "b",
                "Pb",
                1.0,
                unit="mg/L",
                basis="solution_concentration",
            ),
        )
    )
    with pytest.raises(CompositionError, match="basis and unit"):
        composition_bar_data(mixed_basis)


def test_summary_sd_error_bars_are_explicit_and_n1_remains_missing() -> None:
    raw = CompositionTable(
        (
            _m("a1", "a", "Pb", 0.9, replicate="1"),
            _m("a2", "a", "Pb", 1.1, replicate="2"),
            _m("b1", "b", "Pb", 1.5, replicate="1"),
        )
    )
    summaries = summarize_composition_replicates(raw)
    assert isinstance(summaries, CompositionSummaryTable)
    bars = composition_bar_data(summaries, error="sd")
    assert bars.series[0].values.tolist() == pytest.approx([1.0, 1.5])
    assert bars.series[0].errors[0] == pytest.approx(np.sqrt(0.02))
    assert np.isnan(bars.series[0].errors[1])


def test_raw_table_rejects_sd_error_request() -> None:
    with pytest.raises(CompositionError, match="summarize replicates"):
        composition_bar_data(_complete_raw(), error="sd")


def test_plot_composition_uses_shared_grouped_bar_renderer_and_labels() -> None:
    data = _complete_raw()
    spec = FigureSpec(xlabel="Catalyst", ylabel="ICP loading", ylim=(0.0, 3.0))
    fig, ax = plot_composition(data, spec)
    try:
        assert len(ax.patches) == 4
        assert ax.get_xlabel() == "Catalyst"
        assert ax.get_ylabel() == "ICP loading"
        assert ax.get_ylim() == pytest.approx((0.0, 3.0))
        heights = [patch.get_height() for patch in ax.patches]
        assert heights == pytest.approx([1.0, 1.5, 2.0, 2.5])
    finally:
        plt.close(fig)


def test_element_series_style_is_addressed_by_stable_key() -> None:
    data = _complete_raw()
    spec = FigureSpec(
        series_styles={"element:Pb": SeriesStyle(visible=False)}
    )
    fig, ax = plot_composition(data, spec)
    try:
        assert len(ax.patches) == 2
        assert [patch.get_height() for patch in ax.patches] == pytest.approx([2.0, 2.5])
    finally:
        plt.close(fig)


def test_conflicting_sample_display_labels_fail_instead_of_guessing() -> None:
    data = CompositionTable(
        (
            CompositionMeasurement(
                key="a-pb",
                sample_key="a",
                sample_label="A one",
                element="Pb",
                analyte="Pb",
                value=1.0,
                unit="wt%",
                basis="bulk_mass_fraction",
            ),
            CompositionMeasurement(
                key="a-fe",
                sample_key="a",
                sample_label="A two",
                element="Fe",
                analyte="Fe",
                value=2.0,
                unit="wt%",
                basis="bulk_mass_fraction",
            ),
        )
    )
    with pytest.raises(CompositionError, match="conflicting display labels"):
        composition_bar_data(data)
