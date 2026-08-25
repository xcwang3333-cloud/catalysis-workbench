# Advanced Volumetric 3-D Rendering

v0.7 Block 7 adds a publication-oriented static three-dimensional backend for the renderer-neutral volumetric state introduced in Blocks 1-2. Scientific scalar-field state remains owned by CatalysisWorkbench; PyVista/VTK is an optional rendering implementation only.

## Installation boundary

The base package does not require or import PyVista or VTK.

Install the optional backend explicitly:

```bash
pip install "catalysis-workbench[volumetric3d]"
```

The reviewed Block-7 dependency window is:

```text
pyvista >= 0.48.4, < 0.49
vtk >= 9.5, < 9.7
```

PyVista is MIT licensed. VTK is BSD-3-Clause. VTK wheels are large, so this stack remains isolated from the base wheel. Current scikit-image was not selected because its development line requires Python >=3.12 while CatalysisWorkbench continues to support Python >=3.11.

## Public authority

The public rendering input is still `VolumetricScene` with retained `IsosurfaceLayerSpec`, `SliceLayerSpec`, optional `StructureScene`, and `StructureCameraSpec` state.

Block 7 does not create a second scientific volumetric representation. In particular, it does not:

- alter `ScalarField` or released-v0.6 `VolumetricGrid` semantics;
- recompute charge-density difference;
- normalize or clip scientific scalar values;
- smooth or resample a scientific field;
- align, shift, wrap or replicate the source grid;
- infer an isovalue, slice, bond, camera orientation or periodic image.

PyVista/VTK objects are private backend temporaries. `render_volumetric_scene_3d(...)` returns a CatalysisWorkbench-owned `Volumetric3DRenderResult` containing only an immutable uint8 screenshot and backend/version provenance. It never returns a Plotter, actor, VTK mesh or VTK array.

## Explicit render specification

`Volumetric3DRenderSpec` contains presentation/export controls only:

- exact screenshot width and height in pixels;
- transparent-background choice;
- surface and slice lighting switches;
- anti-aliasing mode;
- scalar-bar visibility;
- atom-sphere tessellation;
- explicit mapping from retained bond linewidth to a 3-D tube radius;
- camera framing factors and perspective view angle;
- optional explicit fractional clipping bounds.

The scene itself retains the layer colors, opacities, colormaps, scalar display limits, background and `StructureCameraSpec` projection/azimuth/elevation/roll.

## Full-lattice source-grid geometry

For a scalar field with source shape `(n0, n1, n2)`, each retained source sample is located at

```text
f(i,j,k) = (i/n0, j/n1, k/n2)
r(i,j,k) = f(i,j,k) @ L
```

where `L` is the complete retained 3x3 lattice matrix whose rows are the lattice vectors.

The PyVista backend builds an explicit `StructuredGrid` from these Cartesian positions. It does not approximate the cell using only axis lengths or `ImageData.spacing`. This distinction is mandatory for skew cells.

The scalar array is copied to backend point data with ordering regression-tested against the retained source array. The source array remains immutable and its digest remains unchanged.

## Isosurface semantics

An `IsosurfaceLayerSpec.threshold` is the only isovalue used by the backend.

VTK contouring linearly interpolates mesh geometry between retained source-grid samples. That interpolation is a presentation mesh operation only; it does not create a replacement scientific `ScalarField`, modify source values or become new scientific authority.

A visible threshold that produces no contour fails explicitly. There is no inferred percentile, extrema-based threshold, smoothing, periodic seam welding or unit-cell replication.

For a hand-verifiable scalar field whose value equals one fractional coordinate, the regression suite checks that a contour at threshold `t` produces Cartesian vertices which map back through `inv(L)` to that same fractional coordinate `t` even for a skew lattice.

## Exact slice semantics

`SliceLayerSpec` consumes an already-reviewed `ScalarFieldSlice`. The 3-D backend does not ask VTK to slice the original volume.

The exact retained slice positions are obtained through `slice_cartesian_coordinate_grid(...)` and the exact retained 2-D values are copied to a 2-D structured surface. `value_min` and `value_max` remain color-display limits only.

