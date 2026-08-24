# FTIR / ATR-FTIR processing

Issue #50 introduces the first v0.3 scientific module. The module is intentionally limited to explicit one-dimensional FTIR/ATR-FTIR processing and publication rendering; it does not introduce automatic preprocessing pipelines, peak deconvolution, vendor-binary readers, hyperspectral maps, or a GUI.

## Scientific data contract

An FTIR spectrum is a core `Series` with:

- x-axis semantic `wavenumber` (or `wn`) and an explicit inverse-centimetre unit such as `cm^-1`, `cm-1`, `1/cm`, or `cm⁻¹`;
- strictly monotonic wavenumber values without duplicates; increasing and decreasing storage order are both accepted and preserved;
- y-axis semantic `absorbance`, `transmittance`, or `normalized_absorbance`;
- absorbance represented as dimensionless/arbitrary units and transmittance represented with an explicit fraction or percent scale.

The module does not infer absorbance/transmittance semantics from numerical ranges or display labels.

## Explicit transmittance conversion

`transmittance_to_absorbance(series, input_scale=...)` implements

`A = -log10(T)`

where `T` is the fractional transmittance. `input_scale='percent'` divides the supplied values by 100 before applying the logarithm; `input_scale='fraction'` uses them directly. The declared input scale must agree with the y-axis unit.

After conversion, every value must satisfy `0 < T <= 1`. Zero, negative, or greater-than-unity fractional values are rejected rather than clipped. Missing values are not silently discarded. The output records the input scale, formula, deterministic source-data digest, and processing-history entry.

## Baseline fitting and subtraction

Baseline estimation is never hidden inside `process_ftir`.

`fit_ftir_baseline(series, windows, degree=...)` fits a polynomial by least squares using only caller-supplied `FTIRBaselineWindow` intervals. The selected points must cover more points than the polynomial degree and every window must be fully contained in the measured range. The polynomial is evaluated on the exact source grid and returned as a separate `FTIRBaselineFit.baseline` Series.

The fit stores:

- explicit windows;
- polynomial degree;
- scaled polynomial coefficients;
- numerical centering/scaling used for conditioning;
- number of fit points;
- source key/label and SHA-256 identity.

`subtract_ftir_baseline` requires the exact source grid. A stored `FTIRBaselineFit` can only be subtracted from the source numerical data on which it was fitted; a changed source must be refitted.

The first implementation deliberately excludes automatic baseline-window selection, rubber-band baselines, AsLS/airPLS/SNIP, and algorithm ranking. `pybaselines` remains a BSD-3-Clause future adapter candidate once those methods receive a separate scientific contract.

## Explicit processing recipe

`FTIRProcessingConfig` can request:

- wavenumber crop;
- normalization (`max`, `max_abs`, `minmax`, or `area`);
- normalization target and area mode;
- vertical offset.

An explicit baseline is supplied separately to `process_ftir(..., baseline=...)`. With the default configuration and no baseline, processing only validates/canonicalizes semantics; it performs no numerical correction.

Normalization is limited to absorbance-like data. Transmittance must be explicitly converted first. Savitzky-Golay smoothing remains available through the shared processing primitive but is not an FTIR default or hidden step.

Dataset processing accepts stable-key-specific configuration overrides and baselines. Unknown or empty mapping keys fail rather than falling back to display labels.

## Band measurement

`measure_ftir_band(series, FTIRBand(low, high), area_mode=...)` is a direct-window measurement, not a peak fit.

- the requested window must be fully measured;
- the reported peak is the maximum measured absorbance point inside the window;
- integration boundaries are explicitly interpolated onto the requested low/high wavenumbers when those boundaries fall between measured points;
- integration always proceeds from lower to higher wavenumber, so the scalar area is independent of whether the source Series is stored ascending or descending;
- `area_mode='net'` preserves signed corrected absorbance and `area_mode='absolute'` integrates `abs(y)`;
- transmittance is rejected until explicitly converted to absorbance;
- missing values inside the measured/integration window fail explicitly.

The result records source direction, the low-to-high integration convention, source digest, exact integration-window digest, units, point counts, peak position, peak absorbance, and area.

## Visualization

`plot_ftir` is a lazy adapter over the shared `FigureSpec` / `render_curves` stack.

It supports:

- Series and Dataset overlays;
- explicit stacking;
- stable-key styling inherited from the shared renderer;
- `FTIRPeakAnnotation` labels;
- `wavenumber_direction='descending'|'ascending'|'source'`.

`descending` is the default because conventional FTIR figures display high wavenumber on the left. This changes only the axes display limits; stored scientific arrays are never reversed. `source` requires every overlaid spectrum to share the same storage direction.

Overlay validation requires matching y semantic, y unit, and normalization recipe. Absorbance and transmittance are not silently mixed, and spectra with different normalization targets are rejected before rendering.

Publication export remains the shared PNG/SVG/PDF path.

## Prior-art and license decisions

The Issue #50 survey considered:

- `spectrochempy/spectrochempy` — CeCILL-B: unit/coordinate-aware spectroscopy objects, explicit baseline processors, processing/plotting separation, and provenance ideas; architecture/API reference only, no copied implementation.
- `derb12/pybaselines` — BSD-3-Clause: mature unified baseline API and baseline/corrected-signal separation; permissive future dependency/adapter candidate, but no automatic algorithm selection in Issue #50.
- `uw-ssec/ProSpecPy` — BSD-3-Clause: modular FTIR and batch-workflow organization; workflow reference only.
- `charlesll/rampy` — GPL-2.0: baseline-region, stacking/resampling/smoothing workflow ideas; reference only, no code reuse.
- `JRay-Lin/SpectraLab` — MIT: explicit raw/baseline/corrected states and baseline-parameter persistence; UI/data-state reference only.

No upstream implementation code is copied into this module.

## Out of scope for Issue #50

- automatic baseline method selection;
- peak deconvolution / nonlinear fitting / automatic band assignment;
- automatic atmospheric H2O or CO2 correction;
- 2-D FTIR maps and hyperspectral cubes;
- vendor-binary file readers beyond the existing tabular-import path;
- GUI or interactive editor implementation;
- v0.3 release/version/tag operations.
