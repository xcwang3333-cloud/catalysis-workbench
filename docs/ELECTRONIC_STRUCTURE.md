# Electronic-structure and volumetric result semantics

This document describes the reviewed v0.6 block-1 contracts for source electronic DOS/PDOS state and VASP volumetric charge-density input. CatalysisWorkbench is a post-processing library: it parses already generated calculation outputs and converts them immediately into immutable, backend-neutral scientific state. It does not run VASP, Bader, or LOBSTER.

## Dependency and adapter boundary

The optional `structure` extra remains the reviewed backend surface:

```text
catalysis-workbench[structure]
    -> pymatgen-core>=2026.7.16
```

The 2026 `pymatgen` package split places the VASP I/O and electronic-structure classes used here directly in `pymatgen-core`. Block 1 therefore does not add full `pymatgen`, ASE, PyProcar, Sumo, or any second VASP backend.

Backend objects such as `Vasprun`, `Dos`, and `Chgcar` are adapter internals. Public scientific authority is held by CatalysisWorkbench-owned `ElectronicEnergyAxis`, `DOSProjection`, `DOSChannel`, `ElectronicDOS`, and `VolumetricGrid` objects.

## Electronic energy reference

`ElectronicEnergyAxis.values_ev` is the exact retained source grid in eV.

The object records separately:

- `reference_kind`;
- `source_fermi_ev`, when supplied by the producer;
- `applied_shift_ev`.

The first VASP adapter uses `reference_kind="source-native"` and `applied_shift_ev=0`. It does **not** subtract `E_F`. An `E-E_F` transformation belongs to later explicit DOS processing, so a parsed source cannot be Fermi-shifted twice.

Energy grids must be finite, strictly increasing, and duplicate-free. The adapter does not sort or deduplicate source values silently.

## Spin semantics

Scientific DOS storage uses physical channels:

- non-spin-polarized `ISPIN=1`: `total`;
- collinear `ISPIN=2`: `up` and `down`.

All DOS density arrays remain non-negative source quantities. Plotting spin-down below zero is a display convention only and is not permitted in block-1 scientific state.

Non-collinear and SOC projection layouts are rejected by the initial `vasprun.xml` adapter instead of being collapsed into misleading `up`/`down` channels.

## Site and orbital projection identity

`DOSProjection` separates stable identity from display labels.

A site/orbital projection retains:

- zero-based site index;
- deterministic `AtomicStructure.site_key`;
- canonical element;
- exact producer orbital label;
- stable projection key.

The attached structure is checked against the projection identity. Element/site/orbital aggregation is not performed in block 1; later DOS processing must request aggregation explicitly.

## DOS units and normalization

The initial VASP adapter records DOS arrays as `states/eV`.

Normalization basis is explicit:

- total DOS: `cell`;
- site/orbital projected DOS: `site`.

The library does not silently max-normalize, area-normalize, broaden, smooth, interpolate, or resample these source arrays.

## CHGCAR physical convention

`pymatgen-core`'s legacy text `Chgcar` parser retains the numerical volumetric grid read from the VASP file. For the standard CHGCAR convention, the file grid is the electron-number density multiplied by the real-space cell volume.

For cell volume `V_cell` in Å³:

```text
n(r) = chgcar_grid(r) / V_cell
```

CatalysisWorkbench therefore divides the `pymatgen-core` parsed component by `V_cell` **once** and stores the result in `1/angstrom^3`.

For a grid with `N_grid = nx * ny * nz` points:

```text
voxel_volume = V_cell / N_grid
integral[n(r)] = sum(chgcar_grid) / N_grid
```

The installed-wheel optional-backend smoke includes a hand-verifiable CHGCAR fixture to protect this normalization from backend drift or accidental double normalization.

The current VASP Wiki page contains wording around the FFT-grid factor that is not internally consistent with its own electron-count summation equation. The block-1 implementation follows the VASP-developer forum clarification and, critically, verifies the actual `pymatgen-core` parser behavior in regression tests rather than relying on prose alone.

## Volumetric component semantics

The initial CHGCAR adapter supports:

- `total` electron-number density;
- collinear `diff` converted to the explicit `magnetization_z` component.

Every retained component has the same lattice, grid shape, unit, and structure identity. Unknown/non-collinear component layouts fail closed.

`VolumetricGrid.component_integrals` are direct numerical diagnostics of the retained components. The positive total electron-number density is not described as a signed Coulomb charge density.

Block 1 does not perform charge-density subtraction. Multi-file lattice/grid/component compatibility and charge-density-difference arithmetic belong to v0.6 block 9.

## Provenance and immutability

Electronic and volumetric arrays are detached from caller-owned memory and made immutable. Scientific-state digests are deterministic and do not depend on descriptive metadata. Source path/format/backend and optional caller `source_id` remain available as detached metadata.

## Explicit block-1 exclusions

Block 1 does not provide:

- DOS/PDOS selection, aggregation, Fermi referencing, broadening, or plotting;
- band-center analysis;
- Bader charge parsing;
- COHP/ICOHP parsing;
- CHE/free-energy thermodynamics;
- charge-density-difference arithmetic;
- PROCAR/fat-band, LOCPOT/work-function, ELF, NEB, or volumetric rendering;
- calculation submission or external executable management.

Those responsibilities remain in their frozen later v0.6/v0.7 blocks.
