# CatalysisWorkbench v0.4 Plan

v0.4 starts from the reviewed post-v0.3 documentation baseline on `main` at `112c3c29fc8dcbfbf70f384baaba3f66fc1429f1`. The tagged v0.3 release remains immutable at `v0.3.0 -> 845ac4c15d399a8816c7ba66d61ea6ec4cc11293`.

v0.4 is the advanced-experimental-analysis release. Its first architecture decision is deliberate: **shared constrained peak fitting is designed together with XPS as a concrete spectroscopy consumer before either layer is implemented**.

This document defines dependency order and scientific/API boundaries. It is not permission to bypass the normal Issue -> Draft PR -> exact-head CI -> two-pass review -> merge-gate workflow.

## Release scope and dependency order

The intended v0.4 sequence is:

1. shared constrained peak-fitting foundation and mature nonlinear-fit backend integration;
2. XPS data semantics, explicit energy calibration and background preparation;
3. constrained XPS peak components/doublets and shared-fit integration;
4. XPS publication plotting and fit diagnostics/summary;
5. EIS plotting and basic equivalent-circuit fitting;
6. quantitative BET fitting;
7. product calibration and GC/HPLC/NMR-derived quantification;
8. completion-state synchronization and later release hardening/version gates.

The ordering is architectural. Work may be split further when an Issue is too large, but later consumers must not force hidden scientific assumptions into the shared foundation.

## Prior-art and license record for the first architecture block

### `lmfit/lmfit-py`

- Upstream LICENSE: BSD-3-Clause.
- Provides named parameters, fixed/varying state, lower/upper bounds, expression constraints, composite models, fit statistics, standard errors/correlations and confidence-interval tooling on top of NumPy/SciPy.
- Built-in model coverage includes Gaussian/Lorentzian/Voigt/pseudo-Voigt and Doniach-style asymmetric fitting support relevant to spectroscopy.
- Decision: **preferred backend candidate** for the first constrained-fitting implementation. CatalysisWorkbench owns the scientific contract, validation, deterministic provenance and stable result objects; it should not reimplement mature nonlinear least-squares optimization.
- No runtime dependency is added by this architecture checkpoint. Dependency changes belong to the first implementation Issue and must pass packaging/license review.

### `derb12/pybaselines`

- Upstream license: BSD-3-Clause.
- Mature general baseline-correction ecosystem for spectroscopy/materials data.
- Decision: later dependency/adapter candidate for general spectroscopy baselines. A search of the upstream project did not establish Shirley or Tougaard as provided XPS-specific backgrounds, so the architecture must not assume that all XPS background work can be delegated to pybaselines.

### `jacobdben/XPyS`

- Upstream license: MIT.
- Useful reference concepts: explicit p/d doublet separation, caller-provided peak guesses, linear background, Shirley background and separate fitting/plotting operations.
- Decision: scientific/workflow reference only. No code is copied.

### `JulioAzcarate/pyFitXPS`

- GitHub repository license metadata is non-standard/NOASSERTION.
- Useful reference concepts: sequential spectra, explicit energy-scale correction, separation of original/corrected/fit result state, lmfit-backed XPS fitting and physically motivated asymmetric/convolved line shapes.
- Decision: architecture/scientific reference only; no implementation reuse without a separately verified compatible license.

### `Julian-Hochhaus/LG4X-V2`

- Top-level project text is MIT, but its LICENSE explicitly records mixed third-party provenance including GPL-derived XPS/VAMAS code.
- Useful reference concepts: lmfit-backed XPS GUI, interactive parameter editing and fit-consistency validation.
- Decision: **reference-only** for workflow/UX. Do not copy implementation or vendor/XPS parsing code from this project into CatalysisWorkbench.

## Shared constrained-fitting contract

The shared fitter is technique-agnostic, but its first contract is justified by the concrete XPS consumer.

### Stable scientific identity

- Parameter and component identity uses stable non-display keys.
- Human-readable labels are metadata only and may be duplicated or changed without changing the scientific mapping.
- Dataset-level mappings must continue the project rule of addressing scientific state by stable keys rather than display labels.

### Parameter specification

The first implementation should provide an immutable/value-oriented parameter specification equivalent in responsibility to `FitParameterSpec`:

