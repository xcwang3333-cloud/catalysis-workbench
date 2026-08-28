# CatalysisWorkbench v1.0 Architecture Plan

## 1. Status and authority

This document defines the proposed v1.0 development architecture after completion
of all six v0.9 implementation Blocks. It is an architecture/scope contract, not
a release artifact, and does not itself authorize a merge, tag, GitHub Release,
or package-registry publication.

Architecture-planning baseline:

- Repository: `xcwang3333-cloud/catalysis-workbench`
- Default branch: `main`
- Exact baseline SHA: `5feec0520c36f418a6d0b84bfe8fd7c331916563`
- Baseline development version: `0.9.0.dev0`
- v0.9 Blocks 1-6: complete on `main`
- Retained stable GitHub Release/tag: `v0.7.0`
- v0.8/v0.9 routine tag or GitHub Release: not planned
- PyPI/package-registry publication: separately gated and currently deferred

GitHub remote state remains the formal operational source of truth. If this plan
later drifts from merged code, exact-head CI, PR state, or an explicit user
decision, live repository state wins and the document must be corrected.

The architecture checkpoint keeps version `0.9.0.dev0`. The first approved v1.0
implementation Block is the appropriate point to begin the `1.0.0.dev0`
development identity. This plan does not declare a stable `1.0.0` release.

## 2. v1.0 mission

v1.0 turns the reviewed scientific APIs and v0.9 reproducible workflow layer
into a coherent local research workbench with explicit project/workspace state,
persistent evidence, and an application layer suitable for a desktop UI.

Primary scope:

- local reproducible workspace/project state;
- explicit user-controlled asset import/catalog state;
- persistent run, QA, and figure evidence association;
- workspace composition of recipes, figures, and generated artifacts;
- a GUI-neutral application/session controller; and
- a dependency-gated desktop shell plus v1.0-facing API hardening.

v1.0 is not another scientific-algorithm expansion phase. Existing `core`,
`processing`, `io`, `experimental`, `computation`, `visualization`, and
`workflow` contracts remain authoritative and are consumed rather than
redesigned.

## 3. Architecture boundary

Dependency direction is one-way:

~~~text
core / processing / io / experimental / computation / visualization
                              |
                              v
                         workflow
                              |
                              v
                         workspace
                              |
                              v
                        application
                              |
                              v
                    desktop presentation
~~~

Planned new package boundaries:

~~~text
src/catalysis_workbench/workspace/
src/catalysis_workbench/application/
~~~

A desktop-specific package is added only if a separately reviewed desktop-toolkit
decision authorizes it.

### Workspace responsibilities

`catalysis_workbench.workspace` owns explicit persistent project state and
references to reviewed CatalysisWorkbench objects/evidence. It does not own
scientific algorithms and does not silently execute workflows.

### Application responsibilities

`catalysis_workbench.application` owns GUI-neutral session state and user-action
orchestration. It coordinates workspace operations and calls existing public
workflow, visualization, and scientific APIs. It does not reimplement their
numerical semantics.

### Desktop responsibilities

The desktop layer is presentation and interaction only. It routes scientific
operations through reviewed application/workflow contracts and must not contain
an independent scientific execution engine.

## 4. Frozen scientific and workflow invariants

The following remain mandatory throughout v1.0:

- no hidden sorting of scientifically meaningful sequences;
- no hidden interpolation or resampling;
- no silent normalization;
- no silent unit conversion;
- no unsupported species or chemical assignment;
- no unsupported scientific inference;
- preserve provenance rather than reconstruct it heuristically;
- keep numerical semantics explicit;
- fail closed on incompatible state;
- preserve source, acquisition, recipe-step, batch-item, asset, and other
  user-defined order where meaningful;
- QA remains evidence-producing and non-mutating;
- presentation editing never mutates scientific results;
- serialized state cannot request arbitrary Python callable execution;
- serialized state cannot trigger dynamic import or automatic operation
  discovery; and
- workspace/application convenience adapts to existing scientific APIs, never
  changes those APIs merely to simplify a UI.

v0.9 recipe execution remains literal ordered execution. v1.0 does not silently
reinterpret `WorkflowRecipe` as a DAG, infer dependencies, topologically sort
steps, repair forward references, or introduce automatic parallelism.

## 5. Workspace identity, path, and persistence contract

The first v1.0 workspace is a strict local file-backed abstraction rather than a
database-backed system.

A workspace manifest must have:

- an explicit schema version;
- an explicit ordered asset list;
- stable caller-visible asset identifiers;
- deterministic canonical JSON identity;
- strict unknown-field rejection;
- duplicate-key rejection during JSON loading;
- explicit overwrite behavior with persistent writes defaulting to
  `overwrite=False`; and
