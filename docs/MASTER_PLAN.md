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

Checkpoint date: 2026-08-26.

- Repository: `xcwang3333-cloud/catalysis-workbench`.
- Stable integration branch: `main`.
- Exact architecture baseline: `fa7baaf8ce68369b0e732faf4e7621a818db92b6`, the Issue #249 / PR #250 v0.8 architecture squash merge; post-merge CI #550 / run `32920821932` passed on that exact `main` head.
- Current verified implementation head: `45d0515dd5c1c70f15f4d5cd76ba2a359dc66bb2`, the expected-head squash merge of v0.8 Block 1 through Issue #253 / PR #254; post-merge CI #562 / run `32922349620` passed on that exact `main` head.
- Distribution/runtime version is `0.7.0`.
- Released tag `v0.7.0 -> e3062fc12c794f54c7b7613875ec73608a587a59` is immutable and independently reverse-verified.
- The public GitHub Release `CatalysisWorkbench v0.7.0` is published from that existing verified tag.
- Final v0.7 publication-evidence synchronization completed through Issue #243 / PR #244 at `bd3d69ed90f5f7ea2cdc6b950a6e9f33ca2fc338`.
- All seven v0.7 scientific blocks, Gate A, Gate B, Gate C, GitHub Release publication, and publication-evidence synchronization are complete.
- `v0.5.0 -> 9400ac0044ac333d2cae228554c08d955a816a4c` remains immutable; its public GitHub Release is complete.
- `v0.4.0 -> bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6` remains immutable; its public GitHub Release is complete.
- PyPI/package-registry publication remains explicitly deferred.
- v0.7 architecture checkpoint: Issue #197 / PR #198 — complete at `a854b5d4ab6168d857f9f783c9b4c1827e064972`.
- v0.7 architecture central-document synchronization: Issue #199 / PR #201 — complete at `7f04e1312a67417ea9b1ddd10482722c599040d4`.
- v0.7 Block 1, shared scalar-field + renderer-neutral volumetric scene foundation: Issue #202 / PR #203 — complete at `4a101337f7822c4d687dd2edf3cc12168278619b`.
- Block-1 final head `db0526cfca5b6cc540ac8198b9fd2a02754ba391` passed CI #474 / run `32855491587` and exact-head reviews `5019699984`, `5019702262`; unresolved review threads were zero and the PR was behind=0 / mergeable=true before squash merge.
- v0.7 Block-1 completion-state synchronization: Issue #204 / PR #205 — complete at `ff263c20b8986c65a47dfdd544ca712a8e3f3cd8`.
- v0.7 Block 2, charge-density-difference + electron-density + ELF visualization: Issue #206 / PR #207 — complete at `b9e3e27c667df9afc6060e387ad0ca4510a73d78`.
- Block-2 final head `c3a952f9aad9535cfc7b2a88413527fd40487cfe` passed CI #486 / run `32862918547` and exact-head reviews `5020510393`, `5020512056`; unresolved review threads were zero and the PR was behind=0 / mergeable=true before expected-head squash merge.
- v0.7 Block-2 completion-state synchronization: Issue #208 / PR #209 — complete at `bf80f9bb3ffa1d1a764ff71a5202c05e4b5e827e`.
- v0.7 Block 3, band-structure state/adapters + passive band plotting: Issue #210 / PR #211 — complete at `4a4b1329cbd8153f868cdc2d353dfc0c613778a4`.
- Block-3 final head `b1f1dca77b469f6d3fb4524f7c51f719fa9350e4` passed CI #490 / run `32867366543` (Ruff, full pytest, fresh-wheel/public-API smoke, v0.6 + v0.7 Block-1/2/3 installed audits, optional structure/electronic/bonding/ELFCAR/band adapters including current `pymatgen-core` line-mode KPOINTS and reciprocal `2*pi` convention smoke, and documented examples) and exact-head reviews `5020939345`, `5020940558`; unresolved review threads were zero and the PR was behind=0 / mergeable=true before expected-head squash merge.
- v0.7 Block-3 completion-state synchronization: Issue #212 / PR #213 — complete at `fa29a40f465fa41afa7620d1dad9cce22720ee06`.
- v0.7 Block 4, PROCAR projection processing + fat-band plotting: Issue #214 / PR #216 — complete at `28852bb7ef6f7c23319d5a6442659f55516eed59`.
- Block-4 final head `fef79825073ecb6bf5be834db8bd441c69f99191` passed CI #504 / run `32872508844` (Ruff, full pytest, fresh-wheel/public-API smoke, v0.6 + v0.7 Block-1/2/3/4 installed audits, optional structure/electronic/bonding/ELFCAR/band/PROCAR adapter audits including current `pymatgen-core.Procar` five-decimal k-point and raw terminal-`tot` omission behavior, and documented examples) and exact-head reviews `5021426413`, `5021427725`; unresolved review threads were zero and the PR was behind=0 / mergeable=true before expected-head squash merge.
- v0.7 Block-4 completion-state synchronization: Issue #217 / PR #218 — complete at `d1bd5d710f4353b76bf1dd3f3e0a9a49a288353d`.
- v0.7 Block 5, LOCPOT planar-potential/work-function processing + plotting: Issue #219 / PR #220 — complete at `ab4b8c6f5445920124c2a61799e189ae25b8d404`.
- Block-5 final head `34cf2253bf9744149d498edecf186d5fe04e6afe` passed CI #515 / run `32876765592` (Ruff, 1057 tests, fresh-wheel/public-API smoke through v0.7 Block 5, optional structure/electronic/bonding/ELFCAR/band/PROCAR/LOCPOT adapter audits including current `pymatgen-core.Locpot` exact-value round-trip and skew-cell normal-coordinate behavior, and documented examples) and exact-head reviews `5021836289`, `5021837599`; unresolved review threads were zero and the PR was behind=0 / mergeable=true before expected-head squash merge.
- v0.7 Block-5 completion-state synchronization: Issue #221 / PR #222 — complete at `51b04e9b7a63b200c6679d83730e49451f9bee64`.
- v0.7 Block 6, explicit NEB image-energy state + discrete barrier plotting: Issue #223 / PR #224 — complete at `7a80b99bc513b7a6b33d1a9481ff25c1c4d95b85`.
- Block-6 final head `5aa1926e7125c49950589553b8463e5ecfb936fd` passed CI #521 / run `32879644216` (Ruff, full pytest, fresh-wheel/public-API smoke through v0.7 Block 6, all prior optional structure/electronic/bonding/ELFCAR/band/PROCAR/LOCPOT audits, and documented examples) and exact-head reviews `5022088404`, `5022089761`; unresolved review threads were zero and the PR was behind=0 / mergeable=true before expected-head squash merge.
- v0.7 Block-6 completion-state synchronization: Issue #225 / PR #226 — complete at `0e433d55f7d08632e590a9be495cb10128a7a0d6`.
- v0.7 Block 7, advanced volumetric 3D rendering + static export: Issue #227 / PR #228 — complete at `24d3a8e67e4ef996125e575308b88ab6f9532448`.
- Block-7 final head `6dc1472b9157151d67b20f8b359542e103d5f6c2` passed CI #526 / run `32882938623` (Ruff, full pytest, base fresh-wheel/public-API smoke through v0.7 Block 7, all prior optional structure/electronic/bonding/ELFCAR/band/PROCAR/LOCPOT audits, documented examples, and separate fresh-wheel `[volumetric3d]` PyVista/VTK headless skew-cell render/export smoke) and exact-head reviews `5022437132`, `5022439286`; unresolved review threads were zero and the PR was behind=0 / mergeable=true before expected-head squash merge.
- [`V0_7_PLAN.md`](V0_7_PLAN.md) remains the release-specific authority for the frozen seven-block v0.7 scope, scientific/visualization contracts, dependency order, prior-art/license decisions, testing strategy, and release boundaries.
- [`VOLUMETRIC_VISUALIZATION.md`](VOLUMETRIC_VISUALIZATION.md) records the reviewed Block-1 scalar-field/source-grid/renderer-neutral foundation and Block-2 charge-density-difference, electron-density, ELFCAR/ELF, and exact-slice visualization contracts.
- [`BAND_STRUCTURE.md`](BAND_STRUCTURE.md) records the reviewed Block-3 reciprocal-space, physical-spin, explicit Fermi-reference, VASP line-mode adapter, path-discontinuity, and passive band-plotting contract.
- [`PROCAR_FAT_BANDS.md`](PROCAR_FAT_BANDS.md) records the reviewed Block-4 projection-state, current-backend orbital semantics, explicit site/orbital aggregation, caller-visible compatibility tolerances, SOC/vector fail-closed boundary, and presentation-only fat-band contract.
- [`LOCPOT_WORK_FUNCTION.md`](LOCPOT_WORK_FUNCTION.md) records the reviewed Block-5 local-potential scalar-field, skew-cell planar-average geometry, explicit vacuum-window/Fermi compatibility, transparent work-function arithmetic, passive plotting, and optional-backend boundaries.
- [`NEB_BARRIERS.md`](NEB_BARRIERS.md) records the reviewed Block-6 exact image-order/path state, ordinal/explicit reaction coordinates, explicit-reference energies, discrete retained-image barrier arithmetic, passive plotting, and no-spline/no-optimizer boundaries.
- [`VOLUMETRIC_3D.md`](VOLUMETRIC_3D.md) records the reviewed Block-7 optional PyVista/VTK backend, full-lattice skew-cell geometry, explicit isosurface/exact-slice/fractional-clipping semantics, retained structure/camera mapping, backend-hidden result state, and static headless PNG-export boundary.
- All seven v0.7 implementation blocks are complete.
- Post-release maintenance Issue #245 / PR #246 is complete at `9235e34046d9b07e219393c97f60bfadf817ed71`; `symmetric_color_limits()` is backwards-compatible future v0.8 heatmap groundwork and is not a v0.8 data-model implementation.
- v0.8 architecture checkpoint Issue #249 / PR #250 is complete at `fa7baaf8ce68369b0e732faf4e7621a818db92b6`.
- v0.8 Block 1 shared immutable operando-stack foundation is complete through Issue #253 / PR #254 at merge `45d0515dd5c1c70f15f4d5cd76ba2a359dc66bb2`; final head `eadf5b2e6630b137922f365a88f4b9ef3c43b12b` passed CI #561 / run `32922150384` and formal reviews `5026150379`, `5026170031` with zero unresolved threads, followed by successful post-merge main CI #562 / run `32922349620`.
- v0.8 Block 2 — exact measured-point operations, derived traces, and explicit cross-modal comparison — is the next scientific implementation work package. No v0.7.1, tag, release, or package-registry action is implied.

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
| v0.7.x | advanced computational visualization | complete/released as v0.7.0; GitHub Release published; post-release color-limit maintenance #245/#246 complete; PyPI deferred |
| v0.8.x | operando/time-resolved analysis | architecture frozen; Block 1 complete; Block 2 next |
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

