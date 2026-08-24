# CatalysisWorkbench

**CatalysisWorkbench** is a Python workbench for quantitative post-processing, comparative analysis, and publication-quality visualization of catalysis experimental, characterization, and computational data.

The reviewed v0.1 scientific foundation covers common one-dimensional XY workflows: tabular import, reusable processing, LSV/polarization curves, XRD, Raman, and exact-size PNG/SVG/PDF export. v0.2 development is extending that foundation into quantitative electrochemistry; shared electrochemistry quantity/provenance conventions, scatter/bar rendering, Tafel analysis, Faradaic efficiency, and product partial-current density are already merged on `main`.

## Install from a source checkout

CatalysisWorkbench currently targets Python 3.11+.

```bash
python -m pip install -e .
```

For development and tests:

```bash
python -m pip install -e ".[dev]"
```

The v0.1.0 release process uses a separate release-hardening gate followed by a final-version gate. A `v0.1.0` tag must point to reviewed `main` only after the final-version CI/review passes and explicit release authorization is given; see [`docs/RELEASING.md`](docs/RELEASING.md).

## Quickstart: CSV -> LSV processing -> publication export

```python
from catalysis_workbench.experimental.echem import (
    LSVProcessingConfig,
    plot_lsv,
    process_lsv,
    rhe_offset_from_she,
)
from catalysis_workbench.io import read_csv
from catalysis_workbench.visualization import FigureSpec, export_figure, get_preset

raw = read_csv(
    "examples/data/lsv_example.csv",
    x="Potential [V]",
    y="Current [mA]",
    source_id="quickstart-lsv",
)

# Illustrative Ag/AgCl reference potential versus SHE. Replace this with the
# value appropriate to the actual reference electrode/filling solution.
rhe_offset_v = rhe_offset_from_she(
    reference_potential_vs_she_v=0.210,
    ph=13.0,
    temperature_k=298.15,
)

processed = process_lsv(
    raw[0],
    LSVProcessingConfig(
        rhe_offset_v=rhe_offset_v,
        source_reference="Ag/AgCl",
        resistance_ohm=5.0,
        electrode_area_cm2=0.196,
        normalize_to_current_density=True,
    ),
)

spec: FigureSpec = (
    get_preset("publication")
    .with_layout(figure_width_in=3.5, figure_height_in=2.625)
    .with_style(axis_label_size=8, tick_label_size=7, line_width=1.2)
    .with_export(dpi=300)
)

fig, _ = plot_lsv(processed, spec)
export_figure(fig, "lsv.svg", spec=spec)
export_figure(fig, "lsv.pdf", spec=spec)
export_figure(fig, "lsv.png", spec=spec)
```

The processing API does not silently guess a reference electrode, pH, reference potential, current sign, or electrode area. Those choices remain explicit and are stored in provenance.

Three complete compact examples are available in [`examples/`](examples/):

```bash
python examples/lsv_quickstart.py
python examples/xrd_quickstart.py
python examples/raman_quickstart.py
```

## Public API map

The supported import surfaces are intentionally organized by responsibility rather than re-exporting every object from the package root.

- `catalysis_workbench.core`: `Axis`, `Series`, `Dataset`.
- `catalysis_workbench.io`: `read_csv`, `read_txt`, `read_excel`, `read_tabular`, `TabularReadError`.
- `catalysis_workbench.processing`: crop, normalization, offset, Savitzky-Golay smoothing, interpolation, integration, explicit baseline subtraction, Dataset mapping, and processing errors/results.
- `catalysis_workbench.experimental.echem`: reviewed LSV processing/configuration; explicit electrochemistry quantity/reference/provenance helpers; Tafel fitting; Faradaic-efficiency analysis and closure QA; product partial-current density and closure QA; plus lazy publication plotting adapters.
- `catalysis_workbench.experimental.characterization`: XRD and Raman validation, processing, quantitative Raman-band helpers, annotations/reference sticks, and `plot_xrd` / `plot_raman`.
- `catalysis_workbench.visualization`: `FigureSpec`, `LayoutSpec`, `PlotStyle`, `SeriesStyle`, annotations/export settings, presets, shared curve/scatter/bar renderers, and `export_figure`.

