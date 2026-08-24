# EIS semantics, equivalent circuits, fitting, and publication plotting

CatalysisWorkbench treats electrochemical impedance spectroscopy as literal complex scientific data. The initial v0.4 EIS layer deliberately keeps the scientific vocabulary small: explicit frequency/impedance semantics, ideal R/C/CPE elements, explicit series/parallel composition, constrained complex least-squares fitting, Nyquist/Bode rendering, and fit diagnostics.

The layer does **not** choose a circuit, guess units, sort frequencies, invent initial values, select weighting, infer an electrochemical mechanism, or hide a sign conversion.

## Public API

The numerical EIS surface is exported from `catalysis_workbench.experimental.echem`:

- `EISError`
- `EISDirection`
- `EISParameterSpec`
- `EISResistor`
- `EISCapacitor`
- `EISCPE`
- `EISSeriesCircuit`
- `EISParallelCircuit`
- `EISCircuit`
- `EISFitConfig`
- `EISFittedParameter`
- `EISFitResult`
- `EISFitDiagnostics`
- `validate_eis_series`
- `validate_eis_circuit`
- `eis_circuit_element_keys`
- `eis_circuit_parameter_keys`
- `evaluate_eis_circuit`
- `fit_eis`
- `summarize_eis_fit`

Publication adapters are lazily dispatched from the same package:

- `plot_eis_nyquist`
- `plot_eis_bode`

Importing the numerical electrochemistry package does not import Matplotlib. The plotting module is loaded only when an EIS plotting function is called.

## Core data representation

EIS uses the existing immutable core `Series`:

```python
Series(
    x=frequency_hz,
    y=complex_impedance,
    x_axis=Axis("frequency", unit="Hz"),
    y_axis=Axis("impedance", unit="ohm"),
)
```

The stored scientific quantity is literal complex impedance:

```text
Z = Z' + j Z''
```

Requirements:

- x semantic is `frequency` (the conservative alias `freq` is accepted);
- frequency unit is Hz/hertz;
- y semantic is `impedance` (the conservative alias `z` is accepted);
- impedance unit is ohm/Ω;
- frequency is real, finite, strictly positive, and strictly monotonic;
- both ascending and descending source order are valid;
- impedance is explicitly complex-valued and finite;
- a purely real storage vector is rejected in this first EIS API instead of being silently reinterpreted as complex impedance.

The library does not sort, interpolate, resample, unwrap phase, drop points, or multiply the imaginary part by `-1` in scientific state.

## Stable source identity

`EISFitResult.source_sha256` is calculated with the existing electrochemistry `series_data_sha256()` helper over the exact numerical x/y arrays. Because complex y data are preserved by the core model and the digest includes dtype/shape/bytes, a changed real part, imaginary part, frequency grid, or point order changes the numerical identity.

Fit overlays in publication plots are fail-closed: source key, numerical digest, frequency grid/order, and observed complex impedance must match the plotted `Series` exactly.

## Initial circuit vocabulary

The first EIS circuit model is a typed object graph, not a string parser. Leaf element keys are stable mathematical identifiers and must be globally unique across the circuit.

### Resistor

For resistance `R > 0` Ω:

```text
Z_R = R
```

Public parameter key:

```text
<element_key>.R
```

### Capacitor

For capacitance `C > 0` F and angular frequency `ω = 2πf`:

```text
Z_C = 1 / (jωC)
```

Public parameter key:

```text
<element_key>.C
```

### Constant-phase element

The initial CPE convention is:

```text
Z_CPE = 1 / [Q (jω)^n]
```

with:

```text
Q > 0
0 < n <= 1
```

Public parameter keys:

```text
<element_key>.Q
<element_key>.n
```

At `n = 1`, this expression has the same mathematical form as an ideal capacitor with `Q` numerically playing the capacitance role under the stated convention. CatalysisWorkbench does not convert Q into a different physical capacitance interpretation automatically.

### Series composition

`EISSeriesCircuit((a, b, ...))` requires at least two child nodes and evaluates:

```text
Z_series = Σ Z_child
```

### Parallel composition

`EISParallelCircuit((a, b, ...))` requires at least two child nodes and evaluates:

```text
Y_parallel = Σ (1 / Z_child)
Z_parallel = 1 / Y_parallel
```

Zero child impedance, non-finite admittance, or zero total admittance fails explicitly rather than returning an unexplained infinity/NaN.

## Why there is no circuit string DSL yet

Packages such as `impedance.py` demonstrate that circuit strings can be useful for broad user-facing model construction. CatalysisWorkbench deliberately starts with typed value objects so that topology, element identity, parameter state, validation, and later GUI state are explicit before a parser grammar is introduced.

The first implementation therefore has no hidden shorthand such as `R0-p(R1,C1)` and no automatic topology inference from a string/sample name.

## Parameter state

`EISParameterSpec` stores:

- finite initial value;
- vary/fixed state;
- optional finite lower bound;
- optional finite upper bound.

Caller bounds must contain the initial value. Circuit element domains are enforced in addition to caller bounds:

- R/C/Q values stay strictly positive;
- CPE n stays in `(0, 1]`.

A caller may write a conventional non-negative lower bound `0.0`; the optimizer's effective strict-positive physical domain uses the smallest representable positive float rather than allowing a fitted zero that would make capacitor/CPE equations singular.

No cross-parameter expression/tie system is part of this first EIS stage.

## Circuit evaluation

`evaluate_eis_circuit(circuit, frequency_hz, parameter_values=...)` evaluates exactly on the caller frequency vector.

The evaluation helper:

- requires finite positive frequencies;
- never sorts/regrids them;
- accepts optional explicit overrides addressed by public `element.parameter` keys;
- rejects unknown parameter keys;
- validates overrides against caller bounds and physical element domains;
- returns a detached immutable complex128 array.

## Fitting objective

`fit_eis()` uses `scipy.optimize.least_squares` with the trust-region reflective (`trf`) method and explicit `EISFitConfig` tolerances.

For each measured point:

```text
r_complex = Z_observed - Z_model
```

The optimization vector is the deterministic concatenation:

```text
[Re(r_complex), Im(r_complex)]
```

for the entire measured frequency grid.

This means real and imaginary channels are fitted simultaneously. CatalysisWorkbench does not fit only magnitude, only phase, or only one complex component unless a later Issue explicitly defines such a mode.

### Optimization controls

`EISFitConfig` exposes:

- `xtol`
- `ftol`
- `gtol`
- `max_nfev`

The first implementation uses linear least-squares loss and the SciPy `trf` bounded optimizer. There is no automatic global optimizer/model search.

## Weighting

Default:

```text
weights = None
```

means uniform residual multipliers.

If explicit weights are supplied:

- there must be exactly one multiplier per measured frequency point;
- every multiplier must be finite and strictly positive;
- the same point multiplier is applied to the real and imaginary residual channels.

For point `i` with weight `w_i`:

```text
r_real,objective,i = w_i Re(r_i)
r_imag,objective,i = w_i Im(r_i)
```

There is no automatic modulus weighting, proportional weighting, standard-deviation weighting, or magnitude-dependent reweighting in this stage.

## Physical residual versus optimization objective

The public physical residual is always:

```text
Z_residual = Z_observed - Z_best_fit
```

It is complex and is independent of objective weighting.

`objective_sum_squares` is calculated from the actual weighted/unweighted real+imag objective vector used for fitting. The API therefore does not confuse a point's physical complex deviation with the scalar objective minimized by the optimizer.

## Fixed-only circuit evaluation

If every public circuit parameter is fixed, `fit_eis()` does not run an optimizer. It evaluates the circuit exactly, records zero optimizer evaluations, computes the same physical residual/objective state, and reports that the model was evaluated without optimization.

## Fit result

`EISFitResult` retains:

- source key/label and deterministic numerical SHA-256;
- source frequency direction;
- canonical Hz/ohm units;
- immutable circuit specification;
- explicit fit config;
- exact frequency vector/order;
- exact observed complex impedance;
- exact best-fit complex impedance;
- exact physical complex residual;
- backend-independent fitted parameter values/fixed state/caller bounds;
- explicit weights or uniform-weighting state;
- optimizer success/message/status/evaluation count;
- objective sum of squares;
- number of varying parameters;
- backend/method identity.

