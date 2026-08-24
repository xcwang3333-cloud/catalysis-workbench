# CatalysisWorkbench Master Plan

This document is the project-level execution map for CatalysisWorkbench. It connects the long-range release roadmap to active GitHub Issues, scientific/API quality gates, documentation responsibilities, and the rule that repository state is authoritative.

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

Checkpoint date: 2026-08-25.

- Repository: `xcwang3333-cloud/catalysis-workbench`.
- Stable integration branch: `main`.
- Reviewed Gate-A `main` baseline: `ce06abc11559fa7679869fc83a59356735ce6824` (`release: harden frozen v0.4 installed-wheel and public API (#104)`).
- v0.4 architecture checkpoint: Issue #73 / PR #74 — complete at `a7fb245bd39f8aa3dc18141c2ecf6f005f02ebd1`.
- shared constrained peak-fitting: Issue #75 / PR #76 — complete at `b6f428d96df9950373c17e5de487ac4113a2aacc`; CI #255; reviews `5008457897`, `5008470806`.
- XPS preparation: Issue #79 / PR #80 — complete at `a13dbd541b299f79d83e47f079c4638b082a8061`; CI #261; reviews `5008700786`, `5008706395`.
- constrained XPS fitting: Issue #83 / PR #84 — complete at `7897393e1e1e9e4d23fad774b4eeecdd70e2a90b`; final CI #267 / run `32739584536`; reviews `5009021201`, `5009026855`.
- XPS publication plotting/diagnostics: Issue #87 / PR #88 — complete at `3eab8c8e936cf1897081b7a396306288e517a3bb`; final CI #274 / run `32741710370`; reviews `5009266827`, `5009270492`.
- EIS: Issue #91 / PR #92 — complete at `cd8dd171a16576067934a13ad3ac41d0fb18d55a`; final CI #285 / run `32746265252`; reviews `5009748594`, `5009757335`.
- quantitative BET: Issue #95 / PR #96 — complete at `c76a49d64e096d6db001c27c598356baa797f3a9`; final CI #294 / run `32752441329`; reviews `5010325152`, `5010328048`.
- product calibration / inverse sample quantification: Issue #99 / PR #100 — complete at `adc0f50178d899b4f257842da6e7bac553a25254`; final head `967d495bba8c8f0102b8b37a6f880f566d776206`; CI #298 / run `32755942830`; reviews `5010636300`, `5010639945`.
- completion-state documentation checkpoint: Issue #101 / PR #102 — complete at `a02df77d078671e24b07b37f6196204e312c9146`.
- v0.4 scientific implementation: **complete**.
- v0.4 Gate A / Issue #103 / PR #104 — complete at `ce06abc11559fa7679869fc83a59356735ce6824`; final head `9d79845d6fae253b01a46794c3c055e4966c6e55`; CI #302 / run `32758548117`; reviews `5010905065`, `5010908809`.
- Active release stage: **v0.4 Gate B / Issue #105 — final `0.4.0` version candidate and exact-wheel audit**.
- Reviewed runtime fitting dependency: `lmfit>=1.3.4`.
- Gate-B branch distribution/runtime version is `0.4.0`; `main` remains the reviewed Gate-A baseline until Gate B merges.
- `v0.3.0` remains fixed on release commit `845ac4c15d399a8816c7ba66d61ea6ec4cc11293`.
- No `v0.4.0` tag, GitHub Release, or package-registry publication has been performed.
- Next boundary after Gate B: **Gate C creation of tag `v0.4.0`**, requiring separate explicit authorization.

Live GitHub Issue/PR/tag state remains authoritative if this checkpoint becomes stale.

## Release map

Detailed long-range scope is maintained in [`ROADMAP.md`](ROADMAP.md).

