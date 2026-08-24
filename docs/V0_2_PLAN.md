# v0.2 electrochemistry plan

v0.2 extends the reviewed v0.1 XY foundation into quantitative electrochemical analysis. New scientific modules must continue to follow the project rule: survey comparable open-source projects before implementation, record useful algorithms/architecture/tests/licenses, reuse mature dependencies where appropriate, and keep scientific calculations separate from visualization.

For the project-wide execution model, merge gates, and long-range release map, see [`MASTER_PLAN.md`](MASTER_PLAN.md). For release-hardening/final-version/tag rules, see [`V0_2_RELEASING.md`](V0_2_RELEASING.md).

## Current status

Checkpoint date: 2026-08-24.

- Current `main` checkpoint after Gate-A merge: `8bfea97d0c3d2f68cf05d0da7cd8bc857a555fb7`.
- **All planned v0.2 implementation Issues #19-#28 are complete and merged.**
- **Issue #43 / PR #44 Gate-A release hardening is complete.**
- There is no remaining open scientific feature Issue in the defined v0.2 sequence.
- **Active release target: Issue #45 — Gate-B final `0.2.0` version candidate and exact-wheel validation.**
- The Gate-B branch changes distribution/runtime version together to `0.2.0`; no `v0.2.0` tag is created by this step.
- The historical [`RELEASING.md`](RELEASING.md) governs v0.1 only; [`V0_2_RELEASING.md`](V0_2_RELEASING.md) defines the v0.2 Gate A/B/C sequence.

GitHub Issues, Pull Requests, merged `main`, and exact-commit CI remain authoritative if this status block becomes stale.

## Shared contracts and completed modules

The v0.2 implementation sequence established one integrated quantitative electrochemistry stack:

- #19 — shared quantity/unit/reference/provenance conventions.
- #20 — shared scatter and categorical bar visualization primitives.
- #21 — Tafel analysis and publication plotting.
- #22 — Faradaic efficiency and multi-product closure QA.
- #23 — product partial-current density and closure QA.
- #24 — catalyst-mass, metal-mass, and ECSA activity normalization.
- #25 — TOF and TOFapp with explicit inventory semantics.
- #26 — CV, Cdl, and ECSA analysis.
- #27 — electrochemical stability analysis.
- #28 — RRDE and Koutecky-Levich basics.

The reviewed LSV public API from v0.1 remains compatible and reuses the shared #19 quantity layer.

## Backlog map

- [x] #18 — v0.1 release hardening, quickstart examples, and API smoke gate.
- [x] #19 — shared electrochemistry quantity, unit, reference, and provenance conventions.
- [x] #20 — shared scatter and bar visualization primitives.
- [x] #21 — Tafel analysis and publication plotting.
- [x] #22 — Faradaic efficiency and multi-product closure QA.
- [x] #23 — product partial-current density and closure QA.
- [x] #24 — mass and specific activity normalization.
- [x] #25 — TOF and TOFapp.
- [x] #26 — CV, Cdl, and ECSA.
- [x] #27 — electrochemical stability analysis.
- [x] #28 — RRDE and Koutecky-Levich basics.
- [x] #43 — v0.2 Gate-A release hardening, installed public-API smoke expansion, and release-policy definition.
- [ ] **#45 — Gate-B final `0.2.0` version candidate and release validation.**

## Final implemented v0.2 scientific scope

### Shared electrochemistry foundation — #19

- conservative explicit-string unit conversion for potential, current/current density, charge, time, scan rate, area, mass/loading, amount/rate, and rotation rate;
- explicit reference-name handling and electron stoichiometry;
- deterministic `SourceDataRef`, `FitWindow`, and `AnalysisProvenance` contracts;
- numerical electrochemistry remains Matplotlib-lazy.

### Shared quantitative visualization — #20

- generic curve/scatter/bar rendering through the existing `FigureSpec` stack;
- stable-key styles and explicit-only uncertainty;
- compatibility guards for reference and normalization metadata;
- exact-size publication export remains shared rather than domain-specific.

### Tafel — #21

- explicit fit window, physical branch, and numeric current sign;
- signed slope/intercept/R² and immutable fit provenance;
- no automatic Tafel-region selection or mechanism inference.

### Faradaic efficiency — #22

- explicit amount/charge and rate/current formulations;
- caller-supplied electron number;
- multi-product closure QA without clipping or renormalization;
- stable product keys and source provenance.

### Partial current density — #23

- `j_product = FE_fraction * j_total` with explicit signed/magnitude behavior;
- exact condition-grid compatibility and no hidden interpolation;
- product-current closure QA without rescaling.

### Activity normalization — #24

- canonical total-current numerator;
- explicit `catalyst_mass`, `metal_mass`, and `ecsa` denominator bases;
- geometric current-density reconstruction only through explicit geometric area;
- double-normalization rejection and stable-key denominator mappings.

### TOF / TOFapp — #25

- active-site inventory is the only built-in basis that produces intrinsic TOF;
- total-metal or bulk inventory produces TOFapp;
- rate and product-partial-current routes with explicit electron number and sign mode;
- exact count-to-mol conversion and provenance-rich denominator semantics.

### CV / Cdl / ECSA — #26