Block-2 final head `c3a952f9aad9535cfc7b2a88413527fd40487cfe` passed CI #486 / run `32862918547` and final-head reviews `5020510393`, `5020512056` before expected-head squash merge `b9e3e27c667df9afc6060e387ad0ca4510a73d78`.

### Block-2 completion-state sync — complete

Issue #208 / PR #209 synchronized the merged Block-2 state into central documentation at `bf80f9bb3ffa1d1a764ff71a5202c05e4b5e827e` before Block 3 began.

### Band-structure state, VASP adapter, and passive plotting — complete

Issue #210 / PR #211 delivered CatalysisWorkbench-owned immutable band-structure state with exact ordered reciprocal k-points, explicit full reciprocal-lattice matrix and `2*pi` convention, exact physical `total` or complete collinear `up/down` channels, source band index/order, explicit path segments and source labels, retained source Fermi/reference state, periodic structure provenance and deterministic digests. Path distance uses the retained full reciprocal matrix literally and excludes discontinuity jumps; it never inserts or removes `2*pi`. `reference_band_structure_to_fermi(...)` performs only the explicit retained `E - E_F` transformation and is idempotent; neither parser nor renderer shifts energies implicitly. The lazy optional `read_vasprun_band_structure(...)` supports standard reciprocal-coordinate line-mode VASP `KPOINTS` plus `vasprun.xml`, maps physical spin from VASP `ISPIN`, validates every source path point against the explicit line-mode interpolation, and fails closed on hybrid/uniform+line mismatches, unsupported layouts, SOC/noncollinear state, or ambiguous spin semantics. Passive Matplotlib plotting renders every retained band/spin/segment separately so discontinuities are never connected and no gap, metallicity, occupation, symmetry path or band reconnection is inferred. The reviewed domain contract is recorded in [`BAND_STRUCTURE.md`](BAND_STRUCTURE.md), with no new runtime dependency or Block-4 PROCAR implementation.

