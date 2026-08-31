# CatalysisWorkbench Master Plan

This document is the current project-level execution map. Detailed historical implementation and release evidence remains in version-specific plans, release documents, Issues, Pull Requests, commits, and CI runs.

## Authority and source of truth

GitHub is the operational source of truth. When descriptive documents disagree with live repository state, use this precedence order:

1. merged `main` code and tests;
2. current Pull Requests and Issues;
3. exact-head CI for the commit under review;
4. version-specific architecture/release plans;
5. this master plan, roadmap, and README summaries.

Documentation must be corrected when it drifts; it never overrides merged code, exact CI, or explicit release decisions.

## Current checkpoint — v1.1 Gate B final-version candidate

Repository: `xcwang3333-cloud/catalysis-workbench`.

Stable baseline:

- stable version/tag: `v1.0.0`;
- exact stable tag target: `22b944992bfd3791f91cc951f89eb22e8bf47325`;
- GitHub Release: `CatalysisWorkbench v1.0.0`, published;
- project license: BSD-3-Clause;
- PyPI/package-registry publication: not performed.

Current v1.1 candidate:

- final-version candidate: `1.1.0`;
- v1.1 Blocks 1–6: complete and merged;
- Stable 1.1 Gate A squash merge / Gate-B baseline: `843df51828d740405aa5365142541ed361e069cc`;
- Gate-A post-merge CI #854: success;
- Gate-A post-merge Stable 1.0 Readiness #116: success;
- Gate-A post-merge Stable 1.1 Readiness #3: success;
- current phase: Stable 1.1 Gate B — mechanical final-version candidate synchronization.

Gate A release hardening is complete. Gate B changes only release identity/evidence to exact `1.1.0`. The `v1.1.0` tag, GitHub Release publication, installers, and package-registry publication remain later separately authorized gates.

## Historical milestone summary

### v0.1–v0.7

The early releases established the reviewed scientific analysis surface: common immutable XY state, electrochemistry, characterization, constrained fitting, product calibration, structures, XAS/EXAFS, electronic-structure analysis, catalysis thermodynamics, and advanced computational visualization.

`v0.7.0` remains a retained historical stable tag/Release at `e3062fc12c794f54c7b7613875ec73608a587a59`.

### v0.8 — operando/time-resolved science

Completed development milestone with immutable exact-grid stacks, measured-grid operations, passive time-resolved visualization, technique adapters, descriptor trajectories, and explicit cross-modal comparison. No routine standalone v0.8 tag/Release was created.

### v0.9 — reproducible workflows

Completed development milestone with explicit sequential `WorkflowRecipe` state, deterministic workflow-run evidence, batching, QA, publication presets, and FigureSpec integration. Literal recipe order remains authoritative; v0.9 did not become a DAG scheduler or dynamic callable system.

### v1.0 — reproducible local workbench

The six v1.0 implementation blocks delivered:

1. strict local workspace/manifest persistence;
2. explicit asset import/catalog with copy/reference policy and content digests;
3. persistent evidence ledger;
4. workspace recipe/FigureSpec composition;
5. GUI-neutral transaction-safe `ApplicationSession`; and
6. optional lazy PySide6 desktop plus API/install hardening.

Stable 1.0 maturity work then finalized `1.0.0`, created and reverse-verified `v1.0.0` at `22b944992bfd3791f91cc951f89eb22e8bf47325`, and published the corresponding GitHub Release. PyPI remained deferred.

## v1.1 product direction

v1.1 changes the ordinary-user desktop interaction model without replacing the reviewed lower-layer scientific/workflow/workspace contracts.

Product position:

> a task-driven catalysis data-analysis and publication-figure workbench for research users, not a workflow editor.

Frozen ordinary-user path:

```text
Home
  -> choose analysis goal
  -> import and map data
  -> configure explicit scientific processing
  -> inspect live analysis
  -> edit presentation-only Figure state
  -> export Figure Package + scientific source data
```

Recipe, Workspace, Evidence, SHA identities, and backend FigureSpec details stay behind normal-user task surfaces unless an explicit compatibility/advanced path needs them.

## v1.1 block status

### Block 1 — Analysis Document + Home shell — complete

Introduced the task catalog, deterministic `AnalysisDocument`, independent `AnalysisSession`, Home task cards, recent-project history, and clean first-save semantics. Development version advanced to `1.1.0.dev0` while frozen v1.0 compatibility gates remained active.

### Block 2 — Data Intake & Mapping — complete

Added bounded preview, explicit X/Y scientific mapping, path-independent source/mapping identities, verified raw-byte ownership, first-save staging, mapped-series management, and raw materialization without hidden scientific transforms.

### Block 3 — Live Scientific Analysis — complete

Added explicit LSV processing, FE/current pairing and partial-current calculation, Generic XY analysis-range handling, deterministic internal workflow compilation/evaluation, valid-state commit semantics, and stale previous-valid result presentation.

### Block 4 — Figure Workbench — complete

Added schema-4 presentation-only `FigureDraft` state bound to exact scientific trace identities, explicit stale/refresh semantics, publication preview, physical figure sizing, display ranges, legend/typography/line/marker styling, and immutable scientific-processing boundaries.

### Block 5 — Figure Package Export — complete

Added SVG/PDF/PNG publication output plus XLSX/TXT scientific source data, path-independent package semantic identity, exact per-file hashes, workspace provenance, fail-closed publication/rollback, and task-first export preflight.

