# CatalysisWorkbench Roadmap

CatalysisWorkbench is developed in staged releases. The project focuses on quantitative post-processing, comparative analysis, and publication-quality visualization of catalysis data.

Before implementing each major scientific or visualization module, comparable open-source projects should be surveyed and useful algorithms, data-model ideas, visualization patterns, tests, and license constraints recorded in [`REFERENCES.md`](REFERENCES.md).

## v0.1.0 — Common XY workflow

- Core `Dataset` / `Series` models.
- Excel / CSV / TXT import.
- Multi-catalyst series handling.
- Crop, normalization, offset, baseline, smoothing, interpolation, integration.
- LSV / polarization-curve processing and plotting.
- XRD processing and multi-sample plotting.
- Raman processing and multi-sample plotting.
- Shared `FigureSpec` / `PlotStyle` model with adjustable figure size, axes geometry/aspect ratio, fonts, line widths/styles, markers, ticks, legends, limits, margins and export settings.
- Publication presets as editable starting templates, not locked themes.
- SVG / PDF / PNG export.

## v0.2.0 — Core electrochemistry — released 2026-08-24

- Tafel analysis.
- Faradaic efficiency.
- Partial current density.
- Mass/specific activity.
- TOF / TOFapp.
- CV / Cdl / ECSA.
- Stability analysis.
- RRDE / Koutecky–Levich basics.
- Installed-wheel public-API and representative numerical smoke coverage for the reviewed v0.2 electrochemistry surface.

## v0.3.x — Extended experimental processing — in progress

- FTIR / ATR-FTIR — implemented and merged through Issue #50 / PR #51.
- TGA / DTG / TPR / TPD — implemented and merged through Issue #54 / PR #55.
- Basic BET / gas-sorption plotting — selected as the next v0.3 scientific module; prior-art and scientific/API contract review are required before implementation.
- ICP/composition data integration — planned.
- Shared peak-fitting primitives — planned.

The remaining v0.3 modules are roadmap scope, not an automatic execution order. Issue #56 records the current planning decision to implement the bounded basic BET / gas-sorption plotting layer next, while quantitative BET fitting remains reserved for v0.4.

## v0.4.x — Advanced experimental analysis

- XPS processing and constrained peak fitting.
- EIS plotting and basic equivalent-circuit fitting.
- BET quantitative fitting.
- Product quantification from calibration data and GC/HPLC/NMR-derived values.

## v0.5.x — XAS and structures

- XANES import, normalization, and comparison.
- FT-EXAFS and WT-EXAFS visualization.
- EXAFS fitting-result summaries.
- POSCAR / CONTCAR / CIF / XYZ import.
- Bond lengths, angles, coordination, and structure comparison.
- Basic atomic-structure visualization, informed by dedicated open-source structure-visualization projects such as `pretty-lattice` while keeping structure analysis and rendering separated.
- DFT energetics and adsorption-energy analysis.

## v0.6.x — Electronic structure and catalysis thermodynamics

- CHE and free-energy analysis.
- Free-energy diagrams.
- DOS / PDOS processing and band-center analysis.
- Bader charge analysis.
- COHP / ICOHP analysis.
- Geometry–bonding correlations.
- Charge-density-difference calculation with lattice/grid validation.

## v0.7.x — Advanced computational visualization

- Charge-density-difference isosurfaces and slices.
- ELF / charge-density visualization.
- Band-structure plotting.
- Work-function processing.
- NEB / barrier plots.

## v0.8.x — Operando and time-resolved data

- Operando Raman / IR stacks, waterfalls, and heatmaps.
- Operando XAS mapping.
- Operando XRD mapping.
- Peak area / position / FWHM versus potential or time.
- Cross-modal correlation analysis.

## v0.9.x — Reproducible and interactive workflows

- Batch processing.
- Publication figure presets.
- Reusable analysis recipes.
- Scientific QA checks.
- Processing metadata and reproducibility records.
- First interactive plot editor prototype using the existing `FigureSpec` model for immediate redraw when style/layout parameters change.

## v1.0.0 — Personal catalysis data workbench

- Stable Python API.
- Project workspace for processed experimental, characterization, and computational data.
- Local GUI with file import, parameter controls, real-time figure preview, style-template selection, per-parameter override, and export.
- Real-time controls should include font size, line width/style, marker symbol/size, axis dimensions/aspect ratio, margins, ticks, legends, limits and related publication parameters without changing the scientific analysis pipeline.

## Explicitly out of scope

- Synthesis management and electronic laboratory notebooks.
- TEM/SEM image processing and STEM atom recognition.
- Instrument control.
- Full Rietveld refinement engine.
- Full Artemis-class EXAFS fitting engine.
- HPC job submission or complete VASP workflow management.
