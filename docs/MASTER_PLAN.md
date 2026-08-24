# CatalysisWorkbench Master Plan

This document is the project-level execution map for CatalysisWorkbench. It connects the long-range release roadmap to the active GitHub Issue sequence, scientific/API quality gates, documentation responsibilities, and the rule that repository state is authoritative.

## Authority and source of truth

GitHub is the only operational source of truth for project state.

When documents and live repository state disagree, use this precedence order:

1. merged `main` code and tests;
2. current GitHub Issues and Pull Requests;
3. CI status for the exact commit under review;
4. this master plan and release-specific planning documents;
5. README summaries and other descriptive documentation.

Planning documents must be corrected when they drift from merged reality. They do not override code, Issue state, review findings, or CI.

## Current checkpoint

Checkpoint date: 2026-08-24.

- Repository: `xcwang3333-cloud/catalysis-workbench`.
- Stable integration branch: `main`.
- Current scientific `main` baseline: `c76a49d64e096d6db001c27c598356baa797f3a9` (`feat: add explicit quantitative BET fitting (#96)`).
- v0.4 architecture checkpoint: Issue #73 / PR #74 — complete at `a7fb245bd39f8aa3dc18141c2ecf6f005f02ebd1`.
- v0.4 shared constrained peak-fitting foundation: Issue #75 / PR #76 — complete at `b6f428d96df9950373c17e5de487ac4113a2aacc`.
- shared-fitting exact-head CI #255 / run `32733891934` — success.
- shared-fitting formal reviews: `5008457897`, `5008470806`.
- XPS semantics/energy correction/region/background preparation: Issue #79 / PR #80 — complete at `a13dbd541b299f79d83e47f079c4638b082a8061`.
- XPS preparation exact-head CI #261 / run `32736488212` — success.
- XPS preparation formal reviews: `5008700786`, `5008706395`.
- constrained XPS components/doublets and shared-fit integration: Issue #83 / PR #84 — complete at `7897393e1e1e9e4d23fad774b4eeecdd70e2a90b`.
- constrained-XPS final exact-head CI #267 / run `32739584536` — success on `02d2800ec6e87cb41dca041d2734cc09c5da9235`.
- constrained-XPS formal reviews: `5009021201`, `5009026855`.
- XPS publication plotting and fit diagnostics: Issue #87 / PR #88 — complete at `3eab8c8e936cf1897081b7a396306288e517a3bb`.
- XPS plotting final exact-head CI #274 / run `32741710370` — success on `15288b21be118a450614445d6bbf82d80d459271`.
- XPS plotting final-head review records: `5009266827`, `5009270492`.
- EIS semantics, R/C/CPE circuit fitting, Nyquist/Bode plotting, and diagnostics: Issue #91 / PR #92 — complete at `cd8dd171a16576067934a13ad3ac41d0fb18d55a`.
- EIS final exact-head CI #285 / run `32746265252` — success on `18d81a0029cc851c136420fc550ec3e823094862`.
- EIS final-head review records: `5009748594`, `5009757335`.
- quantitative BET fitting and Rouquerol consistency checks: Issue #95 / PR #96 — complete at `c76a49d64e096d6db001c27c598356baa797f3a9`.
- BET final exact-head CI #294 / run `32752441329` — success on `47aee74a5a6b16dbf60bb95c2910ccd197205f2f`.
- BET final-head review records: `5010325152`, `5010328048`.
- Reviewed runtime fitting dependency: `lmfit>=1.3.4`.
- Distribution/runtime version remains `0.3.0`.
- `v0.3.0` remains fixed on release commit `845ac4c15d399a8816c7ba66d61ea6ec4cc11293`.
- Package-registry publication has not been performed and remains a separate policy decision.
- Active status checkpoint: Issue #97 — post-BET docs synchronization and product-calibration handoff.
- Next scientific stage after #97: product calibration / GC-HPLC-NMR-derived quantification.

Live GitHub Issue/PR/tag state remains authoritative if this checkpoint becomes stale.

## Release map

Detailed long-range scope is maintained in [`ROADMAP.md`](ROADMAP.md).

