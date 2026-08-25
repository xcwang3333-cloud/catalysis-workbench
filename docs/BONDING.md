# COHP / ICOHP bonding analysis

CatalysisWorkbench v0.6 block 5 consumes already-generated standard LOBSTER COHP/ICOHP outputs. It does not run LOBSTER, generate `lobsterin`, infer chemistry, or select bonds automatically.

## Parser boundary

The optional `structure` dependency already provides `pymatgen-core>=2026.7.16`, whose LOBSTER I/O is used lazily through `pymatgen.io.lobster.Cohpcar` and `Icohplist`. Backend parser objects are immediately converted into CatalysisWorkbench-owned immutable result state and are never part of the public scientific API.

The first adapter accepts only standard COHP/ICOHP output. COOP/ICOOP, COBI/ICOBI, multi-center COBI and LCFO-specific variants fail explicitly rather than being relabeled as COHP.

## Energy reference

Current pymatgen documentation states that LOBSTER shifts the parsed COHP energy grid so the Fermi level is at zero. CatalysisWorkbench therefore retains the parsed axis as:

- `reference_kind = "fermi"`;
- numerical Fermi position `0 eV`;
- `source_fermi_ev = 0.0` in the shared `ElectronicEnergyAxis`;
- `applied_shift_ev = 0.0`.

No additional Fermi subtraction is performed. The producer/backend-reported Fermi value is retained separately as `producer_fermi_ev` provenance and is not reused as the numerical zero position of the already-referenced axis.

## Scientific sign convention

COHP and integrated COHP/ICOHP values are retained exactly in the source LOBSTER sign convention.

CatalysisWorkbench does **not** silently multiply scientific arrays or summary values by `-1`. The familiar `-COHP` / `-ICOHP` presentation convention is a display transform only and is not part of block-5 scientific state.

This distinction is important because a publication axis labeled `-COHP` must never overwrite or masquerade as the producer value retained for quantitative analysis.

## Physical spin state

Scientific storage never uses mirrored plotting conventions.

- non-spin-polarized LOBSTER output becomes one physical `total` channel;
- collinear spin-polarized output must provide complete `up` and `down` channels;
- incomplete or unrecognized spin identity fails closed;
- numerical spin-down COHP values are retained exactly as supplied by LOBSTER.

For ICOHP(E_F), spin summation is never implicit. `sum_icohp_spins()` requires the caller to name the physical channels to combine and retains both the selected spin identities and source summary digest.

## COHP state

`COHPChannel` retains one physical-spin channel for a concrete source bond or explicit orbital-resolved bond channel:

- stable channel key;
- stable bond key;
- original source bond label;
- physical spin;
- source-sign COHP array;
- source-sign integrated-COHP array;
- bond length when supplied by the backend;
- source site indices when supplied;
- optional orbital key, source orbital label and exact converted orbital descriptors;
- deterministic scientific digest.

`COHPResult` retains the shared Fermi-referenced energy axis, ordered channels, optional producer Fermi provenance and source information. Every channel array must align exactly with the retained energy grid.

The source `average` COHP entry is intentionally omitted from the concrete-bond collection. It is not silently reclassified as a physical bond.

## Orbital-resolved identity

Orbital-resolved COHP is retained only when the backend supplies explicit identity. CatalysisWorkbench stores a stable orbital key, the producer orbital label and literal converted orbital descriptors.

No automatic `s/p/d/f` grouping or chemistry interpretation is inferred from display strings in this block.

## ICOHP(E_F) summary state

`ICOHPBondSummary` retains:

- stable bond key and original source label;
- bond length in angstrom;
- source `number_of_bonds` multiplicity basis;
- source-sign physical spin values at E_F;
- deterministic digest.

A non-spin summary contains only `total`. A spin-polarized summary must contain both `up` and `down`. A scientific state containing `total` together with `up/down` is rejected as ambiguous.

`ICOHPResult` preserves source order. `select_icohp_bonds()` and `select_cohp_channels()` are exact selectors; they do not rank, threshold, regroup or reinterpret bonds.

## Reporting tables

`cohp_channels_frame()` creates a detached point-wise table with energy/reference, channel/bond identity, physical spin, source-sign COHP/integrated COHP and retained bond/orbital provenance.

`icohp_bonds_frame()` creates a detached one-row-per-bond summary with separate `icohp_total`, `icohp_up` and `icohp_down` columns. It never creates an unlabeled implicit spin sum.

Returned DataFrames are detached reporting state. Editing them cannot mutate retained scientific results.

## Explicit exclusions

Block 5 does not perform:

- LOBSTER execution or input generation;
- strongest-bond ranking or percentage thresholds;
- cation/anion inference from Mulliken, Loewdin or bond-valence state;
- neighbor graph construction;
- qualitative automatic bonding/antibonding classification;
- automatic chemistry narrative;
- cross-structure bond matching;
- geometry-bonding correlation (v0.6 block 6);
- CHE/free-energy analysis;
- charge-density-difference analysis;
- implicit `-COHP/-ICOHP` sign inversion.

LobsterPy is useful reference prior art for automated bonding workflows and plotting, but its automatic strongest-bond thresholds and cation/anion inference are intentionally outside the CatalysisWorkbench block-5 contract.
