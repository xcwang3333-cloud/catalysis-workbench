from __future__ import annotations

from math import log

import numpy as np
import pytest

from catalysis_workbench.computation import (
    BOLTZMANN_EV_PER_K,
    CHEProtonElectronResult,
    CHEState,
    DFTEnergyEntry,
    DFTEnergyLedger,
    FreeEnergyCorrection,
    FreeEnergyEvaluation,
    FreeEnergyRecipe,
    ReactionFreeEnergyTerm,
    ThermodynamicEntry,
    ThermodynamicsError,
    che_reaction_term,
    che_result_frame,
    evaluate_che_proton_electron,
    evaluate_free_energy,
    free_energy_contributions_frame,
    reaction_free_energy,
    reaction_free_energy_frame,
    thermodynamic_entry_frame,
    thermodynamic_reaction_term,
)


def _ledger(*, basis: str | None = "per state") -> DFTEnergyLedger:
    return DFTEnergyLedger(
        entries=(
            DFTEnergyEntry(
                key="state",
                energy_ev=-10.0,
                normalization_basis=basis,
                source_id="vasp-state",
            ),
            DFTEnergyEntry(
                key="product",
                energy_ev=-9.0,
                normalization_basis=basis,
                source_id="vasp-product",
            ),
        ),
        source_id="fixture-ledger",
    )


def _full_entry(*, label: str | None = "display state") -> ThermodynamicEntry:
    return ThermodynamicEntry(
        key="state-g",
        dft_entry_key="state",
        zpe_ev=0.5,
        thermal_enthalpy_correction_ev=0.2,
        entropy_ev_per_k=0.001,
        temperature_k=300.0,
        corrections=(
            FreeEnergyCorrection(
                key="solvation",
                correction_type="solvation",
                value_ev=-0.3,
                source_id="caller-solvation",
            ),
            FreeEnergyCorrection(
                key="field",
                correction_type="field",
                value_ev=0.1,
                source_id="caller-field",
            ),
        ),
        label=label,
    )


def _full_recipe(*, label: str | None = "display recipe") -> FreeEnergyRecipe:
    return FreeEnergyRecipe(
        key="full",
        include_zpe=True,
        include_thermal_enthalpy=True,
        include_entropy=True,
        correction_keys=("solvation", "field"),
        label=label,
    )


def _h2_evaluation(
    *,
    energy_ev: float = -6.0,
    temperature_k: float | None = None,
) -> FreeEnergyEvaluation:
    ledger = DFTEnergyLedger(
        entries=(
            DFTEnergyEntry(
                key="h2",
                energy_ev=energy_ev,
                normalization_basis="per H2 molecule",
                source_id="h2-dft",
            ),
        ),
        source_id="h2-ledger",
    )
    if temperature_k is None:
        entry = ThermodynamicEntry(key="h2-g", dft_entry_key="h2")
        recipe = FreeEnergyRecipe(key="electronic-only")
    else:
        entry = ThermodynamicEntry(
            key="h2-g",
            dft_entry_key="h2",
            entropy_ev_per_k=0.001,
            temperature_k=temperature_k,
        )
        recipe = FreeEnergyRecipe(key="with-entropy", include_entropy=True)
    return evaluate_free_energy(ledger, entry, recipe)


def test_free_energy_evaluation_is_hand_verifiable() -> None:
    result = evaluate_free_energy(_ledger(), _full_entry(), _full_recipe())

    expected = -10.0 + 0.5 + 0.2 - 300.0 * 0.001 - 0.3 + 0.1
    assert result.free_energy_ev == pytest.approx(expected)
    assert [item.contribution_type for item in result.contributions] == [
        "electronic_dft",
        "zpe",
        "thermal_enthalpy",
        "entropy",
        "additional_correction",
        "additional_correction",
    ]
    assert [item.key for item in result.contributions[-2:]] == [
        "correction:field",
        "correction:solvation",
    ]
    assert result.contributions[3].value_ev == pytest.approx(-0.3)
    assert result.normalization_basis == "per state"
    assert result.ledger_digest == _ledger().digest


