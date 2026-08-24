# Shared constrained peak fitting

Issue #75 implements the first v0.4 scientific module: a technique-agnostic constrained one-dimensional peak-fitting foundation backed by `lmfit`.

The purpose of this layer is not to provide automatic spectroscopy interpretation. CatalysisWorkbench owns explicit scientific state, validation, provenance, stable identities, and backend-independent results; `lmfit` supplies mature nonlinear optimization and line-shape evaluation.

## Public API

The supported public surface is exported from `catalysis_workbench.processing`:

- `FitParameterSpec`
- `PeakComponentSpec`
- `PeakFitSpec`
- `FittedParameter`
- `PeakFitResult`
- `PeakFittingError`
- `fit_peaks`

The durable CatalysisWorkbench API does not expose mutable `lmfit.Parameter`, `Parameters`, `Model`, or `ModelResult` objects.

## Supported model families

The initial deliberately bounded model catalogue is:

| Public model | Public input parameters | Backend |
| --- | --- | --- |
| `gaussian` | `amplitude`, `center`, `sigma` | `lmfit.models.GaussianModel` |
| `lorentzian` | `amplitude`, `center`, `sigma` | `lmfit.models.LorentzianModel` |
| `voigt` | `amplitude`, `center`, `sigma`, `gamma` | `lmfit.models.VoigtModel` |
| `pseudo_voigt` | `amplitude`, `center`, `sigma`, `fraction` | `lmfit.models.PseudoVoigtModel` |
| `doniach` | `amplitude`, `center`, `sigma`, `gamma` | `lmfit.models.DoniachModel` |

Model parameters use the corresponding lmfit line-shape definitions. In particular, `amplitude` is the backend model amplitude parameter rather than a generic peak height, and `sigma` is the backend width parameter rather than a universal FWHM.

CatalysisWorkbench validates backend model domains before optimization so that an invalid caller value cannot be silently clipped by lmfit. Width `sigma` must start strictly above zero; pseudo-Voigt `fraction` must respect the backend `[0, 1]` domain. Additional model families require a separate scientific consumer and regression tests.

## Parameter specifications and ties

`FitParameterSpec` records:

- finite initial `value`;
- `vary=True` or fixed state;
- optional finite `lower` and `upper` bounds;
- optional explicit expression/tie.

A tied parameter must set `vary=False`.

Public expressions reference stable component and parameter identities with braces:

```python
FitParameterSpec(
    1.5,
    vary=False,
    expr="{left.center} + 2.5",
)
```

The public reference syntax is `{component_key.parameter_name}`. CatalysisWorkbench translates these stable public references into backend parameter names internally. Unknown references and circular dependencies fail before optimization when determinable.

Component keys must match `[A-Za-z][A-Za-z0-9_]*` and must be unique within a fit. Human-readable labels and assignment metadata are not mathematical identity.

## Fit window and source data

`fit_peaks()` accepts one real-valued core `Series` and one `PeakFitSpec`.

The input contract is conservative:

- x and fit-window y values must be finite;
- x must be strictly monotonic, ascending or descending;
- source order is preserved;
- the fit window is explicit, low-to-high numerically, and inclusive of measured points;
- no sorting, interpolation, resampling, smoothing, normalization, peak detection, or automatic component-count selection occurs;
- complex data are rejected;
- the fit window must contain at least three measured points and more points than independently varying public parameters.

The same physical synthetic peak stored ascending or descending should recover equivalent fitted parameters while retaining its original storage direction in the result.

## Background

Issue #75 deliberately does not implement a baseline or spectroscopy-specific background algorithm.

`PeakFitSpec.background` may be:

- `None`, meaning an explicit zero background; or
- a caller-supplied finite numeric array with exactly one value for every point in the source `Series`.

The source-aligned background is cropped by the same fit-window mask and retained in the result.

The optimization target is:

```text
observed_y - background
```

The returned total fit is:

```text
best_fit_y = background + modeled_peaks
```

XPS Shirley/Tougaard backgrounds and general automatic baseline estimation belong to later dedicated modules; they are not hidden inside this shared fitter.

## Weights

`PeakFitSpec.weights` are optional non-negative residual multipliers on the selected fit-window grid. Their required length is therefore the number of measured points inside the fit window, not the full source length.

When supplied, the backend objective uses weighted residuals. `PeakFitResult.residual` remains the unweighted physical residual:

```text
residual = observed_y - best_fit_y
```

The weights do not imply a specific statistical uncertainty model. Callers remain responsible for choosing weights that match their measurement model.

## Result and uncertainty semantics

`PeakFitResult` retains:

- source key, label, axis names/units, and deterministic source-data SHA-256;
- the exact `PeakFitSpec` recipe;
- fit-window x and observed y;
- exact background used;
- total fitted y;
- individual component curves in stable-key order;
- unweighted physical residual;
- fitted parameter summaries addressed as `component.parameter`;
- optional parameter standard errors and correlations;
- optional covariance matrix plus deterministic public parameter order;
- chi-square, reduced chi-square, AIC/BIC where the backend supplies meaningful values;
- varying-parameter count, success state, message, method, and backend identity.

Scientific arrays stored on result objects are detached and read-only.

If lmfit cannot estimate a parameter standard error or covariance matrix, CatalysisWorkbench reports that value as `None`. Missing uncertainty is never replaced by zero.

When all public parameters are fixed or expression-constrained, no optimizer is run. CatalysisWorkbench evaluates the model directly, reports zero varying parameters, preserves the physical residual, and does not fabricate covariance/AIC/BIC uncertainty claims.

## Example

```python
import numpy as np

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.processing import (
    FitParameterSpec,
    PeakComponentSpec,
    PeakFitSpec,
    fit_peaks,
)

x = np.linspace(-5.0, 5.0, 401)
y = 1.0 + 12.0 / (0.8 * np.sqrt(2.0 * np.pi)) * np.exp(
    -((x - 0.75) ** 2) / (2.0 * 0.8**2)
)
source = Series(
    x=x,
    y=y,
    key="spectrum-1",
    x_axis=Axis("energy", unit="eV"),
    y_axis=Axis("intensity", unit="counts"),
)

peak = PeakComponentSpec(
    key="peak_a",
    model="gaussian",
    parameters={
        "amplitude": FitParameterSpec(10.0, lower=0.0),
        "center": FitParameterSpec(0.5, lower=-2.0, upper=2.0),
        "sigma": FitParameterSpec(1.0, lower=0.1, upper=2.0),
    },
)

result = fit_peaks(
    source,
    PeakFitSpec(
        x_min=-4.0,
        x_max=4.0,
        components=(peak,),
        background=np.ones(source.n_points),
    ),
)
print(result.parameters["peak_a.center"].value)
```

## Explicit non-goals of Issue #75

This foundation does not automatically:

- detect peaks;
- choose component count;
- assign chemical species or oxidation states;
- apply XPS binding-energy correction;
- choose XPS spin-orbit separation or branching ratio;
- calculate Shirley or Tougaard backgrounds;
- estimate a general spectroscopy baseline;
- smooth or normalize spectra;
- perform global/sequential multi-spectrum fitting;
- plot fit results;
- expose a GUI.

These boundaries are intentional. XPS semantics/background preparation and constrained XPS doublets are the next dedicated v0.4 stages.
