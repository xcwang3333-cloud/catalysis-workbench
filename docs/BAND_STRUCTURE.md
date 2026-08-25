# Band-structure state and plotting

This document defines the reviewed v0.7 Block-3 band-structure contract. The release-level architecture remains authoritative in [`V0_7_PLAN.md`](V0_7_PLAN.md).

## Scope

Block 3 adds CatalysisWorkbench-owned ordinary band-structure state, explicit reciprocal-path distance processing, a narrow VASP `vasprun.xml` + line-mode `KPOINTS` adapter, explicit Fermi referencing, and passive Matplotlib plotting.

It does not add projected bands, PROCAR/fat-band processing, automatic symmetry-path generation, band-gap analysis, scissor corrections, noncollinear/SOC interpretation, or another runtime dependency.

## Immutable band state

`BandStructureState` retains one exact ordered reciprocal-space k-point list, one explicit reciprocal Cartesian basis, physical band channels, explicit path segments, source Fermi state, reference semantics, periodic structure provenance, source digest and deterministic result digest.

K-points use retained fractional reciprocal coordinates. Band energies are retained as exact finite `(n_bands, n_kpoints)` arrays in eV. `BandEnergyChannel.band_indices` records the exact zero-based source-array order used by the adapter; no crossing-aware reconnection or sorting is performed.

Physical spin is explicit:

- non-spin-polarized VASP `ISPIN=1` -> `total`;
- collinear `ISPIN=2` -> complete `up` and `down` channels.

A backend container key is not automatically a physical-spin declaration. In particular, current `pymatgen-core` stores a non-spin-polarized band array under backend `Spin.up`; the reviewed adapter maps that source to physical `total` because VASP `ISPIN=1` is authoritative.

## Reciprocal lattice and the `2*pi` convention

The state retains both the reciprocal-lattice Cartesian matrix and the boolean `reciprocal_cartesian_includes_2pi`.

The initial VASP adapter retains current `pymatgen-core`'s documented physics reciprocal-lattice convention, which includes the conventional `2*pi` coefficient, and records `reciprocal_unit="1/angstrom"`.

CatalysisWorkbench never repairs this convention by multiplying or dividing by `2*pi` later. A path step is computed literally as

`delta_k_cartesian = delta_k_fractional @ reciprocal_lattice_cartesian`

and its Euclidean norm is accumulated in the retained reciprocal unit.

This rule also covers non-orthogonal reciprocal cells because the full matrix is used; independent axis-length scaling is not equivalent.

## Explicit path segments

`BandPathSegment` stores inclusive source k-point index bounds and optional endpoint labels. Labels are retained only when supplied by the path definition.

`band_path_coordinates(...)` accumulates distance only inside each retained segment. The start of a later discontinuous segment is placed at the previous accumulated endpoint for compact plotting, but the reciprocal-space jump between those segments is not counted as physical path length.

No line is drawn across a discontinuity. This separation is scientific geometry state, not a plotting heuristic.

## Explicit Fermi referencing

The VASP adapter returns `reference_kind="source-native"` with the source Fermi energy retained and `applied_shift_ev=0`.

`reference_band_structure_to_fermi(...)` is the only Block-3 convenience transformation for Fermi referencing:

`E_fermi_ref = E_source - E_F`.

The returned state retains the same source digest and source Fermi value, records `reference_kind="fermi"`, and records the exact applied shift `-E_F`. Calling the transformation again on an already Fermi-referenced state is idempotent.

The parser and renderer do not shift energies implicitly. Vacuum alignment, potential alignment and scissor corrections are outside Block 3.

## VASP adapter boundary

`read_vasprun_band_structure(...)` lazily uses the existing optional `pymatgen-core` dependency. The minimum accepted source is a standard reciprocal-coordinate line-mode band calculation whose parsed `actual_kpoints` exactly match the supplied line-mode `KPOINTS` endpoint pairs and subdivision count.

The adapter reads the source eigenvalue energy column literally and does not use occupations to infer metallicity, band edges, gaps, or band connectivity.

The line-mode source is reconciled fail-closed:

- `KPOINTS` must be line mode;
- coordinate mode must be reciprocal;
- subdivision count must be at least two;
- endpoint records must occur in explicit pairs;
- expected actual k-point count is `number_of_segments * subdivisions`;
- every actual point in every segment must match the literal endpoint interpolation within the narrow parser tolerance retained in metadata.

Hybrid or uniform-grid-plus-line layouts that require automatic source slicing/reordering are rejected by the minimum Block-3 adapter rather than guessed.

`LSORBIT` and `LNONCOLLINEAR` sources fail closed in Block 3. A later extension must introduce a reviewed spinor/vector contract instead of collapsing those states into misleading `up/down` channels.

Projected eigenvalues are not parsed in Block 3. PROCAR/projected-band state belongs to Block 4.

## Passive plotting

`plot_band_structure(...)` consumes an existing `BandStructureState` and its derived `BandPathCoordinates`.

Each retained band, physical spin and path segment is drawn as a separate line. Consequently, discontinuous segments are never connected. High-symmetry tick labels come only from retained source labels; two different supplied labels at the same compact visual boundary may be shown deterministically as `label1 | label2`.

The y-axis uses the state's current explicit reference:

- source-native state -> literal source energies;
- Fermi-referenced state -> retained `E - E_F` energies.

An optional Fermi marker is placed at the retained source Fermi value for source-native state or at zero for explicitly Fermi-referenced state. Plotting never triggers a reference transformation.

`FigureSpec` controls ordinary publication presentation. Rendering does not mutate k-points, band energies, band order, path segments or source state.

## Prior art and dependencies

Current `pymatgen-core` is MIT and remains the existing lazy optional low-level VASP parser backend. Its current reciprocal-lattice and band-container behavior is integration-tested rather than exposed as public authority.

Sumo is MIT and is used only as a reference for publication band-plot/branch UX. No Sumo implementation is copied or adapted and Sumo is not a runtime dependency.

Block 3 adds no runtime dependency.

## Deferred to later blocks

- Block 4: PROCAR projection state, explicit site/orbital aggregation and fat-band plotting.
- Block 5: LOCPOT planar potential and work-function processing.
- Block 6: NEB retained image-energy/barrier state and plotting.
- Block 7: advanced volumetric three-dimensional rendering/export.

Automatic symmetry-path generation, band-gap/direct-gap/metallicity inference, VASP execution and HPC workflow management remain outside this Block.
