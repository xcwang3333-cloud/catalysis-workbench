# Electrochemical stability analysis

Issue #27 implements quantitative stability analysis for already prepared electrochemical time series. The design deliberately separates **time-axis construction/preprocessing** from **stability metrics**: CatalysisWorkbench analyzes the time axis it is given and never silently stitches files, removes pauses, smooths traces, or decides which period should count as the baseline.

## Scientific prior art

The implementation was designed after reviewing open-source electrochemistry/time-series projects and their handling of elapsed time, absolute time, segmented durability experiments, and technique semantics.

### Open-source references

- `Catalysis-for-Energy-Conversion/EC-Lab-Automated-Analysis-Project` — MIT. Its CP durability workflow explicitly distinguishes real wall-clock `cumulative` time from `running_only` electrolysis time and reconstructs long experiments split across multiple programs. This is useful evidence that elapsed-time meaning must be explicit. CatalysisWorkbench does **not** copy its file-stitching code and does not infer either time mode during stability analysis; any stitching belongs to an explicit upstream processing step.
- `bcliang/gamry-parser` — MIT. Its chronoamperometry parser can expose either seconds since experiment start or timestamp-like values. CatalysisWorkbench takes the same high-level lesson that elapsed and absolute time are distinct data semantics, but Issue #27 accepts only a numerical elapsed-time axis with an explicit supported unit.
- `ljelissiry/eCAT` — MIT. It keeps CA/CP as identifiable electrochemical technique types instead of treating every time-series file as interchangeable. CatalysisWorkbench likewise validates the y-axis scientific semantic (`current`, `current_density`, `potential`, `faradaic_efficiency`, or `activity`) and retains reference/normalization metadata where they are physically relevant.
- `ixdat/ixdat` — MIT. Its electrochemical data architecture remains useful prior art for keeping numerical values attached to explicit units/calibration context. Issue #27 reuses CatalysisWorkbench's existing `Series`, quantity conversion, and deterministic provenance foundations rather than adding a second time-series data model.

No upstream implementation code is copied.

## Scope

Issue #27 covers quantitative analysis of already prepared:

- current vs time;
- current density vs time;
- potential vs time;
- Faradaic efficiency vs time;
- activity vs time.

It does not parse potentiostat files, stitch restarts, reconstruct absolute timestamps, perform iR correction, smooth data, reject outliers, infer steady state, decide when degradation starts, or automatically choose the baseline/final intervals.

## Time-axis contract

The x axis must:

- have semantic name `time`;
- have an explicit unit supported by the shared Issue #19 time conversion layer;
- contain finite real numeric values;
- be strictly increasing after conversion to seconds.

Duplicate or decreasing time values fail explicitly. A trace assembled from restarted experiments must therefore be stitched upstream into one physically declared elapsed-time axis before stability metrics are requested.

The library does not know whether that elapsed time represents wall-clock duration, operating-only duration, or another experiment-specific definition. Callers should preserve that meaning in source metadata.

## Y-axis contract

Supported y semantics are:

- `current`;
- `current_density`;
- `potential`;
- `faradaic_efficiency`;
- `activity`.

The y unit must be explicit. Additional required metadata are:

- `potential`: explicit non-empty `reference` metadata;
- `current_density`: explicit non-empty `normalization` metadata;
- `activity`: explicit non-empty `normalization` metadata.

These fields remain compatibility-critical for multi-catalyst comparison. The module does not reinterpret or convert the source y values; summary metrics stay in the source y unit, while drift is reported per canonical second.

## Explicit windows

Every analysis uses three caller-declared windows:

1. `analysis_window`: interval used for initial/final point reporting and linear drift fitting;
2. `baseline_window`: interval averaged to define the retention denominator/reference;
3. `final_window`: interval averaged to define the retention numerator/final reference.

Each window has explicit lower/upper bounds and an explicit time unit. Bounds are converted to seconds only for numerical selection.

Rules:

- windows are inclusive of measured points on their boundaries;
- no boundary interpolation is performed;
- all three windows must lie inside the measured time range;
- baseline and final windows must lie inside the analysis window;
- baseline must not occur after or overlap the final window (`baseline.upper <= final.lower`);
- the analysis interval must contain at least two usable points;
- baseline/final windows must each contain at least one usable point.

A zero-width baseline/final window is allowed only when it selects an actual measured point. This preserves the ability to request an explicit single-point reference while making averaged noisy baselines the normal, visible alternative.

## Missing-value policy

Time values must always be finite. Source y data may contain NaN because the core model preserves explicit missing data.

`missing_policy` is explicit:

- `reject` (default): any NaN inside the analysis interval fails the calculation;
- `omit`: NaN y values inside the analysis interval are omitted from all metrics, and the omitted count is recorded.

No infinity, strings, booleans, or complex y values are accepted. No missing data are silently dropped.

## Initial/final and window averages

The result distinguishes:

- `initial_value`: first usable measured y value inside the analysis interval;
- `final_value`: last usable measured y value inside the analysis interval;
- `baseline_mean`: arithmetic mean of usable measured points in the baseline window;
- `final_mean`: arithmetic mean of usable measured points in the final window.

Retention and change metrics are based on the explicit window means rather than an implicit noisy first/last point.

## Change and retention

Signed physical values are never changed implicitly.

The signed absolute change is always:

```text
absolute_change = final_mean - baseline_mean
```

Retention has an explicit mode.

### `signed`

```text
retention_fraction = final_mean / baseline_mean
relative_change_fraction = retention_fraction - 1
```

### `magnitude`

```text
retention_fraction = abs(final_mean) / abs(baseline_mean)
relative_change_fraction = retention_fraction - 1
```

Percent forms multiply the corresponding fraction by 100.

A zero baseline denominator fails explicitly. `magnitude` is never applied unless requested.

For potentials, a percentage retention relative to an electrode-reference zero may not be a physically meaningful performance descriptor. The library therefore reports the calculation exactly as requested without interpreting it; potential drift/change is generally the more informative metric.

## Linear drift

Linear drift is fit over all usable points in the declared analysis window:

```text
y(t) = drift_slope * t_seconds + drift_intercept
```

The result records slope, intercept, R-squared, point count, and the analysis window. No smoothing, outlier rejection, resampling, or weighting is applied.

For a mathematically constant trace, slope is zero and the perfect constant fit is recorded with `R² = 1` rather than failing on the zero-variance special case.

The drift-slope unit is the source y unit per second.

## Dataset contract

`analyze_stability_dataset(...)` accepts an exact mapping from stable `Series.key` to `StabilityAnalysisConfig`.

- every Dataset Series must have a non-empty stable key;
- mapping keys must match Dataset keys exactly;
- display labels are never lookup keys;
- output order follows Dataset order;
- results preserve each source digest and compatibility metadata.

Different catalysts may therefore use different explicit baseline/final/analysis windows without any label-based ambiguity.

## Plotting boundary

`plot_stability(...)` renders original time-series data through the shared curve renderer after stability-specific semantic validation. It does not calculate metrics or preprocess the trace.

`plot_stability_summary(...)` renders already calculated scalar metrics as shared categorical bars. Category identity uses stable source keys. Summary plotting never recomputes retention or drift.

Multi-Series long-term overlays require compatible time/y axis names and units plus critical y metadata such as `reference` and `normalization`, inherited from the shared visualization compatibility guard.

## Explicit non-goals

Issue #27 does not automatically:

- concatenate restarted experiments;
- choose wall-clock versus operating-only time;
- smooth or filter data;
- remove spikes/outliers;
- detect steady-state regions;
- choose baseline/final windows;
- infer degradation mechanisms;
- convert a potential drift into an activity-retention claim;
- normalize current/activity to a new denominator.

Those operations, when needed, must be separate explicit transformations with their own provenance.