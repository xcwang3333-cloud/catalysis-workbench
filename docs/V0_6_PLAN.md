# CatalysisWorkbench v0.6 Plan

v0.6 is the electronic-structure and catalysis-thermodynamics release. This document freezes the architecture, scientific semantics, dependency boundaries, implementation order, and v0.7 handoff before any v0.6 scientific implementation begins. GitHub remains the operational source of truth.

## Baseline and release state

- Architecture checkpoint Issue: #146.
- Exact architecture base: `main` at `bed5c6e750a6066baa8daa21492aa9eb90e8bca8`.
- Released v0.5 tag: `v0.5.0 -> 9400ac0044ac333d2cae228554c08d955a816a4c`.
- Released v0.4 tag: `v0.4.0 -> bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6`.
- Distribution/runtime version is `0.5.0` and does not change in the architecture checkpoint.
- The public GitHub Release `CatalysisWorkbench v0.5.0` is complete.
- PyPI/package-registry publication remains explicitly deferred and must not be resumed without a separate future authorization.
- The v0.5 post-release documentation Issue #143 is completed/closed; any older wording that still calls it active is documentation drift, not live state.
- No v0.6 implementation may move or recreate `v0.5.0` or any earlier release tag.

## Existing computation/public-API baseline

At the architecture base, `catalysis_workbench.computation` owns four reviewed areas:

1. immutable `AtomicStructure` state;
2. explicit geometry/periodic-image/coordination/comparison results;
3. renderer-neutral `StructureScene` state;
4. explicit DFT energy ledgers, relative energies, linear combinations, and adsorption-energy arithmetic.

There is no reviewed public object yet for DOS/PDOS, Bader, COHP/ICOHP, thermochemical corrections, CHE state, or volumetric charge density. v0.6 therefore adds these capabilities without exposing third-party parser objects as public authority and without creating a second incompatible energy stack alongside `DFTEnergyLedger`.

## Architecture principles

The project-wide rules continue to apply, with additional v0.6 constraints:

1. CatalysisWorkbench owns immutable public scientific result contracts; third-party parser/backend objects are adapter internals.
2. Keep file parsing/backend access, numerical analysis, immutable result state, reporting, and rendering separate.
3. Every energy value carries explicit eV semantics and an auditable reference/zero convention.
4. Preserve source-native state where possible; transformations such as Fermi shifting, projection aggregation, normalization, spin summation, or sign inversion are explicit operations that return new state.
5. Site identities reuse deterministic `AtomicStructure` site keys/indices when structure-coupled data are represented.
6. Spin and orbital/site projections are scientific state, not display labels.
7. Scientific incompatibilities fail closed rather than being silently sorted, shifted, interpolated, resampled, aligned, renormalized, or remapped.
8. Numerical modules remain Matplotlib-lazy. Plotting is a passive consumer of reviewed retained arrays/state.
9. Optional mature permissive backends are preferred for difficult file parsing, but dependency addition occurs only in the concrete implementation Issue after wheel/API validation.
10. v0.1-v0.5 public surfaces remain compatible unless a breaking change is separately planned and reviewed.

## Frozen v0.6 scope

v0.6 contains nine scientific implementation blocks after this architecture checkpoint:

1. electronic-structure and volumetric data semantics/adapters;
2. DOS/PDOS processing and passive publication plotting;
3. band-center / DOS-moment analysis;
4. Bader-result parsing and explicit charge accounting;
5. COHP/ICOHP parsing and bonding analysis;
6. geometry-bonding correlation state/analysis;
7. CHE/free-energy thermodynamic bookkeeping;
8. passive free-energy diagrams;
9. charge-density-difference calculation with lattice/grid validation.

The architecture order is deliberately not the original roadmap order: all later electronic descriptors first depend on one shared file/reference/projection/grid semantics layer.

## Prior-art, license, and dependency decisions

### Pymatgen / pymatgen-core

`materialsproject/pymatgen` and `materialsproject/pymatgen-core` are MIT licensed and Python 3.11+ compatible in the surveyed current releases. The project already uses optional `pymatgen-core` support for v0.5 structure adapters. Full `pymatgen` supplies mature VASP and LOBSTER I/O including `Vasprun`, `Chgcar`, `Procar`, `Cohpcar`, and `Icohplist`-class functionality.

v0.6 decision:

- preferred optional parser/backend candidate for VASP rich output and LOBSTER output;
- CatalysisWorkbench owns the public immutable result objects and converts backend state into them immediately;
- do not expose `Vasprun`, `CompleteDos`, `Chgcar`, `Cohpcar`, `Icohplist`, or other mutable/backend-specific objects as authoritative public results;
- a concrete implementation PR must validate exact full-`pymatgen` version compatibility, installed-wheel behavior, supported formats, and dependency footprint before adding an `electronic`-style optional extra.

### Sumo

`SMTG-Bham/sumo` is MIT licensed and builds publication-oriented DOS/band plotting on top of pymatgen. It is a strong reference for projection selection, DOS decomposition, CLI/plot separation, and publication figure behavior.

Decision: reference-only for v0.6 plotting/API ideas. Do not add it as a runtime dependency because CatalysisWorkbench already owns `FigureSpec`/rendering and needs a narrower retained-state contract.

### LobsterPy

`JaGeo/LobsterPy` is BSD-3-Clause licensed and provides mature automated LOBSTER bonding analysis and plotting.

Decision: reference-only initially for COHP/ICOHP workflows, diagnostics, and test ideas. The first CatalysisWorkbench bonding layer stays explicit and does not import automatic strongest-bond/relevant-bond chemistry heuristics as hidden defaults. Pymatgen's lower-level LOBSTER parsers are the preferred backend candidate.

### py4vasp

`vasp-dev/py4vasp` is Apache-2.0 licensed and provides the official Python interface to newer VASP HDF5 output.

Decision: useful reference and possible later optional HDF5 adapter, but not required for the first v0.6 legacy text/XML scope. Avoid adding two VASP backends before a concrete need exists.

### ASE

ASE is LGPL-2.1-or-later. `ase.thermochemistry` provides HarmonicThermo/IdealGasThermo-style thermochemical routines and is scientifically useful prior art for explicit vibrational, temperature, pressure, entropy and free-energy terms.

Decision: thermochemistry/reference-only initially. v0.6 can represent caller-supplied thermochemical components transparently with the existing NumPy/SciPy stack; do not add ASE merely to avoid simple explicit bookkeeping.

### PyProcar

`romerogroup/pyprocar` is GPLv3 and is a mature reference for PROCAR-centric orbital/site/spin projection processing and visualization.

Decision: reference-only. No copied/adapted GPL implementation and no runtime dependency. PROCAR-driven band/fat-band plotting is a v0.7 feature anyway.

### Henkelman-group Bader code

The Henkelman-group Bader code is GPLv3-or-later and is an external executable that performs the actual zero-flux charge partitioning.

Decision: external-program/reference-only. v0.6 parses standard Bader result output and performs explicit charge accounting; it does not bundle, compile, install, or launch the Bader executable.

### CatMAP

`SUNCAT-Center/catmap` is GPL-3.0 and implements electrochemical thermodynamic corrections and full microkinetic modeling. Its CHE treatment is useful scientific/workflow prior art.

Decision: CHE/reference-only. v0.6 implements transparent free-energy/CHE bookkeeping only; microkinetics, coverage solving, transfer-coefficient kinetics and descriptor maps are outside the release.

### VASPKIT

VASPKIT is currently distributed as binaries under its own academic/scientific/educational/noncommercial usage agreement rather than as a normal permissive open-source Python dependency.

Decision: workflow/output/reference-only. No code copying, bundling, or runtime invocation.

### LOBSTER

LOBSTER is external noncommercial research software used to generate bonding outputs such as `COHPCAR.lobster` and `ICOHPLIST.lobster`.

Decision: external producer only. CatalysisWorkbench parses already generated results; it does not redistribute or launch the LOBSTER engine. Parser citations/producer provenance remain visible.

### pymatgen-analysis-diffusion

`materialyzeai/pymatgen-analysis-diffusion` is BSD-3-Clause but is scoped to diffusion analysis (van Hove, probability density, migration paths/IDPP).

Decision: surveyed and not relevant to v0.6; no dependency.

## Shared electronic-structure semantics

### Energy axis and reference

Electronic energies are represented in eV with both the numerical axis and its reference semantics retained.

Required state includes:

- exact source energy array;
- source/native Fermi level when available;
- energy-reference kind such as source-native, Fermi-referenced, vacuum-referenced, or caller-defined custom reference;
- explicit shift applied to create a referenced axis;
- provenance/source digest.

Rules:

- never silently subtract `E_F` during parsing and then lose the original reference;
- never apply a second Fermi shift to LOBSTER data that are already reported with `E_F = 0`;
- plotting may choose a referenced display axis only through explicit retained transformation state;
- cross-calculation overlay/comparison must state whether each trace is source-native, independently Fermi-referenced, vacuum-referenced, or otherwise aligned.

