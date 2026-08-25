"""Review regressions for v0.6 CHE/free-energy thermodynamics."""

from __future__ import annotations

import pytest

from catalysis_workbench.computation import (
    DFTEnergyEntry,
    DFTEnergyLedger,
    FreeEnergyRecipe,
    ThermodynamicEntry,
    evaluate_free_energy,
    reaction_free_energy,
    thermodynamic_reaction_term,
)


def _state(key: str, energy_ev: float):
    ledger = DFTEnergyLedger(
        entries=(
            DFTEnergyEntry(
                key=key,
                energy_ev=energy_ev,
                normalization_basis="per reaction cell",
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


def test_reaction_term_sequence_is_retained_explicit_scientific_state() -> None:
    """Equal sums do not erase the caller-declared reaction-term sequence."""
    reactant = thermodynamic_reaction_term(_state("reactant", -1.0), -1.0)
    product = thermodynamic_reaction_term(_state("product", -2.0), +1.0)

    forward = reaction_free_energy(
        (reactant, product),
        expression_label="reactant -> product",
    )
    reversed_terms = reaction_free_energy(
        (product, reactant),
        expression_label="same arithmetic, reversed declaration order",
    )

    assert forward.delta_g_ev == pytest.approx(reversed_terms.delta_g_ev)
    assert tuple(item.source_key for item in forward.terms) == ("reactant", "product")
    assert tuple(item.source_key for item in reversed_terms.terms) == ("product", "reactant")
    assert forward.digest != reversed_terms.digest
