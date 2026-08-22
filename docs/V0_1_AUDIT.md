# v0.1 completion audit

Date: 2026-08-22

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

Issue #18 / the v0.1 release-hardening branch resolves the non-scientific gaps identified by the initial audit:

- README now contains source-install instructions, an executable public-API quickstart, accurate v0.1/future scope boundaries, and a public import-surface map.
- `examples/` contains compact synthetic LSV, XRD, and Raman data plus end-to-end import -> process -> plot -> PNG/SVG/PDF scripts. Generated figures are ignored under `examples/output/` so following the examples does not dirty the checkout.
- The LSV quickstart derives the RHE offset from an explicit illustrative reference potential versus SHE, pH, and temperature through `rhe_offset_from_she(...)`; it no longer presents a reference-electrode potential as though it were already a complete RHE offset.
- `CHANGELOG.md` records the unreleased v0.1 feature set and scientific/API principles.
- `docs/RELEASING.md` defines the explicit wheel/install/smoke/review gate and separates the later version/tag action from feature work.
- CI builds a wheel, installs it into a fresh virtual environment, runs `pip check`, proves imports do not resolve from the repository `src/` tree, verifies installed distribution metadata equals runtime `__version__`, resolves every name in the six documented package-level `__all__` surfaces, runs representative public-API LSV/XRD/Raman smoke workflows, and executes all three documented examples against the installed wheel.
- The post-review release-hardening CI passes Ruff, all 218 pytest tests, wheel build/install/dependency checks, installed public-API/version/export smoke, and all documented end-to-end examples.

The only intentionally unresolved release step is the final version/tag action. `pyproject.toml` and `catalysis_workbench.__version__` remain `0.1.0.dev0` until the release-hardening PR receives formal review and explicit approval. They must be changed to `0.1.0` together in the later release gate, followed by one more full CI/wheel smoke run before tagging `v0.1.0`.

## Public API audit

The reviewed v0.1 public surfaces are coherent and do not require renaming for release hardening:

- `catalysis_workbench.core`
- `catalysis_workbench.io`
- `catalysis_workbench.processing`
- `catalysis_workbench.experimental.echem`
- `catalysis_workbench.experimental.characterization`
- `catalysis_workbench.visualization`

Their package-level `__all__` exports match the documented reviewed APIs and are now resolved directly from the installed wheel in CI. The root package intentionally remains small and exposes version metadata rather than flattening all domain APIs into one namespace. No reviewed scientific public call is removed or renamed by Issue #18.

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

1. Complete and review v0.1 release hardening, then perform the separate version/tag gate.
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