def test_not_supplied_is_distinct_from_zero_and_requested_missing_fails() -> None:
    entry = ThermodynamicEntry(key="state-g", dft_entry_key="state")
    frame = thermodynamic_entry_frame(entry)
    assert frame.loc[0, "zpe_supplied"] == np.bool_(False)
    assert frame.loc[0, "thermal_enthalpy_supplied"] == np.bool_(False)
    assert frame.loc[0, "entropy_supplied"] == np.bool_(False)
    assert frame.loc[0, "zpe_ev"] is None

    zero = ThermodynamicEntry(key="zero", dft_entry_key="state", zpe_ev=0.0)
    assert thermodynamic_entry_frame(zero).loc[0, "zpe_supplied"] == np.bool_(True)

    with pytest.raises(ThermodynamicsError, match="ZPE"):
        evaluate_free_energy(
            _ledger(),
            entry,
            FreeEnergyRecipe(key="needs-zpe", include_zpe=True),
        )


def test_temperature_is_required_for_temperature_dependent_input() -> None:
    with pytest.raises(ThermodynamicsError, match="temperature_k"):
        ThermodynamicEntry(
            key="bad",
            dft_entry_key="state",
            entropy_ev_per_k=0.001,
        )
    with pytest.raises(ThermodynamicsError, match="temperature_k"):
        ThermodynamicEntry(
            key="bad",
            dft_entry_key="state",
            thermal_enthalpy_correction_ev=0.1,
        )
    with pytest.raises(ThermodynamicsError, match="greater than zero"):
        ThermodynamicEntry(
            key="bad",
            dft_entry_key="state",
            entropy_ev_per_k=0.001,
            temperature_k=0.0,
        )


def test_unselected_supplied_terms_do_not_enter_result() -> None:
    result = evaluate_free_energy(
        _ledger(),
        _full_entry(),
        FreeEnergyRecipe(key="electronic-only"),
    )
    assert result.free_energy_ev == pytest.approx(-10.0)
    assert [item.contribution_type for item in result.contributions] == ["electronic_dft"]
    assert result.temperature_k == pytest.approx(300.0)


def test_additional_correction_and_recipe_order_are_canonical() -> None:
    first = FreeEnergyCorrection(
        key="b",
        correction_type="manual",
        value_ev=0.2,
        source_id="source-b",
    )
    second = FreeEnergyCorrection(
        key="a",
        correction_type="manual",
        value_ev=-0.1,
        source_id="source-a",
    )
    entry_one = ThermodynamicEntry(
        key="state-g",
        dft_entry_key="state",
        corrections=(first, second),
    )
    entry_two = ThermodynamicEntry(
        key="state-g",
        dft_entry_key="state",
        corrections=(second, first),
    )
    recipe_one = FreeEnergyRecipe(key="r", correction_keys=("b", "a"))
    recipe_two = FreeEnergyRecipe(key="r", correction_keys=("a", "b"))

    assert [item.key for item in entry_one.corrections] == ["a", "b"]
    assert entry_one.digest == entry_two.digest
    assert recipe_one.correction_keys == ("a", "b")
    assert recipe_one.digest == recipe_two.digest
    assert evaluate_free_energy(_ledger(), entry_one, recipe_one).digest == (
        evaluate_free_energy(_ledger(), entry_two, recipe_two).digest
    )


def test_duplicate_and_unknown_correction_keys_fail_closed() -> None:
    correction = FreeEnergyCorrection(
        key="same",
        correction_type="manual",
        value_ev=0.1,
        source_id="source",
    )
    with pytest.raises(ThermodynamicsError, match="unique"):
        ThermodynamicEntry(
            key="bad",
            dft_entry_key="state",
            corrections=(correction, correction),
        )
    with pytest.raises(ThermodynamicsError, match="unique"):
        FreeEnergyRecipe(key="bad", correction_keys=("a", "a"))
    with pytest.raises(ThermodynamicsError, match="unavailable"):
        evaluate_free_energy(
            _ledger(),
            ThermodynamicEntry(key="state-g", dft_entry_key="state"),
            FreeEnergyRecipe(key="bad", correction_keys=("missing",)),
        )


def test_ledger_reference_and_normalization_basis_are_required_and_retained() -> None:
    entry = ThermodynamicEntry(key="state-g", dft_entry_key="missing")
    with pytest.raises(ThermodynamicsError, match="unknown DFT entry"):
        evaluate_free_energy(_ledger(), entry, FreeEnergyRecipe(key="r"))

    with pytest.raises(ThermodynamicsError, match="normalization_basis"):
        evaluate_free_energy(
            _ledger(basis=None),
            ThermodynamicEntry(key="state-g", dft_entry_key="state"),
            FreeEnergyRecipe(key="r"),
        )


