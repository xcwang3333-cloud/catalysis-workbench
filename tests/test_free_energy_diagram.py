from __future__ import annotations

import numpy as np
import pytest

from catalysis_workbench.computation import (
    CHEState,
    DFTEnergyEntry,
    DFTEnergyLedger,
    FreeEnergyDiagramError,
    FreeEnergyDiagramSeries,
    FreeEnergyDiagramState,
    FreeEnergyRecipe,
    ThermodynamicEntry,
    build_free_energy_diagram_series,
    diagram_context_from_che,
    diagram_state_from_free_energy,
    evaluate_che_proton_electron,
    evaluate_free_energy,
    free_energy_diagram_frame,
    validate_free_energy_diagram_series_compatibility,
)
from catalysis_workbench.visualization import (
    CategoryStyle,
    FigureSpec,
    SeriesStyle,
    VisualizationError,
    plot_free_energy_diagram,
)


def _evaluation(
    key: str,
    energy_ev: float,
    *,
    label: str | None = None,
    basis: str = "per reaction cell",
):
    ledger = DFTEnergyLedger(
        entries=(
            DFTEnergyEntry(
                key=key,
                energy_ev=energy_ev,
                normalization_basis=basis,
                source_id=f"dft-{key}",
            ),
        ),
        source_id=f"ledger-{key}",
    )
    return evaluate_free_energy(
        ledger,
        ThermodynamicEntry(key=key, dft_entry_key=key, label=label),
        FreeEnergyRecipe(key="electronic-only"),
    )


def _states(*, basis: str = "per reaction cell") -> tuple[FreeEnergyDiagramState, ...]:
    return tuple(
        diagram_state_from_free_energy(evaluation, label=label)
        for evaluation, label in (
            (_evaluation("initial", -10.0, basis=basis), "Initial"),
            (_evaluation("intermediate", -9.0, basis=basis), "Intermediate"),
            (_evaluation("final", -9.5, basis=basis), "Final"),
        )
    )


def _absolute_series(
    *,
    key: str = "path-a",
    states: tuple[FreeEnergyDiagramState, ...] | None = None,
    comparison_basis: str = "same reaction path",
    context=None,
    label: str | None = "Path A",
) -> FreeEnergyDiagramSeries:
    return build_free_energy_diagram_series(
        _states() if states is None else states,
        key=key,
        energy_mode="absolute",
        comparison_basis=comparison_basis,
        context=context,
        label=label,
    )


def _relative_series(
    *,
    key: str = "path-a",
    reference_state_key: str = "initial",
    states: tuple[FreeEnergyDiagramState, ...] | None = None,
    comparison_basis: str = "same reaction path",
    context=None,
) -> FreeEnergyDiagramSeries:
    return build_free_energy_diagram_series(
        _states() if states is None else states,
        key=key,
        energy_mode="reference_relative",
        comparison_basis=comparison_basis,
        reference_state_key=reference_state_key,
        context=context,
    )


def _che_context(*, potential_v: float = 0.2):
    h2 = _evaluation("h2", -6.0, basis="per H2 molecule")
    che = evaluate_che_proton_electron(
        h2,
        CHEState(
            temperature_k=298.15,
            ph=7.0,
            potential_v=potential_v,
            potential_reference="RHE",
        ),
    )
    return che, diagram_context_from_che(che)


def test_absolute_diagram_is_hand_verifiable_and_ordered() -> None:
    result = _absolute_series()
    assert result.state_keys == ("initial", "intermediate", "final")
    assert result.state_labels == ("Initial", "Intermediate", "Final")
    np.testing.assert_allclose(result.plotted_energy_ev, [-10.0, -9.0, -9.5])
    assert result.plotted_energy_ev.flags.writeable is False
    assert result.reference_state_key is None
    assert result.normalization_basis == "per reaction cell"


def test_reference_relative_requires_explicit_reference_and_uses_g_minus_gref() -> None:
    result = _relative_series(reference_state_key="intermediate")
    np.testing.assert_allclose(result.plotted_energy_ev, [-1.0, 0.0, -0.5])
    assert result.reference_state_key == "intermediate"

    with pytest.raises(FreeEnergyDiagramError, match="explicit reference"):
        build_free_energy_diagram_series(
            _states(),
            key="bad",
            energy_mode="reference_relative",
            comparison_basis="same reaction path",
        )
    with pytest.raises(FreeEnergyDiagramError, match="identify one retained"):
        _relative_series(reference_state_key="missing")


