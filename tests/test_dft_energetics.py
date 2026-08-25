from __future__ import annotations

import numpy as np
import pytest

from catalysis_workbench.computation import (
    DFTEnergeticsError,
    DFTEnergyEntry,
    DFTEnergyLedger,
    EnergyCombinationResult,
    EnergyTerm,
    adsorption_energy,
    combine_energies,
    dft_energy_entries_frame,
    energy_combination_frame,
    relative_energies,
    relative_energy_frame,
)
from catalysis_workbench.visualization import plot_relative_energies


def _ledger() -> DFTEnergyLedger:
    return DFTEnergyLedger(
        entries=(
            DFTEnergyEntry(
                "a",
                -10.0,
                label="A",
                normalization_basis="cell",
                source_id="calc-a",
                metadata={"nested": {"values": [1, 2]}},
            ),
            DFTEnergyEntry(
                "b",
                -9.5,
                label="B",
                normalization_basis="cell",
                source_id="calc-b",
            ),
            DFTEnergyEntry(
                "c",
                -10.2,
                label="C",
                normalization_basis="cell",
                source_id="calc-c",
            ),
        ),
        source_id="dft-set-1",
        metadata={"code": "VASP"},
    )


def test_energy_entry_and_ledger_are_fail_closed_and_immutable() -> None:
    ledger = _ledger()
    assert ledger.entry("b").energy_ev == pytest.approx(-9.5)
    assert len(ledger.digest) == 64
    assert ledger.entry("a").metadata["nested"]["values"] == (1, 2)
    detached = ledger.entry("a").metadata_dict()
    detached["nested"]["values"].append(3)
    assert ledger.entry("a").metadata["nested"]["values"] == (1, 2)

    with pytest.raises(DFTEnergeticsError, match="unique"):
        DFTEnergyLedger(
            entries=(DFTEnergyEntry("a", 0.0), DFTEnergyEntry("a", 1.0)),
            source_id="duplicate",
        )
    with pytest.raises(DFTEnergeticsError, match="finite"):
        DFTEnergyEntry("bad", np.inf)
    with pytest.raises(DFTEnergeticsError, match="unknown"):
        ledger.entry("missing")


def test_relative_energies_are_hand_verifiable_and_reconstructible() -> None:
    result = relative_energies(_ledger(), "a")
    assert result.entry_keys == ("a", "b", "c")
    assert result.entry_labels == ("A", "B", "C")
    np.testing.assert_allclose(result.energies_ev, [-10.0, -9.5, -10.2])
    np.testing.assert_allclose(result.delta_energy_ev, [0.0, 0.5, -0.2])
    assert result.normalization_basis == "cell"
    assert result.energies_ev.flags.writeable is False
    assert result.delta_energy_ev.flags.writeable is False

    with pytest.raises(DFTEnergeticsError, match="include the reference"):
        relative_energies(_ledger(), "a", entry_keys=("b", "c"))


def test_relative_energies_require_explicit_matching_basis() -> None:
    unknown = DFTEnergyLedger(
        entries=(DFTEnergyEntry("a", 1.0), DFTEnergyEntry("b", 2.0)),
        source_id="unknown-basis",
    )
    with pytest.raises(DFTEnergeticsError, match="explicit reference"):
        relative_energies(unknown, "a")

    mixed = DFTEnergyLedger(
        entries=(
            DFTEnergyEntry("a", 1.0, normalization_basis="cell"),
            DFTEnergyEntry("b", 2.0, normalization_basis="atom"),
        ),
        source_id="mixed-basis",
    )
    with pytest.raises(DFTEnergeticsError, match="matching normalization_basis"):
        relative_energies(mixed, "a")


