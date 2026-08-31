# CatalysisWorkbench

CatalysisWorkbench is a local Python workbench for quantitative catalysis data post-processing, reproducible workflows, scientific QA/evidence, and publication-quality visualization.

## Current state

The retained stable baseline is **CatalysisWorkbench v1.0.0**. The immutable `v1.0.0` tag points to:

```text
22b944992bfd3791f91cc951f89eb22e8bf47325
```

A public GitHub Release named `CatalysisWorkbench v1.0.0` exists for that stable line.

The active v1.1 final-version candidate identity is:

```text
1.1.0
```

v1.1 Blocks 1–6 and Stable 1.1 Gate A are complete and merged on `main`. Gate A was squash-merged as `843df51828d740405aa5365142541ed361e069cc`; post-merge CI #854, Stable 1.0 Readiness #116, and Stable 1.1 Readiness #3 all succeeded on that exact commit.

Stable 1.1 Gate B now performs mechanical final-version synchronization only: distribution/runtime identity, version-sensitive smoke evidence, and exact artifact expectations are `1.1.0`. Gate B does **not** create `v1.1.0`, publish a GitHub Release, create installers, or upload to a package registry.

PyPI/package-registry publication remains deferred until a separately verified publication gate. Live GitHub state is authoritative if descriptive documentation drifts.

## Installation

CatalysisWorkbench targets Python 3.11+.

Base installation from a source checkout:

```bash
python -m pip install .
```

Development/test environment:

```bash
python -m pip install ".[dev]"
```

Optional desktop:

```bash
python -m pip install ".[desktop]"
```

The desktop extra uses:

```text
PySide6-Essentials>=6.11.2,<6.12
```

Qt remains optional and lazy-loaded. Importing the base package or asking for the installed version does not require PySide6.

Other optional extras remain available for reviewed structure and volumetric 3-D workflows:

```bash
python -m pip install ".[structure]"
python -m pip install ".[volumetric3d]"
```

## v1.1 task-first desktop

After installing the desktop extra, launch Home with either:

```bash
catalysis-workbench
```

or:

```bash
python -m catalysis_workbench.desktop
```

Open a saved v1.1 analysis project explicitly:

```bash
catalysis-workbench --project /path/to/project
```

Inspect the installed version without loading Qt:

```bash
catalysis-workbench --version
```

The normal v1.1 path is:

```text
Home
  -> choose LSV / FE & Partial Current / Generic XY
  -> Data Intake & Mapping
  -> Live Scientific Analysis
  -> Figure Workbench
  -> Figure Package Export
```

A task starts as a clean in-memory analysis. The desktop does not require a project directory until the first explicit Save Project action.

### Data Intake & Mapping

The reviewed desktop intake formats are `.csv`, `.txt`, `.tsv`, `.dat`, `.xlsx`, and `.xlsm`. Mapping explicitly records X/Y columns, scientific meaning, units, and optional reference state. Raw bytes are digest-pinned; after save, the project owns verified raw copies.

The desktop does not recursively crawl directories, infer chemistry, or silently reinterpret columns as scientific authority.

### Live Scientific Analysis

The reviewed task-first scientific paths are:

- **LSV / Polarization** — explicit reference/RHE handling, iR correction, optional area normalization, output current-density unit, and scientific analysis range;
- **FE & Partial Current** — explicit current-series ↔ FE-series pairing, compatible x grids, and signed partial-current calculation; and
- **Generic XY** — explicit mapped XY input with scientific analysis-range cropping only.

Invalid draft settings do not mutate the committed analysis. Hidden interpolation, nearest-match alignment, smoothing, baseline correction, fitting, normalization, and automatic FE/current pairing are not introduced by the desktop.

### Figure Workbench

Figure editing is presentation-only. It controls result/trace selection, visibility/order/labels, publication preset, physical size, axes, display ranges, legend, typography, lines, and markers.

A FigureDraft is bound to exact scientific trace identities. If analysis results change, the figure becomes stale and must be explicitly refreshed. Figure display limits do not crop the scientific arrays used for source-data export.

### Figure Package Export

