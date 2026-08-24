# CatalysisWorkbench v0.4 Plan

v0.4 is the advanced-experimental-analysis release. It builds on the released `v0.3.0` tag at `845ac4c15d399a8816c7ba66d61ea6ec4cc11293`; that tag remains immutable. Scientific implementation of the planned v0.4 scope and Gate A release hardening are complete. Gate B is the authorized final-version candidate and reports distribution/runtime version `0.4.0`; v0.4 is **not yet tagged or released**.

GitHub remains the operational source of truth. This document records reviewed dependency order and scientific/API boundaries; exact release-gate evidence is maintained in [`V0_4_RELEASING.md`](V0_4_RELEASING.md).

## Current checkpoint

Checkpoint date: 2026-08-25.

- architecture checkpoint: Issue #73 / PR #74 — complete at `a7fb245bd39f8aa3dc18141c2ecf6f005f02ebd1`;
- shared constrained peak fitting: Issue #75 / PR #76 — complete at `b6f428d96df9950373c17e5de487ac4113a2aacc`; CI #255; reviews `5008457897`, `5008470806`;
- XPS preparation: Issue #79 / PR #80 — complete at `a13dbd541b299f79d83e47f079c4638b082a8061`; CI #261; reviews `5008700786`, `5008706395`;
- constrained XPS fitting: Issue #83 / PR #84 — complete at `7897393e1e1e9e4d23fad774b4eeecdd70e2a90b`; final CI #267 / run `32739584536`; reviews `5009021201`, `5009026855`;
- XPS plotting/diagnostics: Issue #87 / PR #88 — complete at `3eab8c8e936cf1897081b7a396306288e517a3bb`; final CI #274 / run `32741710370`; reviews `5009266827`, `5009270492`;
- EIS: Issue #91 / PR #92 — complete at `cd8dd171a16576067934a13ad3ac41d0fb18d55a`; final CI #285 / run `32746265252`; reviews `5009748594`, `5009757335`;
- quantitative BET: Issue #95 / PR #96 — complete at `c76a49d64e096d6db001c27c598356baa797f3a9`; final CI #294 / run `32752441329`; reviews `5010325152`, `5010328048`;
- product calibration / inverse sample quantification: Issue #99 / PR #100 — complete at `adc0f50178d899b4f257842da6e7bac553a25254`; final head `967d495bba8c8f0102b8b37a6f880f566d776206`; CI #298 / run `32755942830`; reviews `5010636300`, `5010639945`;
- completion-state documentation checkpoint: Issue #101 / PR #102 — complete at `a02df77d078671e24b07b37f6196204e312c9146`;
- Gate A / Issue #103 / PR #104 — complete at `ce06abc11559fa7679869fc83a59356735ce6824`; final head `9d79845d6fae253b01a46794c3c055e4966c6e55`; CI #302 / run `32758548117`; reviews `5010905065`, `5010908809`;
- all planned v0.4 scientific blocks: **complete**;
- reviewed runtime dependency: `lmfit>=1.3.4` (BSD-3-Clause upstream);
- active Gate-B branch project version: `0.4.0`;
- immutable prior release tag: `v0.3.0 -> 845ac4c15d399a8816c7ba66d61ea6ec4cc11293`;
- active release stage: **Gate B / Issue #105 — final `0.4.0` exact-wheel candidate**;
- no `v0.4.0` tag, GitHub Release, or package-registry publication has been performed;
- next boundary after Gate B: **Gate C tag creation**, requiring separate explicit authorization.

## v0.4 dependency order — completed

