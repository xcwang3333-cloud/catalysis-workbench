# Atomic structures and structure-file adapters

The v0.5 structure foundation separates authoritative scientific state from third-party parsing. `AtomicStructure` is owned by CatalysisWorkbench; `pymatgen-core` is an optional, lazy file-I/O backend only.

## Installation boundary

The base package does not require pymatgen:

```bash
pip install catalysis-workbench
```

Install the optional structure backend only when POSCAR / CONTCAR / CIF / XYZ parsing is required:

```bash
pip install "catalysis-workbench[structure]"
```

The reviewed backend is `pymatgen-core>=2026.7.16` (MIT, Python >=3.11). It was selected instead of hand-written crystallographic/VASP parsers because it provides mature structure and periodic-boundary I/O. CatalysisWorkbench does not expose a pymatgen `Structure` or `Molecule` as authoritative public state.

## `AtomicStructure`

`catalysis_workbench.computation.AtomicStructure` retains ordered site state:

- `species`: full per-site species strings, in source order;
- `elements`: canonical per-site element symbols;
- `cartesian_coordinates`: immutable `N x 3` float array in angstrom;
- `lattice_angstrom`: optional immutable `3 x 3` lattice matrix, with row vectors `a`, `b`, `c`, in angstrom;
- `pbc`: explicit `(a, b, c)` periodic-boundary flags;
- `site_keys`: unique stable keys, generated from source order when omitted;
- `site_labels`: optional ordered site labels;
- `metadata`: deeply frozen source/provenance metadata;
- `digest`: deterministic SHA-256 identity of retained scientific/ordered identity state.

The digest includes ordered species, element symbols, coordinates, lattice/no-lattice state, PBC flags, site keys, and site labels. It intentionally excludes `metadata`, so moving an identical file or changing a source-path annotation does not change scientific identity.

### Validation

Construction fails explicitly when:

- no sites are present;
- coordinate/lattice values are complex or non-finite;
- coordinates are not `N x 3`;
- a lattice is not `3 x 3` or is singular;
- any periodic axis is enabled without a lattice;
- species/elements/keys/labels do not match site count;
- site keys are blank or duplicated;
- PBC flags are not actual booleans.

Source arrays and nested metadata are detached before retention. Returned scientific arrays are read-only. `metadata_dict()` returns a detached mutable copy.

## File adapters

The lazy adapters live in `catalysis_workbench.io`:

```python
from catalysis_workbench.io import (
    read_cif_structure,
    read_contcar,
    read_poscar,
    read_xyz_structure,
)

structure = read_poscar("POSCAR", source_id="relaxed-slab")
```

### POSCAR and CONTCAR

`read_poscar()` and `read_contcar()` use `pymatgen.io.vasp.inputs.Poscar.from_file()` with POTCAR lookup disabled. Parsed coordinates and lattice are converted immediately to `AtomicStructure`; the result is fully periodic `(True, True, True)`. Site order is not sorted by CatalysisWorkbench.

### CIF

`read_cif_structure()` uses `CifParser.parse_structures(primitive=False)`. CatalysisWorkbench does not request primitive/conventional-cell conversion.

A CIF yielding more than one structure is ambiguous and fails unless `index=` is supplied explicitly:

```python
second = read_cif_structure("multi.cif", index=1)
```

Disordered / partial-occupancy structures are rejected in this first block instead of being collapsed into an arbitrary ordered species.

### XYZ

`read_xyz_structure()` converts one XYZ frame to explicitly non-periodic state `(False, False, False)` and does not fabricate a lattice. A multi-frame XYZ requires explicit `index=` unless only one frame exists.

## Species and labels

For ordered pymatgen sites, the adapter retains:

- full `str(site.specie)` as the species identity;
- the corresponding canonical element symbol separately;
- the parser-provided site label when present.

This prevents oxidation-decorated species strings from being confused with bare elements while keeping the element identity available for later geometry/visualization work.

## Provenance

Adapter metadata records:

- `structure_format`;
- `structure_backend = "pymatgen-core"`;
- `source_path`;
- optional caller-supplied `source_id`.

These provenance fields are not part of the scientific digest.

## Explicit non-actions

This layer does not infer bonds, neighbors, coordination numbers, site mappings, symmetry-standardized cells, primitive/conventional cells, or visualization state. Those are later v0.5 blocks with separate reviewed contracts.
