# CatalysisWorkbench v0.7 Plan

v0.7 is the advanced computational-visualization release. This document freezes the architecture, scientific semantics, dependency boundaries, implementation order, visualization contracts, testing strategy, and v0.8 handoff before any v0.7 scientific implementation begins. GitHub remains the operational source of truth.

## Baseline and release state

- Architecture checkpoint Issue: #197.
- Exact architecture base: `main` at `fcc8c0ce73953c8d7468a58dcb0c172e520c4202`.
- Released v0.6 tag: `v0.6.0 -> c7793b309f41d174c14534bd6d4acdacc2a57636`.
- Distribution/runtime version is `0.6.0` and does not change in the architecture checkpoint.
- The public GitHub Release `CatalysisWorkbench v0.6.0` is complete.
- PyPI/package-registry publication remains explicitly deferred and must not be resumed without a separate future authorization.
- Immediately before Issue #197 was created, open Issues and open PRs were both zero.
- No v0.7 implementation may move or recreate `v0.6.0` or any earlier release tag.

## Existing v0.6 computation and visualization baseline

v0.7 extends reviewed state rather than replacing it.

The relevant v0.6 baseline already provides:

1. immutable `AtomicStructure` and renderer-neutral static `StructureScene` state;
2. immutable `ElectronicDOS` / `ElectronicEnergyAxis` state and explicit DOS/PDOS processing;
3. immutable electron-number-density `VolumetricGrid` state with exact lattice/grid/structure provenance and canonical `1/angstrom^3` density semantics;
4. lazy optional `pymatgen-core` VASP adapters for reviewed DOS/PDOS and CHGCAR state;
5. strict `ChargeDensityDifferenceResult` arithmetic on explicitly co-registered `VolumetricGrid` sources;
6. publication-oriented `FigureSpec`, `PlotStyle`, shared Matplotlib rendering helpers, and exact-size export;
7. explicit free-energy diagram state/rendering without transition-state or NEB semantics.

The v0.6 `VolumetricGrid` is deliberately narrow: it is an electron-number-density container and currently requires `density_unit == "1/angstrom^3"`. ELF is dimensionless and LOCPOT is a potential field, so v0.7 must not weaken or silently generalize the released `VolumetricGrid` contract merely to carry unrelated scalar quantities.

## Architecture principles

The project-wide separation remains parser/backend -> CatalysisWorkbench immutable state -> explicit processing -> passive rendering.

Additional v0.7 rules are frozen as follows:

1. v0.6 scientific results remain authoritative. Visualization never re-runs charge-density-difference arithmetic, DOS aggregation, CHE, geometry matching, or another prior scientific operation.
2. Add a separate backend-neutral scalar-field contract for unit-bearing three-dimensional scalar quantities rather than repurposing the density-only `VolumetricGrid`.
3. Preserve exact source values, lattice, grid shape, structure identity, field kind, physical unit, registration/provenance, and deterministic digests.
4. Cross-field overlays fail closed unless lattice/grid/registration semantics are explicitly compatible. No hidden alignment, origin shift, resampling, interpolation to a new scalar grid, supercell conversion, or unit conversion is permitted.
5. Rendering parameters such as colors, opacity, camera, lighting, line width, fat-band display scale, positive/negative color convention, and scalar-bar style are presentation state, never scientific state.
6. Scientific processing and I/O modules remain visualization-backend-lazy. Optional PyVista/VTK or mesh-extraction libraries, if later approved, are imported only in the concrete rendering path.
7. Third-party parser, mesh, and renderer objects never become the public scientific authority.
8. Any implementation-time backend dependency is added only after exact-version behavior, license, wheel availability, Python support, headless CI behavior, and installed-wheel API boundaries are revalidated in that block.
9. Existing v0.1-v0.6 public APIs remain compatible unless a breaking change is separately planned and reviewed.
10. VASP/HPC job execution and complete simulation workflow management remain outside the project scope.

## Frozen v0.7 scope and dependency order

v0.7 contains seven implementation blocks after this architecture checkpoint:

1. shared scalar-field state plus renderer-neutral volumetric scene/slice/isosurface specifications;
2. charge-density-difference, electron-density, and ELF visualization;
3. band-structure state/adapters plus passive band plotting;
4. PROCAR projection processing plus fat-band plotting;
5. LOCPOT planar-potential/work-function processing plus plotting;
6. NEB/barrier retained state plus passive plotting;
7. advanced volumetric three-dimensional backend/rendering/export.

After the seven scientific/visualization blocks, synchronize completion state and follow the normal Gate A/B/C release sequence.

The order is intentional. Scalar-field unit/registration/scene semantics precede all volumetric consumers. Ordinary band-state/reference/path semantics precede projected/fat-band state. Advanced renderer integration comes last so the scientific state and passive minimum renderers do not depend on a heavy graphics backend.

## Block 1 — shared scalar-field and volumetric-scene foundation

### Scalar-field state

Introduce a CatalysisWorkbench-owned immutable three-dimensional scalar-field concept. Exact public names may narrow during implementation review, but the retained scientific contract must include:

- one fully periodic `AtomicStructure` with explicit lattice;
- one finite three-dimensional scalar array;
- exact grid shape;
- stable `field_kind` separate from display labels;
- explicit physical `value_unit` such as `1/angstrom^3`, `eV`, or a documented dimensionless unit token;
- exact source/result digest and source provenance;
- explicit registration/frame identity when cross-field overlay or comparison is intended;
- cell volume and voxel/grid diagnostics where physically meaningful;
- immutable retained arrays and detached reporting metadata.

A scalar-field object represents one physical field. Multiple components or multiple physical quantities are represented as distinct field objects/layers rather than being hidden behind ambiguous component names.

Adapters from existing v0.6 state are explicit:

- `VolumetricGrid` component -> scalar field while retaining the exact source grid/component/digest and canonical density unit;
- `ChargeDensityDifferenceResult.difference_grid` -> signed difference scalar field while retaining result/source digests and registration identity.

No adapter may renormalize, smooth, align, interpolate, or copy a field into a different lattice/grid convention.

### Discrete slices

The minimum scientific slice operation selects retained source-grid planes explicitly. It may use an exact grid index and named lattice/grid axis. Returned slice state retains:

- source field digest;
- selected axis and exact grid index;
- source-grid coordinate/fractional position;
- exact two-dimensional source values and unit;
- axis/lattice provenance needed to label physical coordinates.

No hidden trilinear interpolation or arbitrary-plane resampling occurs in the minimum slice operation. Arbitrary resampled planes, if ever added, require a separate explicit processing contract.

For a skew periodic cell, slice and mesh geometry must use the full lattice matrix. Grid-index positions are interpreted in fractional cell coordinates and then transformed to Cartesian coordinates by the retained lattice; implementations must not approximate a general cell by multiplying grid fractions by three independent lattice-vector norms.

### Isosurface specification

An isosurface request retains an explicit physical threshold in the source field unit. A signed field may expose multiple independently specified layers, for example positive and negative charge-density-difference thresholds.

Mesh extraction inherently estimates geometric surface positions between sampled voxels. That interpolation is renderer/mesh geometry only: it does not create, store, or replace a new scientific scalar grid and must not mutate source values. The threshold and extraction provenance remain visible.

Mesh vertices returned in array/grid coordinates must be converted through fractional coordinates and the full retained lattice matrix before Cartesian rendering. Axis-length-only `spacing` is not scientifically sufficient for a non-orthogonal cell. Automatic periodic wrapping, seam welding, or supercell replication is not performed; any displayed periodic image copies are explicit presentation transforms.

### Renderer-neutral scene

Introduce renderer-neutral volumetric scene/layer specifications that can combine:

- one or more scalar-field slice/isosurface layers;
- existing structure/atom/cell presentation state;
- explicit camera/orientation state;
- scalar-bar/legend labels derived from retained field semantics;
- presentation-only colors, opacity, lighting, clipping visibility, and layer ordering.

