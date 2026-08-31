# Changelog

All notable changes to CatalysisWorkbench are recorded here.

## [Unreleased]

### Added

- v1.1 desktop dogfooding hardening adds the `catalysis-workbench` CLI entry point, a Qt-free `--version` path, explicit `--project` launch into a v1.1 project, Export-page Save Project, post-export Open Folder / Export Another actions, actionable desktop errors with optional technical details, and a presentation-only Recent Projects cache.
- Cumulative fresh-wheel dogfood smoke coverage now exercises Generic XY, LSV / Polarization, and FE & Partial Current through the installed desktop path, with the Block-6 smokes wired into regular CI.

### Changed

- v1.1 Block 6 hardens the ordinary desktop workflow without changing the reviewed scientific semantics or the frozen v1.0 compatibility surface.
- Stable 1.1 Gate A is merged and post-merge verified at `843df51828d740405aa5365142541ed361e069cc`; CI #854, Stable 1.0 Readiness #116, and Stable 1.1 Readiness #3 are green on that exact main commit.
- Gate B synchronizes the release candidate mechanically to `1.1.0`, including distribution/runtime identity, version-sensitive installed-smoke evidence, and exact wheel/sdist expectations. No feature, scientific, dependency, schema, public-API, or runtime-semantic change is introduced.
- Stable 1.0 Readiness remains an active compatibility gate. Gate B does not create `v1.1.0`, publish a GitHub Release, create installers, or publish to PyPI/package registries.

## [0.6.0] - 2026-08-25

The v0.6 release freezes the reviewed electronic-structure and catalysis-thermodynamics scope after Gate A release hardening, Gate B final-version exact-wheel validation, Gate C tag verification, and public GitHub Release publication. Tag `v0.6.0` resolves exactly to reviewed Gate-B release commit `c7793b309f41d174c14534bd6d4acdacc2a57636`, and distribution/runtime version through the tag is `0.6.0`. The GitHub Release `CatalysisWorkbench v0.6.0` is published from that existing tag with reviewed release notes. PyPI/package-registry publication remains deferred.

### Added

- Electronic-structure and volumetric semantics/adapters with immutable retained state, explicit energy/Fermi/spin/projection/component conventions, and reviewed optional VASP adapters.
- DOS/PDOS processing and passive publication plotting with explicit energy referencing, compatible retained-channel aggregation, source-grid-only cropping, and no hidden resampling.
- Band-center / DOS first-moment analysis with caller-selected windows/tolerances and retained numerical provenance.
- Bader-result parsing and explicit charge accounting without hidden POTCAR/ZVAL/oxidation-state inference.
- COHP/ICOHP parsing and explicit bonding analysis with source-sign semantics, deterministic bond/orbital identities, and retained multiplicity/provenance.
- Explicit geometry–bonding correlation datasets without hidden matching, statistics, ranking, or causal interpretation.
- CHE/free-energy thermodynamics with explicit correction/reference/potential/pH bookkeeping and no hidden chemistry/pathway lookup.
- Passive free-energy-diagram state and plotting with explicit caller ordering/reference semantics and no hidden CHE recomputation.
- Charge-density-difference arithmetic `Δn(r)=n_combined(r)-Σc_i n_reference_i(r)` with strict grid/lattice/unit/component/common-registration validation and no hidden interpolation, resampling, alignment, supercell conversion, component conversion, or renormalization.
- Unified v0.6 fresh-wheel installed/public-API release audit covering representative reviewed computation exports, optional structure/electronic/bonding adapters, and documented quickstarts.

### Changed

