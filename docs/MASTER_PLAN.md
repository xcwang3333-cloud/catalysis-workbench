# CatalysisWorkbench Master Plan

This document is the project-level execution map for CatalysisWorkbench. It connects the long-range release roadmap to the active GitHub Issue sequence, scientific/API quality gates, documentation responsibilities, and the rule that repository state is authoritative.

## Authority and source of truth

GitHub is the only operational source of truth for project state.

When documents and live repository state disagree, use this precedence order:

1. merged `main` code and tests;
2. current GitHub Issues and Pull Requests;
3. CI status for the exact commit under review;
4. this master plan and release-specific planning documents;
5. README summaries and other descriptive documentation.

Planning documents must be corrected when they drift from merged reality. They do not override code, Issue state, review findings, or CI.

## Current checkpoint

Checkpoint date: 2026-08-24.

- Repository: `xcwang3333-cloud/catalysis-workbench`.
- Stable integration branch: `main`.
- Current scientific `main` baseline: `a13dbd541b299f79d83e47f079c4638b082a8061` (`feat: add XPS semantics and background preparation (#80)`).
- v0.4 architecture checkpoint: Issue #73 / PR #74 — complete at `a7fb245bd39f8aa3dc18141c2ecf6f005f02ebd1`.
- v0.4 shared constrained peak-fitting foundation: Issue #75 / PR #76 — complete at `b6f428d96df9950373c17e5de487ac4113a2aacc`.
- shared-fitting exact-head CI #255 / run `32733891934` — success.
- shared-fitting formal reviews: `5008457897`, `5008470806`.
- XPS semantics/energy correction/region/background preparation: Issue #79 / PR #80 — complete at `a13dbd541b299f79d83e47f079c4638b082a8061`.
- XPS exact-head CI #261 / run `32736488212` — success.
- XPS formal reviews: `5008700786`, `5008706395`.
- Reviewed runtime fitting dependency: `lmfit>=1.3.4`.
- Distribution/runtime version remains `0.3.0`.
- `v0.3.0` remains fixed on release commit `845ac4c15d399a8816c7ba66d61ea6ec4cc11293`.
- Package-registry publication has not been performed and remains a separate policy decision.
- Active status checkpoint: Issue #81 — post-XPS-preparation docs sync and constrained-fitting handoff.
- Next scientific stage after #81: constrained XPS components/doublets and shared-fit integration.

Live GitHub Issue/PR/tag state remains authoritative if this checkpoint becomes stale.

## Release map

Detailed long-range scope is maintained in [`ROADMAP.md`](ROADMAP.md).

| Release | Primary scope | State |
| --- | --- | --- |
| v0.1.x | common XY core, tabular I/O, reusable processing, LSV, XRD, Raman, shared publication rendering/export | complete/released |
| v0.2.x | quantitative core electrochemistry and shared scatter/bar summaries | complete/released as v0.2.0 |
| v0.3.x | FTIR, thermal analysis, basic gas sorption, ICP/composition | complete/released as v0.3.0 |
| v0.4.x | advanced experimental analysis: shared fitting, XPS, EIS, quantitative BET, product calibration | implementation active |
| v0.5.x | XAS, structures, basic DFT energetics | planned |
| v0.6.x | electronic structure and catalysis thermodynamics | planned |
| v0.7.x | advanced computational visualization | planned |
| v0.8.x | operando/time-resolved analysis | planned |
| v0.9.x | reproducible batch workflows and first interactive editor | planned |
| v1.0.0 | stable personal catalysis data workbench and local GUI | planned |

Release numbering is a planning boundary, not permission to weaken scientific validation or compatibility requirements.

## Completed release baselines

### v0.2

The quantitative core electrochemistry release is complete. Its detailed dependency graph and scientific contracts are retained in [`V0_2_PLAN.md`](V0_2_PLAN.md), with release evidence in [`V0_2_RELEASING.md`](V0_2_RELEASING.md).

Completed scope includes Tafel, Faradaic efficiency, partial current density, catalyst-/metal-mass and ECSA activity normalization, TOF/TOFapp, CV/Cdl/ECSA, stability, RRDE, and Koutecky-Levich basics. The release tag and later post-release documentation synchronization are complete and immutable.

### v0.3

The extended experimental-processing release is complete as `v0.3.0`.

- FTIR / ATR-FTIR — Issue #50 / PR #51.
- TGA / DTG / TPR / TPD — Issue #54 / PR #55.
- basic gas sorption — Issue #58 / PR #59.
- ICP / elemental composition — Issue #62 / PR #63.
- documentation checkpoints — #52/#53, #56/#57, #60/#61, #64/#65.
- Gate A — #66 / #67.
- Gate B final-version candidate — #68 / #69.
- Gate C tag verification — #70.
- post-release docs synchronization — #71 / #72.

