# CatalysisWorkbench

**CatalysisWorkbench** is a Python workbench for quantitative post-processing, comparative analysis, and publication-quality visualization of catalysis experimental, characterization, and computational data.

The reviewed v0.1 scientific foundation covers common one-dimensional XY workflows: tabular import, reusable processing, LSV/polarization curves, XRD, Raman, and exact-size PNG/SVG/PDF export. The v0.2 quantitative-electrochemistry release is complete: shared electrochemistry quantity/provenance conventions, scatter/bar rendering, Tafel analysis, Faradaic efficiency, product partial-current density, activity normalization, TOF/TOFapp, CV/Cdl/ECSA, stability analysis, and RRDE/Koutecky-Levich basics are released as `v0.2.0`. v0.3 development is active on top of that stable release: reviewed FTIR / ATR-FTIR, TGA / DTG / TPR / TPD thermal analysis, and basic gas-sorption isotherm processing/publication plotting are now merged, while the package/runtime version intentionally remains `0.2.0` until a separate v0.3 release gate is reviewed.

## Install from a source checkout

CatalysisWorkbench currently targets Python 3.11+.

```bash
python -m pip install -e .
```

For development and tests:

```bash
python -m pip install -e ".[dev]"
```

The tagged v0.1.0 release used a separate release-hardening gate followed by a final-version gate; see [`docs/RELEASING.md`](docs/RELEASING.md). v0.2 followed the dedicated Gate A/B/C procedure in [`docs/V0_2_RELEASING.md`](docs/V0_2_RELEASING.md): Gate A / Issue #43 hardened the installed-wheel API, Gate B / Issue #45 finalized and validated `0.2.0`, and Gate C / Issue #47 created and verified tag `v0.2.0` on release commit `1f7f4057397c61ef2f771b96fceadc8a529b62d9`. Package-registry publication remains a separate policy decision.

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

Six complete compact examples are available in [`examples/`](examples/):

```bash
python examples/lsv_quickstart.py
python examples/xrd_quickstart.py
python examples/raman_quickstart.py
python examples/ftir_quickstart.py
python examples/thermal_quickstart.py
python examples/sorption_quickstart.py
```

## Public API map

The supported import surfaces are intentionally organized by responsibility rather than re-exporting every object from the package root.

- `catalysis_workbench.core`: `Axis`, `Series`, `Dataset`.
- `catalysis_workbench.io`: `read_csv`, `read_txt`, `read_excel`, `read_tabular`, `TabularReadError`.
- `catalysis_workbench.processing`: crop, normalization, offset, Savitzky-Golay smoothing, interpolation, integration, explicit baseline subtraction, Dataset mapping, and processing errors/results.
- `catalysis_workbench.experimental.echem`: reviewed LSV processing/configuration; explicit electrochemistry quantity/reference/provenance helpers; Tafel fitting; Faradaic-efficiency analysis and closure QA; product partial-current density and closure QA; catalyst-/metal-mass and ECSA activity normalization; TOF/TOFapp; CV/Cdl/ECSA; stability analysis; RRDE metrics; Koutecky-Levich fitting/apparent electron-number helpers; plus lazy publication plotting adapters.
- `catalysis_workbench.experimental.characterization`: XRD, Raman, FTIR/ATR-FTIR, TGA/DTG/TPR/TPD, and basic gas-sorption validation/processing; quantitative Raman/FTIR band helpers; explicit FTIR transmittance conversion and baseline fitting; explicit TGA mass normalization and DTG derivation/sign semantics; direct thermal-window extrema/area measurement; explicit gas-sorption `P/P0`, loading, adsorbate/temperature/branch/STP semantics and measured-point summaries; annotations/reference sticks; and lazy `plot_xrd` / `plot_raman` / `plot_ftir` / `plot_thermal` / `plot_sorption` adapters.
- `catalysis_workbench.visualization`: `FigureSpec`, `LayoutSpec`, `PlotStyle`, `SeriesStyle`, annotations/export settings, presets, shared curve/scatter/bar renderers, and `export_figure`.