| Release | Primary scope | State |
| --- | --- | --- |
| v0.1.x | common XY core, tabular I/O, reusable processing, LSV, XRD, Raman, shared publication rendering/export | complete/released |
| v0.2.x | quantitative core electrochemistry and shared scatter/bar summaries | complete/released as v0.2.0 |
| v0.3.x | FTIR, thermal analysis, basic gas sorption, ICP/composition | complete/released as v0.3.0 |
| v0.4.x | advanced experimental analysis: shared fitting, XPS, EIS, quantitative BET, product calibration | implementation active |
| v0.5.x | XAS, structures, basic DFT energetics | planned |
| v0.6.x | electronic structure and catalysis thermodynamics | planned |
| v0.7.x | advanced computational visualization | planned |
| v0.8.x | operando/time-resolved analysis | planned |
| v0.9.x | reproducible batch workflows and first interactive editor | planned |
| v1.0.0 | stable personal catalysis data workbench and local GUI | planned |

Release numbering is a planning boundary, not permission to weaken scientific validation or compatibility requirements.

## Completed release baselines

### v0.2

The quantitative core electrochemistry release is complete. Its detailed dependency graph and scientific contracts are retained in [`V0_2_PLAN.md`](V0_2_PLAN.md), with release evidence in [`V0_2_RELEASING.md`](V0_2_RELEASING.md).

Completed scope includes Tafel, Faradaic efficiency, partial current density, catalyst-/metal-mass and ECSA activity normalization, TOF/TOFapp, CV/Cdl/ECSA, stability, RRDE, and Koutecky-Levich basics. The release tag and later post-release documentation synchronization are complete and immutable.

### v0.3

The extended experimental-processing release is complete as `v0.3.0`.

- FTIR / ATR-FTIR — Issue #50 / PR #51.
- TGA / DTG / TPR / TPD — Issue #54 / PR #55.
- basic gas sorption — Issue #58 / PR #59.
- ICP / elemental composition — Issue #62 / PR #63.
- documentation checkpoints — #52/#53, #56/#57, #60/#61, #64/#65.
- Gate A — #66 / #67.
- Gate B final-version candidate — #68 / #69.
- Gate C tag verification — #70.
- post-release docs synchronization — #71 / #72.

The reviewed release tag is `v0.3.0 -> 845ac4c15d399a8816c7ba66d61ea6ec4cc11293`. Quantitative BET fitting and shared peak fitting were intentionally excluded from the v0.3 scientific gate and were implemented later in v0.4.

## v0.4 execution status

The detailed dependency order and scientific boundaries are maintained in [`V0_4_PLAN.md`](V0_4_PLAN.md).

### Architecture checkpoint — complete

Issue #73 / PR #74 established the v0.4 architecture before implementation.

Key decisions:

- generic constrained fitting and technique-specific scientific state are separate layers;
- mature nonlinear optimization is wrapped rather than reimplemented;
- XPS owns binding-energy semantics, explicit energy-reference correction, XPS backgrounds, and spin-orbit constraints;
- caller-supplied physical constraints remain visible and auditable;
- plotting remains separate from numerical processing/fitting.

### Shared constrained fitting — complete

Issue #75 / PR #76 delivered the first scientific implementation block.

Reviewed public behavior includes:

- `FitParameterSpec`, `PeakComponentSpec`, `PeakFitSpec`, `FittedParameter`, `PeakFitResult`, `PeakFittingError`, and `fit_peaks` under `catalysis_workbench.processing`;
- Gaussian, Lorentzian, Voigt, pseudo-Voigt, and Doniach initial model families;
- stable non-display component identities;
- explicit initial/fixed/bounded/tied parameter state;
- `{component.parameter}` public cross-component references;
- explicit fit windows, caller background, and residual-multiplier weights;
- ascending/descending monotonic source-order support without hidden sorting/interpolation;
- deterministic source-data provenance and immutable result arrays;
- physical residual/component/total-fit output;
- optional stderr/covariance/correlation state that remains unavailable when the backend cannot estimate it;
- explicit validation against backend model domains so invalid caller initial values are not silently clipped;
- fixed/constrained-only evaluation without fabricated uncertainty;
- installed-wheel fitting smoke and preservation of all reviewed v0.1-v0.3 tests/quickstarts.

