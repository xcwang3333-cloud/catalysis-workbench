# CatalysisWorkbench v0.5 Plan

v0.5 is the XAS, atomic-structure, and basic DFT-energetics release. This document defines the reviewed architecture, dependency order, scientific completion state, and release handoff. GitHub remains the operational source of truth.

## Baseline and release state

- Architecture checkpoint Issue: #115.
- Exact architecture base: `main` at `c588b1b0286754c3381f69973183e265fca7621d`.
- Released v0.4 tag: `v0.4.0 -> bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6`.
- v0.4 GitHub Release is complete.
- PyPI/package-registry publication is deferred. Issue #113 is closed `not_planned`; the merged trusted-publishing workflow remains dormant until a future explicit decision.
- No v0.5 implementation or release gate may move or recreate `v0.4.0`.
- v0.5 Gate A is complete at merge `0ffcd7e4a89340d993468039ba83b44bc7638050`.
- v0.5 Gate B is complete at release commit `9400ac0044ac333d2cae228554c08d955a816a4c`.
- Distribution/runtime version is `0.5.0` after reviewed Gate B exact-wheel validation.
- Gate C / Issue #142 is complete: `v0.5.0` resolves exactly to `9400ac0044ac333d2cae228554c08d955a816a4c` and reads distribution/runtime version `0.5.0` through the tag.
- The public GitHub Release `CatalysisWorkbench v0.5.0` is published from that existing tag; Issue #144 is complete.

## Scientific completion checkpoint

All eight frozen v0.5 scientific implementation blocks are complete on `main` as of 2026-08-25. The scientific-completion baseline is `a7ebd009ec83b0aeb068ad2d2f6712c17a783f1f`.

1. XAS semantics + XANES preparation/normalization/comparison — Issue #117 / PR #118 — complete.
2. EXAFS k-space + FT-EXAFS transform/plotting — Issue #119 / PR #120 — complete.
3. WT-EXAFS transform/visualization — Issue #121 / PR #122 — complete.
4. EXAFS fitting-result summary integration — Issue #123 / PR #124 — complete.
5. Atomic structure model + POSCAR/CONTCAR/CIF/XYZ adapters — Issue #125 / PR #126 — complete.
6. Geometry/coordination/structure comparison — Issue #127 / PR #129 — complete.
7. Static publication-oriented structure visualization — Issue #130 / PR #131 — complete.
8. Basic DFT total/relative/reaction/adsorption-energy analysis — Issue #132 / PR #133 — complete at scientific-completion commit `a7ebd009ec83b0aeb068ad2d2f6712c17a783f1f`.

Completion-state documentation synchronization #134/#135 is complete at `8c958ffc29a36afa9340cada2239b51520c87a3d`. Gate A #136/#137, Gate B #138/#139, post-Gate-B sync #140/#141, Gate C #142, and GitHub Release #144 are complete. Final post-release documentation synchronization is tracked by Issue #143.

## Architecture principles

The existing project rules continue to apply:

1. reuse the immutable core `Series` / `Dataset` model where it is scientifically sufficient;
2. introduce domain state only when generic XY state cannot safely represent the scientific contract;
3. keep parsing, numerical analysis, immutable result state, and rendering as separate responsibilities;
4. expose scientific choices such as references, windows, polynomial orders, weights, cutoffs, periodic-image conventions, and normalization bases rather than guessing them;
5. preserve deterministic source identity/provenance and fail closed on incompatible state;
6. wrap mature open-source backends when they solve difficult generic infrastructure better than a local reimplementation;
7. keep numerical imports Matplotlib-lazy and make plotting a passive consumer of reviewed result arrays/state;
8. preserve the v0.1-v0.4 public surfaces unless a breaking change is separately planned and reviewed.

## Frozen v0.5 scope

v0.5 contains eight planned scientific blocks, all now implemented and merged:

1. XAS semantics plus XANES preparation, normalization, and comparison.
2. EXAFS k-space preparation plus FT-EXAFS transform and publication plotting.
3. WT-EXAFS transform/visualization.
4. EXAFS fitting-result summary integration.
5. Atomic-structure model plus POSCAR / CONTCAR / CIF / XYZ adapters.
6. Bond/angle/coordination analysis and structure comparison.
7. Basic static publication-oriented structure visualization.
8. Basic DFT total/relative/reaction/adsorption-energy analysis.

CHE/free-energy thermodynamics, DOS/PDOS, Bader, COHP/ICOHP, charge-density difference, advanced volumetric rendering, operando mapping, GUI editing, and VASP job management remain later-release work.

## Prior-art and license decisions

### XAS: xraylarch

`xraypy/xraylarch` is the primary current XAS scientific reference. Upstream is MIT licensed and covers mature XAS/XANES/EXAFS processing, plotting, and fitting workflows.