The scene contract contains no PyVista, VTK, scikit-image, Plotly, or Matplotlib collection object.

## Block 2 — charge-density-difference, charge-density, and ELF visualization

### Charge-density difference

Visualization consumes the reviewed v0.6 `ChargeDensityDifferenceResult`; it never recalculates

`Delta n(r) = n_combined(r) - sum_i c_i n_reference_i(r)`.

Required behavior:

- signed `difference` values are retained literally in `1/angstrom^3`;
- positive and negative isosurfaces are separate explicit layers;
- a convenience symmetric threshold may accept one caller-supplied positive magnitude and construct `+magnitude` / `-magnitude` display layers, but no magnitude is inferred from data extrema, percentiles, or chemistry heuristics;
- slices retain exact source-grid values;
- source `registration_id`, grid/lattice provenance and result digest remain auditable;
- no display operation changes integrated-difference diagnostics or scientific state.

### Electron density

Electron-density visualization consumes reviewed `VolumetricGrid` density state. The canonical unit remains `1/angstrom^3`. No max normalization, logarithmic transform, clipping, smoothing, or contrast transform is silently applied to scientific data. Such display mappings, if offered, are explicitly presentation-only.

### ELF

ELF is represented as a distinct dimensionless scalar field. The initial VASP adapter should consume already-generated ELF output through a reviewed permissive parser path where available, then immediately convert to CatalysisWorkbench state.

Rules:

- preserve source values exactly after parser conversion;
- do not force ELF into `VolumetricGrid` or label it as electron density;
- do not clip or renormalize values to `[0, 1]` merely for plotting;
- adapter-level physical-range validation may fail closed on clearly invalid producer state but must never repair data silently;
- retain source structure/lattice/grid/provenance and explicit dimensionless unit semantics.

## Block 3 — band-structure state, adapters, and passive plotting

Introduce backend-neutral immutable band-structure state with at least:

- exact ordered k points in source reciprocal coordinates;
- explicit reciprocal-lattice matrix, reciprocal-coordinate convention, and whether the Cartesian reciprocal basis includes the conventional `2*pi` factor;
- explicit path segment boundaries and high-symmetry labels only when supplied by the source/path definition;
- band energies in eV with physical spin identity;
- exact band index/order as supplied;
- source Fermi level and explicit energy-reference state;
- structure/reciprocal-lattice provenance;
- source/result digests and metadata needed to reconstruct the plotted path.

The minimum VASP adapter may use reviewed `pymatgen-core` I/O where its exact installed surface supports the required `vasprun.xml`/KPOINTS band data. Backend objects are converted immediately.

Scientific rules:

- no automatic symmetry-path generation;
- no hidden k-point interpolation;
- no automatic band sorting/reconnection across crossings;
- no scissor correction;
- no hidden Fermi shift;
- no automatic band-gap/direct-gap/metallicity inference in the minimum visualization block;
- path distance, when used for plotting, is derived only from retained k points, the explicitly retained reciprocal-lattice convention, and explicit segment boundaries;
- plotted reciprocal path distance has an explicit physical unit, normally `1/angstrom` for a Cartesian reciprocal basis, and implementations must not introduce or omit a `2*pi` factor silently;
- discontinuous path segments are not joined as if physically continuous.

Passive plotting consumes retained band energies/reference/path state only. Fermi-referenced plotting requires an explicit retained transformation analogous to the v0.6 DOS reference rules.

## Block 4 — PROCAR projected bands and fat-band plotting

PROCAR projection state extends one exact compatible band source rather than creating an unrelated energy/path authority.

Retain explicitly:

- exact source band/k-point identity;
- physical spin identity;
- site index/key and element identity when structure-coupled;
- orbital identity exactly as supplied by the producer/backend;
- non-negative finite projection weights with explicit source semantics;
- source projection digest and compatible band-source digest;
- any producer normalization/completeness diagnostics that can be retained without inference.

