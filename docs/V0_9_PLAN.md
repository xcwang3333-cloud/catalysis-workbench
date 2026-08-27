# CatalysisWorkbench v0.9 Architecture Plan

## 1. Status and authority

This document is the local v0.9 development architecture authority candidate.
It governs development planning on the independent local branch only; it is not
formal GitHub release evidence and does not supersede GitHub main.

- Local development branch: dev/v09-local
- Local bootstrap anchor:
  b75891f0ff319b6f958eb3c1923e78a6411eee8e
- Original local bootstrap parent / retired v0.8 release-preparation checkpoint:
  c75ddb84c35bfe9d2ddd66a8823c99d773b66c29
  This ancestor is retained only as local development provenance and is not part of the promoted v0.9 history.
- Development version: 0.9.0.dev0

The bootstrap anchor is a local development checkpoint. It is not described as
a released, formally reviewed, or GitHub exact-head-CI-authorized SHA.

Formal v0.9 integration is performed by replaying or cherry-picking the intended
v0.9 commits onto the official post-v0.8 GitHub main, followed by complete
validation on the resulting exact head. Local commit SHAs are portable
development evidence, not presumed formal merge SHAs. The completed v0.8
scientific implementation history and the frozen docs/V0_8_PLAN.md remain
untouched.

## 2. v0.9 mission

v0.9 provides reproducible and interactive workflow infrastructure over the
already implemented scientific APIs.

Its primary scope is:

- reproducible recipes;
- explicit reviewed recipe execution;
- deterministic batch workflows;
- scientific QA evidence;
- reproducible publication presets; and
- a first presentation-only interactive FigureSpec editor prototype.

v0.9 is not another scientific-algorithm expansion phase. Existing v0.8
Raman, FTIR, XAS, XANES, and XRD implementations are consumed through their
reviewed public contracts; they are not redesigned by the workflow layer.

## 3. Architecture boundary

Cross-domain orchestration belongs in:

~~~text
catalysis_workbench.workflow
~~~

It does not belong in:

- core, whose responsibility is the minimal immutable Axis, Series, and Dataset
  model;
- processing, whose responsibility is reusable numerical transformations rather
  than orchestration;
- io, whose responsibility is explicit reading and source representation rather
  than execution;
- experimental, whose responsibility is experimental-domain science; or
- computation, whose responsibility is computational-domain science.

The dependency direction is:

~~~text
existing domain APIs
        |
        v
workflow orchestration / evidence / QA
        |
        v
future v1.0 workspace / GUI
~~~

Workflow may call existing reviewed APIs only through explicit, source-controlled
adapters. It must not silently change their validation rules, ordering, numerical
semantics, units, provenance, or failure behavior.

## 4. Existing foundations to reuse

### Core immutable data

Workflow consumes the existing Axis, Series, and Dataset types unchanged. Their
immutable arrays, stable-key behavior, explicit order, axis semantics, and
non-mutating update methods remain authoritative.

### Existing processing APIs

The initial simple adapter candidates are:

- crop;
- offset; and
- normalize.

Later reviewed candidates are:

- savgol; and
- integrate.

map_dataset() is explicitly excluded from automatic serialized execution because
it accepts an arbitrary Python callable.

Complex APIs such as peak fitting, operando descriptors, IO readers, and
renderers are not first-slice registry targets. They require separately reviewed
adapter contracts because their inputs, outputs, backend evidence, or
domain-specific compatibility rules are more complex.

### Existing provenance and digest systems

The electrochemistry AnalysisProvenance model is domain-specific. Operando
canonical and digest helpers are also domain-specific and private. Existing
domain provenance remains authoritative within its own domain and may be
retained by workflow execution evidence without being generalized or rewritten.

Workflow must not turn any current private digest helper into a global public
serialization standard. Workflow-level records will consume existing public
domain identities and provenance unchanged.

### Existing visualization foundation

The following types and facilities are reused unchanged:

