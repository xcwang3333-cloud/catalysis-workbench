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
- Current synchronized `main` checkpoint: `8bfea97d0c3d2f68cf05d0da7cd8bc857a555fb7` (`release: harden v0.2 installed API and release gates (#44)`).
- v0.1 scientific/common-XY foundation is released as v0.1.0.
- **All planned v0.2 implementation Issues #19-#28 are complete and merged.**
- **Gate A / Issue #43 is complete and merged through PR #44.**
- **Active target: Issue #45 — Gate-B final `0.2.0` version candidate and release validation.**
- The Gate-B branch changes distribution/runtime version together from `0.2.0.dev0` to `0.2.0` and must rerun the complete exact-head package/public-API gate.
- A `v0.2.0` Git tag remains a separate Gate-C operation after Gate B merges and requires explicit release authorization.

Live GitHub issue/PR state remains authoritative if this checkpoint becomes stale.

## Release map

The detailed release scope is maintained in [`ROADMAP.md`](ROADMAP.md). The intended progression is:

| Release | Primary scope | Planning state |
| --- | --- | --- |
| v0.1.x | common XY core, tabular I/O, reusable processing, LSV, XRD, Raman, publication curve rendering/export | complete/released foundation |
| v0.2.x | quantitative core electrochemistry and shared scatter/bar summaries | implementation + Gate A complete; Gate-B final-version candidate active |
| v0.3.x | extended experimental processing | planned |
| v0.4.x | advanced experimental analysis | planned |
| v0.5.x | XAS, structures, basic DFT energetics | planned |
| v0.6.x | electronic structure and catalysis thermodynamics | planned |
| v0.7.x | advanced computational visualization | planned |
| v0.8.x | operando and time-resolved analysis | planned |
| v0.9.x | reproducible batch workflows and first interactive editor | planned |
| v1.0.0 | stable personal catalysis data workbench and local GUI | planned |

Release numbering is a planning boundary, not permission to weaken scientific validation or compatibility requirements.

## v0.2 execution status

The detailed v0.2 scientific contract is maintained in [`V0_2_PLAN.md`](V0_2_PLAN.md), and the release procedure is maintained separately in [`V0_2_RELEASING.md`](V0_2_RELEASING.md).

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

### Active final-version target — #45 / Gate B

Issue #45 owns the final-version candidate. Its scope is intentionally narrow:

1. change both version declarations together from `0.2.0.dev0` to `0.2.0`;
2. establish the `[0.2.0] - 2026-08-24` changelog candidate entry while retaining a fresh `[Unreleased]` section;
3. rerun Ruff, full pytest, wheel build, fresh-environment install, `pip check`, installed public-API smoke, representative #21-#28 numerical smoke, and documented LSV/XRD/Raman examples against the final-version wheel;
4. verify the built distribution and runtime version both report exactly `0.2.0`;
5. perform two-pass release/API/packaging/version review on the exact head;
6. keep scientific algorithms, public APIs, v0.3 work, package-registry publication, and Git tagging out of the Gate-B PR.

Only after Gate B is reviewed, merged, and rechecked on `main` may Gate C be considered. Merging Gate B does not itself create `v0.2.0`.

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
- [`V0_2_PLAN.md`](V0_2_PLAN.md): v0.2 dependency graph, issue-level status, scientific scope, and implementation/release handoff.
- [`V0_2_RELEASING.md`](V0_2_RELEASING.md): v0.2 release-hardening, final-version, tag, and package-distribution boundaries.
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

Complete Issue #45 on `release/v0.2-final` created exactly from `main=8bfea97d0c3d2f68cf05d0da7cd8bc857a555fb7`: validate the synchronized `0.2.0` source/runtime version, build and smoke-test the final-version wheel in a fresh environment, perform two-pass release/API/packaging/version review, then use the exact-head Ready/merge gate. Do not create `v0.2.0` or publish a package during Gate B; Gate C remains separately authorized.