A Figure Package can contain:

- figure files: SVG, PDF, PNG;
- scientific source data: XLSX, TXT; and
- a deterministic verification manifest.

Export requires a saved/clean project, a current FigureDraft, an available figure font, at least one visible trace, and a new destination directory. Block 6 adds an explicit Save Project action directly from export preflight plus post-export Open Folder and Export Another actions; it does not add hidden autosave or overwrite behavior.

The exported source data contains the full scientific arrays for visible traces. Figure display ranges never crop source-data output.

## v1.0 compatibility shell

The stable v1.0 workspace/application/desktop contracts remain frozen compatibility surfaces. Explicit integrations can continue to use `ApplicationSession` and the legacy desktop creation path in `catalysis_workbench.desktop.app.create_desktop(...)`.

The v1.1 task-first project format is not an automatic migration of a legacy v1.0 workspace. Opening a legacy workspace through the v1.1 project path fails closed rather than guessing a scientific task.

The frozen top-level `catalysis_workbench.desktop.__all__` contract remains unchanged during v1.1 development.

## Architecture

Dependency direction remains one-way:

```text
core / processing / io / experimental / computation / visualization
                              ↓
                           workflow
                              ↓
                          workspace
                              ↓
                         application
                              ↓
                     desktop presentation
```

Responsibilities remain separated:

- scientific packages own numerical/scientific semantics;
- `workflow` owns reviewed literal recipe execution, batching, QA, and deterministic run evidence;
- `workspace` owns explicit local project assets, evidence, and composition state;
- `application` owns GUI-neutral transaction-safe session state and user-action orchestration; and
- `desktop` owns presentation and interaction only.

The desktop layer does not become a second scientific execution engine.

## Scientific capability summary

The stable scientific surface carried into v1.1 includes the reviewed capabilities developed through v1.0:

- electrochemistry: LSV/polarization, Tafel, FE, partial current, activity normalization, TOF/TOFapp, CV/Cdl/ECSA, stability, RRDE/Koutecky-Levich, and EIS;
- characterization: XRD, Raman, FTIR/ATR-FTIR, TGA/DTG/TPR/TPD, gas sorption/BET, ICP/composition, XPS, XAS/XANES, FT-EXAFS, WT-EXAFS, and neutral EXAFS fit summaries;
- product analysis: explicit calibration, inverse quantification, named factors, replicate summaries, and passive calibration plotting;
- computation: structures, periodic geometry, DFT energetics, DOS/PDOS, band centers, Bader, COHP/ICOHP, geometry-bonding correlations, CHE/free-energy state, charge-density difference, band/PROCAR/LOCPOT/NEB processing, and optional static volumetric 3-D rendering; and
- operando/time-resolved analysis: immutable exact-grid stacks, measured-point operations, passive visualization, descriptor trajectories, and explicit cross-modal comparison.

Scientific transformations remain explicit and fail closed on incompatible state.

## Development governance

Promotion remains:

```text
latest verified main
-> scoped feature branch
-> implementation + focused regressions
-> Draft PR
-> exact-head GitHub CI
-> formal diff/review
-> fixes + fresh exact-head CI when required
-> final review on final head
-> Ready
-> STOP
-> separate merge authorization
-> expected-head squash merge
-> exact-main post-merge verification
```

Ready status is not merge authorization. Branch deletion, final-version changes, tags, GitHub Releases, and package-registry publication are separately gated operations.

## Project documents

- [`docs/MASTER_PLAN.md`](docs/MASTER_PLAN.md) — current execution/source-of-truth map.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — version and maturity direction.
- [`docs/V1_0_PLAN.md`](docs/V1_0_PLAN.md) — frozen v1.0 architecture contract.
- [`docs/V1_1_PLAN.md`](docs/V1_1_PLAN.md) — detailed v1.1 Blocks 1–5 architecture history.
- [`docs/V1_1_BLOCK6.md`](docs/V1_1_BLOCK6.md) — final v1.1 dogfooding/hardening contract.
- [`docs/DESKTOP.md`](docs/DESKTOP.md) — desktop installation, behavior, and compatibility details.