1. **Shared constrained peak-fitting foundation — complete (#75 / #76).**
2. **XPS semantics, energy correction, and background preparation — complete (#79 / #80).**
3. **Constrained XPS components/doublets and shared-fit integration — complete (#83 / #84).**
4. **XPS publication plotting and fit diagnostics — complete (#87 / #88).**
5. **EIS semantics, Nyquist/Bode plotting and basic equivalent-circuit fitting — complete (#91 / #92).**
6. **Quantitative BET fitting — complete (#95 / #96).**
7. **Product calibration and sample quantification — complete (#99 / #100).**
8. **Completion-state synchronization — complete (#101 / #102).**
9. **Gate A frozen-scope release hardening — complete (#103 / #104).**
10. **Gate B final-version candidate — active (#105).**
11. **Gate C tag creation — not authorized; separate boundary.**

## Shared constrained fitting foundation

Issue #75 introduced a technique-agnostic fitting layer under `catalysis_workbench.processing` backed by reviewed `lmfit` optimization/model primitives.

Reviewed invariants:

- stable non-display component/parameter keys;
- explicit initial, fixed, bounded and tied parameter state;
- public `{component.parameter}` cross-component references;
- explicit fit windows, caller background and optional residual-multiplier weights;
- Gaussian, Lorentzian, Voigt, pseudo-Voigt and Doniach initial line-shape families;
- physical residual `observed - model` remains distinct from the weighted optimizer objective;
- ascending/descending source order is preserved;
- no hidden sorting, interpolation, smoothing, normalization, baseline estimation, peak detection, component-count selection or chemistry assignment;
- invalid caller state is checked before the backend can silently clip it;
- immutable result/provenance state and uncertainty that remains unavailable when it cannot be estimated.

Full behavior is documented in [`PEAK_FITTING.md`](PEAK_FITTING.md).

## XPS stack

### Preparation — #79 / #80

Reviewed behavior:

- canonical binding-energy semantics in eV;
- explicit additive correction `E_corrected = E_source + shift_ev`;
- repeated library-applied correction rejected;
- measured-point-only region selection with source-order preservation;
- deterministic linear background;
- independently implemented Shirley fixed-point background with explicit tolerances/iteration limit/convergence failure;
- no automatic charge correction, chemistry lookup, smoothing or normalization.

### Constrained fitting — #83 / #84

Reviewed behavior:

- XPS fitting remains a thin consumer of shared `fit_peaks()`;
- `XPSDoubletSpec` uses caller-supplied signed separation, amplitude ratio and explicit model-specific shape/width relations;
- no hidden p/d/f textbook ratios or splitting tables;
- prepared background must match source key/digest, units, direction, x grid/order and observed intensities exactly;
- duplicate/colliding keys and incompatible scientific state fail before optimization.

### Publication plotting/diagnostics — #87 / #88

Reviewed behavior:

- `plot_xps_fit()` consumes retained observed/background/component/best-fit arrays only;
- optional residual panel uses the reviewed physical residual;
- binding-energy direction is display-only;
- deterministic stable visual keys use the existing `FigureSpec` system;
- diagnostics mirror existing fit/statistical/uncertainty availability without fabricating chemistry or uncertainty.

Full XPS behavior is documented in [`XPS.md`](XPS.md).

## EIS — #91 / #92

Reviewed behavior:

- canonical frequency/Hz and literal complex impedance/ohm state;
- strictly positive monotonic ascending/descending frequency with source order retained;
- ideal R/C/CPE elements with explicit series/parallel composition;
- stable `element.parameter` identities and caller-visible initial/fixed/bounds state;
- SciPy trust-region least squares using deterministic real+imag objective channels;
- public physical residual remains exact `Z_observed - Z_best_fit` regardless of objective weighting;
- immutable fail-closed result reconstruction ties units, direction, circuit, parameters, fit, residual, weights and objective state together;
- passive Nyquist/Bode plotting performs no unit/sign/order correction beyond caller-visible display conventions;
- numerical imports remain Matplotlib-lazy.

`ECSHackWeek/impedance.py` (MIT) and `vyrjana/pyimpspec` (GPL-3.0) were reference-only. No EIS dependency was added. Full behavior is documented in [`EIS.md`](EIS.md).

## Quantitative BET — #95 / #96

Reviewed behavior:

- reuses the reviewed v0.3 `Series` / `SorptionCondition` / `SorptionWindow` foundation;
- explicit adsorption branch and relative-pressure fraction basis;
- caller-selected inclusive measured-point region only;
- exact BET transform `p / [n(1-p)]` and OLS state;
- R² is diagnostic only, with no hidden threshold;
- independent positive-parameter, Rouquerol transform-monotonicity and monolayer-inside-region checks;
- `evaluate_bet_region()` exposes criterion state while `fit_bet()` returns only a physically accepted result;
- explicit loading conversion to mol/g and caller-supplied molecular cross-sectional area;
- fail-closed preprocessing allowlist permits only reviewed preparation, measured-point crop and explicit relative-pressure conversion;
- passive retained-array BET plotting does not refit/search/convert/sort/smooth/resample.

pyGAPS, BETSI, SESAMI_web and BEaTmap were directly verified as current MIT reference projects for Issue #95; no implementation was copied and no new dependency was added. Full behavior is documented in [`BET.md`](BET.md).

## Product calibration and sample quantification — #99 / #100

The final planned v0.4 scientific block is a technique-agnostic product-analysis layer under `catalysis_workbench.experimental.product`, explicitly upstream of the existing electrochemical FE/product calculations.

### Calibration contract

- core `Series` input uses x semantic `calibration_quantity` and y semantic `response`, each with explicit units;
- at least three observations and two distinct known quantities are required;
- repeated known quantities remain explicit observations and are not automatically averaged;
- optional `CalibrationRange` selects measured standards only and preserves source indices/order;
- first reviewed model is linear only: `response = intercept + slope * quantity`;
- caller explicitly chooses `intercept_policy="free"` or `"zero"`;
- no polynomial/nonlinear model or automatic model/range selection;
- retained result includes source identity/digest, selected arrays, coefficients, best-fit response, physical residual, centered R² when defined, uncertainty availability and exact two-point fit line;
- public result reconstruction is fail-closed against contradictory retained state.

### Inverse quantification

- `quantify_response()` consumes a reviewed calibration result separately from calibration fitting;
- response unit must match calibration response unit exactly;
- inverse quantity is `(response - intercept) / slope`;
- negative inferred quantity fails instead of being clipped;
- extrapolation outside the selected calibration quantity span is rejected by default and requires explicit opt-in;
- ordered `QuantificationFactor` values are explicit positive finite dimensionless multipliers with unique stable keys;
- factor labels have no hidden mathematical meaning;
- output quantity unit remains the calibration x unit; there is no generic unit algebra or hidden concentration-to-moles transformation;
- no product identity, internal-standard identification, response-factor lookup, dilution/injection/aliquot/sample-volume/mass/density/flow correction, electron stoichiometry or FE calculation is inferred.

### Replicates and plotting

- replicate summary reports arithmetic mean, sample SD (`ddof=1`), RSD when defined and n;
- one replicate keeps mean/n while SD/RSD remain unavailable;
- no automatic outlier rejection or weighting;
- `plot_calibration()` is a lazy passive adapter over exact retained standards and fit-line arrays using stable `FigureSpec` keys;
- rendering performs no refit, range selection, conversion, sorting, smoothing or uncertainty invention.

### Prior-art/license boundary

Issue #99 and [`PRODUCT_CALIBRATION.md`](PRODUCT_CALIBRATION.md) record:

- `cremerlab/hplc-py` — GPL-3.0, scientific/workflow reference only;
- `FelixKatz77/pyGecko` — MIT, GC-FID quantification workflow/API reference only;
- `MyonicS/ChromStream` — MIT, architecture reference for separating parsing/integration from calibration;
- `jjhelmus/nmrglue` — BSD-3-Clause, raw-NMR processing/reference and possible later adapter candidate.

No upstream implementation was copied/adapted and no new runtime dependency was added.

Validation evidence: final feature head `967d495bba8c8f0102b8b37a6f880f566d776206`; CI #298 / run `32755942830` success; final-head reviews `5010636300`, `5010639945`; behind=0, mergeable=true, review threads=0; squash merge/current scientific baseline `adc0f50178d899b4f257842da6e7bac553a25254`.

## v0.4 release state

All seven planned scientific blocks and the completion-state synchronization are complete.

Gate A / Issue #103 / PR #104 is complete. It froze the scientific scope, added the unified installed-wheel/public-API audit, retained version `0.3.0`, passed exact-head CI #302 / run `32758548117` and formal reviews `5010905065`, `5010908809`, and squash-merged as `ce06abc11559fa7679869fc83a59356735ce6824`.

Gate B / Issue #105 is separately authorized and active. It changes both version declarations to `0.4.0`, changes only the expected release version in the existing unified wheel audit, stages the `[0.4.0]` changelog candidate, and reruns the complete frozen-scope audit on the final exact head. It does not authorize a tag.

The remaining release boundaries are:

1. **Gate C — tag creation and reverse verification.** Only after Gate B has merged and explicit authorization is given.
2. **GitHub Release creation — separate action.** Not inferred from a tag.
3. **Package registry publication — separate policy/action.** Not inferred from either a tag or GitHub Release.

## Prior-art / license decisions

Long-lived architecture references remain in [`REFERENCES.md`](REFERENCES.md). Module-specific decisions are additionally retained in their Issues/documents. Reference presence never authorizes code reuse.

Important v0.4 decisions:

- `lmfit/lmfit-py` — BSD-3-Clause; reviewed runtime backend for shared peak fitting;
- `derb12/pybaselines` — BSD-3-Clause; possible future baseline adapter, not assumed to supply XPS-specific semantics;
- `jacobdben/XPyS` — MIT; XPS workflow/scientific reference only;
- `Julian-Hochhaus/lmfitxps` — Shirley implementation has mixed/GPL provenance recorded upstream; reference only for that implementation;
- `Julian-Hochhaus/LG4X-V2` — mixed provenance including GPL-derived portions; reference only;
- `ECSHackWeek/impedance.py` — MIT; EIS workflow/API/test reference only;
- `vyrjana/pyimpspec` — GPL-3.0; EIS architecture/validation reference only;
- pyGAPS / BETSI / SESAMI_web / BEaTmap — current MIT references for quantitative BET;
- product-calibration references are recorded in Issue #99 and `PRODUCT_CALIBRATION.md` because that module document is the reviewed local license record for this stage.

## Compatibility and version policy

- preserve reviewed v0.1-v0.3 public behavior unless a breaking change is separately planned/reviewed;
- scientific incompatibilities fail explicitly rather than being silently corrected/aligned;
- numerical analysis and rendering remain separate responsibilities;
- runtime dependencies are added only when a concrete Issue justifies them and packaging/license review passes;
- Gate B synchronizes `[project].version` and runtime `__version__` to `0.4.0` together;
- `v0.3.0` remains fixed on its reviewed release commit;
- Gate B does not create `v0.4.0`; Gate C, GitHub Release creation and package-registry publication remain distinct authorization boundaries.

## Required quality loop

Scientific Issues follow:

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

Release gates use the same exact-head discipline with release/API/packaging/version review. CI or review evidence from an older head is never reused after the head changes.

After Gate B / Issue #105 merges and `main` is reverified at `0.4.0`, execution must stop before Gate C until explicit authorization is given to create tag `v0.4.0`.
