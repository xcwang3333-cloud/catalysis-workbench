# Electronic-structure and volumetric result semantics

This document describes the reviewed v0.6 electronic-structure contracts: block 1 source DOS/PDOS and volumetric state plus block 2 explicit DOS/PDOS processing and passive plotting. CatalysisWorkbench is a post-processing library: it parses already generated calculation outputs and converts them immediately into immutable, backend-neutral scientific state. It does not run VASP, Bader, or LOBSTER.

## Dependency and adapter boundary

The optional `structure` extra remains the reviewed backend surface:

```text
catalysis-workbench[structure]
    -> pymatgen-core>=2026.7.16
```

The 2026 `pymatgen` package split places the VASP I/O and electronic-structure classes used here directly in `pymatgen-core`. Block 1 therefore does not add full `pymatgen`, ASE, PyProcar, Sumo, or any second VASP backend. Block 2 adds no dependency.

Backend objects such as `Vasprun`, `Dos`, and `Chgcar` are adapter internals. Public scientific authority is held by CatalysisWorkbench-owned `ElectronicEnergyAxis`, `DOSProjection`, `DOSChannel`, `ElectronicDOS`, `VolumetricGrid`, and derived `DOSTrace` objects.

## Electronic energy reference

`ElectronicEnergyAxis.values_ev` is the exact retained energy grid in eV.

The object records separately:

- `reference_kind`;
- `source_fermi_ev`, when supplied by the producer;
- `applied_shift_ev`.

The first VASP adapter uses `reference_kind="source-native"` and `applied_shift_ev=0`. It does **not** subtract `E_F`.

Block 2 provides the explicit `reference_dos_to_fermi()` transformation. It constructs a new retained axis using `E - E_F`, records `reference_kind="fermi"`, and sets the total applied shift to `-source_fermi_ev`. Applying the same transform to a consistent already-Fermi-referenced trace is idempotent, so the source cannot be shifted twice.

Energy grids must be finite, strictly increasing, and duplicate-free. Source parsing and block-2 processing do not sort or deduplicate values silently.

## Spin semantics

Scientific DOS storage uses physical channels:

- non-spin-polarized `ISPIN=1`: `total`;
- collinear `ISPIN=2`: `up` and `down`.

All scientific DOS density arrays remain non-negative. `plot_dos(..., mirror_spin_down=True)` creates a negative renderer-local copy only for traces whose contributing channels are all physical `down` channels. The retained `DOSTrace.density` is never negated or mutated.

Non-collinear and SOC projection layouts are rejected by the initial `vasprun.xml` adapter instead of being collapsed into misleading `up`/`down` channels.

## Site and orbital projection identity

`DOSProjection` separates stable identity from display labels.

A site/orbital projection retains:

- zero-based site index;
- deterministic `AtomicStructure.site_key`;
- canonical element;
- exact producer orbital label;
- stable projection key.

The attached structure is checked against the projection identity. Block 2 `select_dos_channels()` can filter by stable projection key, projection kind, site index/key, element, orbital, and physical spin while preserving the retained source order. An empty match fails explicitly.

Element/site/orbital aggregation is never triggered merely by labels. `aggregate_dos()` sums only the exact channels supplied by the caller and retains every contributing channel digest, projection key, and spin identity.

## DOS units and normalization

The initial VASP adapter records DOS arrays as `states/eV`.

Normalization basis is explicit:

- total DOS: `cell`;
- site/orbital projected DOS: `site`.

Block-2 aggregation requires matching density units and normalization bases. The minimum block does not convert between cell/site/per-volume/per-atom bases and does not silently max-normalize or area-normalize traces.

## Retained block-2 DOS processing

`DOSTrace` is an immutable derived result rather than a plotting object. It retains:

- the current `ElectronicEnergyAxis` and reference state;
- positive scientific density values;
- source `ElectronicDOS` digest;
- exact contributing source-channel digests, projection keys, and physical spin identities;
- density unit and normalization basis;
- explicit operation history and deterministic scientific digest.

Supported block-2 operations are intentionally narrow:

1. exact retained-channel selection;
2. single-channel trace construction with `dos_channel_trace()`;
3. explicit compatible-channel summation with `aggregate_dos()`;
4. explicit Fermi referencing with `reference_dos_to_fermi()`;
5. inclusive energy-window crop with `crop_dos_trace()`;
6. detached point-wise pandas export with `dos_trace_frame()`.

Cropping is source-grid point selection only. It does not interpolate requested boundaries, and a window retaining fewer than two points fails.

No Gaussian broadening, smoothing, interpolation, resampling, automatic orbital grouping, or normalization transform is performed in block 2.

## Passive DOS plotting

`plot_dos()` consumes only retained `DOSTrace` arrays and the existing `FigureSpec` rendering model. It does not reselect channels, aggregate, shift energies, crop, normalize, broaden, smooth, or interpolate.

Overlay compatibility is fail-closed: all traces on one DOS axes must have matching energy-reference kind, density unit, and normalization basis. These semantics are also copied into shared `Axis.metadata`, so the generic curve-renderer compatibility gate remains active.

An optional Fermi marker is derived from retained state only:

```text
current_axis_EF = source_fermi_ev + applied_shift_ev
```

For a Fermi-referenced trace the marker is therefore 0 eV. For source-native state it remains at the retained source Fermi position. A single marker is rejected when overlaid traces retain different Fermi positions.

## Detached reporting

`dos_trace_frame()` returns an independent one-row-per-point `pandas.DataFrame` containing the retained energy/density values plus trace/source digests, source projection/spin provenance, reference state, unit, normalization basis, and operation history. Editing the DataFrame cannot mutate the immutable `DOSTrace`.

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

Block 1/2 do not perform charge-density subtraction. Multi-file lattice/grid/component compatibility and charge-density-difference arithmetic belong to v0.6 block 9.

## Provenance and immutability

Electronic, DOS-processing, and volumetric arrays are detached from caller-owned memory and made immutable. Scientific-state digests are deterministic and do not depend on descriptive metadata or display labels. Source path/format/backend and optional caller `source_id` remain available through the retained source objects.

## Explicit later-block exclusions

The current electronic-structure implementation does not provide:

- band-center or higher DOS-moment analysis (block 3);
- direct DOSCAR parsing;
- Gaussian broadening, smoothing, interpolation, or resampling;
- automatic chemistry-based projection grouping;
- Bader charge parsing;
- COHP/ICOHP parsing;
- CHE/free-energy thermodynamics;
- charge-density-difference arithmetic;
- PROCAR/fat-band, LOCPOT/work-function, ELF, NEB, or volumetric rendering;
- calculation submission or external executable management.

Those responsibilities remain in their frozen later v0.6/v0.7 blocks.