Initial v0.5 decision:

- use Larch as a scientific/equation/workflow/test reference;
- do not add `xraylarch` as a default runtime dependency for the first v0.5 XAS layer;
- implement only the narrower transparent post-processing contracts that fit CatalysisWorkbench's role;
- do not recreate a full Larix/Artemis/FEFF-path fitting environment.

A later Issue may justify an adapter/dependency if a concrete feature cannot be implemented safely with the existing NumPy/SciPy stack.

### Structures: pymatgen-core

`materialsproject/pymatgen-core` is the preferred runtime-backend candidate for structure parsing and periodic-boundary geometry. Current upstream is MIT licensed and supports Python 3.11+.

Architecture decision:

- CatalysisWorkbench owns its public immutable structure/result contracts;
- third-party objects do not become the public API;
- the reviewed structure-I/O implementation validated `pymatgen-core` through an optional `structure` extra rather than making it a mandatory base dependency;
- use a mature parser/PBC engine instead of hand-writing CIF/POSCAR parsing when the backend satisfies the reviewed contract.

ASE remains a useful atomistic reference but its package license is LGPL-2.1-or-later; it was not added merely when the narrower MIT backend covered the required v0.5 scope.

### Structure visualization: pretty-lattice

`songfeitong/pretty-lattice` is MIT licensed and is a major UX/architecture reference for publication-ready crystal figures. Relevant ideas include:

- analysis/parsing separated from visual styling;
- mature structure parsing delegated to pymatgen;
- an intermediate scene representation between structure data and renderer;
- read-only final structures;
- attractive starting defaults with explicit colors, radii, bond/material, opacity, orientation, and export controls;
- preview/export using one visual state.

CatalysisWorkbench does not copy the Three.js/browser implementation into the scientific core. v0.5 provides a static renderer and renderer-neutral scene state; interactive browser/local-GUI editing remains v0.9-v1.0.

## 1. XAS semantics and XANES preparation

### Data contract

A one-dimensional XAS trace remains a core `Series` when possible.

Canonical semantics:

- x axis: `energy`, unit `eV`;
- y axis: explicit absorption-like semantic such as `mu`, `normalized_mu`, or a caller-provided reviewed equivalent;
- source order is preserved;
- duplicate/non-monotonic energy handling is explicit rather than silently sorted.

XAS-specific immutable state records reviewed state such as:

- absorber/edge label when caller supplied;
- explicit `e0_ev`;
- energy-reference shift history;
- pre-edge and post-edge regions;
- polynomial orders;
- normalization edge step and retained arrays;
- source identity/digest and deterministic processing state.

The implementation supports caller-controlled energy/eV validation, additive energy shift, measured-point regions, pre-edge/post-edge polynomial normalization, edge-step normalization, explicit E−E0 transformation, and passive comparison plotting. It does not perform automatic oxidation-state assignment, white-line chemistry assignment, beamline-specific reader inference, or hidden edge-database lookup.

## 2. EXAFS k-space and FT-EXAFS

The reviewed EXAFS layer keeps transform conventions explicit and retains the complex transform rather than magnitude alone.

Caller-visible state includes k range/weighting, transform window and parameters, zero-padding/FFT state, source direction and exact k grid. The implementation requires a compatible uniform k grid instead of silently interpolating and retains magnitude/real/imaginary/phase views from the authoritative complex transform. Plotting consumes retained state without recomputing the transform.

A full EXAFS background/fitting engine is not part of this block.

## 3. WT-EXAFS

WT-EXAFS is implemented as a separate explicit numerical Cauchy transform, not a plotting trick. The retained state includes source k/chi identity, k weighting, Cauchy order, explicit k/R grids, transform parameters and the authoritative complex matrix, with passive magnitude/real/imaginary/phase rendering.

The EXAFS phase mapping is independently regression-tested with a single-frequency `chi(k)=cos(2R0k)` ridge case. Chemistry-dependent hidden wavelet defaults are not introduced.

## 4. EXAFS fitting-result summaries

v0.5 integrates already computed fitting results; it does not become an Artemis-class fitting engine.

The summary contract retains path/shell stable keys, coordination number when supplied, fitted R, sigma-squared, delta-E0, optional amplitude-like state, explicit uncertainty availability, and diagnostic labels exactly as provided by the producing tool. Statistics are not reinterpreted across external fitting programs.

## 5. Atomic-structure foundation and file adapters

The computation layer now owns an immutable `AtomicStructure` contract with ordered species/sites, Cartesian coordinates in angstrom, optional lattice, PBC flags, deterministic site keys, detached metadata and source digest.

POSCAR, CONTCAR, CIF and XYZ adapters use the reviewed optional `pymatgen-core` backend. Third-party mutable structure objects are not public authority.