Objects or functions in implementation modules that are not exported by these package-level `__all__` surfaces should be treated as internal and may change during development.

## Scope

CatalysisWorkbench focuses on data that require secondary processing before they can be interpreted or used in an SCI figure.

### Experimental data

- Electrochemistry: the v0.2 core is released — LSV/polarization processing, shared quantity/provenance conventions, Tafel, Faradaic efficiency, partial current density, mass/ECSA activity normalization, TOF/TOFapp, CV/Cdl/ECSA, stability, and RRDE/K-L basics. Advanced EIS and product-calibration workflows remain later roadmap work.
- Characterization: XRD, Raman, FTIR/ATR-FTIR, TGA/DTG/TPR/TPD, and the reviewed basic gas-sorption isotherm foundation are implemented. ICP/composition data integration is selected as the next v0.3 scientific module; shared peak-fitting, XPS, and XAS remain staged in the roadmap. Quantitative BET fitting remains v0.4 scope.
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

The v0.1 scientific/common-XY feature set is released as v0.1.0. The complete v0.2 implementation sequence #19-#28 plus Gate A/B/C release validation is released as `v0.2.0` on 2026-08-24. The tag resolves exactly to reviewed release commit `1f7f4057397c61ef2f771b96fceadc8a529b62d9`. Package-registry publication is not implied by the Git tag and remains out of scope until a separate distribution policy is reviewed.

Post-release v0.3 development is active on `main`: Issue #50 / PR #51 added FTIR/ATR-FTIR, Issue #54 / PR #55 added TGA/DTG/TPR/TPD thermal analysis, and Issue #58 / PR #59 added the basic gas-sorption isotherm foundation at merge commit `de0352970f79ce37467907116c02a3d8bc15a178`. These development modules intentionally leave the package/runtime version at `0.2.0`; no `v0.3.0` release or tag is implied by this state.

New functionality follows a strict feature loop: prior-art scan with license recording, implementation/regression tests, CI, Draft PR, scientific/API/compatibility review, fixes, CI, second review, Ready/merge gate, squash merge, `main` verification when visible, then issue closure. Release/version work uses the same exact-head discipline with release/API/packaging/version review.

See [`docs/MASTER_PLAN.md`](docs/MASTER_PLAN.md) for the project-wide execution model and current checkpoint, [`docs/V0_2_PLAN.md`](docs/V0_2_PLAN.md) for the completed v0.2 feature/release record, [`docs/V0_2_RELEASING.md`](docs/V0_2_RELEASING.md) for the completed v0.2 release gates and reusable release-policy record, [`docs/FTIR.md`](docs/FTIR.md) for the reviewed FTIR/ATR-FTIR scientific/API contract, [`docs/THERMAL_ANALYSIS.md`](docs/THERMAL_ANALYSIS.md) for the reviewed TGA/DTG/TPR/TPD scientific/API contract, [`docs/GAS_SORPTION.md`](docs/GAS_SORPTION.md) for the reviewed basic gas-sorption scientific/API contract, and [`docs/ROADMAP.md`](docs/ROADMAP.md) for the long-range release scope.

## Roadmap

- **v0.2:** released as `v0.2.0` on 2026-08-24 after reviewed scientific implementation and Gate A/B/C release validation.
- **v0.3:** development active; FTIR/ATR-FTIR, TGA/DTG/TPR/TPD, and basic gas-sorption processing/plotting are complete, with ICP/composition data integration selected next before shared peak-fitting primitives.
- **v0.4-v0.6:** advanced experimental analysis, XAS, structures, and major DFT post-processing.
- **v0.7-v1.0:** advanced volumetric visualization, operando/time-resolved analysis, reproducible batch workflows, and a local GUI.

The `main` branch is kept stable. New work should be developed through feature/release branches and pull requests, and live GitHub repository state remains authoritative if descriptive documentation becomes stale.
