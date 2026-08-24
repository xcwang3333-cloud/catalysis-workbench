# CatalysisWorkbench v0.5 Plan

v0.5 is the XAS, atomic-structure, and basic DFT-energetics release. This document defines the architecture and dependency order before scientific implementation. GitHub remains the operational source of truth.

## Baseline and release state

- Architecture checkpoint Issue: #115.
- Exact architecture base: `main` at `c588b1b0286754c3381f69973183e265fca7621d`.
- Released v0.4 tag: `v0.4.0 -> bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6`.
- Distribution/runtime version remains `0.4.0` during v0.5 development until a later reviewed release Gate B.
- v0.4 GitHub Release is complete.
- PyPI/package-registry publication is deferred. Issue #113 is closed `not_planned`; the merged trusted-publishing workflow remains dormant until a future explicit decision.
- No v0.5 implementation may move or recreate `v0.4.0`.

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

v0.5 contains eight planned scientific blocks:

1. XAS semantics plus XANES preparation, normalization, and comparison.
2. EXAFS k-space preparation plus FT-EXAFS transform and publication plotting.
3. WT-EXAFS transform/visualization.
4. EXAFS fitting-result summary integration.
5. Atomic-structure model plus POSCAR / CONTCAR / CIF / XYZ adapters.
6. Bond/angle/coordination analysis and structure comparison.
7. Basic static publication-oriented structure visualization.
8. Basic DFT total/relative/adsorption-energy analysis.

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
- a concrete structure-I/O implementation Issue must validate `pymatgen-core` behavior, wheel compatibility, dependency weight, and exact supported formats before adding it to `pyproject.toml`;
- use a mature parser/PBC engine instead of hand-writing CIF/POSCAR parsing when the backend satisfies the reviewed contract.

ASE remains a useful atomistic reference but its package license is LGPL-2.1-or-later; it is not added merely when the narrower MIT backend covers the required v0.5 scope.

### Structure visualization: pretty-lattice

`songfeitong/pretty-lattice` is MIT licensed and is a major UX/architecture reference for publication-ready crystal figures. Relevant ideas include:

- analysis/parsing separated from visual styling;
- mature structure parsing delegated to pymatgen;
- an intermediate scene representation between structure data and renderer;
- read-only final structures;
- attractive starting defaults with explicit colors, radii, bond/material, opacity, orientation, and export controls;
- preview/export using one visual state.

CatalysisWorkbench will not copy the Three.js/browser implementation into the scientific core. v0.5 targets a basic static renderer and renderer-neutral state; interactive browser/local-GUI editing remains v0.9-v1.0.

## 1. XAS semantics and XANES preparation

### Data contract

A one-dimensional XAS trace remains a core `Series` when possible.

Canonical semantics:

- x axis: `energy`, unit `eV`;
- y axis: explicit absorption-like semantic such as `mu`, `normalized_mu`, or a caller-provided reviewed equivalent;
- source order is preserved;
- duplicate/non-monotonic energy handling is explicit rather than silently sorted.

XAS-specific immutable state may record:

- absorber/edge label when caller supplied;
- explicit `e0_ev`;
- energy-reference shift history;
- pre-edge and post-edge regions;
- polynomial orders;
- normalization edge step and retained arrays;
- source identity/digest and deterministic processing state.

### Initial XANES operations

The first implementation should support explicit caller-controlled:

- validation of energy/eV and finite measured data;
- additive energy shift without hidden calibration lookup;
- measured-point region selection;
- pre-edge baseline fitting;
- post-edge normalization fitting;
- edge-step normalization;
- multi-sample comparison using the existing visualization model.

No automatic oxidation-state assignment, white-line chemistry assignment, beamline-specific reader inference, or hidden edge database belongs in this block.

## 2. EXAFS k-space and FT-EXAFS

The EXAFS layer consumes reviewed XAS/XANES state and keeps every transform convention explicit.

Required caller-visible state includes:

- `e0_ev` used for conversion;
- energy-to-k convention and physical constants used;
- k range;
- k weighting;
- background/subtraction source when applicable;
- transform window family and parameters;
- zero padding / FFT grid state;
- retained complex transform rather than magnitude only;
- R range used only for display/summary unless an analysis step explicitly crops data.

The result should retain exact k/chi and R/complex-FT arrays plus provenance. Plotting must render retained magnitude/real/imaginary channels without recomputing the transform.

A full EXAFS background/fitting engine is not implied by this block.

## 3. WT-EXAFS

WT-EXAFS is a separate explicit numerical transform, not a plotting trick.

The API must retain:

- source k/chi identity;
- k weighting;
- selected wavelet family;
- scale/frequency mapping convention;
- transform parameters;
- exact k/R or k/frequency grid used;
- complex transform or the minimum state needed to reproduce magnitude/phase views.