### Spin

Scientific storage uses physical channels rather than plotting conventions.

Initial collinear channels are explicit `up` and `down`. Numerical DOS values remain non-negative as supplied by the source. A common mirrored DOS plot with spin-down below zero is display-only.

For non-collinear VASP output, total and magnetization components must remain distinguishable. A concrete adapter may initially reject unsupported non-collinear projections rather than collapsing them into misleading up/down channels.

### Site and orbital projections

Projection identity is deterministic and separate from labels.

Retained projection state may include:

- structure/site key and zero-based site index;
- element/species;
- orbital family (`s`, `p`, `d`, `f`) and exact component when present (`px`, `dxy`, etc.);
- spin channel;
- producer/parser provenance.

Element/site/orbital aggregation is always an explicit analysis operation. No automatic summation merely because display labels are similar.

### Normalization and units

For VASP DOSCAR, the surveyed native total DOS convention is states/eV and integrated DOS is states; site/l-projected DOS is reported in states/atom/energy. CatalysisWorkbench stores an explicit density unit and normalization basis rather than encoding these semantics in a plot label.

Supported normalization states may include source-native extensive DOS, per-volume DOS, and explicit per-atom/site aggregation. Max-normalized or area-normalized traces, if later offered for visual comparison, are derived display/analysis state and never silently replace quantitative DOS.

## File-format and adapter boundary

### `vasprun.xml`

Preferred first rich VASP DOS/PDOS source because it retains Fermi energy, structure, spin and projection metadata in a parser-friendly form. Initial implementation should use a reviewed optional full-pymatgen backend rather than hand-writing a general XML parser.

### `DOSCAR`

Direct DOSCAR support is useful but format semantics vary with spin, LORBIT/projection settings and non-collinear output. It is not allowed to guess a layout heuristically. A direct adapter may enter the DOS block only after regression fixtures cover the supported variants and unsupported variants fail clearly.

### `PROCAR`

PROCAR contains band/k-point/atom/orbital projection weights, not a DOS object. v0.6 records the format in the survey but does not create a broad PROCAR public API merely for future use. Band/fat-band analysis and plotting remain v0.7.

### `CHGCAR`

CHGCAR contains the structure, fine FFT-grid dimensions, total electron-number density data and, for magnetic calculations, additional magnetization blocks.

Canonical v0.6 physical density convention:

- retain grid shape `(nx, ny, nz)` and lattice matrix in angstrom;
- convert the stored VASP values to electron-number density `n(r)` in `1/angstrom^3` using the documented FFT-grid and cell-volume normalization;
- retain component identity such as total density or magnetization component;
- the integral of total `n(r)` over the cell is a sanity diagnostic against electron count when producer state permits;
- do not call the positive electron-number density a signed Coulomb charge density.

### `LOCPOT`

LOCPOT is surveyed as a local-potential source in eV, but work-function/vacuum-potential processing remains v0.7. No unused v0.6 public adapter is required unless shared parsing infrastructure demonstrably needs it.

### Bader `ACF.dat`

The first Bader adapter targets already generated standard atom-resolved result tables. It preserves raw atom index/position, integrated electron population, Bader volume and minimum-distance-like diagnostics when present. It does not run the external partitioning algorithm.

### LOBSTER `COHPCAR.lobster` / `ICOHPLIST.lobster`

The first bonding adapter uses a reviewed pymatgen LOBSTER parser backend where practical and converts immediately to CatalysisWorkbench-owned immutable state.

LOBSTER energy arrays are treated as already Fermi-referenced when the producer/parser reports that convention. Bond labels, site pairs, bond lengths, cell translations where available, spin channels, orbital resolution, `number_of_bonds`, and integrated values at `E_F` are retained rather than flattened.

## 1. Electronic-structure and volumetric semantics/adapters

This foundation block introduces only shared state needed by later scientific blocks.

Candidate public contracts include:

- immutable electronic energy-axis/reference state;
- immutable DOS channel/projection identifiers;
- immutable volumetric grid/component state;
- VASP/LOBSTER adapter conversion boundaries that return CatalysisWorkbench objects.

Initial implementation targets rich `vasprun.xml` DOS/PDOS conversion and CHGCAR total-density conversion/validation. COHP and Bader domain-specific result objects remain in their own later blocks.

The block must not add band plotting, Bader partitioning, COHP analysis, CHE, or charge-density subtraction merely because the parser backend can expose those features.

