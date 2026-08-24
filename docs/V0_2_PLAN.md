# v0.2 electrochemistry plan

v0.2 extends the reviewed v0.1 XY foundation into quantitative electrochemical analysis. New scientific modules must continue to follow the project rule: survey comparable open-source projects before implementation, record useful algorithms/architecture/tests/licenses, reuse mature dependencies where appropriate, and keep scientific calculations separate from visualization.

For the project-wide execution model, merge gates, and long-range release map, see [`MASTER_PLAN.md`](MASTER_PLAN.md). For release-hardening/final-version/tag rules, see [`V0_2_RELEASING.md`](V0_2_RELEASING.md).

## Current status

Checkpoint date: 2026-08-24.

- Synchronized `main` checkpoint after the feature-completion documentation pass: `27f52d65a5c700f46163a0eb2a7481eeb2480f8c`.
- **All planned v0.2 implementation Issues #19-#28 are complete and merged.**
- The development version remains `0.2.0.dev0` in both distribution metadata and runtime version state.
- There is no remaining open scientific feature Issue in the defined v0.2 sequence.
- **Active release target: Issue #43 — release hardening, public API audit, and final-version gate definition.**
- Issue #43 strengthens installed-wheel validation and release policy while deliberately retaining `0.2.0.dev0`.
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
- [ ] **#43 — v0.2 release hardening, installed public-API smoke expansion, and final-version gate definition.**

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

The scientific sequence is complete. Repository issue/PR numbering is shared, so do not fabricate a numerical continuation from #28; the next real contract is Issue #43.

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

## Active release-hardening contract — #43 / Gate A

Feature completion does **not** itself create a release. Issue #43 is the Gate-A hardening step and must leave the package at `0.2.0.dev0`.

Gate A requires:

1. installed-wheel import provenance proving imports do not resolve from repository `src/`;
2. exact installed distribution/runtime version equality;
3. complete package-level `__all__` resolution with duplicate/empty export guards;
4. representative installed-wheel v0.2 calculations for Tafel, FE, activity, TOF/TOFapp, Cdl/ECSA, stability, RRDE, and K-L using explicit scientific inputs/metadata;
5. retained v0.1 LSV/XRD/Raman installed-wheel smoke and documented examples;
6. Ruff, full pytest, wheel build, fresh environment installation, and `pip check`;
7. release/API/packaging review of the exact head;
8. no scientific algorithm changes, no final version bump, and no tag.

## Final version and tag handoff — Gate B / Gate C

Only after Issue #43/Gate A is completed may a separate Gate-B version candidate be considered. Gate B changes both version declarations together to `0.2.0`, reruns the complete final-version CI/wheel smoke, and receives formal release/API/packaging/version review.

Gate C is the separate tag operation. `v0.2.0` may be created only from the reviewed Gate-B `main` commit after an explicit release authorization and changelog-date recheck.

Package-registry publication remains a separate policy decision and is not implied by completing v0.2 features, Gate A/B, or by creating a Git tag.

## v0.3 transition boundary

Do not mix v0.3 feature implementation into Issue #43 or a v0.2 final-version branch. The repository should first record whether v0.2 is being finalized through Gate B/C or intentionally retained as a development checkpoint. Once that transition is explicit, v0.3 issues can be opened from the appropriate reviewed `main` state.

## Status synchronization

After each merged issue or release gate, re-read `main`, open Issues/PRs, this plan, the README capability summary, changelog/version state, and relevant module documentation. Update only statements that became false or materially incomplete; long-range scope remains in [`ROADMAP.md`](ROADMAP.md).
