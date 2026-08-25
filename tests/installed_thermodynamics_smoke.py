from __future__ import annotations

from catalysis_workbench.computation import (
    BOLTZMANN_EV_PER_K,
    CHEProtonElectronResult,
    CHEState,
    DFTEnergyEntry,
    DFTEnergyLedger,
    FreeEnergyContribution,
    FreeEnergyCorrection,
    FreeEnergyEvaluation,
    FreeEnergyRecipe,
    ReactionFreeEnergyResult,
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

assert ThermodynamicsError is not None
assert FreeEnergyContribution is not None
assert FreeEnergyEvaluation is not None
assert CHEProtonElectronResult is not None
assert ReactionFreeEnergyTerm is not None
assert ReactionFreeEnergyResult is not None
assert BOLTZMANN_EV_PER_K > 0.0

ledger = DFTEnergyLedger(
    entries=(
        DFTEnergyEntry(
            key="h2",
            energy_ev=-6.0,
            normalization_basis="per H2 molecule",
            source_id="installed-h2",
        ),
    ),
    source_id="installed-ledger",
)
entry = ThermodynamicEntry(
    key="h2-g",
    dft_entry_key="h2",
    zpe_ev=0.2,
    thermal_enthalpy_correction_ev=0.1,
    entropy_ev_per_k=0.001,
    temperature_k=300.0,
    corrections=(
        FreeEnergyCorrection(
            key="solvation",
            correction_type="solvation",
            value_ev=-0.05,
            source_id="installed-caller",
        ),
    ),
)
recipe = FreeEnergyRecipe(
    key="installed-recipe",
    include_zpe=True,
    include_thermal_enthalpy=True,
    include_entropy=True,
    correction_keys=("solvation",),
)
free_energy = evaluate_free_energy(ledger, entry, recipe)
assert abs(free_energy.free_energy_ev - (-6.05)) < 1e-12
assert len(thermodynamic_entry_frame(entry)) == 1
assert len(free_energy_contributions_frame(free_energy)) == 5

che = evaluate_che_proton_electron(
    free_energy,
    CHEState(
        temperature_k=300.0,
        ph=7.0,
        potential_v=0.2,
        potential_reference="RHE",
    ),
)
assert abs(che.mu_ev - (0.5 * free_energy.free_energy_ev - 0.2)) < 1e-12
assert len(che_result_frame(che)) == 1

state_ledger = DFTEnergyLedger(
    entries=(
        DFTEnergyEntry(
            key="state",
            energy_ev=-1.0,
            normalization_basis="per reaction cell",
            source_id="installed-state",
        ),
    ),
    source_id="installed-state-ledger",
)
state = evaluate_free_energy(
    state_ledger,
    ThermodynamicEntry(key="state-g", dft_entry_key="state"),
    FreeEnergyRecipe(key="state-recipe"),
)
reaction = reaction_free_energy(
    (
        thermodynamic_reaction_term(state, +1.0),
        che_reaction_term(che, -1.0),
    ),
    expression_label="installed explicit reaction",
)
assert reaction.delta_g_ev == state.free_energy_ev - che.mu_ev
assert len(reaction_free_energy_frame(reaction)) == 2
