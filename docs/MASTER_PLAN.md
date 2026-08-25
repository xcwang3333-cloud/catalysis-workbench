# CatalysisWorkbench Master Plan

This document is the project-level execution map for CatalysisWorkbench. It connects the long-range release roadmap to active GitHub Issues, scientific/API quality gates, documentation responsibilities, and the rule that repository state is authoritative.

## Authority and source of truth

GitHub is the only operational source of truth for project state.

When documents and live repository state disagree, use this precedence order:

1. merged `main` code and tests;
2. current GitHub Issues and Pull Requests;
3. CI status for the exact commit under review;
4. this master plan and release-specific planning documents;
5. README summaries and other descriptive documentation.

Planning documents must be corrected when they drift from merged reality. They do not override code, Issue state, review findings, CI, immutable release tags, or explicit release-boundary decisions.

## Current checkpoint

Checkpoint date: 2026-08-25.

- Repository: `xcwang3333-cloud/catalysis-workbench`.
- Stable integration branch: `main`.
- Exact pre-sync baseline: `b9e3e27c667df9afc6060e387ad0ca4510a73d78`, the expected-head squash merge of v0.7 Block-2 Issue #206 / PR #207.
- Distribution/runtime version is `0.6.0`.
- Released tag `v0.6.0 -> c7793b309f41d174c14534bd6d4acdacc2a57636` is immutable.
- The public GitHub Release `CatalysisWorkbench v0.6.0` is published from that existing tag.
- Final v0.6 post-release documentation synchronization is complete at `fcc8c0ce73953c8d7468a58dcb0c172e520c4202` through Issue #195 / PR #196.
- All nine v0.6 scientific blocks, Gate A, Gate B, Gate C, GitHub Release publication, and final post-release documentation synchronization are complete.
- `v0.5.0 -> 9400ac0044ac333d2cae228554c08d955a816a4c` remains immutable; its public GitHub Release is complete.
- `v0.4.0 -> bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6` remains immutable; its public GitHub Release is complete.
- PyPI/package-registry publication remains explicitly deferred.
- v0.7 architecture checkpoint: Issue #197 / PR #198 — complete at `a854b5d4ab6168d857f9f783c9b4c1827e064972`.
- v0.7 architecture central-document synchronization: Issue #199 / PR #201 — complete at `7f04e1312a67417ea9b1ddd10482722c599040d4`.
- v0.7 Block 1, shared scalar-field + renderer-neutral volumetric scene foundation: Issue #202 / PR #203 — complete at `4a101337f7822c4d687dd2edf3cc12168278619b`.
- Block-1 final head `db0526cfca5b6cc540ac8198b9fd2a02754ba391` passed CI #474 / run `32855491587` and exact-head reviews `5019699984`, `5019702262`; unresolved review threads were zero and the PR was behind=0 / mergeable=true before squash merge.
- v0.7 Block-1 completion-state synchronization: Issue #204 / PR #205 — complete at `ff263c20b8986c65a47dfdd544ca712a8e3f3cd8`.
- v0.7 Block 2, charge-density-difference + electron-density + ELF visualization: Issue #206 / PR #207 — complete at `b9e3e27c667df9afc6060e387ad0ca4510a73d78`.
- Block-2 final head `c3a952f9aad9535cfc7b2a88413527fd40487cfe` passed CI #486 / run `32862918547` (Ruff, 1009-test full pytest, fresh-wheel/public-API smoke, v0.6 + v0.7 Block-1/2 installed audits, optional structure/electronic/bonding + real current `pymatgen-core` ELFCAR round-trip, and documented examples) and exact-head reviews `5020510393`, `5020512056`; unresolved review threads were zero and the PR was behind=0 / mergeable=true before expected-head squash merge.
- [`V0_7_PLAN.md`](V0_7_PLAN.md) remains the release-specific authority for the frozen seven-block v0.7 scope, scientific/visualization contracts, dependency order, prior-art/license decisions, testing strategy, and release boundaries.
- [`VOLUMETRIC_VISUALIZATION.md`](VOLUMETRIC_VISUALIZATION.md) records the reviewed Block-1 scalar-field/source-grid/renderer-neutral foundation and Block-2 charge-density-difference, electron-density, ELFCAR/ELF, and exact-slice visualization contracts.
- Active stage: **Issue #208 — synchronize the completed v0.7 Block-2 state into central documentation**.
- v0.7 Block 3, band-structure state/adapters + passive band plotting, begins only after #208 merges and `main` plus release boundaries are reverified.