- complete validation before persistent mutation.

### Workspace-owned path confinement

Every workspace-owned path stored in deterministic state must be a relative path
whose meaning is rooted explicitly at the workspace root supplied at the I/O
boundary.

The initial path contract fails closed on:

- absolute paths;
- drive-qualified paths where applicable;
- parent traversal components such as `..`;
- any resolved workspace-owned path that escapes the declared workspace root;
- ambiguous empty/root-only asset paths; and
- workspace-owned symbolic-link entries or symbolic-link traversal.

Symlink support is deliberately excluded from the first slice. A future proposal
to allow symlinks must separately define identity, root confinement, target
mutation, broken-link, cross-platform, and TOCTOU semantics before support is
added.

Path validation used for security/root confinement is not scientific-data
normalization. The implementation may canonicalize only the representation
required by the reviewed workspace path schema; it must not silently rewrite a
user-selected external source into a different source.

External references and workspace-owned files are distinct. An external source
may live outside the workspace root only through an explicit external-reference
operation and must never be mistaken for a workspace-owned relative path.

### Deterministic workspace identity exclusions

Workspace deterministic identity must not depend on:

- absolute workspace root;
- host name;
- user name;
- PID;
- timestamps;
- temporary filenames; or
- GUI selection state.

Those values may be retained separately as non-identity metadata only if a
future reviewed use case requires them.

The workspace layer must not crawl directories automatically or infer assets
from arbitrary files. Discovery is explicit and user-controlled.

## 6. Asset contract

A workspace asset is an explicit reference to user-selected or
CatalysisWorkbench-produced state.

Initial asset categories may include:

- source files;
- serialized `WorkflowRecipe` state;
- workflow/batch execution evidence;
- `QAReport` evidence;
- `FigureSpec` and preset-bundle state; and
- exported figures or other generated artifacts.

Asset category is not scientific interpretation. The workspace layer must not
assign chemical meaning, measurement technique, parser, units, or species from
a filename unless the caller explicitly supplies a reviewed mapping.

File ownership policy is explicit:

- `reference` keeps an explicit external source reference;
- `copy` creates a separately validated workspace-owned file; and
- neither policy may silently substitute for the other.

Where file bytes are identity-bearing, content digests are computed from the
actual retained bytes. File paths alone are not treated as scientific content
identity.

## 7. Persistent evidence contract

v1.0 persists associations between workspace assets and evidence already
produced by reviewed APIs rather than inventing a second scientific provenance
system.

The initial ledger may associate:

- `WorkflowRun`;
- `BatchRunRecord`;
- `QAReport`;
- recipes and their deterministic identities;
- figures/specifications and their deterministic identities; and
- exported artifact identities.

The first implementation uses explicit schema-versioned files and ordered
manifests. SQL, an ORM, a migration framework, a background service, or a server
is not required for the first v1.0 slice.

The ledger records what reviewed APIs produced; it does not decide what
scientific result should have been produced.

## 8. Block 1 — Workspace foundation

Planned package:

~~~text
src/catalysis_workbench/workspace/
    __init__.py
    manifest.py
    persistence.py
~~~

Minimum planned public concepts:

- `WorkspaceManifest`;
- `WorkspaceAsset`;
- `create_workspace()`;
- `open_workspace()`; and
- `save_workspace()`.

Required semantics:

- frozen/deeply immutable manifest state;
- explicit ordered assets;
- strict schema-versioned JSON;
- deterministic manifest SHA-256;
- explicit workspace root supplied only at I/O boundaries;
- reviewed root-confinement checks for every workspace-owned path;
- reject absolute, parent-traversing, root-escaping, and symlink workspace-owned
  paths in the initial slice;
- validate all candidate state before persistent mutation;
- no directory crawling;
- no automatic scientific import;
- no workflow execution;
- no database; and
- no new dependency.

Block 1 begins the `1.0.0.dev0` development identity only after the architecture
checkpoint is approved for implementation.

## 9. Block 2 — Explicit asset import and catalog

Planned extension:

~~~text
src/catalysis_workbench/workspace/assets.py
~~~

Required semantics:

- explicit caller-selected source;
- explicit stable asset key;
- explicit `reference` versus `copy` policy;
- content digest where file bytes are part of identity;
- literal caller asset order;
- collision detection before mutation;
- workspace-owned destinations must satisfy Block-1 root confinement;
- external references remain explicitly external and are never rewritten into
  workspace-owned paths;
- no parser guessing from filename or extension as scientific authority;
- no recursive scanning;
- no silent file move/delete;
- no hidden source substitution; and
- no new dependency.

