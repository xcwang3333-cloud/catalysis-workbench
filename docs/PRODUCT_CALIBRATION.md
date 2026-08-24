# Product calibration and sample quantification

This document defines the reviewed v0.4 contract for converting already integrated analytical response values into quantified product values. It sits upstream of the existing electrochemical Faradaic-efficiency and product-rate calculations.

## Scope

The first product-analysis layer is technique-agnostic. It accepts calibration standards and already integrated detector responses from workflows such as GC, HPLC, or NMR, but it does not parse vendor files, identify products, detect peaks, fit chromatograms, integrate peaks, or perform NMR spectral processing.

The numerical API lives under `catalysis_workbench.experimental.product` and remains separate from `experimental.echem` and `experimental.characterization`.

## Prior-art and license boundary

Issue #99 refreshed the following upstream references:

- `cremerlab/hplc-py` — GPL-3.0. Its calibration tutorial separates chromatographic peak integration from the calibration curve and inverts a fitted linear response for unknown concentration. Workflow/scientific reference only; no GPL implementation is copied or adapted and no dependency is added.
- `FelixKatz77/pyGecko` — MIT. Relevant for GC-FID/internal-standard quantification workflows. CatalysisWorkbench does not copy its automatic identification or response-factor behavior and does not infer identities or internal standards.
- `MyonicS/ChromStream` — MIT. Relevant because GC parsing/integration and calibration are separated. Architecture reference only; no dependency or implementation copy.
- `jjhelmus/nmrglue` — BSD-3-Clause. Relevant to later NMR file-processing/integration adapters. The current module starts from already integrated NMR response and does not reimplement NMR processing.

The initial implementation uses only existing NumPy/SciPy dependencies.

## Calibration input

A calibration relationship is represented by the existing core `Series`:

- x axis semantic: `calibration_quantity`;
- y axis semantic: `response`;
- both axes require explicit non-empty units;
- x and y must be finite real one-dimensional arrays of equal length;
- known calibration quantities must be non-negative;
- at least three standard observations and at least two distinct known quantities are required;
- repeated known quantities remain independent replicate standards and are not averaged automatically;
- source order is retained.

Calibration input is fail-closed against existing processing history. The first reviewed calibration layer expects already integrated response values and does not accept a generic transformed response series as if it were raw calibration evidence.

`CalibrationRange(low, high)` optionally selects an inclusive numerical range of measured standards. It never creates synthetic boundary observations and retained source indices preserve original order.

## Linear model

The only reviewed model is

```text
response = intercept + slope * calibration_quantity
```

The caller explicitly chooses the intercept policy:

- `free`: ordinary least squares with slope and intercept fitted;
- `zero`: intercept fixed exactly to zero and only slope fitted.

There is no automatic model selection, polynomial calibration, nonlinear calibration, hidden standard-range optimization, or R² acceptance threshold.

`CalibrationFitResult` retains:

- deterministic source identity and numerical SHA-256;
- source axes/units and source arrays;
- selected measured indices and arrays;
- model and intercept policy;
- slope/intercept and available standard-error state;
- exact best-fit response and physical residual `observed - best_fit`;
- centered R² when mathematically defined;
- point and varying-parameter counts;
- a two-point retained fit line spanning the selected calibration range.

When response variance is zero, centered R² and regression uncertainty that cannot be meaningfully estimated remain unavailable rather than being represented as zero.

Public result reconstruction is fail-closed: contradictory source digest, model coefficients, retained best-fit arrays, residuals, units, ranges, or fit-line state are rejected.

## Inverse quantification

`quantify_response()` is separate from calibration fitting. For an explicit compatible calibration result:

```text
quantity_raw = (response - intercept) / slope
quantity_final = quantity_raw * product(explicit factors)
```

Rules:

- the response unit must exactly match the calibration response unit;
- the fitted slope must be finite and non-zero;
- scalar or array response shape is retained;
- output quantity unit is exactly the calibration x unit;
- negative inferred quantity fails explicitly and is never clipped to zero;
- extrapolation outside the selected calibration-quantity span is rejected by default;
- `allow_extrapolation=True` is an explicit opt-in and retains an extrapolation mask;
- calibration inversion does not perform generic unit algebra or automatically convert concentration to amount/rate.

`QuantificationFactor(key, value)` represents a caller-supplied named positive finite dimensionless multiplier. Factors retain caller order and duplicate keys are rejected. A label such as `dilution` has no hidden mathematical meaning beyond the explicitly supplied multiplier.

No internal-standard response ratio, injection volume, aliquot volume, sample volume/mass, density, gas-flow correction, detector response factor, product identity, stoichiometry, or Faradaic efficiency is inferred from labels.

## Replicate summary

`summarize_quantification_replicates()` reports:

- arithmetic mean;
- sample standard deviation with `ddof=1` when at least two values exist;
- RSD percent when defined;
- replicate count;
- retained quantity unit.

For one replicate, mean and n remain available but SD and RSD remain unavailable. No outlier rejection or automatic weighting is applied.

## Plotting

`plot_calibration()` is a lazy passive plotting adapter using the existing `FigureSpec` system.

It renders only retained state:

- `calibration_observed`: exact selected standard observations;
- `calibration_fit`: exact retained two-point fit line.

Plotting does not refit, select a range, convert responses, sort data, smooth data, infer units, or fabricate uncertainty.

## Relationship to electrochemistry

The existing Faradaic-efficiency layer intentionally consumes already quantified product amount or molar rate. Product calibration remains upstream. A caller may explicitly convert a reviewed quantified product result into the units required by an electrochemical calculation, but this first product-calibration block does not infer electron number, reaction stoichiometry, FE, current, charge, or rate basis.

## Explicit non-goals

The first stage does not provide:

- raw GC/HPLC/NMR vendor-file parsing;
- baseline correction, peak detection, deconvolution, integration, or product assignment;
- automatic internal-standard identification or ratio calculation;
- hidden detector response-factor libraries;
- nonlinear/polynomial calibration models;
- automatic model/range selection or outlier deletion;
- generic dimensional unit conversion;
- concentration-to-moles, flow, aliquot, injection, density, sample-volume or sample-mass transformations beyond explicit dimensionless factors;
- automatic propagation of calibration confidence intervals to unknown samples;
- Faradaic-efficiency calculation;
- a second visualization framework.

## Validation expectations

The module is protected by hand-verifiable regression tests for exact linear recovery, fixed-zero behavior, measured-point range selection, repeated standards, undefined R², immutable/fail-closed result reconstruction, response-unit compatibility, inverse quantification, extrapolation policy, negative-result failure, named factors, replicate statistics, passive rendering, Matplotlib-lazy numerical imports, and fresh-wheel fit/quantify/plot/export smoke.