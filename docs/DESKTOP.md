# CatalysisWorkbench desktop shells

CatalysisWorkbench provides an optional local Qt presentation layer over the reviewed application, workspace, workflow, visualization, and scientific APIs. The base package remains usable without Qt.

## Stable and development lines

- stable baseline: `v1.0.0` at `22b944992bfd3791f91cc951f89eb22e8bf47325`;
- current development identity: `1.1.0.dev0`;
- current desktop phase: v1.1 Block 6 — Dogfooding Hardening & Desktop Cleanup;
- PyPI/package-registry publication: not performed.

The stable v1.0 compatibility shell remains available while v1.1 develops a task-first ordinary-user workbench.

## Installation

Base package:

```bash
python -m pip install .
```

Desktop extra:

```bash
python -m pip install ".[desktop]"
```

Approved optional GUI dependency:

```text
PySide6-Essentials>=6.11.2,<6.12
```

Qt is not a base runtime dependency. Importing `catalysis_workbench.desktop` remains lazy and does not import PySide6 until an actual graphical path is requested.

## Ordinary-user command line

After installing the desktop extra:

```bash
catalysis-workbench
```

opens the task-first v1.1 Home shell.

A saved v1.1 analysis project can be opened explicitly with:

```bash
catalysis-workbench --project /path/to/project
```

The installed version can be inspected without loading Qt:

```bash
catalysis-workbench --version
```

`python -m catalysis_workbench.desktop` uses the same task-first command-line path.

If graphical launch is requested without the optional desktop dependencies, the CLI prints an actionable `[desktop]` installation instruction instead of exposing a raw PySide6 import traceback.

The existing Python `launch_desktop(root)` compatibility behavior is not reinterpreted by the console command. Explicit legacy v1.0 integration paths remain frozen.

## v1.1 ordinary-user workflow

```text
Home
  -> Analysis Workbench
  -> Figure Workbench
  -> Export Figure Package
```

### Home

Home offers three reviewed tasks:

- LSV / Polarization;
- FE & Partial Current; and
- Generic XY Plot.

It also exposes Open Project and Recent Projects.

Choosing a task creates a clean in-memory analysis. A project directory is created only by an explicit Save Project action.

Recent Projects is presentation-only `QSettings` history. Paths and timestamps never participate in scientific identities. Block 6 caches resolved recent-project display state while the stored `(path, last_opened)` fingerprint is unchanged, so unrelated processing/Figure refreshes do not repeatedly reopen historical projects from disk.

### Analysis Workbench

The reviewed layout is:

```text
DATA  |  LIVE ANALYSIS PREVIEW  |  PROCESSING
```

The center preview remains the largest region.

#### Data intake and mapping

Normal-user tabular formats are:

- `.csv`;
- `.txt`;
- `.tsv`;
- `.dat`;
- `.xlsx`; and
- `.xlsm`.

The import dialog separates bounded read-only preview from explicit scientific mapping. The user confirms:

- X column;
- X meaning;
- X unit;
- optional X reference;
- Y column;
- Y meaning;
- Y unit; and
- series display name.

Parser state remains visible. Delimited text retains its resolved delimiter; Excel retains the selected sheet. Changing parser state invalidates confirmation until preview reload.

Unit inference remains deliberately conservative: only trailing square-bracket forms such as `Potential [V]` are inferred. Parentheses are not treated as units.

`Apply this mapping to compatible files` requires matching selected column positions, names, and conservatively inferred units. It does not silently reinterpret differently labeled files.

Before first save, the session retains verified source locations. First save stages verified workspace-owned raw copies and project control state before publication. After save, materialization uses the workspace-owned raw bytes. Missing, changed, or tampered bytes fail closed.

#### Live scientific processing

Processing state is explicit task-specific application state, not arbitrary recipe editing.

LSV / Polarization supports reviewed controls for:

- no RHE conversion, direct RHE offset, or reference-vs-SHE + pH conversion;
- temperature for the SHE/pH route;
- solution resistance and iR-correction fraction;
- optional geometric area/current-density normalization;
- explicit output current-density unit; and
- scientific analysis range.

FE & Partial Current requires explicit current-series ↔ FE-series pairs. The desktop does not infer pairs from filenames, display names, or order. FE/current x coordinates must already be compatible; no interpolation/resampling/nearest-match alignment is introduced.

Generic XY intentionally supports only the reviewed mapped-data path plus scientific analysis-range cropping. The v1.1 desktop does not add generic smoothing, fitting, baseline correction, or normalization.

Processing fields remain draft UI state until they form a valid scientific configuration and candidate evaluation succeeds. Invalid drafts do not mutate the committed `AnalysisDocument`. A previous valid result may remain visible only with an explicit stale label indicating that current settings are not applied.

