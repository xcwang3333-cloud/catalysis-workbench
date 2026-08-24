# CatalysisWorkbench v0.4 Plan

v0.4 is the advanced-experimental-analysis release. It builds on the released `v0.3.0` tag at `845ac4c15d399a8816c7ba66d61ea6ec4cc11293`; that tag remains immutable. Ordinary v0.4 feature work keeps distribution/runtime version `0.3.0` until a later explicit release gate.

GitHub remains the operational source of truth. This document records the reviewed dependency order and scientific/API boundaries; it does not replace exact-head CI, review, or merge evidence.

## Current checkpoint

Checkpoint date: 2026-08-24.

- v0.4 architecture checkpoint: Issue #73 / PR #74 — complete at `a7fb245bd39f8aa3dc18141c2ecf6f005f02ebd1`.
- shared constrained peak-fitting foundation: Issue #75 / PR #76 — complete at `b6f428d96df9950373c17e5de487ac4113a2aacc`.
- shared-fitting exact-head CI: run #255 / `32733891934` — success.
- shared-fitting formal review ids: `5008457897`, `5008470806`.
- XPS semantics, explicit energy correction, measured-point region preparation, and linear/Shirley background: Issue #79 / PR #80 — complete.
- XPS preparation merge commit / current scientific baseline: `a13dbd541b299f79d83e47f079c4638b082a8061`.
- XPS exact-head CI: run #261 / `32736488212` — success.
- XPS formal review ids: `5008700786`, `5008706395`.
- reviewed runtime dependency: `lmfit>=1.3.4` (BSD-3-Clause upstream).
- project version remains `0.3.0`.
- no v0.4 tag, GitHub Release, or package-registry publication has been authorized or performed.
- active scientific stage after the docs checkpoint: **constrained XPS components/doublets and shared-fit integration**.

## v0.4 dependency order

1. **Shared constrained peak-fitting foundation — complete (#75 / #76).**
2. **XPS semantics, energy correction, and background preparation — complete (#79 / #80).**
3. **Constrained XPS components/doublets and shared-fit integration — active next stage.**
4. XPS publication plotting and fit diagnostics/summary.
5. EIS plotting and basic equivalent-circuit fitting.
6. Quantitative BET fitting.
7. Product calibration and GC/HPLC/NMR-derived quantification.
8. Completion-state synchronization and later release-hardening/version gates.

Later consumers may refine an Issue boundary, but they must not force hidden scientific assumptions into the shared fitting foundation.

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

### Explicit non-goals retained after stage B

The XPS preparation layer does not automatically:

- detect peaks or choose component count;
- fit peak components;
- create spin-orbit doublets;
- look up literature binding energies, splittings, or branching ratios;
- assign oxidation states/species;
- apply charge correction from chemical labels;
- smooth or normalize intensity;
- choose a background family;
- run global/sequential multi-spectrum analysis;
- render publication figures.

## XPS stage C — constrained fitting boundary

The active next scientific stage consumes both completed layers: prepared XPS state from stage B and the generic shared fitter from stage A.

### Domain adapter responsibility

The XPS layer may provide value-oriented component/doublet specifications that translate into `PeakComponentSpec` / `PeakFitSpec`, but it must not expose mutable backend `lmfit` state as the scientific API.

A constrained XPS fitting request must:

- accept a validated/prepared XPS region;
- consume either explicit zero background or an `XPSBackgroundResult` aligned exactly to that region;
- verify background/source grid alignment and source numerical identity before fitting;
- translate XPS domain constraints into the existing public `{component.parameter}` tie syntax;
- call the shared `fit_peaks()` path rather than implementing a second optimizer;
- retain enough XPS preparation + shared-fit provenance to audit the complete analysis chain.

### Spin-orbit doublets

- doublets are represented as linked shared-fitting components;
- separation is caller supplied in eV;
- amplitude/area ratio is caller supplied;
- width tie policy is caller supplied and explicit;
- no element/orbital label silently selects textbook separation, branching ratio, peak shape, or width rule;
- component/assignment labels are descriptive metadata, not evidence that a chemical state has been proven.

### Stage-C non-goals

- no automatic peak detection or component count;
- no literature lookup of binding energies/splittings/ratios;
- no automatic charge correction;
- no hidden background recomputation/selection;
- no smoothing/normalization;
- no oxidation-state/species inference;
- no publication plotting yet;
- no global/sequential multi-spectrum fitting unless separately contracted.

## Visualization boundary

XPS plotting remains a later lazy adapter over the existing `FigureSpec`/shared visualization system. Rendering may show measured spectrum, explicit background, component curves, total fit, and residual diagnostics, but it must not perform fitting, background calculation, energy correction, smoothing, normalization, or assignment.

## Prior-art / license decisions

The architecture record remains in [`REFERENCES.md`](REFERENCES.md). Key decisions relevant to the next stages are:

- `lmfit/lmfit-py` — BSD-3-Clause; implemented runtime backend for shared fitting;
- `derb12/pybaselines` — BSD-3-Clause; potential general-spectroscopy baseline adapter, not assumed to supply XPS Shirley/Tougaard semantics;
- `jacobdben/XPyS` — MIT; XPS scientific/workflow reference only;
- `JulioAzcarate/pyFitXPS` — non-standard/NOASSERTION repository license metadata; reference only;
- `Julian-Hochhaus/lmfitxps` — Shirley implementation has mixed/GPL provenance recorded in its LICENSE; reference only for that implementation;
- `Julian-Hochhaus/LG4X-V2` — mixed provenance including GPL-derived portions despite top-level MIT text; workflow/UX reference only.

No XPS implementation code is copied from reference-only projects.

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