`lmfit>=1.3.4` is a reviewed runtime dependency. Full behavior is documented in [`PEAK_FITTING.md`](PEAK_FITTING.md).

### XPS semantics and preparation — complete

Issue #79 / PR #80 delivered the second v0.4 scientific block.

Reviewed public behavior under `catalysis_workbench.experimental.characterization` includes:

- `validate_xps_series` with explicit `binding_energy`/eV and `intensity` semantics;
- strictly monotonic ascending or descending source storage with source-order preservation;
- `shift_xps_binding_energy` using the literal additive convention `E_corrected = E_source + shift_ev`, deterministic provenance, and repeated-correction rejection;
- `prepare_xps_region` using inclusive measured-point-only numerical bounds without interpolation or synthesized endpoints;
- immutable `XPSBackgroundResult` state with exact source/grid/endpoint/method/convergence provenance;
- direction-safe `linear_xps_background` and independently implemented fixed-point `shirley_xps_background`;
- explicit Shirley convergence/failure state and no copied mixed-provenance implementation;
- numerical XPS imports remaining Matplotlib-lazy;
- fresh installed-wheel XPS smoke while all existing installed smokes and seven quickstarts remain green.

Tougaard, peak fitting, doublet helpers, automatic charge correction, literature lookup, chemistry assignment, smoothing/normalization, plotting, and global/sequential XPS analysis remained outside stage B.

### Constrained XPS fitting — complete

Issue #83 / PR #84 delivered the third v0.4 scientific block as a thin domain adapter over the reviewed shared fitter.

Reviewed public behavior includes:

- `XPSDoubletSpec`, `XPSProcessingStep`, `XPSPeakFitResult`, and `fit_xps_peaks` exported through `catalysis_workbench.experimental.characterization`;
- explicit signed doublet separation with `secondary.center = primary.center + separation_ev`;
- explicit positive caller-supplied amplitude ratio;
- explicit caller-supplied ratios for every remaining model-specific width/shape parameter, with no hidden sigma/gamma/fraction defaults;
- no embedded p/d/f textbook branching ratios, separation tables, charge-correction rules, or chemistry lookup;
- generated links use the existing `{component.parameter}` public expression syntax;
- duplicate/colliding component keys fail before optimization;
- XPS fitting delegates optimization to shared `fit_peaks()` rather than adding a second backend;
- prepared `XPSBackgroundResult` alignment is fail-closed on source key/digest, binding-energy and intensity units, source direction, exact x grid/order, exact observed y, background length/finiteness, and exact fit-region coverage;
- XPS source/preparation history, background state, doublet recipe, source digest/direction and shared fit result remain auditable in `XPSPeakFitResult`;
- assignment/display labels do not alter mathematics;
- installed-wheel constrained-XPS smoke and all prior smokes/quickstarts pass.

One fail-closed review finding was fixed before the final gate: intensity-unit and declared source-direction compatibility were added to background alignment with dedicated regressions. Final evidence is CI #267 / run `32739584536`, reviews `5009021201` and `5009026855`, and merge commit `7897393e1e1e9e4d23fad774b4eeecdd70e2a90b`.

### XPS publication plotting and diagnostics — complete

Issue #87 / PR #88 delivered the fourth v0.4 scientific block as a passive rendering/diagnostic consumer of reviewed XPS fit state.

Reviewed behavior includes:

- lazy `plot_xps_fit()` public dispatch through `catalysis_workbench.experimental.characterization`;
- measured/background/component/best-fit curves rendered directly from retained `XPSPeakFitResult.fit` arrays with no model reevaluation;
- optional residual panel using the exact reviewed physical residual `observed - best_fit`;
- display-only `descending`, `ascending`, or source-order binding-energy orientation without reversing/mutating numerical arrays;
- deterministic stable visual keys `xps_observed`, `xps_background`, `xps_best_fit`, `xps_residual`, while fitted components retain their actual mathematical keys;
- collision/unknown-style-key failure rather than silent style aliasing;
- existing `FigureSpec` typography, line/marker, axes geometry, legend, limit, annotation and export state remains authoritative;
- a small internal multi-axes figure-context refactor preserving the existing single-axes renderer path;
- `XPSFitDiagnostics` / `summarize_xps_fit()` mirror existing success/method/backend/statistics/covariance/stderr availability without fabrication or chemical interpretation;
- root numerical characterization imports remain Matplotlib-lazy;
- installed-wheel plotting/diagnostics/SVG export smoke plus all existing smokes/quickstarts pass.