Live GitHub Issue/PR/tag state remains authoritative if this checkpoint becomes stale.

## Release map

Detailed long-range scope is maintained in [`ROADMAP.md`](ROADMAP.md).

| Release | Primary scope | State |
| --- | --- | --- |
| v0.1.x | common XY core, tabular I/O, reusable processing, LSV, XRD, Raman, shared publication rendering/export | complete/released |
| v0.2.x | quantitative core electrochemistry and shared scatter/bar summaries | complete/released as v0.2.0 |
| v0.3.x | FTIR, thermal analysis, basic gas sorption, ICP/composition | complete/released as v0.3.0 |
| v0.4.x | shared fitting, XPS, EIS, quantitative BET, product calibration | complete/released as v0.4.0; GitHub Release published; PyPI deferred |
| v0.5.x | XAS/XANES, FT/WT-EXAFS, EXAFS summaries, structures/geometry/static visualization, basic DFT energetics | complete/released as v0.5.0; GitHub Release published; PyPI deferred |
| v0.6.x | electronic structure and catalysis thermodynamics | complete/released as v0.6.0; GitHub Release published; PyPI deferred |
| v0.7.x | advanced computational visualization | architecture + Blocks 1-2 complete; completion sync #208 active before Block 3 |
| v0.8.x | operando/time-resolved analysis | planned |
| v0.9.x | reproducible batch workflows and first interactive editor | planned |
| v1.0.0 | stable personal catalysis data workbench and local GUI | planned |

Release numbering is a planning boundary, not permission to weaken scientific validation or compatibility requirements.

## Completed release baselines

### v0.1-v0.3

Historical release details are retained in [`RELEASING.md`](RELEASING.md), [`V0_2_PLAN.md`](V0_2_PLAN.md), [`V0_2_RELEASING.md`](V0_2_RELEASING.md), and [`V0_3_RELEASING.md`](V0_3_RELEASING.md).

The reviewed `v0.3.0` tag remains `845ac4c15d399a8816c7ba66d61ea6ec4cc11293`.

### v0.4

The detailed v0.4 scientific contracts and release evidence remain in [`V0_4_PLAN.md`](V0_4_PLAN.md) and [`V0_4_RELEASING.md`](V0_4_RELEASING.md).

Completed scientific scope:

- shared constrained peak fitting — #75/#76;
- XPS preparation — #79/#80;
- constrained XPS fitting — #83/#84;
- XPS plotting/diagnostics — #87/#88;
- EIS — #91/#92;
- quantitative BET — #95/#96;
- product calibration/inverse sample quantification — #99/#100.

Release gates:

- Gate A — #103/#104 — frozen-scope installed-wheel/public-API hardening, merge `ce06abc11559fa7679869fc83a59356735ce6824`;
- Gate B — #105/#106 — distribution/runtime version finalized to `0.4.0`, release commit `bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6`;
- Gate C — #107 — tag `v0.4.0` created and reverse-verified on that exact commit;
- post-tag docs sync — #108/#111 — complete;
- GitHub Release tracking — #112 — completed after user-confirmed publication and post-publication tag/main invariants;
- PyPI publication — #113 — intentionally deferred/closed `not_planned`.

## v0.5 execution status

The reviewed architecture, frozen scope, prior-art decisions, detailed scientific contracts, and release handoff are maintained in [`V0_5_PLAN.md`](V0_5_PLAN.md); release-gate evidence is maintained in [`V0_5_RELEASING.md`](V0_5_RELEASING.md).

### Architecture checkpoint — complete

Issue #115 / PR #116 froze the eight-block v0.5 scientific scope before implementation and confirmed the separation of XAS numerical state, immutable structure state, renderer-neutral visual state, and explicit DFT-energy arithmetic.

### XAS/XANES — complete

Issue #117 / PR #118 delivered explicit energy/eV semantics, caller-controlled energy shifts, measured-point regions, explicit E0 plus pre/post-edge polynomial normalization, fail-closed edge-step state, retained source provenance, explicit E−E0 comparison state, and passive plotting. No automatic oxidation-state or chemistry assignment is performed.

### FT-EXAFS — complete

Issue #119 / PR #120 delivered explicit uniform k-grid requirements, retained transform/window state, complex χ(R), magnitude/real/imaginary/phase views, and passive plotting without hidden interpolation or transform recomputation.

