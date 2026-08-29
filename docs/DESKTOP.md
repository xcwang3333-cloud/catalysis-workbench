# CatalysisWorkbench desktop shells

CatalysisWorkbench provides an optional local Qt presentation layer over the reviewed application, workspace, workflow, visualization, and scientific APIs. The base package remains usable without Qt.

## Installation

```bash
python -m pip install .
```

Install the desktop extra when the Qt Widgets shell is required:

```bash
python -m pip install ".[desktop]"
```

The approved optional dependency is:

```text
PySide6-Essentials>=6.11.2,<6.12
```

The desktop package is lazy: importing `catalysis_workbench.desktop` does not import PySide6. Toolkit modules are loaded only when a desktop class or launcher is requested. If the optional extra is absent, explicit desktop access fails with `DesktopDependencyError` rather than breaking base-package imports.

## Default launch in v1.1 development

From an environment containing the desktop extra:

```bash
python -m catalysis_workbench.desktop
```

The no-argument launcher opens the task-first v1.1 Home shell. Home offers:

- LSV / Polarization;
- FE & Partial Current;
- Generic XY Plot;
- Open Project; and
- Recent Projects.

Choosing a task creates a clean in-memory untitled analysis. It does **not** ask for a directory. The first Save Project operation creates the project directory and writes `workspace.json` plus `project.json`.

The current v1.1 workbench now covers the reviewed ordinary-user path through Block 5:

```text
Home
  -> Analysis Workbench
  -> Figure Workbench
  -> Export Figure Package
```

Data intake and mapping are explicit, scientific processing is task-specific, figure editing is presentation-only, and export produces publication figure files together with source data while provenance remains an internal workspace concern.

## Analysis Workbench

The normal Analysis Workbench is a three-column view:

```text
DATA  |  LIVE ANALYSIS PREVIEW  |  PROCESSING
```

The center preview remains the largest region. The DATA pane owns source and mapping state, the center pane displays mapped raw or current scientific results, and PROCESSING owns task-specific scientific parameters.

`Continue to Figure` becomes available only when the committed analysis evaluates successfully. It does not bypass invalid draft processing state.

## v1.1 Block 2 data intake and mapping

### Add files

`+ Add files` and drag-and-drop accept the reviewed tabular formats:

- `.csv`;
- `.txt`;
- `.tsv`;
- `.dat`;
- `.xlsx`; and
- `.xlsm`.

Multiple files can be selected in one intake operation. Recursive directory import, legacy `.xls`, and normal-user external-reference mode are intentionally outside v1.1.

Each selected file is hashed before it enters the analysis document. File-system locations are used only to locate bytes; absolute paths do not participate in raw, mapping, or scientific-input identity.

### Preview and explicit mapping

The Import Data dialog separates file selection, a bounded read-only preview, and explicit mapping. The user confirms:

- X column;
- X scientific meaning;
- X unit;
- optional X reference such as `RHE`;
- Y column;
- Y scientific meaning;
- Y unit; and
- series display name.

Parser state remains explicit. Excel sheets are selected visibly. Delimited-text input records the resolved delimiter. If the delimiter or sheet parser state is changed, the preview must be reloaded before the mapping can be confirmed.

Unit inference is deliberately conservative: only a trailing square-bracket form such as `Potential [V]` or `Current density / [mA cm^-2]` is treated as an inferred unit. Parentheses are not interpreted as units because scientific headers often use parentheses for semantic content. Inferred values remain editable and must still pass the explicit mapping gate.

Each file is shown as valid/confirmed, requiring confirmation, or invalid. `Apply this mapping to compatible files` copies the selected X/Y positions and scientific semantics only when the target has those positions **and** the selected X/Y column names plus conservatively inferred units exactly match the source preview. Files with the same column positions but different headers or inferred units remain unconfirmed and require explicit review. The batch action does not rewrite each file's parser state or silently interpolate data.

### Data list and mapped raw preview

Mapped series appear in the DATA list. The user can:

- rename a series;
- reorder series by drag-and-drop;
- edit a mapping;
- inspect a read-only data preview; and
- remove a series from the analysis.

The central Matplotlib preview may sample large series for display responsiveness, but display sampling never changes the materialized scientific `Series`, its input identity, workflow identity, or the saved raw bytes.

### Saved raw ownership and fail-closed behavior

Before the first save, the analysis session keeps verified transient locations for the selected source bytes. The first Save Project operation stages the project and workspace-owned raw copies before the final project directory becomes authoritative.

After a successful save, materialization and Edit Mapping use the verified workspace-owned copy rather than depending on the original external path. Moving or deleting the original external file therefore does not break a correctly saved project.

Raw-file mutation and workspace-copy tampering fail closed. The application re-verifies the expected source digest before materialization or mapping edits and pins that expected digest into the batch copy itself, so a source that changes between pre-save verification and copying is rolled back before the workspace manifest is committed.

Workspace batch-copy operations use expected-manifest checks. Project/document writes retain the existing exact-identity concurrency rules, and failed first-save staging is rolled back without deleting unknown external content.

