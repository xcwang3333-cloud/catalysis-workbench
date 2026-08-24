# CatalysisWorkbench v0.4 Plan

v0.4 is the advanced-experimental-analysis release. It builds on the released `v0.3.0` tag at `845ac4c15d399a8816c7ba66d61ea6ec4cc11293`; that tag remains immutable. Ordinary v0.4 feature work keeps distribution/runtime version `0.3.0` until a later explicit release gate.

GitHub remains the operational source of truth. This document records the reviewed dependency order and scientific/API boundaries; it does not replace exact-head CI, review, or merge evidence.

## Current checkpoint

Checkpoint date: 2026-08-24.

- v0.4 architecture checkpoint: Issue #73 / PR #74 — complete at `a7fb245bd39f8aa3dc18141c2ecf6f005f02ebd1`.
- shared constrained peak-fitting foundation: Issue #75 / PR #76 — complete at `b6f428d96df9950373c17e5de487ac4113a2aacc`.
- shared-fitting exact-head CI: run #255 / `32733891934` — success.
- shared-fitting formal review ids: `5008457897`, `5008470806`.
- XPS semantics, explicit energy correction, measured-point region preparation, and linear/Shirley background: Issue #79 / PR #80 — complete at `a13dbd541b299f79d83e47f079c4638b082a8061`.
- XPS preparation exact-head CI: run #261 / `32736488212` — success.
- XPS preparation formal review ids: `5008700786`, `5008706395`.
- constrained XPS components/doublets and shared-fit integration: Issue #83 / PR #84 — complete at `7897393e1e1e9e4d23fad774b4eeecdd70e2a90b`.
- constrained-XPS final exact-head CI: run #267 / `32739584536` — success on `02d2800ec6e87cb41dca041d2734cc09c5da9235`.
- constrained-XPS formal review ids: `5009021201`, `5009026855`.
- XPS publication plotting and fit diagnostics: Issue #87 / PR #88 — complete at `3eab8c8e936cf1897081b7a396306288e517a3bb`.
- XPS plotting final exact-head CI: run #274 / `32741710370` — success on `15288b21be118a450614445d6bbf82d80d459271`.
- XPS plotting final-head review records: `5009266827`, `5009270492` (COMMENT because GitHub rejects self-APPROVE).
- EIS semantics, R/C/CPE circuit fitting, Nyquist/Bode plotting and diagnostics: Issue #91 / PR #92 — complete at `cd8dd171a16576067934a13ad3ac41d0fb18d55a`.
- EIS final exact-head CI: run #285 / `32746265252` — success on `18d81a0029cc851c136420fc550ec3e823094862`.
- EIS final-head review records: `5009748594`, `5009757335` (COMMENT because GitHub rejects self-APPROVE).
- EIS reference/license boundary is recorded in `REFERENCES.md`: `ECSHackWeek/impedance.py` (MIT) and `vyrjana/pyimpspec` (GPL-3.0) are reference-only and neither is a dependency.
- quantitative BET fitting and Rouquerol consistency checks: Issue #95 / PR #96 — complete at `c76a49d64e096d6db001c27c598356baa797f3a9`.
- BET final exact-head CI: run #294 / `32752441329` — success on `47aee74a5a6b16dbf60bb95c2910ccd197205f2f`.
- BET final-head review records: `5010325152`, `5010328048`.
- BET prior-art/license boundary is recorded in `REFERENCES.md`: pyGAPS, BETSI, SESAMI_web, and BEaTmap are current MIT reference-only projects; no implementation was copied and no new dependency was added.
- reviewed runtime dependency: `lmfit>=1.3.4` (BSD-3-Clause upstream).
- project version remains `0.3.0`.
- `v0.3.0` remains fixed on `845ac4c15d399a8816c7ba66d61ea6ec4cc11293`.
- no v0.4 tag, GitHub Release, or package-registry publication has been authorized or performed.
- active scientific stage after the post-BET docs checkpoint: **product calibration / GC-HPLC-NMR-derived quantification**.

