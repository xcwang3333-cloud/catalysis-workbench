# Shared electrochemistry foundation

Issue #19 defines the common quantity, unit, reference, and result-provenance layer used by the v0.2 electrochemistry roadmap. The layer is deliberately small: it standardizes quantities that later modules need without introducing a general-purpose unit system or a new scientific data container.

## Unit policy

Units are explicit strings. Missing, non-string, or unsupported units fail rather than being guessed. Numerical conversion preserves sign and converts into one canonical calculation basis per quantity.

| Quantity | Accepted v0.2 foundation units | Canonical calculation basis |
| --- | --- | --- |
| Potential | V, mV | V |
| Current | A, mA, uA/µA/μA | A |
| Current density | A, mA, uA per cm² with reviewed slash/spaced aliases | A/cm² |
| Charge | C, mC, uC/µC/μC, Ah, mAh, uAh/µAh/μAh | C |
| Time | s, min, h | s |
| Scan rate | V/s, mV/s, V/min, mV/min | V/s |
| Area | cm², mm², m² | cm² |
| Mass | kg, g, mg, ug/µg/μg | g |
| Areal loading | g, mg, ug per cm² | g/cm² |
| Amount | mol, mmol, umol/µmol/μmol, nmol | mol |
| Molar rate | mol/mmol/umol/nmol per s or min | mol/s |
| Rotation rate | rad/s, rpm, rps | rad/s |

Bare `Hz` is not treated as a rotation-rate alias because the angular-versus-cyclic-frequency convention must stay explicit. Current/current-density conversions never take absolute values or reverse sign.

The vectorized quantity converters always return float64 NumPy arrays and preserve the input shape. A scalar input therefore produces a zero-dimensional NumPy array; callers that specifically require a Python scalar should convert explicitly with `.item()`. This array-return contract is intentional so later electrochemistry modules can share one predictable low-level numerical API.

`electron_number(...)` requires a positive integer-valued real numeric input. Integer-valued floats and NumPy integer scalars are accepted; booleans and strings, including numeric strings such as `"4"`, are rejected. Product names, catalyst labels, and other strings never imply electron stoichiometry.

## Reference-electrode policy

Reference names are explicit strings. `normalize_reference_name(...)` only normalizes whitespace; `same_reference(...)` adds case-insensitive comparison. There is no built-in Ag/AgCl, SCE, SHE, or other reference-electrode potential table. Conversion to RHE continues to require an explicit offset or explicit user-supplied reference potential versus SHE plus pH/temperature through the reviewed LSV API.

## Result provenance

Later fit/scalar-result dataclasses should compose the shared frozen records rather than inventing module-specific provenance shapes:

- `SourceDataRef`: stable Series key/label, validated numerical x/y SHA-256, axis names, and original units;
- `FitWindow`: explicit finite lower/upper physical bounds, non-empty unit, and integer selected-point count of at least two;
- `AnalysisProvenance`: validated source identity, explicit input basis, optional validated fit window, sorted unit declarations, and sorted scalar analysis parameters.

The public dataclass constructors protect the same invariants as the factory path. `SourceDataRef` rejects malformed SHA-256 values and missing axis semantics. `AnalysisProvenance` requires a `SourceDataRef`, accepts only a `FitWindow` or `None`, canonicalizes direct tuple fields deterministically, rejects duplicate normalized keys, and rejects nested/non-scalar parameter values.

`series_data_sha256(...)` hashes the numerical x/y arrays only. Axis names/units remain explicit neighboring fields in `SourceDataRef`; the digest is data identity, not a substitute for scientific semantics.

Unit declarations are stricter than generic analysis parameters: every recorded unit value must be an explicit non-empty string. If a result has no applicable unit, omit that unit entry rather than storing a numeric, boolean, empty, or null placeholder. Analysis parameters may use deterministic scalar string/int/float/bool/None values. Arrays, curves, fit covariance matrices, and other structured scientific outputs should be explicit result fields rather than opaque nested metadata.

## LSV compatibility

The v0.1 public LSV entry points remain unchanged:

- `rhe_offset_from_she`
- `convert_potential_to_rhe`
- `correct_ir_drop`
- `to_current_density`
- `process_lsv`
- `process_lsv_dataset`
- `plot_lsv`

The refactor moves common potential/current/current-density parsing into the shared quantity layer while preserving `LSVError`, signed iR behavior, geometric-area reconstruction checks, deterministic processing history, missing-unit behavior, and lazy Matplotlib imports. Legacy current-density aliases accepted by the reviewed v0.1 LSV layer, including slash, compact, and reciprocal-centimeter spellings, remain supported.

## Scope boundary

This foundation does not implement Tafel fitting, FE, product partial current, mass/specific activity, TOF/TOFapp, Cdl/ECSA, stability metrics, RRDE, or Koutecky-Levich analysis. It supplies the common scientific vocabulary those modules will use. It also does not introduce Pint, xarray, a table core, a database, or a hidden reference-electrode registry.

Because `v0.1.0` is already tagged, the first v0.2 development branch advances distribution and runtime versions together to `0.2.0.dev0`; the released `v0.1.0` tag remains immutable.