- explicit caller-selected analysis potential and scan rates;
- anodic/cathodic sweep pairing and `Δj/2` Cdl fit semantics;
- no automatic declaration of a non-Faradaic region;
- ECSA requires explicit specific capacitance and basis/source description.

### Stability — #27

- explicit analysis, baseline, and final windows;
- signed/magnitude retention, linear drift, and missing-value policy;
- no hidden smoothing, outlier removal, baseline selection, or time reconstruction;
- `time_basis` compatibility prevents wall-clock/running-only durability traces from silently mixing.

### RRDE / Koutecky-Levich — #28

- explicit RRDE collection efficiency and current-mode semantics;
- exact disk/ring alignment with no interpolation;
- standard ORR-style apparent electron-number/peroxide equations without hidden clipping;
- rpm/rps/rad/s canonicalization to angular frequency;
- free-intercept K-L fit of reciprocal current versus `omega^-1/2`;
- apparent K-L electron number requires explicit transport constants and, for total current, explicit electrode area;
- no device-specific `N`, electrolyte constants, background processing, or reaction inference is hidden in the API.

## Cross-module invariants established by v0.2

The complete implementation now enforces these shared expectations:

- units, references, normalization bases, sign modes, fit windows, stoichiometry, and denominator bases are explicit;
- stable `Series.key` values, not display labels, address per-catalyst mappings and style state;
- deterministic source digests and analysis provenance accompany derived quantitative results;
- no scientific module silently interpolates, clips, renormalizes, flips signs, smooths, or guesses physical constants where that would alter meaning;
- plotting adapters consume already calculated values and reuse the shared visualization layer;
- incompatible reference/normalization/time/sign semantics fail before misleading overlays are created;
- installed-package smoke remains part of the CI merge gate.

## Required implementation order — completed

1. [x] #18 — v0.1 release hardening.
2. [x] #19 — electrochemistry quantity/unit/result foundation.
3. [x] #20 — shared scatter/bar rendering.
4. [x] #21 — Tafel.
5. [x] #22 — Faradaic efficiency.
6. [x] #23 — partial current density.
7. [x] #24 — mass/specific activity normalization.
8. [x] #25 — TOF/TOFapp.
9. [x] #26 — CV/Cdl/ECSA.
10. [x] #27 — stability analysis.
11. [x] #28 — RRDE/K-L basics.

The scientific sequence is complete. Repository issue/PR numbering is shared; release work continues through actual GitHub Issues rather than fabricating a numerical scientific continuation from #28.

## Mandatory feature loop

Any future scientific issue continues to follow:

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
    -> exact-head merge gate
    -> squash merge
    -> main CI verification when visible
    -> issue closure
```

Release-hardening/version-gate work uses the same exact-head discipline with release/API/packaging/version review in place of scientific-feature review.

## Completed release-hardening contract — #43 / Gate A

Gate A completed at `0.2.0.dev0` and established:

1. installed-wheel import provenance proving imports do not resolve from repository `src/`;
2. exact installed distribution/runtime version equality;
3. complete package-level `__all__` resolution with duplicate/empty export guards;
4. representative installed-wheel v0.2 calculations for Tafel, FE, product partial current, activity, TOF/TOFapp, Cdl/ECSA, stability, RRDE, and K-L using explicit scientific inputs/metadata;
5. retained LSV/XRD/Raman installed-wheel smoke and documented examples;
6. Ruff, full pytest, wheel build, fresh-environment installation, and `pip check`;
7. two-pass release/API/packaging review;
8. a reviewed Gate-A/Gate-B/Gate-C release policy in [`V0_2_RELEASING.md`](V0_2_RELEASING.md).

## Active final-version contract — #45 / Gate B

Gate B changes both version declarations together to `0.2.0` and must independently revalidate the final-version artifact. It requires:

1. `[project].version == catalysis_workbench.__version__ == "0.2.0"`;
2. a built `catalysis_workbench-0.2.0-*.whl`;
3. fresh-venv wheel install plus `pip check`;
4. complete installed public `__all__` resolution from the wheel, not repository `src/`;
5. the unchanged representative #21-#28 installed numerical smoke and LSV/XRD/Raman installed examples;
6. an explicit `[0.2.0] - 2026-08-24` changelog candidate entry and a fresh `[Unreleased]` section;
7. two-pass release/API/packaging/version review on the exact final-version head;
8. no scientific/API changes, no v0.3 feature work, no package publication, and no tag creation.

## Tag handoff — Gate C

Gate C is the separate tag operation. `v0.2.0` may be created only from the reviewed Gate-B `main` commit after explicit release authorization and changelog-date recheck. Merging Gate B is not itself tag authorization.

Package-registry publication remains a separate policy decision and is not implied by completing v0.2 features, Gate A/B, or by creating a Git tag.

## v0.3 transition boundary

Do not mix v0.3 feature implementation into the v0.2 final-version branch. The repository should complete the Gate-B transition and record the Gate-C decision before beginning v0.3 implementation from the reviewed `main` state.

## Status synchronization

After each merged issue or release gate, re-read `main`, open Issues/PRs, this plan, the README capability summary, changelog/version state, and relevant module documentation. Update only statements that became false or materially incomplete; long-range scope remains in [`ROADMAP.md`](ROADMAP.md).