The first CI attempt exposed only two Ruff defects (unused import and one overlong smoke line); these were corrected without scientific changes. Final evidence is exact-head CI #274 / run `32741710370`, final-head review records `5009266827` and `5009270492`, and expected-head squash merge `3eab8c8e936cf1897081b7a396306288e517a3bb`.

Full XPS preparation/fitting/plotting/diagnostics behavior is documented in [`XPS.md`](XPS.md).

### EIS semantics, basic circuit fitting, and plotting — complete

Issue #91 / PR #92 delivered the fifth v0.4 scientific block as an explicit complex-impedance domain layer under `catalysis_workbench.experimental.echem`.

Reviewed behavior includes:

- existing immutable complex-capable `Series` is reused with explicit `frequency`/Hz and `impedance`/ohm semantics and literal `Z = Z' + jZ''` storage;
- finite positive strictly monotonic ascending or descending frequency is accepted without hidden sorting, interpolation, resampling, sign conversion, or phase unwrapping;
- ideal `EISResistor`, `EISCapacitor`, and `EISCPE` leaves plus explicit `EISSeriesCircuit` / `EISParallelCircuit` composition form the initial typed circuit graph;
- CPE uses the explicit convention `Z = 1 / [Q (j 2π f)^n]` with `Q > 0` and `0 < n <= 1`;
- element keys and public `element.parameter` names are stable and globally unique within a circuit;
- parameter initial values, fixed/vary state and bounds remain explicit and are checked against physical domains;
- `fit_eis()` uses existing SciPy trust-region least squares with deterministic real+imag residual stacking and optional explicit positive point weights applied equally to both objective channels;
- the public physical complex residual remains exactly `Z_observed - Z_best_fit` independent of objective weighting;
- `EISFitResult` is immutable and fail-closes contradictory reconstructed source/direction/unit/circuit/parameter/best-fit/residual/weight/objective state;
- `EISFitDiagnostics` / `summarize_eis_fit()` expose retained fit state without fabricating covariance, standard errors, or electrochemical interpretation;
- lazy `plot_eis_nyquist()` derives exact `Re(Z)` plus caller-selected raw `Im(Z)` or conventional `-Im(Z)` as display state only;
- lazy two-panel `plot_eis_bode()` derives exact magnitude and principal phase without hidden unwrap/reordering and reuses existing `FigureSpec`/multi-axes rendering infrastructure;
- fit overlays require exact source/digest/grid/observed-state alignment;
- root numerical electrochemistry imports remain Matplotlib-lazy;
- `impedance.py` (MIT) and `pyimpspec` (GPL-3.0) are reference-only; no EIS runtime dependency was added;
- installed-wheel EIS fit/plot/export smoke and all existing smokes/quickstarts pass.

Formal review found one real fail-closed issue before the final gate: a manually reconstructed public `EISFitResult` could initially carry contradictory metadata/state. That constructor was hardened and dedicated contradiction regressions were added before the final CI. Final evidence is exact-head CI #285 / run `32746265252` on `18d81a0029cc851c136420fc550ec3e823094862`, reviews `5009748594` and `5009757335`, and expected-head squash merge `cd8dd171a16576067934a13ad3ac41d0fb18d55a`.

Full EIS scientific/fitting/plotting behavior is documented in [`EIS.md`](EIS.md).

### Quantitative BET fitting — complete

Issue #95 / PR #96 delivered the sixth v0.4 scientific block as a fail-closed quantitative consumer of the reviewed v0.3 measured gas-sorption foundation.

Reviewed behavior includes:

- explicit adsorption-branch input and canonical relative-pressure fraction semantics;
- one caller-supplied measured-point `SorptionWindow` candidate region with source order preserved and no synthesized endpoints;
- exact BET transform `p / [n(1-p)]`, exact OLS regression and retained `R²` diagnostic state without a hidden linearity threshold;
- independent physical-consistency checks for positive intercept/`C`/monolayer state, increasing `n(1-p)` with increasing pressure, and fitted monolayer loading inside the selected measured loading span;
- `evaluate_bet_region()` exposes candidate/criterion state while `fit_bet()` returns only an accepted region and fails with the failed criteria otherwise;
- explicit conversion from `mmol/g`, `mol/kg`, `cm^3(STP)/g`, or caller-molar-mass `mg/g` to mol/g before area calculation;
- caller-supplied molecular cross-sectional area with no adsorbate-name lookup table;
- immutable candidate/result arrays and reconstruction checks for transforms, regression state, derived parameters, loading conversion, area and consistency state;
- preprocessing provenance is fail-closed: reviewed `sorption.prepare`, measured-point `crop`, and explicit `sorption.convert_relative_pressure` are accepted, while unknown or y/grid-altering processing is rejected;
- lazy `plot_bet_fit()` renders only exact retained candidate points and retained OLS line through the existing `FigureSpec` stack and performs no refit/region search/conversion/sorting/smoothing/resampling;
- current pyGAPS, BETSI, SESAMI_web, and BEaTmap repositories were directly verified as MIT references; no implementation code was copied and no new runtime dependency was added.

Review found and fixed two real fail-closed issues before the final gate: frozen metadata entries required generic mapping support, and the initial preprocessing blacklist was replaced by an explicit safe allowlist so unknown processing cannot silently enter quantitative BET. Final evidence is exact-head CI #294 / run `32752441329` on `47aee74a5a6b16dbf60bb95c2910ccd197205f2f`, reviews `5010325152` and `5010328048`, and expected-head squash merge `c76a49d64e096d6db001c27c598356baa797f3a9`.

Full quantitative BET behavior is documented in [`BET.md`](BET.md).

### Active next scientific block — product calibration / GC-HPLC-NMR quantification

After the docs-only #97 checkpoint, implementation proceeds to an explicit product-calibration and sample-quantification layer. It must extend the existing v0.2 FE/product-analysis foundation without making detector- or chemistry-specific assumptions from labels.

Required initial boundary:

- separate calibration-standard model fitting from unknown-sample quantification;
- calibration response and known-amount/concentration units remain explicit and compatible;
- caller chooses the calibration model form, fit range/selected standards, intercept policy and any weighting rather than the library silently selecting them;
- retain exact calibration x/y points, model coefficients/fit statistics, units, selected range, source identity and deterministic provenance in immutable result state;
- sample quantification must consume an explicit reviewed calibration result and expose every dilution, injection, aliquot, sample-volume/mass, internal-standard or other multiplicative conversion factor it applies;
- replicate aggregation and uncertainty propagation/reporting must have explicit state; unavailable uncertainty must not be fabricated as zero;
- GC/HPLC/NMR detector response and internal-standard response factors are caller-supplied or separately calibrated, not inferred from product labels;
- product identity, electron stoichiometry and Faradaic-efficiency inputs remain separate downstream scientific state rather than consequences of a calibration label;
- numerical quantification and publication plotting remain separate responsibilities and reuse existing `Series`/result/`FigureSpec` conventions where appropriate.

Explicit non-goals of the first product-calibration block:

- no automatic product identification or peak assignment;
- no instrument-vendor binary parsing unless separately contracted;
- no hidden response-factor library, dilution factor, injection volume, standard density, stoichiometry or internal-standard relation;
- no automatic model/fit-range selection solely from maximum `R²`;
- no direct FE calculation hidden inside calibration fitting;
- no GUI or new plotting framework parallel to `FigureSpec`.

### Later v0.4 dependency order

1. product calibration / GC-HPLC-NMR quantification;
2. completion-state synchronization and later release gates.

## Mandatory development loop

Every new scientific feature follows the same merge path:

```text
prior-art/license refresh
    -> implementation + regression tests
    -> Draft PR
    -> exact-head CI
    -> scientific/API/compatibility review
    -> direct fixes on the feature branch
    -> fresh exact-head CI after every head change
    -> second formal review on final exact head
    -> Ready
    -> merge gate
    -> expected-head squash merge
    -> main verification
    -> issue closure
```