### WT-EXAFS — complete

Issue #121 / PR #122 delivered a separate explicit Cauchy k–R transform with retained complex matrix, k/R grids, k weighting, wavelet order and independent ridge-regression evidence for the EXAFS phase mapping.

### EXAFS fitting-result summaries — complete

Issue #123 / PR #124 delivered a neutral interchange/summary layer for external fit path/shell parameters, uncertainty availability and producer-specific diagnostics without pretending that unlike external statistics are interchangeable.

### Atomic structures and adapters — complete

Issue #125 / PR #126 delivered CatalysisWorkbench-owned immutable structure state and reviewed POSCAR/CONTCAR/CIF/XYZ adapters. `pymatgen-core` is isolated behind the optional `structure` extra rather than becoming public authority or an unconditional base dependency.

### Geometry/coordination/comparison — complete

Issue #127 / PR #129 delivered explicit `PeriodicImage` / `SiteImage` identities, exact distance/angle operations with no hidden minimum-image replacement, caller-bounded cutoff coordination, and caller-mapped structure comparison without automatic site matching or Kabsch alignment.

### Static structure visualization — complete

Issue #130 / PR #131 delivered a renderer-neutral immutable `StructureScene`, explicit atom/bond/cell state, presentation-only colors/radii, caller-visible camera/projection state and passive Matplotlib 3D rendering. `pretty-lattice` was a permissive architecture/UX reference only; no browser/Three.js implementation was copied.

### Basic DFT energetics — complete

Issue #132 / PR #133 delivered immutable explicit-eV energy ledgers, explicit normalization bases/source IDs, same-basis relative energies, generic caller-defined linear combinations, transparent `E(combined)-E(slab)-nE(adsorbate)` adsorption-energy arithmetic, detached reporting tables and passive relative-energy plotting.

Final v0.5 scientific-completion commit: `a7ebd009ec83b0aeb068ad2d2f6712c17a783f1f`.

CHE/free-energy thermodynamics, DOS/PDOS, Bader, COHP/ICOHP, charge-density difference, advanced volumetric rendering, operando mapping, GUI editing and VASP job management remain later-release work.

## v0.5 release handoff

Completed release steps:

```text
#134/#135 completion-state docs sync — complete
    -> Gate A #136/#137 — complete, version retained at 0.4.0
    -> Gate B #138/#139 — complete, exact-wheel candidate finalized at 0.5.0
    -> #140/#141 post-Gate-B docs sync — complete
    -> Gate C #142 — complete; v0.5.0 reverse-verified
    -> GitHub Release #144 — complete; CatalysisWorkbench v0.5.0 published
    -> #143 final post-release docs sync — complete at bed5c6e750a6066baa8daa21492aa9eb90e8bca8
    -> package-registry publication — only if separately reauthorized
```

Gate A final head `fb13cdbf633366a0840f5f2e21af215bee47b133` passed CI #358 / run `32799486710` and reviews `5014277750`, `5014278425` before squash merge `0ffcd7e4a89340d993468039ba83b44bc7638050`.

Gate B final head `b95841ed472aff1fa4d05af7335547ee5c3cd611` passed CI #360 / run `32800514038` and reviews `5014348449`, `5014349058` before squash merge `9400ac0044ac333d2cae228554c08d955a816a4c`. Distribution/runtime version is `0.5.0`.

Gate C / #142 created and reverse-verified `v0.5.0` exactly on `9400ac0044ac333d2cae228554c08d955a816a4c`; the tag must not be moved or recreated. GitHub Release / #144 is publicly published from that existing tag. Final post-release docs sync #143 is complete. PyPI/package-registry publication remains deferred.

## v0.6 execution status

The reviewed v0.6 architecture, scientific semantics, dependency boundaries, implementation order, prior-art/license decisions, and v0.7 handoff are maintained in [`V0_6_PLAN.md`](V0_6_PLAN.md).

### Architecture checkpoint — complete

Issue #146 / PR #147 froze the architecture before any v0.6 scientific implementation. The checkpoint was merged at `3803e014376a7edb22d6a9a5b6480541742499be` after exact-head CI and final-head scientific/API/license review.

The frozen scientific implementation order is:

