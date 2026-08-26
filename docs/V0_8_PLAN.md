# CatalysisWorkbench v0.8 Plan

v0.8 is the operando and time-resolved analysis release. This document freezes
the architecture, scientific semantics, dependency boundaries, implementation
order, visualization contracts, testing strategy, and v0.9 handoff before any
v0.8 production implementation begins. GitHub remains the operational source of
truth.

## Starting checkpoint and immutable release boundaries

The architecture baseline is `84dab32835961a8d66669fac12f0fea9806f21b3`, the verified post-v0.7
central-document synchronization merge. CI #547 / run `32919919103` passed on
that exact `main` head.

The release boundary is fixed:

- `v0.7.0 -> e3062fc12c794f54c7b7613875ec73608a587a59` remains immutable;
- distribution and runtime release version remain `0.7.0`;
- the public GitHub Release `CatalysisWorkbench v0.7.0` is published from the
  verified tag;
- PyPI/package-registry publication remains explicitly deferred;
- ordinary v0.8 architecture and scientific work must not move or recreate any
  existing tag, publish a release, or change version metadata before the
  separately reviewed Gate-B candidate.

## Architecture decision

v0.8 introduces a shared `catalysis_workbench.experimental.operando` layer.

The new layer is intentionally not added to `catalysis_workbench.core`.
`Axis`, `Series`, and `Dataset` remain the released one-dimensional
foundation. Operando state is a domain-aware two-dimensional consumer that
coordinates already prepared spectra or patterns across an explicit acquisition
sequence.

One stack type is shared by Raman, FTIR, XAS/XANES, and XRD. The project must not
create four incompatible matrix containers with different frame, unit, grid, or
provenance rules.

## Frozen retained-state model

### Frame coordinate

An immutable frame coordinate retains:

- a stable unique key;
- an existing `Axis` carrying semantic key, label, unit, and metadata;
- one finite real one-dimensional value per retained frame;
- exact source order;
- optional caller metadata that does not replace the explicit axis semantics.

A stack may retain multiple frame coordinates, for example time, potential,
current density, temperature, cycle index, or source sequence. One
`primary_coordinate_key` is caller selected for a given view or operation.

Frame-coordinate values may repeat and need not be monotonic. Cyclic potential
programs can revisit the same potential, and acquisition order must not be
reconstructed from the coordinate values. Frame identity is provided by unique,
ordered frame keys.

Potential coordinates do not cause reference-electrode, pH, RHE conversion, or
sign conventions to be inferred. Such semantics must already be explicit in the
coordinate axis/metadata and remain compatible with the released
electrochemistry conventions.

### Operando stack

The immutable stack retains:

- unique ordered `frame_keys`;
- one strictly monotonic signal-coordinate array, preserving its increasing or
  decreasing source direction;
- a `signal_axis` and a separate `value_axis`;
- a finite real matrix shaped exactly `(n_frames, n_signal_points)`;
- one or more compatible frame coordinates, each of length `n_frames`;
- the explicit primary coordinate key;
- ordered source keys and reconstructible source-array digests for every frame;
- frozen metadata and a digest over all retained scientific state.

The initial stack builder consumes already validated `Series` objects. Every
frame must have:

- the same signal-point count;
- exactly equal retained signal coordinates;
- compatible signal-axis key, unit, and direction;
- compatible value semantic, unit, and normalization/processing basis;
- a unique source/frame key;
- finite real signal and value arrays.

Grid equality is literal array equality in the first release. No default
tolerance is hidden. A future tolerance or regridding workflow requires a
separate reviewed contract.

Mixed grids, mixed directions, mixed units, mixed intensity bases, missing or
non-finite values, complex values, contradictory digests, duplicate frame keys,
unknown primary coordinates, and shape mismatches fail closed.

The builder does not sort, interpolate, resample, align, smooth, baseline
correct, normalize, clip, fill missing values, convert units, infer frame
coordinates, or mutate caller-owned arrays.

### Derived operando trace

An immutable trace retains one explicit scalar result per frame together with:

- the exact ordered frame keys;
- the selected frame coordinate and its axis/unit;
- a value axis/unit and finite real values;
- an operation/method identifier and caller-visible parameters;
- source stack digest plus per-frame or source-result digests;
- any domain window, peak key, fit key, or descriptor identity required to
  reconstruct what was measured.

A label such as a Raman band, XRD phase, or XAS species is metadata. It is not
evidence that the software identified or proved the chemical assignment.

### Exact cross-modal comparison

The first cross-modal layer compares two already derived traces only when they
have exactly equal ordered frame keys and an explicitly compatible selected
coordinate array, axis semantic, and unit.

