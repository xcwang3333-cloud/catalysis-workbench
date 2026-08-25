from __future__ import annotations

from catalysis_workbench.computation import (
    CHEState,
    DFTEnergyEntry,
    DFTEnergyLedger,
    FreeEnergyDiagramContext,
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
from catalysis_workbench.visualization import plot_free_energy_diagram

assert FreeEnergyDiagramError is not None
assert FreeEnergyDiagramState is not None
assert FreeEnergyDiagramContext is not None
assert FreeEnergyDiagramSeries is not None


def evaluation(key: str, value: float, *, basis: str = "per reaction cell"):
    ledger = DFTEnergyLedger(
        entries=(
            DFTEnergyEntry(
                key=key,
                energy_ev=value,
                normalization_basis=basis,
                source_id=f"installed-{key}",
            ),
        ),
        source_id=f"installed-ledger-{key}",
    )
    return evaluate_free_energy(
        ledger,
        ThermodynamicEntry(key=key, dft_entry_key=key),
        FreeEnergyRecipe(key="electronic-only"),
    )


states = tuple(
    diagram_state_from_free_energy(evaluation(key, value))
    for key, value in (("initial", -10.0), ("middle", -9.0), ("final", -9.5))
)
series = build_free_energy_diagram_series(
    states,
    key="installed-path",
    energy_mode="reference_relative",
    comparison_basis="installed reaction path",
    reference_state_key="initial",
)
assert tuple(series.plotted_energy_ev) == (0.0, 1.0, 0.5)
assert validate_free_energy_diagram_series_compatibility((series,)) == (series,)
frame = free_energy_diagram_frame(series)
assert list(frame["state_key"]) == ["initial", "middle", "final"]

h2 = evaluation("h2", -6.0, basis="per H2 molecule")
che = evaluate_che_proton_electron(
    h2,
    CHEState(
        temperature_k=298.15,
        ph=7.0,
        potential_v=0.2,
        potential_reference="RHE",
    ),
)
context = diagram_context_from_che(che)
context_series = build_free_energy_diagram_series(
    states,
    key="installed-context-path",
    energy_mode="absolute",
    comparison_basis="installed reaction path",
    context=context,
)
context_frame = free_energy_diagram_frame(context_series)
assert context_frame.loc[0, "diagram_context_digest"] == context.digest
assert context_frame.loc[0, "che_source_digest"] == che.digest

figure, ax = plot_free_energy_diagram(series)
assert len(ax.lines) == 5
figure.canvas.draw()
print("installed v0.6 free-energy diagram smoke: ok")
