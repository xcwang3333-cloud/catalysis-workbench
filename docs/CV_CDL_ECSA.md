# CV, double-layer capacitance (Cdl), and ECSA

Issue #26 implements the common scan-rate CV route to double-layer capacitance and an explicit, assumption-visible conversion from Cdl to ECSA. The module deliberately does not treat every surface-area estimate as interchangeable and does not decide for the user which potential region is non-Faradaic.

## Scientific prior art

The implementation was designed after reviewing both open-source workflows and electrochemical reporting guidance.

### Open-source references

- `Catalysis-for-Energy-Conversion/EC-Lab-Automated-Analysis-Project` — MIT licensed. Its dedicated Cdl workflow extracts forward and backward sweep currents at a user-selected potential, uses bracketed linear interpolation without extrapolation, calculates a half-current difference, and fits the result versus scan rate. Its source code uses a free-intercept linear regression even though one part of the manual describes a through-origin fit. CatalysisWorkbench adopts the useful explicit-target and bracket-only interpolation ideas, but does not copy code.
- The same project silently prefers current density when available and falls back to total current, drops invalid rows, skips malformed steps, and applies an absolute value to the half-current difference. CatalysisWorkbench intentionally does none of those things: current basis, missing-data policy, and sign handling are explicit API choices.
- `gcarrascohuertas/electrochemical_ECSA_processing_autolab` — GPL-3.0. This project is reference-only. It mainly demonstrates a Randles-Sevcik / peak-current ECSA route and therefore reinforces that different ECSA methods must not be collapsed into one generic calculation. No code is copied or adapted.

### Reporting cautions

Electrocatalysis literature repeatedly emphasizes that Cdl-based ECSA requires a user-justified non-Faradaic window and a material/electrolyte-specific capacitance assumption. The specific capacitance `Cs` is not universal, and Cdl is not equivalent to active-site count. CatalysisWorkbench therefore records `Cs` explicitly and never supplies a hidden default.

## Scope

Issue #26 covers only:

1. explicit sampling of anodic and cathodic CV sweeps at a caller-selected potential;
2. the common half-current-difference versus scan-rate Cdl fit;
3. conversion of Cdl to ECSA using an explicit caller-supplied specific capacitance;
4. traceable plotting of the original CV sweeps and already calculated Cdl fits.

It does not implement Randles-Sevcik ECSA, hydrogen underpotential-deposition ECSA, CO stripping, BET area, adsorption-based site counting, or automatic non-Faradaic-window discovery.

## CV sweep contract

A Cdl measurement is represented by paired anodic and cathodic `Series` at one explicit scan rate.

Each sweep must satisfy all of the following:

- x-axis semantic name is `potential` with an explicit unit and explicit `reference` metadata;
- y-axis semantic name is either `current` or `current_density`;
- current units are supported by the shared Issue #19 quantity layer;
- current-density input must explicitly declare geometric-area normalization;
- anodic potential is strictly increasing;
- cathodic potential is strictly decreasing;
- after unit conversion and reversing the cathodic grid, the two potential grids match exactly within the documented numerical tolerance;
- NaN, infinity, duplicate potential points, empty data, and mismatched grids fail explicitly;
- the pair has a non-empty stable key and a positive finite scan rate with explicit units.

No sweep is silently paired by filename, display label, or ordering.

## Sampling at the declared potential

The caller supplies the physical potential and unit used for Cdl analysis. The library does not determine whether this potential is non-Faradaic.

Two sampling modes are supported:

- `exact`: the target potential must be present on the measured grid;
- `linear`: a one-dimensional linear interpolation is permitted only between the two measured points that bracket the target within one monotonic sweep.

Neither mode extrapolates. Interpolation never aligns two sweeps to a new common grid; the pair grid itself must already be compatible.

## Half-current-difference equation

At a selected potential `E*` and scan rate `v`:

```text
DeltaI_half(v) = [I_anodic(E*) - I_cathodic(E*)] / 2
```

For geometric current density:

```text
Deltaj_half(v) = [j_anodic(E*) - j_cathodic(E*)] / 2
```

Sign handling is explicit:

- `signed` preserves the algebraic half difference;
- `magnitude` applies `abs(...)` only because the caller requested it.

The library never hides an absolute-value conversion.

## Cdl fit

The fitted model is, by default, a free-intercept linear regression:

```text
DeltaI_half = Cdl * v + b
```

or, for geometric current density:

```text
Deltaj_half = Cdl,geo * v + b
```

where scan rate is converted to `V/s` before fitting.

A minimum of three distinct scan rates is required. Duplicate scan rates, non-finite values, or zero scan-rate variance fail explicitly. Results are sorted by canonical scan rate for deterministic provenance and plotting.

The result records:

- canonical scan rates;
- sampled anodic and cathodic current/current-density values;
- signed or magnitude half-current differences;
- target potential and reference;
- sampling method and difference mode;
- current basis;
- slope, intercept, R-squared and point count;
- exact pair keys and deterministic source references/digests.

A non-positive fitted slope is rejected as an invalid Cdl result rather than silently applying an absolute value to the slope.

## Dimensional meaning of Cdl

The current basis changes the physical dimension of the fitted slope:

- total-current fit: `A / (V/s) = F`, so the result is total `Cdl` in farads;
- geometric-current-density fit: `(A/cm^2) / (V/s) = F/cm^2_geo`, so the result is geometric-area-normalized Cdl.

These two results are scientifically distinct and cannot silently overlay as equivalent data.

## ECSA conversion

The conventional relation is:

```text
ECSA = Cdl_total / Cs
```

where `Cs` is an explicitly supplied specific capacitance in `F/cm^2_ECSA` or a supported prefixed equivalent.

There is no default `Cs`.

### Total-current-derived Cdl

If the Cdl fit used total current, the fitted slope is already total capacitance:

```text
ECSA_cm2 = Cdl_F / Cs_F_per_cm2
```

### Geometric-current-density-derived Cdl

If the Cdl fit used geometric current density, its slope is `F/cm^2_geo`. Dividing it directly by `Cs` would yield a dimensionless roughness factor, not an area. CatalysisWorkbench therefore requires an explicit geometric electrode area:

```text
Cdl_total_F = Cdl_geo_F_per_cm2 * A_geo_cm2
ECSA_cm2 = Cdl_total_F / Cs_F_per_cm2
```

This prevents a dimensionless area ratio from being mislabeled as ECSA.

`Cs` must be finite and strictly positive. Its original value/unit and caller-provided basis/source description are retained in result provenance.

## Circular-normalization guard

Issue #26 may consume only total current or geometrically normalized current density. A current density already normalized by ECSA, catalyst mass, metal mass, BET area, or another non-geometric denominator cannot be used to derive Cdl/ECSA.

This prevents circular calculations such as deriving ECSA from an already ECSA-normalized current.

## Plotting boundary

Publication adapters receive already validated/calculated data. They do not:

- select a non-Faradaic potential;
- infer scan rate;
- pair sweeps;
- interpolate across experiments;
- calculate Cdl or ECSA;
- take absolute values;
- normalize current;
- choose a representative condition;
- aggregate replicates.

CV overlays and Cdl fit plots reuse the shared `FigureSpec`/renderer infrastructure, so visual controls remain consistent with the rest of CatalysisWorkbench.

## Explicit non-goals

Issue #26 does not claim that Cdl-derived ECSA equals the number of catalytically active sites. It does not provide a universal `Cs`, auto-detect double-layer windows, correct iR drop, convert references, estimate BET area, or derive reaction-specific site density.