## v1.1 Block 3 live scientific analysis

Block 3 advances `AnalysisDocument` to schema 3 and persists deterministic task-specific processing state. Schema 1 and 2 projects remain readable and are normalized in memory to schema 3 without rewriting their project file during open. An explicit subsequent save writes the schema-3 form.

Computed arrays are runtime-only. GUI draft text, selected preview tab, file-system paths, timestamps, and display sampling are not part of document identity.

### LSV / Polarization

The LSV task exposes a common processing configuration and optional per-series overrides. The normal-user controls include:

- no RHE conversion, direct RHE offset, or reference-vs-SHE + pH conversion;
- temperature for the SHE/pH conversion path;
- solution resistance and iR-correction fraction;
- optional electrode area and current-density normalization;
- explicit output current-density unit; and
- scientific analysis-range limits.

Analysis range is scientific processing state and is intentionally distinct from the Figure Workbench display range.

### FE & Partial Current

The FE & Partial Current task requires explicit current-series ↔ FE-series pairing. Pairs are not inferred from filenames, display names, list order, or matching point counts.

Current inputs can use the same current-processing model as LSV before partial-current calculation. FE and current inputs must already use compatible x coordinates. Block 3 does not interpolate, resample, nearest-match, or otherwise fabricate alignment.

Partial current uses the reviewed signed current-density convention. The live preview exposes FE and partial current as separate views rather than placing unlike y quantities on one implicit axis.

### Generic XY

Generic XY intentionally supports analysis-range cropping only in Block 3. Smoothing, fitting, baseline correction, normalization, interpolation, and other generic transformations remain out of scope.

### Live evaluation and workflow identity

Task-first processing state compiles into an internal deterministic `WorkflowRecipe`. The analysis layer resolves its private Block-3 operation descriptors without mutating the frozen public workflow registry.

`AnalysisEvaluator` materializes mapped inputs, executes the compiled analysis, and returns explicit `success`, `incomplete`, or `error` state. A successful result carries a deterministic `WorkflowRun` and scientific output identities.

Display-name edits do not change scientific run identity. Mapping edits that change `data_id` atomically rewrite any processing override and explicit FE/current pair references. Removing a referenced data series atomically removes its dependent processing references and remains one undoable document revision.

### Processing drafts and previous-valid results

Processing controls are draft UI state until the fields form a valid processing object and the candidate evaluates without a scientific execution error. Only then is the processing state committed to `AnalysisDocument`.

Invalid numeric text or invalid scientific settings do not mutate the committed document. If a previous valid run exists, the center pane may continue displaying it only with the explicit stale label:

```text
Previous valid result — current settings are not applied
```

The stale result is not presented as current evidence and is never persisted as document state.

Save, Home, Open Project, mapping edits, data removal, and application close do not silently discard an invalid uncommitted processing draft. The desktop requires an explicit discard/cancel decision before the transition.

## v1.1 Block 4 Figure Workbench

Block 4 advances `AnalysisDocument` to schema 4 and stores immutable `FigureDraft` presentation state bound to exact scientific trace identities. A FigureDraft is created explicitly from a successful analysis result and becomes stale when its underlying scientific result changes.

The Figure Workbench is a three-column publication editor:

```text
CONTENT  |  PUBLICATION PREVIEW  |  PROPERTIES
```

Normal controls cover result selection, trace visibility/order/labels, publication preset, physical figure size, axis labels/scales, display ranges, legend, typography, line and marker styling. These edits affect presentation only. They do not modify processing parameters or scientific arrays.

Display range is deliberately distinct from analysis range. Setting Figure Workbench `xlim` or `ylim` changes the rendered view but does not crop the scientific series. When analysis results change, the figure is explicitly marked stale and styling is disabled until `Refresh from Analysis` rebinds the FigureDraft to the new exact scientific identities.

## v1.1 Block 5 Figure Package export

`Continue to Export` opens an explicit Figure Package page for a current FigureDraft. The page shows ordinary-user preflight state rather than workspace asset IDs, hashes, evidence records, or composition internals.

The reviewed export formats are:

- figure files: SVG, PDF, PNG;
- source data: XLSX, TXT.

At least one figure format and one source-data format must be selected. The destination must be a new directory whose parent already exists.

Export preflight requires:

- the analysis project is saved and clean;
- the selected FigureDraft is current rather than stale;
- its configured font family is available on the system; and
- at least one trace remains visible.

The source-data package contains the **full scientific arrays** for visible traces. Figure display limits never crop exported source data. TXT and XLSX outputs preserve explicit missing-value information; each exported trace is also bound to its exact scientific identity in the package manifest.

A package semantic SHA is derived from path-independent scientific/presentation state and selected formats. File-system destination, timestamps, and absolute paths are excluded from that semantic identity. The package manifest separately records exact SHA-256 and size for every generated file, so binary container differences remain verifiable without contaminating scientific identity.

