# Volumetric visualization foundation

This document defines the reviewed v0.7 Block-1 scalar-field and renderer-neutral volumetric-scene contract. The release-specific architecture remains authoritative in `V0_7_PLAN.md`.

## Scope

Block 1 provides a common state layer for later charge-density-difference, electron-density and ELF visualization. It does not render meshes, infer chemistry, parse ELFCAR, or add PyVista/VTK/scikit-image as runtime dependencies.

## ScalarField

`ScalarField` represents exactly one finite three-dimensional scalar quantity on one fully periodic `AtomicStructure` with an explicit nonsingular lattice.

Retained scientific state includes the exact source-grid values, grid shape, `field_kind`, explicit `value_unit`, optional explicit `registration_id`, source type/key/digest, structure identity, cell volume, voxel volume and deterministic digest. Metadata is detached provenance and does not alter the scientific digest.

The contract is unit-generic but never unit-converting. No normalization, clipping, smoothing, interpolation, resampling, alignment, origin shift or lattice transformation is performed.

### Released-v0.6 adapters

`scalar_field_from_volumetric_grid(...)` selects exactly one retained `VolumetricGrid` component and preserves its values, structure, canonical unit and source digest.

`scalar_field_from_charge_density_difference(...)` exposes the already-computed signed `ChargeDensityDifferenceResult.difference` as a scalar field. It preserves the result digest, difference-grid digest and explicit registration identity. It does not repeat charge-density-difference arithmetic.

Adapter-owned provenance keys are reserved and cannot be overwritten by caller metadata. Optional caller metadata is retained separately under `adapter_metadata`.

## Source-grid coordinates

The retained periodic grid convention is

`fractional(i, j, k) = (i/Nx, j/Ny, k/Nz)`.

Cartesian geometry is always obtained with the full lattice matrix:

`cartesian = fractional @ lattice_angstrom`.

This full-matrix rule is required for skew cells. Independent axis-length spacing is not an equivalent geometry contract.

`fractional_grid_coordinate(...)` and `cartesian_grid_coordinate(...)` evaluate one source-grid point on demand; constructing a full Cartesian volume is not required for ordinary scalar-field state.

## Exact source-grid slices

`slice_scalar_field(...)` selects exactly one source plane by axis `0|1|2` and zero-based integer index. The slice retains the exact `numpy.take` source values, original unit, source-field digest, structure/lattice identity, full source grid shape, in-plane source-axis order and fixed fractional coordinate `index/N_axis`.

There is no arbitrary-plane interpolation, averaging, wrapping or resampling in Block 1.

`slice_fractional_coordinate_grid(...)` and `slice_cartesian_coordinate_grid(...)` construct physical slice coordinates on demand from the retained source-grid convention and full lattice matrix.

## Renderer-neutral layer specifications

`IsosurfaceLayerSpec` retains an explicit finite threshold in the source field unit plus display-only color, opacity, visibility and label state. Thresholds are never inferred from extrema, percentiles or chemistry. Positive and negative isovalues are distinct explicit layers.

`SliceLayerSpec` retains one exact `ScalarFieldSlice` plus display-only colormap, opacity, visibility and optional display range. These presentation settings never alter the retained scalar values.

Neither class extracts a mesh or invokes Matplotlib, PyVista, VTK or scikit-image.

## VolumetricScene compatibility

`VolumetricScene` preserves caller-declared layer order. Multiple volumetric layers fail closed unless they retain the same structure digest, exact grid shape, exact lattice matrix and identical registration-id semantics. No alignment or resampling is attempted.

Multiple layers derived from one exact source field may omit `registration_id`, because their co-registration is intrinsic to the retained source-field identity. A scene that combines distinct source-field digests requires the same explicit nonblank `registration_id`; two independently sourced fields are never treated as co-registered merely because both omit registration metadata.

An optional existing `StructureScene` may be attached only when its `structure_digest` exactly matches the volumetric layers. Bonds and coordination are never rebuilt automatically.

Scene camera, background, colors, opacity and colormap are presentation-only. Layer `geometry_digest` values retain scientific geometry selection such as source field/slice identity and explicit isovalue while excluding display restyling.

## Prior-art and dependency boundary

PyVista structured-grid/contour APIs are useful reference for later backend integration because they accept explicit point grids and explicit contour values. scikit-image marching-cubes is also reference-only; its axis-aligned spacing parameter is not a replacement for the full skew-lattice matrix contract used here.

Block 1 adds no new runtime dependency. Heavy 3-D mesh extraction, rendering and export remain v0.7 Block 7.

## Deferred to later blocks

- Block 2: charge-density-difference, electron-density and ELF technique-specific visualization workflows, including any ELF/ELFCAR adapter decision.
- Blocks 3-6: band structure, PROCAR/fat bands, LOCPOT/work function and NEB/barrier state/plotting.
- Block 7: advanced volumetric 3-D backend, mesh extraction, rendering and export.

VASP/HPC execution and complete workflow management remain outside the project scope.