### Figure Workbench

The reviewed layout is:

```text
CONTENT  |  PUBLICATION PREVIEW  |  PROPERTIES
```

`FigureDraft` is presentation state bound to exact scientific trace identities. Figure edits can control:

- selected result view;
- trace visibility/order/labels;
- publication preset;
- physical figure size;
- axis labels and scales;
- display ranges;
- legend;
- typography; and
- line/marker styling.

Presentation edits never rewrite scientific processing or arrays.

Figure display range is distinct from scientific analysis range. If scientific results change, the FigureDraft becomes stale. Styling/export remains blocked until the user explicitly refreshes the Figure from Analysis.

### Figure Package Export

The reviewed package formats are:

- figure: SVG, PDF, PNG;
- source data: XLSX, TXT.

At least one figure format and one source-data format are required. The destination must be a new directory with an existing real parent directory.

Preflight requires:

- saved and clean project state;
- current rather than stale FigureDraft;
- available configured font family; and
- at least one visible trace.

Block 6 adds an explicit `Save Project` button when export preflight reports an unsaved/dirty project. This remains an explicit save; first save still asks the user for the project location. There is no hidden autosave.

After success, the Export page exposes:

- `Open Folder` — asks the operating system to open/reveal the package directory; and
- `Export Another` — clears the destination/success presentation state while retaining selected formats.

The application does not automatically overwrite, merge, or suffix existing packages.

Source-data output contains the **full scientific arrays** for visible traces. Figure display limits never crop source data. TXT/XLSX preserve missing-value information. The package manifest records a path-independent semantic package identity plus exact per-file SHA-256/size verification.

Package generation and publication are staged and fail closed. Unknown concurrent target/workspace content is never silently deleted during rollback.

A successful export advances workspace provenance but is not an `AnalysisDocument` semantic revision; document SHA, revision, Undo/Redo, and clean/dirty state are preserved.

## Block 6 hardening behavior

The Block-6 contract is in [`V1_1_BLOCK6.md`](V1_1_BLOCK6.md).

The final fresh-wheel desktop gate covers Generic XY, LSV, and FE/Partial Current from real file-backed inputs through Figure Package generation and saved-project reopen verification.

Block 6 also hardens errors at the desktop presentation boundary. User dialogs provide a short actionable summary and retain the exact original exception text under technical details. This does not repair or reinterpret failed scientific/application state.

High-value guidance exists for externally changed project/workspace state, legacy v1.0 workspaces presented to the v1.1 path, and unavailable figure fonts. Unknown errors retain their exact underlying message.

## v1.0 compatibility shell

The reviewed v1.0 desktop remains available for explicit integrations through `catalysis_workbench.desktop.app.create_desktop(...)` and `ApplicationSession`.

The v1.1 task-first shell does not automatically migrate legacy v1.0 workspaces. A legacy workspace without `project.json` fails closed when passed to the v1.1 Open Project path.

The frozen v1.0 top-level `catalysis_workbench.desktop.__all__` contract remains unchanged during v1.1 development even though explicit v1.1 modules/classes exist.

## Architecture boundary

Dependency direction remains:

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

The desktop owns presentation and interaction only. It does not own scientific algorithms, scientific inference, QA policy, workflow scheduling, provenance reconstruction, or workspace persistence rules.

`application.analysis` remains GUI-neutral and must not import PySide6/PyQt. Matplotlib rendering is invoked only by reviewed visualization/application paths.

## CI and installed-wheel validation

Regular scientific/application tests remain Qt-free. The desktop extra is installed separately for offscreen validation.

The cumulative v1.1 gates include:

- deterministic AnalysisDocument/task-catalog/schema compatibility tests;
- data intake, mapping, raw-copy, mutation/tamper/rollback tests;
- LSV/FE/Generic XY scientific-processing and identity tests;
- invalid processing-draft and previous-valid-result behavior;
- FigureDraft exact binding, stale/refresh, display-range, and presentation-only tests;
- Figure Package identity/full-source-data/provenance/rollback tests;
- fresh-wheel Qt-free `catalysis-workbench --version` validation;
- complete offscreen Generic XY/LSV/FE desktop dogfood journeys;
- frozen v1.0 installed-wheel and desktop compatibility smokes; and
- complete Stable 1.0 Readiness platform coverage.

The development candidate remains `1.1.0.dev0`.

## Release boundary

Block 6 does not authorize final `1.1.0`, a v1.1 tag, GitHub Release, installer publication, or PyPI/package-registry publication. Those remain separate decisions after dogfooding review.
