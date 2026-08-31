# CatalysisWorkbench v1.1 plan

## Purpose

v1.1 moves the optional desktop from a workspace-first administration shell toward a task-first scientific workbench while preserving the reviewed v1.0 scientific, workflow, provenance, and workspace contracts.

Block 1 established the deterministic analysis-document lifecycle and Home/Analysis presentation shell. Block 2 added explicit real-data intake, mapping, raw-source ownership, and mapped-raw preview. Block 3 added task-specific scientific processing, deterministic workflow-backed live evaluation, and ordinary-user Processing controls. Block 4 added a presentation-only Figure Workbench bound to exact scientific result identities. Block 5 adds fail-closed publication Figure Packages containing both rendered figures and full scientific source data.

## Block 1 — AnalysisDocument + Home shell

### User flow

```text
launch desktop
    -> Home
    -> choose LSV / FE & Partial Current / Generic XY
    -> clean untitled in-memory analysis
    -> edit title / undo / redo
    -> Save Project
    -> workspace.json + project.json
    -> close and reopen project
```

Selecting a task does not create a directory. A project directory appears only on the first successful Save Project operation.

### Task catalog

Block 1 uses a closed, stable application-level catalog:

| task_id | display name | default title |
| --- | --- | --- |
| `lsv` | LSV / Polarization | Untitled LSV analysis |
| `fe_partial_current` | FE & Partial Current | Untitled FE & partial current analysis |
| `generic_xy` | Generic XY Plot | Untitled XY analysis |

There is no extension-based task inference or dynamic plugin discovery in this block.

### AnalysisDocument

`AnalysisDocument` is immutable and deterministic. Its Block-1 serialized scientific/application state is only:

```json
{
  "schema_version": 1,
  "task_id": "lsv",
  "title": "Untitled LSV analysis"
}
```

Its SHA-256 identity is derived from canonical JSON. UUIDs, timestamps, absolute paths, and software versions are intentionally excluded from the document identity.

### Project envelope

A saved v1.1 project has two control files at its root:

```text
project-root/
├── workspace.json
└── project.json
```

`workspace.json` remains the asset catalog. `project.json` is application/document control state and is reserved workspace metadata rather than a `WorkspaceAsset`.

The Block-1 project envelope is:

```json
{
  "schema_version": 1,
  "document": {
    "schema_version": 1,
    "task_id": "lsv",
    "title": "Untitled LSV analysis"
  }
}
```

Project and document SHA-256 identities are derived, not serialized back into the envelope.

### Session semantics

The new `AnalysisSession` is independent from the frozen v1.0 `ApplicationSession`.

An untouched task selection is **unsaved but clean**: it has an in-memory document and no project root, but no user edit has occurred. Returning Home from that state does not require a discard prompt.

A semantic edit makes the document dirty relative to its saved or initial baseline. Undo and redo operate on document revisions only; file-system operations are not undoable. Saving does not erase undo history, so undoing after a save can make the document dirty again and redoing back to the saved identity clears dirty state.

Dirty replacement, close, open, and Home transitions are fail-closed unless the user explicitly chooses Save or Discard.

### Persistence and concurrency

Open reads the workspace manifest and project document twice and commits session state only when both exact identities agree.

Save verifies the expected workspace-manifest SHA and project-file SHA, writes `project.json` through a temporary file plus fsync and atomic replacement, then re-reads and verifies the exact candidate before advancing the session baseline.

Changing only the analysis title must not change `workspace.json` identity.

A first save must target a non-existing directory. If verification fails after this block created the directory, rollback removes only files that still exactly match the artifacts this operation created. Unknown external content is never silently removed.

Malformed JSON, unknown schemas/tasks, legacy v1.0 workspaces without `project.json`, and symlinked project control paths fail closed. Block 1 does not guess or migrate a legacy workspace into an analysis task.

### Desktop migration strategy

The v1.0 `CatalysisWorkbenchMainWindow` remains available for explicit legacy integrations. The new task-first `CatalysisWorkbenchWindow` is implemented in parallel.

