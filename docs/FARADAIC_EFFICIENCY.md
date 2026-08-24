# Faradaic efficiency analysis contract

Issue #22 adds explicit Faradaic-efficiency (FE) calculations on top of the shared v0.2 electrochemistry quantity layer. The module starts from already quantified product amount or molar production rate; instrument-specific product quantification remains outside this scope.

## Prior art

The implementation was designed after inspecting open-source electrochemistry/product-analysis workflows:

- `ixdat/ixdat` (MIT) keeps electrochemical current, calibrated molecular flux, time/axis context, and calibration state explicit. Its EC-MS workflow is the main architecture reference for separating product quantification from later electrochemical analysis.
- `ixdat/tutorials` (MIT) demonstrates an EC-MS workflow in which a calibration is first established and then applied to product signals before they are combined with electrochemistry. CatalysisWorkbench Issue #22 deliberately begins after this calibration stage.
- `MEG-LBNL/Polarization_Decoupling_Analysis` (GPL-3.0) is practical CO2RR prior art combining chronoamperometry and GC products to calculate product-wise and total FE. It also illustrates choices CatalysisWorkbench intentionally does not adopt: hard-coded product/electron mappings, negative-FE clipping, and fixed total-FE rejection thresholds. The GPL implementation is reference-only and no source code is copied.

No new runtime dependency is needed. Unit conversion and Faraday's constant come from the reviewed Issue #19 electrochemistry foundation.

## Scientific definitions

Accumulated-product FE is

```text
FE = z F n_product / |Q|
```

where `n_product` is converted to mol, `Q` is converted to C, `z` is the explicitly supplied positive integer electron stoichiometry, and `F` is the shared Faraday constant.

Steady-state/rate FE is

```text
FE = z F r_product / |I|
```

where `r_product` is converted to mol/s and `I` to A.

The denominator magnitude makes FE non-negative while the original signed canonical charge/current is retained in `FaradaicEfficiencyResult.denominator_canonical`. No current or charge sign is silently rewritten.

## Low-level result contract

`faradaic_efficiency_from_amount(...)` and `faradaic_efficiency_from_rate(...)` return an immutable `FaradaicEfficiencyResult` rather than a context-free scalar.

The result stores:

- calculation mode (`amount_charge` or `rate_current`);
- explicit electron number;
- canonical product values (`mol` or `mol/s`);
- signed canonical denominator values (`C` or `A`).

`fraction`, `percent`, and `exceeds_unity` are derived properties. FE above 100% remains visible; nothing is clipped or renormalized.

Scalar and array inputs follow NumPy broadcasting. Incompatible shapes, Boolean inputs, numeric strings/object coercion, complex/non-numeric values, NaN/inf, negative product amount/rate, zero denominator, unsupported units, and invalid electron numbers fail explicitly. The FE public boundary therefore accepts actual real numeric arrays/scalars only; it does not rely on permissive string-to-float coercion in lower-level unit helpers.

## Condition-resolved Series

`faradaic_efficiency_series(...)` accepts one product `Series` and one denominator `Series`.

Supported semantic pairs are:

- product `y_axis.name == "amount"` with denominator `y_axis.name == "charge"`;
- product `y_axis.name == "molar_rate"` with denominator `y_axis.name == "current"`.

The condition x axes must match exactly in values and order, axis name, unit, and compatibility-critical `reference` / `normalization` metadata. Issue #22 performs no interpolation, synchronization, or nearest-neighbor matching.

The output preserves the product key, label, and condition axis. Its y axis is `faradaic_efficiency` with explicit unit `%` (default) or `fraction`.

Output metadata records:

- FE mode and electron number;
- shared Faraday constant;
- canonical calculation units;
- signed canonical denominator values;
- product `SourceDataRef` identity/digest;
- denominator `SourceDataRef` identity/digest;
- explicit output unit.

This keeps multi-source traceability without changing the lightweight core data model.

## Multi-product Dataset

`faradaic_efficiency_dataset(...)` preserves Dataset order and product key/label identity. Every product must have a non-empty stable key, and `electron_numbers` must contain exactly those keys after normalization.

No product name implies a stoichiometry. For example, CO being a two-electron product is scientific caller knowledge, not a library lookup rule.

## Closure and QA policy

`faradaic_efficiency_closure(...)` accepts one FE Series or a Dataset of compatible FE Series and returns `FaradaicEfficiencyClosure` containing:

- condition values/axis;
- unmodified total FE fraction;
- point-wise exceedance mask;
- ordered product keys;
- ordered `SourceDataRef` records for every FE Series included in the sum;
- explicit limit and tolerance.

The closure result is itself invariant-bearing: its exceedance mask must be genuinely boolean, must match the configured threshold exactly, and its source records must correspond in order to the summarized product keys and condition-axis semantics. This preserves deterministic source digests after the individual FE Series have been reduced to a total.

Default behavior is report-only. The exceedance criterion is

```text
total_FE > limit_fraction + tolerance_fraction
```

`strict=True` raises if any condition exceeds that threshold. Neither mode clips products, discards conditions, or rescales totals to 100%.

## Publication adapter

`plot_faradaic_efficiency(...)` is imported lazily so numerical electrochemistry remains usable without importing Matplotlib.

- `kind="scatter"` delegates to the shared `render_scatter` stack and can accept explicit `ScatterError` data.
- `kind="curve"` delegates to `render_curves`.

The adapter performs no FE calculation, normalization, QA filtering, smoothing, or product summation. Stable `Series.key` styling and shared axis compatibility remain authoritative.

## Scope boundary

Issue #22 implements FE calculation plus multi-product FE closure/QA. It does not implement raw GC/HPLC/IC/NMR/MS peak integration, calibration curves, gas-flow conversion, liquid-volume/headspace corrections, online-MS calibration, time synchronization, FE uncertainty propagation, product selectivity ratios, carbon balance, carbon efficiency, or automatic stoichiometry lookup. Those require additional assumptions or product-analysis infrastructure and remain separate roadmap work.
