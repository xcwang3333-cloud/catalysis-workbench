# CatalysisWorkbench

**CatalysisWorkbench** is a Python workbench for quantitative post-processing, comparative analysis, and publication-quality visualization of catalysis experimental, characterization, and computational data.

The v0.1 scientific foundation covers common one-dimensional XY workflows: tabular import, reusable processing, LSV/polarization curves, XRD, Raman, and exact-size PNG/SVG/PDF export.

## Install from a source checkout

CatalysisWorkbench currently targets Python 3.11+.

```bash
python -m pip install -e .
```

For development and tests:

```bash
python -m pip install -e ".[dev]"
```

The v0.1.0 release candidate has completed the separate release-hardening gate. The final `v0.1.0` tag is created only after the version-gate CI/review passes and an explicit final release authorization is given; see [`docs/RELEASING.md`](docs/RELEASING.md).

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

## Public API map for v0.1

The supported v0.1 import surfaces are intentionally organized by responsibility rather than re-exporting every object from the package root.

- `catalysis_workbench.core`: `Axis`, `Series`, `Dataset`.
- `catalysis_workbench.io`: `read_csv`, `read_txt`, `read_excel`, `read_tabular`, `TabularReadError`.
- `catalysis_workbench.processing`: crop, normalization, offset, Savitzky-Golay smoothing, interpolation, integration, explicit baseline subtraction, Dataset mapping, and processing errors/results.
- `catalysis_workbench.experimental.echem`: LSV processing/configuration, explicit RHE/iR/current-density helpers, and `plot_lsv`.
- `catalysis_workbench.experimental.characterization`: XRD and Raman validation, processing, quantitative Raman-band helpers, annotations/reference sticks, and `plot_xrd` / `plot_raman`.
- `catalysis_workbench.visualization`: `FigureSpec`, `LayoutSpec`, `PlotStyle`, `SeriesStyle`, annotations/export settings, presets, `render_curves`, and `export_figure`.

Objects or functions in implementation modules that are not exported by these package-level `__all__` surfaces should be treated as internal and may change during development.

## Scope

CatalysisWorkbench focuses on data that require secondary processing before they can be interpreted or used in an SCI figure.

### Experimental data

- Electrochemistry: LSV, with Tafel, CV, FE, partial current density, ECSA/Cdl, RRDE/K-L, EIS, and stability staged in later roadmap releases.
- Characterization: XRD and Raman in v0.1; FTIR/ATR-FTIR, XPS, BET/sorption, XAS, composition, and thermal-analysis curves are staged later.
- Product analysis: calibration, GC/HPLC/NMR-derived quantification, product rates, and Faradaic efficiency are staged after the core electrochemistry foundation.

### Computational data

Planned modules cover atomic structures, geometry, adsorption/free energies, CHE, DOS/PDOS, Bader charge, COHP/ICOHP, charge-density difference, and related post-processing. These are not part of v0.1.

### Visualization

v0.1 provides publication-ready curve rendering with adjustable figure/axes geometry, typography, lines/markers, ticks, legends, annotations, limits, presets, and exact-size PNG/SVG/PDF export. Shared scatter/bar and advanced scientific visualizations are staged in later releases.

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

## v0.1.0 release status

The v0.1 scientific/common-XY feature set and release-hardening gate are complete. The release candidate reports version `0.1.0`; before the `v0.1.0` tag is created, the version-gate branch must pass the full Ruff/pytest and installed-wheel smoke checks, receive formal review, be merged to `main`, and then receive explicit final tag authorization. See [`docs/V0_1_AUDIT.md`](docs/V0_1_AUDIT.md), [`CHANGELOG.md`](CHANGELOG.md), and [`docs/RELEASING.md`](docs/RELEASING.md).

## Roadmap

- **v0.2:** Tafel, FE, partial current, activity normalization, TOF/TOFapp, CV/Cdl/ECSA, stability, RRDE/K-L, plus shared electrochemistry quantity conventions and scatter/bar rendering.
- **v0.3-v0.6:** extended experimental characterization, advanced electrochemistry, XAS, structures, and major DFT post-processing.
- **v0.7-v1.0:** advanced volumetric visualization, operando/time-resolved analysis, reproducible batch workflows, and a local GUI.

See [`docs/ROADMAP.md`](docs/ROADMAP.md) and [`docs/V0_2_PLAN.md`](docs/V0_2_PLAN.md) for staged details.

## Development status

The `main` branch is kept stable. New work should be developed through feature/release branches and pull requests. v0.1 is feature-complete and release-hardened; the `0.1.0` version candidate remains untagged until the final release gate is explicitly approved.
