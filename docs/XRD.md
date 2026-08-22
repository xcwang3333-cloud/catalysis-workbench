# XRD processing and plotting design

## Prior-art survey

CatalysisWorkbench keeps the v0.1 XRD workflow narrow and post-processing oriented.

- `ixdat/ixdat` (MIT) is the reader-architecture reference. Its dedicated XRD XY reader keeps conservative file parsing separate from scientific objects. CatalysisWorkbench follows the same separation: tabular/text readers parse input, while `experimental.characterization` owns diffraction semantics.
- `materialsproject/pymatgen` (MIT) provides a mature `XRDCalculator` for structure-derived reference diffraction. Its calculated pattern exposes 2θ positions and intensities and can scale the strongest peak to 100. CatalysisWorkbench v0.1 therefore models reference sticks as explicit positions plus optional relative intensities, but does not add pymatgen as a dependency. A later optional CIF/Structure adapter can convert pymatgen output into `XRDReferencePattern`.
- `dkriegner/xrayutilities` provides broad powder-diffraction simulation/refinement functionality under GPL-2.0. It is prior-art only for this module: CatalysisWorkbench does not copy its implementation or add a GPL dependency for a lightweight publication post-processing workflow.
- `derb12/pybaselines` remains the preferred mature baseline-estimation backend. XRD v0.1 only subtracts an explicitly supplied baseline through the shared processing primitive; it does not clone baseline-estimation algorithms.

## v0.1 scientific contract

An experimental powder pattern is a normal core `Series`: x is 2θ in explicit degree units and y is intensity. Common semantic 2θ names are accepted, but radians are not silently converted. X must be real, finite, and strictly increasing. XRD intensity is real-valued; NaN can remain as a plotting gap, while numerical transforms keep the shared explicit missing-data policy.

Raw intensity accepts common count, count-rate, arbitrary-unit, or dimensionless semantics. `normalized_intensity` must use arbitrary or dimensionless units; unrelated physical units such as electrical current are rejected before analysis or rendering. Equivalent spellings such as `count`/`counts`, `deg`/`degree`/`°`, and `two_theta`/`2θ` are canonicalized only on temporary render copies. The source `Series` remains unchanged, while the generic shared renderer can still enforce exact signatures for genuinely incompatible axes such as counts versus cps.

`XRDProcessingConfig` defines deterministic baseline -> crop -> normalize -> vertical-offset processing. Numerical kernels are delegated to shared `subtract_baseline`, `crop`, `normalize`, and `offset`. Normalized output is relabeled as `Normalized intensity` with `a.u.` units and explicit normalization metadata. XRD normalization targets must be positive. The compatibility-critical `normalization` metadata encodes method, target, and area mode when relevant, so max-normalized, area-normalized, target=1, and target=100 patterns cannot silently overlay as equivalent quantitative bases.

An explicit baseline `Series` may use equivalent 2θ/intensity spelling aliases. The XRD layer validates semantic equivalence and adapts only the temporary baseline axes to the source before calling the generic exact-axis `subtract_baseline` primitive; genuinely different intensity bases or x grids remain errors.

`process_xrd_dataset` preserves Dataset order, keys, labels, and metadata and supports stable-key-specific processing overrides/baselines. `stack_xrd_dataset` applies deterministic offsets using the shared `offset()` primitive and records collection-level stack history.

## Publication rendering

`plot_xrd()` delegates ordinary curves, axes layout, typography, legends, per-Series styles, and export behavior to the shared `FigureSpec` / `render_curves` engine. The XRD adapter adds only domain semantics:

- publication-oriented 2θ axis labeling;
- render-only canonicalization of equivalent XRD axis/unit spellings;
- optional non-mutating stacked display via `stack_xrd_dataset`;
- stable-key-addressed peak annotations anchored to interpolated experimental intensity;
- optional reference sticks drawn in normalized axes-height bands so they do not change the experimental y limits.

Reference intensities are normalized only for stick height inside their own reference pattern. Reference positions outside the visible x range do not expand the experimental axis. Numerical characterization imports remain independent of Matplotlib because the plotting adapter is loaded lazily.
