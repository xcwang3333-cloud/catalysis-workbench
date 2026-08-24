# XPS semantics, energy correction, and background preparation

Issue #79 implements the first XPS-specific scientific layer in CatalysisWorkbench. It prepares explicit, auditable numerical state for later constrained XPS peak fitting; it does **not** fit peak components or infer chemistry.

## Public API

The reviewed numerical surface is intended to be exported from `catalysis_workbench.experimental.characterization`:

- `XPSError`
- `XPSDirection`
- `XPSBackgroundMethod`
- `XPSBackgroundResult`
- `validate_xps_series`
- `shift_xps_binding_energy`
- `prepare_xps_region`
- `linear_xps_background`
- `shirley_xps_background`

The numerical XPS layer does not import a CatalysisWorkbench plotting adapter and does not render figures.

## Scientific input contract

The first XPS implementation accepts a real-valued core `Series` with explicit axis semantics:

- x-axis semantic: `binding_energy` (conservative aliases `binding_energy`, `binding e`, and `BE` normalize to the same token);
- x unit: eV/electronvolt;
- y-axis semantic: `intensity`;
- x values finite and strictly monotonic;
- ascending and descending binding-energy storage are both supported;
- source storage order is preserved by public transformations/results;
- intensity values must be real and may not contain infinity; an operation that consumes a selected numerical region requires finite intensity values in that region.

The library does not infer XPS semantics from display labels alone and does not silently sort, interpolate, reverse, or drop data.

## Explicit binding-energy correction

`shift_xps_binding_energy(series, shift_ev, ...)` performs exactly one caller-supplied additive energy transformation:

```text
E_corrected = E_source + shift_ev
```

The sign convention is literal. A positive `shift_ev` moves every stored binding-energy value upward by that amount; a negative shift moves it downward.

The transformation:

- leaves intensity values unchanged;
- preserves stable key and display label;
- preserves ascending/descending storage direction;
- canonicalizes the XPS x semantic/unit to binding energy/eV;
- records `shift_ev` and optional caller-supplied `reference` / `rationale` in deterministic processing provenance;
- records the applied shift in x-axis metadata;
- rejects a second XPS energy-shift operation rather than silently accumulating corrections.

A zero shift is allowed when explicitly requested. It still records that an energy-reference operation was performed, which prevents a second hidden correction.

CatalysisWorkbench does not look up C 1s, Au 4f, Fermi-level, or any other reference position from a label. The caller owns the reference value and rationale.

## Measured-point region preparation

`prepare_xps_region(series, x_min_ev, x_max_ev)` selects only measured points satisfying:

```text
x_min_ev <= binding_energy <= x_max_ev
```

No boundary interpolation or endpoint synthesis occurs. The selected points retain their original source order. The operation records the requested numerical bounds and required minimum point count in processing history.

Missing/non-finite intensity values inside the selected region fail explicitly; values outside the selected region are not silently used to alter the result.

For background work, prepare the desired XPS region first and then calculate the background on that returned region. This keeps endpoint choice visible and makes the later shared-fitting background array naturally align with the prepared source grid.

## Background result

`XPSBackgroundResult` is a value-oriented record containing:

- method (`linear` or `shirley`);
- source key/label and deterministic numerical SHA-256;
- source storage direction;
- eV and intensity-unit semantics;
- exact x and observed-y arrays used;
- calculated background on the same grid/order;
- numerical low/high binding-energy endpoints and measured endpoint intensities;
- convergence/settings state for iterative Shirley calculation.

Stored scientific arrays are detached/read-only. A background result is preparation state, not a fit, component assignment, or chemical interpretation.

## Linear background

The linear XPS background is the straight line through the two **measured** endpoint intensities identified by numerical minimum and maximum binding energy of the input region.

For endpoints `(E_L, I_L)` and `(E_R, I_R)` with `E_L < E_R`:

```text
B(E) = I_L + (I_R - I_L) * (E - E_L) / (E_R - E_L)
```

The numerical result is identical physically for ascending and descending source storage, then returned in the original source order. Endpoint values are enforced exactly.