Callers must select compatible subsets before comparison. The library does not
automatically intersect keys, choose a coordinate, perform nearest-neighbor
matching, interpolate time/potential, apply dynamic time warping, search lags,
or shift one trace for a stronger relationship.

The first quantitative correlation method is explicit ordinary Pearson
correlation over the retained paired finite values. Constant traces and
insufficient observations fail explicitly. The result retains paired values,
sample count, coefficient, two-sided p-value when supplied by the existing
SciPy kernel, source digests, and the method identity. Correlation is reported
as a statistical association, never as causation or mechanism evidence.

## Explicit measured-point operations

v0.8 operations preserve exact measured values:

- frame selection is by explicit frame keys or retained integer indices;
- signal cropping retains measured signal points inside caller-supplied bounds;
- coordinate selection uses caller-selected coordinate keys and explicit
  comparisons without sorting;
- frame cuts return the exact retained one-dimensional spectrum/pattern;
- signal-position cuts return exact retained values at one retained point;
- domain window measurements reuse reviewed domain functions where available.

No selection operation synthesizes coordinates or values. Interpolated boundary
integration already reviewed inside a domain function remains that domain
function's explicit responsibility and provenance; the operando layer does not
silently add another interpolation.

## Passive visualization contract

Visualization remains a consumer of retained stack or trace state.

### Waterfall

Waterfall rendering preserves the exact signal coordinates, frame order, and
scientific values. A caller-visible finite offset step is applied only to the
display coordinates. The retained stack is unchanged. No normalization,
baseline correction, sorting, color inference, or trace omission occurs.

### Heatmap

The initial heatmap uses retained signal coordinates, explicit frame display
positions, and the exact matrix. Frame display positions use one caller-selected
mode:

- `ordinal` uses the retained acquisition indices and works for repeated or
  non-monotonic condition programs without rewriting their coordinate values;
- `coordinate` uses one selected retained frame coordinate only when its values
  are unique and strictly monotonic in retained order; repeated or non-monotonic
  values fail closed instead of being sorted, deduplicated, or converted to cell
  geometry.

Matplotlib `pcolormesh` center/edge geometry is presentation geometry only;
scientific values are never resampled.

The caller controls:

- selected coordinate and explicit `ordinal` or `coordinate` frame geometry;
- retained frame order;
- explicit value limits or an explicitly requested
  `symmetric_color_limits()` result;
- colormap;
- rasterization/export behavior;
- whether the displayed signal or condition axis is reversed.

The renderer performs no robust/percentile range, clipping, contouring,
smoothing, interpolation, automatic sign/center inference, automatic colormap
selection, or hidden missing-value masking.

### Cuts and traces

Frame cuts, signal-position cuts, and derived traces are plotted from exact
retained arrays using the existing `FigureSpec` and export infrastructure.
Plotting never recalculates band areas, peak positions, widths, correlations, or
other scientific results.

## Domain consumer boundaries

### Raman and FTIR

Operando Raman and FTIR adapters consume series already accepted by the
released validators and processing functions. Every stack must retain one
compatible shift/wavenumber grid and one compatible intensity/absorbance basis.

Band-area, peak-position, and FWHM trajectories require caller-supplied reviewed
band/window/fit identities. v0.8 does not detect peaks, select baselines,
normalize spectra, assign vibrations, or infer intermediates.

### XAS and XANES

Operando XAS adapters consume validated raw XAS series or reviewed normalized
XANES result state under one explicit mode. Raw and normalized states cannot be
mixed in one stack.

Energy grids, energy references, edge/pre-edge/post-edge normalization
provenance, and value units must remain compatible. White-line, edge-position,
window-integral, or fit-derived trajectories require explicit caller methods and
parameters. No species fraction, oxidation state, linear-combination component,
edge shift, or reference spectrum is inferred.

### XRD

Operando XRD adapters consume already validated/prepared XRD series with one
exact 2theta grid, direction, intensity unit, and normalization basis.

Window intensity, caller-selected peak position/FWHM, or fit-derived trajectories
retain their explicit regions and source state. The library does not identify
phases, index peaks, match databases, perform Rietveld refinement, infer lattice
parameters, or claim phase fractions.

## Frozen six-block implementation order

### Block 1 — shared stack foundation

Deliver the immutable frame-coordinate, operando-stack and exact-grid builder
contracts, public exports, digests, reconstruction checks, installed-wheel
audit, and focused failures.

### Block 2 — exact operations, traces and cross-modal comparison

Deliver measured-point frame/signal selection, exact frame and signal cuts,
derived trace state, exact trace compatibility/pairing, and explicit Pearson
correlation with no automatic alignment.

### Block 3 — passive publication visualization

