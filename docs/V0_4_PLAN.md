# CatalysisWorkbench v0.4 Plan

v0.4 is the advanced-experimental-analysis release. It builds on the released `v0.3.0` tag at `845ac4c15d399a8816c7ba66d61ea6ec4cc11293`; that tag remains immutable. Ordinary v0.4 feature work keeps distribution/runtime version `0.3.0` until a later explicit release gate.

GitHub remains the operational source of truth. This document records the reviewed dependency order and scientific/API boundaries; it does not replace exact-head CI, review, or merge evidence.

## Current checkpoint

Checkpoint date: 2026-08-24.

- v0.4 architecture checkpoint: Issue #73 / PR #74 — complete.
- architecture merge commit: `a7fb245bd39f8aa3dc18141c2ecf6f005f02ebd1`.
- shared constrained peak-fitting foundation: Issue #75 / PR #76 — complete.
- shared-fitting merge commit / current scientific baseline: `b6f428d96df9950373c17e5de487ac4113a2aacc`.
- exact-head fitting CI: run #255 / `32733891934` — success.
- fitting formal review ids: `5008457897`, `5008470806`.
- reviewed runtime dependency: `lmfit>=1.3.4` (BSD-3-Clause upstream).
- project version remains `0.3.0`.
- no v0.4 tag, GitHub Release, or package-registry publication has been authorized or performed.
- next scientific stage: **XPS data semantics, explicit energy correction, and explicit linear/Shirley background preparation**.

## v0.4 dependency order

1. **Shared constrained peak-fitting foundation — complete (#75 / #76).**
2. **XPS semantics, energy correction, and background preparation — next.**
3. Constrained XPS components/doublets and shared-fit integration.
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

## XPS stage B — semantics and preparation

The next Issue must establish XPS scientific state before constrained peak optimization is introduced.

### Binding-energy semantics

- canonical x semantic is binding energy;
- supported unit is explicit eV in the first implementation;
- semantics are validated from axis state/metadata, not inferred only from display text;
- x must be finite and strictly monotonic; ascending and descending storage are both valid;
- source order is preserved;
- duplicate/non-finite energy values fail explicitly;
- no automatic sorting or interpolation.

### Energy-reference correction

Energy correction is a separate explicit transformation.

- caller supplies an additive shift in eV;
- corrected energy is `E_corrected = E_source + shift_eV`;
- the shift, source reference/rationale, and deterministic provenance are retained;
- correction does not change intensity values;
- repeated or contradictory correction must be detectable rather than silently accumulated;
- no element/orbital name or expected literature position triggers automatic charge correction.

### Fit-region preparation

- caller supplies the low/high binding-energy region;
- selection is inclusive of measured points and independent of storage direction;
- no interpolation or endpoint synthesis occurs;
- the prepared region retains source identity and correction/background provenance;
- insufficient or missing measured data fail explicitly.

### Initial XPS backgrounds

The first XPS preparation stage may implement only explicitly contracted background families:

1. **linear** — determined from caller-visible boundary values/regions under a documented equation;
2. **Shirley** — implemented with an explicit numerical equation, convergence criterion/iteration limit, direction handling, and hand-verifiable or independently reproducible regression cases.

Background output is a separate retained numerical state/array that can later be passed into the shared fitter. Background preparation must not fit peaks or silently smooth/normalize/reorder the spectrum.

Tougaard remains deferred until a dedicated Issue contracts its equation, parameters, numerical implementation, and validation evidence.

### Explicit non-goals of XPS stage B

Stage B does not automatically:

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

After stage B is reviewed and merged, XPS-specific constrained fitting may consume the shared fitter.

- spin-orbit doublets are linked shared-fitting components;
- separation, amplitude/area ratio, and width ties are caller supplied in the first implementation;
- no hidden textbook lookup is permitted;
- assignment labels are metadata, not evidence that a chemical state has been proven;
- explicit XPS background state from stage B feeds the shared fitter rather than being recreated inside the generic fitting layer.

## Visualization boundary

XPS plotting remains a later lazy adapter over the existing `FigureSpec`/shared visualization system. Rendering may show measured spectrum, explicit background, component curves, total fit, and residual diagnostics, but it must not perform fitting, background calculation, energy correction, smoothing, normalization, or assignment.

## Prior-art / license decisions

The architecture record remains in [`REFERENCES.md`](REFERENCES.md). Key decisions relevant to the next stages are:

- `lmfit/lmfit-py` — BSD-3-Clause; now an implemented runtime backend for shared fitting;
- `derb12/pybaselines` — BSD-3-Clause; potential general-spectroscopy baseline adapter, not assumed to supply XPS Shirley/Tougaard semantics;
- `jacobdben/XPyS` — MIT; XPS scientific/workflow reference only;
- `JulioAzcarate/pyFitXPS` — non-standard/NOASSERTION repository license metadata; reference only;
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