Block-3 final head `b1f1dca77b469f6d3fb4524f7c51f719fa9350e4` passed CI #490 / run `32867366543` with Ruff, full pytest, fresh-wheel/public-API audits, current optional-backend line-mode KPOINTS/reciprocal-convention smoke and documented examples, plus final-head reviews `5020939345`, `5020940558`, before expected-head squash merge `4a4b1329cbd8153f868cdc2d353dfc0c613778a4`.

### Block-3 completion-state sync — complete

Issue #212 / PR #213 synchronized the merged Block-3 state into central documentation at `fa29a40f465fa41afa7620d1dad9cce22720ee06` before Block 4 began.

### PROCAR projection processing + fat-band plotting — complete

Issue #214 / PR #216 delivered CatalysisWorkbench-owned immutable PROCAR projection state explicitly bound to one reviewed Block-3 `BandStructureState`, which remains the sole energy/path/reference authority. Projection channels retain canonical `(band, kpoint, site, orbital)` order, exact physical-spin/site/orbital provenance, finite non-negative dimensionless weights and deterministic digests. `aggregate_band_projection(...)` requires explicit physical spin, source site indices and exact retained orbital labels, canonicalizes request identity to retained source order, and performs only the selected sum with no hidden element/orbital grouping, spin summation, normalization or thresholding. Direct `AggregatedBandProjection` construction fails closed if site indices are not in retained source order or if supplied site keys/elements do not exactly match the associated `AtomicStructure`.

