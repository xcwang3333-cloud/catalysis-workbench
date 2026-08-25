# WT-EXAFS numerical and visualization contract

WT-EXAFS is an explicit numerical transform in v0.5, not a plotting effect. This block implements one reviewed analytic Cauchy wavelet convention and retains the full complex k–R transform state.

## Prior-art boundary

The scientific reference is the continuous Cauchy wavelet approach used for EXAFS by Munoz, Argoul and Farges and represented in the MIT-licensed `xraypy/xraylarch` workflow. Larch documents WT-EXAFS as a joint k/R representation and expects a uniform k grid starting at zero.

CatalysisWorkbench does not add xraylarch as a runtime dependency and does not copy its historical implementation. The v0.5 API makes Cauchy order and the R grid separate explicit parameters instead of inferring one from the other.

## Input contract

`cauchy_wt_exafs()` consumes a reviewed EXAFS `Series`:

- x semantic `k`, explicit inverse-angstrom unit;
- y semantic `chi`, dimensionless;
- real finite values;
- non-negative, uniform, strictly monotonic k;
- the uniform k grid must include zero and align to the zero-origin Δk grid.

Descending source order is allowed. The original source arrays/direction are retained, while the numerical WT grid is explicitly constructed in ascending k order.

No interpolation, resampling, background subtraction, FT-window reuse, or energy→k conversion is performed.

## EXAFSWTSpec

The complete transform recipe is retained in `EXAFSWTSpec`:

- `order`: positive integer Cauchy order;
- `rmin_angstrom`;
- `rmax_angstrom`;
- `rstep_angstrom`;
- `kweight`;
- `nfft`;
- `family="cauchy"`;
- `frequency_mapping="omega_peak=2R"`;
- `normalization="2pi_over_factorial"`.

The R range must be an integer multiple of the requested R step so the exact retained grid is unambiguous.

No chemistry-dependent wavelet parameter is guessed.

## Explicit Cauchy convention

EXAFS oscillations are represented in the usual form

```text
chi(k) ~ cos(2 R k)
```

so a contribution at distance-like Fourier coordinate `R` has angular frequency

```text
omega_peak = 2 R
```

For Cauchy order `m >= 1` and `R > 0`, CatalysisWorkbench defines the scale

```text
a = m / (2 R)
```

and the positive-frequency analytic kernel

```text
H_R(omega) = (2*pi / m!) * (a*omega)^m * exp(-a*omega),  omega > 0
H_R(omega) = 0,                                           omega <= 0
```

The peak occurs at `a*omega = m`, therefore `omega_peak = 2R` by construction.

The kernel is evaluated in logarithmic form using `lgamma(m+1)` for numerical stability. The input signal is explicitly `k^kweight * chi(k)` before frequency-domain filtering.

For `R = 0`, the retained transform row is defined as exactly zero rather than evaluating the singular scale mapping.

## FFT implementation

The numerical implementation zero-pads the explicitly weighted signal to `nfft`, applies the analytic positive-frequency Cauchy kernel, and inverse-transforms each retained R row.

FFT use is an implementation of the declared convolution/filter convention; it is not a hidden scientific normalization. `nfft` must be at least the source k-grid length.

Unlike the FT-EXAFS block, this WT block does not reuse a Hanning window. The Cauchy kernel itself provides k/R localization.

## EXAFSWTResult

The immutable result retains:

- source stable key;
- deterministic digest of exact source k/chi arrays;
- exact source arrays in original order;
- original source direction;
- Δk;
- ascending zero-origin k grid;
- exact R grid;
- complex WT matrix with shape `(n_R, n_k)`;
- magnitude;
- real part;
- imaginary part;
- principal phase.

Public reconstruction recomputes the declared numerical convention and fails closed if source identity, grid state, complex transform, or any derived component contradicts the retained state.

The complex matrix is authoritative. Magnitude/real/imaginary/phase are retained convenience views and are cross-checked against it.

## Hand-verifiable ridge test

A synthetic single-frequency EXAFS signal

```text
chi(k) = cos(2 R0 k)
```

has its WT magnitude ridge at `R0` away from finite-grid edges. The regression suite uses this property as an independent physical-frequency check of the `omega_peak = 2R` mapping.

## Interpretation guardrail

WT intensity is convention-dependent: Cauchy order, k weighting, R grid and FFT padding all belong to the transform recipe. Quantitative comparison of WT magnitudes should therefore use identical transform specifications.

The WT map localizes oscillatory contributions in k and R-like Fourier space. It does not by itself assign a scattering shell, chemical identity, or exact crystallographic bond length.

## Plotting

`plot_wt_exafs()` is a passive lazy renderer of the retained two-dimensional matrix.

Supported views:

- magnitude;
- real;
- imaginary;
- phase.

The renderer does not recompute the transform, alter k weighting/order/R mapping, interpolate data, infer shells, or phase-correct distances. `cmap`, `vmin`, `vmax`, and optional colorbar display are presentation-only choices.

Numerical `experimental.characterization` imports remain Matplotlib-lazy.

## Example

```python
from catalysis_workbench.experimental.characterization import (
    EXAFSWTSpec,
    cauchy_wt_exafs,
    plot_wt_exafs,
)

wt = cauchy_wt_exafs(
    chi_k,
    EXAFSWTSpec(
        order=20,
        rmin_angstrom=0.0,
        rmax_angstrom=6.0,
        rstep_angstrom=0.05,
        kweight=2.0,
        nfft=2048,
    ),
)
figure, ax = plot_wt_exafs(wt, component="magnitude")
```

The numerical choices above are illustrative explicit caller choices, not element-specific defaults.
