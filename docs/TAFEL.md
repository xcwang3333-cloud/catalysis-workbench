# Tafel analysis contract

Issue #21 implements explicit, traceable Tafel fitting on top of the v0.2 electrochemistry foundation and the shared publication renderer.

## Prior art

The implementation was designed after surveying several open-source projects and mature numerical dependencies:

- `ixdat/ixdat` (MIT) is the electrochemistry architecture reference for keeping potential/current quantities attached to explicit calibration and reference metadata.
- `NordicEC/EC4py` (MIT) is practical electrochemistry post-processing prior art that includes Tafel-slope extraction. CatalysisWorkbench does not copy its implementation and keeps its own immutable `Series`/provenance API.
- PyPI `tafel` by Koki Muraoka (MIT, experimental) is a focused Tafel extraction tool for xy/CSV/BioLogic inputs. It is workflow prior art only; CatalysisWorkbench does not inherit its file/CLI assumptions.
- `scipy.stats.linregress` from SciPy (BSD-3-Clause) is the regression kernel. CatalysisWorkbench adds the electrochemical semantics, selection policy, unit conversion, provenance, result model, and publication adapter around that mature implementation.

No new runtime dependency is required because SciPy is already part of CatalysisWorkbench.

## Scientific definition

The v0.2 Tafel model is

```text
E = intercept + slope * log10(|j| / (1 A cm^-2))
```

where `E` is converted to volts and `j` is converted to A cm^-2 before taking the logarithm. The fitted coefficient is retained with its mathematical sign. `TafelFitResult.slope_mv_dec` is therefore signed; `slope_magnitude_mv_dec` is provided only as an explicit convenience for conventional positive-magnitude reporting.

The implementation does not convert potential to overpotential because an equilibrium potential is not an Issue #21 input. The slope is unaffected by a constant potential offset, while the intercept remains reference-dependent and is therefore stored together with the explicit potential reference.

## Input contract

`fit_tafel(...)` accepts one core `Series` and requires:

- `x_axis.name == "potential"`;
- `y_axis.name == "current_density"`;
- an explicit supported potential unit (`V` or `mV` through the shared quantity layer);
- an explicit supported current-density unit;
- `x_axis.metadata["reference"]`, for example `"RHE"`;
- `y_axis.metadata["normalization"]`, for example `"geometric_area"`;
- an explicit two-bound potential `fit_window` and explicit `fit_window_unit`;
- explicit physical `branch` (`"cathodic"` or `"anodic"`);
- explicit numeric `current_sign` (`"negative"` or `"positive"`).

Branch and numeric sign are deliberately separate. This allows a cathodic experiment exported with a positive-current instrument convention to be represented without silently changing the scientific data.

Fit-window bounds are inclusive after conversion to volts. Potential NaN values outside the selected region are ignored by selection. A current-density NaN inside the selected region fails explicitly; selected zero current also fails because its logarithm is undefined.

At least three selected points and at least two distinct log-current values are required. The v0.2 implementation does not silently drop selected points to make a fit succeed.

## Result contract

`TafelFitResult` is immutable and stores:

- signed `slope_v_dec`;
- signed `slope_mv_dec` property;
- positive `slope_magnitude_mv_dec` property;
- `intercept_v`;
- `r_squared`;
- explicit branch and numeric current sign;
- explicit current-density normalization basis and potential reference;
- immutable float64 selected log-current values;
- immutable float64 selected potentials in V;
- immutable float64 fitted potentials in V;
- shared `AnalysisProvenance`, including `SourceDataRef` and canonical `FitWindow`.

The source digest hashes the original numerical `Series` arrays. The canonical fit window is stored in volts, while the caller's input fit-window unit is retained in provenance. Provenance also records the current-density basis, branch, sign convention, reference, and canonical calculation units.

## Dataset fitting

`fit_tafel_dataset(...)` preserves Dataset order and requires every input `Series` to have a non-empty stable key. Fit windows are always supplied as a complete stable-key mapping. `fit_window_unit`, `branch`, and `current_sign` may be one common string or complete stable-key mappings.

Missing keys, unknown keys, duplicate normalized mapping keys, empty source keys, and non-string mapped branch/sign/unit values fail explicitly. No display label is used as an analysis address.

## Publication adapter

`plot_tafel(...)` is imported lazily so importing numerical `experimental.echem` does not import Matplotlib. It performs no refitting or scientific transformation.

Each result is converted into two temporary core `Series` objects:

- selected raw points: marker-only;
- fitted values: line-only.

Both use the same color by default and are rendered by the shared `render_curves` / `FigureSpec` stack. Multi-result plots therefore inherit existing compatibility checks for the current-density normalization basis and potential reference. The default y label retains the explicit reference, for example `Potential (V vs RHE)`.

## Scope boundary

Issue #21 does not implement automatic Tafel-region detection, outlier rejection, robust regression, kinetic-current correction, Butler-Volmer nonlinear fitting, exchange-current interpretation, bootstrap/statistical uncertainty, transfer-coefficient inference, rate-determining-step inference, or mechanistic classification from a slope value. Those operations require additional scientific assumptions and must remain separate, explicit later work if added.
