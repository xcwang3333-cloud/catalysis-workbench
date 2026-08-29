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

The no-argument launcher now opens the task-first v1.1 Home shell. Home offers:

- LSV / Polarization;
- FE & Partial Current;
- Generic XY Plot;
- Open Project; and
- Recent Projects.

Choosing a task creates a clean in-memory untitled analysis. It does **not** ask for a directory. The first Save Project operation creates the project directory and writes `workspace.json` plus `project.json`.

The Block-1 Analysis shell is deliberately an empty-state scaffold. Real data import/mapping, scientific analysis controls, and Figure Workbench integration are later v1.1 blocks.

## v1.0 compatibility shell

The reviewed v1.0 desktop remains available for explicit integrations through `catalysis_workbench.desktop.app.create_desktop(...)` and `ApplicationSession`. It retains workspace/asset, recipe, workflow, evidence/QA, and FigureSpec behavior.

Block 1 does not replace or migrate existing v1.0 workspaces. A v1.0 workspace that lacks `project.json` is reported as a legacy workspace when passed to the v1.1 Open Project path; the application does not guess which scientific task it represents.

The frozen v1.0 top-level `catalysis_workbench.desktop.__all__` contract is retained as a compatibility gate even though the new v1.1 window exists through its explicit module/API path.

## Analysis-document lifecycle

The v1.1 `AnalysisDocument` and `AnalysisSession` live in the GUI-neutral application layer.

An untouched untitled analysis is **unsaved but clean**. It can return Home without a discard prompt. Once the user edits the title (and, in later blocks, data/analysis state), the document becomes dirty and Home/Open/Exit transitions require Save, Discard, or Cancel.

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

The desktop layer is presentation and interaction only. It does not own scientific algorithms, parser guessing, QA policy, workflow scheduling, provenance reconstruction, or workspace persistence rules.

`application.analysis` remains headless and must not import PySide6, PyQt, or Matplotlib pyplot.

## Legacy workspace, recipe, evidence, and figure behavior

The v1.0 compatibility shell still supports explicit local workspace creation/opening and explicit file import. Import remains intentionally non-magical: callers supply source, stable asset ID, asset type, `copy` versus `reference`, and copy destination when applicable.

Recipe editing preserves literal `WorkflowRecipe` step order. Workflow execution still requires explicit in-memory inputs and explicit input identities; the desktop does not infer workflow inputs from catalog assets.

The compatibility shell can inspect reviewed run, evidence-ledger, and QA state without fabricating provenance. Existing FigureSpec presentation editing remains presentation-only and does not mutate scientific results.

## CI and packaging validation

The regular CI remains Qt-free for base application tests and separately installs the desktop extra for offscreen Qt validation. The v1.1 Block-1 gates include:

- deterministic AnalysisDocument and task-catalog tests;
- dirty/unsaved and Undo/Redo session tests;
- strict project persistence, concurrency, symlink, rollback, and reserved-metadata tests;
- a fresh-wheel v1.1 application smoke;
- the existing frozen v1.0 desktop smoke; and
- a fresh-wheel v1.1 Home/Analysis desktop smoke.

The development candidate is `1.1.0.dev0`. The existing Stable 1.0 Readiness workflow remains active as a frozen v1.0 API/desktop compatibility audit while its candidate-version and artifact checks follow the currently built v1.1 development wheel.

## Release boundary

v1.1 Block 1 does not authorize a Git tag, GitHub Release, or PyPI publication. Those remain separate release decisions.
