from __future__ import annotations

import sys
from importlib import import_module

import numpy as np

import catalysis_workbench.computation as cw

assert "matplotlib.pyplot" not in sys.modules

ledger = cw.DFTEnergyLedger(
    entries=(
        cw.DFTEnergyEntry("combined", -105.0, normalization_basis="cell"),
        cw.DFTEnergyEntry("slab", -90.0, normalization_basis="cell"),
        cw.DFTEnergyEntry("ads", -14.0, normalization_basis="molecule"),
    ),
    source_id="installed-dft-smoke",
)
relative = cw.relative_energies(
    cw.DFTEnergyLedger(
        entries=(
            cw.DFTEnergyEntry("a", -10.0, normalization_basis="cell"),
            cw.DFTEnergyEntry("b", -9.5, normalization_basis="cell"),
        ),
        source_id="installed-relative",
    ),
    "a",
)
np.testing.assert_allclose(relative.delta_energy_ev, [0.0, 0.5])

adsorption = cw.adsorption_energy(
    ledger,
    combined_key="combined",
    slab_key="slab",
    adsorbate_key="ads",
)
assert np.isclose(adsorption.value_ev, -1.0)
assert adsorption.terms[2].coefficient == -1.0
assert len(cw.energy_combination_frame(adsorption)) == 3

plot_relative_energies = import_module(
    "catalysis_workbench.visualization"
).plot_relative_energies
figure, ax = plot_relative_energies(relative)
assert len(ax.patches) == 2
figure.canvas.draw()
