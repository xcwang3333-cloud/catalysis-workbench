# CatalysisWorkbench Roadmap

CatalysisWorkbench is developed in staged releases. The project focuses on quantitative post-processing, comparative analysis, and publication-quality visualization of catalysis data.

Before implementing each major scientific or visualization module, comparable open-source projects should be surveyed and useful algorithms, data-model ideas, visualization patterns, tests, and license constraints recorded in project documentation.

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

## v0.4.x — Advanced experimental analysis — scientific implementation complete

The architecture-first dependency order is maintained in [`V0_4_PLAN.md`](V0_4_PLAN.md). The scientific scope below is merged to `main`; v0.4 has **not** yet entered its separately authorized release-hardening/version/tag gates.

1. **Shared constrained peak-fitting foundation — complete through Issue #75 / PR #76.**
   - `lmfit>=1.3.4` reviewed as the BSD-3-Clause runtime fitting backend;
   - stable parameter/component keys and explicit initial/fixed/bounded/tied parameters;
   - Gaussian, Lorentzian, Voigt, pseudo-Voigt, and Doniach initial model families;
   - deterministic fit provenance, physical residuals, fit statistics and optional uncertainty/covariance state;
   - exact-head CI #255 and two formal reviews passed before merge `b6f428d96df9950373c17e5de487ac4113a2aacc`.
2. **XPS data semantics and preparation — complete through Issue #79 / PR #80.**
   - explicit binding-energy/eV semantics and additive energy correction;
   - measured-point-only region preparation, linear background, independently implemented Shirley background;
   - exact-head CI #261 and two formal reviews passed before merge `a13dbd541b299f79d83e47f079c4638b082a8061`.
3. **Constrained XPS peak fitting — complete through Issue #83 / PR #84.**
   - shared-fitter consumer with explicit signed doublet separation and caller-supplied amplitude/shape relations;
   - fail-closed prepared-background alignment and no hidden textbook ratios or chemistry lookup;
   - exact-head CI #267 and two formal reviews passed before merge `7897393e1e1e9e4d23fad774b4eeecdd70e2a90b`.
4. **XPS publication plotting and fit diagnostics — complete through Issue #87 / PR #88.**
   - passive retained-array rendering through `FigureSpec`, optional physical residual panel, display-only binding-energy direction;
   - exact-head CI #274 / run `32741710370` and final-head reviews passed before merge `3eab8c8e936cf1897081b7a396306288e517a3bb`.
5. **EIS semantics, basic equivalent-circuit fitting, and plotting — complete through Issue #91 / PR #92.**
   - explicit frequency/Hz and literal complex-impedance/ohm semantics;
   - ideal R/C/CPE elements with explicit series/parallel topology;
   - SciPy real+imag least-squares objective with retained physical complex residual;
   - passive Nyquist/Bode plotting and fail-closed result reconstruction;
   - final exact-head CI #285 / run `32746265252`, reviews `5009748594` and `5009757335`, merge `cd8dd171a16576067934a13ad3ac41d0fb18d55a`.
6. **Quantitative BET fitting — complete through Issue #95 / PR #96.**
   - caller-visible measured `SorptionWindow`, exact BET transform and independent Rouquerol consistency state;
   - explicit loading-to-mol/g conversion and molecular cross-sectional area;
   - fail-closed preprocessing allowlist and passive retained-array BET plotting;
   - final exact-head CI #294 / run `32752441329`, reviews `5010325152` and `5010328048`, merge `c76a49d64e096d6db001c27c598356baa797f3a9`.
7. **Product calibration / GC-HPLC-NMR-derived quantification — complete through Issue #99 / PR #100.**
   - new technique-agnostic `catalysis_workbench.experimental.product` layer upstream of electrochemical FE;
   - explicit linear calibration with caller-selected free or fixed-zero intercept policy and optional measured-point `CalibrationRange`;
   - retained calibration points, coefficients, physical residuals, R²/uncertainty availability and fail-closed result reconstruction;
   - separate inverse quantification with exact response-unit matching, default extrapolation rejection, explicit ordered positive dimensionless factors and no hidden unit/stoichiometric conversion;
   - explicit replicate mean/sample-SD/RSD summaries and passive `FigureSpec` calibration plotting;
   - raw GC/HPLC/NMR parsing, peak integration/assignment, internal-standard identification and automatic response-factor/model/range inference remain out of scope;
   - final exact head `967d495bba8c8f0102b8b37a6f880f566d776206`, CI #298 / run `32755942830`, reviews `5010636300` and `5010639945`, squash merge `adc0f50178d899b4f257842da6e7bac553a25254`.

All planned v0.4 scientific blocks are therefore complete on `main`. Runtime/distribution version remains `0.3.0`. The next boundary is **v0.4 release hardening / Gate A**, which requires separate explicit authorization. Scientific completion alone does not authorize a version bump, `v0.4.0` tag, GitHub Release, or package-registry publication.

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