def test_generic_linear_combination_retains_fractional_negative_and_zero_terms() -> None:
    ledger = DFTEnergyLedger(
        entries=(
            DFTEnergyEntry("x", -100.0, normalization_basis="cell"),
            DFTEnergyEntry("y", -90.0, normalization_basis="cell"),
            DFTEnergyEntry("z", -10.0, normalization_basis="molecule"),
            DFTEnergyEntry("zero", 7.0, normalization_basis="molecule"),
        ),
        source_id="reaction-set",
    )
    result = combine_energies(
        ledger,
        (
            EnergyTerm("x", 1.0),
            EnergyTerm("y", -1.0),
            EnergyTerm("z", -0.5),
            EnergyTerm("zero", 0.0),
        ),
        expression_label="explicit reaction",
        result_basis="reaction_event",
    )
    np.testing.assert_allclose(result.term_energies_ev, [-100.0, -90.0, -10.0, 7.0])
    np.testing.assert_allclose(result.contributions_ev, [-100.0, 90.0, 5.0, 0.0])
    assert result.value_ev == pytest.approx(-5.0)
    assert result.terms[-1].coefficient == 0.0

    with pytest.raises(DFTEnergeticsError, match="entry keys must be unique"):
        EnergyCombinationResult(
            ledger_digest=ledger.digest,
            terms=(EnergyTerm("x", 1.0), EnergyTerm("x", -1.0)),
            term_energies_ev=(-100.0, -100.0),
            contributions_ev=(-100.0, 100.0),
            value_ev=0.0,
            expression_label="duplicate",
            result_basis="event",
        )


def test_adsorption_energy_is_a_transparent_named_linear_combination() -> None:
    ledger = DFTEnergyLedger(
        entries=(
            DFTEnergyEntry("combined", -105.0, normalization_basis="cell"),
            DFTEnergyEntry("slab", -90.0, normalization_basis="cell"),
            DFTEnergyEntry("ads", -14.0, normalization_basis="molecule"),
        ),
        source_id="adsorption-set",
    )
    result = adsorption_energy(
        ledger,
        combined_key="combined",
        slab_key="slab",
        adsorbate_key="ads",
    )
    assert [term.entry_key for term in result.terms] == ["combined", "slab", "ads"]
    np.testing.assert_allclose([term.coefficient for term in result.terms], [1.0, -1.0, -1.0])
    assert result.value_ev == pytest.approx(-1.0)
    assert result.result_basis == "adsorption_event"
    assert result.expression_label == "E(combined) - E(slab) - 1*E(ads)"

    with pytest.raises(DFTEnergeticsError, match="positive"):
        adsorption_energy(
            ledger,
            combined_key="combined",
            slab_key="slab",
            adsorbate_key="ads",
            adsorbate_stoichiometry=0.0,
        )


def test_reporting_frames_are_detached_and_retain_explicit_units_and_terms() -> None:
    ledger = _ledger()
    relative = relative_energies(ledger, "a")
    combination = combine_energies(
        ledger,
        (EnergyTerm("b", 1.0), EnergyTerm("a", -1.0)),
        expression_label="B-A",
        result_basis="cell_difference",
    )

    entries_frame = dft_energy_entries_frame(ledger)
    assert list(entries_frame["entry_key"]) == ["a", "b", "c"]
    assert list(entries_frame["energy_ev"]) == [-10.0, -9.5, -10.2]

    relative_frame = relative_energy_frame(relative)
    assert list(relative_frame["delta_energy_ev"]) == pytest.approx([0.0, 0.5, -0.2])
    relative_frame.loc[0, "delta_energy_ev"] = 999.0
    assert relative.delta_energy_ev[0] == pytest.approx(0.0)

    combination_frame = energy_combination_frame(combination)
    assert list(combination_frame["coefficient"]) == [1.0, -1.0]
    assert list(combination_frame["contribution_ev"]) == pytest.approx([-9.5, 10.0])
    assert combination_frame["result_value_ev"].iloc[0] == pytest.approx(0.5)


def test_relative_energy_plot_is_passive_and_uses_retained_category_order() -> None:
    result = relative_energies(_ledger(), "a")
    before = np.array(result.delta_energy_ev, copy=True)
    figure, ax = plot_relative_energies(result)
    assert len(ax.patches) == 3
    assert [tick.get_text() for tick in ax.get_xticklabels()] == ["A", "B", "C"]
    np.testing.assert_array_equal(result.delta_energy_ev, before)
    figure.canvas.draw()