The existing `catalysis_workbench.io` layer remains responsible for actual
reviewed data reading. The workspace catalog stores explicit references and does
not become a second IO implementation.

## 10. Block 3 — Persistent run and evidence ledger

Planned extension:

~~~text
src/catalysis_workbench/workspace/evidence.py
~~~

Required semantics:

- explicit association between assets, recipes, runs, QA reports, and artifacts;
- deterministic ordered record identity;
- reuse existing public evidence/digest state where available;
- no invented scientific provenance;
- no timestamps in deterministic identity;
- no free-form traceback text in deterministic identity;
- no automatic retry or execution; and
- no database dependency in the initial implementation.

## 11. Block 4 — Workspace workflow and figure composition

Planned responsibilities:

- save/load recipes through the reviewed v0.9 serialization contract;
- associate recipes with explicit input/output assets;
- save/load `FigureSpec` and reproducible preset bundles through reviewed
  serialization bridges;
- associate exported figures with the exact presentation/evidence state that
  produced them; and
- expose an ordered recipe editing model suitable for a future GUI.

Required boundary:

- ordered recipe editing is not DAG execution;
- no topological sort;
- no arbitrary callable insertion;
- no dynamic operation import;
- no automatic operation discovery;
- no hidden scientific parameter defaults beyond existing reviewed public
  operation contracts; and
- no scientific-data mutation by workspace composition.

## 12. Block 5 — GUI-neutral application/session controller

Planned package:

~~~text
src/catalysis_workbench/application/
    __init__.py
    session.py
    commands.py
~~~

Minimum responsibilities:

- open/close/select workspace state;
- explicit asset selection;
- recipe selection and ordered editing orchestration;
- explicit workflow execution through `catalysis_workbench.workflow`;
- QA invocation through reviewed QA APIs;
- figure-state selection/editing through reviewed visualization APIs; and
- immutable or transaction-safe application-state updates.

The controller must be testable without opening a GUI window. Invalid commands
must fail before committed application state is mutated.

Block 5 must not import a future desktop toolkit at top-level package import.

## 13. Block 6 — Desktop shell and v1.0 API hardening

Target user-facing capabilities:

- local workspace creation/opening;
- project/asset navigation;
- explicit file chooser/import action;
- ordered recipe editor;
- run/result/evidence inspection;
- scientific QA evidence view;
- integration of the existing FigureSpec editor; and
- export-oriented presentation controls.

A complete desktop shell likely requires a dedicated GUI toolkit. No new runtime
or optional GUI dependency is authorized by this document.

Before `pyproject.toml` is changed for PySide6 or another GUI framework, stop
and report:

- dependency name and exact role;
- runtime versus optional-dependency placement;
- current license and distribution implications;
- installation/wheel burden on supported platforms;
- headless-CI implications;
- import/lazy-loading strategy;
- viable no-new-dependency alternative; and
- public-API impact.

If no toolkit is authorized, Block 6 narrows to application-controller/API
hardening and integration with the existing Matplotlib FigureSpec editor. A
complete desktop shell remains deferred rather than forcing an unreviewed
dependency.

Final v1.0 hardening includes installed-wheel/public-API audit, import-laziness
checks, version identity, documentation synchronization, and compatibility
review. Stable `1.0.0`, a tag, GitHub Release, or PyPI publication remain
separately authorized decisions.

## 14. Explicit non-goals

Unless separately re-architected later, v1.0 does not include:

- new scientific-analysis algorithms merely to fill the GUI;
- a new DAG/workflow execution engine;
- implicit dependency inference or topological scheduling;
- multiprocessing, distributed queues, cloud execution, or HPC scheduling;
- instrument control;
- cloud synchronization;
- collaborative multi-user server state;
- an online plugin marketplace;
- arbitrary third-party code execution from workspace files;
- automatic recursive file discovery;
- automatic chemistry/species assignment;
- silent scientific correction or data cleaning;
- mandatory SQL/database infrastructure; or
- package-registry publication as a side effect of v1.0 development.

## 15. Prior-art and license review

The repositories below are architecture references only. No external source code
is copied, adapted, vendored, or added as a dependency by this plan.

### signac

Upstream: https://github.com/glotzerlab/signac

Useful concepts:

- file-system-oriented management of heterogeneous data spaces;
- explicit project/state organization; and
- reproducibility-oriented metadata separation.

License verified from upstream repository metadata at this checkpoint: BSD
3-Clause License.

Decision: workspace/data-management concepts only; no dependency and no code
reuse.

### pyiron_base

Upstream: https://github.com/pyiron/pyiron_base

Useful concepts:

- an integrated materials-science work environment;
- separation between project/job management and scientific backends; and
- workflow-management boundaries.

