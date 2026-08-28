# CatalysisWorkbench

CatalysisWorkbench is a local Python workbench for quantitative catalysis data post-processing, reproducible workflows, scientific QA/evidence, and publication-quality visualization.

## Current development state

The active development identity is `1.0.0.dev0` on the v1.0 line. The reviewed v1.0 architecture adds a local workspace, explicit asset catalog, persistent evidence ledger, recipe/FigureSpec composition, a GUI-neutral application session, and an optional desktop presentation shell on top of the existing scientific APIs.

Release status remains deliberately separate from development state:

- `v0.7.0` is the only currently retained stable GitHub Release/tag and remains fixed on `e3062fc12c794f54c7b7613875ec73608a587a59`;
- v0.8 is a completed operando/time-resolved scientific implementation milestone with no routine tag or GitHub Release;
- v0.9 is the completed reproducible-workflow development foundation carried into v1.0, with no routine tag or GitHub Release;
- `1.0.0.dev0` is a development version, not a stable release;
- stable `1.0.0`, a v1.0 tag, GitHub Release, and PyPI/package-registry publication all require separate explicit authorization.

Live GitHub state is authoritative if descriptive documentation drifts.

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

Optional structure adapters:

```bash
python -m pip install ".[structure]"
```

Optional volumetric 3-D backend:

```bash
python -m pip install ".[volumetric3d]"
```

Optional v1.0 desktop shell:

```bash
python -m pip install ".[desktop]"
python -m catalysis_workbench.desktop
```

The desktop extra uses `PySide6-Essentials>=6.11.2,<6.12`. Qt is not an ordinary runtime dependency. Importing `catalysis_workbench.desktop` remains lazy and does not load PySide6 until a desktop class or launcher is requested. See [`docs/DESKTOP.md`](docs/DESKTOP.md).

## Architecture

The dependency direction is intentionally one-way:

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

- scientific packages own numerical and scientific semantics;
- `workflow` owns reviewed literal recipe execution, batching, QA, and deterministic run evidence;
- `workspace` owns explicit local project state, asset identity, evidence associations, and recipe/figure composition;
- `application` owns GUI-neutral transaction-safe session state and user-action orchestration;
- `desktop` owns presentation and interaction only.

The desktop/workspace layers do not infer chemistry, select parsers from filenames as scientific authority, discover arbitrary operations, execute serialized callables, reinterpret ordered recipes as DAGs, or silently normalize/convert scientific state.

## v1.0 workspace and application surface

The v1.0 development line adds:

- strict file-backed `WorkspaceManifest` persistence with deterministic SHA-256 identity and confined workspace-owned paths;
- explicit asset import with caller-selected source, stable asset ID/type, and explicit `copy` versus `reference` policy;
- deterministic persistent evidence records referencing existing reviewed recipe/run/batch/QA identities;
- workspace composition for recipe snapshots, explicit input/output assets, FigureSpec/preset state, exported figures, and pinned evidence/content digests;
- a headless `ApplicationSession` with transaction-safe workspace state, ordered recipe editing, explicit workflow execution, explicit QA aggregation, and FigureSpec editing;
- an optional Qt Widgets desktop shell for workspace creation/opening, asset navigation/import, recipe inspection/editing, run/evidence/QA inspection, FigureSpec presentation controls, and integration with the existing Matplotlib FigureSpec editor.

Workspace/application convenience never replaces the existing reviewed scientific IO, workflow, QA, or visualization contracts.

## Scientific capability summary

CatalysisWorkbench retains the reviewed scientific scope developed through v0.8:

- electrochemistry: LSV/polarization processing, Tafel, Faradaic efficiency, product partial-current density, activity normalization, TOF/TOFapp, CV/Cdl/ECSA, stability, RRDE/Koutecky-Levich, and EIS;
- characterization: XRD, Raman, FTIR/ATR-FTIR, TGA/DTG/TPR/TPD, gas sorption/BET, ICP/composition, XPS, XAS/XANES, FT-EXAFS, WT-EXAFS, and neutral EXAFS fit summaries;
- product analysis: explicit calibration, inverse quantification, named factors, replicate summaries, and passive calibration plotting;
- computation: atomic structures, explicit periodic geometry, DFT energy bookkeeping, DOS/PDOS, band centers, Bader, COHP/ICOHP, geometry-bonding correlations, CHE/free-energy state, charge-density difference, band/PROCAR/LOCPOT/NEB processing, and optional static volumetric 3-D rendering;
- operando/time-resolved: immutable exact-grid stacks, exact measured-point operations, passive waterfall/heatmap/cut/trace rendering, Raman/FTIR/XAS/XANES/XRD adapters, explicit descriptor trajectories, and explicit Pearson cross-modal comparison.

Scientific transformations remain explicit and fail closed on incompatible state. Plotting and desktop presentation remain passive consumers of reviewed scientific results.

## Basic Python workflow

```python
from catalysis_workbench.io import read_csv
from catalysis_workbench.experimental.echem import LSVProcessingConfig, process_lsv
from catalysis_workbench.visualization import export_figure, get_preset
from catalysis_workbench.experimental.echem import plot_lsv

raw = read_csv(
    "examples/data/lsv_example.csv",
    x="Potential [V]",
    y="Current [mA]",
    source_id="example",
)
processed = process_lsv(
    raw[0],
    LSVProcessingConfig(
        rhe_offset_v=0.97,
        source_reference="Ag/AgCl",
        resistance_ohm=5.0,
        electrode_area_cm2=0.196,
        normalize_to_current_density=True,
    ),
)
spec = get_preset("publication").with_export(dpi=300)
fig, _ = plot_lsv(processed, spec)
export_figure(fig, "lsv.svg", spec=spec)
```

The library does not silently guess reference electrodes, pH, current sign, electrode area, scientific units, chemistry, or analysis parameters.

## Public package map

- `catalysis_workbench.core` — shared immutable scientific data models.
- `catalysis_workbench.io` — reviewed tabular/scientific file readers.
- `catalysis_workbench.processing` — reusable numerical processing and shared constrained fitting.
- `catalysis_workbench.experimental` — electrochemistry, characterization, product, and operando analysis.
- `catalysis_workbench.computation` — atomistic/DFT post-processing.
- `catalysis_workbench.visualization` — immutable figure specifications and publication renderers.
- `catalysis_workbench.workflow` — reproducible recipes, explicit execution/batching, QA, and evidence.
- `catalysis_workbench.workspace` — local project persistence, asset/evidence/composition state.
- `catalysis_workbench.application` — GUI-neutral transaction-safe session/controller API.
- `catalysis_workbench.desktop` — optional lazy-loaded Qt presentation shell.

Package-level `__all__` surfaces define supported public imports; implementation-only names should be treated as internal during development.

## Development and release governance

Every feature follows the same promotion discipline:

```text
latest verified main
→ scoped branch
→ implementation + regression tests
→ Draft PR
→ exact-head GitHub CI
→ formal review
→ fixes + fresh exact-head CI when required
→ final review on final head
→ Ready
→ separate merge authorization
→ expected-head squash merge
→ exact main-head verification
→ post-merge CI verification
```

Ready status is not merge authorization. Branch deletion, tags, GitHub Releases, stable-version finalization, and package-registry publication are separately gated operations.

See [`docs/MASTER_PLAN.md`](docs/MASTER_PLAN.md) for the current execution map, [`docs/ROADMAP.md`](docs/ROADMAP.md) for release direction, [`docs/V1_0_PLAN.md`](docs/V1_0_PLAN.md) for the v1.0 architecture contract, [`docs/DESKTOP.md`](docs/DESKTOP.md) for desktop behavior, and the retained `docs/V0_X_*` files for historical release/scientific evidence.