1. electronic-structure + volumetric semantics/adapters;
2. DOS/PDOS processing + passive plotting;
3. band-center analysis;
4. Bader result parsing + charge accounting;
5. COHP/ICOHP parsing + bonding analysis;
6. geometry–bonding correlation;
7. CHE/free-energy thermodynamics;
8. free-energy diagrams;
9. charge-density-difference calculation + lattice/grid validation.

The architecture establishes shared energy-reference, spin, site/orbital projection, normalization, provenance, lattice/grid and component semantics before descriptor-specific processing. CHE extends the reviewed v0.5 DFT-energy foundation instead of creating a second incompatible energy model.

### Architecture central-document sync — complete

Issue #148 / PR #149 synchronized the completed architecture checkpoint into central documentation at `aac05d4426c15c8932c608d07ef42e4dc07b09ce` before scientific implementation began.

### Electronic-structure + volumetric semantics/adapters — complete

Issue #150 / PR #151 delivered CatalysisWorkbench-owned immutable `ElectronicEnergyAxis`, `DOSProjection`, `DOSChannel`, `ElectronicDOS`, and `VolumetricGrid` state plus lazy `pymatgen-core` `vasprun.xml`/CHGCAR adapters. Source-native energy/Fermi state, non-spin `total` versus collinear `up`/`down`, deterministic site/orbital projection identity, canonical volumetric component ordering, and CHGCAR electron-number-density conversion are explicit. The installed optional-backend regression verified current `pymatgen-core` parser grid semantics before applying the reviewed `parsed_grid / V_cell` conversion.

Block-1 final head `229fa5c3ec9225bde8afd1931cefe0dea521eabe` passed CI #376 / run `32808329764` and final-head reviews `5014903632`, `5014904435` before squash merge `58023070bf7f642748b69e99281a5ed7ed4d40df`.

### Block-1 completion-state sync — complete

Issue #152 / PR #153 synchronized the merged block-1 state into central documentation at `39df1101d1ed7dde5c4ab6d264b8796c27c97620` before block 2 began.

### DOS/PDOS processing + passive plotting — complete

Issue #154 / PR #155 delivered immutable `DOSTrace` derived state, explicit channel selection and compatible aggregation, explicit idempotent `E-E_F` referencing, source-grid-only crop, detached reporting, and passive `FigureSpec` DOS plotting. Scientific densities remain non-negative; spin-down mirroring is renderer-only. Cross-source source-native overlays fail closed, and aggregation provenance is canonicalized to source channel order.

Block-2 final head `1e18c838f0ce0203ae0f841fbde3786c00970d16` passed CI #388 / run `32810513894` and final-head reviews `5015058136`, `5015059007` before squash merge `09e63e72e1b79d8c151c97769d4bfbd2fb6a366f`.

### Block-2 completion-state sync — complete

Issue #156 / PR #157 synchronized the merged block-2 state into central documentation at `c597fdaba7509a0c6c4cf6088c7367c94cec0547` before block 3 began.

### Band-center / DOS first-moment analysis — complete

Issue #158 / PR #159 delivered CatalysisWorkbench-owned immutable `BandCenterResult` state and explicit first-moment analysis on reviewed `DOSTrace` input. Integration uses retained source-grid points with explicit caller window and denominator tolerance; no hidden interpolation, smoothing, broadening, normalization, Fermi shift, projection selection, or spin recombination occurs. Requested versus actually integrated endpoints, numerator/denominator, integration method, energy reference, normalization basis, and exact trace/channel/projection/spin provenance remain auditable.

Block-3 final head `415258a2ff7547af4fd9b2717404d06c341c0de1` passed CI #397 / run `32814966504` and final-head reviews `5015455765`, `5015456841` before squash merge `cdbc4822592cf43033af1f0242793d5912098b7c`.

### Block-3 completion-state sync — complete

Issue #160 / PR #161 synchronized the merged block-3 state into central documentation at `c1a6ed407f3081dec2da535e4e7d5b571f9a8012` before block 4 began.

### Bader result parsing + explicit charge accounting — complete

Issue #162 / PR #163 delivered CatalysisWorkbench-owned immutable raw and reference-derived Bader state plus a narrow standard `ACF.dat` reader. Raw producer `CHARGE` values are retained explicitly as `bader_electrons`; optional `AtomicStructure` mapping is direct-order only with a caller-supplied Cartesian tolerance; and charge accounting derives `electron_transfer = N_Bader - N_reference` and `partial_charge = N_reference - N_Bader` only from caller-supplied reference populations and provenance. No external partitioner is executed, no POTCAR/ZVAL or oxidation state is inferred, and malformed/reordered/incompatible state fails closed.