A normal no-argument `launch_desktop()` / `python -m catalysis_workbench.desktop` enters the new Home shell. Explicit v1.0 `create_desktop(root, session=ApplicationSession())` remains unchanged for compatibility tests and advanced legacy use.

The Home shell contains exactly three task cards, Open Project, and Recent Projects. Recent-project history is desktop-only `QSettings` state and never participates in scientific SHA identities.

The Analysis shell in Block 1 is an empty-state scaffold with DATA, LIVE ANALYSIS, and PROCESSING columns. `Continue to Figure` remains disabled until later blocks add real data and analysis state.

### Headless boundary

`application.analysis` must not import PySide6, PyQt, or Matplotlib pyplot. Dependency direction remains:

```text
scientific -> workflow -> workspace -> application -> desktop
```

### Compatibility gates

Block 1 must keep all frozen v1.0 installed-wheel and desktop smoke tests passing. In particular, the v1.0 top-level `catalysis_workbench.desktop.__all__` tuple remains unchanged; the new window is available through the explicit v1.1 module/API path without silently widening the frozen v1.0 public export contract.

### Development-version note

Block 1 bootstraps the v1.1 development line at `1.1.0.dev0`. Distribution/runtime identity, historical installed-smoke current-version assertions, workflow provenance version evidence, and release-readiness candidate/artifact checks are synchronized mechanically to that development identity. The Stable 1.0 compatibility audit remains active and continues to enforce the frozen v1.0 public/desktop surface. This development-version bootstrap creates no tag, GitHub Release, or registry publication.

## Block 1 non-scope

Block 1 does not add real CSV/TXT/XLSX data mapping, LSV or FE computation changes, automatic workspace-to-workflow binding, Figure Workbench implementation, publication-package export, new third-party dependencies, Git tags, GitHub Releases, or PyPI publication.

## Block 2 — Data Intake & Mapping

### User flow

```text
Home
    -> choose task
    -> Analysis Workbench
    -> Add files / drop files
    -> bounded preview
    -> explicit X/Y + meaning + unit/reference mapping
    -> confirm each file
    -> mapped raw live preview
    -> rename / reorder / edit mapping / preview data
    -> Save Project
    -> reopen and materialize from workspace-owned raw bytes
```

Block 2 does not require a project directory before data intake. Source bytes can be mapped while the analysis remains an unsaved in-memory document; the first Save Project operation takes ownership of those exact bytes through verified workspace copies.

### Supported file boundary

The normal desktop accepts exactly the reviewed Block-2 tabular formats:

- `.csv`;
- `.txt`;
- `.tsv`;
- `.dat`;
- `.xlsx`; and
- `.xlsm`.

Recursive import, legacy `.xls`, directory watching, arbitrary binary formats, and normal-user external-reference mode are outside Block 2.

### Deterministic data model

Block 2 advances `AnalysisDocument` to schema 2. A schema-2 document may contain an ordered tuple of `DataSeriesSpec` records. Existing schema-1 analysis documents remain readable through an explicit compatibility migration; opening a schema-1 project does not mutate the project file merely because it was read.

Each mapped input separates three concepts:

- `SourceSpec`: immutable source-format and exact-content identity;
- `TabularMappingSpec`: parser state plus explicit X/Y scientific mapping; and
- `DataSeriesSpec`: one named mapped series that combines source and mapping state.

Raw, mapping, and scientific-input identities are deterministic and path independent. File-system paths are transient locators only and are not scientific identity. The same exact bytes and mapping therefore retain the same scientific-input identity after a project or source file moves.

The desktop does not expose workspace asset IDs, recipe IDs, SHA fields, or copy/reference policy as normal-user data-entry fields.

### Preview and parser contract

`io.tabular_preview` provides a bounded GUI-neutral preview. The preview is intentionally not a spreadsheet editor and does not change raw values.

For delimited text, syntax-level delimiter detection may be used to establish the explicit parser state. For Excel, sheet selection remains visible. Changing delimiter or sheet parser state invalidates confirmation until the preview has been reloaded with that parser state.