The lazy optional `read_procar_projection(...)` accepts one ordinary non-SOC PROCAR path, binds it to the reviewed Block-3 band source, exposes caller-visible `kpoint_atol` / `energy_atol_ev`, validates exact band/site/orbital/spin compatibility and does not reorder k-points, reconstruct paths, pad bands, replace energies or collapse SOC/vector state. Current `pymatgen-core.Procar` behavior is retained truthfully: parsed k-points are rounded to five decimals and the raw terminal PROCAR `tot` header/column is removed by the backend, so CatalysisWorkbench retains only backend-exposed `parsed.orbitals`, records `raw_terminal_tot_retained=False`, and never reconstructs or normalizes against that omitted total. A sole backend channel maps to physical `total` for a non-spin band source; collinear spin requires complete `up/down`.

Passive `plot_fat_band(...)` obtains x coordinates only from Block-3 `band_path_coordinates(...)`, y coordinates only from retained Block-3 band energies, and applies projection weight only through caller-visible presentation scaling. Discontinuous path segments remain separate; marker area, marker, alpha, color and base-line width do not change scientific state. The reviewed domain contract is recorded in [`PROCAR_FAT_BANDS.md`](PROCAR_FAT_BANDS.md). PyProcar remains GPLv3 reference-only and no new runtime dependency was added.

Block-4 final head `fef79825073ecb6bf5be834db8bd441c69f99191` passed CI #504 / run `32872508844` with Ruff, full pytest, fresh-wheel/public-API audits, current optional-backend PROCAR parser/conversion smoke and documented examples, plus final-head reviews `5021426413`, `5021427725`, before expected-head squash merge `28852bb7ef6f7c23319d5a6442659f55516eed59`.

### Block-4 completion-state sync — complete

Issue #217 / PR #218 synchronized the merged Block-4 state into central documentation at `d1bd5d710f4353b76bf1dd3f3e0a9a49a288353d` before Block 5 began.

### LOCPOT planar potential + explicit work-function processing — complete

Issue #219 / PR #220 delivered exact local-potential processing on the reviewed Block-1 scalar-field foundation. The lazy optional `read_locpot_field(...)` preserves one finite VASP LOCPOT scalar grid exactly as `ScalarField(field_kind="local-potential", value_unit="eV")`, retains parser/source provenance and optional caller-visible `calculation_id`, and performs no CHGCAR-style volume normalization, unit conversion, smoothing, clipping, electrostatic-zero shift, dipole correction, interpolation, resampling or alignment. Current optional-backend smoke verifies `pymatgen-core.Locpot` write/read and exact-value preservation.