The reviewed release tag is `v0.3.0 -> 845ac4c15d399a8816c7ba66d61ea6ec4cc11293`. Quantitative BET fitting and shared peak fitting were intentionally excluded from the v0.3 scientific gate.

## v0.4 execution status

The detailed dependency order and scientific boundaries are maintained in [`V0_4_PLAN.md`](V0_4_PLAN.md).

### Architecture checkpoint — complete

Issue #73 / PR #74 established the v0.4 architecture before implementation.

Key decisions:

- generic constrained fitting and XPS-specific scientific state are separate layers;
- mature nonlinear optimization is wrapped rather than reimplemented;
- XPS owns binding-energy semantics, explicit energy-reference correction, XPS backgrounds, and spin-orbit constraints;
- general spectroscopy baseline algorithms are not treated as automatically interchangeable with XPS Shirley/Tougaard backgrounds;
- caller-supplied physical constraints remain visible and auditable;
- plotting remains separate from numerical processing/fitting.

### Shared constrained fitting — complete

Issue #75 / PR #76 delivered the first scientific implementation block.

Reviewed public behavior includes:

- `FitParameterSpec`, `PeakComponentSpec`, `PeakFitSpec`, `FittedParameter`, `PeakFitResult`, `PeakFittingError`, and `fit_peaks` under `catalysis_workbench.processing`;
- Gaussian, Lorentzian, Voigt, pseudo-Voigt, and Doniach initial model families;
- stable non-display component identities;
- explicit initial/fixed/bounded/tied parameter state;
- `{component.parameter}` public cross-component references;
- explicit fit windows, caller background, and residual-multiplier weights;
- ascending/descending monotonic source-order support without hidden sorting/interpolation;
- deterministic source-data provenance and immutable result arrays;
- physical residual/component/total-fit output;
- optional stderr/covariance/correlation state that remains unavailable when the backend cannot estimate it;
- explicit validation against backend model domains so invalid caller initial values are not silently clipped;
- fixed/constrained-only evaluation without fabricated uncertainty;
- installed-wheel fitting smoke and preservation of all reviewed v0.1-v0.3 tests/quickstarts.

`lmfit>=1.3.4` is now a reviewed runtime dependency. No XPS background, energy correction, doublet helper, automatic peak detection, smoothing, normalization, or plotting was introduced by #75.

Full behavior is documented in [`PEAK_FITTING.md`](PEAK_FITTING.md).

### XPS semantics and preparation — complete

Issue #79 / PR #80 delivered the second v0.4 scientific block.

Reviewed public behavior under `catalysis_workbench.experimental.characterization` includes:

- `validate_xps_series` with explicit `binding_energy`/eV and `intensity` semantics;
- strictly monotonic ascending or descending source storage with source-order preservation;
- `shift_xps_binding_energy` using the literal additive convention `E_corrected = E_source + shift_ev`, deterministic provenance, and repeated-correction rejection;
- `prepare_xps_region` using inclusive measured-point-only numerical bounds without interpolation or synthesized endpoints;
- immutable `XPSBackgroundResult` state with exact source/grid/endpoint/method/convergence provenance;
- `linear_xps_background` using measured numerical low/high-energy endpoint intensities;
- `shirley_xps_background` independently implemented from the explicit fixed-point integral equation using measured-grid trapezoids, deterministic linear initialization, explicit tolerances/max iterations, exact endpoints, and explicit zero-integral/non-convergence failure;
- direction-equivalent linear/Shirley physical behavior with output restored to source storage order;
- numerical XPS imports remaining Matplotlib-lazy;
- fresh installed-wheel XPS smoke while all existing installed smokes and seven quickstarts remain green.

Fresh prior-art review retained XPyS and pyFitXPS as reference-only sources. `lmfitxps` was also treated as reference-only for Shirley because its LICENSE records GPL-derived inspiration for that implementation; no such implementation code was copied or adapted.

Tougaard, peak fitting, doublet helpers, automatic charge correction, literature lookup, chemistry assignment, smoothing/normalization, plotting, and global/sequential XPS analysis remain outside stage B.

Full behavior is documented in [`XPS.md`](XPS.md).

### Active next scientific block — constrained XPS fitting

After the docs-only #81 checkpoint, implementation proceeds to constrained XPS components/doublets as a domain consumer of the existing shared fitter.

Required contract:

- input is an explicitly validated/prepared XPS region;
- background is explicit zero or an `XPSBackgroundResult` aligned to the exact source region grid and numerical identity;
- XPS component state translates into the shared `PeakComponentSpec` / `PeakFitSpec` contracts rather than introducing a second optimizer;
- spin-orbit doublets use linked components with caller-supplied separation, amplitude/area ratio, and width tie policy;
- shared public `{component.parameter}` constraints remain the underlying tie mechanism;
- XPS fitting results retain enough preparation and fit provenance to audit the complete chain;
- assignment labels are metadata only and do not prove oxidation state/speciation.

Explicit non-goals of the active block:

- no automatic peak detection or component-count choice;
- no hidden textbook/literature lookup of binding energies, doublet separation, branching ratio, peak shape, or width relation;
- no automatic charge correction;
- no hidden background selection/recomputation;
- no smoothing or normalization;
- no chemical-state inference;
- no publication plotting yet;
- no global/sequential multi-spectrum fitting unless separately contracted.

### Later v0.4 dependency order

1. constrained XPS components/doublets and shared-fit integration;
2. XPS publication plotting and diagnostics;
3. EIS plotting and basic equivalent-circuit fitting;
4. quantitative BET fitting;
5. product calibration / GC-HPLC-NMR quantification;
6. completion-state synchronization and later release gates.

## Mandatory development loop

Every new scientific feature follows the same merge path:

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
    -> merge gate
    -> expected-head squash merge
    -> main verification
    -> issue closure
```

A feature is not complete because code exists or a local/old CI run passed. Completion requires the final exact head to satisfy the scientific contract, public API/compatibility expectations, CI, documentation, and Issue acceptance criteria.

For release-hardening or version-gate work, use the same exact-head discipline but substitute release/API/packaging/version review as appropriate.

## Prior-art rule

Before coding a new scientific or visualization feature:

1. survey comparable open-source GitHub/scientific-Python projects;
2. identify useful equations, data-processing patterns, API/data-model ideas, visualization approaches, and regression-test cases;
3. record licenses;
4. distinguish architecture/reference-only use from dependencies or copied/adapted implementation;
5. record decisions in [`REFERENCES.md`](REFERENCES.md) and the module-specific scientific document/Issue where appropriate.

Permissive prior art is not copied automatically. GPL, mixed-provenance, missing-license, or otherwise restrictive projects may be useful reference-only sources, but implementation reuse must respect license compatibility.

## Scientific and API guardrails

Across releases:

- units, reference states, normalization bases, sign conventions, fit windows, stoichiometry, constraints, and denominator bases are explicit rather than inferred from display labels;
- numerical processing and visualization remain separate responsibilities;
- stable keys, not display labels, address sample/component-specific state;
- derived results retain deterministic source identity and enough analysis state to remain auditable;
- scientific incompatibilities fail explicitly instead of being silently aligned, converted, clipped, renormalized, smoothed, or corrected;
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
- second review is performed after all fixes on the final exact head;
- docs describe the behavior actually present in that head;
- behind=0, mergeable state is true, unresolved review threads are zero;
- merge uses the same head SHA that passed final CI/review.

After squash merge, re-read `main`. When connector visibility does not expose a main-push CI run, do not mislabel an older PR run as main CI evidence.

## Documentation roles

- [`../README.md`](../README.md): user-facing overview, installation, public capability summary, and links.
- [`MASTER_PLAN.md`](MASTER_PLAN.md): project-wide execution order, checkpoint summary, governance, and quality gates.
- [`ROADMAP.md`](ROADMAP.md): long-range release scope; not a per-commit log.
- [`V0_4_PLAN.md`](V0_4_PLAN.md): active v0.4 dependency order and scientific/API boundaries.
- [`PEAK_FITTING.md`](PEAK_FITTING.md): reviewed shared-fitting contract.
- [`XPS.md`](XPS.md): reviewed XPS semantics, energy-correction, region, and background-preparation contract.
- [`REFERENCES.md`](REFERENCES.md): prior-art projects, useful ideas, licenses, and dependency/reference-only decisions.
- module-specific documents: exact scientific/API contracts for implemented modules.
- GitHub Issues: active acceptance criteria.
- GitHub Pull Requests: concrete diff, review evidence, CI state, and merge decision.

## State-maintenance rule

After each merged scientific Issue, update only documentation whose statements became false or materially incomplete. Before starting the next feature, verify:

- live `main` HEAD;
- open Issues/PRs;
- current release plan;
- public capability claims;
- whether the preceding Issue is actually closed/completed;
- version/tag/publication boundaries.

The post-XPS-preparation checkpoint is Issue #81. After it merges, the next active scientific Issue should implement constrained XPS fitting without reopening the completed shared-fitting or XPS-preparation architecture.
