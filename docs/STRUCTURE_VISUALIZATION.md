# Static structure visualization

The v0.5 structure-visualization layer separates scientific structure state, resolved visual scene state, and the concrete renderer.

```text
AtomicStructure
    -> build_structure_scene(...)
    -> immutable StructureScene
    -> plot_structure(...)
```

The renderer never receives an `AtomicStructure` and therefore cannot infer bonds, periodic images, coordination, or other scientific geometry while drawing.

## Renderer-neutral scene

`StructureScene` retains already-resolved atom, bond, unit-cell, camera, and presentation state. Atom identities use the reviewed `SiteImage` contract, so periodic copies remain explicit.

By default, `build_structure_scene()` includes exactly the canonical zero-image sites in original site order. Additional periodic images are included only when the caller supplies them in `atom_images`.

Bonds are never inferred. A visible bond requires an explicit `StructureBondSpec(first, second, style)` and both endpoint `SiteImage` identities must already exist in the scene atom list.

For periodic structures, the 12 unit-cell edges are generated directly from the retained lattice row vectors. Cell geometry is visual geometry only and does not alter the structure model.

## Presentation-only element defaults

The scene layer provides deterministic colors and compact visual radii for common elements plus neutral fallbacks. These values are deliberately presentation-only:

- they are not covalent or ionic radii databases;
- they are not used for bond detection;
- they are not used for coordination analysis;
- changing them cannot change any scientific result.

Callers may override styles per element or per stable site key with `StructureAtomStyle`.

## Camera and projection

`StructureCameraSpec` makes the camera reproducible. The v0.5 default is orthographic projection with explicit elevation, azimuth, and roll angles. Perspective is supported only when requested explicitly.

This is intentionally narrower than the interactive trackball/orbit controls used by browser-oriented tools such as pretty-lattice.

## Static Matplotlib renderer

`plot_structure(scene, ...)` is a passive Matplotlib 3D adapter. It draws:

- one marker for each retained atom visual;
- one line for each explicit bond;
- the retained 12 cell edges when visible;
- optional retained atom labels.

`points_per_angstrom` converts the scene's presentation radius to marker size. This conversion is a display scale, not a scientific length transformation. The renderer applies equal x/y/z plotting extents, an explicit projection, and the physical figure dimensions carried by `FigureSpec`.

The default axes are hidden for publication-style structure figures. `show_axes=True` exposes Cartesian axes in angstrom for diagnostic use.

## Example

```python
from catalysis_workbench.computation import (
    SiteImage,
    StructureAtomStyle,
    StructureBondSpec,
    build_structure_scene,
)
from catalysis_workbench.visualization import plot_structure

scene = build_structure_scene(
    structure,
    bonds=(StructureBondSpec(SiteImage("site-0000"), SiteImage("site-0001")),),
    element_styles={"Pb": StructureAtomStyle("#575961", 0.65)},
)
figure, ax = plot_structure(scene)
```

## Prior-art boundary

`pretty-lattice` is the major scene/UX reference: it separates backend-resolved atom/bond/cell records from frontend controls and uses a reproducible orthographic starting view. CatalysisWorkbench adopts that separation principle but does not copy the Three.js/browser implementation.

## Explicit non-actions

This v0.5 block does not provide automatic bond inference, polyhedra, symmetry-derived images, browser/Three.js rendering, interactive editing, ray tracing, volumetric data, or charge-density visualization.