`planar_average_potential(...)` performs only the arithmetic mean over the two source-grid axes orthogonal to the caller-selected lattice/grid axis. Fractional coordinates remain exact source indices `i/n`; for skew cells the physical normal repeat height is `V_cell / A_opposite_face`, not the norm of the selected lattice vector. `vacuum_level_from_profile(...)` uses only an explicit caller-supplied half-open retained-source index window and initially supports the explicit `mean` statistic; the immutable result self-validates source indices, fractional bounds and physical normal bounds against retained profile size/height. There is no automatic vacuum plateau, surface-side, dipole-region or flatness inference, and no macroscopic averaging or smoothing.

Explicit `FermiLevelSource` state retains finite eV, provenance and mandatory nonblank `calculation_id`; the Block-3 convenience path uses retained `source_fermi_ev`, not plotted reference state or inferred band extrema. `calculate_work_function(...)` requires matching calculation identity and performs only transparent `Phi = V_vacuum - E_F`, preserving unexpected negative values rather than clipping them. Passive `plot_planar_potential(...)` renders retained profile/vacuum/Fermi/work-function state without scientific recomputation. The reviewed domain contract is recorded in [`LOCPOT_WORK_FUNCTION.md`](LOCPOT_WORK_FUNCTION.md); no new runtime dependency was added.

Block-5 final head `34cf2253bf9744149d498edecf186d5fe04e6afe` passed CI #515 / run `32876765592` with Ruff, 1057 tests, fresh-wheel/public-API audits, current optional-backend LOCPOT exact-value/skew-cell smoke and documented examples, plus final-head reviews `5021836289`, `5021837599`, before expected-head squash merge `ab4b8c6f5445920124c2a61799e189ae25b8d404`.

### Block-5 completion-state sync — complete

Issue #221 / PR #222 synchronized the merged Block-5 state into central documentation at `51b04e9b7a63b200c6679d83730e49451f9bee64` before Block 6 began.

### Explicit NEB image-energy state + discrete barrier plotting — complete

Issue #223 / PR #224 delivered CatalysisWorkbench-owned immutable `NEBImageState`, exact ordered `NEBPath`, and explicit `NEBBarrierResult` state for post-processing already-generated image energies. Each image retains literal finite absolute energy in eV, nonblank source provenance and optional immutable `AtomicStructure` provenance. Paths preserve exact caller/source image order, unique stable image keys, explicit ordinal coordinates or caller-supplied finite reaction coordinates, and absolute or explicit-reference-relative `E_i - E_ref` plotting energies. Attached structures never trigger hidden atom mapping, reordering, MIC remapping, Kabsch alignment, IDPP, geometry fitting or reaction-coordinate inference.

`calculate_neb_barrier(...)` requires explicit retained initial, saddle and final image keys, validates source order as initial before saddle before final, and performs only `E_saddle - E_initial` / `E_saddle - E_final` on retained absolute energies. Negative arithmetic is retained rather than clipped. No highest-energy saddle selection, spline maximum, smoothing, interpolation, polynomial fitting or continuous transition-state inference is introduced. Passive `plot_neb_path(...)` renders retained x/y values with straight source-order point-to-point connections and highlights a saddle only from an explicitly supplied compatible barrier result. The reviewed domain contract is recorded in [`NEB_BARRIERS.md`](NEB_BARRIERS.md); full pymatgen and ASE remain reference-only, and no new runtime dependency was added.

Block-6 final head `5aa1926e7125c49950589553b8463e5ecfb936fd` passed CI #521 / run `32879644216` with Ruff, full pytest, fresh-wheel/public-API audits through v0.7 Block 6, all existing optional-backend audits and documented examples, plus final-head reviews `5022088404`, `5022089761`, before expected-head squash merge `7a80b99bc513b7a6b33d1a9481ff25c1c4d95b85`.

### Block-6 completion-state sync — complete

Issue #225 / PR #226 synchronized the merged Block-6 state into central documentation at `0e433d55f7d08632e590a9be495cb10128a7a0d6` before Block 7 began.