| Release | Primary scope | State |
| --- | --- | --- |
| v0.1.x | common XY core, tabular I/O, reusable processing, LSV, XRD, Raman, shared publication rendering/export | complete/released |
| v0.2.x | quantitative core electrochemistry and shared scatter/bar summaries | complete/released as v0.2.0 |
| v0.3.x | FTIR, thermal analysis, basic gas sorption, ICP/composition | complete/released as v0.3.0 |
| v0.4.x | shared fitting, XPS, EIS, quantitative BET, product calibration | scientific scope + Gate A complete; Gate B `0.4.0` candidate active; tag pending |
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

Completed scope includes Tafel, Faradaic efficiency, partial current density, catalyst-/metal-mass and ECSA activity normalization, TOF/TOFapp, CV/Cdl/ECSA, stability, RRDE, and Koutecky-Levich basics.

### v0.3

The extended experimental-processing release is complete as `v0.3.0`.

- FTIR / ATR-FTIR — Issue #50 / PR #51.
- TGA / DTG / TPR / TPD — Issue #54 / PR #55.
- basic gas sorption — Issue #58 / PR #59.
- ICP / elemental composition — Issue #62 / PR #63.
- Gate A — #66 / #67.
- Gate B final-version candidate — #68 / #69.
- Gate C tag verification — #70.
- post-release docs synchronization — #71 / #72.

The reviewed release tag is `v0.3.0 -> 845ac4c15d399a8816c7ba66d61ea6ec4cc11293`. Quantitative BET and shared peak fitting were intentionally excluded from v0.3 and implemented in v0.4.

## v0.4 execution status

The detailed scientific contracts and dependency order are maintained in [`V0_4_PLAN.md`](V0_4_PLAN.md). The release procedure and evidence are maintained in [`V0_4_RELEASING.md`](V0_4_RELEASING.md).

### Architecture checkpoint — complete

Issue #73 / PR #74 established the v0.4 architecture before implementation.

Key decisions:

- generic constrained fitting and technique-specific scientific state are separate layers;
- mature optimization is wrapped rather than reimplemented;
- technique-specific semantics, baselines/backgrounds and physical constraints remain visible at the domain layer;
- caller-supplied physical constraints remain explicit and auditable;
- plotting remains separate from numerical processing/fitting;
- scientific incompatibilities fail explicitly rather than being silently corrected.

### Shared constrained fitting — complete

Issue #75 / PR #76 delivered the shared fitting foundation under `catalysis_workbench.processing`.

Reviewed behavior includes explicit fit windows, stable component/parameter keys, fixed/bounded/tied parameter state, Gaussian/Lorentzian/Voigt/pseudo-Voigt/Doniach families, caller background, physical residuals, optional uncertainty/covariance state, immutable provenance, and explicit validation against backend model domains. `lmfit>=1.3.4` is the reviewed runtime backend. Full behavior is documented in [`PEAK_FITTING.md`](PEAK_FITTING.md).

### XPS preparation — complete

Issue #79 / PR #80 established explicit binding-energy/eV semantics, additive energy-reference correction, measured-point region preparation, direction-safe linear background, and an independently implemented Shirley fixed-point background with explicit convergence/failure state. Numerical imports remain Matplotlib-lazy. Full behavior is documented in [`XPS.md`](XPS.md).

### Constrained XPS fitting — complete

Issue #83 / PR #84 added `XPSDoubletSpec`, `XPSPeakFitResult`, and `fit_xps_peaks()` as a thin consumer of the shared fitter. Doublet separation, amplitude ratios and every remaining model-specific width/shape relation are explicit; prepared backgrounds require exact source/grid/unit/direction alignment; no textbook branching ratios, chemistry assignment or charge-correction lookup are hidden in the fitter.

### XPS publication plotting and diagnostics — complete

Issue #87 / PR #88 added passive rendering over retained XPS fit arrays plus optional physical-residual diagnostics, stable `FigureSpec` keys, display-only binding-energy orientation and immutable diagnostic summaries. Plotting does not refit or reevaluate scientific state.

### EIS — complete