def test_duplicate_state_keys_and_mixed_basis_fail_closed() -> None:
    states = _states()
    duplicate = FreeEnergyDiagramState(
        key=states[0].key,
        absolute_energy_ev=states[1].absolute_energy_ev,
        source_key="other",
        source_type="manual",
        source_digest="source-other",
        normalization_basis=states[0].normalization_basis,
    )
    with pytest.raises(FreeEnergyDiagramError, match="unique"):
        _absolute_series(states=(states[0], duplicate))

    mixed = (
        states[0],
        FreeEnergyDiagramState(
            key="other",
            absolute_energy_ev=-8.0,
            source_key="other",
            source_type="manual",
            source_digest="source-other",
            normalization_basis="per molecule",
        ),
    )
    with pytest.raises(FreeEnergyDiagramError, match="matching normalization_basis"):
        _absolute_series(states=mixed)


def test_direct_series_reconstruction_rejects_inconsistent_plotted_values() -> None:
    source = _absolute_series()
    with pytest.raises(FreeEnergyDiagramError, match="contradicts"):
        FreeEnergyDiagramSeries(
            key=source.key,
            states=source.states,
            energy_mode=source.energy_mode,
            plotted_energy_ev=(0.0, 0.0, 0.0),
            normalization_basis=source.normalization_basis,
            comparison_basis=source.comparison_basis,
        )


def test_order_is_scientific_state_but_display_labels_are_not() -> None:
    original_states = _states()
    relabeled_states = tuple(
        FreeEnergyDiagramState(
            key=state.key,
            absolute_energy_ev=state.absolute_energy_ev,
            source_key=state.source_key,
            source_type=state.source_type,
            source_digest=state.source_digest,
            normalization_basis=state.normalization_basis,
            label=f"display-{index}",
        )
        for index, state in enumerate(original_states)
    )
    assert [a.digest for a in original_states] == [b.digest for b in relabeled_states]

    original = _absolute_series(states=original_states, label="Original")
    relabeled = _absolute_series(states=relabeled_states, label="Relabeled")
    assert original.digest == relabeled.digest
    assert original != relabeled

    reordered = _absolute_series(
        states=(original_states[1], original_states[0], original_states[2]),
    )
    assert reordered.state_keys != original.state_keys
    assert reordered.digest != original.digest


def test_free_energy_adapter_preserves_exact_reviewed_value_and_provenance() -> None:
    evaluation = _evaluation("adsorbed", -3.25, label="Adsorbed")
    state = diagram_state_from_free_energy(evaluation)
    assert state.key == evaluation.key
    assert state.label == evaluation.label
    assert state.absolute_energy_ev == pytest.approx(evaluation.free_energy_ev)
    assert state.source_key == evaluation.key
    assert state.source_digest == evaluation.digest
    assert state.normalization_basis == evaluation.normalization_basis


def test_che_context_is_copied_exactly_without_recalculation() -> None:
    che, context = _che_context()
    assert context.che_source_digest == che.digest
    assert context.temperature_k == pytest.approx(che.temperature_k)
    assert context.ph == pytest.approx(che.ph)
    assert context.input_potential_v == pytest.approx(che.input_potential_v)
    assert context.input_potential_reference == che.input_potential_reference
    assert context.potential_she_v == pytest.approx(che.potential_she_v)


def test_reporting_frame_is_detached_and_retains_context_provenance() -> None:
    che, context = _che_context()
    result = _absolute_series(context=context)
    frame = free_energy_diagram_frame(result)
    assert list(frame["state_key"]) == ["initial", "intermediate", "final"]
    assert list(frame["absolute_energy_ev"]) == pytest.approx([-10.0, -9.0, -9.5])
    assert frame.loc[0, "diagram_context_digest"] == context.digest
    assert frame.loc[0, "che_source_digest"] == che.digest
    frame.loc[0, "plotted_energy_ev"] = 999.0
    assert result.plotted_energy_ev[0] == pytest.approx(-10.0)