No hidden wavelet defaults should be chemistry-dependent. Numerical implementation/dependency choice requires prior-art refresh and hand-verifiable regression cases before merge.

## 4. EXAFS fitting-result summaries

v0.5 integrates already computed fitting results; it does not become an Artemis-class fitting engine.

The first summary contract should represent caller/imported values such as:

- path/shell stable key and display label;
- coordination number when provided;
- effective path length / fitted R;
- Debye-Waller-like sigma-squared;
- delta-E0;
- amplitude-related state when supplied;
- uncertainty/availability state;
- fit R-factor / chi-square-like diagnostic labels exactly as supplied by the producing tool;
- producing-tool/source metadata.

The summary layer must not reinterpret one program's statistic as another program's identically named quantity without an explicit adapter.

## 5. Atomic-structure foundation and file adapters

A new immutable CatalysisWorkbench-owned structure contract is introduced under the computation layer.

Minimum retained state:

- ordered site/species identity;
- Cartesian coordinates in angstrom;
- lattice matrix in angstrom when periodic;
- periodic boundary flags;
- deterministic site keys/indices;
- optional site labels and lightweight source metadata;
- deterministic source digest.

Public APIs must not expose mutable third-party structure objects as authoritative state.

Initial adapters:

- POSCAR;
- CONTCAR;
- CIF;
- XYZ.

Parsing belongs in I/O/adapter code; the resulting immutable model belongs to the computation/public scientific layer.

## 6. Geometry, coordination, and structure comparison

Initial geometry APIs should support:

- bond/site distance;
- angle;
- explicit periodic-image distance;
- caller-defined coordination by cutoff or reviewed explicit neighbor strategy;
- coordination number summaries;
- pairwise/local-geometry comparison between structures with explicit site mapping.

Guardrails:

- never infer a chemical bond merely from element labels;
- never hide periodic-image selection;
- never silently reorder sites to make two structures appear aligned;
- site mapping must be caller supplied or produced by a separately reviewed deterministic mapping algorithm;
- distances are angstrom and angles degrees unless a future generalized unit layer explicitly changes that contract.

## 7. Basic structure publication visualization

Rendering is separate from structure analysis.

The first static visual state should support at minimum:

- atom colors;
- atom radii/scales;
- bond visibility/style where bonds were explicitly supplied or generated from explicit geometry rules;
- cell visibility/style;
- camera/view orientation;
- orthographic/perspective choice if supported by the renderer;
- labels;
- background;
- physical output dimensions and vector/raster export where technically meaningful.

An intermediate scene representation is preferred so future GUI/browser rendering can reuse the same scientific/visual state without changing geometry analysis.

## 8. Basic DFT energetics and adsorption energy

The first computation-energy API consumes explicit energies rather than running VASP.

Required state:

- stable calculation/species keys;
- energy values with explicit eV unit;
- reference identities and stoichiometric coefficients;
- explicit normalization basis where relevant;
- deterministic provenance/source identifiers.

Initial operations:

- relative energies against an explicit reference;
- reaction-energy-like explicit linear combinations;
- adsorption energy from caller-supplied slab/adsorbate/combined energies and explicit coefficients;
- comparison tables/plots as passive visualization.

No CHE potential/pH correction, gas-phase thermochemical database lookup, ZPE/entropy correction, chemical-potential inference, DOS/PDOS, Bader, COHP/ICOHP, or charge-density-difference work belongs here.

## Dependency order

The planned implementation order is:

0. **Architecture checkpoint — Issue #115.**
1. **XAS semantics + XANES preparation/normalization/comparison.**
2. **EXAFS k-space + FT transform/plotting.**
3. **WT-EXAFS transform/visualization.**
4. **EXAFS fitting-result summary integration.**
5. **Atomic structure model + POSCAR/CONTCAR/CIF/XYZ adapters.**
6. **Geometry/coordination/structure comparison.**
7. **Basic structure publication visualization.**
8. **Basic DFT energetics/adsorption-energy analysis.**
9. **Completion-state documentation synchronization.**
10. **Gate A frozen-scope release hardening.**
11. **Gate B final-version candidate.**
12. **Gate C tag creation/reverse verification under separate authorization.**

The XAS and structure stacks are mostly independent. Reordering is allowed only when the responsible Issue records a concrete dependency reason; scientific implementation must not begin before this architecture checkpoint merges.

## Mandatory feature loop

Every v0.5 scientific block follows:

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

- v0.5 development does not move `v0.4.0`.
- v0.5 scientific implementation does not itself authorize a version bump.
- Gate B will eventually synchronize distribution/runtime version only after the frozen scope passes Gate A.
- Gate C tag creation remains a separate explicit authorization boundary.
- GitHub Release creation remains separate from a Git tag.
- PyPI/package-registry publication remains deferred unless explicitly reauthorized in a future decision.
