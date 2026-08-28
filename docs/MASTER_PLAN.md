# CatalysisWorkbench Master Plan

This document is the current project-level execution map. Detailed historical implementation and release evidence remains in the retained version-specific plans, release documents, Issues, Pull Requests, commits, and CI runs.

## Authority and source of truth

GitHub is the operational source of truth. When descriptive documents disagree with live repository state, use this precedence order:

1. merged `main` code and tests;
2. current Pull Requests and Issues;
3. exact-head CI for the commit under review;
4. version-specific architecture/release plans;
5. this master plan, roadmap, and README summaries.

Documentation must be corrected when it drifts; it never overrides merged code, exact CI, or explicit release decisions.

## Current checkpoint — 2026-08-28

Repository: `xcwang3333-cloud/catalysis-workbench`.

- default/integration branch: `main`;
- current exact main: `ad73fc4725131310919cddc6b78307fbe5f8c17d`;
- development version: `1.0.0.dev0`;
- v1.0 Blocks 1-6: complete and merged;
- latest completed block: Block 6 via PR #294 / squash merge `ad73fc4725131310919cddc6b78307fbe5f8c17d`;
- Block-6 post-merge CI: #736 / run `33156625277`, success;
- retained stable tag/GitHub Release: `v0.7.0 -> e3062fc12c794f54c7b7613875ec73608a587a59`;
- routine v0.8/v0.9 tags or GitHub Releases: not planned;
- stable `1.0.0`, v1.0 tag, GitHub Release, and PyPI publication: not authorized by development work and separately gated.

The v0.8 operando/time-resolved scientific implementation and the v0.9 reproducible-workflow foundation are complete development milestones carried into v1.0. The six-block v1.0 local-workbench implementation is now complete on `main`; the next project phase is the Stable 1.0 maturity gate, not an implicit Block 7.

## Historical release summary

- v0.1-v0.6 remain valid historical development/release milestones. Their old tag/Release artifacts were intentionally removed, while implementation commits, Issues/PRs, CI and version-specific documents remain retained.
- v0.7 is the only currently retained stable GitHub Release/tag.
- v0.8 is a completed scientific implementation milestone with no standalone release cycle.
- v0.9 is the completed reproducible-workflow development foundation and has no routine release artifact.
- v1.0 is a completed six-block development implementation at version `1.0.0.dev0`; stable release finalization remains separately gated.

Historical technical details should be read from `V0_X_PLAN.md`, `V0_X_RELEASING.md`, technique documents, and GitHub evidence rather than duplicated indefinitely in this central file.

## v1.0 architecture authority

The architecture checkpoint is PR #287, merged as:

`00e1d44d1a42df2a7889e21b6d116d26513020ba`

Dependency direction is frozen as:

```text
core / processing / io / experimental / computation / visualization
                              ↓
                           workflow
                              ↓
                          workspace
                              ↓
                         application
                              ↓
                     desktop presentation
```

v1.0 is primarily workspace/application integration, not a new scientific-algorithm expansion phase.

## v1.0 implementation status

### Block 1 — Workspace foundation — complete

PR #288 merged as `a8ee1f8f09747c3932e437b481e9ec98d6724a53`.

Delivered strict file-backed workspace manifests, ordered immutable assets, deterministic canonical JSON/SHA-256 identity, explicit root confinement, fail-closed symbolic-link handling, and the transition to development version `1.0.0.dev0`.

### Block 2 — Explicit asset import/catalog — complete

PR #289 merged as `ebf449c328346948363b831e8c2ef731b23644e2`.

Delivered explicit caller-selected sources, stable asset IDs/types, explicit `copy` versus `reference` policy, retained-byte content digests, collision prevalidation, literal asset order, copy rollback limited to import-created paths, and no parser/technique guessing.

### Block 3 — Persistent evidence ledger — complete

PR #291 merged as `7cd8ea4500ac5c3d6beab3234935826a6d48e030`.

Delivered deterministic file-backed evidence records that reference existing reviewed recipe/run/batch/QA/content identities rather than inventing a second scientific provenance engine. No database, retry engine, or background service was introduced.

PR #290 is not the promoted Block-3 implementation; live GitHub state remains authoritative for any superseded/stale PR cleanup.

### Block 4 — Workspace workflow/figure composition — complete

PR #292 merged as `84ba0ae04e56482333d0953af576c2979fc02848`.

Delivered reviewed recipe/FigureSpec/preset snapshot bridges, explicit input/output asset associations, content/evidence digest pinning, exported-figure composition state, and literal ordered recipe editing. DAG scheduling/topological semantics remain explicitly excluded.

### Block 5 — GUI-neutral application/session controller — complete

PR #293 merged as `81900cdd73db7cb02febbcebf619cbcd25cdf1d0`.

Delivered immutable/transaction-safe `ApplicationState` and `ApplicationSession`, explicit workspace selection/refresh, ordered asset and recipe state, reviewed workflow execution with explicit inputs/identities, explicit QA aggregation, FigureSpec state editing, and fail-closed manifest-race handling. No desktop toolkit is imported by the application layer.