- stable parameter key/name;
- initial value;
- `vary`/fixed state;
- optional finite lower and upper bounds;
- optional expression/tie to other named parameters;
- deterministic validation of impossible bounds, invalid names and invalid ties before fitting when possible.

The public contract must not expose mutable backend `Parameter` objects as CatalysisWorkbench's durable scientific state.

### Peak-component specification

A peak-component specification equivalent in responsibility to `PeakComponentSpec` should contain:

- stable component key;
- explicit model family;
- explicit parameter specifications;
- optional display/assignment metadata that is not used as mathematical identity.

The initial model family is intentionally small: Gaussian, Lorentzian, Voigt, pseudo-Voigt and one explicitly documented Doniach/Doniach-Sunjic-style asymmetric model supported by the selected backend. Additional line shapes require a concrete scientific consumer and regression tests.

### Fit specification

A fit specification equivalent in responsibility to `PeakFitSpec` must record:

- explicit fit window;
- ordered components;
- explicit background representation/policy;
- weighting or measurement-uncertainty basis when used;
- solver/method choice when it changes fit behavior;
- deterministic options required to reproduce the fit.

No automatic peak detection, component-count choice, smoothing, normalization, baseline estimation, hidden resampling or chemistry assignment occurs in the shared fitter.

### Fit result

A result object equivalent in responsibility to `PeakFitResult` must retain enough information to audit and replot the analysis without exposing backend internals as the primary API:

- source-data reference and deterministic numerical digest;
- exact fit specification/provenance;
- x grid used for fitting;
- observed values used for fitting;
- total best-fit curve;
- background curve/state where applicable;
- per-component curves in stable-key order;
- residuals;
- optimized parameter values;
- standard errors/covariance/correlations where the backend actually provides them;
- fit statistics relevant to the selected objective;
- success/status/message and backend/method identity.

Unavailable covariance or standard errors remain explicitly unavailable. They must never be replaced by zero or silently described as estimated uncertainty.

## Background and baseline boundary

The shared fitting layer does not define one universal spectroscopy background.

- It may accept a caller-prepared background array or a separately contracted background model.
- General spectroscopy baseline estimation may later use a `pybaselines` adapter.
- XPS-specific background algorithms belong to the XPS layer and feed an explicit result into the shared fitting layer.
- Initial XPS background scope may include **linear** and **Shirley** backgrounds when implemented with hand-verifiable regression tests.
- Tougaard background is deferred unless a dedicated Issue contracts its equation, parameters, numerical method and validation data.
- Background selection is always explicit and becomes fit provenance.

This boundary prevents a generic peak-fitting API from silently acquiring technique-specific background assumptions.

## XPS scientific/API contract

### Binding-energy semantics

- Canonical x semantic is binding energy with explicit eV unit.
- Scientific semantics are validated from axis state/metadata rather than inferred only from a display label.
- Ascending and descending stored binding-energy grids may be supported if strictly monotonic; source order is preserved unless an explicit operation states otherwise.
- Duplicate/non-finite energy values and missing fit-window data fail explicitly.

### Energy calibration/reference correction

- Energy correction is a separate explicit transformation with an additive shift and caller-visible reference rationale/metadata.
- No automatic charge correction is inferred from element names, peak assignments or expected literature positions.
- Corrected data preserve the raw source identity and record the applied shift/provenance.
- Repeated or contradictory correction must be detectable rather than silently accumulated.

### Fit windows

- XPS fit regions are caller-supplied and stored in provenance.
- No automatic region selection or hidden clipping is performed.
- A fit window must contain enough finite measured points for the requested model; failures are explicit.

### Spin-orbit doublets

- Doublets are represented as linked peak components using shared parameter constraints.
- Separation and area/amplitude ratio constraints are **caller supplied** in the first implementation.
- The library must not silently look up textbook spin-orbit separations or branching ratios from an element/orbital label.
- Width ties and other physical constraints are explicit parameters/expressions, not hidden defaults.
- Component assignment labels are descriptive metadata; fitting does not prove chemical state, oxidation state or speciation.

### XPS background preparation

- Background type and parameters are explicit.
- Linear and Shirley may be the first supported background families.
- Background preparation does not silently smooth, normalize or reorder the measured spectrum.
- Background numerical output and parameters are retained so later fitting/plotting can be audited independently.

### Explicit non-goals

The initial XPS stack does not automatically:

- detect peaks;
- choose the number of components;
- assign oxidation states or chemical species;
- apply charge correction;
- select literature binding energies;
- choose spin-orbit separation/branching ratios;
- smooth spectra;
- normalize spectra;
- choose a background;
- perform global/sequential multi-spectrum fitting unless separately contracted.

## Visualization contract

XPS publication rendering will be a later lazy adapter over the existing `FigureSpec`/shared visualization model.

It should be able to render:

- measured spectrum;
- total fit;
- explicit background;
- individual stable-key components;
- residual diagnostics;
- caller-controlled annotations and axes direction.

Rendering performs no fit, background calculation, energy correction, smoothing or normalization. Importing the numerical XPS/fitting API should remain Matplotlib-lazy.

## Proposed implementation Issues

### A. Shared constrained peak-fitting foundation

Deliver the value-oriented parameter/component/fit/result contracts, lmfit adapter, bounded initial model family, deterministic provenance and hand-verifiable synthetic regressions. No XPS-specific background or chemistry belongs in this Issue.

### B. XPS semantics and preparation

Deliver binding-energy/intensity validation, explicit energy correction, fit-region preparation, linear/Shirley background state and provenance. No peak optimization belongs in this Issue except what is required for a narrowly scoped calibration reference if separately justified.

### C. Constrained XPS fitting

Deliver XPS component/doublet specifications as a consumer of the shared fitter, caller-supplied separation/ratio/width ties, fit integration and XPS-specific result summaries.

### D. XPS publication plotting and diagnostics

Deliver lazy shared-renderer plotting for raw/background/components/total fit/residuals plus compact quickstart and installed-wheel smoke.

### E. EIS

Use a fresh prior-art/license review led by `ECSHackWeek/impedance.py`; preserve complex data, explicit units/sign conventions and explicit equivalent-circuit definitions.

### F. Quantitative BET

Begin from the v0.3 sorption contract and perform a fresh equation/region-selection review. BET/Rouquerol criteria must be explicit and independently regression-tested; no inference may be hidden inside plotting.

### G. Product calibration

Define calibration standards, regression/uncertainty, dilution/injection/sample bases and raw instrument-derived quantity boundaries before GC/HPLC/NMR product values enter FE workflows.

## Compatibility and dependency policy

- v0.4 builds on the released v0.3 public API and should preserve reviewed v0.1-v0.3 behavior unless a breaking change is separately planned and reviewed.
- New numerical modules remain independent from Matplotlib until plotting is requested.
- Runtime dependencies are added only when a concrete implementation Issue demonstrates that wrapping a mature library is preferable to reimplementation and license/packaging checks pass.
- Adding `lmfit` is therefore expected to be considered in the first implementation Issue, not in this architecture-only checkpoint.
- `pybaselines`, `impedance.py` or other libraries are not automatically added merely because they are prior art.

## Version and release policy

Architecture and ordinary v0.4 feature work do **not** authorize a version bump, tag, GitHub Release or package-registry publication.

Until a later reviewed release gate says otherwise:

- `[project].version` remains `0.3.0`;
- runtime `catalysis_workbench.__version__` remains `0.3.0`;
- tag `v0.3.0` remains fixed on its reviewed release commit;
- package-registry publication remains separately authorization-gated.

## Quality gate for each scientific Issue

Every v0.4 scientific Issue must follow the existing project loop:

```text
prior-art/license refresh
    -> implementation + hand-verifiable regression tests
    -> Draft PR
    -> exact-head CI
    -> scientific/API/compatibility review
    -> direct fixes
    -> new exact-head CI if the head changes
    -> second formal review on the final exact head
    -> behind=0 / mergeable / review threads=0
    -> Ready
    -> expected-head squash merge
    -> verify main when visible
    -> close Issue
```

No successful test/review result from an older head may be reused after a commit changes the PR head.

## Architecture-checkpoint acceptance

Issue #73 is complete only when:

- this plan and central planning/reference documents consistently record the v0.4 architecture;
- prior-art licenses and dependency/reference-only decisions are explicit;
- shared fitting and XPS-specific responsibilities are separated;
- the first implementation Issue can be written without inventing new architecture during coding;
- docs-only exact-head CI passes;
- two architecture/scientific/API review passes have no unresolved blockers;
- the branch is not behind `main`, review threads are zero and the exact reviewed head is squash-merged.