## 2. DOS / PDOS processing and passive plotting

The DOS layer consumes reviewed immutable electronic-structure state.

Required operations/state:

- total DOS selection;
- exact site/element/orbital/spin projection selection;
- explicit projection aggregation;
- optional explicit energy referencing such as `E - E_F`;
- explicit crop/window without hidden interpolation;
- retained normalization basis and source identity;
- detached table export;
- passive publication plotting through the existing visualization specification model.

Plotting rules:

- negative mirrored spin-down is presentation-only;
- Fermi marker/zero label follows retained reference state;
- plotting does not re-aggregate orbitals, shift energies, normalize, broaden or smooth behind the caller's back;
- multi-sample overlay fails when the requested reference/normalization semantics are incompatible.

Additional Gaussian broadening or interpolation is not part of the minimum first block unless separately justified and tested because these operations change the quantitative trace.

## 3. Band-center / DOS-moment analysis

Band center is defined as an explicit first moment of the selected DOS:

`epsilon_center = integral rho(E) * E dE / integral rho(E) dE`

The result retains:

- selected projection/site/orbital/spin state;
- exact energy reference/zero;
- explicit integration window;
- numerator and denominator;
- integration method;
- resulting center in eV;
- source digest/provenance.

Rules:

- occupied-only, unoccupied-only, or full-range integration is caller-selected rather than inferred from a name such as `d_band_center`;
- a zero/near-zero denominator fails explicitly;
- non-monotonic/duplicate energy grids are not silently sorted or deduplicated;
- combining spin channels means an explicit physical sum of the selected positive DOS channels before integration;
- normalization scaling does not change the mathematical center but remains part of provenance.

Higher moments/width/skewness can be deferred unless implementation remains narrow and fully tested; the v0.6 acceptance target is the explicit first moment.

## 4. Bader result parsing and charge accounting

The Bader layer represents external partitioning results without claiming to perform the partitioning itself.

Per-site retained state includes when available:

- deterministic site key/index;
- output Cartesian position in angstrom;
- integrated Bader electron population;
- Bader volume in angstrom^3;
- minimum-distance diagnostic in angstrom;
- source/result provenance;
- optional caller-supplied reference valence-electron count.

Derived charge conventions are explicit:

- `electron_transfer = N_Bader - N_reference`, positive meaning electron gain;
- `partial_charge = N_reference - N_Bader`, positive meaning electron deficiency/cationic direction.

The API must never use an ambiguous field named only `charge` for these derived quantities.

When mapped to `AtomicStructure`, site count/order and positions must be checked with an explicit tolerance. A count mismatch, ambiguous mapping, or incompatible structure fails rather than silently attaching rows by position.

Oxidation-state assignment, charge-density partitioning, executable discovery/launch and automatic POTCAR/ZVAL lookup are outside the initial block. A future adapter may read explicitly supplied valence reference metadata, but provenance must remain visible.

## 5. COHP / ICOHP parsing and bonding analysis

The bonding layer consumes external LOBSTER output and preserves producer semantics.

Retained COHP state includes:

- exact energy grid/reference;
- raw COHP and integrated COHP channels per spin;
- bond label/stable key;
- site pair and translation/image identity where available;
- bond length in angstrom;
- orbital-resolved identities when present;
- producer/parser provenance.

Retained ICOHP summary state includes:

- bond identity;
- bond length;
- `number_of_bonds`/multiplicity basis;
- spin-resolved ICOHP(E_F);
- explicit spin-summed value only when requested.

Sign rule: preserve the LOBSTER/source COHP/ICOHP sign convention in scientific state. Common `-COHP`/`-ICOHP` presentation may be offered only as a display transform whose sign inversion is explicit.

No hidden strongest-bond threshold, cation/anion inference, bond classification, or automatic chemistry narrative belongs in the first block.

## 6. Geometry-bonding correlations

This block joins reviewed geometry state from v0.5 to reviewed v0.6 bonding/charge descriptors using explicit stable identities.

Initial use cases include:

- bond length versus ICOHP;
- bond angle/local geometry metric versus a caller-selected bonding descriptor;
- site geometry/coordination versus a caller-selected Bader descriptor when an explicit mapping exists.

The result is a detached correlation dataset that retains x/y definitions, units, source keys, mapping provenance and excluded/missing state.

Optional statistical summaries such as Pearson/Spearman correlation may be exposed only on explicit request and must report sample count and undefined cases. No correlation result is presented as causal evidence.