Unit inference is deliberately conservative. Only trailing square-bracket syntax such as `Potential [V]` or `Current density / [mA cm^-2]` is inferred automatically. Parentheses are not treated as units because they may carry scientific semantic meaning. Scientific X/Y meaning, unit, and optional reference remain explicit mapping fields.

Import status is per file:

- `✓` confirmed and valid;
- `⚠` structurally usable but still requiring explicit confirmation; or
- `✕` invalid or not currently previewable/mappable.

`Apply this mapping to compatible files` copies X/Y column positions and their scientific semantic fields only when the target has those positions and the selected X/Y column names plus conservatively inferred units exactly match the source preview. Same-position columns with different headers or inferred units are not auto-confirmed. The batch action does not copy parser state and does not interpolate, resample, or otherwise reshape target data.

### Materialization boundary

A confirmed `DataSeriesSpec` materializes deterministically into a path-free core `Series`. Materialization performs parsing, exact selected-column extraction, numeric validation, and explicit axis metadata construction only.

Block 2 does **not** perform RHE conversion, iR correction, geometric-area normalization, FE arithmetic, partial-current calculation, smoothing, interpolation, filtering, fitting, baseline correction, or plot-range cropping. Those belong to scientific processing or presentation blocks.

The Analysis Workbench center pane can sample a large materialized series for responsive drawing, but display sampling is presentation-only and never modifies the scientific `Series`, its SHA identity, or the stored raw bytes.

### Workspace ownership and first-save transaction

Before first save, `AnalysisSession` retains verified transient locations for source bytes. Each add operation re-verifies the source digest before accepting the mapping.

The first Save As operation is staged in a sibling temporary directory. All required workspace-owned raw copies, `workspace.json`, and `project.json` are written and verified before the final project root becomes authoritative. A failed stage does not expose a half-created project as a successful save.

After save, materialization and Edit Mapping resolve the workspace-owned copy instead of depending on the original external path. Deleting or moving the original external source therefore does not invalidate a correctly saved project.

Workspace raw bytes are digest pinned. The expected raw digest is carried into the batch-copy request and compared with the digest calculated while bytes are copied, so a source that changes after pre-save verification but during copying is rolled back before manifest commit. A changed workspace copy after save, a missing copy, manifest mismatch, or concurrent control-file mutation also fails closed instead of being silently accepted as old evidence.

Batch raw-copy registration uses an expected workspace-manifest identity and rollback rules that remove only exact artifacts created by the failed operation. Unknown external content is never deleted.

### Analysis-session semantics

Adding multiple files is one semantic document revision, so the batch can be undone as one operation. Rename, mapping replacement, remove, and reorder are also explicit semantic revisions.

Series order in schema 2 is literal application state and is retained across save/reopen. Block 2 does not create hidden sorting rules.

Saved edits remain subject to the existing dirty-state contract: Home, Open Project, and Exit require Save, Discard, or Cancel when the analysis differs from its baseline.

### Desktop surface

The Block-2 Analysis Workbench uses the reviewed three-column layout:

```text
DATA (left) | LIVE ANALYSIS PREVIEW (center, largest) | PROCESSING (right)
```

The DATA pane supports multi-file selection, file drop, mapped-series selection, inline display-name editing, drag reorder, Edit mapping, Preview data, and explicit removal.

The center pane plots mapped raw data and labels axes from the explicit mapping. It does not claim that scientific processing has occurred.

The PROCESSING pane remains a boundary placeholder in Block 2. `Continue to Figure` remains disabled until a later block defines and validates scientific processing state.

### Compatibility and validation gates

Block 2 must preserve the frozen v1.0 public surface while adding the v1.1 functionality through its explicit modules and application types. In particular, `workspace.__all__`, `workspace.assets.__all__`, and the frozen desktop compatibility exports are not widened merely to expose new internal transaction helpers.

The Block-2 gates include:

- deterministic source/mapping/input identity tests;
- schema-1 read compatibility and schema-2 persistence tests;
- bounded preview tests;
- materialization identity tests;
- batch session add/edit/remove/reorder/undo coverage;
- external-source mutation and missing-source fail-closed coverage;
- workspace-copy digest/tamper coverage, including copy-time expected-digest mismatch rollback;
- first-save staging and rollback coverage;
- installed-wheel Block-2 raw-source persistence smoke;
- fresh-wheel offscreen desktop import/mapping/live-preview/edit-mapping smoke, including negative batch-compatibility coverage;
- full regular CI; and
- the complete Stable 1.0 Readiness compatibility matrix.

