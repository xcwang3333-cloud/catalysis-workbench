# CatalysisWorkbench Master Plan

This document is the project-level execution map for CatalysisWorkbench. It connects the long-range release roadmap to the active GitHub issue sequence, scientific/API quality gates, documentation responsibilities, and the rule that repository state is authoritative.

## Authority and source of truth

GitHub is the only operational source of truth for project state.

When documents and live repository state disagree, use this precedence order:

1. merged `main` code and tests;
2. current GitHub Issues and Pull Requests;
3. CI status for the exact commit under review;
4. this master plan and release-specific planning documents;
5. README summaries and other descriptive documentation.

Planning documents must be corrected when they drift from merged reality. They do not override code, issue state, review findings, or CI.

## Current checkpoint

Checkpoint date: 2026-08-24.

- Repository: `xcwang3333-cloud/catalysis-workbench`.
- Stable integration branch: `main`.
- Reviewed post-v0.3 documentation baseline on `main`: `112c3c29fc8dcbfbf70f384baaba3f66fc1429f1` (`docs: synchronize post-release v0.3.0 state (#72)`).
- `v0.3.0` tagged release commit: `845ac4c15d399a8816c7ba66d61ea6ec4cc11293` (`release: finalize v0.3.0 candidate (#69)`).
- `v0.2.0` tagged release commit: `1f7f4057397c61ef2f771b96fceadc8a529b62d9` (`release: finalize v0.2.0 candidate (#46)`).
- v0.1 scientific/common-XY foundation is released as `v0.1.0`.
- **All planned v0.2 implementation Issues #19-#28 are complete and merged.**
- **v0.2 Gate A / Issue #43 / PR #44, Gate B / Issue #45 / PR #46, and Gate C / Issue #47 are complete.**
- Issue #48 / PR #49 completed the post-v0.2-release documentation synchronization without changing the tagged release contents.
- **The frozen v0.3 scientific scope is complete:** Issue #50 / PR #51 delivered FTIR / ATR-FTIR, Issue #54 / PR #55 delivered TGA / DTG / TPR / TPD, Issue #58 / PR #59 delivered basic gas sorption, and Issue #62 / PR #63 delivered ICP/elemental-composition integration.
- Issue #52 / PR #53 synchronized the first v0.3 FTIR checkpoint.
- Issue #56 / PR #57 synchronized the post-thermal checkpoint and selected gas sorption next.
- Issue #60 / PR #61 synchronized the post-sorption checkpoint and selected ICP/composition next.
- Issue #64 / PR #65 synchronized the post-ICP checkpoint without changing scientific code, API, tests, or version metadata.
- **The v0.3 scope decision is complete:** shared peak-fitting was deferred to v0.4 for joint design with constrained XPS/spectroscopy consumers.
- **v0.3 Gate A / Issue #66 / PR #67 is complete** at merge commit `8a3ae75f43ffa7d808f2a431f6326912a5dff9c6`; it hardened the frozen scope while intentionally retaining package/runtime version `0.2.0`.
- **v0.3 Gate B / Issue #68 / PR #69 is complete** at merge commit `845ac4c15d399a8816c7ba66d61ea6ec4cc11293`; it synchronized distribution/runtime version to `0.3.0` and passed the exact-wheel release audit plus two-pass release review.
- **v0.3 Gate C / Issue #70 is complete:** tag `v0.3.0` was explicitly authorized, created, and reverse-verified to resolve exactly to `845ac4c15d399a8816c7ba66d61ea6ec4cc11293`.
- Distribution metadata and runtime `__version__` at the tagged v0.3 release both report `0.3.0`; changelog release date is 2026-08-24.
- Issue #71 / PR #72 completed post-v0.3-release documentation synchronization at `112c3c29fc8dcbfbf70f384baaba3f66fc1429f1` without moving the `v0.3.0` tag.
- **Active project boundary: Issue #73 — v0.4 shared constrained peak-fitting + XPS architecture.** It is docs/planning only and starts from the reviewed post-v0.3 baseline.
- Package-registry publication remains a separate explicit policy decision and has not been performed.

Live GitHub issue/PR/tag state remains authoritative if this checkpoint becomes stale.

## Release map

The detailed release scope is maintained in [`ROADMAP.md`](ROADMAP.md). The intended progression is:

| Release | Primary scope | Planning state |
| --- | --- | --- |
| v0.1.x | common XY core, tabular I/O, reusable processing, LSV, XRD, Raman, publication curve rendering/export | complete/released as v0.1.0 |
| v0.2.x | quantitative core electrochemistry and shared scatter/bar summaries | complete/released as v0.2.0 on 2026-08-24 |
| v0.3.x | extended experimental processing | complete/released as v0.3.0 on 2026-08-24 |
| v0.4.x | advanced experimental analysis | architecture active through #73 — shared constrained peak-fitting + XPS first, then XPS plotting, EIS, quantitative BET and product calibration |
| v0.5.x | XAS, structures, basic DFT energetics | planned |
| v0.6.x | electronic structure and catalysis thermodynamics | planned |
| v0.7.x | advanced computational visualization | planned |
| v0.8.x | operando and time-resolved analysis | planned |
| v0.9.x | reproducible batch workflows and first interactive editor | planned |
| v1.0.0 | stable personal catalysis data workbench and local GUI | planned |

Release numbering is a planning boundary, not permission to weaken scientific validation or compatibility requirements.

## v0.2 execution status

The detailed v0.2 scientific contract and completed issue sequence are maintained in [`V0_2_PLAN.md`](V0_2_PLAN.md), and the completed release procedure is maintained separately in [`V0_2_RELEASING.md`](V0_2_RELEASING.md).

### Completed foundations and modules

- #18 — v0.1 release hardening, quickstarts, and installed-package smoke gate.
- #19 — shared electrochemistry quantity/unit/reference/provenance foundation.
- #20 — shared scatter and categorical bar visualization primitives.
- #21 — explicit Tafel analysis and publication plotting.
- #22 — explicit Faradaic efficiency plus multi-product closure QA.
- #23 — explicit product partial-current density plus closure QA.
- #24 — explicit catalyst-mass, metal-mass, and ECSA activity normalization.
- #25 — explicit TOF versus TOFapp analysis.
- #26 — CV, Cdl, and ECSA analysis with explicit specific-capacitance basis.
- #27 — explicit electrochemical stability analysis.
- #28 — RRDE and Koutecky-Levich basics.
- PR #42 — completion-state documentation synchronization.
- #43 / PR #44 — Gate-A release hardening, full installed-wheel public-API audit, representative #21-#28 numerical smoke, and v0.2 Gate A/B/C release-policy definition.
- #45 / PR #46 — Gate-B final version `0.2.0`, exact-wheel validation, two-pass release/API/packaging/version review, and merge.
- #47 — Gate-C explicit release authorization, `v0.2.0` tag creation, and exact-target verification.
- #48 / PR #49 — post-release documentation synchronization; no change to the tagged release commit.

### Released v0.2 baseline

`v0.2.0` is the reviewed baseline for the complete quantitative core electrochemistry scope. Gate-B CI built `catalysis_workbench-0.2.0-py3-none-any.whl`, installed it into a fresh virtual environment, passed `pip check`, complete public `__all__` resolution, representative #21-#28 numerical smoke, and the installed LSV/XRD/Raman examples. Gate C subsequently verified the tag is identical to the reviewed release commit.

No scientific/API implementation change belongs in post-release documentation synchronization. v0.2 is operationally closed; later development proceeds without moving the `v0.2.0` tag.

## v0.3 execution status

v0.3 extends experimental characterization while retaining the same explicit scientific-contract and exact-head review discipline. The scientific scope is frozen and the Git release is complete as `v0.3.0`. The completed release procedure and evidence are maintained in [`V0_3_RELEASING.md`](V0_3_RELEASING.md).

### Completed scientific modules

- #50 / PR #51 — FTIR / ATR-FTIR validation and processing; explicit transmittance-to-absorbance conversion; caller-window polynomial baseline fitting; direction-independent direct-window band integration; stable-key Dataset workflows; shared publication plotting; prior-art/license documentation; installed-wheel smoke and quickstart.
- #54 / PR #55 — TGA / DTG / TPR / TPD thermal-analysis foundation; explicit °C/K temperature semantics/conversion; raw-mass versus normalized TGA bases; explicit reference-mass normalization; measured-grid DTG with explicit sign convention; TPR/TPD detector-signal semantics; measured-point-supported thermal-window extrema/integration; stable-key Dataset workflows; compatibility guards; provenance; lazy shared publication plotting; installed-wheel smoke and quickstart.
- #58 / PR #59 — basic gas-sorption isotherm semantics and publication plotting; explicit `P/P0` fraction/percent representation; explicit loading units and adsorbate/temperature/branch state; explicit standard-gas conditions for `cm^3(STP)/g`; no branch inference from pressure direction; stable-key Dataset processing; measured-point-only window summaries; strict compatibility guards; lazy shared publication plotting; installed-wheel smoke and quickstart.
- #62 / PR #63 — ICP/elemental-composition scalar data integration; immutable composition measurement/table objects; explicit bulk-mass-fraction versus solution-concentration bases and units; explicit solution-to-bulk digestion/dilution mass balance; deterministic tidy CSV/Excel import; explicit replicate mean/sample-SD/RSD summaries; no hidden closure normalization or unit conversion; shared grouped-bar publication plotting; installed-wheel smoke and quickstart.