Automatic cross-structure atom/bond matching is not introduced here; callers use reviewed `SiteMapping`/bond identities or a future separately reviewed deterministic mapping algorithm.

## 7. CHE and free-energy thermodynamics

This block extends the v0.5 energy ledger rather than introducing an incompatible parallel energy model.

### Free-energy components

A thermodynamic entry preserves the distinction between:

- electronic DFT energy in eV;
- zero-point energy (ZPE) in eV;
- optional thermal enthalpy correction in eV;
- entropy in eV/K together with temperature in K;
- caller-supplied additional corrections such as solvation in eV, each with a stable key/type/source;
- explicit availability state so “not supplied” is not silently treated as a measured zero.

A reviewed recipe evaluates a free energy using only explicitly included terms. The library does not query a hidden gas-phase, vibrational, solvation, or experimental thermochemistry database.

ASE thermochemistry is a scientific reference for later frequency-to-thermochemistry helpers, but the first v0.6 block can consume explicit caller-supplied ZPE/entropy/thermal terms without adding ASE.

### CHE reference

The computational hydrogen electrode uses an explicit `H2` free-energy reference and explicit potential/pH state.

For one proton-electron pair on the SHE scale, the convention is represented transparently as

`mu(H+ + e-) = 1/2 G(H2) - e U_SHE - k_B T ln(10) * pH`.

In eV per electron and volts, the `e U` contribution is numerically the potential in eV, but the API retains the physical meaning rather than relying on an undocumented unit trick.

If a potential is supplied versus RHE, the SHE/RHE conversion is explicit. At the same temperature, using the ideal Nernst relation makes the pH term cancel for the paired CHE chemical potential when expressed consistently versus RHE; that cancellation must arise from recorded conversion state rather than a hidden special case.

Reaction/free-energy arithmetic uses explicit stoichiometric coefficients with a documented products-positive/reactants-negative convention. The sign of potential/pH corrections therefore follows from the coefficient rather than from reaction-name heuristics.

### v0.6 CHE exclusions

Out of scope:

- automatic reaction-pathway discovery;
- microkinetic/coverage solving;
- transition-state transfer coefficients;
- automatic solvation/hydrogen-bond corrections;
- constant-potential DFT correction schemes;
- Pourbaix construction;
- automatic gas-phase thermochemical lookup.

## 8. Free-energy diagrams

Free-energy diagrams are passive consumers of reviewed retained thermodynamic state.

The first diagram contract supports:

- an explicit ordered sequence of states/steps;
- retained absolute or reference-relative free energies in eV;
- explicit potential/pH/reference labels derived from scientific state;
- optional comparison of several catalyst/pathway series only when state semantics are compatible;
- publication rendering through existing `FigureSpec`/style machinery;
- detached tabular reporting of the plotted values.

Rendering must not recompute CHE corrections or silently choose a reference state. Transition-state/barrier plots and NEB profiles remain v0.7.

## 9. Charge-density difference with lattice/grid validation

The numerical operation is an explicit linear combination of co-registered volumetric electron-number-density grids, commonly

`Delta n(r) = n_combined(r) - sum_i c_i * n_reference_i(r)`.

The exact coefficients are caller-visible and retained.

Compatibility gates before arithmetic:

- identical grid shape;
- compatible lattice matrix within an explicit numerical tolerance;
- same periodic-cell orientation/convention;
- compatible volumetric component semantics;
- compatible physical density unit;
- explicit source structure/site identity sufficient to establish that the grids are already co-registered.

There is no hidden interpolation, resampling, fractional translation, origin shift, atom reorder, Kabsch alignment, supercell conversion, or grid matching.

The result retains:

- exact difference grid;
- lattice/grid metadata;
- component/unit;
- source identities and coefficients;
- voxel/cell-volume information;
- integrated difference/sanity diagnostic.

For CHGCAR total density, the canonical numerical unit is `1/angstrom^3` electron-number density. Magnetic components may be retained by adapters, but subtraction is permitted only like-for-like. Non-collinear component support may fail closed in the first implementation if not fully validated.

Isosurfaces, slices, contour maps and other volumetric rendering are explicitly v0.7, not part of this block.

## Frozen dependency order

