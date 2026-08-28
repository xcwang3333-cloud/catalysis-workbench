# CatalysisWorkbench v1.0 Architecture Plan

## 1. Status and authority

This document is the architecture/scope contract for the v1.0 local-workbench development line. It does not itself authorize a merge, stable version, Git tag, GitHub Release, branch deletion, or package-registry publication.

Architecture checkpoint:

- repository: `xcwang3333-cloud/catalysis-workbench`;
- architecture PR: #287;
- architecture merge: `00e1d44d1a42df2a7889e21b6d116d26513020ba`;
- development identity after Block 1: `1.0.0.dev0`;
- Blocks 1-6: complete on `main`;
- Block-6 squash merge: `ad73fc4725131310919cddc6b78307fbe5f8c17d`;
- Block-6 post-merge CI: #736 / run `33156625277`, success;
- retained stable GitHub Release/tag: `v0.7.0`;
- routine v0.8/v0.9 tag/GitHub Release: not planned;
- stable `1.0.0`, v1.0 tag, GitHub Release and PyPI publication: separately gated.

GitHub remote state remains the operational source of truth. Final exact-head implementation/CI/review evidence belongs to the applicable Pull Request.

## 2. Mission

v1.0 turns the reviewed scientific APIs and v0.9 reproducible-workflow foundation into a coherent local research workbench with:

- explicit local workspace/project state;
- explicit user-controlled asset import/catalog state;
- persistent evidence association;
- workspace recipe/figure composition;
- a GUI-neutral transaction-safe application/session layer; and
- an optional desktop presentation shell.

v1.0 is not another scientific-algorithm expansion phase. Existing `core`, `processing`, `io`, `experimental`, `computation`, `visualization`, and `workflow` contracts remain authoritative.

## 3. Dependency direction

Dependency direction is one-way:

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

### Workspace

`catalysis_workbench.workspace` owns explicit persistent local project state and references to reviewed evidence. It does not own scientific algorithms, parser inference, or workflow scheduling.

### Application

`catalysis_workbench.application` owns GUI-neutral session state and user-action orchestration. It coordinates reviewed workspace/workflow/visualization APIs without changing their scientific semantics.

### Desktop

`catalysis_workbench.desktop` is optional presentation/interaction only. It must not contain a second scientific engine, provenance engine, workspace implementation, parser policy, QA policy, or workflow scheduler.

## 4. Frozen scientific and workflow invariants

Throughout v1.0:

- no hidden sorting of scientifically meaningful sequences;
- no hidden interpolation or resampling;
- no silent normalization or unit conversion;
- no automatic chemistry/species/phase interpretation;
- preserve reviewed provenance rather than reconstructing it heuristically;
- fail closed on incompatible state;
- preserve source, acquisition, recipe-step, batch-item, asset and explicit evidence order where identity-bearing;
- QA remains evidence-producing and non-mutating;
- presentation editing never mutates scientific results;
- serialized/workspace state cannot request arbitrary Python callables;
- serialized/workspace state cannot trigger dynamic operation imports/discovery; and
- convenience layers adapt to reviewed scientific APIs rather than changing those APIs to simplify a UI.

v0.9 recipe execution remains literal ordered execution. v1.0 does not reinterpret `WorkflowRecipe` as a DAG, infer dependencies, topologically sort steps, repair forward references, or introduce hidden parallelism.

## 5. Workspace identity and path contract

The first v1.0 workspace is strict, local and file-backed.

Identity/persistence rules:

- explicit schema versions;
- ordered identity-bearing state;
- deterministic canonical JSON SHA-256;
- strict unknown-field and duplicate-key rejection;
- validation before persistent mutation;
- explicit overwrite semantics;
- no absolute workspace root, host, user, PID, timestamp, temp filename or GUI-selection state in deterministic identity.

Workspace-owned paths must be explicit relative paths rooted at the workspace root supplied at the IO boundary. The initial contract rejects absolute/drive-qualified paths, `..`, root escape, ambiguous empty paths, workspace-owned symbolic links and symbolic-link traversal.