### Advanced volumetric 3D rendering + static export — complete

Issue #227 / PR #228 delivered a publication-oriented static 3-D backend while preserving the reviewed renderer-neutral `VolumetricScene` as authority. The heavy PyVista/VTK stack is isolated behind the lazy optional `volumetric3d` extra, so the base wheel neither requires nor imports it. `Volumetric3DRenderSpec` retains explicit presentation/export controls, while `Volumetric3DRenderResult` retains only an immutable uint8 screenshot, scene/render digests and backend versions; no Plotter, actor, mesh or other backend object becomes public state.

Full 3-D field geometry uses exact source-grid fractional coordinates `f=(i/n0,j/n1,k/n2)` followed by the complete lattice transform `r=f@L`, including skew cells; source values are mapped into VTK `StructuredGrid` point order explicitly. Isosurfaces use only caller-retained thresholds, with contour interpolation treated solely as presentation mesh geometry. Exact slices consume the existing `ScalarFieldSlice` Cartesian points and values rather than backend scientific slicing. Optional fractional clipping is explicit presentation geometry using `f=r@L^-1`; retained `StructureScene` atoms, explicit bonds, cell edges and camera state are rendered without new chemical inference, alignment or atom remapping. Scientific arrays/digests are verified unchanged after rendering. Static off-screen screenshots and PNG export are supported; interactive GUI/browser/Jupyter editing remains later scope. PyVista is MIT and VTK BSD-3-Clause; current scikit-image was not added because its current line requires Python >=3.12 while CatalysisWorkbench retains Python >=3.11. The reviewed contract is recorded in [`VOLUMETRIC_3D.md`](VOLUMETRIC_3D.md).

Block-7 final head `6dc1472b9157151d67b20f8b359542e103d5f6c2` passed CI #526 / run `32882938623` with Ruff, full pytest, base fresh-wheel/public-API audits through v0.7 Block 7, all existing optional-backend audits and documented examples, plus a separate fresh-wheel `[volumetric3d]` PyVista/VTK headless skew-cell rendering/PNG-export smoke. Final-head reviews `5022437132`, `5022439286` found no blockers before expected-head squash merge `24d3a8e67e4ef996125e575308b88ab6f9532448`.

### v0.7 release and post-release maintenance — complete

Issue #229 / PR #230 synchronized the completed seven-block scientific state before release hardening. Gate A #231/#232 completed the frozen-scope installed-wheel/public-API audit; Gate B #233/#234 finalized and exact-wheel validated distribution/runtime `0.7.0` at release commit `e3062fc12c794f54c7b7613875ec73608a587a59`; Gate C #237/#238 created and independently reverse-verified `v0.7.0` on that exact commit. The one-shot tag workflow was removed through #239/#240, Gate-C evidence synchronized through #241/#242, the public GitHub Release was published and synchronized through #243/#244, and post-release #245/#246 added the backwards-compatible `symmetric_color_limits()` primitive without changing version or release artifacts. PyPI/package-registry publication remains deferred.

## v0.8 execution status

The reviewed v0.8 architecture, scientific semantics, dependency boundaries, implementation order, prior-art/license decisions, testing strategy, and release handoff are maintained in [`V0_8_PLAN.md`](V0_8_PLAN.md).

### Architecture checkpoint — complete

Issue #249 / PR #250 froze the shared operando/time-resolved state model, literal common-grid and fail-closed compatibility rules, exact measured-point operations, passive visualization boundary, Raman/FTIR/XAS/XRD domain consumers, and six-block dependency order before production implementation. It merged at `fa7baaf8ce68369b0e732faf4e7621a818db92b6`; post-merge CI #550 / run `32920821932` passed on that exact `main` head.

The frozen implementation order is:

1. shared immutable frame-coordinate and operando-stack foundation;
2. exact operations, derived traces, and explicit cross-modal comparison;
3. passive waterfall, heatmap, cut, and trace visualization;
4. operando Raman and FTIR adapters/trajectories;
5. operando XAS/XANES adapters/mapping/descriptor trajectories;
6. operando XRD adapters/mapping/window and peak trajectories.

### Shared immutable frame-coordinate and operando-stack foundation — complete

