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
- reviewed runtime dependency: `lmfit>=1.3.4` (BSD-3-Clause upstream).
- project version remains `0.3.0`.
- no v0.4 tag, GitHub Release, or package-registry publication has been authorized or performed.
- active scientific stage after the docs checkpoint: **XPS publication plotting and fit diagnostics/summary**.

## v0.4 dependency order

1. **Shared constrained peak-fitting foundation — complete (#75 / #76).**
2. **XPS semantics, energy correction, and background preparation — complete (#79 / #80).**
3. **Constrained XPS components/doublets and shared-fit integration — complete (#83 / #84).**
4. **XPS publication plotting and fit diagnostics/summary — active next stage.**
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

## Active XPS stage D — publication plotting and diagnostics

The next scientific Issue may add a lazy XPS publication adapter over the existing `FigureSpec` / shared visualization infrastructure.

### Rendering scope

A reviewed stage-D adapter may render, without recomputation:

- measured XPS spectrum from the exact fit/result grid;
- explicit retained background;
- stable-key component curves;
- total best-fit curve;
- optional physical residual diagnostics;
- caller-visible labels/legend entries and publication annotations;
- standard exact-size PNG/SVG/PDF export through the existing visualization layer.

### Visualization invariants

- XPS binding energy is commonly displayed descending, but any axis inversion must be a rendering choice only; numerical arrays/results are not reordered or mutated;
- plotting must consume already prepared/fitted state and must not call fitting/background/energy-correction functions;
- no smoothing, normalization, baseline/background selection, peak detection, chemistry assignment, or hidden resampling may occur during rendering;
- stable component keys, not display labels, should control per-component styling;
- existing `FigureSpec` typography, line/marker, axes-geometry, legend, limit, annotation and export controls remain the style contract rather than creating an XPS-specific parallel style system;
- residual presentation must use the already reviewed physical residual `observed - best_fit`, not an optimizer-weighted objective residual;
- plotting imports remain lazy for numerical characterization consumers.

Fit diagnostics/summary may expose already-computed shared fit statistics and uncertainty availability, but stage D must not fabricate missing covariance/standard errors or reinterpret chemical state.

## Later v0.4 stages

After XPS plotting/diagnostics:

1. EIS plotting and basic equivalent-circuit fitting;
2. quantitative BET fitting;
3. product calibration / GC-HPLC-NMR quantification;
4. completion-state synchronization and later release gates.

## Prior-art / license decisions

The architecture record remains in [`REFERENCES.md`](REFERENCES.md). Key decisions relevant to current XPS work are:

- `lmfit/lmfit-py` — BSD-3-Clause; implemented runtime backend for shared fitting;
- `derb12/pybaselines` — BSD-3-Clause; potential general-spectroscopy baseline adapter, not assumed to supply XPS Shirley/Tougaard semantics;
- `jacobdben/XPyS` — MIT; XPS scientific/workflow reference only; its code-level p/d doublet ratios are not adopted as hidden defaults;
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