- FigureSpec;
- LayoutSpec;
- PlotStyle;
- SeriesStyle;
- CategoryStyle;
- AnnotationSpec;
- ExportSpec; and
- the current visualization preset registry.

FigureSpec remains the authoritative presentation state. Its current immutable
update APIs and to_dict()/from_dict() bridge are extended by composition, not
replaced.

## 5. Strict canonical JSON contract

A future private helper is planned at:

~~~text
src/catalysis_workbench/_canonical_json.py
~~~

That file is not created by this architecture checkpoint.

The canonical JSON contract requires:

- strict JSON-compatible values only;
- string JSON object keys;
- object key order to have no semantic significance;
- canonical encoding to sort JSON object keys;
- ordered semantic sequences to retain their literal input order;
- recipe steps never to be sorted;
- batch items never to be sorted;
- preset bundle entries never to be sorted unless a future format explicitly
  defines them as unordered;
- rejection of NaN, Infinity, and -Infinity;
- rejection of duplicate JSON object keys during loading;
- rejection of unknown schema versions;
- rejection of unknown fields unless a future schema explicitly allows them;
- no default=str fallback;
- no implicit NumPy-to-JSON conversion;
- no silent unit conversion;
- deterministic UTF-8 canonical bytes; and
- deterministic SHA-256.

Sorting JSON mapping keys for canonical encoding is not scientific data sorting.
Scientific, acquisition, recipe-step, batch-item, and other user-provided
sequence order remains literal wherever it is semantically meaningful.

## 6. Reproducibility identity model

### recipe_sha256

Block 1 implements recipe_sha256. It contains only deterministic declarative
recipe state:

- recipe schema version;
- ordered recipe steps;
- stable step IDs;
- stable operation IDs;
- explicit named input and output bindings; and
- strict canonical parameters.

It excludes:

- timestamps;
- elapsed time;
- host;
- username;
- PID;
- absolute paths;
- UI state;
- package version; and
- backend version.

### content_sha256

content_sha256 is implemented only when execution exists in Block 2. It may
include:

- recipe_sha256;
- explicit scientific input identities;
- operation contract versions;
- output identities; and
- scientific compatibility semantics needed to interpret those identities.

Block 1 must not invent content_sha256 before execution and output state exist.

### record_sha256

record_sha256 is implemented only with execution and batch evidence in Blocks
2-3. It may additionally include deterministic environment evidence that was
actually relevant to the executed operations:

- the CatalysisWorkbench version;
- backend versions actually used; and
- deterministic success or failure codes.

The following remain outside deterministic identity:

- timestamps;
- runtime duration;
- host, user, and PID;
- absolute paths;
- traceback text;
- free-form exception text;
- logs; and
- temporary filenames.

They may be retained as clearly separate metadata when useful.

## 7. Block 1 — Reproducible recipe foundation

Block 1 creates declarative immutable workflow recipe state only.

The planned module is:

~~~text
src/catalysis_workbench/workflow/recipe.py
~~~

The planned minimum public API is:

- WorkflowRecipe;
- RecipeStep;
- recipe_to_dict();
- recipe_from_dict();
- dump_recipe(); and
- load_recipe().

Persistent write APIs must refuse overwrite by default. If an overwrite argument
is introduced, its default is:

~~~text
overwrite=False
~~~

Required semantics are:

- frozen, deeply immutable state;
- literal ordered steps;
- explicit stable step_id;
- explicit stable operation_id;
- named input and output bindings;
- strict JSON-compatible parameters;
- an explicit schema version; and
- deterministic recipe_sha256.

Block 1 fails closed on:

- duplicate IDs;
- invalid bindings;
- unsupported parameter types;
- non-finite JSON numbers;
- unknown schema versions;
- unknown serialized fields; and
- duplicate JSON keys.

Block 1 non-goals are:

- execution;
- DAG inference;
- automatic dependency resolution;
- automatic operation discovery;
- Python import paths;
- arbitrary Python callables;
- scientific processing; and
- a schema migration engine.