Objects or functions in implementation modules that are not exported by these package-level `__all__` surfaces should be treated as internal and may change during development.

## Scope

CatalysisWorkbench focuses on data that require secondary processing before they can be interpreted or used in an SCI figure.

### Experimental data

- Electrochemistry: LSV/polarization processing, shared quantity/provenance conventions, Tafel analysis, Faradaic efficiency, and product partial-current density are implemented. Mass/specific activity, TOF/TOFapp, CV/Cdl/ECSA, stability, and RRDE/K-L are the remaining planned v0.2 sequence.
- Characterization: XRD and Raman are implemented; FTIR/ATR-FTIR, XPS, BET/sorption, XAS, composition, and thermal-analysis curves are staged later.
- Product analysis: v0.2 Faradaic efficiency starts from already quantified product amounts or rates. Raw calibration and GC/HPLC/NMR-derived quantification workflows remain staged after the core electrochemistry foundation.

### Computational data

Planned modules cover atomic structures, geometry, adsorption/free energies, CHE, DOS/PDOS, Bader charge, COHP/ICOHP, charge-density difference, and related post-processing. These are not part of the current implemented core.

### Visualization

The shared visualization layer provides publication-ready curve, scatter, and categorical bar rendering with adjustable figure/axes geometry, typography, lines/markers, ticks, legends, annotations, limits, presets, explicit errors where supplied, stable-key styling, and exact-size PNG/SVG/PDF export. Later releases will build advanced scientific visualizations and interactive editing on the same explicit figure-state model.

## Out of scope

CatalysisWorkbench is not intended to manage synthesis records, laboratory notebooks, inventory, TEM/SEM image processing, instrument control, HPC job submission, or complete VASP workflow management.

## Architecture

```text
src/catalysis_workbench/
├── core/              # Shared scientific data models
├── io/                # Excel/CSV/TXT and scientific file readers
├── processing/        # Reusable mathematical processing
├── experimental/      # Experimental analysis
│   ├── echem/
│   └── characterization/
├── computation/       # DFT and atomistic post-processing
└── visualization/     # Publication-quality rendering
```

Scientific calculation and visualization are deliberately separated:

```text
Raw data -> I/O -> standardized data -> scientific analysis -> result -> visualization/export
```

A catalyst or sample name remains lightweight metadata on a data series; CatalysisWorkbench does not introduce a laboratory sample-management system.

## Release and development status

The v0.1 scientific/common-XY feature set and release-hardening gate are complete. v0.2 development has completed the shared electrochemistry foundation (#19), scatter/bar rendering (#20), Tafel (#21), Faradaic efficiency (#22), and product partial-current density (#23). The next implementation target is **Issue #24: mass and specific activity normalization**.

New functionality follows a strict feature loop: prior-art scan with license recording, implementation/regression tests, CI, Draft PR, scientific/API/compatibility review, fixes, CI, second review, Ready/merge gate, squash merge, `main` CI verification, then issue closure.

See [`docs/MASTER_PLAN.md`](docs/MASTER_PLAN.md) for the project-wide execution model and current checkpoint, [`docs/V0_2_PLAN.md`](docs/V0_2_PLAN.md) for the active v0.2 dependency/order plan, and [`docs/ROADMAP.md`](docs/ROADMAP.md) for the long-range release scope.

## Roadmap

- **v0.2:** quantitative core electrochemistry, with #19-#23 complete and #24-#28 remaining in the planned sequence.
- **v0.3-v0.6:** extended experimental characterization, advanced electrochemistry, XAS, structures, and major DFT post-processing.
- **v0.7-v1.0:** advanced volumetric visualization, operando/time-resolved analysis, reproducible batch workflows, and a local GUI.

The `main` branch is kept stable. New work should be developed through feature/release branches and pull requests, and live GitHub repository state remains authoritative if descriptive documentation becomes stale.