Block-4 final head `f436186df908a8185e196f120d90ae392ee62fc6` passed CI #405 / run `32818958204` and final-head reviews `5015794214`, `5015796101` before squash merge `e2b38c243a664913fb31fca6ed31744e7190d957`.

### Block-4 completion-state sync — complete

Issue #164 / PR #165 synchronized the merged block-4 state into central documentation at `308ca1243f60bd28b981e3d51dbff3532de16e28` before block 5 began.

### COHP/ICOHP parsing + explicit bonding analysis — complete

Issue #166 / PR #167 delivered CatalysisWorkbench-owned immutable source-sign COHP/ICOHP state plus lazy `pymatgen-core` LOBSTER adapters. LOBSTER energies remain explicitly already Fermi-referenced with numerical zero at `E_F`; no second Fermi shift or hidden `-COHP/-ICOHP` inversion occurs. Physical `total` versus `up/down` spin state, deterministic bond/orbital identities, exact `number_of_bonds` multiplicity, explicit ICOHP spin summation, source-order selectors, and detached reporting remain auditable. Unsupported COOP/COBI/multi-center/LCFO variants and incomplete spin state fail closed; no strongest-bond threshold or chemistry inference is introduced.

Block-5 final head `c3bcf5caea142ee4165ebc45ae5a64ef7b7b9cde` passed CI #417 / run `32822387619` and final-head reviews `5016125861`, `5016128385` before squash merge `415f8de126bac6ad2f6086f68152c472fb4064f2`.

### Block-5 completion-state sync — complete

Issue #168 / PR #169 synchronized the merged block-5 state into central documentation at `8cc7ed82497ee6245a65091b88b61eb9153128c5` before block 6 began.

### Geometry–bonding correlation — complete

Issue #170 / PR #171 delivered CatalysisWorkbench-owned immutable `CorrelationPoint`, `CorrelationExclusion`, and `CorrelationDataset` state with explicit x/y definitions and units, exact source keys/digests, caller-visible mapping provenance, deterministic scientific identity, and separate explicit exclusion records. The narrow ICOHP bond-length convenience path preserves source-sign ICOHP, requires explicit physical spin selection, canonicalizes an explicitly selected spin set to source order, and retains `number_of_bonds` only as provenance. No automatic atom/bond matching, silent omission, statistics/regression, ranking, or causal interpretation is introduced.

Block-6 final head `98222d17513db661ead7945ae212d665458a8d00` passed CI #424 / run `32825053421` and final-head reviews `5016939992`, `5016943168` before squash merge `f66bcae9bd254cf3abe12e8f161b0a38080c7ad3`.

### Block-6 completion-state sync — complete

Issue #172 / PR #173 synchronized the merged block-6 state into central documentation at `9d6d8e2868f38336ba1a8e25adab3fd3b787df1a` before block 7 began.

### CHE / free-energy thermodynamics — complete

Issue #174 / PR #175 delivered explicit thermodynamic entries that reference the reviewed v0.5 `DFTEnergyLedger`, caller-selected free-energy recipes, retained ZPE/thermal/entropy/additional-correction availability and provenance, explicit SHE/RHE Computational Hydrogen Electrode state, and products-positive/reactants-negative reaction free-energy arithmetic. RHE input is explicitly converted to SHE before the common CHE equation so pH cancellation arises algebraically rather than through a hidden special case. No thermochemical database, pathway inference, Pourbaix/microkinetic layer, plotting, or new runtime dependency is introduced.

Block-7 final head `3d008e98281ec95a4f6fd7310db18be97f8a36f3` passed CI #434 / run `32833845931` and final-head reviews `5017464310`, `5017466412` before squash merge `e25610d56eb414ac6aedae07874042d3f4edd194`.

### Block-7 completion-state sync — complete

Issue #176 / PR #177 synchronized the merged block-7 state into central documentation at `917500868591fe6793172fec44d943b8a8a36930` before block 8 began.

### Free-energy diagrams — complete

Issue #178 / PR #179 delivered CatalysisWorkbench-owned immutable ordered free-energy diagram state with exact source provenance, explicit absolute versus caller-referenced `G_i - G_ref` semantics, retained Block-7 CHE context, strict multi-series compatibility checks, detached reporting, and passive `FigureSpec`/Matplotlib rendering of retained horizontal levels and straight connectors. There is no implicit first-state zeroing, CHE/pH/potential recomputation in the renderer, pathway discovery, hidden state removal, transition-state/barrier construction, or new runtime dependency.