Deliver waterfall, heatmap, cut and trace plotting through `FigureSpec`.
Verify presentation-only offsets/mesh geometry, source-array immutability,
explicit color limits, reversed-display behavior, and exact-size export.

### Block 4 — operando Raman and FTIR

Deliver domain adapters, compatibility checks, heatmap/waterfall examples, and
explicit band/peak trajectory consumers over reviewed domain state.

### Block 5 — operando XAS/XANES

Deliver raw-versus-normalized mode separation, domain adapters, mapping examples,
and explicit descriptor trajectories without hidden energy alignment or species
inference.

### Block 6 — operando XRD

Deliver XRD adapters, mapping examples, and explicit caller-window/peak
trajectories without phase inference or refinement.

Each scientific block must be followed by only the central-document updates
made necessary by the merged state. The six-block boundary must not expand
silently during implementation.

## Prior art and license decisions

The scan is incremental because general project dependencies and visualization
references are already reviewed in `REFERENCES.md`.

- xarray labeled dimensions, coordinates, and attributes are an architecture
  reference. xarray is Apache-2.0. v0.8 does not add xarray as a dependency and
  copies no implementation.
- HyperSpy navigation axes versus signal axes are a useful multidimensional
  workflow reference. HyperSpy is GPL-3.0 and remains reference-only; no
  dependency or copied/adapted code is permitted.
- specutils multidimensional spectral-axis representations are an API/axis
  reference. specutils is BSD-3-Clause and is not added as a dependency.
- Matplotlib `pcolormesh` and `LineCollection` are rendering references.
  Matplotlib is already a runtime dependency under its own PSF-based license.
- CatalysisWorkbench-owned `Axis`, `Series`, `Dataset`, domain validators,
  digest/provenance patterns, `FigureSpec`, and
  `symmetric_color_limits()` are the implementation foundation.

No new runtime dependency is authorized by this architecture checkpoint. NumPy,
SciPy, and Matplotlib remain the numerical/rendering stack.

## Testing and installed-package gates

Every block requires focused unit coverage plus the repository's full exact-head
CI. The v0.8 matrix must cover:

- immutability and caller-array non-mutation;
- exact frame and signal order;
- increasing and decreasing signal axes;
- repeated and non-monotonic frame-coordinate values retained in scientific
  state;
- ordinal heatmap rendering for those coordinates plus fail-closed coordinate
  geometry when values are repeated or non-monotonic;
- multiple coordinates and explicit primary-coordinate selection;
- exact common-grid success and every mixed-grid/unit/basis failure;
- finite/real/shape/key/digest reconstruction failures;
- exact selection/cropping/cut semantics;
- no automatic intersection or alignment of cross-modal traces;
- correlation constant/insufficient-input failures;
- passive-renderer source-digest invariance;
- explicit heatmap range and presentation-only waterfall offset behavior;
- domain-specific raw/processed compatibility boundaries;
- fresh-wheel public imports and documented examples.

Optional dependencies, if a later block genuinely requires one, need a separate
reviewed dependency/license decision and their own fresh-wheel smoke. This
architecture authorizes none.

## Release handoff

After all six scientific blocks merge:

1. synchronize the completed scientific state;
2. Gate A freezes and audits the full installed-wheel/public-API scope while
   retaining version `0.7.0`;
3. Gate B changes distribution/runtime version to the final `0.8.0` candidate
   and validates the exact wheel;
4. Gate C tag creation and reverse verification require separate explicit
   authorization and must target the reviewed Gate-B commit exactly;
5. GitHub Release publication remains a separate explicit decision;
6. PyPI/package-registry publication remains deferred unless separately
   authorized.

## Explicitly out of scope for v0.8

- raw proprietary vendor-file parsing or live instrument acquisition;
- streaming, callbacks, dashboards, instrument control, or real-time feedback;
- automatic grid alignment, interpolation, resampling, time warping, or lag
  search;
- hidden smoothing, baseline correction, normalization, clipping, unit
  conversion, missing-value repair, or coordinate inference;
- automatic Raman/IR peak detection or chemical assignment;
- XAS species/oxidation-state/linear-combination inference;
- XRD phase identification, database matching, indexing, Rietveld refinement,
  lattice refinement, or phase fractions;
- causality or mechanism claims from correlation;
- GUI/browser/Jupyter interactive editing, which remains v0.9-v1.0 scope;
- VASP/HPC or other job execution;
- v0.7.1, tag movement/recreation, release publication, or package-registry
  publication.

## Immediate handoff after this architecture checkpoint

After this Issue merges, synchronize the architecture authority into central
documentation only where necessary, reverify the exact `main` head and v0.7
release invariants, and begin Block 1 from a new scoped Issue and Draft PR. No
production v0.8 code belongs in the architecture checkpoint.