## 6. Geometry, coordination, and structure comparison

Reviewed geometry APIs provide exact site/image distance and angle, explicit bounded-image cutoff coordination, and caller-mapped structure comparison.

Guardrails remain:

- no chemical bond inference merely from element labels;
- no hidden minimum-image replacement;
- periodic images are explicit;
- coordination search bounds are caller-visible;
- structure comparison does not silently reorder sites, auto-map, or Kabsch-align structures;
- distances are angstrom and angles degrees.

## 7. Basic structure publication visualization

Rendering is separate from structure analysis. v0.5 introduces a CatalysisWorkbench-owned renderer-neutral immutable `StructureScene` with exact atom/site-image records, explicit caller-supplied bonds, unit-cell geometry, presentation-only atom colors/radii, explicit camera/projection state, and passive Matplotlib 3D rendering.

No automatic bond inference, polyhedron generation, browser GUI, or interactive structure editing is included.

## 8. Basic DFT energetics and adsorption energy

The computation-energy API consumes explicit caller-supplied energies rather than running VASP.

Reviewed state includes stable energy keys, finite eV values, explicit normalization bases/source IDs, deterministic ledger digest, caller-defined linear-combination coefficients, retained contribution arrays, and detached reporting tables.

Initial operations include:

- relative energies against an explicit same-basis reference;
- generic reaction-energy-like explicit linear combinations;
- transparent adsorption energy as `E(combined) - E(slab) - n*E(adsorbate)` with caller-visible `n`;
- passive relative-energy table/plot reporting.

No CHE potential/pH correction, gas-phase thermochemical lookup, ZPE/entropy correction, chemical-potential inference, DOS/PDOS, Bader, COHP/ICOHP, or charge-density-difference work belongs here.

## Dependency order and completion state

0. **Architecture checkpoint — Issue #115 — complete.**
1. **XAS semantics + XANES preparation/normalization/comparison — #117/#118 — complete.**
2. **EXAFS k-space + FT transform/plotting — #119/#120 — complete.**
3. **WT-EXAFS transform/visualization — #121/#122 — complete.**
4. **EXAFS fitting-result summary integration — #123/#124 — complete.**
5. **Atomic structure model + POSCAR/CONTCAR/CIF/XYZ adapters — #125/#126 — complete.**
6. **Geometry/coordination/structure comparison — #127/#129 — complete.**
7. **Basic structure publication visualization — #130/#131 — complete.**
8. **Basic DFT energetics/adsorption-energy analysis — #132/#133 — complete.**
9. **Completion-state documentation synchronization — #134/#135 — complete.**
10. **Gate A frozen-scope release hardening — #136/#137 — complete at `0ffcd7e4a89340d993468039ba83b44bc7638050`.**
11. **Gate B final-version candidate — #138/#139 — complete at `9400ac0044ac333d2cae228554c08d955a816a4c`; version `0.5.0`.**
12. **Post-Gate-B docs sync — #140/#141 — complete at `85d19870ff6b117318f903d59a9e16b35ac19830`.**
13. **Gate C tag creation/reverse verification — #142 — complete; `v0.5.0 -> 9400ac0044ac333d2cae228554c08d955a816a4c`.**
14. **GitHub Release — #144 — complete; `CatalysisWorkbench v0.5.0` publicly published from the existing tag.**
15. **Final post-release docs synchronization — #143 — active.**

## Mandatory feature loop

Every v0.5 scientific block followed:

```text
live main verification
    -> prior-art/license refresh
    -> exact-base branch
    -> implementation + hand-verifiable regression tests
    -> Draft PR
    -> exact-head CI
    -> scientific/API/compatibility review
    -> direct fixes
    -> fresh CI after every head change
    -> second formal review on final exact head
    -> Ready
    -> behind=0 / mergeable / review threads=0
    -> expected-head squash merge
    -> direct main verification
    -> Issue closure
```

CI or review evidence from an older head is stale after any head change.

## Release and publication boundaries

- v0.5 scientific implementation and release gates did not move `v0.4.0`.
- Gate A completed frozen-scope hardening while retaining distribution/runtime version `0.4.0`.
- Gate B completed final-version synchronization and exact-wheel validation at `0.5.0`.
- Gate B final head `b95841ed472aff1fa4d05af7335547ee5c3cd611` passed CI #360 / run `32800514038` and reviews `5014348449`, `5014349058` before squash merge `9400ac0044ac333d2cae228554c08d955a816a4c`.
- Gate C completed the separately authorized tag operation; `v0.5.0` is immutable at `9400ac0044ac333d2cae228554c08d955a816a4c`.
- The GitHub Release `CatalysisWorkbench v0.5.0` is publicly published from that existing tag with reviewed release notes.
- PyPI/package-registry publication remains deferred unless explicitly reauthorized in a future decision.
