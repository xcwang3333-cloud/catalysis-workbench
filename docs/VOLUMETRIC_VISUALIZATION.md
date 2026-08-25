# Volumetric visualization

This document defines the reviewed v0.7 scalar-field and volumetric-visualization contracts. The release-specific architecture remains authoritative in `V0_7_PLAN.md`.

## Block 1 — scalar-field and renderer-neutral foundation

`ScalarField` represents exactly one finite three-dimensional scalar quantity on one fully periodic `AtomicStructure` with an explicit nonsingular lattice. Retained scientific state includes exact source-grid values, grid shape, `field_kind`, explicit `value_unit`, optional explicit `registration_id`, source type/key/digest, structure identity, cell volume, voxel volume and deterministic digest. Metadata is detached provenance and does not alter the scientific digest.

The contract is unit-generic but never unit-converting. No normalization, clipping, smoothing, interpolation, resampling, alignment, origin shift or lattice transformation is performed.

### Released-v0.6 adapters

`scalar_field_from_volumetric_grid(...)` selects exactly one retained `VolumetricGrid` component and preserves its values, structure, canonical unit and source digest.

`scalar_field_from_charge_density_difference(...)` exposes the already-computed signed `ChargeDensityDifferenceResult.difference` as a scalar field. It preserves the result digest, difference-grid digest and explicit registration identity. It does not repeat charge-density-difference arithmetic.

Adapter-owned provenance keys are reserved and cannot be overwritten by caller metadata. Optional caller metadata is retained separately under `adapter_metadata`.

### Source-grid coordinates

The retained periodic grid convention is

`fractional(i, j, k) = (i/Nx, j/Ny, k/Nz)`.

Cartesian geometry is always obtained with the full lattice matrix:

`cartesian = fractional @ lattice_angstrom`.

This full-matrix rule is required for skew cells. Independent axis-length spacing is not an equivalent geometry contract.

`fractional_grid_coordinate(...)` and `cartesian_grid_coordinate(...)` evaluate one source-grid point on demand; constructing a full Cartesian volume is not required for ordinary scalar-field state.

### Exact source-grid slices

`slice_scalar_field(...)` selects exactly one source plane by axis `0|1|2` and zero-based integer index. The slice retains the exact source values, original unit, source-field digest, structure/lattice identity, full source grid shape, in-plane source-axis order and fixed fractional coordinate `index/N_axis`.

There is no arbitrary-plane interpolation, averaging, wrapping or resampling. `slice_fractional_coordinate_grid(...)` and `slice_cartesian_coordinate_grid(...)` construct physical slice coordinates on demand from the retained source-grid convention and full lattice matrix.

### Renderer-neutral layer specifications

`IsosurfaceLayerSpec` retains an explicit finite threshold in the source field unit plus display-only color, opacity, visibility and label state. Thresholds are never inferred from extrema, percentiles or chemistry. Positive and negative isovalues are distinct explicit layers.

`SliceLayerSpec` retains one exact `ScalarFieldSlice` plus display-only colormap, opacity, visibility and optional display range. These presentation settings never alter retained scalar values.

Neither class extracts a mesh or stores a Matplotlib, PyVista, VTK or scikit-image object.

### VolumetricScene compatibility

`VolumetricScene` preserves caller-declared layer order. Multiple volumetric layers fail closed unless they retain the same structure digest, exact grid shape, exact lattice matrix and identical registration-id semantics. No alignment or resampling is attempted.

Multiple layers derived from one exact source field may omit `registration_id`, because their co-registration is intrinsic to the retained source-field identity. A scene that combines distinct source-field digests requires the same explicit nonblank `registration_id`; two independently sourced fields are never treated as co-registered merely because both omit registration metadata.

An optional existing `StructureScene` may be attached only when its `structure_digest` exactly matches the volumetric layers. Bonds and coordination are never rebuilt automatically.

Scene camera, background, colors, opacity and colormap are presentation-only. Layer `geometry_digest` values retain scientific geometry selection such as source field/slice identity and explicit isovalue while excluding display restyling.

## Block 2 — charge density, electron density, and ELF

### Charge-density difference

`build_charge_density_difference_scene(...)` consumes an existing reviewed `ChargeDensityDifferenceResult`. It converts that already-computed result through `scalar_field_from_charge_density_difference(...)` and creates separate positive and negative `IsosurfaceLayerSpec` objects in caller-visible order.

