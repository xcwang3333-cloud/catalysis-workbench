# Shared electrochemistry foundation

Issue #19 defines the common quantity, unit, reference, and result-provenance layer used by the v0.2 electrochemistry roadmap. The layer is deliberately small: it standardizes quantities that later modules need without introducing a general-purpose unit system or a new scientific data container.

## Unit policy

Units are explicit strings. Missing or unsupported units fail rather than being guessed. Numerical conversion preserves sign and converts into one canonical calculation basis per quantity.

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

`electron_number(...)` requires a positive integer. Product names, catalyst labels, and other strings never imply electron stoichiometry.

## Reference-electrode policy

`normalize_reference_name(...)` only normalizes whitespace; `same_reference(...)` adds case-insensitive comparison. There is no built-in Ag/AgCl, SCE, SHE, or other reference-electrode potential table. Conversion to RHE continues to require an explicit offset or explicit user-supplied reference potential versus SHE plus pH/temperature through the reviewed LSV API.

## Result provenance

Later fit/scalar-result dataclasses should compose the shared frozen records rather than inventing module-specific provenance shapes:

- `SourceDataRef`: stable Series key/label, numerical x/y SHA-256, axis names, and original units;
- `FitWindow`: explicit lower/upper physical bounds, unit, and selected point count;
- `AnalysisProvenance`: source identity, explicit input basis, optional fit window, sorted scalar unit declarations, and sorted scalar analysis parameters.

`series_data_sha256(...)` hashes the numerical x/y arrays only. Axis names/units remain explicit neighboring fields in `SourceDataRef`; the digest is data identity, not a substitute for scientific semantics.

Provenance mappings accept deterministic scalar values only. Arrays, curves, fit covariance matrices, and other structured scientific outputs should be explicit result fields rather than opaque nested metadata.

## LSV compatibility

The v0.1 public LSV entry points remain unchanged:

- `rhe_offset_from_she`
- `convert_potential_to_rhe`
- `correct_ir_drop`
- `to_current_density`
- `process_lsv`
- `process_lsv_dataset`
- `plot_lsv`

The refactor moves common potential/current/current-density parsing into the shared quantity layer while preserving `LSVError`, signed iR behavior, geometric-area reconstruction checks, deterministic processing history, and lazy Matplotlib imports.

## Scope boundary

This foundation does not implement Tafel fitting, FE, product partial current, mass/specific activity, TOF/TOFapp, Cdl/ECSA, stability metrics, RRDE, or Koutecky-Levich analysis. It supplies the common scientific vocabulary those modules will use. It also does not introduce Pint, xarray, a table core, a database, or a hidden reference-electrode registry.

Because `v0.1.0` is already tagged, the first v0.2 development branch advances distribution and runtime versions together to `0.2.0.dev0`; the released `v0.1.0` tag remains immutable.
