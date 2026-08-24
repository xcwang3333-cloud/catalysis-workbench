# Quantitative BET fitting contract

Issue #95 adds the first quantitative BET surface-area layer on top of the reviewed v0.3 gas-sorption foundation. It consumes prepared `Series` objects, explicit `SorptionCondition` metadata, and caller-supplied `SorptionWindow` regions. It does not introduce a second isotherm model or an automatic BET-range selector.

## Scientific boundary

The first implementation is deliberately conservative:

- adsorption branch identity is explicit and must already be `adsorption`;
- `P/P0` must already be represented as dimensionless fraction unit `1`;
- percent input is not silently converted inside BET fitting; use `convert_relative_pressure()` first;
- the BET region is one caller-supplied `SorptionWindow` and contains measured points only;
- source ascending or descending storage order is retained;
- no sorting, interpolation, synthesized endpoints, smoothing, resampling, outlier deletion, branch inference, or adsorbate-property lookup occurs;
- ordinary least-squares linearity is reported but is not sufficient by itself to accept a region;
- a fit is accepted only when the explicitly implemented physical-consistency checks pass.

The basic measured-isotherm semantics remain documented in [`GAS_SORPTION.md`](GAS_SORPTION.md).

## Input contract

Start from a prepared sorption branch:

```python
from catalysis_workbench.experimental.characterization import (
    SorptionCondition,
    SorptionWindow,
    fit_bet,
    prepare_sorption_series,
)

prepared = prepare_sorption_series(
    raw,
    SorptionCondition(
        adsorbate="N2",
        measurement_temperature_k=77.0,
        branch="adsorption",
        standard_temperature_k=273.15,
        standard_pressure_kpa=101.325,
    ),
)

result = fit_bet(
    prepared,
    SorptionWindow(0.01, 0.18, "BET region"),
    cross_section_nm2=0.162,
)
```

`cross_section_nm2=0.162` above is an explicit caller choice for the example. CatalysisWorkbench does not infer this value from the string `"N2"`.

The selected region must contain at least three measured points and every selected pressure must satisfy

\[
0 < P/P_0 < 1.
\]

Three points is a numerical regression minimum in this API, not a recommendation that three-point BET reporting is universally sufficient experimentally.

## BET transform and regression

For each selected measured point define

\[
p = P/P_0
\]

and let `n` be the measured adsorbed quantity in its declared source loading unit. The linear BET transform is

\[
y_{\mathrm{BET}} = \frac{p}{n(1-p)}.
\]

CatalysisWorkbench applies ordinary least squares to the exact selected measured arrays:

\[
y_{\mathrm{BET}} = i + s p,
\]

where `i` is the intercept and `s` is the slope.

The result retains the exact selected source indices, pressure array, loading array, BET transform, fitted transform, slope, intercept, correlation coefficient, and

\[
R^2=r^2.
\]

`R²` is diagnostic state only. No hidden `R²` cut-off accepts or rejects the region.

## Derived BET parameters

The initial reviewed equations are

\[
C = \frac{s}{i}+1,
\]

\[
n_m = \frac{1}{s+i},
\]

and

\[
p_m = \frac{1}{\sqrt{C}+1}.
\]

`n_m` initially has the same loading unit as the supplied isotherm. Its explicit conversion to mol/g for surface-area calculation is retained separately.

## Core consistency checks

`evaluate_bet_region()` reports three independent checks in `BETConsistencyResult`.

### 1. Positive parameter state

An accepted region requires finite positive intercept, positive `C`, and positive `n_m`.

### 2. Rouquerol transform monotonicity

Define

\[
R(p)=n(1-p).
\]

The selected values must be strictly increasing with increasing `p`. If source storage is descending, the criterion is evaluated on a temporary increasing-pressure view only. Public retained arrays remain in source order.

### 3. Monolayer loading inside the measured selected span

The fitted `n_m` must lie strictly between the minimum and maximum measured loading values in the selected region.

`evaluate_bet_region()` may be used to inspect these checks without claiming an accepted BET area. `fit_bet()` calls the same evaluation and fails explicitly if any required check is false.

A region with excellent or even exact linearity can therefore still be rejected.

## Relationship to Rouquerol, pyGAPS, BETSI, SESAMI, and BEaTmap

The first CatalysisWorkbench implementation intentionally distinguishes core consistency checks from later automatic-region algorithms.