A feature is not complete because code exists or a local/old CI run passed. Completion requires the final exact head to satisfy the scientific contract, public API/compatibility expectations, CI, documentation, and Issue acceptance criteria.

For release-hardening or version-gate work, use the same exact-head discipline but substitute release/API/packaging/version review as appropriate.

## Prior-art rule

Before coding a new scientific or visualization feature:

1. survey comparable open-source GitHub/scientific-Python projects;
2. identify useful equations, data-processing patterns, API/data-model ideas, visualization approaches, and regression-test cases;
3. record licenses;
4. distinguish architecture/reference-only use from dependencies or copied/adapted implementation;
5. record decisions in [`REFERENCES.md`](REFERENCES.md) and the module-specific scientific document/Issue where appropriate.

Permissive prior art is not copied automatically. GPL, mixed-provenance, missing-license, or otherwise restrictive projects may be useful reference-only sources, but implementation reuse must respect license compatibility.

## Scientific and API guardrails

Across releases:

- units, reference states, normalization bases, sign conventions, fit windows, stoichiometry, constraints, and denominator bases are explicit rather than inferred from display labels;
- numerical processing and visualization remain separate responsibilities;
- stable keys, not display labels, address sample/component-specific state;
- derived results retain deterministic source identity and enough analysis state to remain auditable;
- scientific incompatibilities fail explicitly instead of being silently aligned, converted, clipped, renormalized, smoothed, or corrected;
- shared primitives are extended centrally instead of creating technique-specific duplicate stacks;
- public import surfaces remain deliberate and installed-wheel smoke tests protect them;
- existing reviewed behavior remains compatible unless a breaking change is separately planned and reviewed.

## Merge gate

Before Ready/squash merge, confirm at minimum:

- Issue scope and acceptance criteria are satisfied;
- prior-art/license decisions are recorded when functionality is added;
- regression tests cover hand-verifiable behavior and explicit failure modes;
- Ruff/full pytest pass;
- package/fresh-wheel public-API smoke passes when exercised by CI;
- formal review has no unresolved blockers;
- second review is performed after all fixes on the final exact head;
- docs describe the behavior actually present in that head;
- behind=0, mergeable state is true, unresolved review threads are zero;
- merge uses the same head SHA that passed final CI/review.

After squash merge, re-read `main`. When connector visibility does not expose a main-push CI run, do not mislabel an older PR run as main CI evidence.

## Documentation roles

- [`../README.md`](../README.md): user-facing overview, installation, public capability summary, and links.
- [`MASTER_PLAN.md`](MASTER_PLAN.md): project-wide execution order, checkpoint summary, governance, and quality gates.
- [`ROADMAP.md`](ROADMAP.md): long-range release scope; not a per-commit log.
- [`V0_4_PLAN.md`](V0_4_PLAN.md): active v0.4 dependency order and scientific/API boundaries.
- [`PEAK_FITTING.md`](PEAK_FITTING.md): reviewed shared-fitting contract.
- [`XPS.md`](XPS.md): reviewed XPS semantics, preparation, fitting, plotting and diagnostics contract.
- [`EIS.md`](EIS.md): reviewed EIS semantics, circuit fitting, Nyquist/Bode plotting and diagnostics contract.
- [`BET.md`](BET.md): reviewed quantitative BET equations, consistency, conversion, provenance and plotting contract.
- [`REFERENCES.md`](REFERENCES.md): prior-art projects, useful ideas, licenses, and dependency/reference-only decisions.
- module-specific documents: exact scientific/API contracts for implemented modules.
- GitHub Issues: active acceptance criteria.
- GitHub Pull Requests: concrete diff, review evidence, CI state, and merge decision.

## State-maintenance rule

After each merged scientific Issue, update only documentation whose statements became false or materially incomplete. Before starting the next feature, verify:

- live `main` HEAD;
- open Issues/PRs;
- current release plan;
- public capability claims;
- whether the preceding Issue is actually closed/completed;
- version/tag/publication boundaries.

The post-BET checkpoint is Issue #97. After it merges, the next active scientific Issue should implement explicit product calibration / GC-HPLC-NMR-derived quantification without reopening or duplicating the completed measured-isotherm, quantitative BET, XPS, EIS, or shared-fitting foundations.