Block-8 final head `d2046565ab4ab490ed3169e02c03b2d369b4ad74` passed CI #439 / run `32836733241` and final-head reviews `5017795338`, `5017796858` before squash merge `0d8dd67f716c47b4c611dd56cfc0cb243db3fb29`.

### Block-8 completion-state sync — complete

Issue #180 / PR #181 synchronized the merged block-8 state into central documentation at `cec7a9eae1ae256a82ee72b74a80039c6b164bda` before block 9 began.

### Charge-density difference + strict co-registration validation — complete

Issue #182 / PR #183 delivered explicit co-registered volumetric difference arithmetic on the reviewed `VolumetricGrid` foundation. Caller-visible coefficients, exact grid shape/unit/component semantics, explicit registration identity, and direct lattice-matrix compatibility under a retained absolute tolerance are validated before arithmetic. Different combined/subsystem atomic structures are permitted only while their exact structure/grid provenance remains retained; no interpolation, resampling, origin shift, remapping, alignment, supercell conversion, component conversion, unit conversion, or CHGCAR re-normalization is performed.

Block-9 final head `5312c16cfd877a6fab1346c31e9f0a252be45f57` passed CI #447 / run `32839258539` and final-head reviews `5018036286`, `5018037530` before squash merge `f47d2165f282c8fe2745d1bd50ed32886b0f2054`.

### v0.6 release completion — complete

All nine v0.6 scientific blocks were synchronized through #184/#185 before release hardening. Gate A #186/#187, Gate B #188/#189, Gate C #192, GitHub Release #193, and final post-release documentation synchronization #195/#196 are complete. The released tag remains `v0.6.0 -> c7793b309f41d174c14534bd6d4acdacc2a57636`; distribution/runtime version is `0.6.0`; the public GitHub Release is published; PyPI remains deferred.

## v0.7 execution status

The reviewed v0.7 architecture, scientific/visualization semantics, dependency boundaries, implementation order, prior-art/license decisions, testing strategy, and release handoff are maintained in [`V0_7_PLAN.md`](V0_7_PLAN.md).

### Architecture checkpoint — complete

Issue #197 / PR #198 froze the seven-block v0.7 architecture before implementation and merged at `a854b5d4ab6168d857f9f783c9b4c1827e064972`. Final head `d15fd0ab0d86901846c46d7cd09837c9dbf8d9d7` passed CI #460 / run `32850343815` and exact-head architecture/scientific plus API/compatibility/license reviews `5019179196`, `5019180975`.

The frozen implementation order is:

1. shared scalar-field state + renderer-neutral volumetric scene/slice/isosurface specifications;
2. charge-density-difference + electron-density + ELF visualization;
3. band-structure state/adapters + passive band plotting;
4. PROCAR projection processing + fat-band plotting;
5. LOCPOT planar-potential/work-function processing + plotting;
6. NEB/barrier retained state + passive plotting;
7. advanced volumetric 3D backend/rendering/export.

### Architecture central-document sync — complete

Issue #199 / PR #201 synchronized the completed v0.7 architecture checkpoint into central documentation at `7f04e1312a67417ea9b1ddd10482722c599040d4` before Block 1 began.

### Shared scalar-field + renderer-neutral volumetric scene foundation — complete

Issue #202 / PR #203 delivered immutable unit-generic `ScalarField` state, exact source-grid `ScalarFieldSlice` state, full-lattice fractional-to-Cartesian grid/slice geometry including skew cells, narrow released-v0.6 adapters from `VolumetricGrid` and `ChargeDensityDifferenceResult`, deeply frozen provenance/metadata, explicit renderer-neutral `IsosurfaceLayerSpec`, `SliceLayerSpec`, and `VolumetricScene`, plus installed-wheel/public-API smoke and domain documentation in [`VOLUMETRIC_VISUALIZATION.md`](VOLUMETRIC_VISUALIZATION.md). The implementation performs no hidden normalization, unit conversion, interpolation, averaging, resampling, alignment, origin shift, threshold inference, mesh extraction, or renderer-backend import.

