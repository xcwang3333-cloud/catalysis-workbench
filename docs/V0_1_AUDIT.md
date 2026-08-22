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

## Release-readiness gaps

The scientific implementation is complete, but v0.1 should not yet be presented as a finished release:

1. `pyproject.toml` still reports `0.1.0.dev0`.
2. `examples/README.md` is still a placeholder; there are no compact end-to-end user examples for import -> process -> plot -> export.
3. README still describes the project as early development and does not yet provide a minimal installation/quick-start/API map.
4. A release smoke test should exercise the public imports and one representative LSV, XRD, and Raman workflow from a clean installation.
5. Release notes/changelog and the v0.1 tag/release step remain to be completed.

These are release-hardening tasks, not missing scientific v0.1 features.

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

1. v0.1 release hardening.
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