Block-5 exact post-merge main is `eec2f85d117902459178f65c4543b5674de54912`; CI #832 and Stable 1.0 Readiness #94 both succeeded on that exact commit.

### Block 6 — Dogfooding Hardening & Desktop Cleanup — complete

Architecture contract: [`V1_1_BLOCK6.md`](V1_1_BLOCK6.md).

Block 6 is intentionally narrow:

- complete fresh-wheel Generic XY, LSV, and FE/Partial Current journeys from real file-backed inputs through Figure Package and reopen verification;
- add explicit Save Project from Export preflight;
- add post-export Open Folder / Export Another affordances;
- present actionable desktop error summaries while retaining exact technical details;
- avoid reopening unchanged Recent Projects on every presentation refresh;
- provide a normal-user `catalysis-workbench` command with Qt-free `--version` and explicit v1.1 `--project` routing; and
- reconcile central documentation with the real stable-v1.0/current-v1.1 state.

Block 6 does **not** add scientific algorithms, new task families, a new `AnalysisDocument` schema, hidden interpolation/resampling, autosave, automatic stale-Figure refresh, package overwrite/merge, new dependencies, servers/cloud state, or release publication. It was squash-merged as `c81ee2e1aa8767e1560a14c5f7f4c1209fc4b6f9`; post-merge CI #851 and Stable 1.0 Readiness #113 succeeded. Stable 1.1 Gate A later squash-merged as `843df51828d740405aa5365142541ed361e069cc` and passed post-merge CI #854, Stable 1.0 Readiness #116, and Stable 1.1 Readiness #3. Gate B is now the active final-version candidate phase.

## Scientific and reproducibility invariants

Across all current and future work:

- units, reference states, normalization bases, signs, fit windows, stoichiometry, and other scientific choices remain explicit;
- scientifically meaningful source/acquisition/recipe/batch/asset order is preserved unless an explicit reviewed operation says otherwise;
- there is no hidden alignment, interpolation, resampling, sorting, normalization, or unit conversion;
- incompatible state fails closed instead of being silently repaired;
- deterministic identities exclude timestamps, host/PID/temp-path/UI-selection noise unless separately stored as non-identity metadata;
- QA produces evidence and does not mutate scientific results;
- presentation editing never changes scientific result state;
- serialized/workspace state cannot request arbitrary Python callables or dynamic imports; and
- existing reviewed scientific APIs remain authoritative under workflow/workspace/application/desktop convenience layers.

## Dependency policy

Normal core/scientific dependencies remain controlled through explicit architecture review.

The desktop toolkit remains the separately reviewed optional extra:

```text
PySide6-Essentials>=6.11.2,<6.12
```

Base installs and application/workspace layers remain Qt-free. Block 6 adds no dependency.

Any future dependency requires review of role, license, distribution burden, supported platforms, import strategy, headless CI, and no-dependency alternatives before metadata changes.

## Prior-art rule

Before major scientific, workflow, workspace, application, or visualization architecture is implemented:

1. search relevant open-source GitHub/scientific-Python projects;
2. record useful architecture, validation/test ideas, and license constraints;
3. distinguish architecture-only references from dependencies or copied/adapted implementation;
4. do not copy source merely because it is available; and
5. perform exact-version provenance/license review before any external adaptation.

Current architecture-only references include napari, Orange3, LabPlot, signac, pyiron_base, AiiDA, and Kedro concepts. No Block-6 dependency or copied implementation is introduced from those projects.

## Mandatory development loop

```text
latest exact main
-> scoped feature branch
-> implementation + focused regressions
-> Draft PR
-> exact-head GitHub CI
-> formal diff/review
-> fixes and new exact-head CI when required
-> final review of final head
-> Ready
-> STOP
-> separate user merge authorization
-> expected-head squash merge
-> exact main verification
-> post-merge main CI verification
```

Ready does not authorize merge.

Without separate explicit authorization, do not:

- merge a PR;
- delete a branch;
- change the final-version identity outside an explicitly authorized release gate;
- create/move a v1.1 tag;
- create a v1.1 GitHub Release; or
- publish to PyPI/package registry.

## Documentation roles

- [`../README.md`](../README.md) — user-facing current capabilities, installation, and boundaries.
- [`ROADMAP.md`](ROADMAP.md) — long-range version/maturity direction.
- [`V1_0_PLAN.md`](V1_0_PLAN.md) — frozen v1.0 architecture contract.
- [`V1_1_PLAN.md`](V1_1_PLAN.md) — detailed v1.1 Blocks 1–5 implementation history.
- [`V1_1_BLOCK6.md`](V1_1_BLOCK6.md) — Block-6 dogfooding/hardening contract.
- [`DESKTOP.md`](DESKTOP.md) — desktop installation, behavior, layering, and CI contract.
- `V0_X_PLAN.md` / `V0_X_RELEASING.md` — retained historical architecture/release evidence.
- GitHub PRs/Issues/CI — operational evidence and current promotion state.

## Stop conditions

Stop implementation and report before proceeding if a proposal requires any unreviewed:

- runtime or optional dependency;
- change to existing scientific numerical semantics;
- reinterpretation of literal recipe order as DAG semantics;
- arbitrary callable execution or dynamic import from serialized/workspace state;
- automatic operation/parser/chemistry discovery;
- hidden recursive file discovery;
- ambiguous workspace path ownership or symlink semantics;
- scientific auto-correction by QA/application/desktop code;
- GUI mutation of scientific results outside reviewed APIs;
- database/server/cloud/background-service architecture; or
- destructive Git/release operation.