### Block 6 — Optional desktop shell and v1.0 API hardening — complete

PR #294 merged as `ad73fc4725131310919cddc6b78307fbe5f8c17d`.

Post-merge CI #736 / run `33156625277` succeeded on the exact merge/main SHA with:

- `test` — success;
- `package-smoke` — success;
- `volumetric3d-smoke` — success; and
- `desktop-smoke` — success.

The separately authorized dependency decision remains:

```text
optional extra: desktop
PySide6-Essentials>=6.11.2,<6.12
```

Block 6 delivered a lazy Qt Widgets presentation shell, application workspace-action hardening, independent offscreen installed-wheel CI, user-facing desktop documentation, import-laziness checks, and central documentation/API synchronization.

The shell provides local workspace creation/opening, project/asset navigation, explicit file import, ordered recipe inspection/editing, run/evidence/QA inspection, FigureSpec presentation controls, and an explicit integration hook to the existing Matplotlib FigureSpec editor.

It does not introduce parser guessing, recursive discovery, automatic QA selection, scientific algorithms, arbitrary callable execution, dynamic operation discovery, DAG scheduling, silent data correction, database/server/cloud scope, or Qt imports in lower layers.

## Next phase — Stable 1.0 maturity gate

Completing Blocks 1-6 does not itself authorize a stable release.

The next scoped project phase is a release-readiness audit that must review at least:

- final supported public API and compatibility surface;
- the exact `1.0.0.dev0` to `1.0.0` version transition;
- project license and Qt/PySide6 third-party distribution obligations;
- fresh-wheel installation for supported platforms, including `[desktop]`;
- release notes/changelog and package metadata;
- exact release-candidate SHA and tag target;
- whether to create a GitHub Release; and
- whether to publish to PyPI/package registry.

Stable version finalization, tag creation, GitHub Release publication, and registry publication remain separate explicit authorization gates.

## Scientific and reproducibility invariants

Across current and future work:

- units, reference states, normalization bases, signs, fit windows, stoichiometry and other scientific choices remain explicit;
- scientifically meaningful source/acquisition/recipe/batch/asset order is preserved unless an explicit reviewed operation says otherwise;
- no hidden alignment, interpolation, resampling, sorting, normalization or unit conversion;
- incompatible state fails closed instead of being silently repaired;
- deterministic identities exclude timestamps, host/PID/temp-path/UI-selection noise unless separately stored as non-identity metadata;
- QA produces evidence and does not mutate scientific results;
- presentation editing never changes scientific result state;
- serialized/workspace state cannot request arbitrary Python callables or dynamic imports;
- existing reviewed scientific APIs remain authoritative under workspace/application/desktop convenience layers.

## Dependency policy

Normal core/scientific dependencies remain controlled through explicit architecture review.

The v1.0 Block-6 Qt toolkit is optional and isolated behind the `desktop` extra. Base installs, ordinary package smoke, and the application/workspace layers remain Qt-free.

Any future new runtime or optional dependency requires a fresh review of role, license, distribution burden, supported platforms, import strategy, headless CI, and no-dependency alternatives before `pyproject.toml` changes.

## Mandatory development loop

```text
latest exact main
→ scoped feature branch
→ implementation + focused regressions
→ Draft PR
→ exact-head GitHub CI
→ formal diff/review
→ fixes and new exact-head CI when required
→ final review of final head
→ Ready
→ separate user merge authorization
→ expected-head squash merge
→ exact main verification
→ post-merge main CI verification
```

Ready does not authorize merge.

Without separate explicit authorization, do not:

- merge a PR;
- delete a branch;
- create or move a v1.0 tag;
- create a GitHub Release;
- finalize stable `1.0.0`; or
- publish to PyPI/package registry.

## Prior-art rule

Before new scientific, workflow, workspace, application, or visualization architecture is implemented:

1. search relevant open-source GitHub/scientific-Python projects;
2. record useful architecture, algorithms, validation/test ideas and license constraints;
3. distinguish architecture-only references from dependencies or copied/adapted implementation;
4. do not copy permissive or restrictive source merely because it exists; and
5. perform exact-version provenance/license review before any external code adaptation.

Current v1.0 references include signac, pyiron_base, AiiDA, Orange3, Kedro concepts inherited from v0.9, and napari for desktop/application separation. References are architecture-only unless a separate dependency decision explicitly says otherwise.

## Documentation roles

- [`../README.md`](../README.md) — user-facing current capabilities, installation and boundaries.
- [`ROADMAP.md`](ROADMAP.md) — long-range version/maturity direction.
- [`V1_0_PLAN.md`](V1_0_PLAN.md) — frozen v1.0 architecture and block contracts.
- [`DESKTOP.md`](DESKTOP.md) — optional desktop installation, behavior, layering and headless-CI contract.
- `V0_X_PLAN.md` / `V0_X_RELEASING.md` — retained historical architecture/release evidence.
- technique-specific documents — reviewed scientific contracts.
- [`REFERENCES.md`](REFERENCES.md) — long-lived open-source/scientific prior-art notes.
- GitHub PRs/Issues/CI — concrete operational evidence and current promotion state.

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
