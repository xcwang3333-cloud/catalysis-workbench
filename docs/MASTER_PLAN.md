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
- Current reviewed `main` checkpoint after thermal merge: `d06d4459955d50801ed7676326efcecdccb6df73` (`feat: add explicit TGA DTG TPR TPD thermal analysis (#55)`).
- FTIR feature merge commit: `bf6e834b584943747b8dcb5278141e8ca0c5512f` (`feat: add explicit FTIR and ATR-FTIR processing (#51)`).
- `v0.2.0` tagged release commit: `1f7f4057397c61ef2f771b96fceadc8a529b62d9` (`release: finalize v0.2.0 candidate (#46)`).
- v0.1 scientific/common-XY foundation is released as `v0.1.0`.
- **All planned v0.2 implementation Issues #19-#28 are complete and merged.**
- **Gate A / Issue #43 / PR #44 is complete.**
- **Gate B / Issue #45 / PR #46 is complete.**
- **Gate C / Issue #47 is complete: tag `v0.2.0` was explicitly authorized, created, and verified identical to the tagged release commit.**
- Distribution metadata and runtime `__version__` at the tagged release both report `0.2.0`; changelog release date is 2026-08-24.
- Package-registry publication remains a separate policy decision and was not part of the v0.2 Git release.
- Issue #48 / PR #49 completed the post-v0.2-release documentation synchronization; it did not change the tagged release contents.
- **v0.3 development is active: Issue #50 / PR #51 completed FTIR / ATR-FTIR, and Issue #54 / PR #55 completed the TGA / DTG / TPR / TPD thermal-analysis foundation.**
- Issue #52 / PR #53 synchronized the first v0.3 FTIR checkpoint.
- Issue #56 is the docs-only post-thermal synchronization and planning checkpoint; it changes no scientific implementation or version metadata.
- **Basic BET / gas-sorption plotting is selected as the next v0.3 scientific module.** ICP/composition integration and shared peak-fitting primitives remain later v0.3 scope.

Live GitHub issue/PR/tag state remains authoritative if this checkpoint becomes stale.

## Release map

The detailed release scope is maintained in [`ROADMAP.md`](ROADMAP.md). The intended progression is:

| Release | Primary scope | Planning state |
| --- | --- | --- |
| v0.1.x | common XY core, tabular I/O, reusable processing, LSV, XRD, Raman, publication curve rendering/export | complete/released as v0.1.0 |
| v0.2.x | quantitative core electrochemistry and shared scatter/bar summaries | complete/released as v0.2.0 on 2026-08-24 |
| v0.3.x | extended experimental processing | in progress — FTIR/ATR-FTIR and thermal analysis complete; basic BET/gas-sorption plotting selected next |
| v0.4.x | advanced experimental analysis | planned |
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

No scientific/API implementation change belongs in post-release documentation synchronization. v0.2 is operationally closed; new development proceeds on top of the reviewed post-release `main` baseline without moving the `v0.2.0` tag.

## v0.3 execution status

v0.3 extends experimental characterization while retaining the same explicit scientific-contract and exact-head review discipline. Package/runtime version remains `0.2.0` during this development work unless a separate reviewed release gate later changes it.

### Completed

- #50 / PR #51 — FTIR / ATR-FTIR validation and processing; explicit transmittance-to-absorbance conversion; caller-window polynomial baseline fitting; direction-independent direct-window band integration; stable-key Dataset workflows; shared publication plotting; prior-art/license documentation; installed-wheel smoke and quickstart.
- #54 / PR #55 — TGA / DTG / TPR / TPD thermal-analysis foundation; explicit °C/K temperature semantics/conversion; raw-mass versus normalized TGA bases; explicit reference-mass normalization; measured-grid DTG with explicit sign convention; TPR/TPD detector-signal semantics; measured-point-supported thermal-window extrema/integration; stable-key Dataset workflows; compatibility guards; provenance; lazy shared publication plotting; installed-wheel smoke and quickstart.

### Documentation checkpoints

- #52 / PR #53 — docs-only synchronization after the merged FTIR module.
- #56 — docs-only synchronization after the thermal merge plus next-module priority decision. It does not alter scientific code, version metadata, tags, or release state.

### Remaining roadmap scope and priority

1. **Basic BET / gas-sorption plotting — selected next.** The v0.3 contract should establish explicit relative-pressure (`P/P0`), adsorbed-quantity, adsorption/desorption branch, unit, provenance, overlay, and publication-plot semantics without prematurely implementing quantitative BET fitting.
2. ICP/composition data integration — planned after the basic sorption layer unless a later explicit planning decision changes the order.
3. Shared peak-fitting primitives — planned later in v0.3; this is cross-cutting and should be designed around concrete downstream needs rather than pulled forward without a scientific consumer.

Quantitative BET fitting remains v0.4 scope. The next scientific Issue must begin with a prior-art/license survey before locking its API contract.

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
- [`V0_2_RELEASING.md`](V0_2_RELEASING.md): v0.2 release-hardening, final-version, tag, and package-distribution boundaries plus completed release record.
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

## Immediate next action

Complete Issue #56 as a docs-only status synchronization. After its exact-head CI/review/merge gate, open the next v0.3 scientific Issue for **basic BET / gas-sorption plotting**, beginning with a fresh prior-art/license survey and an explicit scientific/API contract. Do not include quantitative BET fitting or other v0.4 algorithms unless separately planned and reviewed.