License verified from upstream repository metadata at this checkpoint: BSD
3-Clause License.

Decision: project/job/application layering concepts only; no dependency and no
code reuse.

### AiiDA core

Upstream: https://github.com/aiidateam/aiida-core

Useful concepts:

- explicit workflow/provenance separation;
- durable provenance as a first-class concern; and
- separation of orchestration from scientific code.

License verified from upstream `LICENSE.txt` at this checkpoint: MIT License.

AiiDA's database, scheduler, daemon, SSH, distributed workflow, and broader
infrastructure scope substantially exceed the deliberately local v1.0 scope.

Decision: provenance/layering concepts only; no dependency and no code reuse.

### Orange3

Upstream: https://github.com/biolab/orange3

Useful concepts:

- desktop-oriented interactive data analysis;
- visual-programming and inspector-style interaction patterns; and
- separation between user interaction and analytical components.

License verified from upstream `LICENSE` at this checkpoint: GNU GPL-3.0+.

Decision: UX/interaction concepts only. No code, widgets, assets, or source are
copied or adapted, and Orange3 is not added as a dependency.

### Existing v0.9 references

The v0.9 architecture already records Kedro, signac, SciencePlots, and
Matplotlib event/widget references. Those decisions remain valid. v1.0 does not
retroactively broaden their reuse permissions or dependency status.

Any later proposal to copy or adapt external code requires a new exact-version
license/provenance review even when architecture-level license information is
known.

## 16. Dependency policy

Target for Blocks 1-5:

~~~text
NEW RUNTIME DEPENDENCY REQUIRED: NO
NEW OPTIONAL DEPENDENCY REQUIRED: NO
~~~

Block 6 desktop-toolkit status:

~~~text
NEW GUI DEPENDENCY: NOT YET AUTHORIZED
~~~

No dependency is added merely because a reference project uses one.

## 17. Validation discipline

Every implementation Block requires at minimum:

~~~bash
python -m ruff check .
python -m pytest
~~~

Blocks changing public API, packaging, version identity, installed behavior, or
optional dependencies also require:

~~~bash
python -m build
~~~

and a fresh environment that:

- installs the exact wheel;
- confirms imports come from site-packages rather than repository `src`;
- passes `pip check`;
- runs the applicable installed smoke; and
- runs cumulative public-API/package audit coverage.

Desktop/UI Blocks additionally require headless controller tests. Any toolkit
later authorized must have a CI-safe import/headless strategy before formal
implementation.

Local validation is diagnostic/development evidence only. Formal promotion
requires GitHub exact-head CI on the PR head and final review of that same head.

## 18. Git and promotion discipline

Every v1.0 phase starts from the latest verified `main` on its own scoped feature
branch.

Default formal path:

~~~text
latest exact main
→ scoped feature branch
→ implementation + focused validation
→ full pre-push validation at block freeze
→ Draft PR
→ exact-head GitHub CI
→ formal diff/review
→ fixes and new exact-head CI when required
→ final review of final head
→ Ready
→ separate user merge authorization
→ expected-head squash merge
→ exact main-head verification
→ post-merge main CI verification
~~~

No direct push to `main`.

Without separate explicit authorization, do not:

- merge a PR;
- delete a branch;
- create a v1.0 tag;
- create a GitHub Release; or
- publish to PyPI/package registry.

## 19. Documentation-state note

At this architecture checkpoint, live `main` reports `0.9.0.dev0` in both
`pyproject.toml` and `catalysis_workbench.__version__`, while portions of the
central README/master-plan narrative still describe the earlier pre-promotion
state in which `main` remained at `0.7.0`.

That descriptive drift does not change the v1.0 technical baseline. Central
README/MASTER_PLAN/ROADMAP synchronization should be handled deliberately as a
scoped documentation update rather than silently mixed into scientific or
workspace code.

## 20. Stop conditions

Stop architecture or implementation and report before proceeding if a proposed
change requires:

- a new runtime dependency;
- a new optional dependency;
- modification of existing scientific numerical semantics;
- reinterpretation of literal recipe order as DAG semantics;
- arbitrary callable execution from serialized/workspace state;
- dynamic imports based on serialized/workspace state;
- automatic operation discovery;
- hidden recursive file discovery;
- hidden sequence sorting;
- ambiguous or non-confined workspace-owned path semantics;
- symlink support without an explicit reviewed identity/confinement contract;
- scientific auto-correction by QA or application code;
- GUI mutation of scientific results outside reviewed APIs;
- an unclear workspace/application/science ownership boundary;
- a database/server/cloud requirement not already reviewed; or
- a destructive Git operation.
