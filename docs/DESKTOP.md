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

The Block-2 Analysis Workbench adds explicit scientific-data intake while preserving the task-first flow. Scientific processing controls and Figure Workbench integration remain later v1.1 blocks.

## v1.1 Block 2 data intake and mapping

The normal Analysis Workbench is a three-column view:

```text
DATA  |  LIVE ANALYSIS PREVIEW  |  PROCESSING
```

The center preview remains the largest region. Block 2 displays mapped raw values only; import does not apply RHE conversion, iR correction, current normalization, interpolation, smoothing, fitting, or any other scientific transformation.

### Add files

`+ Add files` and drag-and-drop accept the reviewed tabular formats:

- `.csv`;
- `.txt`;
- `.tsv`;
- `.dat`;
- `.xlsx`; and
- `.xlsm`.

Multiple files can be selected in one intake operation. Recursive directory import, legacy `.xls`, and normal-user external-reference mode are intentionally outside Block 2.

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

### Data list and preview

Mapped series appear in the DATA list. The user can:

- rename a series;
- reorder series by drag-and-drop;
- edit a mapping;
- inspect a read-only data preview; and
- remove a series from the analysis.

The central Matplotlib preview is presentation-only. Large series may be sampled for display responsiveness, but that display sampling never changes the materialized scientific `Series`, its input identity, or the saved raw bytes.

`Continue to Figure` remains disabled in Block 2 because scientific processing validity is not yet defined by this block.

### Saved raw ownership and fail-closed behavior

Before the first save, the analysis session keeps verified transient locations for the selected source bytes. The first Save Project operation stages the project and workspace-owned raw copies before the final project directory becomes authoritative.

After a successful save, materialization and Edit Mapping use the verified workspace-owned copy rather than depending on the original external path. Moving or deleting the original external file therefore does not break a correctly saved project.

Raw-file mutation and workspace-copy tampering fail closed. The application re-verifies the expected source digest before materialization or mapping edits and pins that expected digest into the batch copy itself, so a source that changes between pre-save verification and copying is rolled back before the workspace manifest is committed.

Workspace batch-copy operations use expected-manifest checks. Project/document writes retain the existing exact-identity concurrency rules, and failed first-save staging is rolled back without deleting unknown external content.

## v1.0 compatibility shell

The reviewed v1.0 desktop remains available for explicit integrations through `catalysis_workbench.desktop.app.create_desktop(...)` and `ApplicationSession`. It retains workspace/asset, recipe, workflow, evidence/QA, and FigureSpec behavior.

Block 2 does not replace or migrate existing v1.0 workspaces. A v1.0 workspace that lacks `project.json` is reported as a legacy workspace when passed to the v1.1 Open Project path; the application does not guess which scientific task it represents.

The frozen v1.0 top-level `catalysis_workbench.desktop.__all__` contract is retained as a compatibility gate even though the new v1.1 window exists through its explicit module/API path.

## Analysis-document lifecycle

The v1.1 `AnalysisDocument` and `AnalysisSession` live in the GUI-neutral application layer.

An untouched untitled analysis is **unsaved but clean**. It can return Home without a discard prompt. Once the user edits the title or mapped data state, the document becomes dirty and Home/Open/Exit transitions require Save, Discard, or Cancel.

Undo and redo restore semantic document identities. Saving establishes a new baseline but does not erase undo history.

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

The desktop layer is presentation and interaction only. It does not own scientific algorithms, domain inference, QA policy, workflow scheduling, provenance reconstruction, or workspace persistence rules. Bounded parser inspection is delegated to the GUI-neutral I/O layer; scientific column meaning and units remain explicit application state.

`application.analysis` remains headless and must not import PySide6, PyQt, or Matplotlib pyplot.

## Legacy workspace, recipe, evidence, and figure behavior

The v1.0 compatibility shell still supports explicit local workspace creation/opening and explicit file import. Import remains intentionally non-magical: callers supply source, stable asset ID, asset type, `copy` versus `reference`, and copy destination when applicable.

Recipe editing preserves literal `WorkflowRecipe` step order. Workflow execution still requires explicit in-memory inputs and explicit input identities; the compatibility desktop does not infer workflow inputs from catalog assets.

The compatibility shell can inspect reviewed run, evidence-ledger, and QA state without fabricating provenance. Existing FigureSpec presentation editing remains presentation-only and does not mutate scientific results.

## CI and packaging validation

The regular CI remains Qt-free for base application tests and separately installs the desktop extra for offscreen Qt validation. The cumulative v1.1 Block-1/Block-2 gates include:

- deterministic AnalysisDocument and task-catalog tests;
- schema-1 to schema-2 compatibility and migration checks;
- path-independent source/mapping/input identity tests;
- bounded tabular-preview and deterministic materialization tests;
- dirty/unsaved and Undo/Redo session tests;
- raw-copy persistence, source-mutation, tamper, rollback, and manifest-concurrency tests;
- strict project persistence, symlink, reserved-metadata, and first-save staging tests;
- fresh-wheel v1.1 application data-intake smoke coverage;
- the existing frozen v1.0 desktop smoke;
- the v1.1 Home/Analysis desktop smoke; and
- a fresh-wheel offscreen Block-2 desktop intake/mapping/raw-copy smoke, including a negative compatibility check for same-position columns with different semantics.

The development candidate is `1.1.0.dev0`. The existing Stable 1.0 Readiness workflow remains active as a frozen v1.0 API/desktop compatibility audit while its candidate-version and artifact checks follow the currently built v1.1 development wheel.

## Release boundary

v1.1 Block 2 does not authorize a Git tag, GitHub Release, or PyPI publication. Those remain separate release decisions.