## Block 2 non-scope

Block 2 does not add electrochemical transformation controls, workflow execution changes, Figure Workbench, publication-package export, automatic scientific/domain inference, recursive import, `.xls`, normal-user external-reference mode, hidden interpolation/resampling, new scientific dependencies, Git tags, GitHub Releases, or PyPI publication.

## Block 3 — Live Scientific Analysis

### User flow

```text
mapped data
    -> task-specific PROCESSING controls
    -> validate committed settings
    -> compile deterministic internal workflow
    -> execute live scientific analysis
    -> inspect raw / processed or FE / partial-current views
    -> revise settings with Undo/Redo support
    -> Save Project
```

Block 3 turns the PROCESSING pane into the scientific-analysis surface. It does not expose recipe editing, operation IDs, workflow bindings, hashes, or provenance records to ordinary users.

### AnalysisDocument schema 3

Block 3 advances the normalized in-memory and newly saved document to schema 3. Schema 1 and schema 2 projects remain readable and are normalized in memory to schema 3 without rewriting the project during open. The first explicit save after opening an older project persists the schema-3 representation.

Schema 3 adds deterministic task-specific `analysis` state. Computed arrays, GUI draft text, selected preview tabs, timestamps, file paths, and software-version evidence remain outside document identity.

Document construction validates all processing references against the current `data_series` identities. Unknown override targets or FE/current pair members fail closed.

### LSV / polarization processing

The LSV task supports one common processing configuration plus optional full per-series overrides. The persisted controls are:

- no RHE conversion, direct RHE offset, or SHE-reference + pH conversion;
- temperature for the SHE/pH conversion path;
- resistance and iR-correction fraction;
- optional geometric electrode area and current-density normalization;
- explicit current-density output unit; and
- a scientific analysis-range crop.

The analysis range is scientific processing state. It is separate from the later Figure Workbench display range.

### FE and partial current

The FE & Partial Current task uses explicit current-series ↔ FE-series pairs. Pairing is never inferred from series names or ordering.

Each current input may use the same current-processing configuration model as LSV before partial-current calculation. FE and current inputs must already share compatible x coordinates; Block 3 does not interpolate, resample, nearest-match, or silently align mismatched grids.

Partial current uses the reviewed signed current-density convention. FE and partial-current results are exposed as separate live-preview views so dissimilar y quantities are not placed on one implicit axis.

### Generic XY

Generic XY processing is deliberately narrow in Block 3: it supports scientific analysis-range cropping only. Smoothing, baseline correction, fitting, normalization, and other generic transforms remain out of scope.

### Deterministic compiler and evaluator

Task-first state compiles into an internal deterministic `WorkflowRecipe`. Block 3 private operation descriptors are resolved by the analysis layer and do not widen or mutate the frozen public workflow registry.

The GUI-neutral `AnalysisEvaluator` materializes the mapped inputs, executes the compiled operations, and returns an explicit success / incomplete / error evaluation. Successful evaluation carries a deterministic `WorkflowRun` with input identities, step records, output identities, recipe identity, content identity, and current package-version environment evidence.

Display-only series renames do not alter scientific input identities or the resulting workflow content identity. Mapping changes that produce a new `data_id` atomically rewrite processing overrides and explicit pair references. Removing a referenced input atomically removes its dependent override/pair state and remains undoable as one document revision.

### Desktop commit and last-valid semantics

Processing fields are draft UI state until they form a valid processing object and the candidate analysis evaluates without a scientific execution error. Valid candidates are committed as semantic `AnalysisDocument` revisions; invalid text or invalid scientific settings leave the committed document unchanged.

When the user is editing an invalid draft after a previously successful run, the center pane may continue to display the previous valid result only when it is explicitly marked stale with `Previous valid result — current settings are not applied`. The stale result is never presented as current evidence and is not written into the document.