## v0.4 dependency order

1. **Shared constrained peak-fitting foundation — complete (#75 / #76).**
2. **XPS semantics, energy correction, and background preparation — complete (#79 / #80).**
3. **Constrained XPS components/doublets and shared-fit integration — complete (#83 / #84).**
4. **XPS publication plotting and fit diagnostics/summary — complete (#87 / #88).**
5. **EIS semantics, Nyquist/Bode plotting and basic equivalent-circuit fitting — complete (#91 / #92).**
6. **Quantitative BET fitting — complete (#95 / #96).**
7. **Product calibration and GC/HPLC/NMR-derived quantification — active next stage.**
8. Completion-state synchronization and later release-hardening/version gates.

Later consumers may refine an Issue boundary, but they must not force hidden scientific assumptions into shared numerical infrastructure.

## Completed shared fitting foundation

Issue #75 introduced a technique-agnostic fitting layer under `catalysis_workbench.processing` backed by mature `lmfit` optimization/model primitives.

### Public contracts

The reviewed public surface includes value-oriented, immutable scientific state equivalent to:

- `FitParameterSpec` — initial value, vary/fixed state, optional finite bounds, optional explicit expression/tie;
- `PeakComponentSpec` — stable component key, explicit model family, explicit parameter mapping, optional display metadata;
- `PeakFitSpec` — explicit fit window, ordered components, explicit caller background/zero background, optional residual-multiplier weights, reviewed fit method;
- `FittedParameter` and `PeakFitResult` — backend-independent fitted state, component curves, total fit, physical residual, statistics, optional stderr/covariance/correlations, source semantics, and deterministic numerical provenance;
- `fit_peaks()` and `PeakFittingError`.

Mutable `lmfit.Parameter`, `Parameters`, `Model`, and `ModelResult` objects are not the durable CatalysisWorkbench public data model.

### Initial reviewed line-shape set

- Gaussian;
- Lorentzian;
- Voigt;
- pseudo-Voigt;
- Doniach-style asymmetric model supplied by lmfit.

Model-specific input parameters are explicit. CatalysisWorkbench validates caller state against backend model domains before optimization so lmfit cannot silently clip an invalid initial value. Additional line shapes require a concrete consumer and regression tests.

### Fitting invariants

- component identity uses stable non-display keys;
- public cross-component ties use `{component.parameter}` references;
- fit regions are caller supplied and direction-independent numerically;
- strictly monotonic ascending or descending source order is preserved;
- no hidden sorting, interpolation, smoothing, normalization, baseline estimation, peak detection, component-count selection, or chemistry assignment occurs;
- background is explicit zero or a caller-prepared source-aligned array;
- public residual is `observed - (background + modeled peaks)` even when residual-multiplier weights are used for the objective;
- fixed/constrained-only requests are evaluated without inventing covariance or standard errors;
- unavailable uncertainty remains unavailable rather than being represented as zero;
- numerical results retain deterministic source-data identity and immutable arrays;
- existing v0.1-v0.3 characterization imports retain their reviewed lazy plotting behavior; the lmfit-backed fitting surface is not eagerly imported for unrelated processing consumers.

Full behavior is documented in [`PEAK_FITTING.md`](PEAK_FITTING.md).

## Completed XPS stage B — semantics and preparation

Issue #79 / PR #80 established the XPS-specific scientific state required before constrained peak optimization. Full behavior is documented in [`XPS.md`](XPS.md).

### Binding-energy semantics

- canonical x semantic is `binding_energy` with explicit eV unit;
- x must be finite and strictly monotonic; ascending and descending storage are both valid;
- source storage order is preserved;
- duplicate/non-finite energy values fail explicitly;
- no automatic sorting or interpolation occurs.

### Energy-reference correction

- correction is a separate explicit transformation;
- caller supplies a finite additive shift in eV;
- corrected energy is `E_corrected = E_source + shift_ev`;
- intensity is unchanged exactly;
- reference/rationale and deterministic processing provenance are retained;
- a second library-applied energy correction is rejected rather than silently accumulated;
- no element/orbital name or expected literature position triggers automatic charge correction.

### Measured-point region preparation

- caller supplies numerical low/high binding-energy bounds;
- selection is inclusive of measured points only;
- no boundary interpolation or endpoint synthesis occurs;
- source direction and deterministic processing history are preserved;
- insufficient or missing selected data fail explicitly.

### Linear and Shirley backgrounds

- linear background is the deterministic line through measured numerical low/high-energy endpoint intensities;
- Shirley background is independently implemented from the explicit fixed-point integral equation rather than copied from reference repositories;
- Shirley uses a measured-grid trapezoidal integration view, linear endpoint initialization, explicit positive relative/absolute tolerances, explicit maximum iterations, exact endpoint enforcement, and explicit failure on invalid integrated signal or non-convergence;
- the internal increasing-energy integration orientation never changes public source storage order;
- background output is retained in immutable `XPSBackgroundResult` state with source digest, grid, measured y, background y, endpoint semantics, direction, method, settings, and convergence metadata;
- Tougaard remains deferred until a dedicated Issue contracts its equation, parameters, numerical method, and validation evidence.

### License boundary

- `jacobdben/XPyS` (MIT) and `JulioAzcarate/pyFitXPS` (non-standard/NOASSERTION metadata) were used only as workflow/architecture references;
- `Julian-Hochhaus/lmfitxps` has top-level MIT text, but its LICENSE records GPL-3.0-derived inspiration for its Shirley implementation; that Shirley implementation is reference-only and was not copied/adapted;
- CatalysisWorkbench's Shirley implementation is project-owned from the explicit documented equation and regression-tested independently.

## Completed XPS stage C — constrained fitting integration

Issue #83 / PR #84 added the XPS domain consumer of the reviewed shared fitter without introducing a second optimizer or hidden chemistry defaults.

### Domain adapter responsibility

The reviewed stage-C public state includes:

- `XPSDoubletSpec` — a value-oriented primary/secondary linkage that generates two stable shared `PeakComponentSpec` objects;
- `XPSProcessingStep` — deterministic retained XPS preparation-history state;
- `XPSPeakFitResult` — composition of XPS source/preparation/background/doublet provenance with the backend-independent shared `PeakFitResult`;
- `fit_xps_peaks()` — the XPS-level fit entry point delegating optimization to shared `fit_peaks()`.

No mutable `lmfit.ModelResult` becomes XPS public state.

### Explicit doublet physics

- separation is caller supplied and signed: `secondary.center = primary.center + separation_ev`;
- amplitude ratio is caller supplied and strictly positive;
- every remaining model-specific shape/width parameter relation is caller supplied explicitly through positive ratios;
- Gaussian/Lorentzian sigma relations therefore have no hidden equality default;
- Voigt gamma, pseudo-Voigt fraction, and Doniach gamma relations must also be present explicitly when required by the shared model family;
- generated ties use the reviewed public `{component.parameter}` expression syntax rather than backend names;
- duplicate/colliding stable keys fail before optimization;
- zero separation is rejected in the reviewed first implementation as a degenerate doublet definition;
- component labels/assignment text are descriptive metadata and do not alter fitting mathematics;
- no p/d/f textbook branching ratio or literature splitting is hard-coded.

### Prepared-background fail-closed alignment

When an `XPSBackgroundResult` is used, stage C verifies before fitting:

- source key;
- deterministic source numerical SHA-256;
- binding-energy unit (`eV`);
- intensity unit;
- declared source direction;
- exact x grid values and order;
- exact observed-y values;
- background length and finiteness;
- that the explicit fit window includes the exact prepared background region.

A background from another shifted spectrum, different region, relabeled intensity basis, opposite direction declaration, reordered grid, or modified intensity cannot be silently cropped/interpolated/reversed into compatibility.

### Fit/result behavior

- XPS semantic validation runs before fitting;
- explicit single shared components and/or explicit XPS doublets may be supplied;
- optional residual-multiplier weights retain the existing shared semantics;
- optimization always delegates to `fit_peaks()`;
- source storage direction is preserved;
- XPS preparation history, background method/state, doublet recipe, source digest/direction, component identities and shared fit outputs remain auditable;
- importing the numerical XPS-fitting module remains Matplotlib-lazy until shared fitting is actually invoked.

### Stage-C validation evidence

- final exact PR head: `02d2800ec6e87cb41dca041d2734cc09c5da9235`;
- CI #267 / run `32739584536` — success;
- installed-wheel constrained-XPS smoke — success;
- existing shared-fitting, XPS-preparation, v0.1-v0.3 regression/smoke/quickstart paths — success;
- formal final-head review ids: `5009021201`, `5009026855`;
- expected-head squash merge commit: `7897393e1e1e9e4d23fad774b4eeecdd70e2a90b`.

## Completed XPS stage D — publication plotting and diagnostics

Issue #87 / PR #88 added a scientifically passive XPS publication-rendering and diagnostic layer over the reviewed `XPSPeakFitResult` state.

### Rendering scope

The reviewed adapter renders directly from retained shared-fit arrays:

- measured XPS spectrum;
- explicit retained background;
- stable-key component curves;
- total best-fit curve;
- optional physical residual diagnostics;
- caller-visible labels/legend entries and publication annotations;
- standard exact-size PNG/SVG/PDF export through the existing visualization layer.

### Visualization invariants

- `plot_xps_fit()` does not call fitting, model evaluation, background calculation, energy correction, smoothing, normalization, assignment, or resampling;
- XPS binding-energy direction is a rendering-only x-limit/orientation choice; retained arrays are not reversed or mutated;
- deterministic non-component visual keys are `xps_observed`, `xps_background`, `xps_best_fit`, and `xps_residual`; fitted components retain their actual mathematical component keys;
- reserved-key collisions and unknown XPS style keys fail explicitly;
- existing `FigureSpec` typography, line/marker, axes-geometry, legend, limit, annotation and export controls remain the style contract rather than an XPS-specific parallel style system;
- optional residual presentation uses the already reviewed physical residual `observed - best_fit`, not an optimizer-weighted objective residual;
- the residual panel uses caller-visible height/gap geometry and shares the main x span/orientation;
- the root characterization import remains Matplotlib-lazy; plotting is dispatched only when called.

### Fit diagnostics

`XPSFitDiagnostics` / `summarize_xps_fit()` mirror already-computed shared fit state including success/message/method/backend, background method, source direction, component keys, point/varying-parameter counts, chi-square/reduced chi-square/AIC/BIC, covariance availability, and parameter stderr availability. Missing uncertainty is not fabricated and no chemical interpretation is inferred.

### Stage-D validation evidence

- final exact PR head: `15288b21be118a450614445d6bbf82d80d459271`;
- CI #274 / run `32741710370` — success;
- fresh-wheel `pip check`, installed XPS plotting/diagnostics/export smoke, existing installed smokes and seven quickstarts — success;
- final-head review records: `5009266827`, `5009270492`;
- behind=0, mergeable=true, unresolved review threads=0 before merge;
- expected-head squash merge commit: `3eab8c8e936cf1897081b7a396306288e517a3bb`.

Full XPS behavior is documented in [`XPS.md`](XPS.md).

## Completed EIS stage — explicit impedance semantics, basic circuit fitting, and plotting

Issue #91 / PR #92 delivered the fifth v0.4 scientific block as an explicit impedance-domain analysis layer under `catalysis_workbench.experimental.echem`.

### EIS data and circuit contracts

Reviewed behavior includes:

- canonical `frequency` x semantics in Hz and literal complex `impedance` y semantics in ohm;
- finite, strictly positive, strictly monotonic ascending or descending frequency vectors with source order preserved;
- real-only impedance rejected rather than silently cast into an ambiguous EIS trace;
- ideal resistor, capacitor, and constant-phase element definitions plus explicit series/parallel composition;
- globally unique stable circuit-element keys and stable `<element>.<parameter>` public parameter keys;
- explicit finite initial values, caller bounds, fixed/vary state, and physical domains;
- deterministic circuit evaluation on the exact caller frequency vector;
- no circuit-string DSL, topology inference, automatic model selection, hidden unit conversion, sorting, interpolation, resampling, or initial-guess heuristic.

### EIS fitting/result invariants

- fitting uses `scipy.optimize.least_squares` with the TRF method and a deterministic real+imag residual vector;
- `weights=None` means uniform objective multipliers; explicit weights contain one finite strictly positive multiplier per frequency point and apply equally to real and imaginary objective channels;
- public physical residual remains exact `Z_observed - Z_best_fit`, independent of objective weighting;
- backend-independent immutable `EISFitResult` retains source identity, frequency order, circuit, fitted parameters, weights, exact arrays, optimizer status and objective state;
- fail-closed result reconstruction cross-checks source SHA, canonical units, frequency direction, circuit topology, parameter keys/vary/bounds/physical domains, best-fit circuit evaluation, physical residual, weight state, objective sum-of-squares and varying-parameter count;
- contradictory public result metadata cannot be reconstructed and later consumed as a valid fit;
- `EISFitDiagnostics` / `summarize_eis_fit()` mirror existing result state without fabricating covariance, standard errors or electrochemical interpretation.

### EIS plotting invariants

- `plot_eis_nyquist()` renders exact retained real impedance and a caller-visible `raw` or common `negative` imaginary display choice;
- Nyquist sign selection is rendering-only and never mutates source or fit arrays;
- `plot_eis_bode()` renders exact `|Z|` and principal phase from retained complex impedance with no unwrap/reordering;
- observed/best-fit overlays require exact source key, source digest, frequency grid/order and observed-impedance alignment;
- EIS plotting uses existing `FigureSpec` typography/layout/style/export contracts and stable layer keys rather than adding a parallel plotting framework;
- numerical `experimental.echem` import remains Matplotlib-lazy until a plotting call is made.

### EIS validation and license evidence

- final exact PR head: `18d81a0029cc851c136420fc550ec3e823094862`;
- CI #285 / run `32746265252` — success;
- Ruff, full pytest, fresh-wheel installation, installed EIS fit/plot/export smoke and existing quickstarts — success;
- final-head review records: `5009748594`, `5009757335`;
- behind=0, mergeable=true and unresolved review threads=0 before merge;
- expected-head squash merge commit / reviewed main checkpoint: `cd8dd171a16576067934a13ad3ac41d0fb18d55a`;
- `ECSHackWeek/impedance.py` (MIT) and `vyrjana/pyimpspec` (GPL-3.0) were used as workflow/architecture/validation references only; no implementation code was copied or adapted and neither project is a dependency.

Full EIS behavior is documented in [`EIS.md`](EIS.md), with license decisions retained in [`REFERENCES.md`](REFERENCES.md).

## Completed quantitative BET stage

Issue #95 / PR #96 delivered the sixth v0.4 scientific block as an explicit, fail-closed consumer of the existing measured gas-sorption foundation rather than a second isotherm hierarchy.

### Quantitative BET scientific/API contract

The reviewed implementation includes:

- explicit adsorption branch and relative-pressure fraction (`P/P0`, unit `1`) input semantics;
- one caller-visible `SorptionWindow` candidate region containing measured points only, with ascending or descending source order retained;
- no hidden sorting, interpolation, synthesized boundary points, resampling, smoothing, outlier deletion, or automatic branch inference;
- exact BET transform `p/[n(1-p)]` and OLS on the exact selected arrays;
- retained slope, intercept, correlation/`R²`, `C`, monolayer loading, and monolayer relative pressure;
- three independent required physical checks: positive parameter state, strictly increasing `n(1-p)` with increasing pressure, and fitted monolayer loading strictly inside the selected measured loading span;
- `evaluate_bet_region()` for auditable candidate/criterion state and `fit_bet()` for accepted fits only;
- no hidden `R²` threshold or automatic/unique optimum-region claim;
- explicit loading conversion for `mmol/g`, `mol/kg`, `cm^3(STP)/g`, and caller-molar-mass `mg/g` before area calculation;
- explicit positive molecular cross-sectional area and no adsorbate-name property lookup;
- immutable result state that revalidates transforms, regression, derived parameters, consistency, loading conversion, and surface area;
- fail-closed preprocessing provenance: only reviewed sorption preparation, measured-point crop, and explicit relative-pressure conversion are accepted; unknown or y/grid-altering transformations are rejected;
- lazy `plot_bet_fit()` draws exact retained BET points and retained OLS line through `FigureSpec` without refitting or recalculating criteria.

### Quantitative BET validation and license evidence

- final exact PR head: `47aee74a5a6b16dbf60bb95c2910ccd197205f2f`;
- CI #294 / run `32752441329` — success;
- Ruff, full pytest, fresh-wheel install/`pip check`, installed BET fit/plot/export smoke, existing installed smokes and seven quickstarts — success;
- final-head review records: `5010325152`, `5010328048`;
- behind=0, mergeable=true and unresolved review threads=0 before merge;
- expected-head squash merge / reviewed main checkpoint: `c76a49d64e096d6db001c27c598356baa797f3a9`;
- pyGAPS, BETSI, SESAMI_web, and BEaTmap were directly rechecked as MIT reference-only projects; no implementation code was copied or adapted and no new runtime dependency was added.

Review also hardened two fail-closed boundaries before the final gate: frozen metadata entries are accepted through generic mapping semantics, and the preprocessing guard uses a safe allowlist rather than a future-fragile blacklist.

Full quantitative BET behavior is documented in [`BET.md`](BET.md), with license decisions retained in [`REFERENCES.md`](REFERENCES.md).

## Active product calibration / GC-HPLC-NMR quantification stage

The next scientific Issue must refresh product-calibration and analytical-chemistry prior art/licenses, then freeze an explicit calibration/quantification contract before implementation. This stage should extend the v0.2 FE/product foundation: calibration converts detector response into an explicit quantified amount/concentration state, while FE remains a separate downstream electrochemical calculation.

### Initial product-calibration scope

The first reviewed stage should cover:

- explicit calibration-standard data with response and known amount/concentration units;
- separation of calibration-model fitting from unknown-sample quantification;
- caller-visible calibration model form, selected standard/fit range, intercept policy, and optional weighting;
- retained exact calibration points, model coefficients, fit statistics, units, selected range, source identity and deterministic provenance;
- an immutable calibration result that can be revalidated against its retained points/model state;
- unknown-sample response conversion only through an explicit compatible calibration result;
- caller-visible dilution, injection, aliquot, sample-volume/mass, internal-standard or other multiplicative conversion factors rather than hidden spreadsheet conventions;
- explicit replicate aggregation and uncertainty availability/propagation state, with unavailable uncertainty left unavailable rather than fabricated as zero;
- reusable publication plotting/summary adapters only after numerical quantification state is defined;
- hand-verifiable synthetic/reference regressions and fresh-wheel public-surface smoke.

### Product-calibration scientific guardrails

- no product identity or detector peak assignment inferred from labels;
- no hidden GC/HPLC/NMR response-factor or internal-standard library;
- no automatic dilution, injection-volume, aliquot, density, sample-volume/mass, or stoichiometric correction;
- no automatic model or fit-range choice based solely on maximum `R²`;
- calibration model and sample quantification remain separate from Faradaic-efficiency/electron-stoichiometry calculation;
- incompatible response/amount units, invalid calibration state, extrapolation policy violations, or unsupported transformations fail explicitly;
- raw calibration points and exact transformation provenance remain auditable;
- no vendor-binary parser, automatic product assignment, chromatographic peak integration, or NMR peak deconvolution in the first calibration block unless separately contracted;
- numerical quantification and publication rendering remain separate responsibilities;
- any new dependency requires explicit prior-art/license/packaging review before adoption.

## Later v0.4 stages

After product calibration / GC-HPLC-NMR quantification:

1. completion-state synchronization;
2. later release-hardening/version gates.

## Prior-art / license decisions

The architecture record remains in [`REFERENCES.md`](REFERENCES.md). Key decisions relevant to completed and active v0.4 work are:

- `lmfit/lmfit-py` — BSD-3-Clause; implemented runtime backend for shared peak fitting;
- `derb12/pybaselines` — BSD-3-Clause; potential general-spectroscopy baseline adapter, not assumed to supply XPS Shirley/Tougaard semantics;
- `jacobdben/XPyS` — MIT; XPS scientific/workflow reference only; its code-level p/d doublet ratios are not adopted as hidden defaults;
- `JulioAzcarate/pyFitXPS` — non-standard/NOASSERTION repository license metadata; reference only;
- `Julian-Hochhaus/lmfitxps` — Shirley implementation has mixed/GPL provenance recorded in its LICENSE; reference only for that implementation;
- `Julian-Hochhaus/LG4X-V2` — mixed provenance including GPL-derived portions despite top-level MIT text; workflow/UX reference only;
- `ECSHackWeek/impedance.py` — MIT; EIS workflow/API/test reference only, no dependency or code copy;
- `vyrjana/pyimpspec` — GPL-3.0; EIS architecture/validation reference only, no dependency or code copy/adaptation;
- `pauliacomi/pyGAPS` — MIT; measured-isotherm and quantitative-BET scientific/API reference only;
- `hjkgrp/SESAMI_web` — MIT; quantitative-BET candidate-region workflow reference only;
- `nakulrampal/betsi-gui` — MIT, current `LICENSE.txt` directly verified during Issue #95; exhaustive candidate-region/reproducibility reference only;
- `PMEAL/BEaTmap` — MIT; candidate-criteria/heatmap workflow reference only.

Reference presence does not authorize code reuse. Product calibration must perform a fresh prior-art/license/equation review in its own Issue before implementation.

## Compatibility and version policy

- preserve reviewed v0.1-v0.3 public behavior unless a breaking change is separately planned and reviewed;
- scientific incompatibilities fail explicitly instead of being silently corrected/aligned;
- processing and visualization remain separate responsibilities;
- runtime dependencies are added only when a concrete Issue justifies them and packaging/license review passes;
- `[project].version` and runtime `__version__` remain `0.3.0` during ordinary v0.4 development;
- `v0.3.0` remains fixed on its reviewed release commit;
- tag/GitHub Release/package-registry publication require separate explicit release authorization.

## Required quality loop

Every scientific Issue follows:

```text
prior-art/license refresh
    -> implementation + hand-verifiable regression tests
    -> Draft PR
    -> exact-head CI
    -> scientific/API/compatibility review
    -> direct fixes
    -> fresh exact-head CI after every head change
    -> second formal review on final exact head
    -> behind=0 / mergeable / review threads=0
    -> Ready
    -> expected-head squash merge
    -> verify main
    -> close Issue
```

CI or review evidence from an older PR head is never reused after the head changes.