def test_display_labels_do_not_change_scientific_digests() -> None:
    entry_a = _full_entry(label="A")
    entry_b = _full_entry(label="B")
    recipe_a = _full_recipe(label="recipe A")
    recipe_b = _full_recipe(label="recipe B")
    assert entry_a.digest == entry_b.digest
    assert recipe_a.digest == recipe_b.digest
    result_a = evaluate_free_energy(_ledger(), entry_a, recipe_a)
    result_b = evaluate_free_energy(_ledger(), entry_b, recipe_b)
    assert result_a.digest == result_b.digest
    assert result_a != result_b


def test_reporting_frames_are_detached() -> None:
    entry = _full_entry()
    evaluation = evaluate_free_energy(_ledger(), entry, _full_recipe())
    entry_frame = thermodynamic_entry_frame(entry)
    contribution_frame = free_energy_contributions_frame(evaluation)

    entry_frame.loc[0, "zpe_ev"] = 99.0
    contribution_frame.loc[0, "value_ev"] = 99.0
    assert entry.zpe_ev == pytest.approx(0.5)
    assert evaluation.contributions[0].value_ev == pytest.approx(-10.0)


def test_che_she_zero_potential_ph_zero_is_half_h2() -> None:
    h2 = _h2_evaluation()
    state = CHEState(
        temperature_k=298.15,
        ph=0.0,
        potential_v=0.0,
        potential_reference="SHE",
    )
    result = evaluate_che_proton_electron(h2, state)
    assert isinstance(result, CHEProtonElectronResult)
    assert result.half_h2_ev == pytest.approx(-3.0)
    assert result.potential_contribution_ev == pytest.approx(0.0)
    assert result.ph_contribution_ev == pytest.approx(0.0)
    assert result.mu_ev == pytest.approx(-3.0)
    assert result.potential_she_v == pytest.approx(0.0)


def test_che_she_potential_and_ph_signs_are_explicit() -> None:
    h2 = _h2_evaluation()
    temperature = 298.15
    ph = 2.0
    potential = 0.4
    result = evaluate_che_proton_electron(
        h2,
        CHEState(
            temperature_k=temperature,
            ph=ph,
            potential_v=potential,
            potential_reference="SHE",
        ),
    )
    shift = BOLTZMANN_EV_PER_K * temperature * log(10.0) * ph
    assert result.nernst_ph_shift_v == pytest.approx(shift)
    assert result.potential_she_v == pytest.approx(potential)
    assert result.potential_contribution_ev == pytest.approx(-potential)
    assert result.ph_contribution_ev == pytest.approx(-shift)
    assert result.mu_ev == pytest.approx(-3.0 - potential - shift)


def test_che_rhe_conversion_uses_general_she_equation_and_cancels_ph() -> None:
    h2 = _h2_evaluation()
    temperature = 310.0
    ph = 7.0
    u_rhe = -0.25
    result = evaluate_che_proton_electron(
        h2,
        CHEState(
            temperature_k=temperature,
            ph=ph,
            potential_v=u_rhe,
            potential_reference="RHE",
        ),
    )
    shift = BOLTZMANN_EV_PER_K * temperature * log(10.0) * ph
    assert result.nernst_ph_shift_v == pytest.approx(shift)
    assert result.potential_she_v == pytest.approx(u_rhe - shift)
    assert result.potential_contribution_ev == pytest.approx(-(u_rhe - shift))
    assert result.ph_contribution_ev == pytest.approx(-shift)
    assert result.mu_ev == pytest.approx(-3.0 - u_rhe)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"temperature_k": 0.0, "ph": 0.0, "potential_v": 0.0, "potential_reference": "SHE"},
        {
            "temperature_k": 298.15,
            "ph": float("nan"),
            "potential_v": 0.0,
            "potential_reference": "SHE",
        },
        {
            "temperature_k": 298.15,
            "ph": 0.0,
            "potential_v": float("inf"),
            "potential_reference": "SHE",
        },
        {"temperature_k": 298.15, "ph": 0.0, "potential_v": 0.0, "potential_reference": "NHE"},
    ],
)
def test_invalid_che_state_fails_closed(kwargs: dict[str, object]) -> None:
    with pytest.raises((ThermodynamicsError, TypeError)):
        CHEState(**kwargs)  # type: ignore[arg-type]