The implementation does not average endpoint windows, interpolate missing boundaries, or fit the line parameters. More elaborate endpoint policies require a separate reviewed contract.

## Shirley background

CatalysisWorkbench implements the Shirley background independently from the fixed-point integral equation. It does not copy a reference repository implementation.

For an internal canonical **increasing-energy numerical view** of the caller data, with low/high measured endpoints `(E_L, I_L)` and `(E_R, I_R)`, define:

```text
B(E) = I_R + (I_L - I_R) * A(E) / A(E_L)
```

where

```text
A(E) = integral_E^E_R [I(E') - B(E')] dE'
```

The internal increasing-energy view exists only to make the integration orientation unambiguous. It does not mutate or reorder the source `Series`; the returned background is restored to the caller's original storage order.

### Numerical policy

The initial background is the measured-endpoint linear background. Each fixed-point iteration:

1. forms `I - B` on the measured grid;
2. evaluates the right-side cumulative integral with trapezoidal integration on the measured x grid;
3. evaluates the explicit Shirley equation;
4. enforces low/high endpoint intensities exactly;
5. checks the maximum absolute update against
   `absolute_tolerance + relative_tolerance * scale`.

Defaults:

- `relative_tolerance = 1e-8`
- `absolute_tolerance = 1e-10` intensity units
- `max_iterations = 200`

The tolerances must be finite and positive and `max_iterations >= 1`.

The calculation fails explicitly when:

- the integrated excess signal is numerically zero/invalid;
- an iteration produces non-finite values;
- convergence is not reached within `max_iterations`.

There is no fixed unexplained iteration count, smoothing, normalization, resampling, intensity clipping, or negative-signal repair heuristic.

### Hand-verifiable limiting case

If the measured low- and high-energy endpoint intensities are equal (`I_L = I_R`) and the integrated excess signal is nonzero, then the factor `(I_L - I_R)` is zero, so the Shirley equation reduces exactly to:

```text
B(E) = I_R = I_L
```

The regression suite tests this constant-background case directly, together with ascending/descending equivalence, fixed-point consistency, zero-integral failure, and non-convergence failure.

## Prior-art and license boundary

The v0.4 architecture survey identified several useful XPS projects, but Issue #79 performs a fresh implementation-boundary check:

- `jacobdben/XPyS` — MIT. Useful workflow reference for linear/Shirley concepts and XPS doublets. Its surveyed implementation reverses increasing-energy input with slicing and uses a fixed 10-iteration Shirley loop. CatalysisWorkbench copies no code and deliberately uses explicit direction preservation plus convergence criteria instead.
- `JulioAzcarate/pyFitXPS` — repository license metadata was previously reviewed as non-standard/NOASSERTION. Useful architecture reference for separating original/working data and an explicit energy-scale correction operation. No implementation reuse.
- `Julian-Hochhaus/lmfitxps` — top-level MIT text, but its LICENSE explicitly states that `shirley_calculate()` was inspired by GPL-3.0 code by Kane O'Donnell. That Shirley implementation is therefore **reference-only and is not copied/adapted** here.

The Shirley implementation in CatalysisWorkbench is written independently from the explicit equation above and validated by project-owned regressions.

## Boundary to shared constrained fitting

Issue #79 does not call `fit_peaks()`.

The intended later workflow is:

```text
raw XPS Series
    -> explicit energy correction (optional, caller requested)
    -> explicit measured-point region preparation
    -> explicit linear/Shirley background
    -> later XPS component/doublet specification
    -> shared constrained peak fitting
    -> later publication plotting
```

This separation keeps XPS background/energy assumptions out of the generic fitting foundation.

## Explicit non-goals

This stage does not:

- detect peaks;
- choose component count;
- fit any peak component;
- create spin-orbit doublets;
- look up binding energies, spin-orbit splittings, or branching ratios;
- automatically charge-correct spectra;
- infer oxidation state/species;
- smooth or normalize intensity;
- calculate Tougaard background;
- perform global/sequential multi-spectrum analysis;
- read proprietary vendor-binary XPS files;
- plot XPS figures;
- provide a GUI.

Those later capabilities require separate scientific/API review.