External references are distinct from workspace-owned copies. An explicit external reference may live outside the workspace root but must never be silently rewritten into a workspace-owned path.

No workspace layer recursively crawls directories or infers assets automatically.

## 6. Asset contract

Assets use caller-visible stable identifiers and explicit policy.

Initial categories include source files, recipes, workflow/batch/QA evidence references, FigureSpec/preset state and exported artifacts.

Asset type is catalog state, not scientific interpretation. The workspace/desktop layers do not infer a scientific technique, parser, species or unit from a filename.

Policies:

- `reference` retains an explicit external source path;
- `copy` creates an explicit workspace-owned file;
- neither policy silently substitutes for the other.

Where file bytes are identity-bearing, SHA-256 is calculated from retained bytes rather than using paths as content identity.

## 7. Evidence contract

v1.0 persists associations among existing reviewed identities rather than inventing parallel scientific provenance.

Evidence may reference:

- `WorkflowRecipe.recipe_sha256`;
- `WorkflowRun.record_sha256`;
- `BatchRunRecord.record_sha256`;
- `QAReport.report_sha256`;
- workspace asset content SHA-256; and
- figure/export identities composed from reviewed state.

The first ledger is schema-versioned file-backed state. SQL, ORM, migration frameworks, servers and background services are excluded.

## 8. Block 1 — Workspace foundation — complete

PR #288; squash merge `a8ee1f8f09747c3932e437b481e9ec98d6724a53`.

Delivered:

- `WorkspaceManifest`, `WorkspaceAsset`;
- `create_workspace()`, `open_workspace()`, `save_workspace()`;
- immutable ordered asset state;
- deterministic canonical JSON/SHA-256 identity;
- explicit root confinement and fail-closed symlink behavior;
- transaction-safe persistence hardening; and
- development version transition to `1.0.0.dev0`.

No crawling, scientific import, workflow execution, database or new dependency was introduced.

## 9. Block 2 — Explicit asset import/catalog — complete

PR #289; squash merge `ebf449c328346948363b831e8c2ef731b23644e2`.

Delivered `workspace.assets.import_asset()` with:

- explicit caller-selected source;
- stable asset ID and explicit asset type;
- explicit `reference` versus `copy`;
- retained-byte content digest;
- literal caller order;
- collision prevalidation;
- Block-1 path confinement for copies;
- external references remaining explicitly external;
- source retention/no silent move-delete;
- no recursive scanning or parser guessing; and
- rollback limited to paths created by the failed copy import.

The reviewed `catalysis_workbench.io` layer remains the scientific IO authority.

## 10. Block 3 — Persistent evidence ledger — complete

Promoted implementation: PR #291; squash merge `7cd8ea4500ac5c3d6beab3234935826a6d48e030`.

Delivered schema-versioned local evidence records and ledger persistence with deterministic ordered identity and explicit links to current workspace assets/related records.

Block 3 reuses existing reviewed recipe/run/batch/QA/content digests. It does not execute workflows or QA, retry failures, invent traceback/timestamp provenance, or require a database.

PR #290 was not the promoted Block-3 implementation; live GitHub state remains authoritative for superseded PR cleanup.

## 11. Block 4 — Workspace recipe/figure composition — complete

PR #292; squash merge `84ba0ae04e56482333d0953af576c2979fc02848`.

Delivered:

- recipe snapshot/load through reviewed v0.9 serializers;
- explicit recipe input/output asset associations;
- content SHA-256 pinning for associated assets;
- FigureSpec and preset-bundle snapshot bridges;
- figure export/evidence composition with evidence digest pinning;
- literal ordered recipe insert/replace/remove/move helpers; and
- reserved workspace-composition metadata ownership.

Ordered editing is not DAG execution. No topological sort, operation discovery, dynamic imports, arbitrary callables or scientific-data mutation is introduced.

## 12. Block 5 — GUI-neutral application/session controller — complete

PR #293; squash merge `81900cdd73db7cb02febbcebf619cbcd25cdf1d0`.

Delivered:

- immutable `ApplicationState`;
- transaction-safe `ApplicationSession`;
- explicit workspace open/close/refresh and asset selection;
- recipe select/edit/save through reviewed composition APIs;
- explicit workflow execution through `execute_recipe()` using caller-supplied inputs and identities;
- QA aggregation only from explicit reviewed findings;
- FigureSpec select/edit/save through reviewed APIs; and
- fail-closed manifest race/TOCTOU handling.

Application import remains GUI-toolkit-free and headless-testable.

## 13. Block 6 — Optional desktop shell + v1.0 API hardening — complete

PR #294; squash merge `ad73fc4725131310919cddc6b78307fbe5f8c17d`.

Final exact-head promotion evidence remains recorded in PR #294. Post-merge CI #736 / run `33156625277` completed successfully on the exact merge/main SHA, with `test`, `package-smoke`, `volumetric3d-smoke`, and `desktop-smoke` all green.

### Authorized dependency decision

The separately approved GUI dependency is:

```text
optional extra: desktop
PySide6-Essentials>=6.11.2,<6.12
```

The dependency is optional, not a normal runtime dependency. The first shell needs Qt Core/Gui/Widgets and does not require the larger PySide6 Addons wheel.

The base install and lower layers remain Qt-free. `catalysis_workbench.desktop` itself is lazy; importing the package does not load PySide6. Requesting a desktop class/launcher without the extra raises a targeted dependency error.

### User-facing scope

Block 6 provides:

- local workspace creation/opening;
- project/asset navigation;
- explicit file chooser/import;
- ordered recipe inspection/editing/save;
- run/result/evidence inspection;
- scientific QA evidence inspection;
- FigureSpec presentation controls;
- explicit integration with the existing Matplotlib FigureSpec editor; and
- export-oriented presentation state.

### Application hardening

Desktop-facing workspace operations are routed through GUI-neutral application wrappers. Workspace create/open/close/import transitions fail closed around dirty recipe/FigureSpec state unless discard is explicit.

The shell does not infer workflow runtime inputs from catalog files, auto-select QA checks, guess scientific parsers from file extensions, or create a second persistence implementation.

### CI and packaging

Existing `test`, `package-smoke` and `volumetric3d-smoke` remain Qt-free.

A separate `desktop-smoke`:

- builds the exact wheel;
- installs `catalysis-workbench[desktop]` in a fresh environment;
- runs `pip check`;
- uses `QT_QPA_PLATFORM=offscreen`;
- creates/destroys the Qt application/window without a persistent event loop; and
- exercises representative workspace, asset, recipe, evidence/QA and figure bindings.

Base-wheel smoke separately protects Qt import laziness and verifies application/workspace use without the desktop extra.

See [`DESKTOP.md`](DESKTOP.md).

## 14. Explicit non-goals

Current v1.0 does not include:

- new scientific-analysis algorithms merely to populate the GUI;
- a new DAG/workflow execution engine;
- implicit dependency inference or topological scheduling;
- multiprocessing/distributed/cloud/HPC scheduling;
- instrument control;
- cloud synchronization or collaborative multi-user server state;
- online plugin marketplace;
- arbitrary third-party code execution from workspace files;
- automatic recursive discovery;
- automatic chemistry/species/phase assignment;
- silent scientific correction/cleaning;
- mandatory SQL/database infrastructure; or
- package-registry publication as a feature side effect.

## 15. Prior-art and license decisions

References are architecture/UX concepts only unless separately stated. No external source, widget code, asset, schema or dependency is copied merely by being surveyed.

### signac — BSD-3-Clause

Reference for file-system-oriented project/data organization and reproducibility metadata separation. No dependency/code reuse.

### pyiron_base — BSD-3-Clause

Reference for project/job/application layering and separation from scientific backends. No dependency/code reuse.

### AiiDA core — MIT

Reference for provenance/orchestration separation. AiiDA database/scheduler/daemon/SSH/distributed infrastructure is deliberately outside v1.0. No dependency/code reuse.

### Orange3 — GPL-3.0+

Reference for desktop interaction and analysis/presentation separation only. No GPL code/widgets/assets are copied or adapted and Orange3 is not a dependency.