Navigation, save, mapping edits, data removal, and close do not silently discard an invalid uncommitted processing draft. The desktop requires an explicit discard/cancel decision before the transition.

The DATA pane remains the source/mapping surface; the center pane becomes the live scientific result surface; PROCESSING owns task-specific scientific settings. `Continue to Figure` remains disabled until Block 4.

### Headless and compatibility boundaries

`application.analysis` remains Qt-free and does not import PySide6, PyQt, or Matplotlib pyplot. The v1.0 public workflow registry and frozen desktop top-level export contract remain unchanged.

Block 3 also retains the Block-2 raw-preview compatibility entry point used by the cumulative installed desktop smoke while routing the current workbench through live evaluation.

### Validation gates

Block 3 adds coverage for:

- schema 1/2 read compatibility and schema-3 persistence;
- strict processing serialization and cross-reference validation;
- common and per-series LSV processing;
- RHE conversion, iR correction, geometric-area normalization, and analysis-range behavior through the existing scientific kernels;
- explicit FE/current pairing and signed partial current without interpolation;
- deterministic task-state compilation and `WorkflowRun` identities;
- display-name changes preserving scientific run identity;
- atomic mapping-remap and removal cascades with Undo/Redo;
- live evaluator incomplete/error/success states;
- invalid processing drafts preserving the committed document and previous valid preview with stale labeling;
- fresh-wheel Block-3 application and offscreen Desktop smoke coverage;
- full regular CI; and
- complete Stable 1.0 Readiness compatibility coverage.

## Block 3 non-scope

Block 3 does not implement Figure Workbench, figure display-range editing, publication-package export, smoothing, interpolation/resampling, fitting, baseline correction, automatic FE/current pairing, recipe-editor exposure, new third-party scientific dependencies, Git tags, GitHub Releases, or PyPI publication.

## Block 4 — Figure Workbench

### User flow

```text
successful current analysis
    -> Continue to Figure
    -> choose result view
    -> Create Figure
    -> edit trace order / labels / visibility
    -> edit publication layout and style
    -> edit display range
    -> preview from exact bound scientific result
    -> Save Project
```

Block 4 is presentation-only. It does not expose Processing controls in the Figure Workbench and does not mutate scientific arrays or workflow execution state.

### AnalysisDocument schema 4 and FigureDraft

Block 4 advances `AnalysisDocument` to schema 4 by adding ordered persisted `FigureDraft` state. Older schema-1/2/3 projects remain readable through explicit in-memory normalization and are not rewritten merely by opening them.

Each `FigureDraft` binds:

- one allowed analysis result `view_id`;
- exact scientific trace identities;
- explicit publication trace order; and
- one immutable `FigureSpec` presentation state.

The FigureDraft SHA is deterministic and excludes paths, timestamps, GUI selection state, and rendered binary bytes.

### Scientific binding and stale semantics

A figure may be created only from a successful current analysis result. The persisted draft records the exact scientific identities behind that view. If later Processing changes produce different scientific identities, the FigureDraft becomes stale.

A stale figure remains inspectable as persisted presentation state but cannot be silently edited/rendered as if it were current. `Refresh from Analysis` explicitly rebinds it to the new science while preserving surviving trace presentation where possible.

Display-only series rename does not change scientific identity and therefore does not itself stale a FigureDraft.

### Figure Workbench surface

The reviewed desktop surface is:

```text
CONTENT | PUBLICATION PREVIEW | PROPERTIES
```

Normal-user controls include result view selection, trace visibility/order/labels, preset, physical figure geometry, axis labels/scales, display limits, legend, typography, and line/marker presentation.

The Figure Workbench does not expose recipe IDs, operation IDs, hashes, evidence records, workspace assets, or provenance internals.

### Display range boundary

Figure `xlim` / `ylim` are presentation state only. They must not crop or mutate the scientific series, workflow outputs, or source-data identity. This distinction becomes an explicit Block-5 export gate: exported source data uses the complete scientific trace even if the Figure preview displays only a narrow range.

### Validation gates

Block 4 adds coverage for:

- schema-4 FigureDraft serialization and older-schema read compatibility;
- exact scientific trace/source-view identity binding;
- stale detection and explicit refresh semantics;
- surviving trace presentation retention across refresh;
- display-range changes preserving scientific data and workflow identity;
- presentation-only trace reorder/label/visibility edits;
- fresh-wheel headless Block-4 smoke;
- offscreen Figure Workbench desktop smoke;
- full regular CI; and
- complete Stable 1.0 Readiness compatibility coverage.

## Block 4 non-scope

Block 4 does not publish Figure Packages, write publication source-data files, add scientific processing, add fitting/smoothing/interpolation, expose workflow/recipe editing, create release tags, create GitHub Releases, or publish PyPI artifacts.

## Block 5 — Figure Package Export

### User flow

```text
current FigureDraft
    -> Continue to Export
    -> choose SVG / PDF / PNG
    -> choose XLSX / TXT source data
    -> choose new package directory
    -> preflight saved/current/font/visible-trace state
    -> Export Package
    -> verified external package + workspace provenance
```

Block 5 completes the reviewed ordinary-user path from imported data to publication output. Export remains explicit and does not hide a project save or Figure refresh.

### Export contract

A Figure Package requires at least one figure format and one source-data format. The supported format sets are closed for Block 5:

- figure: `svg`, `pdf`, `png`;
- source data: `xlsx`, `txt`.

The destination must not already exist and its parent must already be a real directory. Normal-user overwrite/merge behavior is intentionally absent.

### Preflight

Export fails closed unless:

- the analysis project has a saved root;
- the current document is clean relative to that saved baseline;
- the expected workspace-manifest and project-file identities are still current;
- scientific evaluation succeeds;
- the selected FigureDraft matches current science;
- the configured figure font family is available; and
- at least one figure trace is visible.

The Qt Export page presents these conditions as ordinary-language preflight checks. It does not expose provenance SHA fields or asset IDs.

### Full scientific source data

Source-data output is derived from the exact scientific `FigureSourceView`, then filtered only by trace visibility/order. Figure display limits are never applied to the exported arrays.

TXT writes one trace per file with metadata plus explicit `x_missing` / `y_missing` flags. XLSX contains an index sheet plus one sheet per visible trace and preserves missingness explicitly. Neither writer interpolates, resamples, smooths, fits, or otherwise changes scientific values.

### Package semantic identity and exact byte identities

Block 5 separates two identity layers:

1. semantic package identity, derived from canonical path-independent state: task/view, saved analysis-document SHA, FigureDraft SHA, source-view/trace scientific identities, FigureSpec SHA, selected formats, and available workflow provenance;
2. exact file identities, calculated from the actual generated figure/source-data bytes and recorded with file sizes in `manifest.json`.

Destination paths, timestamps, and absolute file-system locations are excluded from semantic package identity. This allows the same scientific/presentation export request to retain one semantic identity even when binary container metadata or destination differs, while every concrete artifact remains hash-verifiable.

### Workspace provenance

Before external publication becomes authoritative, verified copies of the FigureSpec, generated figure/source-data files, and package manifest are registered as workspace-owned assets through expected-manifest copy semantics.

The export transaction also records workflow/package evidence and figure composition records using the existing v1.0 provenance models. These IDs remain backend details; ordinary users interact with the Figure Package rather than manually assembling evidence records.

Repeated exact exports may reuse already verified identical provenance assets. Asset/evidence/composition identity collisions with different content fail closed.

### Atomic publication and rollback

The package is generated in a sibling staging directory. Every generated file is rehashed against the staged manifest before provenance commit. The project snapshot and expected workspace/project identities are rechecked around the transaction.

The final external directory rename is a distinct publication boundary. If that rename or a later verification fails, Block 5 removes only the exact package produced by the operation and restores tracked workspace metadata/assets to their pre-export bytes when safe. Unknown concurrent external content is never silently deleted or overwritten.

If an exact rollback cannot be proven safe because workspace or target content changed concurrently, the operation fails closed and instructs the caller to reopen/inspect rather than fabricating a clean state.