- `pauliacomi/pyGAPS` (MIT) is a scientific/API reference for the BET transform, derived parameters, explicit pressure limits, and core consistency checks.
- `nakulrampal/betsi-gui` (MIT, current `LICENSE.txt` verified) demonstrates exhaustive candidate-region analysis and an expanded reproducibility workflow. Its automatic optimum, fixed minimum-point policy, R² threshold, dense PCHIP reconstruction, and extended optimum criterion are not silently imported here.
- `hjkgrp/SESAMI_web` (MIT) is workflow prior art for reproducible candidate-region search.
- `PMEAL/BEaTmap` (MIT) is reference for individually visible criteria and later candidate-region heatmap visualization.
- Osterrieth et al., *Advanced Materials* 2022, DOI `10.1002/adma.202201502`, demonstrates that several regions can satisfy consistency criteria and that manual region choice can be irreproducible.

CatalysisWorkbench therefore records one explicit caller-selected region and does not claim that maximum linearity identifies a unique scientifically correct region.

No implementation code from these reference projects is copied or adapted and none is added as a dependency by Issue #95.

## Loading conversion and surface area

Regression remains in the source loading unit. Once a region passes consistency, `fit_bet()` converts the fitted monolayer loading to mol/g only for the surface-area calculation.

### `mmol/g`

\[
n_m(\mathrm{mol/g}) = 10^{-3}n_m(\mathrm{mmol/g}).
\]

### `mol/kg`

\[
n_m(\mathrm{mol/g}) = 10^{-3}n_m(\mathrm{mol/kg}).
\]

### `cm^3(STP)/g`

The existing sorption contract already requires explicit standard gas temperature `T_s` and pressure `P_s`. Using the ideal-gas relation and `V` in cm³/g,

\[
n_m(\mathrm{mol/g}) = \frac{P_s V 10^{-3}}{R T_s},
\]

where `P_s` is in kPa, `V × 10^-3` is L/g, and the numerical SI gas constant has equivalent units of kPa·L·mol⁻¹·K⁻¹.

### `mg/g`

Mass loading requires a caller-supplied adsorbate molar mass `M` in g/mol:

\[
n_m(\mathrm{mol/g}) = \frac{n_m(\mathrm{mg/g})10^{-3}}{M}.
\]

No molar mass is inferred from the adsorbate name.

### Specific surface area

With explicit molecular cross-sectional area `σ` in nm²/molecule,

\[
A_{BET}=n_m N_A \sigma 10^{-18},
\]

reported as m²/g.

The retained `BETFitResult` records the cross-section and any molar-mass or standard-gas conversion state required to reproduce the calculation.

## Public result state

The reviewed initial API is:

- `BETConsistencyResult` — independent pass/fail consistency state;
- `BETRegionEvaluation` — exact candidate-region arrays, OLS state, derived parameters, source identity, experimental condition, and consistency state;
- `evaluate_bet_region()` — inspect one explicit measured candidate region without accepting it silently;
- `BETFitResult` — accepted region plus explicit loading-to-molar conversion and specific surface area;
- `fit_bet()` — fail-closed accepted-fit entry point;
- `BETFitDiagnostics` / `summarize_bet_fit()` — value-oriented summary copied from an already computed fit;
- `plot_bet_fit()` — lazy passive plotting of retained BET points and retained OLS line.

Public evaluation/result constructors revalidate their numerical relationships. Contradictory transforms, regression parameters, consistency state, loading conversion, or surface area cannot be reconstructed as valid immutable result state.

No covariance or standard error is fabricated by this initial implementation.

## Publication plotting

`plot_bet_fit()` consumes only an accepted `BETFitResult`:

```python
fig, ax = plot_bet_fit(result, spec)
```

It draws:

- retained selected BET points under stable key `bet_observed`;
- retained OLS line under stable key `bet_fit`.

The adapter does not refit, search regions, convert units, reorder points, recalculate criteria, smooth, or resample. Typography, figure/axes geometry, line/marker state, labels, limits, legend, annotations and export remain controlled by `FigureSpec`.

Importing `catalysis_workbench.experimental.characterization` remains Matplotlib-lazy; plotting code is imported only when `plot_bet_fit()` is called.

## Deferred work

Issue #95 does not implement:

- exhaustive candidate-region enumeration;
- automatic or unique optimal BET-range selection;
- hidden R² thresholds;
- BETSI PCHIP reconstruction or extended optimum logic;
- BEaTmap-style range heatmaps;
- pore volume calculations;
- BJH, DH, DFT/QSDFT/NLDFT pore-size distributions;
- t-plot, alpha-s, Dubinin, or generic isotherm-model fitting;
- hysteresis classification;
- hidden adsorbate cross-section/molar-mass lookup;
- automatic branch inference;
- GUI behavior;
- a version/tag/release/package-publication change.
