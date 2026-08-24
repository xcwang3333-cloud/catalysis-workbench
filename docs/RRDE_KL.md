# RRDE and Koutecky-Levich scientific contract

Issue #28 adds basic rotating ring-disk electrode (RRDE) and Koutecky-Levich (K-L)
analysis. The numerical layer is intentionally conservative: it consumes already
prepared, explicitly aligned electrochemical data and does not perform background
subtraction, smoothing, potential interpolation, branch selection, or instrument-
specific metadata inference.

## Prior-art survey

### MyPyDavid/elchempy — MIT

`MyPyDavid/elchempy` contains dedicated ORR/RRDE and K-L modules. Its RRDE helper uses
the common ORR expressions

- `H2O2[%] = 200 (|Ir|/N) / (|Id| + |Ir|/N)`
- `n = 4 |Id| / (|Id| + |Ir|/N)`

and its electrode helper contains device-specific collection efficiencies such as a
PINE value of `0.38`. Its K-L coefficient module also documents both the
`0.62 ... omega^(1/2)` angular-frequency form and the alternative coefficient used
when rotation is entered directly in rpm.

Useful ideas retained:

- RRDE disk and ring current are separate signals with an explicit collection
  efficiency.
- K-L transport constants must be associated with the actual electrolyte rather than
  inferred from a curve label.
- K-L visualization is naturally a transformed scatter plus linear fit.

CatalysisWorkbench differences:

- no collection efficiency is inferred from an electrode/device name;
- `abs(current)` is never hidden — magnitude use is an explicit mode;
- rotation is always canonicalized to `rad/s` before K-L transformation, so the
  angular-frequency coefficient `0.62` is the only Levich coefficient used by the
  physical-quantity helper;
- no electrolyte constants are bundled or selected automatically.

License: MIT. The implementation here is independent; no source code is copied.

### Achim-Habekost/SpectroElectroChem-Suite — MIT

The RRDE module demonstrates practical disk/ring pairing across rotation rates and
also includes optional background interpolation and smoothing.

Useful idea retained: disk/ring channels and rotation conditions should remain
explicitly addressable.

CatalysisWorkbench difference: background interpolation, smoothing, and branch
reconstruction are upstream preprocessing concerns and are not performed inside the
RRDE metric function.

License: MIT. No source code is copied.

### Polarographica — reference-only method comparison

Polarographica exposes K-L rotation rates and transport parameters to the user and
constructs reciprocal-current versus inverse-square-root rotation plots. It also
contains optional smoothing/baseline corrections and uses an rpm-form coefficient
near `0.201` when deriving physical quantities.

Useful idea retained: physical constants and fit interval must be caller-visible.

CatalysisWorkbench difference: no hidden preprocessing, and no mixing of rpm-form and
angular-frequency-form Levich coefficients. All rotation data are converted to
`rad/s` first.

The repository's license status was not used as a basis for code reuse; it is treated
as reference-only here.

## RRDE contract

### Input

`rrde_metrics(disk, ring, *, collection_efficiency, current_mode)` consumes two
`Series` objects.

Requirements:

- both Series have non-empty stable `Series.key` values;
- both y axes are total `current`, never current density;
- both current units are explicitly supported and are converted to canonical A;
- disk and ring x-axis name, unit, compatibility metadata, shape, and numerical x
  values must match exactly;
- no interpolation or nearest-neighbour alignment is performed;
- `collection_efficiency = N` is an explicit finite scalar with `0 < N <= 1`;
- no electrode or reaction label is used to infer `N` or reaction stoichiometry.

### Current modes

`current_mode='nonnegative'`
: input currents must already be non-negative. This is appropriate when the caller has
  explicitly prepared magnitude-like current data upstream.

`current_mode='magnitude'`
: the calculation explicitly uses `abs(Id)` and `abs(Ir)`. The choice is stored in the
  result.

There is deliberately no implicit magnitude conversion. Typical raw ORR data with a
cathodic negative disk current and anodic positive ring current therefore require the
caller to request `magnitude` explicitly.

### ORR-style equations

With the selected non-negative disk and ring magnitudes `Id` and `Ir` and explicit
collection efficiency `N`:

`denominator = Id + Ir / N`

`n = 4 Id / denominator`

`H2O2[%] = 200 (Ir / N) / denominator`

The implementation does not clip derived values to nominal physical ranges. Invalid
measurements remain visible to downstream QA instead of being silently repaired.
A zero denominator is rejected.

### Provenance

The immutable result stores deterministic `SourceDataRef` values for disk and ring,
canonical A arrays, aligned condition values, condition axis semantics,
`collection_efficiency`, and `current_mode`.

## Koutecky-Levich contract

### Input Series

`fit_koutecky_levich(series, fit_window, *, fit_window_unit, current_mode)` requires:

- x-axis semantic `rotation_rate`;
- explicit rotation unit supported by the shared quantity layer (`rpm`, `rps`, or
  `rad/s`);
- y-axis semantic either total `current` or `current_density`;
- total-current units convertible to A, or current-density units convertible to
  A/cm^2;
- current-density input must explicitly declare geometric normalization;
- caller-selected physical rotation fit window;
- at least three selected points, all with positive rotation rate and non-zero finite
  current.

The fit-window bounds are converted to canonical `rad/s` and select measured points
only. Boundary interpolation is not performed.

### Current modes

`current_mode='signed'`
: fit reciprocal signed current exactly as supplied after unit conversion.

`current_mode='nonnegative'`
: require all selected currents to be strictly positive.

`current_mode='magnitude'`
: explicitly fit reciprocal current magnitude.

The selected mode is stored in provenance. No sign flip is inferred from reaction
labels.

### K-L transformation and fit

Every selected rotation rate is first converted to angular frequency `omega [rad/s]`.
The regression variables are

`x_KL = omega^(-1/2)`

`y_KL = 1 / I` for total-current input, or `1 / j` for current-density input.

A free-intercept linear model is fit:

`y_KL = intercept + slope * x_KL`

The result stores selected canonical rotation/current values, transformed data,
fitted values, slope, intercept, R^2, fit window, current basis/mode, source digest,
and input/canonical units.

The kinetic reciprocal term is the fitted intercept; no forced-zero fit is used.

## Optional apparent electron number from a K-L slope

`kl_electron_number(...)` is deliberately separate from the numerical fit because it
requires transport constants that are experiment-specific.

For canonical angular frequency, the Levich coefficient is

`B = 0.62 n F D^(2/3) nu^(-1/6) C`

for geometric current density, so

`1/j = 1/j_k + [1/B] omega^(-1/2)`.

For total current, electrode geometric area `A` is also required:

`B_I = 0.62 n F A D^(2/3) nu^(-1/6) C`.

Required explicit inputs use the documented cgs electrochemical convention:

- `D`: diffusion coefficient in `cm^2/s`;
- `nu`: kinematic viscosity in `cm^2/s`;
- `C`: bulk concentration in `mol/cm^3`;
- geometric electrode area in `cm^2` only for total-current fits;
- Faraday constant defaults only to the project's shared explicit constant
  `96485.33212 C/mol`; callers may inspect it in provenance.

No default oxygen concentration, diffusion coefficient, viscosity, electrolyte,
reaction label, or disk area is inferred.

Electron-number derivation is allowed only for `magnitude` or `nonnegative` K-L fits
with a positive finite slope. A signed fit remains valid as a regression but is not
silently converted to a positive physical electron number.

## Plotting

RRDE and K-L plotting are thin adapters to the shared visualization layer.

- RRDE derived metrics are rendered from already calculated result Series.
- K-L plotting renders transformed selected points and the stored fitted line.
- plotting performs no realignment, refitting, smoothing, sign conversion, or
  transport-constant calculation.

## Non-goals

Issue #28 does not implement:

- raw instrument-file parsing;
- disk/ring time or potential interpolation;
- background subtraction;
- smoothing or spike removal;
- automatic rotation-rate discovery from filenames;
- instrument model to collection-efficiency lookup;
- automatic electrolyte transport constants;
- automatic ORR/OER reaction inference;
- forced-zero K-L fitting;
- multi-potential K-L extraction from an LSV matrix.
