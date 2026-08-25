# Basic DFT energetics

CatalysisWorkbench v0.5 treats DFT energetics as explicit post-processing of caller-supplied scalar energies. It does not run VASP, infer chemistry, or apply thermodynamic corrections.

## Scientific state

`DFTEnergyEntry` stores one finite energy in eV under a stable key. Optional `normalization_basis` and `source_id` are retained as explicit provenance. `DFTEnergyLedger` keeps ordered unique entries and computes a deterministic digest from the scientific energy state.

Labels and metadata are descriptive. They do not change energy arithmetic.

## Relative energies

`relative_energies()` requires an explicit reference key and one explicit matching, non-missing normalization basis across all compared entries. The function preserves caller/ledger order and returns both retained total energies and the corresponding `delta_energy_ev` values.

The implementation does not silently divide by atom count, formula unit, surface area, active site, or any other basis.

## Explicit linear combinations

`combine_energies()` evaluates only caller-supplied `EnergyTerm(entry_key, coefficient)` objects. Coefficients may be positive, negative, fractional, or zero and are retained exactly in the result. The caller must also supply a `result_basis` describing the normalization of the resulting scalar.

This generic operation can represent reaction-energy-like arithmetic without parsing formulas or inferring stoichiometry.

## Adsorption energy

`adsorption_energy()` is a named convenience wrapper for the explicit expression

`E(combined) - E(slab) - n * E(adsorbate)`

where `n` is the caller-supplied positive `adsorbate_stoichiometry`. The three entry keys and all coefficients are retained in the returned `EnergyCombinationResult`.

No alternative sign convention is inferred. If a project needs a different convention, use `combine_energies()` and state the expression explicitly.

## Reporting and plotting

- `dft_energy_entries_frame()` returns a detached ledger table.
- `relative_energy_frame()` returns a detached relative-energy table.
- `energy_combination_frame()` exposes every retained coefficient, input energy, contribution, and final value.
- `plot_relative_energies()` is a passive categorical bar renderer. It consumes retained `delta_energy_ev` values and does not recompute energetic arithmetic.

## Explicit non-actions in v0.5

This layer does not perform:

- VASP/DFT job submission;
- CHE potential or pH corrections;
- ZPE, entropy, or finite-temperature corrections;
- gas-phase thermochemical database lookup;
- chemical-potential inference;
- formula parsing or automatic stoichiometry;
- DOS/PDOS analysis;
- Bader analysis;
- COHP/ICOHP analysis;
- charge-density-difference analysis.

Those capabilities require separate reviewed scientific contracts in later releases.