The positive threshold must be finite and strictly positive; the negative threshold must be finite and strictly negative. `build_symmetric_charge_density_difference_scene(...)` is only a convenience for one explicit positive magnitude and constructs exactly `+m` and `-m`. Neither helper derives a threshold from extrema, percentiles, integrated difference, chemistry or structure, and neither repeats the v0.6 charge-density-difference arithmetic.

Colors, opacity and labels are presentation-only. The signed field values, `registration_id`, result digest, difference-grid digest, structure, lattice and grid remain unchanged and auditable.

### Electron density

`build_electron_density_scene(...)` requires the explicit `total` component of a reviewed v0.6 `VolumetricGrid` and adapts it literally as `field_kind="electron-density"` with canonical `1/angstrom^3` units. It does not reinterpret `magnetization_z` as total electron density.

The isosurface threshold is an explicit finite caller value. There is no maximum normalization, logarithm, clipping, smoothing, unit conversion, interpolation or grid transformation.

### ELFCAR / ELF channels

`read_elfcar_field(...)` is a lazy optional `pymatgen-core` adapter and returns exactly one `ScalarField` for one explicit physical ELF channel. The returned unit is the literal token `dimensionless`; source values are copied exactly after parser conversion and are not clipped to `[0, 1]`, normalized, converted through `get_alpha()`, or reinterpreted as kinetic-energy density.

For an unpolarized one-channel ELFCAR, the caller selects `spin="total"`. For a collinear two-channel source, the caller must select `spin="up"` or `spin="down"` explicitly.

Current `pymatgen-core` (change introduced in v2026.8.13) exposes direct collinear ELF channels as `spin_up` and `spin_down`. Earlier releases used the misleading keys `total` and `diff` for the two direct spin blocks. CatalysisWorkbench version-guards that historical layout: only an installed backend version older than 2026.8.13 may map legacy `total -> up` and `diff -> down`. A current backend unexpectedly returning two-key `total/diff` fails closed. The legacy ELF keys are never interpreted with CHGCAR total-density/magnetization-difference semantics.

ELF provenance retains the `pymatgen-core` version, backend data keys, selected backend key, physical channel, source path/source ID and a deterministic full-source digest. Unexpected channel layouts, non-finite values and mismatched channel grid shapes fail closed.

`pymatgen-core` remains behind the existing `structure` optional extra; Block 2 adds no new runtime dependency.

### Technique-level ELF scene

`build_elf_scene(...)` accepts only a dimensionless scalar field with an explicit `elf`, `elf-spin-up` or `elf-spin-down` field kind. The caller supplies the finite isovalue. The helper returns renderer-neutral `VolumetricScene` state and performs no mesh extraction.

### Exact 2-D slice rendering

`plot_scalar_field_slice(...)` is the Block-2 passive Matplotlib renderer for one existing `SliceLayerSpec`. It plots the exact retained two-dimensional values as flat source-grid cells; it does not interpolate, smooth, resample, replicate periodically or alter the scalar field.

The renderer requires explicit `value_min` and `value_max` on the `SliceLayerSpec`; it refuses automatic display-range inference. The retained colormap and opacity are display-only.

Two coordinate modes are supported:

- `angstrom`: an intrinsic two-dimensional plane basis is constructed from the two retained in-plane lattice vectors. The first vector defines positive x; the component of the second vector perpendicular to the first defines positive y. This preserves a skew cell's in-plane geometry while leaving source values unchanged.
- `fractional`: the two retained source-grid axes are displayed directly from 0 to 1.

The colorbar reports the retained field label/kind and physical unit. Linear x/y scales are required.

## Dependency and rendering boundary

PyVista structured-grid/contour APIs and scikit-image marching cubes remain reference-only for later integration. Their presence is not required for Blocks 1 or 2, and axis-aligned spacing is not a replacement for the full skew-lattice matrix contract.

Block 2 contains no mesh extraction or three-dimensional rendering. Advanced mesh extraction, PyVista/VTK integration, periodic-image display transforms and 3-D export remain v0.7 Block 7.

## Deferred to later blocks

- Blocks 3-6: band structure, PROCAR/fat bands, LOCPOT/work function and NEB/barrier state/plotting.
- Block 7: advanced volumetric 3-D backend, mesh extraction, rendering and export.

VASP/HPC execution and complete workflow management remain outside the project scope.
