# XPS preparation and constrained fitting

CatalysisWorkbench separates XPS-specific scientific semantics from generic optimization. Issue #79 established binding-energy semantics, explicit energy correction, measured-point region preparation, and explicit linear/Shirley backgrounds. Issue #83 adds constrained XPS component/doublet fitting as a thin domain adapter over the reviewed shared `fit_peaks()` foundation.

The XPS layer does not infer chemistry, choose peak count, look up literature constraints, or perform publication plotting.

## Public API

The reviewed/prepared numerical surface is exported from `catalysis_workbench.experimental.characterization`:

- `XPSError`
- `XPSDirection`
- `XPSBackgroundMethod`
- `XPSBackgroundResult`
- `validate_xps_series`
- `shift_xps_binding_energy`
- `prepare_xps_region`
- `linear_xps_background`
- `shirley_xps_background`

Issue #83 adds the constrained-fitting surface:

- `XPSProcessingStep`
- `XPSDoubletSpec`
- `XPSPeakFitResult`
- `fit_xps_peaks`

The generic peak model/parameter contracts remain owned by `catalysis_workbench.processing`: callers use `FitParameterSpec` and `PeakComponentSpec` rather than an XPS-specific duplicate model system.

The numerical XPS modules do not import a CatalysisWorkbench plotting adapter. Importing `xps_fitting` itself defers shared-fitting/lmfit loading until a doublet is constructed or a fit is actually executed.

## Scientific input contract

XPS accepts a real-valued core `Series` with explicit axis semantics:

- x-axis semantic: `binding_energy` (conservative aliases normalize to the same semantic token);
- x unit: eV/electronvolt;
- y-axis semantic: `intensity`;
- x values finite and strictly monotonic;
- ascending and descending binding-energy storage are both supported;
- source storage order is preserved by public transformations/results;
- intensity values must be real and operations consuming a numerical fit/background region require finite values there.

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

A zero shift is allowed when explicitly requested. It still records that an energy-reference operation was performed.

CatalysisWorkbench does not look up C 1s, Au 4f, Fermi-level, or any other reference position from a label. The caller owns the reference value and rationale.

## Measured-point region preparation

`prepare_xps_region(series, x_min_ev, x_max_ev)` selects only measured points satisfying:

```text
x_min_ev <= binding_energy <= x_max_ev
```

No boundary interpolation or endpoint synthesis occurs. The selected points retain their original source order. The operation records the requested numerical bounds and required minimum point count in processing history.

Missing/non-finite intensity values inside the selected region fail explicitly.

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

The implementation does not average endpoint windows, interpolate missing boundaries, or fit the line parameters.

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

The calculation fails explicitly when the integrated excess signal is numerically zero/invalid, an iteration produces non-finite values, or convergence is not reached within `max_iterations`.

There is no fixed unexplained iteration count, smoothing, normalization, resampling, intensity clipping, or negative-signal repair heuristic.

### Hand-verifiable limiting case

If the measured low- and high-energy endpoint intensities are equal (`I_L = I_R`) and the integrated excess signal is nonzero, then:

```text
B(E) = I_R = I_L
```

The regression suite tests this constant-background case directly, together with ascending/descending equivalence, fixed-point consistency, zero-integral failure, and non-convergence failure.

## Shared constrained fitting boundary

Issue #83 does **not** implement a second optimizer. `fit_xps_peaks()` builds an explicit shared `PeakFitSpec` and delegates optimization to `catalysis_workbench.processing.fit_peaks()`.

The analysis chain is therefore:

```text
raw XPS Series
    -> explicit energy correction (optional, caller requested)
    -> explicit measured-point region preparation
    -> explicit linear/Shirley background (or explicit zero background)
    -> explicit XPS components/doublets
    -> shared constrained peak fitting
    -> later publication plotting
```

Generic line shapes, fit methods, parameter-domain validation, residual semantics, and uncertainty/covariance handling remain owned by the shared fitter.

## Single XPS components

A single XPS peak uses the existing `PeakComponentSpec` directly. The XPS layer does not duplicate the shared model contract.

For example, a Gaussian component explicitly specifies:

```python
PeakComponentSpec(
    key="oxide",
    model="gaussian",
    parameters={
        "amplitude": FitParameterSpec(...),
        "center": FitParameterSpec(...),
        "sigma": FitParameterSpec(...),
    },
    label="display/assignment text only",
)
```

Stable `key` is mathematical identity. `label` and metadata do not alter the model or prove an assignment.

## Explicit spin-orbit doublets

`XPSDoubletSpec` links one caller-supplied primary `PeakComponentSpec` to a generated secondary component. Every mathematical relation is explicit.

Required values are:

- `primary`: the complete primary shared peak component;
- `secondary_key`: a distinct stable secondary key;
- `separation_ev`: finite **signed** center offset;
- `amplitude_ratio`: finite positive multiplier;
- `parameter_ratios`: finite positive multipliers for **every** remaining model parameter other than `amplitude` and `center`.

The generated relations are:

```text
secondary.center = primary.center + separation_ev
secondary.amplitude = primary.amplitude * amplitude_ratio
secondary.<shape> = primary.<shape> * parameter_ratios[<shape>]
```

They are represented with the shared public expression syntax, never backend `cw_*` names.

