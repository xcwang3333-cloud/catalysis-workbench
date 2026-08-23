# v0.1 completion audit

Date: 2026-08-23

## Functional status

The v0.1 common-XY roadmap is function-complete on `main`:

- immutable-style `Axis` / `Series` / ordered `Dataset` core models;
- Excel / CSV / TXT tabular ingestion with stable Series keys and source provenance;
- shared crop, normalize, offset, explicit-baseline subtraction, Savitzky-Golay smoothing, interpolation, and integration primitives;
- LSV processing and publication plotting;
- XRD processing, multi-pattern plotting, annotations, and reference sticks;
- Raman processing, direct-window band metrics/ratios, multi-spectrum plotting, and annotations;
- shared `FigureSpec` / `PlotStyle` visualization state, deterministic curve renderer, editable presets, and exact-canvas PNG/SVG/PDF export.

The final Raman PR quality gate brought the full test suite to 218 passing tests before merge. Earlier v0.1 feature PRs were also formally reviewed and merged only after their scientific/API regression suites passed.

## Release-hardening status

Issue #18 / PR #29 completed and merged the non-scientific release-hardening work before the final version candidate was created:

- README contains source-install instructions, an executable public-API quickstart, accurate v0.1/future scope boundaries, and a public import-surface map.
- `examples/` contains compact synthetic LSV, XRD, and Raman data plus end-to-end import -> process -> plot -> PNG/SVG/PDF scripts. Generated figures are ignored under `examples/output/` so following the examples does not dirty the checkout.
- The LSV quickstart derives the RHE offset from an explicit illustrative reference potential versus SHE, pH, and temperature through `rhe_offset_from_she(...)`; it does not present a reference-electrode potential as though it were already a complete RHE offset.
- `CHANGELOG.md` records the v0.1 feature set and scientific/API principles.
- `docs/RELEASING.md` defines the wheel/install/smoke/review gate and separates version/tag operations from scientific feature work.
- CI builds a wheel, installs it into a fresh virtual environment, runs `pip check`, proves imports do not resolve from the repository `src/` tree, verifies installed distribution metadata equals runtime `__version__`, resolves every name in the six documented package-level `__all__` surfaces, runs representative public-API LSV/XRD/Raman smoke workflows, and executes all three documented examples against the installed wheel.

PR #29 passed formal release/API/packaging review and its final hardening CI before being squash-merged to `main` at commit `20995f0f49a3f5b7a1a80f1d09ea1320f285da5b`.

## Final v0.1.0 version gate

The separate `release/v0.1.0` candidate changes both version declarations together:

- `[project].version = "0.1.0"`;
- `catalysis_workbench.__version__ = "0.1.0"`.

The initial final-version CI on 2026-08-23 demonstrated that the candidate builds and installs as `catalysis_workbench-0.1.0-py3-none-any.whl`, passes Ruff, passes all 218 pytest tests, passes fresh-environment `pip check`, passes exact distribution/runtime version equality and the installed public-API smoke checks, and executes all three documented examples.

The first formal version-gate review found documentation-state consistency issues only: the future tagged snapshot must not describe itself as still untagged, this audit had to stop claiming the source remained `0.1.0.dev0`, and the changelog date requires a guard if tag creation moves to a later calendar date. No scientific-code or public-API changes were requested. Those documentation corrections require the normal final-head CI rerun before the candidate can be merge-ready.

The release policy after that review is: final-head CI green -> second formal release/API/packaging review -> merge reviewed candidate to `main` -> recheck `main` reports `0.1.0` -> create `v0.1.0` only after explicit final authorization. Package-registry publication remains a separate future policy decision.

## Public API audit

The reviewed v0.1 public surfaces are coherent and do not require renaming for release:

- `catalysis_workbench.core`
- `catalysis_workbench.io`
- `catalysis_workbench.processing`
- `catalysis_workbench.experimental.echem`
- `catalysis_workbench.experimental.characterization`
- `catalysis_workbench.visualization`

Their package-level `__all__` exports match the documented reviewed APIs and are resolved directly from the installed wheel in CI. The root package intentionally remains small and exposes version metadata rather than flattening all domain APIs into one namespace. No reviewed scientific public call is removed or renamed by the release gates.

## Architecture audit before v0.2

### Core data model

The current 1-D `Series` / `Dataset` model is sufficient for the planned v0.2 electrochemistry scope. Tafel, FE, partial current, activity, TOF, CV/Cdl/ECSA, stability, RRDE, and Koutecky-Levich analysis can all be represented as one or more condition-dependent Series plus small traceable fit/result dataclasses. No N-D or database-style core expansion is justified before those workflows demonstrate a concrete need.

### Electrochemistry units and semantics

LSV currently owns conservative potential/current/current-density unit handling internally. v0.2 would otherwise duplicate these validators across every electrochemistry module. The first v0.2 foundation task should therefore extract shared electrochemistry quantity helpers while preserving the existing public LSV API and the project rule that units remain explicit strings (Pint remains deferred).

The shared layer should cover potential/reference semantics, current/current density, charge, time, scan rate, electrode area, catalyst/metal loading, amount/rate, rotation rate, and electron-number inputs with deterministic provenance and no hidden reference-electrode lookup.

### Fit/result conventions

v0.2 introduces scalar fit outputs such as Tafel slope, Cdl, ECSA, retention/drift, K-L intercept/slope, and RRDE-derived electron number. These do not require a new global core table model yet, but they do require consistent small immutable result dataclasses containing units, fit window/inputs, stable source identifiers, and deterministic source-data digests.

### Visualization

The v0.1 shared renderer is deliberately curve-oriented. v0.2 will need scatter-style fits and publication bar summaries for FE/activity/TOF comparisons. These should be added once to the shared visualization layer rather than implemented separately inside electrochemistry modules. `FigureSpec` remains the common typography/layout/export state.

### Scope boundary for product analysis

v0.2 Faradaic-efficiency calculations should start from explicit product amount, concentration converted to amount, or molar production rate supplied by the caller. Raw GC/HPLC/NMR peak calibration belongs to the later product-quantification roadmap and must not be silently pulled into v0.2.

### Quantitative terminology

- Partial current must never silently change cathodic-current sign; signed versus magnitude output must be explicit.
- Mass/specific activity must record the denominator basis and unit (for example catalyst mass, metal mass, ECSA).
- `TOF` and `TOFapp` must be distinct. A result normalized by total metal inventory with unknown active-site fraction must not be labeled intrinsic TOF.
- Cdl/ECSA must require explicit non-Faradaic window/scan-rate data and caller-supplied specific capacitance when converting Cdl to ECSA.
- RRDE collection efficiency and K-L constants/rotation units must be explicit inputs or explicit metadata; no hidden defaults that change physical meaning.

## Recommended v0.2 implementation order

1. Finish the documented v0.1.0 final-version merge/recheck/tag gate.
2. Shared electrochemistry quantity/unit/result conventions.
3. Shared scatter/bar visualization primitives.
4. Tafel analysis.
5. Faradaic efficiency.
6. Partial current density.
7. Mass/specific activity.
8. TOF / TOFapp.
9. CV / Cdl / ECSA.
10. Stability analysis.
11. RRDE / Koutecky-Levich basics.

This order deliberately builds the reusable scientific contracts before higher-level metrics that depend on them.
