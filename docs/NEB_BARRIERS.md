# NEB image-energy and discrete barrier contract

v0.7 Block 6 adds post-processing and passive plotting for already-generated NEB image energies. CatalysisWorkbench does not run, optimize, interpolate, or repair an NEB calculation.

The architecture authority remains [`V0_7_PLAN.md`](V0_7_PLAN.md), with concrete acceptance tracked by Issue #223.

## Public scientific state

### `NEBImageState`

One image retains:

- a stable nonblank image key;
- one finite absolute energy in eV;
- explicit source key/type/digest provenance;
- an optional reviewed immutable `AtomicStructure` attachment;
- an optional presentation label;
- a deterministic scientific digest.

The absolute energy is retained literally. The image state does not subtract a reference, normalize, smooth, align, correct, or reinterpret the value.

An attached structure is provenance/inspection state only. It does not trigger atom matching, atom reordering, minimum-image remapping, Kabsch alignment, IDPP, path fitting, or reaction-coordinate construction.

Presentation labels are not part of the scientific digest.

## Exact ordered path state

`NEBPath` retains the exact caller/source image order. Image keys must be unique, and the implementation never sorts images by key, energy, coordinate, structure, or any inferred path property.

### Reaction coordinate

Two explicit modes are available:

- `ordinal`: exact retained source image indices `0, 1, ..., N-1`;
- `explicit`: one finite caller-supplied coordinate for every retained image.

`build_neb_path(...)` selects `ordinal` only when no reaction-coordinate array is supplied. Otherwise it retains the caller array literally.

Explicit coordinates are not sorted, interpolated, normalized, accumulated from structures, or otherwise transformed. CatalysisWorkbench does not infer a geometric reaction coordinate.

### Energy reference

Two retained energy modes are available:

- `absolute`: plotted path energies are the exact image absolute energies;
- `reference_relative`: plotted path energies are exactly `E_i - E_reference` for one explicit retained `reference_image_key`.

There is no implicit first-image zeroing. A relative path requires a caller-visible retained reference image key.

The path object self-validates that its retained plotted-energy array exactly matches the selected absolute/reference arithmetic, so direct construction cannot silently inject another energy transform.

## Explicit discrete barrier

`calculate_neb_barrier(...)` requires all three caller-visible keys:

- `initial_image_key`;
- `saddle_image_key`;
- `final_image_key`.

The three images must be distinct, retained in the path, and ordered `initial < saddle < final` in the exact source path.

Barrier arithmetic uses the image **absolute** energies regardless of whether the path is displayed in absolute or reference-relative mode:

```text
forward discrete-image barrier = E_saddle - E_initial
reverse discrete-image barrier = E_saddle - E_final
```

`NEBBarrierResult` retains exact keys, source indices, image digests, absolute energies, both barrier values, the path digest, and the explicit semantics token `discrete_retained_image`.

The result represents a barrier through one explicitly designated retained image. CatalysisWorkbench does not select the highest-energy image automatically, fit a spline, search a spline maximum, fit a polynomial, smooth the path, or invent a continuous transition state.

Unexpected negative forward or reverse arithmetic is retained rather than clipped.

`validate_neb_barrier_path(...)` can be used by reporting/rendering consumers to fail closed unless the result points to the exact retained image identities and energies of one path.

## Reporting

`neb_path_frame(...)` returns a detached table containing retained image order, coordinates, absolute/plotted energies, reference mode/key, source provenance, image digest, and optional structure digest.

`neb_barrier_frame(...)` returns a detached one-row summary of the explicit discrete barrier state.

These helpers expose already-retained state; they do not recompute a path, reference, saddle, or barrier.

## Passive plotting

`plot_neb_path(...)` renders one retained `NEBPath` using:

- x coordinates exactly from `path.reaction_coordinates`;
- y coordinates exactly from `path.plotted_energy_ev`;
- one marker per retained image;
- straight source-order point-to-point segments only;
- optional saddle highlighting only when a compatible explicit `NEBBarrierResult` is supplied.

The renderer does not invoke a spline, tangent estimator, smoother, interpolator, optimizer, or highest-image search. Without an explicit barrier result, no image is automatically styled as a saddle even if it is the maximum retained energy.

`FigureSpec` controls presentation only. Category labels may rename tick labels for display, but retained images cannot be hidden because doing so would visually alter the scientific path. Linear x/y scales are required for this reviewed Block-6 renderer.

## Prior art and dependency decision

Implementation-time review reconfirmed:

- full `pymatgen` is MIT and provides higher-level `NEBAnalysis` behavior useful as scientific/regression reference;
- ASE is LGPL-2.1-or-later and provides mature NEB optimization, climbing-image, interpolation and plotting behavior useful as reference;
- CatalysisWorkbench intentionally does not add either package as a Block-6 runtime dependency;
- existing optional `pymatgen-core` remains unchanged and is not needed to construct the minimum explicit image/path/barrier state.

The reason is semantic as well as packaging-related: v0.7 intentionally exposes discrete retained-image arithmetic rather than importing automatic spline, interpolation, optimizer, atom-correspondence, or transition-state inference.

## Failure boundaries

Block 6 fails closed for:

- blank image/path/provenance keys;
- nonfinite energies or reaction coordinates;
- fewer than two path images;
- duplicate image keys;
- malformed ordinal coordinates;
- coordinate/energy array length mismatches;
- a relative path without an explicit retained reference image;
- plotted-energy arrays inconsistent with exact retained reference arithmetic;
- missing, duplicate, or source-order-incompatible initial/saddle/final barrier keys;
- barrier values inconsistent with `E_saddle - E_initial/final`;
- non-discrete barrier semantics in the reviewed result object;
- barrier/path provenance mismatch during rendering;
- nonlinear plotting scales or attempts to hide retained path images.

## Explicitly out of scope

v0.7 Block 6 does not:

- execute VASP, VTST, ASE, or another NEB engine;
- generate or interpolate images;
- perform linear or IDPP atom-coordinate interpolation;
- calculate NEB spring or tangent forces;
- run climbing-image optimization;
- inspect force convergence;
- infer atom correspondence or reorder atoms;
- apply minimum-image remapping or structural alignment;
- identify a saddle/highest image automatically;
- fit splines, polynomials, smooth curves, or continuous transition states;
- submit scheduler/HPC jobs;
- implement v0.7 Block-7 advanced 3-D rendering.

## Minimal example

```python
from catalysis_workbench.computation import (
    NEBImageState,
    build_neb_path,
    calculate_neb_barrier,
)
from catalysis_workbench.visualization import plot_neb_path

images = (
    NEBImageState("00", -10.0, "energy:00", "external", "digest-00"),
    NEBImageState("01", -9.4, "energy:01", "external", "digest-01"),
    NEBImageState("02", -9.0, "energy:02", "external", "digest-02"),
    NEBImageState("03", -9.6, "energy:03", "external", "digest-03"),
)

path = build_neb_path(
    images,
    key="diffusion-path",
    reaction_coordinates=[0.0, 0.4, 1.2, 2.0],
    reference_image_key="00",
)
barrier = calculate_neb_barrier(
    path,
    initial_image_key="00",
    saddle_image_key="02",
    final_image_key="03",
)
figure, axes = plot_neb_path(path, barrier=barrier)
```

For these exact image energies, the forward discrete-image barrier is `1.0 eV` and the reverse discrete-image barrier is `0.6 eV` (subject only to ordinary binary floating representation in machine storage).