### Signed-separation convention

`separation_ev` is literal:

```text
secondary.center = primary.center + separation_ev
```

A positive separation places the secondary component at higher binding energy; a negative separation places it at lower binding energy. Zero separation is rejected for the initial doublet helper because it is degenerate with coincident centers.

### No hidden branching ratio

`amplitude_ratio` is never inferred from `p`, `d`, `f`, element names, oxidation state, or assignment labels. A caller who wants a textbook-like value must supply it explicitly.

The relation is explicitly an **lmfit/shared-model amplitude relation**. CatalysisWorkbench does not relabel it as an integrated-area ratio for line shapes where that interpretation is not guaranteed.

### No hidden width/shape relation

For Gaussian/Lorentzian, `parameter_ratios` must explicitly contain `sigma`.

For models with additional parameters the complete relation must also be supplied:

- Voigt: `sigma`, `gamma`;
- pseudo-Voigt: `sigma`, `fraction`;
- Doniach: `sigma`, `gamma`.

Even a conventional equality must be written explicitly as ratio `1.0`. Missing or extra shape relations fail before optimization. This prevents a doublet helper from silently assuming equal widths or equal mixing/asymmetry parameters.

Generated constrained initial values still pass through the shared model-domain validation. For example, an explicit pseudo-Voigt fraction relation that evaluates outside `[0, 1]` fails rather than being clipped silently.

## Prepared-background alignment

When `fit_xps_peaks()` receives an `XPSBackgroundResult`, the adapter is fail-closed. Before fitting it requires:

- background source key equals fit Series key;
- deterministic source numerical SHA-256 equals the fit Series digest;
- exact x-grid values **and order** match;
- exact observed-y values match;
- background unit is eV;
- background array length and finiteness are valid;
- the explicit fit window includes every point of the background's source region.

The adapter never crops, interpolates, reverses, or otherwise repairs a mismatched background. A background from a different energy correction, region, storage order, or modified intensity must be recomputed explicitly from the intended Series.

With `background=None`, the shared fit uses its explicit zero-background semantics and may fit any explicit measured-point subwindow supported by the shared contract.

## XPS fit result and provenance

`XPSPeakFitResult` composes rather than duplicates scientific state. It retains:

- the immutable backend-independent shared `PeakFitResult`;
- XPS source numerical SHA-256;
- source storage direction;
- deterministic XPS processing steps from stage-B history (for example energy shift and region preparation);
- the exact `XPSBackgroundResult` when supplied, or explicit `zero` background state;
- explicit `XPSDoubletSpec` recipes;
- stable component keys through the shared fit specification.

It does not expose `lmfit.ModelResult` and does not duplicate shared fit arrays merely for XPS naming.

## Example constrained doublet

```python
from catalysis_workbench.experimental.characterization import (
    XPSDoubletSpec,
    fit_xps_peaks,
)
from catalysis_workbench.processing import FitParameterSpec, PeakComponentSpec

primary = PeakComponentSpec(
    key="main",
    model="gaussian",
    parameters={
        "amplitude": FitParameterSpec(10.0, lower=0.0),
        "center": FitParameterSpec(284.0),
        "sigma": FitParameterSpec(0.7, lower=0.05),
    },
)

doublet = XPSDoubletSpec(
    primary=primary,
    secondary_key="partner",
    separation_ev=3.2,
    amplitude_ratio=0.5,
    parameter_ratios={"sigma": 1.0},
)

result = fit_xps_peaks(
    region,
    x_min_ev=float(region.x.min()),
    x_max_ev=float(region.x.max()),
    doublets=(doublet,),
    background=background,
)
```

The values above are API examples only, not literature defaults.

## Prior-art and license boundary

The v0.4 architecture survey identified several useful XPS projects. Implementation decisions remain explicit:

- `jacobdben/XPyS` — MIT. Useful workflow reference for linear/Shirley concepts and linked XPS doublets. Its surveyed doublet code hard-codes p/d intensity ratios (`1/2`, `2/3`); CatalysisWorkbench does not copy that implementation and deliberately requires caller-supplied ratios instead.
- `lmfit/lmfit-py` — BSD-3-Clause and already the reviewed shared fitting backend. Stage C reuses CatalysisWorkbench's wrapper/API rather than calling mutable lmfit objects as durable XPS state.
- `JulioAzcarate/pyFitXPS` — repository license metadata previously reviewed as non-standard/NOASSERTION; architecture reference only.
- `Julian-Hochhaus/lmfitxps` — top-level MIT text, but its LICENSE states its Shirley implementation was inspired by GPL-3.0 code; that implementation remains reference-only and is not copied/adapted.

No new runtime dependency is introduced by constrained XPS fitting.

## Explicit non-goals

The current XPS stack does not:

- detect peaks;
- choose component count;
- look up binding energies, spin-orbit splittings, branching ratios, or width rules;
- automatically charge-correct spectra;
- infer oxidation state/species;
- automatically choose or recompute background;
- smooth or normalize intensity;
- calculate Tougaard background;
- perform global/sequential multi-spectrum analysis;
- read proprietary vendor-binary XPS files;
- plot XPS figures;
- provide a GUI.

Those later capabilities require separate scientific/API review.