### Documentation checkpoints

- #52 / PR #53 — docs-only synchronization after the merged FTIR module.
- #56 / PR #57 — docs-only synchronization after the thermal merge plus gas-sorption priority decision.
- #60 / PR #61 — docs-only synchronization after the gas-sorption merge plus ICP/composition priority decision.
- #64 / PR #65 — docs-only synchronization after the ICP/composition merge and explicit handoff to the release decision.
- #71 / PR #72 — post-release documentation synchronization after the verified `v0.3.0` tag; no tagged contents changed.

### Released v0.3 baseline and v0.4 handoff

- Shared peak-fitting is **not** part of v0.3. It moved to v0.4, where model families, baseline/background coupling, parameter constraints/ties, uncertainty/covariance semantics and provenance are designed with constrained XPS/spectroscopy as a concrete downstream consumer.
- Quantitative BET fitting remains v0.4 scope.
- Gate A / Issue #66 / PR #67 completed installed-wheel/API hardening on the frozen scope while version remained `0.2.0`.
- Gate B / Issue #68 / PR #69 finalized distribution/runtime version `0.3.0`, built and installed the exact wheel, passed the unified v0.3 numerical smoke and all seven quickstarts, and completed two-pass release review.
- Gate C / Issue #70 separately authorized and verified tag `v0.3.0` exactly on `845ac4c15d399a8816c7ba66d61ea6ec4cc11293`.
- Package-registry publication remains outside the Git release gate.

## v0.4 architecture and execution status

The detailed v0.4 dependency graph and first scientific/API contracts are maintained in [`V0_4_PLAN.md`](V0_4_PLAN.md).

### Active architecture checkpoint

Issue #73 defines the shared constrained-fitting/XPS architecture before implementation begins.

- `lmfit/lmfit-py` is the preferred nonlinear-fitting backend candidate after BSD-3-Clause verification; no runtime dependency is added by the architecture-only checkpoint.
- the shared fitting layer owns explicit parameter/component/fit/result state, stable keys, bounded/tied parameters, deterministic provenance, residual/statistical output and explicit uncertainty availability;
- the shared layer does **not** choose peaks, component count, smoothing, normalization, baseline/background or chemical assignments;
- XPS owns binding-energy semantics, energy correction, XPS backgrounds and doublet-domain constraints;
- initial doublet separation/ratio/width ties are caller supplied, not silently looked up from element/orbital labels;
- general spectroscopy baselines and XPS backgrounds remain distinct responsibilities; initial XPS work may contract linear/Shirley backgrounds, while Tougaard requires separate scientific scope;
- numerical fitting and XPS preprocessing remain separate from the lazy publication-rendering adapter;
- runtime/distribution version remains `0.3.0` during ordinary architecture/feature work until a later explicit release gate.

### Planned v0.4 sequence

1. shared constrained peak-fitting foundation and lmfit integration;
2. XPS semantics, energy correction and background preparation;
3. constrained XPS components/doublets and shared-fit integration;
4. XPS publication plotting and fit diagnostics;
5. EIS plotting and basic equivalent-circuit fitting;
6. quantitative BET fitting;
7. product-calibration / GC-HPLC-NMR quantification foundation;
8. completion-state synchronization and later release gates.

Each implementation Issue still requires a fresh prior-art/license refresh, hand-verifiable scientific regressions, exact-head CI and two-pass review.

## Mandatory development loop

Every new scientific feature follows the same merge path:

```text
prior-art scan
    -> implementation + regression tests
    -> CI
    -> Draft PR
    -> scientific/API/compatibility review
    -> direct fixes on the feature branch
    -> CI
    -> second formal review
    -> Ready for review
    -> merge gate
    -> squash merge
    -> main CI verification
    -> issue closure
```

A feature is not complete because code exists or local tests pass. Completion requires the reviewed branch to satisfy the scientific contract, public API/compatibility expectations, CI, documentation, and issue acceptance criteria.

For release-hardening or version-gate work, use the same exact-head discipline but replace scientific-feature review with release/API/packaging/version review as appropriate.

## Prior-art rule

Before coding a new scientific or visualization feature:

1. survey comparable open-source GitHub projects;
2. identify useful equations, data-processing patterns, API/data-model ideas, visualization approaches, and regression-test cases;
3. record the license of each relevant project;
4. distinguish architecture/reference-only use from dependencies or copied/adapted implementation;
5. record the decisions in [`REFERENCES.md`](REFERENCES.md) and, where appropriate, the module-specific scientific document and issue body.

Permissive prior art is not copied automatically. GPL or otherwise restrictive projects may be useful reference-only sources, but implementation reuse must respect license compatibility.

## Scientific and API guardrails

Across releases, scientific modules should preserve these project invariants:

- units, reference electrodes, normalization bases, sign conventions, fit windows, stoichiometry, and denominator bases are explicit rather than inferred from labels;
- numerical processing and visualization remain separate layers;
- `Series.key`, not a display label, is the stable address for catalyst/replicate-specific mappings;
- provenance records enough source identity and analysis state to make derived results traceable;
- scientific incompatibilities fail explicitly rather than being silently aligned, converted, clipped, renormalized, smoothed, or corrected;
- shared primitives are extended centrally instead of creating technique-specific duplicate stacks;
- public import surfaces remain deliberate and installed-package smoke tests protect them;
- existing reviewed behavior remains compatible unless a deliberate breaking change is separately planned and reviewed.

## Merge gate

Before a PR may be marked Ready and squash-merged, confirm at minimum:

- issue/scope and acceptance criteria are satisfied;
- prior-art and license decisions are recorded when the PR adds functionality;
- regression tests cover hand-verifiable scientific behavior and explicit failure modes where applicable;
- Ruff and the full pytest suite pass;
- packaging/installed public-API smoke checks pass when exercised by CI;
- scientific/API/compatibility or release/API/packaging review has no unresolved blocking findings;
- the second review is performed after fixes, not assumed from the first review;
- documentation describes the final behavior actually present in the reviewed head;
- the PR head SHA used by the merge gate is the head that passed review and CI.

After squash merge, verify `main` CI when visible and only then close the implementation issue as completed if the PR did not close it automatically. When `main` push CI is not exposed by the connector, do not substitute or mislabel an older PR run as `main` CI evidence.

## Documentation roles

To reduce status drift, each document has a narrow responsibility:

- [`../README.md`](../README.md): user-facing project overview, installation, quickstart, public capability summary, and links to deeper plans.
- [`MASTER_PLAN.md`](MASTER_PLAN.md): project-wide execution order, live checkpoint summary, governance, and quality gates.
- [`ROADMAP.md`](ROADMAP.md): long-range release scope from v0.1 through v1.0; it is not a per-issue progress tracker.
- [`V0_2_PLAN.md`](V0_2_PLAN.md): v0.2 dependency graph, issue-level status, scientific scope, and completed release handoff.
- [`V0_2_RELEASING.md`](V0_2_RELEASING.md): completed v0.2 release-hardening, final-version, tag, and package-distribution boundaries.
- [`V0_3_RELEASING.md`](V0_3_RELEASING.md): completed v0.3 frozen-scope hardening, final-version, tag verification, and package-distribution boundary record.
- [`V0_4_PLAN.md`](V0_4_PLAN.md): active v0.4 dependency order, shared constrained-fitting/XPS architecture and implementation boundaries.
- [`RELEASING.md`](RELEASING.md): historical v0.1 release policy.
- [`REFERENCES.md`](REFERENCES.md): prior-art projects, useful ideas, and license decisions.
- module-specific documents: exact scientific/API contracts for implemented modules.
- GitHub Issues: acceptance criteria and active feature/release contract.
- GitHub Pull Requests: concrete implementation diff, review record, CI state, and merge decision.

## State-maintenance rule

After each merged issue, update only the documents whose statements became false or materially incomplete. Do not churn the entire roadmap after every PR.

At a minimum, before starting the next feature or release stage, verify:

- `main` HEAD and visible CI state;
- open Issues and PRs;
- the current release plan;
- README capability claims;
- whether the prior issue is actually closed/completed;
- whether a final-version/tag policy exists for the release being closed.

This lightweight resynchronization is the required checkpoint between feature/release loops.

## Release sequence from this checkpoint

The v0.3 Git release and post-release synchronization are complete. Issue #73 is the active v0.4 architecture checkpoint and must merge before the first shared fitting implementation Issue begins. After #73, implementation proceeds in the dependency order defined in `V0_4_PLAN.md`, beginning with the shared constrained peak-fitting foundation. Package-registry publication remains a separate explicit policy decision and is not implied by v0.4 development.