Issue #91 / PR #92 delivered explicit complex impedance semantics, R/C/CPE typed circuit composition, real+imag SciPy least-squares fitting, fail-closed immutable fit reconstruction, diagnostics, and passive Nyquist/Bode rendering. Circuit topology, initial values, bounds, fixed/vary state and weights remain caller-visible. `impedance.py` (MIT) and `pyimpspec` (GPL-3.0) were reference-only; no EIS dependency was added. Full behavior is documented in [`EIS.md`](EIS.md).

### Quantitative BET — complete

Issue #95 / PR #96 delivered a fail-closed quantitative consumer of the reviewed measured gas-sorption foundation.

Reviewed behavior includes:

- explicit adsorption-branch and relative-pressure fraction semantics;
- caller-supplied measured-point `SorptionWindow`;
- exact BET transform and OLS state;
- independent positive-parameter, Rouquerol-transform-monotonicity and monolayer-inside-region checks;
- explicit loading-to-mol/g conversion and caller-supplied molecular cross-sectional area;
- fail-closed preprocessing allowlist;
- passive retained-array BET plotting;
- current pyGAPS, BETSI, SESAMI_web and BEaTmap repositories used as MIT references only.

Final evidence is exact-head CI #294 / run `32752441329` on `47aee74a5a6b16dbf60bb95c2910ccd197205f2f`, reviews `5010325152` and `5010328048`, and squash merge `c76a49d64e096d6db001c27c598356baa797f3a9`. Full behavior is documented in [`BET.md`](BET.md).

### Product calibration and sample quantification — complete

Issue #99 / PR #100 delivered the seventh and final planned v0.4 scientific block under `catalysis_workbench.experimental.product`.

Reviewed behavior includes:

- technique-agnostic calibration upstream of the existing `experimental.echem.fe` layer;
- core `Series` calibration standards with explicit `calibration_quantity` and `response` units;
- optional measured-point-only `CalibrationRange` with no synthesized boundaries;
- explicit linear model with caller-selected free or fixed-zero intercept policy;
- retained standards, slope/intercept, physical residual, centered R² when defined, uncertainty availability and exact fit-line state;
- immutable fail-closed calibration-result reconstruction;
- separate `quantify_response()` with exact response-unit matching;
- default extrapolation rejection with explicit opt-in and retained extrapolation mask;
- explicit ordered positive dimensionless `QuantificationFactor` values;
- negative inferred quantities fail instead of being clipped;
- replicate arithmetic mean, sample SD and RSD summaries with unavailable single-replicate uncertainty left unavailable;
- lazy passive calibration plotting through existing `FigureSpec` stable keys;
- no raw GC/HPLC/NMR parsing, baseline/peak integration/assignment, internal-standard identification, hidden response-factor library, nonlinear model/range selection, generic unit algebra, electron stoichiometry or FE calculation.

Prior-art/license decisions are recorded in Issue #99 and [`PRODUCT_CALIBRATION.md`](PRODUCT_CALIBRATION.md): hplc-py (GPL-3.0) reference-only, pyGecko (MIT) reference-only, ChromStream (MIT) reference-only, and nmrglue (BSD-3-Clause) reference/later-adapter candidate. No new runtime dependency was added.

Final evidence: exact head `967d495bba8c8f0102b8b37a6f880f566d776206`; CI #298 / run `32755942830` success; reviews `5010636300` and `5010639945`; behind=0 / mergeable=true / threads=0; expected-head squash merge `adc0f50178d899b4f257842da6e7bac553a25254`.

## v0.4 release gates

All planned v0.4 scientific blocks and the completion-state synchronization are merged.

Gate A / Issue #103 / PR #104 is complete. It froze the v0.4 scientific scope, added the unified installed-wheel/public-API audit, retained version `0.3.0`, passed exact-head CI #302 / run `32758548117` and two formal release reviews, and squash-merged as `ce06abc11559fa7679869fc83a59356735ce6824`.

Gate B / Issue #105 is separately authorized and active. It changes distribution/runtime version together to `0.4.0`, updates the expected exact-wheel version, stages the v0.4 changelog candidate, and reruns the complete Gate-A audit on the final `0.4.0` artifact. It must not add scientific functionality.