## 8. Block 2 — Explicit recipe execution

The planned files are:

~~~text
src/catalysis_workbench/workflow/registry.py
src/catalysis_workbench/workflow/_adapters.py
src/catalysis_workbench/workflow/execution.py
~~~

The planned public API is:

- OperationDescriptor;
- list_recipe_operations();
- get_operation_descriptor();
- execute_recipe();
- StepExecutionRecord; and
- WorkflowRun.

Stable operation IDs are data identifiers. Initial examples are:

~~~text
catalysis.processing.crop.v1
catalysis.processing.offset.v1
catalysis.processing.normalize.v1
~~~

Operation IDs are not Python import paths. The registry is source-controlled,
explicitly reviewed, and fail-closed. Serialized recipes cannot register
arbitrary callables, trigger automatic function discovery, or request dynamic
imports.

Execution order is literal recipe order. There is no hidden DAG topological
sort, forward-reference repair, implicit fallback, or parallel execution.

The first execution slice is intentionally limited to:

1. crop;
2. offset; and
3. normalize.

Registry expansion occurs only after the first contract and its installed-wheel
behavior have been validated.

## 9. Block 3 — Deterministic batch workflows

The planned file is:

~~~text
src/catalysis_workbench/workflow/batch.py
~~~

The planned public API is:

- BatchItem;
- BatchItemRecord;
- BatchRunRecord; and
- run_batch().

Required semantics are:

- caller-provided item order is authoritative;
- item keys are explicit and unique;
- per-item records are deterministic;
- every item uses the existing Block-2 executor with the same recipe; and
- the error policy is explicit.

Initial error policies are:

~~~text
raise
record
~~~

raise fails at the first failed item. record retains a deterministic failure
status for that item and continues in the original caller-provided order.

Block 3 non-goals are:

- multiprocessing;
- threading;
- asynchronous scheduling;
- automatic retry;
- directory crawling;
- distributed queues;
- cloud execution; and
- HPC.

## 10. Block 4 — Scientific QA framework

The planned file is:

~~~text
src/catalysis_workbench/workflow/qa.py
~~~

The planned public API is:

- QAStatus;
- QAFinding;
- QAReport;
- check_digest();
- check_finite_values();
- check_units();
- check_stable_keys(); and
- run_qa().

QA is immutable, explicit, non-mutating, and evidence-producing.

QA is not:

- cleaning;
- correction;
- interpolation;
- normalization;
- unit conversion;
- missing-data imputation;
- scientific interpretation; or
- chemical or species assignment.

A generic QA layer must not assume that every NaN is invalid, every missing unit
is invalid, or every empty Series.key is invalid. Checks are context-sensitive
and are run only when explicitly requested or explicitly required by a reviewed
operation contract.

## 11. Block 5 — Reproducible publication presets

The planned file is:

~~~text
src/catalysis_workbench/visualization/preset_bundles.py
~~~

Block 5 reuses the current FigureSpec and preset registry without replacing
either.

The planned public API is:

- FigurePresetEntry;
- FigurePresetBundle;
- load_preset_bundle();
- save_preset_bundle(); and
- install_preset_bundle().

Required semantics are:

- schema-versioned strict JSON;
- deterministic digest;
- explicit entry order;
- FigureSpec.to_dict()/from_dict() as the validated presentation-model bridge;
- write APIs defaulting to overwrite=False;
- complete install-conflict validation before registry mutation; and
- zero partial registry mutation after a failed installation.

A preset does not claim formal compliance with a named journal unless that claim
is separately verified and explicitly authorized in future scope.

Block 5 non-goals are:

- arbitrary Python configuration execution;
- an online preset registry;
- package download;
- hidden journal rules; and
- replacement of existing FigureSpec semantics.

## 12. Block 6 — Interactive FigureSpec editor prototype

The planned file is:

~~~text
src/catalysis_workbench/visualization/editor.py
~~~

The planned public API is:

- FigureEditorState;
- FigureSpecEditorController; and
- open_figure_spec_editor().

The architecture is:

~~~text
scientific result/data — read only
            +
current immutable FigureSpec
            |
            v
editor controller
            |
            v
new immutable FigureSpec
            |
            v
existing renderer
~~~

The editor modifies presentation state only. Potential controls include:

- font size;
- label, tick, and title size;
- line width and style;
- marker symbol and size;
- figure and axes dimensions;
- aspect ratio;
- margins;
- ticks;
- legend;
- axis limits and scales;
- annotations;
- series and category overrides; and
- export presentation settings.

Controller and state logic must be testable headlessly. The already-declared
Matplotlib dependency and its Agg backend are sufficient for the first
prototype. No new GUI dependency is authorized.

The following remain non-goals until v1.0:

- a complete desktop application;
- a workspace or project database;
- a file browser;
- a drag-and-drop workflow designer;
- GUI editing of scientific-analysis parameters;
- cloud synchronization;
- instrument control; and
- HPC.

## 13. Planned package layout

The planned final v0.9 layout is:

~~~text
src/catalysis_workbench/_canonical_json.py

src/catalysis_workbench/workflow/
    __init__.py
    recipe.py
    registry.py
    _adapters.py
    execution.py
    batch.py
    qa.py

src/catalysis_workbench/visualization/
    preset_bundles.py
    editor.py
~~~

None of these planned implementation files is created by this documentation
commit.

Expected test families are:

~~~text
tests/test_workflow_recipe.py
tests/test_workflow_registry.py
tests/test_workflow_execution.py
tests/test_workflow_batch.py
tests/test_workflow_qa.py
tests/test_visualization_preset_bundles.py
tests/test_visualization_editor.py
~~~

Installed-wheel and public-API smoke coverage is added incrementally for every
Block that introduces public or packaging-visible functionality. The coverage
requirement is frozen, but this plan does not unnecessarily require six separate
smoke filenames if later implementation evidence shows that a cumulative
versioned smoke is cleaner.

## 14. Public API discipline

Each Block introduces only its minimum reviewed public API.

- Private adapters are never wildcard-exported.
- _canonical_json.py remains private.
- _adapters.py remains private.
- Top-level workflow imports must not eagerly import visualization, PyVista, VTK,
  or unrelated optional backends.
- Installed-wheel imports must remain lazy for optional dependencies.
- Public additions must be verified from an installed wheel when implemented.
- Existing scientific public APIs must not be changed solely to make workflow
  adapters easier.

Adapters adapt to scientific APIs, not vice versa.

## 15. Dependency policy

~~~text
NEW RUNTIME DEPENDENCY REQUIRED BY CURRENT v0.9 ARCHITECTURE: NO
NEW OPTIONAL DEPENDENCY REQUIRED BY CURRENT v0.9 ARCHITECTURE: NO
~~~

The current six-Block plan uses only the Python standard library and already
declared project dependencies.

Any future discovery that a Block requires a new dependency is an architecture
stop condition and must be reported before pyproject.toml is modified.

## 16. Prior-art and license review

The following projects are architecture references only. No external source code
is copied, adapted, vendored, or added as a dependency.

### Kedro

Kedro provides useful conceptual prior art for explicit nodes or operations,
explicit data bindings, pipeline composition, and sequential execution. Its
automatic dependency resolution, data catalog, deployment integrations, project
templates, and broader pipeline ecosystem substantially exceed the deliberately
small CatalysisWorkbench v0.9 scope.

- Upstream: https://github.com/kedro-org/kedro
- License verified from the upstream repository at this checkpoint:
  Apache License 2.0.
- Decision: architecture concepts only; no dependency and no code reuse.

### signac

signac provides useful concepts around explicit state, metadata, file-backed
reproducibility, and project-oriented data management. Its project/workspace and
storage-layout machinery is intentionally deferred beyond v0.9.

