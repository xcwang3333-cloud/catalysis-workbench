# TGA / DTG / TPR / TPD thermal-analysis contract

Issue #54 adds a conservative one-dimensional thermal-analysis foundation to CatalysisWorkbench. The module is intended for explicit post-processing and publication rendering of TGA, derived DTG, temperature-programmed reduction (TPR), and temperature-programmed desorption (TPD) curves. It does not attempt kinetic modelling, deconvolution, automatic peak assignment, or vendor-specific instrument parsing.

## Design principles

Thermal data use the existing immutable `Series` / `Dataset` model. Numerical analysis and publication plotting remain separate. Scientific state that changes interpretation is represented explicitly rather than inferred from labels or conventional plotting habits.

The initial contract therefore requires:

- explicit temperature semantic and unit;
- explicit TGA mass basis or TPR/TPD detector-signal semantic;
- explicit TGA normalization reference;
- explicit DTG sign convention;
- explicit temperature window, extremum mode, and area mode for direct-window measurements;
- stable `Series.key` values for per-sample Dataset mappings;
- deterministic source-data digests and processing-history records;
- no silent smoothing, baseline correction, resampling, clipping, sign inversion, normalization, or cross-spectrum alignment.

## Temperature axis

The x axis must identify temperature (`temperature` or `temp`). The first implementation accepts degree Celsius aliases and kelvin aliases and canonicalizes them to `°C` or `K`.

Both strictly ascending and strictly descending source grids are valid. Duplicate or non-monotonic temperatures fail. Processing preserves the source order; no operation silently reverses an input curve.

Temperature conversion is explicit:

```python
converted = convert_temperature(series, target_unit="K")
```

The numerical relationship is

\[
T_{\mathrm{K}} = T_{\mathrm{^\circ C}} + 273.15.
\]

A Celsius-to-kelvin conversion that would produce a temperature below 0 K fails rather than clipping the result.

For DTG data the denominator unit is coupled to the converted temperature axis. Converting a valid `mg/°C` DTG curve to kelvin therefore produces `mg/K`. The numerical DTG values do not require rescaling because one-kelvin and one-degree-Celsius temperature increments have identical magnitude.

The module does not reconstruct temperature from time and a nominal heating rate. If a source file contains time rather than measured temperature, that conversion requires a separate explicit scientific contract.

## TGA semantics

A TGA `Series` must declare one of these y semantics:

- `mass` (the `weight` alias is accepted), with an explicit `g`, `mg`, or `µg` unit;
- `mass_fraction`, with explicit dimensionless unit `1`/`fraction`;
- `mass_percent`, with explicit `%`/percent unit.

Raw mass is never silently normalized to 100%.

### Explicit mass normalization

`normalize_tga_mass()` converts raw mass to fraction or percent using a caller-visible reference:

```python
normalized = normalize_tga_mass(
    raw_tga,
    output="percent",
    reference="first_point",
)
```

For raw mass \(m_i\) and reference mass \(m_{\mathrm{ref}}\), the normalized fraction is

\[
f_i = \frac{m_i}{m_{\mathrm{ref}}},
\]

and percent output is

\[
w_i = 100 f_i.
\]

`reference="first_point"` means the first measured point in the stored source order. A positive explicit numeric reference may be supplied instead and is interpreted in the same mass unit as the source curve. The reference basis, numerical value, unit, and source digest are recorded in provenance.

The sample-specific numerical reference value is provenance, not an overlay-compatibility discriminator. Two samples normalized independently by their own first measured point therefore share the same normalization basis even when their starting masses differ. By contrast, `reference="first_point"` and an explicitly supplied reference mass are distinct normalization bases and are not treated as interchangeable.

Already normalized TGA data are rejected by `normalize_tga_mass()` to prevent accidental double normalization.

## DTG derivation

DTG is an explicit derived curve, not an automatic plotting transformation:

```python
dtg = derive_dtg(tga, sign_mode="mass_loss_positive")
```

The reviewed numerical backend is NumPy `gradient` on the measured temperature grid:

\[
\mathrm{DTG}_{\mathrm{signed}} = \frac{dy}{dT}.
\]

The initial implementation uses `numpy.gradient(y, x, edge_order=1)`. Nonuniform strictly monotonic temperature grids are supported directly; the curve is not interpolated onto a new grid first.

Two sign conventions are supported and must be selected explicitly:

- `sign_mode="signed"`: retain \(dy/dT\);
- `sign_mode="mass_loss_positive"`: report \(-dy/dT\), making a decreasing TGA mass curve positive.

No absolute value, clipping, smoothing, baseline correction, or sign guessing is hidden inside the derivative. At least three finite source points are required. Missing y values cause a failure rather than being discarded.

For example, a raw mass curve that decreases linearly from 10 to 7 mg between 100 and 400 °C in 100 °C increments has

\[
\frac{dm}{dT}=-0.01\ \mathrm{mg\,^\circ C^{-1}},
\]

or `+0.01 mg/°C` in `mass_loss_positive` mode.

The same physical curve stored in descending temperature order yields the same derivative at matching temperatures. Source direction is retained in provenance.

DTG derived from normalized TGA retains the source mass semantic and normalization provenance. For example, a percent-normalized source produces `%/°C`; it is not reinterpreted as raw mass during validation or plotting.

## TPR / TPD signal semantics

TPR and TPD initially represent measured temperature versus detector response. The caller explicitly declares the technique when validating, processing, measuring, or plotting a curve:

```python
validate_temperature_programmed_series(series, technique="tpr")
```

The y axis must identify `detector_signal`, `signal`, `response`, or a normalized-signal equivalent and must carry an explicit unit string. Arbitrary units and dimensionless detector responses are acceptable when explicitly declared.

The module does **not** infer any of the following from a label or signal shape:

- hydrogen consumption;
- ammonia, carbon dioxide, or other desorbed amount;
- acid-site density;
- reducible-metal inventory;
- calibrated molar quantity.

Conversion from detector response to amount requires explicit calibration data and is deferred to a later contract.

## Explicit thermal-window measurement

`ThermalWindow` and `measure_thermal_window()` provide direct, traceable measurements without automatic peak detection:

```python
result = measure_thermal_window(
    tpr,
    ThermalWindow(150.0, 450.0, "main feature"),
    technique="tpr",
    extremum_mode="maximum",
    area_mode="net",
)
```

The window must be fully contained in the measured temperature range and must contain at least one actual measured temperature point. Boundary interpolation alone is not accepted as sufficient support for a quantitative window.

The result reports:

- explicit technique and window;
- maximum or minimum temperature/value selected by `extremum_mode`;
- net or absolute trapezoidal area selected by `area_mode`;
- measured and integration point counts;
- source storage direction;
- source and window SHA-256 digests;
- temperature, signal, and explicit area-unit strings;
- boundary handling mode.

Only the two requested window boundaries may be linearly interpolated. Interior source points are not resampled. If an interpolated boundary would require a missing bracketing y value, the operation fails.

For net area,

\[
A_{\mathrm{net}} = \int_{T_1}^{T_2} y(T)\,dT,
\]

while absolute area is

\[
A_{\mathrm{abs}} = \int_{T_1}^{T_2} |y(T)|\,dT.
\]

Integration is always evaluated from lower to higher temperature, independent of source storage direction. `area_unit` records the explicit product of the reported `signal_unit` and `temperature_unit` (for example `a.u.·°C`). For a DTG curve the string may be `%/°C·°C`, which is dimensionally equivalent to `%`; the initial string-based unit model does not perform general symbolic unit cancellation.

The initial window helper does not assign chemical species, infer an onset temperature, decide how many peaks exist, or fit Gaussian/Lorentzian/Voigt components.