This stage does **not** fabricate covariance or parameter standard errors. If uncertainty reporting is added later, it requires a separately reviewed method and regression evidence.

## Fit diagnostics

`summarize_eis_fit()` returns `EISFitDiagnostics`, which mirrors already-computed result state:

- success/message/status/nfev;
- backend/method;
- weighting mode;
- frequency direction;
- circuit element keys;
- parameter keys;
- point count;
- varying-parameter count;
- objective sum of squares.

The diagnostic object does not assign electrochemical mechanisms or reinterpret the statistical quality of a circuit.

## Nyquist plotting

`plot_eis_nyquist(series, ..., imaginary_display=...)` is a passive plotting adapter.

The x data are always:

```text
Re(Z)
```

Two explicit imaginary display modes are supported:

```text
imaginary_display="negative" -> y = -Im(Z)
imaginary_display="raw"      -> y =  Im(Z)
```

The common electrochemical `-Z''` convention is therefore a rendering choice only. Source and fit arrays remain literal `Z' + jZ''`.

Default observed points and optional best-fit curves can be overridden through stable `FigureSpec.series_styles` keys:

- `eis_observed`
- `eis_best_fit`

An optional caller-visible `equal_aspect=True` requests equal Nyquist axes scaling. It is not silently forced.

## Bode plotting

`plot_eis_bode()` renders directly from the complex data:

```text
magnitude = |Z|
phase_deg = arg(Z) * 180 / π
```

The phase is NumPy's principal complex angle. No phase unwrapping is performed.

When no `FigureSpec` is supplied, the publication preset is copied with logarithmic frequency x scale. If the caller supplies a `FigureSpec`, its `xscale` remains authoritative.

The two-panel layout uses caller-visible phase-height and panel-gap fractions. The magnitude panel carries the main title/annotations/legend; the phase panel uses a linear phase y scale and shares the exact frequency x span/order.

Stable Bode style keys are:

- `eis_magnitude_observed`
- `eis_magnitude_best_fit`
- `eis_phase_observed`
- `eis_phase_best_fit`

No numerical EIS transformation is persisted by the plotting function.

## FigureSpec and export

EIS plotting uses the same `FigureSpec`, `PlotStyle`, `SeriesStyle`, local Matplotlib rc isolation, and `export_figure()` infrastructure as existing CatalysisWorkbench figures.

The plotting layer does not call `show()`, mutate global rcParams, or create a technique-specific parallel style model.

## Prior art and license boundary

### `ECSHackWeek/impedance.py` — MIT

Current upstream GitHub metadata identifies `impedance.py` as MIT licensed. It is useful prior art for the broad separation of EIS preprocessing/validation/circuit fitting/visualization, simultaneous real+imag fitting, explicit circuit parameters, and Nyquist/Bode workflows.

CatalysisWorkbench does not copy its circuit-string parser, circuit-element implementation, fitting implementation, or plotting code and does not add it as a dependency for this stage.

### `vyrjana/pyimpspec` — GPL-3.0

Current upstream GitHub metadata identifies `pyimpspec` as GPL-3.0. Its rich circuit validation, complex-impedance analysis, and plotting ecosystem are useful architecture/test references only.

No GPL implementation code is copied or adapted, and `pyimpspec` is not a CatalysisWorkbench dependency.

### Backend dependencies

No new runtime dependency is introduced. The EIS layer uses existing NumPy, SciPy, and Matplotlib dependencies already present in CatalysisWorkbench.

## Explicit non-goals

The initial EIS stage does not provide:

- automatic circuit topology discovery/model selection;
- automatic initial-parameter guesses;
- hidden frequency-unit conversion;
- hidden frequency sorting/interpolation/resampling;
- hidden `Z''`/`-Z''` scientific conversion;
- automatic weighting selection;
- parameter-expression/tie DSL;
- Warburg/finite-length diffusion elements;
- inductors;
- transmission lines;
- Gerischer/distributed elements;
- DRT;
- Kramers-Kronig validation;
- electrochemical mechanism assignment from circuit labels;
- proprietary instrument-binary parsing;
- a GUI or new plotting framework.

Those capabilities require separate Issues with their own equations, parameter conventions, validation evidence, and license review.
