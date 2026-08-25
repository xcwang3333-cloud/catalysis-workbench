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

## v0.4.0 — Advanced experimental analysis — released 2026-08-25

The architecture-first dependency order is maintained in [`V0_4_PLAN.md`](V0_4_PLAN.md), with release evidence in [`V0_4_RELEASING.md`](V0_4_RELEASING.md). All scientific scope, Gate A release hardening, Gate B final-version validation, Gate C tag verification, post-tag documentation synchronization, and GitHub Release publication are complete. Tag `v0.4.0` resolves exactly to release commit `bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6` and reports distribution/runtime version `0.4.0`. Package-registry/PyPI publication is deferred.

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

Gate A / Issue #103 / PR #104 completed frozen-scope release hardening on exact head `9d79845d6fae253b01a46794c3c055e4966c6e55`, CI #302 / run `32758548117`, reviews `5010905065` and `5010908809`, and squash merge `ce06abc11559fa7679869fc83a59356735ce6824`, while retaining version `0.3.0`.

Gate B / Issue #105 / PR #106 finalized distribution/runtime version `0.4.0`; final head `ae3dc21b1a3a4e907d8c39eb85d3dbebefd8fbb4` passed CI #304 / run `32759679632` and reviews `5011014348`, `5011017132` before squash merge `bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6`. Gate C / Issue #107 then created and reverse-verified `v0.4.0` on that exact commit. The GitHub Release was subsequently published from that existing immutable tag. Package publication remains deferred.

## v0.5.0 — XAS, structures, and basic DFT energetics — released 2026-08-25

The reviewed dependency order and scientific contracts are maintained in [`V0_5_PLAN.md`](V0_5_PLAN.md), with release evidence in [`V0_5_RELEASING.md`](V0_5_RELEASING.md). All eight scientific blocks, completion-state synchronization, Gate A frozen-scope hardening, Gate B final-version exact-wheel validation, Gate C tag verification, GitHub Release publication, and final post-release documentation synchronization are complete. Distribution/runtime version is `0.5.0`. Tag `v0.5.0` resolves exactly to reviewed release commit `9400ac0044ac333d2cae228554c08d955a816a4c`, and the public GitHub Release `CatalysisWorkbench v0.5.0` is published from that existing tag. PyPI/package publication remains deferred.

1. **XAS/XANES — #117 / #118 — complete.**
   - explicit energy/eV semantics, caller-controlled energy shifts, measured-point regions, explicit E0 and pre/post-edge polynomial normalization, positive edge-step validation, retained provenance and passive comparison plotting.
2. **FT-EXAFS — #119 / #120 — complete.**
   - explicit uniform k-grid/transform state, no hidden interpolation, retained complex χ(R), magnitude/real/imaginary/phase views and passive publication plotting.
3. **WT-EXAFS — #121 / #122 — complete.**
   - explicit Cauchy k–R transform, complex WT matrix, retained transform parameters, phase mapping and single-frequency ridge regression evidence.
4. **EXAFS fitting-result summaries — #123 / #124 — complete.**
   - neutral external-fit summary contract preserving path/shell parameters, uncertainty availability and producer-specific diagnostic labels without cross-tool reinterpretation.
5. **Atomic-structure foundation/adapters — #125 / #126 — complete.**
   - immutable CatalysisWorkbench-owned structure state and reviewed POSCAR/CONTCAR/CIF/XYZ adapters using optional `pymatgen-core` support.
6. **Geometry/coordination/comparison — #127 / #129 — complete.**
   - explicit periodic images, exact site distances/angles, caller-bounded cutoff coordination, and explicit site-mapped structure comparison with no hidden MIC/auto-alignment.
7. **Static structure visualization — #130 / #131 — complete.**
   - renderer-neutral immutable `StructureScene`, explicit atom/bond/cell state, presentation-only visual defaults and passive Matplotlib 3D rendering; `pretty-lattice` was architecture/UX reference only.
8. **Basic DFT energetics — #132 / #133 — complete.**
   - immutable explicit eV ledger, same-basis relative energies, generic retained linear combinations, transparent adsorption-energy convention, detached reporting and passive relative-energy plotting.

Release-gate evidence:

- Gate A / #136 / #137: final head `fb13cdbf633366a0840f5f2e21af215bee47b133`, CI #358 / run `32799486710`, reviews `5014277750`, `5014278425`, squash merge `0ffcd7e4a89340d993468039ba83b44bc7638050`, version retained at `0.4.0`.
- Gate B / #138 / #139: final head `b95841ed472aff1fa4d05af7335547ee5c3cd611`, CI #360 / run `32800514038`, reviews `5014348449`, `5014349058`, squash merge `9400ac0044ac333d2cae228554c08d955a816a4c`, distribution/runtime version finalized to `0.5.0`.
- Gate C / #142: tag `v0.5.0` created and reverse-verified exactly on `9400ac0044ac333d2cae228554c08d955a816a4c`; distribution/runtime through the tag is `0.5.0`.
- GitHub Release / #144: `CatalysisWorkbench v0.5.0` publicly published from the existing tag with populated release notes.
- Final post-release documentation synchronization / #143: complete at `bed5c6e750a6066baa8daa21492aa9eb90e8bca8`.

CHE/free-energy thermodynamics, DOS/PDOS, Bader, COHP/ICOHP, charge-density difference and VASP job management remain v0.6+ work.

## v0.6.x — Electronic structure and catalysis thermodynamics

The architecture-first v0.6 scope, scientific semantics, dependency boundaries, prior-art/license decisions, test strategy, and implementation order are frozen in [`V0_6_PLAN.md`](V0_6_PLAN.md). Architecture checkpoint Issue #146 / PR #147 is complete at merge `3803e014376a7edb22d6a9a5b6480541742499be`, and the architecture central-doc synchronization Issue #148 / PR #149 is complete at `aac05d4426c15c8932c608d07ef42e4dc07b09ce`. Scientific block 1 is complete through Issue #150 / PR #151 at merge `58023070bf7f642748b69e99281a5ed7ed4d40df`. Issue #152 is the current docs-only completion-state synchronization before block 2 begins.

Frozen implementation order:

1. **Electronic-structure + volumetric semantics/adapters — complete through #150 / #151.**
   - CatalysisWorkbench-owned immutable energy/DOS/volumetric state, lazy `pymatgen-core` VASP adapters, explicit source-energy/Fermi/spin/projection semantics, and regression-verified CHGCAR `1/angstrom^3` conversion.
2. **DOS / PDOS processing + passive publication plotting — next after #152; not yet implemented.**
3. **Band-center analysis.**
4. **Bader-result parsing + explicit charge accounting.**
5. **COHP / ICOHP parsing + bonding analysis.**
6. **Geometry–bonding correlations.**
7. **CHE / free-energy thermodynamics.**
8. **Free-energy diagrams.**
9. **Charge-density-difference calculation with lattice/grid/component validation.**

The ordering deliberately establishes shared energy-reference, spin, orbital/site projection, normalization, provenance, lattice/grid and volumetric-component semantics before descriptor-specific processing. CHE extends the reviewed v0.5 explicit DFT-energy foundation rather than creating a parallel energy model. PyPI/package-registry publication remains deferred.

## v0.7.x — Advanced computational visualization

- Charge-density-difference isosurfaces and slices.
- ELF / charge-density visualization.
- Band-structure and fat-band / PROCAR plotting.
- Work-function / LOCPOT processing.
- NEB / barrier plots.
- Advanced volumetric rendering.

HPC/VASP job submission and complete workflow management remain outside the current project scope.

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