def test_che_temperature_must_match_temperature_specific_h2_evaluation() -> None:
    h2 = _h2_evaluation(temperature_k=300.0)
    with pytest.raises(ThermodynamicsError, match="temperature"):
        evaluate_che_proton_electron(
            h2,
            CHEState(
                temperature_k=298.15,
                ph=0.0,
                potential_v=0.0,
                potential_reference="SHE",
            ),
        )


def test_che_reporting_frame_is_detached() -> None:
    result = evaluate_che_proton_electron(
        _h2_evaluation(),
        CHEState(
            temperature_k=298.15,
            ph=1.0,
            potential_v=0.2,
            potential_reference="SHE",
        ),
    )
    frame = che_result_frame(result)
    frame.loc[0, "mu_ev"] = 123.0
    assert result.mu_ev != pytest.approx(123.0)


def _evaluation_for_reaction(
    key: str,
    energy_ev: float,
    *,
    basis: str = "per reaction cell",
) -> FreeEnergyEvaluation:
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
        ThermodynamicEntry(key=key, dft_entry_key=key),
        FreeEnergyRecipe(key="electronic-only"),
    )


def test_reaction_free_energy_uses_explicit_products_positive_coefficients() -> None:
    reactant = _evaluation_for_reaction("reactant", -1.0)
    product = _evaluation_for_reaction("product", -2.0)
    result = reaction_free_energy(
        (
            thermodynamic_reaction_term(reactant, -1.0),
            thermodynamic_reaction_term(product, +1.0),
        ),
        expression_label="reactant -> product",
    )
    assert result.delta_g_ev == pytest.approx(-1.0)
    assert [item.contribution_ev for item in result.terms] == pytest.approx([1.0, -2.0])
    assert result.thermodynamic_normalization_basis == "per reaction cell"


def test_reaction_che_coefficient_controls_potential_term_without_name_logic() -> None:
    che = evaluate_che_proton_electron(
        _h2_evaluation(),
        CHEState(
            temperature_k=298.15,
            ph=0.0,
            potential_v=0.5,
            potential_reference="SHE",
        ),
    )
    single = reaction_free_energy(
        (che_reaction_term(che, -1.0),),
        expression_label="one explicit pair",
    )
    double = reaction_free_energy(
        (che_reaction_term(che, -2.0),),
        expression_label="two explicit pairs",
    )
    assert single.delta_g_ev == pytest.approx(-che.mu_ev)
    assert double.delta_g_ev == pytest.approx(-2.0 * che.mu_ev)


def test_reaction_incompatible_thermodynamic_bases_fail_closed() -> None:
    first = _evaluation_for_reaction("a", -1.0, basis="per cell")
    second = _evaluation_for_reaction("b", -2.0, basis="per molecule")
    with pytest.raises(ThermodynamicsError, match="normalization_basis"):
        reaction_free_energy(
            (
                thermodynamic_reaction_term(first, -1.0),
                thermodynamic_reaction_term(second, +1.0),
            ),
            expression_label="incompatible",
        )


def test_reaction_duplicate_source_identity_fails_closed() -> None:
    state = _evaluation_for_reaction("a", -1.0)
    term = thermodynamic_reaction_term(state, -1.0)
    with pytest.raises(ThermodynamicsError, match="unique"):
        reaction_free_energy((term, term), expression_label="duplicate")


def test_reaction_term_validation_and_reporting_frame() -> None:
    state = _evaluation_for_reaction("a", -1.0)
    result = reaction_free_energy(
        (thermodynamic_reaction_term(state, -1.0),),
        expression_label="a consumed",
    )
    frame = reaction_free_energy_frame(result)
    frame.loc[0, "contribution_ev"] = 99.0
    assert result.terms[0].contribution_ev == pytest.approx(1.0)

    with pytest.raises(ThermodynamicsError, match="unsupported"):
        ReactionFreeEnergyTerm(
            source_key="bad",
            source_type="mystery",
            coefficient=1.0,
            value_ev=1.0,
            source_digest="digest",
            normalization_basis="basis",
        )


def test_constant_value_is_explicit_and_stable() -> None:
    assert BOLTZMANN_EV_PER_K == pytest.approx(8.617333262145e-5, rel=0.0, abs=0.0)