Block-1 final head `db0526cfca5b6cc540ac8198b9fd2a02754ba391` passed CI #474 / run `32855491587` and final-head reviews `5019699984`, `5019702262` before expected-head squash merge `4a101337f7822c4d687dd2edf3cc12168278619b`.

### Block-1 completion-state sync — complete

Issue #204 / PR #205 synchronized the merged Block-1 state into central documentation at `ff263c20b8986c65a47dfdd544ca712a8e3f3cd8` before Block 2 began.

### Charge-density-difference + electron-density + ELF visualization — complete

Issue #206 / PR #207 delivered technique-level visualization on the reviewed Block-1 scalar-field and scene foundation. Signed charge-density-difference scenes consume an existing reviewed `ChargeDensityDifferenceResult` without repeated arithmetic. Total electron-density scenes preserve the exact reviewed `VolumetricGrid.total` values, canonical `1/angstrom^3` unit and caller-supplied finite thresholds without normalization, clipping, smoothing, unit conversion, interpolation or grid transformation. Lazy optional `read_elfcar_field(...)` returns one exact dimensionless ELF `ScalarField` per explicit physical channel, maps current `spin_up` / `spin_down` directly, version-guards historical direct-spin `total` / `diff` semantics without ever applying CHGCAR total/magnetization interpretation, and fails closed on ambiguous/unexpected/nonfinite/mismatched state. Passive Matplotlib slice rendering uses exact source-grid values, explicit display ranges, and deterministic fractional/full-lattice or intrinsic-plane geometry including skew cells. No mesh extraction, PyVista/VTK/scikit-image dependency, or Block-7 3-D renderer call is introduced.

Block-2 final head `c3a952f9aad9535cfc7b2a88413527fd40487cfe` passed CI #486 / run `32862918547` with Ruff, 1009-test full pytest, fresh-wheel/public-API audits, real current optional-backend ELFCAR round-trip and documented examples, plus final-head reviews `5020510393`, `5020512056`, before expected-head squash merge `b9e3e27c667df9afc6060e387ad0ca4510a73d78`.

### Current Block-2 completion-state sync

Issue #208 is the docs-only checkpoint after Block 2. It records merged Block-2 reality in central documentation without adding Block-3 implementation. Block 3 begins only after #208 merges and `main`, immutable `v0.6.0`, distribution/runtime `0.6.0`, public v0.6 GitHub Release, and PyPI-deferred state are reverified.

## Mandatory development loop

Every scientific feature follows:

```text
prior-art/license refresh
    -> implementation + regression tests
    -> Draft PR
    -> exact-head CI
    -> scientific/API/compatibility review
    -> direct fixes on the feature branch
    -> fresh exact-head CI after every head change
    -> second formal review on final exact head
    -> Ready
    -> behind=0 / mergeable / review threads=0
    -> expected-head squash merge
    -> main verification
    -> issue closure
```

A feature is not complete because code exists or an old CI run passed. Completion requires the final exact head to satisfy the scientific contract, public API/compatibility expectations, CI, documentation and Issue acceptance criteria.

For release-hardening/version gates, use the same exact-head discipline with release/API/packaging/version review as appropriate.

## Prior-art rule

Before coding a new scientific or visualization feature:

1. survey comparable open-source GitHub/scientific-Python projects;
2. identify useful equations, processing patterns, API/data-model ideas, visualization approaches and regression-test cases;
3. record licenses;
4. distinguish reference-only use from dependencies or copied/adapted implementation;
5. record decisions in the relevant Issue/module documentation and `REFERENCES.md` where safely maintained.

Permissive prior art is not copied automatically. GPL, mixed-provenance, missing-license or otherwise restrictive projects may be reference-only sources, but implementation reuse must respect license compatibility.

## Scientific and API guardrails

Across releases:

- units, reference states, normalization bases, sign conventions, fit windows, stoichiometry, constraints and denominator bases are explicit rather than inferred from display labels;
- numerical processing and visualization remain separate responsibilities;
- stable keys, not display labels, address sample/component-specific state;
- derived results retain deterministic source identity and sufficient analysis state to remain auditable;
- scientific incompatibilities fail explicitly rather than being silently aligned, converted, clipped, renormalized, smoothed or corrected;
- shared primitives are extended centrally instead of creating technique-specific duplicate stacks;
- public import surfaces remain deliberate and installed-wheel smoke tests protect them;
- existing reviewed behavior remains compatible unless a breaking change is separately planned and reviewed.

## Merge gate