Projection selection and aggregation are explicit operations. No element/orbital/site grouping is inferred from display labels. No normalization to a maximum or to 100% is silently applied.

Fat-band line width, marker radius, marker area, alpha, and any display multiplier are presentation-only, caller-visible scale parameters. They never replace the retained projection weight.

Initial non-collinear/SOC PROCAR layouts may fail closed if the source semantics cannot be represented without ambiguity. Support may be expanded only through a separately reviewed contract rather than collapsing vector/spinor state into misleading `up`/`down` channels.

`romerogroup/pyprocar` is GPLv3 and remains behavior/UX reference-only; there is no copied/adapted GPL implementation or runtime dependency.

## Block 5 — LOCPOT, planar potential, and work function

### Local-potential field

LOCPOT is a scalar potential field, not electron density. The VASP adapter must retain:

- exact structure/lattice/grid;
- finite source potential values;
- explicit potential-energy unit verified against the concrete parser/backend fixture;
- source/calculation identity and digest;
- source-native reference semantics.

Do not put LOCPOT into the density-only `VolumetricGrid` merely to reuse storage.

### Planar averaging

Planar averaging is an explicit computation along one caller-selected lattice/grid axis. It averages retained source-grid values across the two in-plane grid indices without interpolation.

For a possibly skew periodic cell, the physical normal height associated with a selected lattice axis is

`h = V_cell / A_opposite_face`,

not blindly the norm of that lattice vector. The one-dimensional coordinate and averaging-axis convention are retained in the result.

### Vacuum region and work function

Vacuum selection is caller-visible. The minimum API uses an explicit grid-index/fractional window or other explicit retained region selection and computes its stated statistic from source points. It does not automatically detect a vacuum plateau, surface side, or dipole-corrected region.

Work-function arithmetic is

`Phi = V_vacuum - E_F`

in eV for compatible source semantics. The result retains:

- exact planar-potential/vacuum-region source digest;
- exact Fermi value/source digest;
- common caller-visible calculation/compatibility identity;
- selected side/region identity when multiple vacuum regions are evaluated;
- `V_vacuum`, `E_F`, and `Phi` separately.

Unrelated calculations fail rather than being silently mixed. No hidden potential alignment, dipole correction, macroscopic smoothing, vacuum-level heuristic, or electrostatic zero shift is applied.

## Block 6 — NEB image-energy and barrier plotting

v0.7 adds post-processing of already-generated image energies; it does not become an NEB optimizer.

The immutable NEB/path state retains:

- exact caller/source image order;
- stable image keys;
- image energies in eV and source digests;
- optional attached structures/provenance;
- explicit reaction-coordinate mode;
- explicit energy-reference image when relative energies are constructed;
- deterministic path/result digest.

The minimum reaction coordinate is either image ordinal/index or explicit caller-supplied finite coordinates. CatalysisWorkbench does not infer a geometric reaction coordinate through hidden atom matching, atom reordering, minimum-image remapping, Kabsch alignment, IDPP, or structure fitting.

Barrier arithmetic uses an explicitly selected saddle/image key. For initial, saddle, and final image energies:

- forward discrete-image barrier = `E_saddle - E_initial`;
- reverse discrete-image barrier = `E_saddle - E_final`.

The result is explicitly a discrete retained-image barrier unless an external producer has supplied stronger transition-state semantics. No spline maximum or continuous transition state is invented.

Passive plotting renders retained image coordinates/energies and optional explicitly retained saddle designation with straight point-to-point connections. No spline, smoothing, interpolation, or fitting is hidden in the renderer.

Running VASP/VTST, generating NEB images, spring/tangent algorithms, climbing-image optimization, convergence control, force analysis, scheduler submission, and HPC orchestration are out of scope.

## Block 7 — advanced volumetric three-dimensional rendering

Block 7 upgrades the rendering backend only after the scalar-field and scene contracts are stable.

Requirements:

- the public input remains the renderer-neutral CatalysisWorkbench volumetric scene;
- backend objects do not leak into computation or public scientific results;
- optional heavy graphics imports remain lazy;
- headless rendering in CI and fresh installed wheels must be validated before dependency merge;
- camera, lighting, opacity transfer, clipping visibility, background, scalar bar and screenshot/export settings are explicit presentation state;
- multi-field layers require compatible retained lattice/grid/registration semantics unless they are intentionally displayed as independent scenes;
- no backend filter may silently overwrite retained scientific arrays.

The initial advanced backend may support publication-oriented static images first. Interactive browser/GUI editing remains a later v0.9-v1.0 workflow and is not an acceptance requirement for v0.7.

## Prior art, licenses, and dependency decisions

### pymatgen-core / pymatgen

The repository already has optional `pymatgen-core>=2026.7.16` support and v0.6 project evidence verifies VASP I/O including `Vasprun`, `Chgcar`, and `Procar` among the available parser surface.

v0.7 decision:

- continue preferring the existing optional permissive `pymatgen-core` backend for low-level VASP I/O where the concrete class is available and fixture-verified;
- keep the dependency optional rather than moving it into the base wheel;
- do not expose backend classes as public results;
- verify ELFCAR/LOCPOT/band/PROCAR behavior in the exact implementation block instead of assuming semantics from class names;
- full `pymatgen` is MIT and adds higher-level analyses such as `NEBAnalysis`; it is reference-only initially and is not added merely for convenience if explicit CatalysisWorkbench state plus core I/O is sufficient.

### Sumo

`SMTG-Bham/sumo` is MIT licensed and remains a strong reference for publication band-structure layout, symmetry labels, projected-band organization, and plotting ergonomics.

Decision: reference-only. CatalysisWorkbench already owns its publication specification/rendering stack and needs stricter retained-state semantics.

### PyProcar

`romerogroup/pyprocar` is GPLv3 and is a mature PROCAR/fat-band reference.

Decision: behavior/UX/test reference only. No runtime dependency, code copy, or adapted GPL implementation.

### PyVista / VTK

Current PyVista declares the MIT license and provides a NumPy-oriented VTK-backed 3D visualization/mesh API. It is the leading optional advanced-renderer candidate because it directly supports surfaces, volumes, cameras, scalar bars, clipping, screenshots, and headless scientific rendering patterns.

Decision: candidate only in the architecture checkpoint. PyVista pulls VTK, so the concrete Block-7 Issue must verify Python 3.11+ wheels, install size, platform support, headless CI behavior, export behavior, lazy import boundaries, and compatibility with the base package before adding any optional dependency. PyVista/VTK objects never become public scientific state.

### scikit-image

Current scikit-image is BSD-3-Clause and provides mature marching-cubes mesh extraction.

Decision: alternative candidate for a lighter explicit mesh-extraction path feeding the existing static renderer. Do not add it in the architecture checkpoint. The concrete volumetric rendering block chooses the narrowest backend that satisfies quality, packaging, headless, and maintenance requirements.

### Full pymatgen NEB analysis

Current full pymatgen is MIT and includes higher-level transition-state/NEB analysis. It is useful scientific and regression reference.

Decision: do not add the full analysis package merely to obtain automatic spline/barrier/path behavior. CatalysisWorkbench v0.7 intentionally retains explicit discrete image energies and caller-visible barrier semantics.

### VASP, VTST, VASPKIT, and VESTA

These remain external producers, workflow tools, or visualization references. CatalysisWorkbench does not bundle, launch, automate, or copy their implementations in v0.7.

## Compatibility and failure rules

The following are hard boundaries across v0.7:

- no weakening of released `VolumetricGrid` density-unit semantics;
- no second charge-density-difference arithmetic implementation;
- no hidden field normalization, clipping, smoothing, interpolation to a new scientific grid, resampling, alignment, atom remapping, lattice reduction, or supercell conversion;
- no axis-length-only approximation of skew-cell scalar-field/slice/isosurface geometry;
- no hidden reciprocal-lattice or `2*pi` convention change in band-path coordinates;
- no hidden k-path generation, band reconnection, projection grouping, Fermi shift, or fat-band normalization;
- no hidden LOCPOT vacuum detection, dipole correction, potential alignment, or cross-calculation mixing;
- no hidden NEB spline, saddle inference, atom correspondence, or path optimization;
- unsupported non-collinear/SOC/projection layouts fail closed rather than being mislabeled;
- display transformations operate on renderer-local copies and cannot mutate immutable scientific state.

