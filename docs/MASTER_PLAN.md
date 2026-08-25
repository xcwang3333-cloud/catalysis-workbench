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
- Current v0.6 architecture baseline: `3803e014376a7edb22d6a9a5b6480541742499be` after Issue #146 / PR #147.
- v0.5 scientific-completion baseline: `a7ebd009ec83b0aeb068ad2d2f6712c17a783f1f`.
- Completion-state docs merge: `8c958ffc29a36afa9340cada2239b51520c87a3d` (#134/#135).
- v0.5 Gate A: #136/#137 — complete at `0ffcd7e4a89340d993468039ba83b44bc7638050`.
- v0.5 Gate B: #138/#139 — complete at release commit `9400ac0044ac333d2cae228554c08d955a816a4c`.
- Gate-B final head `b95841ed472aff1fa4d05af7335547ee5c3cd611` passed CI #360 / run `32800514038` and reviews `5014348449`, `5014349058`.
- Distribution/runtime version is `0.5.0`.
- Gate C / Issue #142 is complete; tag `v0.5.0` resolves exactly to `9400ac0044ac333d2cae228554c08d955a816a4c` and reads distribution/runtime version `0.5.0` through the tag.
- The public GitHub Release `CatalysisWorkbench v0.5.0` is published from the existing verified tag; Issue #144 is complete.
- Final v0.5 post-release documentation synchronization Issue #143 is complete/closed; its merge is `bed5c6e750a6066baa8daa21492aa9eb90e8bca8`.
- Released v0.4 tag: `v0.4.0 -> bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6`, immutable and independently reverse-verified.
- The v0.4 GitHub Release is published from the existing `v0.4.0` tag.
- `v0.3.0` remains fixed on release commit `845ac4c15d399a8816c7ba66d61ea6ec4cc11293`.
- PyPI/package-registry publication is explicitly deferred; Issue #113 is closed `not_planned`.
- v0.5 architecture checkpoint: Issue #115 / PR #116 — complete.
- XAS/XANES: Issue #117 / PR #118 — complete.
- FT-EXAFS: Issue #119 / PR #120 — complete.
- WT-EXAFS: Issue #121 / PR #122 — complete.
- EXAFS fitting-result summaries: Issue #123 / PR #124 — complete.
- Atomic-structure model/adapters: Issue #125 / PR #126 — complete.
- Geometry/coordination/structure comparison: Issue #127 / PR #129 — complete.
- Static structure visualization: Issue #130 / PR #131 — complete.
- Basic DFT energetics: Issue #132 / PR #133 — complete.
- v0.5 scientific implementation: **complete**.
- v0.6 architecture checkpoint: Issue #146 / PR #147 — complete at `3803e014376a7edb22d6a9a5b6480541742499be`.
- v0.6 architecture central-document synchronization: Issue #148 / PR #149 — complete at `aac05d4426c15c8932c608d07ef42e4dc07b09ce`.
- v0.6 block 1, electronic-structure + volumetric semantics/adapters: Issue #150 / PR #151 — complete at `58023070bf7f642748b69e99281a5ed7ed4d40df`.
- Block-1 final head `229fa5c3ec9225bde8afd1931cefe0dea521eabe` passed CI #376 / run `32808329764` and final-head reviews `5014903632`, `5014904435` before squash merge.
- v0.6 block-1 completion-state docs sync: Issue #152 / PR #153 — complete at `39df1101d1ed7dde5c4ab6d264b8796c27c97620`.
- v0.6 block 2, DOS/PDOS processing + passive plotting: Issue #154 / PR #155 — complete at `09e63e72e1b79d8c151c97769d4bfbd2fb6a366f`.
- Block-2 final head `1e18c838f0ce0203ae0f841fbde3786c00970d16` passed CI #388 / run `32810513894` and final-head reviews `5015058136`, `5015059007` before squash merge.
- v0.6 block-2 completion-state docs sync: Issue #156 / PR #157 — complete at `c597fdaba7509a0c6c4cf6088c7367c94cec0547`.
- v0.6 block 3, band-center / DOS first-moment analysis: Issue #158 / PR #159 — complete at `cdbc4822592cf43033af1f0242793d5912098b7c`.
- Block-3 final head `415258a2ff7547af4fd9b2717404d06c341c0de1` passed CI #397 / run `32814966504` and final-head reviews `5015455765`, `5015456841` before squash merge.
- Active stage: **Issue #160 — synchronize block-3 completion state into central documentation**.
- v0.6 block 4 (Bader-result parsing + explicit charge accounting) starts only after #160 is complete and `main` is reverified.

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
| v0.6.x | electronic structure and catalysis thermodynamics | architecture + blocks 1–3 complete; block 4 next after #160 |
| v0.7.x | advanced computational visualization | planned |
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

### Current completion-state sync

Issue #160 is the docs-only synchronization checkpoint after block 3. It records merged reality in central plans without adding Bader parsing or charge-accounting code. Block 4 begins only after #160 merges and `main` is reverified.

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
- [`V0_6_PLAN.md`](V0_6_PLAN.md): v0.6 architecture, frozen dependency order, scientific/API semantics, prior-art/license decisions, test strategy, and v0.7 handoff.
- [`V0_5_PLAN.md`](V0_5_PLAN.md): v0.5 architecture, dependency order, scientific completion state and release handoff.
- [`V0_5_RELEASING.md`](V0_5_RELEASING.md): v0.5 Gate A/B/C procedure and release evidence.
- [`V0_4_PLAN.md`](V0_4_PLAN.md) / [`V0_4_RELEASING.md`](V0_4_RELEASING.md): retained v0.4 scientific/release history.
- technique documents such as [`XAS.md`](XAS.md), [`EXAFS.md`](EXAFS.md), [`WT_EXAFS.md`](WT_EXAFS.md), [`STRUCTURE_GEOMETRY.md`](STRUCTURE_GEOMETRY.md), [`STRUCTURE_VISUALIZATION.md`](STRUCTURE_VISUALIZATION.md), and [`DFT_ENERGETICS.md`](DFT_ENERGETICS.md): reviewed domain contracts.
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

Issue #160 is the active v0.6 block-3 completion-state documentation checkpoint. After it merges, reverify `main`, Issue #160 closure, immutable `v0.5.0`, immutable `v0.4.0`, distribution/runtime version `0.5.0`, and PyPI-deferred state. Then start block 4 (Bader-result parsing + explicit charge accounting) from that exact verified `main` baseline using the frozen order in `V0_6_PLAN.md`.