- Upstream: https://github.com/glotzerlab/signac
- License verified from the upstream repository at this checkpoint:
  BSD 3-Clause License.
- Decision: architecture concepts only; no dependency and no code reuse.

### SciencePlots

SciencePlots demonstrates reusable, composable plotting-style presets. It is
reference-only: CatalysisWorkbench retains its own validated FigureSpec,
immutable overrides, exact-size export, and preset registry rather than adopting
an external style package.

- Upstream: https://github.com/garrettj403/SciencePlots
- License verified from the upstream repository metadata at this checkpoint:
  MIT License.
- Decision: style/preset concept only; no dependency and no code reuse.

### Matplotlib event and widget model

Matplotlib event handling and widgets provide sufficient conceptual and
technical basis for a small GUI-neutral controller plus first editor prototype.
Matplotlib is already a declared runtime dependency; no additional GUI
framework is needed.

- Documentation:
  https://matplotlib.org/stable/users/explain/figure/event_handling.html
- Widget examples:
  https://matplotlib.org/stable/gallery/widgets/index.html
- Decision: use the installed public Matplotlib API; do not copy example or
  third-party code.

Any future proposal to copy or adapt external code requires a new exact-version
license and provenance review even when the architecture-level license above is
known.

## 17. Scientific invariants

The following are mandatory throughout v0.9:

- no hidden sorting of scientifically ordered data;
- no hidden interpolation;
- no silent normalization;
- no silent unit conversion;
- no unsupported species assignment;
- no unsupported scientific inference;
- preserve provenance;
- use explicit numerical semantics;
- fail closed on incompatible state;
- preserve source, acquisition, and user-defined order where meaningful;
- QA never mutates scientific data; and
- the presentation editor never changes scientific results.

## 18. Validation discipline

Every future implementation Block requires at minimum:

~~~bash
python -m ruff check .
python -m pytest
~~~

If a Block changes public API, packaging, wheel behavior, optional dependencies,
or installed usage, it also requires:

~~~bash
python -m build
~~~

and a fresh environment that:

- installs the exact wheel;
- confirms import comes from site-packages rather than repository src;
- passes pip check;
- runs the applicable installed smoke; and
- runs the relevant cumulative installed-wheel and public-API audit.

Local Windows validation is diagnostic evidence only and must never be
represented as final GitHub exact-head Ubuntu CI evidence.

## 19. Git and replay discipline

All v0.9 implementation commits remain independently cherry-pickable.

Expected local history:

~~~text
retired local v0.8 release-preparation ancestor
→ v0.9 bootstrap
→ v0.9 architecture checkpoint
→ Block 1
→ Block 2
→ ...
~~~

Future formal route:

~~~text
official post-v0.8 GitHub main
→ formal v0.9 branch
→ replay/cherry-pick real v0.9 commits
→ rerun full validation
→ Draft PR
→ exact-head GitHub CI
→ formal reviews
→ expected-head merge
→ post-merge main CI
~~~

Local commit SHAs are not assumed to become formal merge SHAs.

## 20. v1.0 boundary

The following are explicitly deferred:

- a full workspace/project abstraction;
- a complete local GUI application;
- a file-import application shell;
- a persistent project database;
- broad GUI parameter orchestration;
- a workflow designer; and
- declaration of a v1.0 stable API.

No dev/v10-local branch is created during v0.9 architecture or implementation.

## 21. Stop conditions

Stop architecture or implementation and report before proceeding if any Block
later requires:

- a new runtime dependency;
- a new optional dependency;
- modification of existing scientific semantics;
- arbitrary callable execution;
- dynamic import based on serialized data;
- automatic operation discovery;
- hidden sequence sorting;
- scientific auto-correction by QA;
- GUI mutation of scientific analysis state;
- an unclear v0.9/v1.0 boundary; or
- a destructive Git operation.