- All nine v0.6 scientific implementation blocks (#150/#151 through #182/#183) are complete; final scientific implementation merge is `f47d2165f282c8fe2745d1bd50ed32886b0f2054`.
- Scientific-completion documentation synchronization #184/#185 merged as `f364e51de5eb2119a2495e93135572605dd8f926`.
- Gate A / Issue #186 / PR #187 hardened the frozen v0.6 scope while retaining version `0.5.0`; final head `a72be9f227f92b94df11b40c0bd77bd97933ecdb` passed CI #451 / run `32844596642` and reviews `5018578746`, `5018579676` before squash merge `c70481e34f6e3f2bf81724f4a30370fec58c1e7b`.
- Gate B / Issue #188 / PR #189 synchronized `[project].version`, runtime `__version__`, and the exact-wheel expected version to `0.6.0`; final head `4544a464ab54e13408e3db23a68acf565f764328` passed CI #453 / run `32845155122` and reviews `5018619904`, `5018620923` before squash merge/reviewed release commit `c7793b309f41d174c14534bd6d4acdacc2a57636`.
- Gate C / Issue #192 created and reverse-verified `v0.6.0` exactly on `c7793b309f41d174c14534bd6d4acdacc2a57636`; distribution/runtime version through the tag is `0.6.0`.
- GitHub Release tracking Issue #193 completed after the public `CatalysisWorkbench v0.6.0` Release was published from the existing tag with populated release notes.
- `v0.5.0` remains immutable at `9400ac0044ac333d2cae228554c08d955a816a4c`; `v0.4.0` remains immutable at `bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6`.
- PyPI/package-registry publication remains deferred.

## [0.5.0] - 2026-08-25

The v0.5 release freezes the reviewed XAS, structure, and basic DFT-energetics scope after Gate A release hardening, Gate B final-version validation, Gate C tag verification, and public GitHub Release publication. Tag `v0.5.0` resolves exactly to reviewed Gate-B release commit `9400ac0044ac333d2cae228554c08d955a816a4c`, and distribution/runtime version through the tag is `0.5.0`. The GitHub Release `CatalysisWorkbench v0.5.0` is published from that existing immutable tag with reviewed release notes. PyPI/package-registry publication remains deferred.

### Added

- Explicit XAS/XANES preparation with energy/eV semantics, caller-controlled energy shifts, measured-point windows, explicit E0 and pre/post-edge polynomial normalization, fail-closed edge-step state, retained provenance, and passive comparison plotting.
- FT-EXAFS with explicit uniform k-grid/transform conventions, retained complex χ(R), magnitude/real/imaginary/phase views, no hidden interpolation, and passive publication plotting.
- WT-EXAFS with explicit Cauchy transform parameters, authoritative complex k–R matrix, retained magnitude/real/imaginary/phase views, and hand-verifiable ridge regression.
- Neutral EXAFS fitting-result summary contracts that preserve external path/shell parameters, uncertainty availability, and producer-specific diagnostic labels without cross-tool reinterpretation.
- Immutable atomic-structure state with optional `pymatgen-core` adapters for POSCAR, CONTCAR, CIF, and XYZ.
- Explicit periodic-image geometry, exact site distance/angle, caller-bounded cutoff coordination, and caller-mapped structure comparison without hidden minimum-image or auto-alignment behavior.
- Renderer-neutral immutable `StructureScene` plus passive static Matplotlib 3D structure publication rendering with explicit atoms, bonds, unit-cell geometry, camera/projection, and presentation-only visual defaults.
- Basic DFT energetics with immutable eV energy ledgers, explicit normalization bases/source IDs, same-basis relative energies, generic retained linear combinations, transparent adsorption-energy arithmetic, detached reporting tables, and passive relative-energy plotting.
- Unified v0.5 fresh-wheel release audit covering installed-source verification, distribution/runtime version agreement, all documented package-level `__all__` surfaces including `catalysis_workbench.computation`, Matplotlib-lazy numerical imports, the retained v0.4 audit, and every reviewed v0.5 base-environment installed smoke.

### Changed

- All eight v0.5 scientific implementation blocks (#117/#118, #119/#120, #121/#122, #123/#124, #125/#126, #127/#129, #130/#131, #132/#133) are complete; scientific-completion commit is `a7ebd009ec83b0aeb068ad2d2f6712c17a783f1f`.
- Completion-state documentation synchronization #134/#135 merged as `8c958ffc29a36afa9340cada2239b51520c87a3d`.
- Gate A / Issue #136 / PR #137 hardened the frozen v0.5 scope while retaining version `0.4.0`; final head `fb13cdbf633366a0840f5f2e21af215bee47b133` passed CI #358 / run `32799486710` and reviews `5014277750`, `5014278425` before squash merge `0ffcd7e4a89340d993468039ba83b44bc7638050`.
- Gate B / Issue #138 / PR #139 synchronized `[project].version`, runtime `__version__`, and the exact-wheel expected version to `0.5.0`; final head `b95841ed472aff1fa4d05af7335547ee5c3cd611` passed CI #360 / run `32800514038` and reviews `5014348449`, `5014349058` before squash merge `9400ac0044ac333d2cae228554c08d955a816a4c`.
- Post-Gate-B state synchronization #140/#141 merged before Gate C; Gate C / Issue #142 then created and reverse-verified `v0.5.0` exactly on `9400ac0044ac333d2cae228554c08d955a816a4c`.
- GitHub Release tracking Issue #144 completed after the public `CatalysisWorkbench v0.5.0` Release was published from the existing tag with populated release notes.
- `v0.4.0` remains immutable at `bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6`.
- PyPI/package-registry publication remains deferred.

## [0.4.0] - 2026-08-25

The v0.4 release freezes the reviewed advanced experimental-analysis scope after Gate A release hardening and Gate B final-version validation. Tag `v0.4.0` was created on 2026-08-25 and reverse-verified to resolve exactly to release commit `bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6`. The GitHub Release has been published from that existing immutable tag; package-registry/PyPI publication remains deferred.

### Added

- Shared constrained peak-fitting foundation with explicit component/parameter identities, caller-visible fixed/bounded/tied state, Gaussian/Lorentzian/Voigt/pseudo-Voigt/Doniach model families, explicit fit regions/background/weights, physical residuals, deterministic provenance, and optional uncertainty/covariance state backed by reviewed `lmfit>=1.3.4`.
- XPS preparation with explicit binding-energy/eV semantics, additive energy-reference correction, measured-point-only region selection, direction-safe linear background, independently implemented Shirley fixed-point background, explicit convergence/failure state, and deterministic preparation provenance.
- Constrained XPS fitting as a thin shared-fitter consumer with caller-supplied signed doublet separation, amplitude and model-specific shape/width relations, fail-closed prepared-background alignment, immutable XPS fit state, passive publication plotting, physical-residual diagnostics, display-only binding-energy direction, and stable `FigureSpec` visual keys.
- EIS analysis with explicit complex-impedance semantics, ideal R/C/CPE series/parallel circuits, caller-visible parameter/bounds/fixed state, deterministic real+imag SciPy least-squares fitting, fail-closed immutable fit reconstruction, diagnostics, and passive Nyquist/Bode publication plotting.
- Quantitative BET fitting with caller-selected measured regions, exact BET/Rouquerol transforms, independent physical-consistency checks, explicit loading-to-area conversion inputs, fail-closed preprocessing provenance, diagnostics, and passive retained-array publication plotting.
- Technique-agnostic product calibration and inverse sample quantification with explicit linear free/fixed-zero-intercept models, measured-point calibration ranges, retained regression/residual state, exact response-unit matching, default extrapolation rejection, explicit ordered positive dimensionless quantification factors, replicate mean/sample-SD/RSD summaries, and passive calibration plotting.
- Unified v0.4 fresh-wheel Gate-A audit covering installed-source verification, distribution/runtime version agreement, all documented package-level `__all__` surfaces including product analysis, Matplotlib-lazy numerical imports, the retained v0.3 numerical audit, and reviewed installed smokes for shared fitting, XPS, EIS, quantitative BET, and product calibration.

### Changed

- Gate A / Issue #103 / PR #104 hardened the frozen v0.4 scope while intentionally retaining version `0.3.0`; exact-head CI #302 / run `32758548117` and two formal release reviews passed before squash merge `ce06abc11559fa7679869fc83a59356735ce6824`.
- Gate B / Issue #105 / PR #106 synchronized `[project].version` and runtime `__version__` to `0.4.0`; final head `ae3dc21b1a3a4e907d8c39eb85d3dbebefd8fbb4` passed exact-head CI #304 / run `32759679632` and reviews `5011014348`, `5011017132` before squash merge `bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6`.
- Gate C / Issue #107 completed the separately authorized Git tag operation; `v0.4.0` resolves exactly to `bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6` and reads distribution/runtime version `0.4.0` through the tag.
- `v0.3.0` remains immutable at `845ac4c15d399a8816c7ba66d61ea6ec4cc11293`; neither the v0.4 Git tag nor GitHub Release publishes a package-registry artifact.

## [0.3.0] - 2026-08-24

The v0.3 release freezes the reviewed extended-characterization scope after Gate A release hardening and Gate B final-version validation. Tag `v0.3.0` was created on 2026-08-24 and reverse-verified to resolve exactly to release commit `845ac4c15d399a8816c7ba66d61ea6ec4cc11293`; package-registry publication remains a separate policy decision.

### Added

- First v0.3 FTIR/ATR-FTIR workflow with explicit wavenumber and absorbance/transmittance semantics, explicit `A = -log10(T)` conversion, caller-window polynomial baseline fitting, direction-independent direct-window band integration, stable-key Dataset processing, shared publication plotting, deterministic provenance, installed-wheel smoke, and compact quickstart documentation.
- Reviewed TGA / DTG / TPR / TPD thermal-analysis foundation with explicit °C/K temperature semantics and conversion, raw-mass versus normalized TGA bases, explicit reference-mass normalization, measured-grid `numpy.gradient` DTG with caller-selected sign convention, TPR/TPD detector-signal semantics, measured-point-supported direct thermal-window extrema/integration, stable-key Dataset processing, compatibility guards, deterministic provenance, lazy shared publication plotting, installed-wheel thermal smoke, and compact quickstart documentation.
- Reviewed basic gas-sorption isotherm foundation with explicit `P/P0` fraction/percent semantics, explicit adsorbed-quantity units, caller-declared adsorbate/measurement temperature/adsorption-desorption branch, explicit standard-gas conditions for `cm^3(STP)/g`, branch-direction independence, stable-key Dataset processing, measured-point-only pressure-window summaries, strict overlay compatibility, lazy shared publication plotting, installed-wheel smoke, and compact quickstart documentation; quantitative BET/Rouquerol/pore-size fitting remains deferred.
- Reviewed ICP/elemental-composition integration foundation with immutable scalar measurement/summary tables, explicit bulk-mass-fraction versus solution-concentration bases and units, explicit digestion/dilution solution-to-bulk mass balance, deterministic tidy CSV/Excel import and stable source keys, arithmetic mean/sample-SD/RSD replicate summaries, strict no-closure/no-hidden-conversion behavior, lazy shared grouped-bar publication plotting, installed-wheel smoke, and compact quickstart documentation.

### Changed

- Gate B synchronized distribution metadata and runtime `__version__` at `0.3.0` and validated a freshly built exact wheel through the unified v0.3 installed numerical audit, existing installed API/module smokes, all seven quickstarts, public `__all__` resolution, `pip check`, installed-source verification, and Matplotlib-lazy characterization import.
- Gate C / Issue #70 completed the separately authorized Git tag operation; `v0.3.0` resolves exactly to `845ac4c15d399a8816c7ba66d61ea6ec4cc11293`.
- Shared peak-fitting remains intentionally deferred to v0.4 for joint design with constrained XPS/spectroscopy consumers; no new scientific algorithms were introduced by the v0.3 release gates.

## [0.2.0] - 2026-08-24

The v0.2 release extends the reviewed common-XY foundation into explicit, provenance-rich quantitative electrochemistry while preserving the v0.1 public behavior.

### Added

- Shared electrochemistry quantity/unit conversion helpers covering potential, current, current density, charge, time, scan rate, area, mass/loading, amount, molar rate, rotation rate, reference names, and explicit electron stoichiometry.
- Reusable frozen electrochemistry provenance records for source-data identity, fit windows, input basis, units, and deterministic analysis parameters.
- Generic publication scatter rendering for `Series`/`Dataset`, including stable-key styles and explicit-only x/y error bars.
- Generic single-series/grouped categorical bar rendering with stable category/series keys, optional explicit errors, category overrides, and shared exact-size figure/export behavior.
- Explicit Tafel analysis with caller-supplied fit windows, physical branch plus numeric current-sign declarations, signed slope/intercept/R^2 reporting, immutable provenance-rich results, stable-key Dataset fitting, and shared publication plotting.
- Explicit Faradaic-efficiency analysis for amount/charge and rate/current formulations, immutable signed-denominator results, stable-key multi-product Series/Dataset workflows, total-FE closure QA without clipping/renormalization, and shared scatter/curve publication plotting.
- Product partial-current density analysis from explicit FE and total current density, including signed/magnitude conventions, exact condition-grid validation, stable-key multi-product Dataset workflows, deterministic source provenance, diagnostic closure QA without renormalization, and shared scatter/curve publication plotting.
- Explicit catalyst-mass, metal-mass, and ECSA activity normalization with canonical total-current reconstruction, geometric-area guards, stable-key denominator mappings, double-normalization rejection, provenance-rich results, and shared publication plotting.
- Explicit TOF/TOFapp analysis from product molar rate or product partial current, including active-site versus total/bulk inventory semantics, explicit electron stoichiometry/current mode, exact count-to-mol conversion, stable-key inventory mappings, and denominator-compatible publication plotting.
- CV/Cdl/ECSA analysis with explicit anodic/cathodic sweep pairing, caller-supplied scan rates and analysis potential, exact or bracketed-linear sampling, `Delta j / 2` fitting, explicit current basis, and ECSA conversion only from caller-supplied specific capacitance plus source/basis provenance.
- Electrochemical stability analysis with caller-declared analysis/baseline/final windows, signed or magnitude retention, missing-value policy, linear drift fitting, stable-key Dataset analysis, time-basis compatibility guards, and shared long-term/summary plotting.
- RRDE analysis with explicit collection efficiency, exact disk/ring alignment, explicit current-mode handling, standard ORR-style apparent electron-number/peroxide metrics without hidden clipping, and shared publication plotting.
- Koutecky-Levich analysis with rpm/rps/rad-s canonicalization to angular frequency, free-intercept reciprocal-current regression, explicit total-current versus geometric-current-density basis, transport-constant-explicit apparent electron-number derivation, fit-specific provenance, and shared transformed-data/fit plotting.
- Gate-A installed-wheel smoke coverage for the reviewed v0.2 electrochemistry surface, including complete public `__all__` resolution and representative #21-#28 numerical paths from a fresh wheel installation.

### Changed

- LSV/polarization processing now delegates common low-level quantity parsing and conversion to the shared electrochemistry foundation while preserving the reviewed v0.1 public API and numerical behavior.
- Shared visualization specifications now include categorical style overrides, configurable bar-group width, and error-bar cap size while preserving existing curve-rendering behavior.
- Development version advanced to `0.2.0.dev0` after the tagged `v0.1.0` release and was finalized to `0.2.0` through Gate B.
- The planned v0.2 scientific feature sequence #19-#28 and Gate A/B/C release process are complete; tag `v0.2.0` was created on 2026-08-24 and verified to resolve exactly to release commit `1f7f4057397c61ef2f771b96fceadc8a529b62d9`.

## [0.1.0] - 2026-08-23

The first usable release establishes the common one-dimensional catalysis-data workflow and publication rendering foundation.

### Added

- Immutable-style `Axis`, `Series`, and ordered `Dataset` scientific data models with stable non-display Series keys and deterministic metadata handling.
- Excel, CSV, TXT/TSV/DAT tabular readers with explicit column selection, conservative unit inference, source provenance, and multi-series handling.
- Shared XY processing primitives for crop, offset, normalization, Savitzky-Golay smoothing, interpolation, integration, explicit baseline subtraction, and Dataset mapping.
- LSV/polarization processing with explicit RHE conversion, signed iR correction, geometric current-density normalization, provenance, and publication plotting.
- XRD validation/processing, multi-pattern overlay/stacking, normalization compatibility, peak annotations, reference sticks, and publication plotting.
- Raman validation/processing, multi-spectrum overlay/stacking, direct-window band measurements, explicit ID/IG-style ratios, provenance, and publication plotting.
- Serializable `FigureSpec`, physical figure/axes geometry, editable presets, per-Series style overrides, annotations, deterministic rendering, and exact-size PNG/SVG/PDF export.
- Compact end-to-end LSV, XRD, and Raman examples plus installed-wheel public-API smoke coverage.

### Scientific/API principles

- Scientific transformations are non-mutating and preserve deterministic provenance.
- Units, electrochemical references, normalization bases, branch/sign behavior, and analysis windows are explicit rather than silently inferred when that would change scientific meaning.
- Visualization is separated from scientific processing; domain plot adapters reuse the shared renderer instead of creating independent Matplotlib stacks.
- v0.1 intentionally remains focused on one-dimensional XY workflows. CLI/GUI, N-D operando data, advanced electrochemistry, extended characterization, and DFT post-processing remain roadmap work.

### Release validation

- Release hardening was completed before the version bump.
- The release candidate is required to pass Ruff, the full pytest suite, wheel build/install, `pip check`, exact distribution/runtime version equality, installed public-API smoke checks, and all documented end-to-end examples before the `v0.1.0` tag is created.
- Package-registry publication is not part of this release gate.