## Fractional clipping

Clipping is disabled unless `Volumetric3DRenderSpec.clip_fractional_bounds` is supplied explicitly.

For row-lattice matrix `L`, Cartesian and fractional coordinates satisfy

```text
r = f @ L
f = r @ inv(L)
```

Therefore the normal of a constant fractional-coordinate plane for axis `a` is proportional to column `a` of `inv(L)`. The backend uses these full-lattice plane normals and explicit lower/upper fractional origins.

Clipping is applied only to temporary presentation geometry. Source scalar values, slice values, scene state and digests are never changed. No interactive clip widget is introduced in v0.7.

## Structure overlay

If a `VolumetricScene` contains `structure_scene`, the backend uses only the already-resolved retained state:

- atom positions, colors, radii and alpha;
- explicit visual bonds and their styles;
- retained cell edges and cell style.

No bond, coordination shell, periodic image or atom correspondence is inferred by the 3-D renderer. Sphere tessellation and the bond-linewidth-to-tube-radius conversion are explicit presentation controls in `Volumetric3DRenderSpec`.

## Camera mapping

`VolumetricScene.camera` remains authoritative for:

- orthographic versus perspective projection;
- azimuth;
- elevation;
- roll.

Block 7 deterministically maps those angles into a backend camera around the visible scene bounds. Bounds are used only for framing distance/scale. The caller-visible render specification controls framing factors and perspective view angle. No scientific structure rotation or alignment is performed.

## Static rendering and export

The v0.7 backend is intentionally off-screen/static.

```python
from catalysis_workbench.visualization import (
    Volumetric3DRenderSpec,
    render_volumetric_scene_3d,
    export_volumetric_scene_3d,
)

spec = Volumetric3DRenderSpec(
    window_size_px=(1200, 900),
    anti_aliasing="ssaa",
)
result = render_volumetric_scene_3d(scene, spec)
export_volumetric_scene_3d(scene, "charge_difference.png", spec)
```

`result.image` is an immutable uint8 RGB/RGBA array. PNG is the reviewed initial export format. Screenshot dimensions and transparency are explicit.

Interactive windows, widgets, browser/Jupyter scene editing and the eventual interactive plot editor remain outside v0.7.

## Headless CI

The optional backend has a separate fresh-wheel CI path. The job:

1. builds the CatalysisWorkbench wheel;
2. installs it with `[volumetric3d]` in a fresh Python 3.11 environment;
3. installs only the system runtime GL libraries required by current VTK wheels;
4. verifies `pip check`;
5. renders skew-cell isosurfaces and exact slices off-screen;
6. exercises explicit fractional clipping, retained structure overlays, orthographic and perspective cameras, and PNG export.

Current VTK 9.5+ wheel behavior is validated directly in CI rather than assumed from documentation. The base-wheel job separately verifies that importing the Block-7 public surface does not import PyVista or VTK.

## Failure boundaries

The backend fails rather than silently repairing state when:

- the optional backend is not installed;
- explicit render settings are malformed;
- a visible isosurface does not intersect the source field;
- every visible volumetric layer is removed by explicit clipping;
- no renderable visible scene geometry exists;
- screenshot/export generation fails.

Existing `VolumetricScene` construction continues to fail earlier on incompatible structure, lattice, grid shape or registration identity.

## Prior art and licenses

Implementation-time review used:

- PyVista 0.48.4 — MIT — selected optional rendering facade;
- VTK 9.5-9.6 line — BSD-3-Clause — selected through the optional PyVista backend;
- scikit-image — BSD family — reference only; current development line requires Python >=3.12 and was not added.

The implementation uses public backend APIs and does not copy/adapt third-party source code.

## Explicitly out of scope

- scientific-grid interpolation/resampling/alignment;
- periodic seam welding or supercell replication;
- automatic threshold selection;
- scientific smoothing/normalization;
- volume segmentation or chemistry inference;
- interactive clipping widgets;
- browser/Jupyter/GUI editor workflows;
- VASP or HPC execution;
- v0.8 operando/time-resolved work;
- release-version/tag/GitHub Release/PyPI mutation.
