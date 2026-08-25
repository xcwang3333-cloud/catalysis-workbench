# Free-energy diagrams

CatalysisWorkbench v0.6 Block 8 separates free-energy diagram state from rendering. The diagram layer consumes reviewed thermodynamic values from Block 7 and never acts as a reaction solver, CHE calculator, transition-state model, or hidden reference selector.

## Ordered pathway state

`FreeEnergyDiagramState` retains one caller-declared pathway state with:

- a stable state key;
- an absolute free energy in eV;
- exact source key, source type, and source digest;
- an explicit normalization basis;
- an optional display label kept separate from scientific identity.

`diagram_state_from_free_energy()` is the narrow convenience adapter for a reviewed `FreeEnergyEvaluation`. It copies the evaluated free energy, exact evaluation digest, key, normalization basis, and optional display label. It does not recompute any thermodynamic correction.

State order is scientific/audit state. A `FreeEnergyDiagramSeries` retains the exact order supplied by the caller. CatalysisWorkbench does not sort states, infer reaction order, discover intermediates, balance formulas, or construct a pathway from names.

## Absolute and reference-relative modes

The caller must explicitly choose an energy mode.

### Absolute

For `energy_mode="absolute"`, the plotted value is the retained absolute free energy:

`G_plot,i = G_i`

An absolute series must not define `reference_state_key`.

### Reference-relative

For `energy_mode="reference_relative"`, the caller must explicitly name one retained state key:

`G_plot,i = G_i - G_ref`

There is deliberately no default rule that makes the first state zero. Missing or unknown reference keys fail closed. The series retains both the absolute state values and the derived immutable plotted values together with the explicit reference key.

Reference subtraction occurs when the scientific diagram series is built. It does not occur in the renderer.

## Normalization and comparison basis

All states within one series must have one matching explicit normalization basis. No basis conversion is attempted.

The caller also supplies a `comparison_basis` string. This identifies the scientific comparison definition shared by series that are intended to be overlaid; display labels do not define compatibility.

`validate_free_energy_diagram_series_compatibility()` requires multiple series to have:

- identical ordered state keys;
- the same energy mode;
- the same normalization basis;
- the same comparison basis;
- the same explicit reference state for reference-relative mode;
- the same retained electrochemical-context digest, or no context on every series.

Incompatible state order, reference semantics, normalization, comparison basis, or electrochemical context fails explicitly rather than being aligned or converted.

## Electrochemical context

`diagram_context_from_che()` copies descriptive electrochemical provenance from a reviewed Block-7 `CHEProtonElectronResult`:

- temperature in K;
- pH;
- input potential in V;
- input reference (`SHE` or `RHE`);
- retained converted `U_SHE`;
- exact CHE source digest.

Block 8 does not recalculate CHE, convert SHE/RHE, or shift state energies with pH or potential. If a free energy at another electrochemical condition is required, that thermodynamic state must first be evaluated explicitly in Block 7 and then supplied to Block 8.

The optional context annotation in the plot is presentation-only and is generated from these retained fields.

## Passive rendering

`plot_free_energy_diagram()` consumes one compatible series or several compatible series and uses the existing `FigureSpec` publication-rendering system.

The renderer draws:

- one horizontal level for each retained pathway state;
- one straight connector between each pair of adjacent retained states;
- categorical state labels in the retained order;
- optional retained electrochemical-context text;
- optional per-series styling through `FigureSpec.series_styles`.

The renderer reads `plotted_energy_ev` directly. It performs no free-energy arithmetic, CHE correction, reference subtraction, smoothing, interpolation, barrier construction, or state sorting. Retained arrays are checked after rendering to ensure plotting did not mutate scientific state.

Free-energy diagrams require linear x and y scales. A pathway state cannot be hidden by a category-style override because silently removing an intermediate state would change the visual meaning of the retained pathway. A whole comparison series may be hidden as a presentation choice.

## Reporting

`free_energy_diagram_frame()` returns a detached one-row-per-state table containing the series/state identity, state order, absolute and plotted energy, mode/reference, source provenance, normalization basis, comparison basis, and retained electrochemical context.

The reporting table distinguishes:

- `diagram_context_digest`: deterministic identity of the retained Block-8 context object;
- `che_source_digest`: exact digest of the Block-7 CHE result from which that context was copied.

Mutating the DataFrame cannot mutate the immutable retained diagram state.

## Prior art and licensing

CatMAP `MechanismAnalysis` is a useful workflow reference for conventional catalytic free-energy-diagram presentation, but it can construct diagrams from a reaction mechanism and model-evaluated thermodynamics. That behavior is intentionally not adopted because CatalysisWorkbench Block 8 is a passive consumer of already reviewed scientific state. CatMAP is GPL-3.0 and is strict reference-only: no code reuse and no dependency.

PyEnergyDiagrams provides a lightweight Matplotlib model based on horizontal levels and connecting lines. It is MIT-licensed and serves only as a presentation reference. CatalysisWorkbench uses its existing Matplotlib/`FigureSpec` stack and does not add PyEnergyDiagrams as a dependency.

The existing CatalysisWorkbench `plot_relative_energies()` implementation is the internal precedent for passive rendering of retained energetic results.

## Explicit exclusions

Block 8 does not provide:

- reaction/pathway discovery;
- formula balancing;
- thermodynamic or CHE recomputation;
- implicit potential or pH shifts;
- hidden first-state zeroing;
- transition states or activation barriers;
- NEB/barrier plotting;
- microkinetic or coverage solving;
- Pourbaix construction;
- charge-density-difference processing.

Transition-state/barrier and NEB visualization remain outside Block 8 and inside the v0.7 advanced-computational-visualization boundary. Charge-density-difference calculation with strict lattice/grid/component validation is v0.6 Block 9.