## Testing strategy

Each implementation block must add hand-verifiable scientific fixtures and failure-mode regressions before broader visual tests.

Minimum release-wide coverage includes:

1. scalar-field unit/kind/grid/lattice/registration validation, immutability, digest stability, and exact adapters from v0.6 density/difference state;
2. discrete slice fixtures proving exact retained source values and no hidden interpolation;
3. skew-cell slice/isosurface geometry fixtures proving full-lattice fractional-to-Cartesian transforms rather than axis-length spacing;
4. signed isosurface threshold state proving thresholds are explicit and source arrays unchanged;
5. ELF and LOCPOT parser fixtures whose units/grid/source behavior are verified against the exact optional backend used;
6. band fixtures with explicit k-point order, segment breaks, labels, spin/reference state and no hidden shift/interpolation;
7. reciprocal-space path fixtures proving the retained reciprocal-basis convention and absence of silent `2*pi` errors;
8. PROCAR fixtures with exact site/orbital/spin projection weights, explicit aggregation, and renderer-only width scaling;
9. skew-cell planar-potential geometry fixture verifying `h = V/A_face`;
10. explicit vacuum-region and `Phi = V_vacuum - E_F` work-function fixtures plus cross-calculation mismatch failures;
11. NEB discrete image/ref/saddle fixtures with exact forward/reverse barrier arithmetic and no spline;
12. passive-renderer tests proving retained arrays/state are not mutated;
13. optional 3D backend tests isolated from the base numerical import path and, if a heavy backend is added, headless fresh-wheel smoke in CI;
14. installed-wheel public-API smoke covering every new reviewed public module;
15. the complete v0.1-v0.6 regression suite remains green.

Visual regression testing should assert stable scene data, artist/mesh inputs, geometry counts/thresholds, labels, and export dimensions where possible rather than relying only on brittle pixel-perfect screenshots.

## Documentation and release sequence

The implementation sequence is:

0. Issue #197 + architecture PR: freeze this plan;
1. if needed, central documentation sync so `V0_7_PLAN.md` is the release-specific authority and Block 1 is identified as next;
2. Blocks 1-7, with completion-state synchronization at reviewed checkpoints following the established project pattern;
3. scientific-completion documentation sync;
4. Gate A frozen-scope packaging/public-API/installed-wheel hardening while retaining the prior release version until the gate contract says otherwise;
5. Gate B final v0.7 version candidate and exact-wheel validation;
6. Gate C tag creation only after separate explicit authorization;
7. GitHub Release/publication steps remain separately authorized; PyPI remains deferred unless that policy is explicitly changed.

Any head change invalidates older exact-head CI/review evidence.

## Explicitly out of scope for v0.7

- VASP, VTST, Bader, LOBSTER, or other simulation/external-program execution;
- HPC scheduler submission, remote execution, job monitoring, restart logic, convergence orchestration, or complete DFT workflow management;
- automatic subsystem construction or charge-density registration/alignment;
- arbitrary scientific-grid resampling/interpolation/alignment as a hidden visualization convenience;
- automatic symmetry k-path generation or band unfolding;
- Wannier interpolation;
- automatic band-gap/effective-mass/topological analysis;
- automatic vacuum/surface/plateau detection or macroscopic electrostatic correction;
- NEB image generation, IDPP, tangent/spring/climbing-image optimization, or continuous transition-state fitting;
- interactive browser/GUI plot editor, which remains v0.9-v1.0 scope;
- operando/time-resolved mapping, which remains v0.8 scope;
- version/tag/GitHub Release/PyPI mutation inside scientific implementation blocks unless a release gate explicitly authorizes it.