# CatalysisWorkbench v1.1 plan

## Purpose

v1.1 moves the optional desktop from a workspace-first administration shell toward a task-first scientific workbench while preserving the reviewed v1.0 scientific, workflow, provenance, and workspace contracts.

Block 1 established the deterministic analysis-document lifecycle and Home/Analysis presentation shell. Block 2 adds explicit real-data intake, mapping, raw-source ownership, and mapped-raw preview. Scientific processing, workflow execution from the task-first surface, Figure Workbench, and publication export remain later blocks.

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
