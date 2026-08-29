# CatalysisWorkbench v1.1 plan

## Purpose

v1.1 moves the optional desktop from a workspace-first administration shell toward a task-first scientific workbench while preserving the reviewed v1.0 scientific, workflow, provenance, and workspace contracts.

The first implementation block is intentionally narrow: it establishes a deterministic analysis-document lifecycle and a Home/Analysis presentation shell. Real data import, scientific processing, workflow execution, and publication-figure work remain later blocks.

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

`AnalysisDocument` is immutable and deterministic. Its serialized scientific/application state is only:

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

The project envelope is:

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