The following actions remain separate after Gate B:

- creating or moving tag `v0.4.0` — Gate C, explicit authorization required;
- creating a GitHub Release;
- publishing to PyPI or another package registry.

Each release boundary must be explicit and exact-head reviewed.

## Mandatory development loop

Every scientific feature follows:

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
    -> behind=0 / mergeable / review threads=0
    -> expected-head squash merge
    -> main verification
    -> issue closure
```

A feature is not complete because code exists or an old CI run passed. Completion requires the final exact head to satisfy the scientific contract, public API/compatibility expectations, CI, documentation and Issue acceptance criteria.

For release-hardening/version gates, use the same exact-head discipline with release/API/packaging/version review as appropriate.

## Prior-art rule

Before coding a new scientific or visualization feature:

1. survey comparable open-source GitHub/scientific-Python projects;
2. identify useful equations, processing patterns, API/data-model ideas, visualization approaches and regression-test cases;
3. record licenses;
4. distinguish reference-only use from dependencies or copied/adapted implementation;
5. record decisions in the relevant Issue/module documentation and `REFERENCES.md` where safely maintained.

Permissive prior art is not copied automatically. GPL, mixed-provenance, missing-license or otherwise restrictive projects may be reference-only sources, but implementation reuse must respect license compatibility.

## Scientific and API guardrails

Across releases:

- units, reference states, normalization bases, sign conventions, fit windows, stoichiometry, constraints and denominator bases are explicit rather than inferred from display labels;
- numerical processing and visualization remain separate responsibilities;
- stable keys, not display labels, address sample/component-specific state;
- derived results retain deterministic source identity and sufficient analysis state to remain auditable;
- scientific incompatibilities fail explicitly rather than being silently aligned, converted, clipped, renormalized, smoothed or corrected;
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
- second review is performed after all fixes on the final exact head for scientific source changes;
- docs describe the behavior actually present in that head;
- behind=0, mergeable=true, unresolved review threads=0;
- merge uses the same head SHA that passed final CI/review.

After squash merge, re-read `main`. When connector visibility does not expose a main-push CI run, do not mislabel an older PR run as main CI evidence.

## Documentation roles

- [`../README.md`](../README.md): user-facing overview, installation, public capability summary and links.
- [`MASTER_PLAN.md`](MASTER_PLAN.md): project-wide execution order, checkpoint summary, governance and quality gates.
- [`ROADMAP.md`](ROADMAP.md): long-range release scope; not a per-commit log.
- [`V0_4_PLAN.md`](V0_4_PLAN.md): v0.4 dependency order, scientific/API boundaries and release handoff.
- [`V0_4_RELEASING.md`](V0_4_RELEASING.md): v0.4 Gate A/B/C procedure and release evidence.
- [`PEAK_FITTING.md`](PEAK_FITTING.md): reviewed shared-fitting contract.
- [`XPS.md`](XPS.md): reviewed XPS contract.
- [`EIS.md`](EIS.md): reviewed EIS contract.
- [`BET.md`](BET.md): reviewed quantitative BET contract.
- [`PRODUCT_CALIBRATION.md`](PRODUCT_CALIBRATION.md): reviewed product calibration/quantification contract and module-specific prior-art/license record.
- [`REFERENCES.md`](REFERENCES.md): long-lived prior-art reference survey.
- GitHub Issues: active acceptance criteria.
- GitHub Pull Requests: concrete diff, review evidence, CI state and merge decision.

## State-maintenance rule

After each merged scientific Issue, update only documentation whose statements became false or materially incomplete. Before starting any next phase, verify:

- live `main` HEAD;
- open Issues/PRs;
- current release plan;
- public capability claims;
- preceding Issue closure/completion;
- version/tag/publication boundaries.

Gate B / Issue #105 is the active v0.4 release stage. After Gate B merges and `main` is verified at `0.4.0`, execution must stop before Gate C until explicit authorization is given to create tag `v0.4.0`.