0. **Architecture checkpoint — Issue #146 / `V0_6_PLAN.md`.**
1. **Electronic-structure + volumetric semantics/adapters.**
2. **DOS/PDOS processing + passive plotting.**
3. **Band-center analysis.**
4. **Bader result parsing + charge accounting.**
5. **COHP/ICOHP parsing + bonding analysis.**
6. **Geometry-bonding correlation.**
7. **CHE/free-energy thermodynamics.**
8. **Free-energy diagrams.**
9. **Charge-density-difference calculation + lattice/grid validation.**
10. **Completion-state documentation synchronization.**
11. **Gate A frozen-scope release hardening.**
12. **Gate B final-version candidate.**
13. **Gate C tag creation/reverse verification under separate user authorization.**

Why this order:

- one shared reference/spin/projection/grid contract must exist before DOS, Bader, COHP or volumetric subtraction;
- DOS must exist before band-center analysis;
- bonding result state must exist before geometry-bonding joins;
- CHE is architecturally orthogonal to file parsing and already depends on the v0.5 explicit DFT-energy foundation, so it follows the electronic/bonding cluster without creating a competing energy model;
- free-energy plotting follows thermodynamics rather than embedding thermodynamic logic in the renderer;
- charge-density difference is last because it has the strictest multi-file compatibility requirements, while the required volumetric grid contract is established early in block 1.

Scientific implementation must not start before this architecture checkpoint merges.

## v0.7 boundary

The following remain v0.7 advanced computational analysis/visualization:

- charge-density-difference isosurfaces and slices;
- ELF/charge-density visualization;
- band-structure and fat-band/PROCAR plotting;
- work-function/local-potential processing from LOCPOT;
- NEB/barrier plots;
- advanced volumetric rendering.

HPC/VASP job submission and complete workflow management remain outside the current project scope rather than being silently pulled into v0.7.

## Test strategy for later implementation blocks

Each scientific block must include hand-verifiable fixtures and failure modes appropriate to its contract.

Minimum planned regression themes:

- DOS: tiny synthetic spin-resolved DOS with exact projection sums, Fermi shift and unit/normalization checks;
- band center: analytic/symmetric DOS cases with known first moments and zero-denominator rejection;
- Bader: small ACF-like fixture with explicit reference valence counts and sign-convention checks;
- COHP/ICOHP: tiny parser fixture preserving Fermi-zero, sign, spin, length/multiplicity and orbital identity;
- correlation: exact stable-key joins plus mismatch/undefined-statistic cases;
- CHE: hand-calculated H2 reference, SHE/RHE/pH/potential sign cases and missing-correction-state checks;
- free-energy diagram: retained values identical to plotted/reported values with no hidden recomputation;
- charge-density difference: tiny 2x2x2 grids with exact arithmetic/integral plus lattice/grid/component mismatch failures.

Third-party backend behavior must be covered by adapter fixtures rather than assumed from upstream documentation alone.

## Mandatory feature loop

Every v0.6 scientific block follows:

```text
live main verification
    -> prior-art/license refresh
    -> exact-base branch
    -> implementation + hand-verifiable regression tests
    -> Draft PR
    -> exact-head CI
    -> scientific review
    -> API/compatibility/packaging review
    -> direct fixes
    -> fresh exact-head CI after every head change
    -> final-head reviews
    -> Ready
    -> behind=0 / mergeable=true / review threads=0
    -> expected-head squash merge
    -> direct main reverse verification
    -> Issue closure
```

Any head change makes earlier CI/review evidence stale.

## Architecture checkpoint acceptance

The architecture checkpoint itself is documentation-only:

- `docs/V0_6_PLAN.md` records the frozen architecture and prior-art/license decisions;
- no scientific source/test/workflow/dependency/version/tag/release/PyPI change is allowed;
- exact-head CI must pass;
- formal architecture/scientific/API/license review must have no blockers;
- if the head changes after review, fresh exact-head CI/review evidence is required;
- before merge: behind=0, mergeable=true, unresolved review threads=0;
- squash merge must use the exact reviewed head;
- post-merge `main`, `v0.5.0`, distribution/runtime version and open Issue/PR state are re-read directly.

Central documentation whose release-state wording drifted after the v0.5 final sync may be corrected in an immediate docs-only follow-up before the first v0.6 scientific implementation block, following the same exact-head discipline.

## Release and publication boundaries

- Architecture and scientific implementation do not change distribution/runtime version from `0.5.0`.
- Gate A later hardens the frozen v0.6 scope while still retaining the pre-release version according to the established release workflow.
- Gate B is the later reviewed version-finalization/exact-wheel boundary.
- Gate C tag creation remains a separate explicit user-authorization boundary.
- GitHub Release publication remains separate from Git tag creation.
- PyPI/package-registry publication remains deferred unless separately reauthorized.
- `v0.5.0` and earlier release tags are immutable.