### AnalysisSession semantics

Export is not a semantic `AnalysisDocument` revision. A successful session export therefore preserves:

- the exact document object and document SHA;
- revision number;
- Undo and Redo stacks; and
- clean/dirty state.

Only the expected workspace-manifest baseline advances to the manifest identity containing the new verified provenance assets. A failed export leaves session state unchanged.

### Validation gates

Block 5 adds coverage for:

- semantic package identity independent of destination;
- exact file SHA/size manifest verification;
- full-source-data export despite narrow Figure display limits;
- visible-trace-only source package semantics;
- TXT/XLSX missing-value preservation;
- saved/dirty/stale/existing-target fail-closed behavior;
- workspace evidence/composition registration;
- final publication failure restoring exact package/workspace/session state;
- cumulative fresh-wheel headless Block-5 smoke;
- cumulative offscreen Figure → Export → Package desktop smoke;
- full regular CI; and
- complete Stable 1.0 Readiness compatibility coverage.

## Block 5 non-scope

Block 5 does not add new scientific transforms, change Figure Workbench styling semantics, expose recipe/workflow/provenance administration to ordinary users, add package overwrite/merge, add new third-party dependencies, create a v1.1 tag or GitHub Release, or publish to PyPI.

## Block 6 — Dogfooding Hardening & Desktop Cleanup

### Purpose

Block 6 hardens the completed v1.1 ordinary-user desktop path for installed-wheel dogfooding. It does not add new scientific transforms, change deterministic identities, or expand the reviewed v1.0 compatibility surface.

### Launch and project entry

The installed package exposes the `catalysis-workbench` console entry point. `catalysis-workbench --version` returns the distribution/runtime development version without importing Qt. `catalysis-workbench --project PATH` explicitly opens an existing v1.1 analysis project; no-argument launch remains the task-first Home shell.

CLI argument parsing and version reporting remain separated from Qt startup so headless package/version checks do not require PySide6 initialization.

### Export completion flow

The Export page can explicitly Save Project when export preflight is blocked only because the current v1.1 analysis is unsaved or dirty. Saving remains the existing verified `AnalysisSession` project transaction; export never silently saves as a side effect.

After a successful Figure Package export, the desktop presents explicit Open Folder and Export Another actions. These are post-publication presentation actions and do not change package scientific identity, workspace provenance, document revision state, or export verification semantics.

### Actionable errors and recent projects

Ordinary desktop failures present an actionable summary plus optional technical details instead of exposing raw exception text as the primary message. Technical details remain diagnostic presentation state and are not serialized into scientific/application identity.

Recent Projects uses a desktop presentation cache only. Cache failure or staleness must not change project persistence, scientific SHA identities, or fail-closed open/save semantics.

### Installed-wheel dogfooding

Block 6 extends cumulative fresh-wheel smoke coverage over the installed desktop path for:

- Generic XY;
- LSV / Polarization; and
- FE & Partial Current.

The smokes exercise representative task creation/data intake/processing/figure/export or project lifecycle paths from an installed wheel, including offscreen desktop execution where required. They supplement rather than replace focused unit/regression coverage.

Regular CI wires the cumulative Block-6 smoke coverage while Stable 1.0 Readiness remains the compatibility gate for the frozen v1.0 surface.

### Validation gates

Block 6 requires:

- console-entry installation and Qt-free `--version` coverage;
- explicit `--project` v1.1 launch coverage;
- Export-page Save Project behavior;
- successful-export Open Folder / Export Another behavior;
- actionable desktop error plus technical-details coverage;
- Recent Projects presentation-cache coverage;
- cumulative fresh-wheel Generic XY / LSV / FE & Partial Current dogfood smoke;
- full regular CI on the exact PR head; and
- complete Stable 1.0 Readiness on the exact PR head.

## Block 6 non-scope

Block 6 does not add new scientific algorithms or transforms, change Figure Package scientific/source-data/provenance semantics, widen the frozen v1.0 public API, add new third-party scientific dependencies, create a v1.1 tag, publish a GitHub Release, merge the PR automatically, or publish to PyPI/package registries.
