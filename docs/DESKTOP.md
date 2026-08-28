# CatalysisWorkbench desktop shell

The v1.0 development line adds an optional local desktop presentation layer on top of the reviewed application, workspace, workflow, visualization, and scientific APIs.

## Installation

The base package remains Qt-free:

```bash
python -m pip install .
```

Install the desktop extra only when a Qt Widgets shell is required:

```bash
python -m pip install ".[desktop]"
```

The approved Block-6 extra is:

```text
PySide6-Essentials>=6.11.2,<6.12
```

It is optional rather than a normal runtime dependency. The first shell requires Qt Core/Gui/Widgets only and deliberately does not depend on the larger PySide6 Addons wheel.

## Launch

From an environment containing the desktop extra:

```bash
python -m catalysis_workbench.desktop
```

The `catalysis_workbench.desktop` package itself is lazy. Importing it does not import PySide6. Toolkit modules are loaded only when a desktop class or launcher is requested. If the optional extra is absent, desktop access fails with a targeted `DesktopDependencyError` rather than breaking base-package imports.

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

The desktop layer is presentation and interaction only. It does not own scientific algorithms, parsing rules, QA policy, workflow scheduling, provenance reconstruction, or workspace persistence semantics.

The shell routes mutations through `catalysis_workbench.application` and reviewed lower-layer APIs. It does not directly replace their contracts.

## Workspace actions

The first shell supports explicit local workspace creation/opening, asset navigation, and explicit file import.

Import remains intentionally non-magical. The user supplies the source file, stable asset ID, asset type, `copy` versus `reference` policy, and copy destination when applicable. The desktop does not guess a scientific parser or technique from an extension and does not recursively crawl directories.

Workspace/session transitions are fail-closed around unsaved recipe or `FigureSpec` state. Opening, closing, creating, or importing cannot silently discard dirty application edits. A caller must save or explicitly choose a discard path.

## Recipe and workflow behavior

Recipe editing preserves literal `WorkflowRecipe` step order. Moving a recipe step is not DAG scheduling and does not trigger dependency inference or topological sorting.

Workflow execution still requires explicit in-memory inputs and explicit input identities. The desktop does not infer runtime inputs from catalog assets and does not dynamically import or discover operations from serialized state.

## Evidence and QA

The shell can inspect already reviewed run, evidence-ledger, and QA state. It does not fabricate provenance and does not auto-select QA checks. QA execution remains an explicit application/workflow operation over caller-supplied reviewed findings.

## Figure presentation

The shell edits reviewed immutable `FigureSpec` presentation state through the application layer. Export-oriented controls change presentation only and do not mutate scientific results.

The existing Matplotlib `FigureSpec` editor remains the detailed interactive presentation editor. The Qt shell provides an explicit integration hook and requires explicit `Series` or `Dataset` data for that editor; it does not infer scientific data from file names or workspace metadata.

## Headless and packaging validation

Block 6 keeps the existing base CI jobs Qt-free and adds a separate `desktop-smoke` job. The desktop job:

- builds the exact project wheel;
- installs `catalysis-workbench[desktop]` in a fresh environment;
- runs `pip check`;
- sets `QT_QPA_PLATFORM=offscreen`;
- creates and destroys the Qt application/window without entering a persistent event loop; and
- exercises representative workspace, asset, recipe, evidence/QA, and figure-presentation bindings.

The ordinary fresh-wheel smoke separately verifies that the desktop package can be imported without loading PySide6 and that base application/workspace APIs remain usable without the desktop extra.

## Release boundary

The current development identity remains `1.0.0.dev0`. Adding the optional desktop extra does not authorize a stable `1.0.0`, Git tag, GitHub Release, or PyPI publication. Those remain separate release decisions.
