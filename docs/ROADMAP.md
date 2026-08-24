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
- RRDE / Koutecký–Levich basics.
- Installed-wheel public-API and representative numerical smoke coverage for the reviewed v0.2 electrochemistry surface.

## v0.3.0 — Extended experimental processing — released 2026-08-24

- FTIR / ATR-FTIR — implemented and merged through Issue #50 / PR #51.
- TGA / DTG / TPR / TPD — implemented and merged through Issue #54 / PR #55.
- Basic BET / gas-sorption plotting — implemented and merged through Issue #58 / PR #59; quantitative BET fitting remains v0.4.
- ICP/composition data integration — implemented and merged through Issue #62 / PR #63.
- Gate A / Issue #66 / PR #67 completed frozen-scope release hardening while retaining version `0.2.0`.
- Gate B / Issue #68 / PR #69 finalized and exact-wheel validated distribution/runtime version `0.3.0`.
- Gate C / Issue #70 created and reverse-verified tag `v0.3.0` on release commit `845ac4c15d399a8816c7ba66d61ea6ec4cc11293`.
- Package-registry publication was not part of the Git release and remains a separate policy decision.

Shared peak-fitting was deliberately deferred from v0.3 to v0.4. Its model families, baseline coupling, parameter constraints/ties, uncertainty/covariance semantics, and provenance are now being designed with concrete constrained XPS/spectroscopy consumers rather than as a speculative standalone abstraction.

## v0.4.x — Advanced experimental analysis — architecture active

The architecture-first dependency order is defined in [`V0_4_PLAN.md`](V0_4_PLAN.md). The first block deliberately separates generic fitting mechanics from XPS-specific scientific semantics.

1. Shared constrained peak-fitting foundation and mature nonlinear-fit backend integration.
   - stable parameter/component keys;
   - explicit initial/fixed/bounded/tied parameters;
   - bounded initial spectroscopy line-shape set;
   - deterministic fit provenance, residuals, fit statistics and uncertainty/covariance state;
   - no automatic peak detection, component-count selection, smoothing, normalization or baseline choice.
2. XPS data semantics and preparation.
   - explicit binding-energy/eV semantics;
   - explicit energy calibration/reference correction;
   - explicit fit regions;
   - XPS-specific linear/Shirley background preparation with Tougaard deferred unless separately contracted.
3. Constrained XPS peak fitting.
   - shared-fitter consumer;
   - caller-supplied doublet separation/ratio/width constraints;
   - no hidden chemistry assignment or literature lookup.
4. XPS publication plotting and fit diagnostics through the shared `FigureSpec` model.
5. EIS plotting and basic equivalent-circuit fitting.
6. BET quantitative fitting with explicit region-selection/Rouquerol contracts.
7. Product quantification from calibration data and GC/HPLC/NMR-derived values.

Architecture Issue #73 introduces no scientific implementation, dependency, version change, tag or package publication. Ordinary v0.4 development continues from runtime/distribution version `0.3.0` until a later reviewed release gate explicitly changes it.

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