## Processing recipes and Dataset behavior

`ThermalProcessingConfig` supports only caller-requested operations:

- temperature crop;
- TGA raw-mass normalization to fraction or percent;
- vertical offset.

The default configuration performs none of these transformations beyond validation/canonical metadata. TGA normalization is applied before a requested crop, so `reference="first_point"` always refers to the first point of the original input Series rather than the first point left after cropping.

Dataset-specific overrides are addressed by stable `Series.key` values. Unknown keys fail. No Dataset workflow performs hidden interpolation or alignment between samples.

Vertical offset is explicit and is recorded in `processing_history`. For publication-only stacked displays, `stack_thermal_dataset()` / `plot_thermal(..., stack_step=...)` are preferred so the display offset remains clearly separated from quantitative operations.

## Overlay compatibility

Thermal overlays are allowed only when scientific interpretation is compatible. The guard compares:

- technique (`tga`, `dtg`, `tpr`, or `tpd`);
- canonical temperature unit;
- y semantic and unit;
- normalization signature;
- DTG sign convention and source mass semantic where applicable.

For example, raw `mg` and raw `g` TGA traces are not silently converted for overlay, and signed DTG cannot be overlaid with mass-loss-positive DTG as if they shared the same convention. Convert or transform data explicitly first.

## Publication plotting

`plot_thermal()` is a thin, lazy adapter over the shared curve renderer:

```python
fig, ax = plot_thermal(
    dtg,
    spec,
    technique="dtg",
    annotations=(ThermalAnnotation(350.0, "DTG max"),),
)
```

Plotting performs no derivative, normalization, smoothing, baseline correction, temperature conversion, or window analysis. It validates compatibility, optionally applies an explicit stack offset, and delegates figure geometry, typography, stable-key styling, limits, labels, and PNG/SVG/PDF export to `FigureSpec` and the shared visualization layer.

`FigureSpec.xlabel=""` remains an explicit request to suppress the x label; `None` means automatic labeling. Explicit x/y limits are preserved when thermal annotations are added.

Importing the numerical characterization API does not import Matplotlib. Matplotlib is loaded only when the lazy `plot_thermal()` wrapper is called.

## Prior art and license decisions

The implementation was scoped after reviewing several open-source projects:

- `MyonicS/pyTGA` — MIT. Useful reference for explicit temperature/weight/time data, experiment stages, multi-vendor parser tests, quick plotting, and example datasets. CatalysisWorkbench does not copy its code and does not add vendor parsers in Issue #54.
- `mayankskii/TGAnalysis` — MIT, MATLAB. Useful scope reference demonstrating the distinction between basic TGA/DTG handling and later kinetics/deconvolution. No MATLAB code is reused.
- `lukasbaldauf/tga-kinetics` — MIT. Useful equation/workflow reference for explicit `-dm/dt` convention, finite-difference rates, simulated datasets, and model sensitivity. Kinetic fitting is deliberately excluded here.
- `Danilosauro/thermogravimetric-analysis` — no repository license detected during review. Reference-only; no implementation reuse.
- NumPy — BSD-3-Clause and already a CatalysisWorkbench dependency. `numpy.gradient` supplies the derivative kernel; CatalysisWorkbench adds thermal semantics, validation, units, sign policy, provenance, and regression tests around it.

No upstream implementation code is copied.

## Explicitly deferred

Issue #54 does not implement:

- vendor-specific TGA readers;
- DSC or DTA;
- Arrhenius, Coats–Redfern, Friedman, Flynn–Wall–Ozawa, KAS, or other kinetic fitting;
- automatic peak detection, onset extrapolation, deconvolution, or shared peak fitting;
- automatic smoothing/baseline/drift/buoyancy correction;
- TPR/TPD detector calibration to chemical amount;
- GUI behavior;
- a v0.3 version bump, release, tag, or package-registry publication.