def test_multi_series_compatibility_accepts_only_explicitly_matching_semantics() -> None:
    first = _absolute_series(key="a")
    second = _absolute_series(key="b")
    assert validate_free_energy_diagram_series_compatibility((first, second)) == (
        first,
        second,
    )

    reordered_states = (_states()[1], _states()[0], _states()[2])
    with pytest.raises(FreeEnergyDiagramError, match="ordered pathway-state keys"):
        validate_free_energy_diagram_series_compatibility(
            (first, _absolute_series(key="b", states=reordered_states))
        )
    with pytest.raises(FreeEnergyDiagramError, match="matching energy_mode"):
        validate_free_energy_diagram_series_compatibility(
            (first, _relative_series(key="b"))
        )
    with pytest.raises(FreeEnergyDiagramError, match="matching comparison_basis"):
        validate_free_energy_diagram_series_compatibility(
            (first, _absolute_series(key="b", comparison_basis="other basis"))
        )

    other_basis = _states(basis="per molecule")
    with pytest.raises(FreeEnergyDiagramError, match="matching normalization_basis"):
        validate_free_energy_diagram_series_compatibility(
            (first, _absolute_series(key="b", states=other_basis))
        )


def test_context_and_reference_mismatches_fail_closed() -> None:
    _, context_a = _che_context(potential_v=0.2)
    _, context_b = _che_context(potential_v=0.3)
    with pytest.raises(FreeEnergyDiagramError, match="electrochemical context"):
        validate_free_energy_diagram_series_compatibility(
            (
                _absolute_series(key="a", context=context_a),
                _absolute_series(key="b", context=context_b),
            )
        )
    with pytest.raises(FreeEnergyDiagramError, match="electrochemical context"):
        validate_free_energy_diagram_series_compatibility(
            (
                _absolute_series(key="a", context=context_a),
                _absolute_series(key="b", context=None),
            )
        )
    with pytest.raises(FreeEnergyDiagramError, match="reference_state_key"):
        validate_free_energy_diagram_series_compatibility(
            (
                _relative_series(key="a", reference_state_key="initial"),
                _relative_series(key="b", reference_state_key="intermediate"),
            )
        )


def test_passive_renderer_uses_retained_values_and_straight_connectors() -> None:
    result = _relative_series(reference_state_key="initial")
    before = np.array(result.plotted_energy_ev, copy=True)
    figure, ax = plot_free_energy_diagram(result)

    assert len(ax.lines) == 5
    np.testing.assert_allclose(ax.lines[0].get_ydata(), [0.0, 0.0])
    np.testing.assert_allclose(ax.lines[1].get_ydata(), [0.0, 1.0])
    np.testing.assert_allclose(ax.lines[2].get_ydata(), [1.0, 1.0])
    np.testing.assert_allclose(ax.lines[3].get_ydata(), [1.0, 0.5])
    np.testing.assert_allclose(ax.lines[4].get_ydata(), [0.5, 0.5])
    assert [tick.get_text() for tick in ax.get_xticklabels()] == [
        "Initial",
        "Intermediate",
        "Final",
    ]
    np.testing.assert_array_equal(result.plotted_energy_ev, before)
    figure.canvas.draw()


def test_renderer_uses_retained_context_as_presentation_only() -> None:
    _, context = _che_context(potential_v=0.2)
    result = _absolute_series(context=context)
    figure, ax = plot_free_energy_diagram(result)
    assert any("0.2 V vs RHE" in text.get_text() for text in ax.texts)
    assert any("pH = 7" in text.get_text() for text in ax.texts)
    figure.canvas.draw()


def test_renderer_style_controls_cannot_hide_pathway_state_or_use_log_scales() -> None:
    result = _absolute_series()
    with pytest.raises(VisualizationError, match="cannot hide"):
        plot_free_energy_diagram(
            result,
            FigureSpec(category_styles={"intermediate": CategoryStyle(visible=False)}),
        )
    with pytest.raises(VisualizationError, match="linear x and y"):
        plot_free_energy_diagram(result, FigureSpec(yscale="log"))
    with pytest.raises(VisualizationError, match="all free-energy diagram series"):
        plot_free_energy_diagram(
            result,
            FigureSpec(series_styles={result.key: SeriesStyle(visible=False)}),
        )


def test_block8_public_contract_contains_no_barrier_or_transition_state_api() -> None:
    from catalysis_workbench.computation import free_energy_diagram as module

    names = tuple(name.lower() for name in module.__all__)
    assert not any("barrier" in name or "transition" in name for name in names)
