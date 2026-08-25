# LOCPOT planar potential and work function

This document records the reviewed v0.7 Block-5 contract for VASP LOCPOT post-processing in CatalysisWorkbench.

## Scope

Block 5 provides four deliberately separate operations:

1. parse one LOCPOT scalar potential grid into the existing immutable `ScalarField` foundation;
2. compute an exact source-grid planar average along one caller-selected lattice/grid axis;
3. compute a vacuum level from one explicit caller-selected profile window;
4. calculate a work function from that retained vacuum level and an explicitly compatible Fermi source.

Passive Matplotlib plotting consumes retained state only. It does not perform scientific analysis.

## LOCPOT scalar potential semantics

`read_locpot_field(...)` lazy-imports the existing optional `pymatgen-core` backend and returns a CatalysisWorkbench-owned `ScalarField` with:

- `field_kind="local-potential"`;
- `value_unit="eV"`;
- the exact parsed periodic `AtomicStructure` and lattice;
- the exact finite source 3-D potential array;
- source/backend provenance and deterministic source/scientific digests;
- optional caller-visible `calculation_id` retained in metadata.

The LOCPOT values are preserved literally after parser conversion. CatalysisWorkbench does **not** divide them by cell volume. The CHGCAR electron-number-density conversion used in v0.6 is not applicable to LOCPOT.

The minimum adapter requires one unambiguous scalar potential component. Multiple backend components fail closed instead of being summed or selected heuristically.

No unit conversion, normalization, interpolation, resampling, smoothing, clipping, potential-zero shift, dipole correction or alignment is performed.

## Exact planar average

`planar_average_potential(field, axis=...)` requires a retained local-potential/eV `ScalarField` and one explicit source axis `0`, `1` or `2`.

For an axis `k`, the retained potential profile is the arithmetic mean of the exact source-grid values over the other two array axes. There is no interpolation, endpoint insertion or macroscopic convolution.

The profile retains:

- source field and structure digests;
- optional calculation identity;
- exact source grid shape;
- selected axis;
- fractional source coordinates `i / n_k`;
- physical normal coordinates in angstrom;
- planar potential values in eV;
- physical normal repeat height;
- deterministic digest.

### Skew-cell geometry

The physical distance associated with one full fractional repeat along the selected lattice coordinate is the perpendicular height between opposite lattice faces, not generally the norm of the corresponding lattice vector.

For selected axis `k`:

```text
A_face = |a_i x a_j|
h = V_cell / A_face
z_i = (i / n_k) h
```

where `i` and `j` are the two other lattice-vector indices.

This is essential for skew cells. A convenience axis grid based only on `|a_k|` is not used for physical normal coordinates.

## Explicit vacuum window

`vacuum_level_from_profile(...)` requires an explicit half-open source-index interval:

```text
[start_index, stop_index)
```

The initial reviewed statistic is exactly `mean`. The result retains the selected source indices, fractional and physical normal-coordinate bounds, source profile/field identity, optional side identity, optional calculation identity and the resulting vacuum level in eV.

CatalysisWorkbench does not automatically detect:

- a vacuum plateau;
- a surface side;
- a dipole region;
- a flatness threshold;
- a macroscopic potential region.

No smoothing, fitting, interpolation or outlier rejection occurs inside vacuum selection.

## Explicit Fermi source

`FermiLevelSource` carries a finite Fermi energy in eV, exact source provenance and a mandatory caller-visible `calculation_id`.

`fermi_source_from_band_structure(...)` is a narrow convenience for the reviewed v0.7 Block-3 `BandStructureState`. It uses the retained `source_fermi_ev` even when the band state has already been explicitly transformed to an `E - E_F` plotting reference. It never infers Fermi energy from band edges, occupations, DOS or plotted zero.

## Work-function arithmetic

`calculate_work_function(...)` implements only:

```text
Phi = V_vacuum - E_F
```

The vacuum result and Fermi source must carry the same nonblank `calculation_id`. Unrelated calculations fail closed.

The immutable `WorkFunctionResult` retains separately:

- `vacuum_ev`;
- `fermi_ev`;
- `work_function_ev`;
- vacuum-result/profile/field source identities;
- Fermi-source identity;
- calculation identity;
- optional side identity;
- deterministic digest.

A negative numerical result is retained as-is. CatalysisWorkbench does not clip or repair it.

There is no hidden potential alignment, electrostatic-zero correction, dipole correction, vacuum inference, Fermi inference or unit conversion.

## Passive plotting

`plot_planar_potential(...)` renders:

- retained physical normal coordinate in angstrom;
- retained planar potential in eV;
- an optional already-computed vacuum window/level;
- an optional retained Fermi level;
- an optional already-computed work-function annotation.

The renderer verifies overlay provenance where relevant and never recomputes planar averages, vacuum statistics, Fermi state or work-function arithmetic. Plot styling is presentation-only.

## Current backend boundary

The existing optional dependency remains:

```text
pymatgen-core>=2026.7.16
```

Current `pymatgen-core` exposes `Locpot` through `pymatgen.io.vasp.outputs` and reads LOCPOT through `Locpot.from_file(...)`. CatalysisWorkbench uses it only as a lazy parser backend; third-party `Locpot` objects are never public authority.

Current common volumetric convenience geometry includes an axis-grid helper based on lattice-vector lengths. Block 5 intentionally does not use that shortcut for skew-cell physical normal coordinates; the full-lattice `V/A_face` construction is independently retained and regression-tested.

No new runtime dependency is introduced.

## Explicitly out of scope

Block 5 does not provide:

- automatic vacuum plateau or surface-side detection;
- macroscopic averaging, convolution or smoothing;
- automatic slab-normal inference from atomic positions;
- potential alignment across unrelated calculations;
- dipole-potential correction;
- Poisson/electrostatic reconstruction;
- Fermi inference from occupations, band edges or DOS;
- NEB/barrier analysis;
- advanced 3-D volumetric rendering;
- VASP/HPC execution or workflow management.