Publication is fail-closed. The application writes and verifies a sibling staging directory, commits verified workspace-owned FigureSpec/package assets and evidence/composition provenance, then publishes the complete external directory. If final directory publication fails, the external package is not left authoritative and the workspace provenance transaction is rolled back to its exact pre-export state when that rollback remains safe.

A successful export is not an `AnalysisDocument` edit. It therefore preserves document SHA, revision, Undo/Redo stacks, and clean/dirty state while advancing only the session's expected workspace-manifest baseline to include the new provenance records.

## v1.0 compatibility shell

The reviewed v1.0 desktop remains available for explicit integrations through `catalysis_workbench.desktop.app.create_desktop(...)` and `ApplicationSession`. It retains workspace/asset, recipe, workflow, evidence/QA, and FigureSpec behavior.

The v1.1 task-first shell does not replace or migrate existing v1.0 workspaces. A v1.0 workspace that lacks `project.json` is reported as a legacy workspace when passed to the v1.1 Open Project path; the application does not guess which scientific task it represents.

The frozen v1.0 top-level `catalysis_workbench.desktop.__all__` contract remains a compatibility gate even though the v1.1 window exists through its explicit module/API path.

The cumulative Block-2 desktop preview compatibility entry point remains available for installed-wheel regression coverage while the current workbench routes normal preview refresh through live evaluation.

## Analysis-document lifecycle

The v1.1 `AnalysisDocument` and `AnalysisSession` live in the GUI-neutral application layer.

An untouched untitled analysis is **unsaved but clean**. It can return Home without a discard prompt. Once the user edits title, mapping, data ordering, committed processing state, or FigureDraft presentation state, the document becomes dirty and Home/Open/Exit transitions require Save, Discard, or Cancel.

Undo and redo restore semantic document identities. Saving establishes a new baseline but does not erase undo history. Export is intentionally excluded from semantic Undo/Redo because it is a verified file-system/provenance side effect rather than a document revision.

A saved project keeps application control state in `project.json`. `project.json` is reserved workspace metadata, not an ordinary workspace asset. Project saves verify exact workspace/project identities and fail closed when files changed outside the current analysis session.

Recent Projects is presentation-only `QSettings` history. It stores paths and last-opened UI timestamps but is not part of scientific provenance or project SHA identity. Missing entries stay visible as unavailable until the user removes them.

## Architecture boundary

The dependency direction is one-way:

```text
scientific layers
      ↓
   workflow
      ↓
  workspace
      ↓
 application
      ↓
   desktop
```

The desktop layer is presentation and interaction only. It does not own scientific algorithms, domain inference, QA policy, workflow scheduling, provenance reconstruction, or workspace persistence rules. Bounded parser inspection is delegated to the GUI-neutral I/O layer; scientific column meaning, units, processing parameters, figure state, and export transactions remain explicit application state.

`application.analysis` remains headless and must not import PySide6 or PyQt. Matplotlib rendering is invoked lazily by figure/export operations rather than imported as desktop state.

## Legacy workspace, recipe, evidence, and figure behavior

The v1.0 compatibility shell still supports explicit local workspace creation/opening and explicit file import. Import remains intentionally non-magical: callers supply source, stable asset ID, asset type, `copy` versus `reference`, and copy destination when applicable.

Recipe editing preserves literal `WorkflowRecipe` step order. Workflow execution still requires explicit in-memory inputs and explicit input identities; the compatibility desktop does not infer workflow inputs from catalog assets.

The compatibility shell can inspect reviewed run, evidence-ledger, and QA state without fabricating provenance. Existing FigureSpec presentation editing remains presentation-only and does not mutate scientific results.

## CI and packaging validation

Regular application tests remain Qt-free and the desktop extra is installed separately for offscreen Qt validation. The cumulative v1.1 Blocks 1–5 gates include:

- deterministic AnalysisDocument/task-catalog and schema migration tests;
- path-independent source/mapping/input identity and bounded preview tests;
- raw-copy persistence, mutation, tamper, rollback, and manifest-concurrency tests;
- task-specific scientific processing, explicit FE/current pairing, workflow execution, and identity tests;
- invalid-draft and previous-valid-result desktop behavior;
- FigureDraft exact binding, stale/refresh, display-range, and presentation-only tests;
- Figure Package semantic identity, full-source-data, missing-value, workspace provenance, and publication-rollback tests;
- cumulative fresh-wheel headless v1.1 Block 1–5 smokes;
- cumulative fresh-wheel offscreen v1.1 Block 1–5 desktop smokes;
- the existing frozen v1.0 installed-wheel and desktop compatibility smokes; and
- the complete Stable 1.0 Readiness compatibility matrix.

The development candidate is `1.1.0.dev0`. The existing Stable 1.0 Readiness workflow remains active as a frozen v1.0 API/desktop compatibility audit while its candidate-version and artifact checks follow the currently built v1.1 development wheel.

## Release boundary

v1.1 Block 5 does not authorize a Git tag, GitHub Release, or PyPI publication. Those remain separate release decisions.
