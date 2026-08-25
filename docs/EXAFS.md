# EXAFS k-space and forward-FT contract

This v0.5 block adds explicit χ(k) validation, k weighting, Hanning-window preparation, a retained complex forward Fourier transform, and passive FT-EXAFS plotting.

It intentionally does **not** perform Autobk/background subtraction, μ(E)→χ(k) extraction, hidden interpolation, phase correction, back transforms, FEFF fitting, or WT-EXAFS.

## Prior-art boundary

The scientific convention is aligned to the current MIT-licensed `xraypy/xraylarch` forward-transform workflow and the long-standing Athena/Demeter representation of complex χ(R). Larch is a scientific/equation/test reference only; CatalysisWorkbench does not add xraylarch as a runtime dependency and does not copy its implementation.

The declared transform convention is

```text
χ(R) = (Δk / sqrt(pi)) * FFT[padded k^w χ(k) Ω(k)]
ΔR   = pi / (Δk * Nfft)
```

where `w` is the explicit k-weight and `Ω(k)` is the retained FT window.

## χ(k) input semantics

A source trace is a normal immutable core `Series` with:

- x semantic `k` (photoelectron wavenumber);
- explicit inverse-angstrom unit;
- y semantic `chi`;
- dimensionless real finite χ(k);
- non-negative k;
- strictly monotonic ascending or descending k;
- uniform measured Δk.

No source points are silently sorted, smoothed, dropped, interpolated, or converted from energy.

## No hidden interpolation

`prepare_exafs_kspace()` requires the measured uniform k points to align to integer positions of a zero-origin Δk transform grid.

For example, a trace sampled at

```text
2.00, 2.05, 2.10, ... Å^-1
```

is aligned to a zero-origin 0.05 Å^-1 grid. Missing positions below the first measured point may be zero-filled only when the retained FT window is exactly inactive there.

An offset grid such as

```text
2.025, 2.075, 2.125, ... Å^-1
```

is rejected rather than interpolated silently. Resampling is a separate scientific operation and is outside this block.

## EXAFSKSpaceSpec

`EXAFSKSpaceSpec` retains all initial preparation choices:

- `kmin`;
- `kmax`;
- `kweight`;
- low-k taper width `dk`;
- high-k taper width `dk2` (`dk2 = dk` only when omitted explicitly);
- window name.

The first reviewed window is `hanning` only.

The Hanning convention is cosine-squared tapering with:

```text
low taper:  kmin - dk/2  ->  kmin + dk/2
plateau:    kmin + dk/2  ->  kmax - dk2/2
high taper: kmax - dk2/2 ->  kmax + dk2/2
```

The low and high tapers must not overlap.

The complete active taper support must be covered by measured χ(k). CatalysisWorkbench will not fabricate missing active-window values.

## EXAFSKSpaceResult

`prepare_exafs_kspace()` returns immutable retained state containing:

- source stable key and deterministic source digest;
- exact source k and χ arrays in original order;
- original source direction (`ascending` or `descending`);
- measured Δk;
- explicit zero-origin transform grid;
- χ mapped onto that grid without interpolation;
- retained Hanning window;
- k-weighted χ;
- final windowed, weighted χ used by the forward FT.

Public reconstruction re-derives this state and fails closed if any retained array, grid spacing, source direction, or digest contradicts the source/specification.

## EXAFSFTSpec

`EXAFSFTSpec` contains:

- `nfft` — even FFT length;
- `rmax_angstrom` — explicit retained output limit.

`nfft` must be at least as long as the prepared zero-origin k grid.

The requested R limit must lie within the representable positive half of the declared FFT grid.

## EXAFSFTResult

`forward_ft_exafs()` zero-pads the already prepared state, applies the declared XAFS normalization, and retains:

- R grid;
- ΔR;
- complex χ(R);
- magnitude `|χ(R)|`;
- real part;
- imaginary part;
- principal complex phase (`numpy.angle`).

The real-valued components are cross-checked against the retained complex transform during reconstruction.

The R axis is **not phase corrected**. Peak positions in an uncorrected FT magnitude must not be interpreted as exact crystallographic bond lengths without an appropriate phase treatment.

## Component materialization

`ft_exafs_component(result, component)` converts one retained real-valued component into a core `Series` without recomputing the transform.

Supported components:

- `magnitude`;
- `real`;
- `imaginary`;
- `phase`.

For χ(R) magnitude/real/imaginary, the dimensional exponent follows the chosen k-weight under the declared convention. For example, k-weight 2 produces an `angstrom^-3` component unit. Phase uses radians.

## Plotting

`plot_ft_exafs()` is a passive lazy adapter through the existing `FigureSpec` curve renderer.

It does not:

- change k-weight;
- change kmin/kmax;
- change taper widths/window;
- recompute the FFT;
- phase-correct R;
- interpolate or smooth data;
- infer shells or bond distances.

One axes cannot mix magnitude, real, imaginary, and phase semantics. Multi-sample overlays are made by materializing the same component from each reviewed transform result and placing those `Series` in a `Dataset` with unique stable keys.

The numerical `experimental.characterization` import remains Matplotlib-lazy.

## Example

```python
from catalysis_workbench.experimental.characterization import (
    EXAFSFTSpec,
    EXAFSKSpaceSpec,
    forward_ft_exafs,
    ft_exafs_component,
    plot_ft_exafs,
    prepare_exafs_kspace,
)

prepared = prepare_exafs_kspace(
    chi_k,
    EXAFSKSpaceSpec(
        kmin=3.0,
        kmax=12.0,
        kweight=2,
        dk=1.0,
        dk2=1.0,
    ),
)
ft = forward_ft_exafs(
    prepared,
    EXAFSFTSpec(nfft=2048, rmax_angstrom=6.0),
)
magnitude = ft_exafs_component(ft, "magnitude")
figure, ax = plot_ft_exafs(magnitude)
```

The numerical values in this example are caller choices, not element-specific or chemistry-specific defaults embedded by CatalysisWorkbench.