### napari — BSD-3-Clause

Block-6 architecture reference for separating Qt main-window/presentation infrastructure from analytical/model concerns and for optional Qt-oriented packaging patterns. No napari source, widget code, assets, schema or dependency is copied/adapted/vendored.

### Existing v0.9 references

Kedro, signac, SciencePlots and Matplotlib widget/event references recorded by the v0.9 architecture remain valid within their original boundaries. v1.0 does not broaden reuse permissions.

Any future proposal to copy/adapt external code requires an exact-version provenance/license review.

## 16. Dependency policy

Blocks 1-5 introduced no new runtime or optional dependency.

Block 6 has one separately authorized optional GUI dependency:

```text
PySide6-Essentials>=6.11.2,<6.12
```

No dependency is added merely because a prior-art project uses it.

Any future dependency change requires a fresh review of role, placement, current license/distribution implications, wheel burden/platform coverage, headless CI, lazy import strategy, public API impact and viable no-new-dependency alternative.

## 17. Validation discipline

Every implementation head requires at minimum:

```bash
python -m ruff check .
python -m pytest
```

Public API, packaging or dependency changes additionally require exact-wheel/fresh-environment validation and `pip check`.

Desktop validation additionally requires:

- base-environment Qt-laziness checks;
- fresh `[desktop]` wheel installation;
- offscreen Qt smoke without a persistent event loop; and
- headless-testable application/controller paths.

Local validation is diagnostic only. Formal promotion requires GitHub CI and final review on the same exact PR head.

## 18. Git and promotion discipline

```text
latest exact main
→ scoped feature branch
→ implementation + focused validation
→ Draft PR
→ exact-head GitHub CI
→ formal diff/review
→ fixes and fresh exact-head CI when required
→ final review of final head
→ Ready
→ separate user merge authorization
→ expected-head squash merge
→ exact main verification
→ post-merge main CI verification
```

No direct push to `main`.

Without separate explicit authorization, do not merge, delete a branch, create/move a v1.0 tag, create a GitHub Release, finalize stable `1.0.0`, or publish to a package registry.

## 19. Documentation state

The earlier central README/MASTER_PLAN/ROADMAP descriptions that said current `main` remained at `0.7.0` or future work was only `0.9.0.dev0` were descriptive drift. Block 6 synchronized those central documents to the real v1.0 `1.0.0.dev0` development state.

This completion checkpoint records that Blocks 1-6 are now merged and post-merge validated. The next project phase is stable-1.0 maturity review, not an implicit Block 7.

Historical release/scientific details remain retained in version-specific plans/releasing documents and GitHub provenance rather than being duplicated indefinitely in central status files.

## 20. Stop conditions

Stop implementation and report before proceeding if a proposed change requires an unreviewed:

- runtime or optional dependency;
- modification of established scientific numerical semantics;
- reinterpretation of recipe order as DAG semantics;
- arbitrary callable execution/dynamic imports from serialized state;
- automatic operation/parser/chemistry discovery;
- hidden recursive discovery or sequence sorting;
- ambiguous workspace path ownership/symlink behavior;
- scientific auto-correction by QA/application/desktop code;
- GUI mutation of scientific results outside reviewed APIs;
- database/server/cloud/background-service architecture; or
- destructive Git/release operation.

## 21. Development completion checkpoint and next gate

The six-block v1.0 development implementation is complete on `main@ad73fc4725131310919cddc6b78307fbe5f8c17d`, with post-merge CI #736 successful.

This is still a development checkpoint, not a stable release. The next separately scoped phase is the Stable 1.0 maturity gate, which must review at least:

- final supported public API and compatibility surface;
- the exact `1.0.0.dev0` to `1.0.0` version transition;
- project license plus Qt/PySide6 third-party distribution obligations;
- fresh-wheel installation on supported platforms, including the optional `[desktop]` extra;
- release notes/changelog and package metadata;
- exact tag target and release-candidate SHA;
- whether to create a GitHub Release; and
- whether to publish to PyPI or another package registry.

None of those release actions is authorized by this document checkpoint.
