# XAS / XANES contract

The first v0.5 XAS layer provides explicit one-dimensional XAS semantics, caller-controlled energy-reference correction, transparent pre/post-edge XANES normalization, and passive publication rendering. It is deliberately smaller than a full XAS environment such as Larch/Larix/Artemis.

## Scope

Implemented in this first block:

- validation of energy/eV XAS `Series`;
- explicit additive energy shift;
- caller-supplied E0;
- inclusive measured-point pre-edge and post-edge windows;
- centered polynomial fits for pre/post-edge curves;
- positive edge-step normalization;
- immutable retained normalization state;
- explicit E-E0 transformation;
- passive raw or normalized XANES comparison plotting.

Deferred to later v0.5 blocks:

- energy-to-k conversion and EXAFS preparation;
- Fourier-transformed EXAFS;
- wavelet-transform EXAFS;
- EXAFS fitting-result integration.

Explicitly outside this layer:

- automatic E0/edge detection;
- oxidation-state or white-line chemistry assignment;
- beamline-specific raw-file ingestion;
- FEFF path generation;
- Artemis-class EXAFS fitting;
- hidden smoothing/interpolation/alignment;
- CHE or electronic-structure analysis.

## Prior art and license boundary

`xraypy/xraylarch` is the principal scientific reference for the XAS workflow. Current upstream is MIT licensed and separates edge-energy selection, pre-edge fitting, post-edge fitting, and edge-jump normalization. CatalysisWorkbench uses those transparent workflow concepts as scientific/equation/test references but does not copy upstream implementation and does not add the full xraylarch dependency stack for this narrow post-processing layer.

The local API/provenance/lazy-rendering pattern follows the reviewed Raman, FTIR, XPS, BET, and other characterization modules.

## Input semantics

A source XAS trace is a normal immutable core `Series`.

Required absolute-energy semantics:

- x axis name: `energy`;
- x unit: eV;
- y axis name: `mu` or `absorption` for unnormalized input, or `normalized_mu` for an already normalized trace;
- numerical values must be real and finite;
- missing values are rejected;
- energy must be strictly monotonic ascending or descending with no duplicate energies.

The original direction is retained. The XAS layer does not silently sort measured data.

Normalized absorption is dimensionless. Common explicit dimensionless/arbitrary-unit spellings are accepted for validation, while library-produced normalized data use unit `1`.

## Energy-reference correction

`shift_xas_energy(series, shift_ev, reference=None)` performs exactly

```text
E_corrected = E_source + shift_ev
```

The shift is caller supplied. No foil database, edge table, absorber label, or chemistry name changes the numerical value.

When `reference` is supplied it is recorded as provenance only. Repeated explicit shifts are allowed and retained in ordered processing history; the cumulative library-applied shift is recorded as metadata. This is intentional because a caller may make several explicit, auditable reference corrections during data preparation.

## XASWindow

`XASWindow(start_ev, end_ev)` defines an inclusive measured-energy interval. It requires

```text
start_ev < end_ev
```

Normalization windows must lie fully inside the measured range. No synthetic boundary points are inserted.

## XANESNormalizationSpec

`XANESNormalizationSpec` contains all numerical choices needed by the initial normalization:

- `e0_ev`;
- `pre_edge` window;
- `post_edge` window;
- `pre_edge_order`;
- `post_edge_order`.

E0 is mandatory and must lie strictly inside the measured energy range. The pre-edge window must end strictly below E0 and the post-edge window must start strictly above E0.

Polynomial orders are explicit non-negative integers. The initial reviewed range is 0 through 4. Each selected measured window must contain at least `order + 1` distinct energies and its least-squares design matrix must have full rank.

The library does not estimate E0 automatically in this block.

## Centered polynomial equations

Fits use the centered coordinate

```text
delta_E = E - E0
```

For coefficients stored in ascending power order:

```text
P_pre(delta_E)  = a0 + a1*delta_E + a2*delta_E^2 + ...
P_post(delta_E) = b0 + b1*delta_E + b2*delta_E^2 + ...
```

Because the coordinate is centered at E0, the fitted values extrapolated to E0 are exactly the intercept coefficients:

```text
P_pre(0)  = a0
P_post(0) = b0
```

The edge step is therefore

```text
edge_step = b0 - a0
```

It must be finite and strictly positive. CatalysisWorkbench does not apply `abs(edge_step)`, flip data signs, or silently repair an unphysical result.

The normalized absorption is

```text
mu_norm(E) = [mu(E) - P_pre(E - E0)] / edge_step
```

This is edge-step normalization. It does not divide by the complete post-edge curve and therefore does not force the far post-edge region to a constant value of one.

## XANESNormalizationResult

`normalize_xanes()` returns an immutable `XANESNormalizationResult` retaining:

- source stable key;
- deterministic source digest;
- exact source energy and absorption arrays;
- E0;
- pre/post windows and polynomial orders;
- centered pre/post polynomial coefficients;
- pre/post polynomial curves evaluated on the complete source grid;
- edge step;
- normalized core `Series`.

Public reconstruction fails closed if retained curves contradict coefficients/energy, edge step contradicts the two intercepts, normalized data contradict the retained fit state, or source provenance contradicts the normalized metadata.

The normalized `Series` uses x semantic `energy` in eV and y semantic `normalized_mu` with unit `1`.

## Explicit E-E0 comparison

`xanes_relative_energy(result)` constructs a new `Series` with

```text
x = E - E0
```

and unchanged normalized y values. The x semantic is `energy_relative_to_e0`, unit eV, with E0 retained in axis metadata.

This is a numerical transformation and is never performed implicitly by plotting.

## Plotting

`plot_xanes()` is a lazy passive adapter through the existing `FigureSpec` and shared curve renderer.

It performs no:

- energy correction;
- normalization;
- E0 lookup/alignment;
- sorting;
- interpolation;
- smoothing;
- refitting;
- chemical assignment.

A multi-spectrum overlay must use one common energy-reference semantic (all absolute energy or all E-E0) and one common absorption semantic (all raw or all normalized). Mixing those states fails explicitly.

The numerical `experimental.characterization` import remains Matplotlib-lazy; Matplotlib is imported only when a plotting function is called.

## Example

```python
from catalysis_workbench.experimental.characterization import (
    XANESNormalizationSpec,
    XASWindow,
    normalize_xanes,
    plot_xanes,
    shift_xas_energy,
    xanes_relative_energy,
)

corrected = shift_xas_energy(source, 0.35, reference="caller-supplied foil alignment")
result = normalize_xanes(
    corrected,
    XANESNormalizationSpec(
        e0_ev=7112.0,
        pre_edge=XASWindow(7040.0, 7080.0),
        post_edge=XASWindow(7160.0, 7240.0),
        pre_edge_order=1,
        post_edge_order=2,
    ),
)

figure, ax = plot_xanes(result.normalized)
relative = xanes_relative_energy(result)
```

Window locations and polynomial orders above are illustrative caller choices, not element-specific defaults embedded by CatalysisWorkbench.