Before Ready/squash merge, confirm at minimum:

- Issue scope and acceptance criteria are satisfied;
- prior-art/license decisions are recorded when functionality is added;
- regression tests cover hand-verifiable behavior and explicit failure modes;
- Ruff/full pytest pass;
- package/fresh-wheel public-API smoke passes when exercised by CI;
- formal review has no unresolved blockers;
- second review is performed after all fixes on the final exact head for scientific source changes;
- docs describe the behavior actually present in that head;
- behind=0, mergeable=true, unresolved review threads=0;
- merge uses the same head SHA that passed final CI/review.

After squash merge, re-read `main`. When connector visibility does not expose a main-push CI run, do not mislabel an older PR run as main CI evidence.

## Documentation roles

- [`../README.md`](../README.md): user-facing overview, installation, public capability summary and links.
- [`MASTER_PLAN.md`](MASTER_PLAN.md): project-wide execution order, checkpoint summary, governance and quality gates.
- [`ROADMAP.md`](ROADMAP.md): long-range release scope; not a per-commit log.
- [`V0_7_PLAN.md`](V0_7_PLAN.md): v0.7 architecture, frozen seven-block dependency order, scientific/visualization semantics, prior-art/license decisions, testing strategy, and release handoff.
- [`VOLUMETRIC_VISUALIZATION.md`](VOLUMETRIC_VISUALIZATION.md): reviewed v0.7 Block-1 scalar-field/source-grid/renderer-neutral foundation and Block-2 density/ELF/exact-slice visualization contracts.
- [`V0_6_PLAN.md`](V0_6_PLAN.md): retained v0.6 architecture, frozen dependency order, scientific/API semantics, prior-art/license decisions, test strategy, and v0.7 handoff.
- [`V0_6_RELEASING.md`](V0_6_RELEASING.md): retained v0.6 Gate A/B/C procedure and release evidence.
- [`V0_5_PLAN.md`](V0_5_PLAN.md): v0.5 architecture, dependency order, scientific completion state and release handoff.
- [`V0_5_RELEASING.md`](V0_5_RELEASING.md): v0.5 Gate A/B/C procedure and release evidence.
- [`V0_4_PLAN.md`](V0_4_PLAN.md) / [`V0_4_RELEASING.md`](V0_4_RELEASING.md): retained v0.4 scientific/release history.
- technique documents such as [`XAS.md`](XAS.md), [`EXAFS.md`](EXAFS.md), [`WT_EXAFS.md`](WT_EXAFS.md), [`STRUCTURE_GEOMETRY.md`](STRUCTURE_GEOMETRY.md), [`STRUCTURE_VISUALIZATION.md`](STRUCTURE_VISUALIZATION.md), [`DFT_ENERGETICS.md`](DFT_ENERGETICS.md), [`GEOMETRY_BONDING_CORRELATION.md`](GEOMETRY_BONDING_CORRELATION.md), [`CHE_THERMODYNAMICS.md`](CHE_THERMODYNAMICS.md), [`FREE_ENERGY_DIAGRAMS.md`](FREE_ENERGY_DIAGRAMS.md), and [`CHARGE_DENSITY_DIFFERENCE.md`](CHARGE_DENSITY_DIFFERENCE.md): reviewed domain contracts.
- [`REFERENCES.md`](REFERENCES.md): long-lived prior-art reference survey; release-specific architecture decisions may additionally be frozen in the corresponding `V0_X_PLAN.md`.
- GitHub Issues: active acceptance criteria.
- GitHub Pull Requests: concrete diff, review evidence, CI state and merge decision.

## State-maintenance rule

After each merged scientific Issue, update only documentation whose statements became false or materially incomplete. Before starting any next phase, verify:

- live `main` HEAD;
- open Issues/PRs;
- current release plan;
- public capability claims;
- preceding Issue closure/completion;
- version/tag/publication boundaries.

Issue #208 is the active v0.7 Block-2 completion-state documentation checkpoint. After it merges, reverify `main`, Issue #208 closure, immutable `v0.6.0 -> c7793b309f41d174c14534bd6d4acdacc2a57636`, distribution/runtime version `0.6.0`, public v0.6 GitHub Release state, and PyPI-deferred state. Then start v0.7 Block 3 (band-structure state/adapters + passive band plotting) from that exact verified `main` baseline using [`V0_7_PLAN.md`](V0_7_PLAN.md) and the completed v0.7 foundations.