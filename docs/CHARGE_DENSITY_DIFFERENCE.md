# Charge-density difference

CatalysisWorkbench v0.6 Block 9 implements strict arithmetic on already co-registered volumetric electron-number-density grids. It deliberately does not perform volumetric visualization, interpolation, alignment, atom matching, or CHGCAR normalization.

## Scientific definition

The retained operation is

`Delta n(r) = n_combined(r) - sum_i c_i * n_reference_i(r)`

where every `c_i` is finite, explicit and caller supplied. The combined source is retained separately from the ordered reference terms. Coefficients are never inferred from source labels, atom counts, stoichiometry, chemical formulas or structure size.

The result is an electron-number-density difference. Although the conventional workflow is often called a "charge-density difference", positive and negative `Delta n(r)` values describe differences in electron-number density under the retained sign convention; the API does not silently convert them to signed Coulomb charge density.

## Canonical volumetric foundation

Block 9 reuses the reviewed immutable `VolumetricGrid` from Block 1.

For current VASP CHGCAR input, the canonical pointwise density unit is exactly `1/angstrom^3`. The reviewed CHGCAR adapter already converts the backend grid once as

`n(r) = parsed_grid / V_cell`.

Block 9 never divides by cell volume again and never divides pointwise values by the number of grid points. The retained voxel volume is

`V_voxel = V_cell / N_grid`,

so integrating the difference uses the existing `VolumetricGrid` integral

`sum(Delta n) * V_voxel`.

For canonical total electron-number density this integrated diagnostic is reported in electrons.

## Public state

`ChargeDensitySource` identifies one retained volumetric source through:

- a stable caller-visible source key;
- the exact immutable `VolumetricGrid` and its digest;
- the exact source `AtomicStructure` digest;
- one explicit component key such as `total`;
- one explicit registration ID asserting the real-space co-registration frame;
- an optional presentation label that is excluded from scientific digest identity.

`ChargeDensityReferenceTerm` combines one source with an explicit coefficient.

`ChargeDensityDifferenceResult` retains:

- the combined source;
- the exact ordered reference terms and coefficients;
- the immutable output `VolumetricGrid` containing exactly one `difference` component;
- the caller-visible lattice tolerance;
- registration/component/unit provenance through the retained sources;
- cell volume, voxel volume and integrated difference through the output grid;
- a deterministic scientific digest.

Direct construction of a result is fail-closed: the retained output difference must exactly equal arithmetic recomputed from the retained source grids and coefficients.

## Co-registration compatibility gates

Before arithmetic, every reference source must satisfy all of the following against the combined source:

1. the same explicit `registration_id`;
2. the same like-for-like component key;
3. the same physical density unit;
4. exactly the same 3D grid shape;
5. a directly compatible lattice matrix under the caller-supplied absolute `lattice_tolerance_angstrom`, evaluated with zero relative tolerance.

The lattice comparison is direct matrix comparison. CatalysisWorkbench does not search for crystallographically equivalent cells, rotate/reduce lattices, build supercells, or otherwise transform a source to make it pass.

The lattice tolerance may be zero for exact matrix equality. It must be finite and non-negative, is retained in the result, and participates in scientific digest identity.

## Registration semantics

A common periodic lattice and grid shape are necessary but not sufficient to prove that several independent volumetric files share the same real-space origin/frame. The caller therefore supplies a common nonblank `registration_id` to each `ChargeDensitySource` as an explicit assertion that the inputs were generated co-registered.

The registration ID is not an alignment algorithm. CatalysisWorkbench never changes coordinates or grids because two sources share the same ID.

Valid combined/subsystem workflows may use different atomic structures. For example, a combined adsorbate-surface calculation and isolated subsystem densities can contain different atom sets while remaining on the same periodic cell and FFT grid. Block 9 therefore does not incorrectly require exact `AtomicStructure` equality across all sources. Instead, every source structure digest is retained for audit, while lattice/grid/component/unit and the explicit registration assertion are checked separately.

## Component semantics

Subtraction is permitted only like-for-like. `total` electron-number density cannot be mixed with `magnetization_z`, and a missing component fails immediately.

The current CHGCAR adapter supports canonical `total` and, for supported collinear data, `magnetization_z`. Unknown/non-collinear component layouts already fail closed in the adapter. Block 9 does not reconstruct spin channels or convert one component into another.

## No hidden alignment or resampling

Block 9 performs none of the following:

- interpolation;
- resampling;
- grid-size conversion;
- fractional translation;
- origin shifting;
- atom reordering/remapping;
- rigid/Kabsch alignment;
- supercell conversion;
- lattice reduction/rotation/equivalence search;
- density-unit conversion;
- component conversion;
- CHGCAR renormalization.

A mismatch is an error, not an invitation to repair the data silently.

## Detached reporting

`charge_density_difference_frame()` returns a detached one-row-per-source table. The combined row has formula coefficient `+1`; each reference row records both the caller-supplied reference coefficient `c_i` and its signed formula coefficient `-c_i`.

The table also exposes result/source/grid/structure digests, registration/component/unit state, grid shape, cell/voxel volume, source-component integrals, the integrated final difference and the lattice tolerance. Editing the DataFrame cannot mutate retained scientific state.

## Prior-art boundary

Current `pymatgen-core` volumetric arithmetic is useful implementation prior art but is intentionally not adopted as the scientific compatibility contract. Its `VolumetricData.linear_add()` currently warns when structures differ and proceeds after limited data-key checks. CatalysisWorkbench instead validates its frozen co-registration contract before any arithmetic.

`pymatgen-core` remains an MIT-licensed optional backend already present under the reviewed `structure` extra. Block 9 adds no dependency.

## v0.7 boundary

Block 9 stops at numerical difference state and detached reporting. The following remain explicitly v0.7:

- charge-density-difference isosurfaces;
- slices and contour maps;
- ELF/charge-density visualization;
- other advanced volumetric rendering.

No Matplotlib or 3D renderer is imported by the Block 9 computation module.
