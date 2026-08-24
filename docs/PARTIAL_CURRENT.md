# Partial current density analysis

Issue #23 adds product-specific partial current density on top of the shared electrochemistry quantity/provenance layer (#19), shared publication renderer (#20), and explicit Faradaic-efficiency layer (#22).

## Scientific definition

For a product with Faradaic efficiency `FE_fraction`,

```text
j_product = FE_fraction * j_total
```

`FE_fraction` is dimensionless. Multiplication therefore preserves the explicit current-density unit of `j_total`.

The numerical API never infers a reaction product, electron stoichiometry, electrode area, or current sign convention. Product stoichiometry belongs upstream in the FE calculation.

## Sign convention

Two output conventions are explicit:

- `sign_mode="signed"`: preserves the sign of `j_total`. A cathodic `-100 mA cm^-2` total current at 95% FE gives `-95 mA cm^-2` product current.
- `sign_mode="magnitude"`: reports `abs(FE * j_total)`. The same input gives `95 mA cm^-2`.

No function silently changes cathodic to positive current. The selected convention is recorded in Series/Dataset provenance.

## FE policy

FE input is accepted only with the explicit representations `fraction` or `%`. Negative FE is rejected. FE above 100% is not clipped or renormalized because Issue #22 treats such values as visible QA information rather than silently modifying experimental results.

At the low-level array boundary, strings, booleans, complex values, infinities, and NaNs are rejected. Normal NumPy broadcasting is allowed only when shapes are broadcast-compatible.

## Series and Dataset contract

`partial_current_density_series(total_current_density, fe, ...)` requires:

- total-current `y_axis.name == "current_density"`;
- an explicit current-density unit supported by the shared #19 quantity layer;
- FE `y_axis.name == "faradaic_efficiency"`;
- FE y-unit exactly `fraction` or `%`;
- real finite condition coordinates;
- identical condition values and order;
- matching condition-axis name and unit;
- matching compatibility-critical condition metadata for `reference` and `normalization`.

There is no hidden interpolation, nearest-neighbor matching, sorting, or resampling.

Output keeps the total-current condition axis and current-density normalization metadata, while product `Series.key` and display label come from the FE Series. Deterministic provenance records the source identity/SHA-256 for both the total-current and FE Series, the equation, sign convention, FE input representation, and whether any FE point exceeds unity.

`partial_current_density_dataset(...)` applies this contract to an ordered FE Dataset. Non-empty stable product keys are required and preserved.

## Closure QA

`partial_current_closure(...)` is diagnostic only. It never rescales partial currents to match the measured total.

Two comparison modes are explicit:

- `signed`: compare `sum(j_product)` with signed `j_total`;
- `magnitude`: compare `sum(abs(j_product))` with `abs(j_total)`.

The report includes summed partial current, signed residual, absolute error, relative error, tolerance, and pass/fail mask. At zero total current, exact zero closure has zero relative error; any non-zero closure error is infinite and fails a finite tolerance.

`partial_current_closure_dataset(...)` adds unit/condition validation and deterministic source references for the total-current Series and every partial-current Series.

## Publication plotting

`plot_partial_current_density(...)` performs no analysis or QA filtering. It validates that input data already have `partial_current_density` semantics and delegates to the shared `render_scatter` or `render_curves` implementation. Numerical electrochemistry imports remain Matplotlib-lazy.

## Prior-art review

The module was designed after reviewing comparable open-source electrochemistry/product-analysis projects:

- `ixdat/ixdat` (MIT): useful architecture reference for keeping electrochemical values, units, axes, calibrations, and simultaneously measured signals explicit. CatalysisWorkbench adopts explicit scientific metadata and exact alignment requirements, but not ixdat's persistence/database model.
- `ixdat/tutorials` (MIT): useful examples for integrating/aligning electrochemical signals and combining calibrated product information with electrochemistry. CatalysisWorkbench deliberately refuses hidden alignment in this API; alignment must occur in an explicit upstream step.
- `MEG-LBNL/Polarization_Decoupling_Analysis` (GPL-3.0, reference-only): useful practical CO2RR reference for product-wise FE/current-density analysis and voltage-dependent product summaries. No implementation code is copied; CatalysisWorkbench keeps FE stoichiometry upstream and avoids clipping/renormalization.
- `kevinsmia1939/PySimpleEChem` (GPL-3.0, reference-only): useful reference for explicit electrode-area normalization and electrochemical current analysis, but not used as an implementation dependency.

No new dependency is required for Issue #23. NumPy and the existing CatalysisWorkbench quantity/provenance/visualization layers provide the necessary numerical and rendering primitives.

## Failure policy

Reject explicitly:

- missing/unsupported current-density unit in Series workflows;
- wrong current-density or FE axis semantics;
- FE unit other than `fraction` or `%`;
- negative, non-numeric, complex, missing, or infinite FE/current values;
- incompatible broadcast shapes;
- condition value/order mismatch;
- condition-axis name/unit/reference/normalization mismatch;
- empty multi-product Dataset or missing stable product keys;
- closure arrays with incompatible shapes or invalid tolerance/mode.

None of these failures triggers an automatic scientific correction.
