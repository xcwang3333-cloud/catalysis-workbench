# v0.2 electrochemistry plan

v0.2 extends the reviewed v0.1 XY foundation into quantitative electrochemical analysis. New scientific modules must continue to follow the project rule: survey comparable open-source projects before implementation, record useful algorithms/architecture/tests/licenses, reuse mature dependencies where appropriate, and keep scientific calculations separate from visualization.

For the project-wide execution model, merge gates, and long-range release map, see [`MASTER_PLAN.md`](MASTER_PLAN.md).

## Current status

Checkpoint date: 2026-08-24.

- Feature checkpoint used for this synchronization: `ecdc033212d2f9b91dfb0505528f743df625524f`.
- Completed: #18, #19, #20, #21, #22, #23.
- Current implementation target: **#24 — mass and specific activity normalization**.
- Remaining after #24: #25, #26, #27, #28.

GitHub Issues, Pull Requests, merged `main`, and exact-commit CI remain authoritative if this status block becomes stale.

## Shared contracts first

Before domain modules proliferate, v0.2 centralizes conservative electrochemistry quantity validation and traceable fit/result conventions. That foundation is now implemented by #19, and the reviewed LSV public API remains compatible. Units remain explicit strings in v0.2; Pint is still deferred.

The visualization layer also now provides generic scatter and categorical bar rendering through #20, reusing the existing `FigureSpec` layout/typography/export state. Domain modules must continue to reuse that shared visualization system rather than creating separate Matplotlib style stacks.

## Backlog map

- [x] #18 — v0.1 release hardening, quickstart examples, and API smoke gate.
- [x] #19 — shared electrochemistry quantity, unit, reference, and provenance conventions.
- [x] #20 — shared scatter and bar visualization primitives.
- [x] #21 — Tafel analysis and publication plotting.
- [x] #22 — Faradaic efficiency and multi-product closure QA.
- [x] #23 — product partial-current density and closure QA.
- [ ] **#24 — mass and specific activity normalization.**
- [ ] #25 — TOF and TOFapp.
- [ ] #26 — CV, Cdl, and ECSA.
- [ ] #27 — electrochemical stability analysis.
- [ ] #28 — RRDE and Koutecky-Levich basics.

## Implemented v0.2 foundation

The completed sequence #19-#23 establishes reusable contracts that later modules should consume rather than duplicate:

- #19: explicit electrochemistry quantities/units, reference handling, source digests, fit-window/provenance types, and v0.1 LSV compatibility.
- #20: shared curve/scatter/bar publication rendering, stable-key styling, explicit supplied errors, and common exact-size figure/export behavior.
- #21: explicit Tafel fit windows, branch/current-sign declarations, signed slope/intercept/R², stable-key Dataset fitting, and traceable fit provenance.
- #22: amount/charge and rate/current Faradaic efficiency with explicit electron stoichiometry, multi-product stable-key workflows, and closure QA without clipping or renormalization.
- #23: product partial-current density from explicit FE and total current density, signed/magnitude modes, exact condition compatibility, deterministic source provenance, and diagnostic closure QA.

## Current target: #24 mass and specific activity normalization

Issue #24 is the next coding target and must begin with a fresh prior-art scan before implementation.

Core scientific requirements:

- numerator semantics must be explicit; total current and current density may only be converted when the dimensional path is declared;
- denominator basis must be explicit and recorded, including catalyst mass, active-metal mass, ECSA, or another caller-declared supported basis;
- built-in v0.2 focus is catalyst-mass activity, metal-mass activity, and ECSA-specific activity;
- no denominator is inferred from sample labels or hidden metadata;
- units must be conservatively validated/converted through the shared #19 quantity layer where applicable;
- current sign is preserved unless magnitude output is explicitly requested;
- double normalization must fail explicitly;
- output axis/provenance metadata must distinguish normalization bases sufficiently for shared renderer compatibility checks;
- Dataset-level denominators must be addressed by stable `Series.key`, not display labels;
- curve/bar plotting must remain a thin adapter over the shared visualization layer from #20.

The prior-art review should record relevant equations, API/data-model ideas, validation/test patterns, visualization/reporting conventions, and licenses in [`REFERENCES.md`](REFERENCES.md) and the module-specific documentation created for #24.

## Domain scope

- Tafel: explicit fit windows/branches, log-current handling, slope/intercept/fit-quality provenance. **Implemented in #21.**
- Faradaic efficiency: explicit charge/electron stoichiometry and product amount/rate inputs; no raw chromatogram calibration yet. **Implemented in #22.**
- Partial current density: explicit FE fraction and signed/magnitude convention. **Implemented in #23.**
- Mass/specific activity: explicit denominator basis (catalyst mass, metal mass, ECSA, or another caller-declared basis). **Current #24 target.**
- TOF/TOFapp: explicit electron number and site/metal inventory; total-metal normalization is `TOFapp` unless an active-site inventory is genuinely supplied.
- CV/Cdl/ECSA: explicit scan rates/non-Faradaic window, Cdl fitting, and caller-supplied specific capacitance for ECSA conversion.
- Stability: chronoamperometry/chronopotentiometry retention, drift, and interval summaries without hiding sign or reference semantics.
- RRDE/K-L: explicit collection efficiency, rotation units, electron-number/peroxide equations, and Koutecky-Levich fitting inputs/constants.

## Required implementation order

1. [x] #18 — finish the v0.1 release gate before changing the public API further.
2. [x] #19 — centralize electrochemistry quantity/unit/result conventions.
3. [x] #20 — add shared scatter/bar rendering so domain modules do not fork visualization.
4. [x] #21 — Tafel; it exercises fit-result conventions directly on the existing LSV foundation.
5. [x] #22 — Faradaic efficiency.
6. [x] #23 — partial current density, reusing FE semantics.
7. [ ] **#24 — mass/specific activity normalization.**
8. [ ] #25 — TOF/TOFapp, reusing product-current and denominator provenance.
9. [ ] #26 — CV/Cdl/ECSA.
10. [ ] #27 — stability analysis.
11. [ ] #28 — RRDE/K-L basics.

Do not skip ahead in this sequence unless a dependency review explicitly changes the plan in GitHub first.

## Dependencies between modules

Faradaic efficiency precedes product partial-current helpers. Activity and TOF should reuse the same current/product and denominator-provenance conventions rather than each inventing unit parsing. #24 should reuse #19 quantity/provenance semantics, #20 rendering, and #23 current-basis/sign conventions where they are scientifically applicable. #25 should then reuse #23 product current plus the denominator-provenance conventions established by #24 where appropriate.

CV/Cdl/ECSA and RRDE/K-L can proceed after the shared electrochemistry foundation because they have fewer dependencies on FE/product metrics, but the planned execution order remains #24 -> #25 -> #26 -> #27 -> #28.

## Mandatory feature loop

Every remaining v0.2 issue follows:

```text
prior-art scan
    -> implementation/tests
    -> CI
    -> Draft PR
    -> scientific/API/compatibility review
    -> fixes
    -> CI
    -> second review
    -> Ready
    -> merge gate
    -> squash merge
    -> main CI
    -> issue closure
```

The first review is not the final approval if it produced fixes. A second formal review must examine the corrected head SHA before the PR becomes Ready.

## Status synchronization

After each merged v0.2 issue, re-read `main`, open Issues/PRs, this plan, the README capability summary, and relevant module documentation before starting the next feature. Update only statements that became false or materially incomplete; long-range scope remains in [`ROADMAP.md`](ROADMAP.md).
