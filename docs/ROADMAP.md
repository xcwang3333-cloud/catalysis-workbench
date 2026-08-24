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
- Basic BET / gas-sorption plotting — implemented and merged through Issue #58 / PR #59; quantitative BET fitting was intentionally deferred to v0.4 and is now implemented there.
- ICP/composition data integration — implemented and merged through Issue #62 / PR #63.
- Gate A / Issue #66 / PR #67 completed frozen-scope release hardening while retaining version `0.2.0`.
- Gate B / Issue #68 / PR #69 finalized and exact-wheel validated distribution/runtime version `0.3.0`.
- Gate C / Issue #70 created and reverse-verified tag `v0.3.0` on release commit `845ac4c15d399a8816c7ba66d61ea6ec4cc11293`.
- Package-registry publication was not part of the Git release and remains a separate policy decision.

Shared peak fitting was deliberately deferred from v0.3 so its constraints, uncertainty semantics, provenance, and concrete XPS consumer could be designed together in v0.4.

## v0.4.x — Advanced experimental analysis — implementation active

The architecture-first dependency order is maintained in [`V0_4_PLAN.md`](V0_4_PLAN.md).

1. **Shared constrained peak-fitting foundation — complete through Issue #75 / PR #76.**
   - `lmfit>=1.3.4` reviewed as the BSD-3-Clause runtime fitting backend;
   - stable parameter/component keys;
   - explicit initial/fixed/bounded/tied parameters;
   - Gaussian, Lorentzian, Voigt, pseudo-Voigt, and Doniach initial model families;
   - deterministic fit provenance, physical residuals, fit statistics, and optional uncertainty/covariance state;
   - explicit caller background and fit window;
   - no automatic peak detection, component-count selection, smoothing, normalization, or baseline choice;
   - exact-head CI #255 and two formal reviews passed before merge commit `b6f428d96df9950373c17e5de487ac4113a2aacc`.
2. **XPS data semantics and preparation — complete through Issue #79 / PR #80.**
   - explicit binding-energy/eV semantics;
   - explicit additive energy calibration/reference correction with provenance;
   - measured-point-only region preparation with source-order preservation;
   - direction-safe linear background;
   - independently implemented Shirley fixed-point integral background with explicit convergence/failure state;
   - Tougaard remains deferred unless separately contracted;
   - exact-head CI #261 and two formal reviews passed before merge commit `a13dbd541b299f79d83e47f079c4638b082a8061`.
3. **Constrained XPS peak fitting — complete through Issue #83 / PR #84.**
   - thin shared-fitter consumer with no second optimizer;
   - explicit signed doublet separation, amplitude ratio and model-specific shape/width relations;
   - prepared XPS background accepted only on the exact matching source/grid/unit/direction state;
   - no hidden p/d/f ratios, chemistry assignment, charge correction or literature lookup;
   - exact-head CI #267 and two formal reviews passed before merge commit `7897393e1e1e9e4d23fad774b4eeecdd70e2a90b`.
4. **XPS publication plotting and fit diagnostics — complete through Issue #87 / PR #88.**
   - passive lazy adapter over retained `XPSPeakFitResult` arrays and the shared `FigureSpec` / visualization stack;
   - measured spectrum, retained background, stable-key component curves, total fit and optional physical residual diagnostics;
   - binding-energy direction is a rendering-only choice and does not reorder/mutate numerical results;
   - `XPSFitDiagnostics` mirrors already-computed statistics and uncertainty availability without fabrication;
   - no fitting, background calculation, energy correction, smoothing, normalization, resampling or chemistry assignment during plotting;
   - exact-head CI #274 / run `32741710370` and final-head reviews passed before merge commit `3eab8c8e936cf1897081b7a396306288e517a3bb`.
5. **EIS semantics, basic equivalent-circuit fitting, and plotting — complete through Issue #91 / PR #92.**
   - explicit frequency/Hz and literal complex-impedance/ohm semantics with source-order preservation;
   - ideal R/C/CPE leaves plus explicit series/parallel topology and stable `element.parameter` identities;
   - caller-visible initial values, fixed/vary state, bounds and explicit residual weights;
   - SciPy real+imag least-squares objective while the public complex residual remains exactly `observed - best_fit`;
   - fail-closed immutable result reconstruction tying units/direction/circuit/parameters/best-fit/residual/weights/objective state together;
   - passive Nyquist raw/`-Im(Z)` and principal-phase Bode plotting through the existing `FigureSpec` stack;
   - no automatic topology/model selection, unit/sign/order correction, hidden weighting or initial-guess heuristic;
   - final exact-head CI #285 / run `32746265252` and reviews `5009748594`, `5009757335` passed before merge commit `cd8dd171a16576067934a13ad3ac41d0fb18d55a`.
6. **Quantitative BET fitting — complete through Issue #95 / PR #96.**
   - explicit adsorption-branch and relative-pressure-fraction compatibility on the reviewed measured-isotherm foundation;
   - caller-visible measured-point `SorptionWindow` candidate region with source order retained and no synthesized endpoints;
   - exact BET transform and OLS diagnostics plus independent positive-parameter, Rouquerol-transform monotonicity, and monolayer-loading-inside-region checks;
   - accepted fits retain slope/intercept, `R²`, BET constant, monolayer loading, monolayer pressure, explicit loading-to-mol/g conversion and specific surface area;
   - explicit adsorbate cross-sectional area, molar-mass/STP conversion inputs and no hidden adsorbate lookup;
   - preprocessing is fail-closed: only reviewed sorption preparation, measured-point crop and explicit relative-pressure conversion provenance are accepted; unknown or y/grid-altering processing is rejected;
   - passive retained-array BET plotting uses the existing `FigureSpec` stack and performs no refitting or region search;
   - final exact-head CI #294 / run `32752441329` succeeded on `47aee74a5a6b16dbf60bb95c2910ccd197205f2f`; final-head reviews `5010325152` and `5010328048` passed before squash merge `c76a49d64e096d6db001c27c598356baa797f3a9`.
7. **Product calibration / GC-HPLC-NMR-derived quantification — active next stage.**
   - separate calibration-standard fitting from sample quantification;
   - keep response and amount units, calibration model form, fit range, intercept policy, dilution/injection/sample-volume factors, replicate handling and uncertainty state caller-visible;
   - retain raw calibration points, exact fit/model state and deterministic provenance;
   - fail explicitly on incompatible units, insufficient calibration state or unsupported transformations;
   - do not infer product identity, detector/internal-standard response factors, dilution, stoichiometry, or Faradaic-efficiency inputs from labels;
   - perform a fresh prior-art/license review and freeze the scientific/API contract before implementation.

Ordinary v0.4 development continues with runtime/distribution version `0.3.0` until a later reviewed release gate explicitly changes it. No v0.4 tag, GitHub Release, or package-registry publication is implied by feature development.

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