Issue #253 / PR #254 delivered the shared `catalysis_workbench.experimental.operando` foundation on top of the released core `Axis` / `Series` / `Dataset` layer: immutable frame coordinates, immutable exact-grid `OperandoStack` state, deterministic reconstructible digests, strict source/grid/axis/basis compatibility, public exports, focused regression tests, and fresh-installed-wheel audit. Acquisition and signal order are retained literally; repeated or non-monotonic frame-coordinate values are valid; signal coordinates must remain strictly monotonic while preserving increasing or decreasing source direction. The implementation performs no interpolation, resampling, alignment, sorting, smoothing, baseline correction, normalization, clipping, unit conversion, coordinate inference, or automatic primary-coordinate selection.

Block-1 final head `eadf5b2e6630b137922f365a88f4b9ef3c43b12b` passed CI #561 / run `32922150384` and formal reviews `5026150379`, `5026170031` with zero unresolved threads after hardening Python/NumPy scalar metadata canonicalization. Expected-head squash merge produced `45d0515dd5c1c70f15f4d5cd76ba2a359dc66bb2`; post-merge main CI #562 / run `32922349620` passed on that exact commit.

No new runtime dependency, hidden alignment/interpolation/normalization, automatic peak/species/phase inference, v0.7.1, tag, release, or package-registry action was introduced. Block 2 — exact measured-point operations, derived traces, and explicit cross-modal comparison — is next.

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
- [`V0_8_PLAN.md`](V0_8_PLAN.md): v0.8 architecture, shared operando state/grid/provenance contracts, frozen six-block dependency order, passive visualization and domain-consumer boundaries, testing strategy, and release handoff.
- [`V0_7_PLAN.md`](V0_7_PLAN.md): v0.7 architecture, frozen seven-block dependency order, scientific/visualization semantics, prior-art/license decisions, testing strategy, and release handoff.
- [`VOLUMETRIC_VISUALIZATION.md`](VOLUMETRIC_VISUALIZATION.md): reviewed v0.7 Block-1 scalar-field/source-grid/renderer-neutral foundation and Block-2 density/ELF/exact-slice visualization contracts.
- [`BAND_STRUCTURE.md`](BAND_STRUCTURE.md): reviewed v0.7 Block-3 ordinary band-state, reciprocal-path/`2*pi`, physical-spin, explicit Fermi-reference, VASP line-mode adapter and passive plotting contract.
- [`PROCAR_FAT_BANDS.md`](PROCAR_FAT_BANDS.md): reviewed v0.7 Block-4 projection-state, backend orbital semantics, explicit aggregation/site identity, compatibility-tolerance, SOC/vector boundary and passive fat-band contract.
- [`LOCPOT_WORK_FUNCTION.md`](LOCPOT_WORK_FUNCTION.md): reviewed v0.7 Block-5 local-potential scalar-field, skew-cell planar averaging, explicit vacuum/Fermi compatibility, transparent work-function arithmetic and passive plotting contract.
- [`NEB_BARRIERS.md`](NEB_BARRIERS.md): reviewed v0.7 Block-6 exact image/path order, ordinal/explicit reaction coordinates, explicit reference-relative energy semantics, discrete barrier arithmetic and passive no-spline rendering contract.
- [`VOLUMETRIC_3D.md`](VOLUMETRIC_3D.md): reviewed v0.7 Block-7 optional PyVista/VTK backend, full-lattice skew-cell source-grid geometry, explicit isosurface/exact-slice/fractional clipping, retained structure/camera mapping, backend-hidden immutable screenshot result and static headless PNG-export contract.
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

The v0.7 release lifecycle and post-release central-state correction are complete. The dedicated v0.8 architecture checkpoint is complete through Issue #249 / PR #250, and shared-stack foundation Block 1 is complete through Issue #253 / PR #254 at `45d0515dd5c1c70f15f4d5cd76ba2a359dc66bb2`; begin Block 2 — exact measured-point operations, derived traces, and explicit cross-modal comparison — from a new scoped Issue and Draft PR, then continue the frozen order in `V0_8_PLAN.md`. Preserve immutable `v0.7.0 -> e3062fc12c794f54c7b7613875ec73608a587a59`, distribution/runtime release version `0.7.0`, the published public GitHub Release, and the PyPI-deferred boundary.
