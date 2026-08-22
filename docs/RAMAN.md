# Raman processing and plotting design

## Prior-art survey

CatalysisWorkbench keeps the v0.1 Raman workflow explicit, traceable, and post-processing oriented.

- `barahona-research-group/RamanSPy` uses a composable preprocessing-pipeline architecture and is distributed under BSD-3-Clause. Its published protocols make operations such as crop, denoise, baseline correction, and normalization explicit rather than hiding them in one opaque command. CatalysisWorkbench follows that explicit-pipeline principle while reusing the project's own shared XY primitives.
- `derb12/pybaselines` is the preferred mature baseline-estimation backend for future integration. v0.1 does not reimplement AsLS/asPLS/SNIP/polynomial baseline estimators; it subtracts an explicitly supplied baseline through the shared processing layer.
- `charlesll/rampy` demonstrates broad Raman/spectral-processing functionality but is GPL-2.0. It is prior-art only here: CatalysisWorkbench does not copy its implementation or add a GPL dependency.

## v0.1 scientific contract

A Raman spectrum is a normal core `Series`: x is Raman shift in explicit inverse-centimetre units and y is Raman intensity. Conservative Raman-shift aliases are accepted, but an absolute `wavenumber` axis is not silently interpreted as Raman shift. Equivalent unit spellings such as `cm^-1`, `cm-1`, `1/cm`, and `cm⁻¹` are treated as the same Raman-shift basis.

Raw intensity supports count, count-rate, arbitrary-unit, and dimensionless bases. `normalized_intensity` is limited to arbitrary/dimensionless units. X must be real, finite, and strictly increasing. Y is real-valued; NaN may remain as a plotting gap, while numerical operations preserve the shared explicit missing-data policy.

`Series.key` / `Series.label` identify spectra or samples. v0.1 does not assign a special physical `reference` role to a Raman Series; a reference spectrum is therefore just another explicitly identified Series unless a later domain-specific workflow defines additional semantics.

`RamanProcessingConfig` composes explicit baseline subtraction -> crop -> Savitzky-Golay smoothing -> normalization -> vertical offset. Numerical work is delegated to shared `subtract_baseline`, `crop`, `savgol`, `normalize`, and `offset`. Savitzky-Golay retains the shared approximately-uniform-spacing requirement. Because v0.1 subtracts an already supplied baseline rather than estimating one, baseline subtraction before crop does not hide a baseline-fitting range choice; future baseline-estimation adapters must make their fitting range explicit.

Normalized Raman output uses `Normalized intensity` / `a.u.` semantics and compatibility-critical metadata that includes method, target, and area mode where applicable. This prevents quantitatively different normalization recipes from silently sharing one publication axis.

## Quantitative band helpers

`RamanBand` defines an explicit shift window. CatalysisWorkbench intentionally does not hard-code D/G band windows because their useful ranges depend on material, excitation wavelength, disorder, preprocessing, and analysis convention.

`measure_raman_band()` is a direct window measurement, not a peak fit or automatic peak detector. The peak position/intensity is the maximum **observed** sample inside the requested window. The band area is integrated over the **exact requested boundaries**: if a boundary falls between measured Raman-shift points, the boundary intensity is linearly interpolated before the shared trapezoidal integration primitive is called. A band must be fully contained within the measured Raman-shift range; partially unmeasured windows are not silently truncated. Boundary interpolation is local and fails if either bracketing intensity is missing, so a NaN gap is never silently bridged.

`RamanBandMeasurement` distinguishes full-source and exact-window data provenance. It records the full input-series SHA-256 digest, the exact integration-window digest, original Raman-shift/intensity units, the number of observed points used for the peak measurement, and the number of points in the integration grid after boundary interpolation.

`raman_ratio()` makes the ratio metric explicit (`height` or `area`), and `id_ig_ratio()` is only a convenience wrapper around caller-supplied D and G bands. Quantitative helpers reject spectra after a vertical display offset. They reject min-max-normalized spectra because the additive shift changes peak-height and area ratios. If the input semantic is `normalized_intensity`, ratio calculation additionally requires known multiplicative normalization provenance supported by v0.1 (`max`, `max_abs`, or `area`); missing or unknown normalized-spectrum provenance is rejected. Missing values inside the selected quantitative/integration window are not silently dropped.

## Publication rendering

`plot_raman()` delegates ordinary curves, layout, typography, legends, per-Series styles, and export to the shared `FigureSpec` / `render_curves` engine. The adapter adds only Raman semantics:

- publication-oriented `Raman shift (cm⁻¹)` labeling;
- semantic automatic y labels, including `Normalized intensity ...` for `normalized_intensity` data;
- non-mutating stacked display via `stack_raman_dataset()`;
- stable-key-addressed peak annotations anchored to interpolated spectrum intensity;
- render-only canonicalization of equivalent Raman-shift/intensity aliases.

Explicit `FigureSpec.xlabel` / `ylabel` overrides, including blank strings, remain authoritative. Source `Series` objects are never rewritten merely to satisfy the generic renderer. Genuine incompatibilities such as counts versus cps, raw versus normalized intensity, or different normalization recipes remain explicit errors. Numerical characterization imports remain independent of Matplotlib because `plot_raman()` is loaded lazily.
