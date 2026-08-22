# CatalysisWorkbench

**CatalysisWorkbench** is a Python workbench for quantitative post-processing, comparative analysis, and publication-quality visualization of catalysis experimental, characterization, and computational data.

## Scope

CatalysisWorkbench focuses on data that require secondary processing before they can be interpreted or used in an SCI figure.

### Experimental data
- Electrochemistry: LSV, CV, FE, partial current density, Tafel, ECSA/Cdl, RRDE/K-L, EIS, stability.
- Characterization: XRD, Raman, FTIR/ATR-FTIR, XPS, BET/sorption, XAS, composition, and thermal-analysis curves.
- Product analysis: calibration, GC/HPLC/NMR-derived quantification, product rates, and Faradaic efficiency.

### Computational data
- Atomic structures and geometry.
- Energetics, adsorption energies, CHE, and free-energy diagrams.
- DOS/PDOS and band-center analysis.
- Bader charge analysis.
- COHP/ICOHP bonding analysis.
- Charge-density difference and other volumetric data.

### Visualization
- Multi-catalyst curve comparison.
- Publication-ready spectra and electrochemical plots.
- Bar/scatter/correlation figures.
- Free-energy diagrams.
- Electronic-structure plots.
- Later: 3D structure and volumetric visualization.

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

The design separates scientific calculation from visualization:

```text
Raw data -> I/O -> standardized data -> scientific analysis -> result -> visualization/export
```

A catalyst or sample name is treated as lightweight metadata on a data series, allowing multiple catalysts to be compared in the same figure without introducing a laboratory sample-management system.

## v0.1.0 MVP

The first usable release will focus on the common XY-data workflow:

- Dataset and Series core models.
- Excel / CSV / TXT import.
- Multi-series handling for multiple catalysts.
- Crop, normalization, offset, baseline, smoothing, interpolation, and integration primitives.
- LSV/polarization-curve processing and plotting.
- XRD processing and multi-sample plotting.
- Raman processing and multi-sample plotting.
- Publication-quality SVG / PDF / PNG export.

## Roadmap

- **v0.1-v0.3:** core experimental post-processing: LSV, CV, FE, Tafel, ECSA, stability, XRD, Raman, FTIR, basic BET, composition and thermal curves.
- **v0.4-v0.6:** XPS, EIS, XAS and major DFT post-processing: structure, energetics, free energy, PDOS, Bader, COHP/ICOHP and charge-density difference.
- **v0.7-v1.0:** advanced volumetric visualization, operando/time-resolved data, correlations, batch workflows, reproducibility metadata and a local GUI.

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the detailed staged plan.

## Development status

CatalysisWorkbench is currently in early development. The `main` branch is kept stable; new work should be developed through feature branches and pull requests.
