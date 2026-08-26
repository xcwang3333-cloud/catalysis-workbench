# CatalysisWorkbench Roadmap

CatalysisWorkbench is developed in staged releases. The project focuses on quantitative post-processing, comparative analysis, and publication-quality visualization of catalysis data.

Before implementing each major scientific or visualization module, comparable open-source projects should be surveyed and useful algorithms, data-model ideas, visualization patterns, tests, and license constraints recorded in project documentation.

## v0.1.0 — Common XY workflow

- Core `Dataset` / `Series` models.
- Excel / CSV / TXT import.
- Multi-catalyst series handling.
- Crop, normalization, offset, baseline, smoothing, interpolation, integration.
- LSV / polarization-curve processing and plotting.
- XRD processing and multi-sample plotting.
- Raman processing and multi-sample plotting.
- Shared `FigureSpec` / `PlotStyle` model with adjustable figure size, axes geometry/aspect ratio, fonts, line widths/styles, markers, ticks, legends, limits, margins and export settings.
- Publication presets as editable starting templates, not locked themes.
- SVG / PDF / PNG export.

## v0.2.0 — Core electrochemistry — released 2026-08-24

- Tafel analysis.
- Faradaic efficiency.
- Partial current density.
- Mass/specific activity.
- TOF / TOFapp.
- CV / Cdl / ECSA.
- Stability analysis.
- RRDE / Koutecký–Levich basics.
- Installed-wheel public-API and representative numerical smoke coverage for the reviewed v0.2 electrochemistry surface.

## v0.3.0 — Extended experimental processing — released 2026-08-24

- FTIR / ATR-FTIR — implemented and merged through Issue #50 / PR #51.
- TGA / DTG / TPR / TPD — implemented and merged through Issue #54 / PR #55.
- Basic BET / gas-sorption plotting — implemented and merged through Issue #58 / PR #59; quantitative BET fitting was intentionally deferred to v0.4 and is now implemented there.
- ICP/composition data integration — implemented and merged through Issue #62 / PR #63.
- Gate A / Issue #66 / PR #67 completed frozen-scope release hardening while retaining version `0.2.0`.
- Gate B / Issue #68 / PR #69 finalized and exact-wheel validated distribution/runtime version `0.3.0`.
- Gate C / Issue #70 created and reverse-verified tag `v0.3.0` on release commit `845ac4c15d399a8816c7ba66d61ea6ec4cc11293`.
- Package-registry publication was not part of the Git release and remains a separate policy decision.

Shared peak fitting was deliberately deferred from v0.3 so its constraints, uncertainty semantics, provenance, and concrete XPS consumer could be designed together in v0.4.

## v0.4.0 — Advanced experimental analysis — released 2026-08-25

The architecture-first dependency order is maintained in [`V0_4_PLAN.md`](V0_4_PLAN.md), with release evidence in [`V0_4_RELEASING.md`](V0_4_RELEASING.md). All scientific scope, Gate A release hardening, Gate B final-version validation, Gate C tag verification, post-tag documentation synchronization, and GitHub Release publication are complete. Tag `v0.4.0` resolves exactly to release commit `bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6` and reports distribution/runtime version `0.4.0`. Package-registry/PyPI publication is deferred.

1. **Shared constrained peak-fitting foundation — complete through Issue #75 / PR #76.**
   - `lmfit>=1.3.4` reviewed as the BSD-3-Clause runtime fitting backend;
   - stable parameter/component keys and explicit initial/fixed/bounded/tied parameters;
   - Gaussian, Lorentzian, Voigt, pseudo-Voigt, and Doniach initial model families;
   - deterministic fit provenance, physical residuals, fit statistics and optional uncertainty/covariance state;
   - exact-head CI #255 and two formal reviews passed before merge `b6f428d96df9950373c17e5de487ac4113a2aacc`.
2. **XPS data semantics and preparation — complete through Issue #79 / PR #80.**
   - explicit binding-energy/eV semantics and additive energy correction;
   - measured-point-only region preparation, linear background, independently implemented Shirley background;
   - exact-head CI #261 and two formal reviews passed before merge `a13dbd541b299f79d83e47f079c4638b082a8061`.
3. **Constrained XPS peak fitting — complete through Issue #83 / PR #84.**
   - shared-fitter consumer with explicit signed doublet separation and caller-supplied amplitude/shape relations;
   - fail-closed prepared-background alignment and no hidden textbook ratios or chemistry lookup;
   - exact-head CI #267 and two formal reviews passed before merge `7897393e1e1e9e4d23fad774b4eeecdd70e2a90b`.
4. **XPS publication plotting and fit diagnostics — complete through Issue #87 / PR #88.**
   - passive retained-array rendering through `FigureSpec`, optional physical residual panel, display-only binding-energy direction;
   - exact-head CI #274 / run `32741710370` and final-head reviews passed before merge `3eab8c8e936cf1897081b7a396306288e517a3bb`.
5. **EIS semantics, basic equivalent-circuit fitting, and plotting — complete through Issue #91 / PR #92.**
   - explicit frequency/Hz and literal complex-impedance/ohm semantics;
   - ideal R/C/CPE elements with explicit series/parallel topology;
   - SciPy real+imag least-squares objective with retained physical complex residual;
   - passive Nyquist/Bode plotting and fail-closed result reconstruction;
   - final exact-head CI #285 / run `32746265252`, reviews `5009748594` and `5009757335`, merge `cd8dd171a16576067934a13ad3ac41d0fb18d55a`.
6. **Quantitative BET fitting — complete through Issue #95 / PR #96.**
   - caller-visible measured `SorptionWindow`, exact BET transform and independent Rouquerol consistency state;
   - explicit loading-to-mol/g conversion and molecular cross-sectional area;
   - fail-closed preprocessing allowlist and passive retained-array BET plotting;
   - final exact-head CI #294 / run `32752441329`, reviews `5010325152` and `5010328048`, merge `c76a49d64e096d6db001c27c598356baa797f3a9`.
7. **Product calibration / GC-HPLC-NMR-derived quantification — complete through Issue #99 / PR #100.**
   - new technique-agnostic `catalysis_workbench.experimental.product` layer upstream of electrochemical FE;
   - explicit linear calibration with caller-selected free or fixed-zero intercept policy and optional measured-point `CalibrationRange`;
   - retained calibration points, coefficients, physical residuals, R²/uncertainty availability and fail-closed result reconstruction;
   - separate inverse quantification with exact response-unit matching, default extrapolation rejection, explicit ordered positive dimensionless factors and no hidden unit/stoichiometric conversion;
   - explicit replicate mean/sample-SD/RSD summaries and passive `FigureSpec` calibration plotting;
   - raw GC/HPLC/NMR parsing, peak integration/assignment, internal-standard identification and automatic response-factor/model/range inference remain out of scope;
   - final exact head `967d495bba8c8f0102b8b37a6f880f566d776206`, CI #298 / run `32755942830`, reviews `5010636300` and `5010639945`, squash merge `adc0f50178d899b4f257842da6e7bac553a25254`.

Gate A / Issue #103 / PR #104 completed frozen-scope release hardening on exact head `9d79845d6fae253b01a46794c3c055e4966c6e55`, CI #302 / run `32758548117`, reviews `5010905065` and `5010908809`, and squash merge `ce06abc11559fa7679869fc83a59356735ce6824`, while retaining version `0.3.0`.

Gate B / Issue #105 / PR #106 finalized distribution/runtime version `0.4.0`; final head `ae3dc21b1a3a4e907d8c39eb85d3dbebefd8fbb4` passed CI #304 / run `32759679632` and reviews `5011014348`, `5011017132` before squash merge `bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6`. Gate C / Issue #107 then created and reverse-verified `v0.4.0` on that exact commit. The GitHub Release was subsequently published from that existing immutable tag. Package publication remains deferred.

## v0.5.0 — XAS, structures, and basic DFT energetics — released 2026-08-25

The reviewed dependency order and scientific contracts are maintained in [`V0_5_PLAN.md`](V0_5_PLAN.md), with release evidence in [`V0_5_RELEASING.md`](V0_5_RELEASING.md). All eight scientific blocks, completion-state synchronization, Gate A frozen-scope hardening, Gate B final-version exact-wheel validation, Gate C tag verification, GitHub Release publication, and final post-release documentation synchronization are complete. Distribution/runtime version is `0.5.0`. Tag `v0.5.0` resolves exactly to reviewed release commit `9400ac0044ac333d2cae228554c08d955a816a4c`, and the public GitHub Release `CatalysisWorkbench v0.5.0` is published from that existing tag. PyPI/package publication remains deferred.

1. **XAS/XANES — #117 / #118 — complete.**
   - explicit energy/eV semantics, caller-controlled energy shifts, measured-point regions, explicit E0 and pre/post-edge polynomial normalization, positive edge-step validation, retained provenance and passive comparison plotting.
2. **FT-EXAFS — #119 / #120 — complete.**
   - explicit uniform k-grid/transform state, no hidden interpolation, retained complex χ(R), magnitude/real/imaginary/phase views and passive publication plotting.
3. **WT-EXAFS — #121 / #122 — complete.**
   - explicit Cauchy k–R transform, complex WT matrix, retained transform parameters, phase mapping and single-frequency ridge regression evidence.
4. **EXAFS fitting-result summaries — #123 / #124 — complete.**
   - neutral external-fit summary contract preserving path/shell parameters, uncertainty availability and producer-specific diagnostic labels without cross-tool reinterpretation.
5. **Atomic-structure foundation/adapters — #125 / #126 — complete.**
   - immutable CatalysisWorkbench-owned structure state and reviewed POSCAR/CONTCAR/CIF/XYZ adapters using optional `pymatgen-core` support.
6. **Geometry/coordination/comparison — #127 / #129 — complete.**
   - explicit periodic images, exact site distances/angles, caller-bounded cutoff coordination, and explicit site-mapped structure comparison with no hidden MIC/auto-alignment.
7. **Static structure visualization — #130 / #131 — complete.**
   - renderer-neutral immutable `StructureScene`, explicit atom/bond/cell state, presentation-only visual defaults and passive Matplotlib 3D rendering; `pretty-lattice` was architecture/UX reference only.
8. **Basic DFT energetics — #132 / #133 — complete.**
   - immutable explicit eV ledger, same-basis relative energies, generic retained linear combinations, transparent adsorption-energy convention, detached reporting and passive relative-energy plotting.

Release-gate evidence:

- Gate A / #136 / #137: final head `fb13cdbf633366a0840f5f2e21af215bee47b133`, CI #358 / run `32799486710`, reviews `5014277750`, `5014278425`, squash merge `0ffcd7e4a89340d993468039ba83b44bc7638050`, version retained at `0.4.0`.
- Gate B / #138 / #139: final head `b95841ed472aff1fa4d05af7335547ee5c3cd611`, CI #360 / run `32800514038`, reviews `5014348449`, `5014349058`, squash merge `9400ac0044ac333d2cae228554c08d955a816a4c`, distribution/runtime version finalized to `0.5.0`.
- Gate C / #142: tag `v0.5.0` created and reverse-verified exactly on `9400ac0044ac333d2cae228554c08d955a816a4c`; distribution/runtime through the tag is `0.5.0`.
- GitHub Release / #144: `CatalysisWorkbench v0.5.0` publicly published from the existing tag with populated release notes.
- Final post-release documentation synchronization / #143: complete at `bed5c6e750a6066baa8daa21492aa9eb90e8bca8`.

## v0.6.0 — Electronic structure and catalysis thermodynamics — released 2026-08-25

The architecture-first v0.6 scope, scientific semantics, dependency boundaries, prior-art/license decisions, test strategy, and implementation order are frozen in [`V0_6_PLAN.md`](V0_6_PLAN.md), with release evidence in [`V0_6_RELEASING.md`](V0_6_RELEASING.md). All nine scientific blocks, completion-state synchronization, Gate A frozen-scope hardening, Gate B exact-wheel final-version validation, Gate C tag verification, and public GitHub Release publication are complete. Tag `v0.6.0` resolves exactly to reviewed release commit `c7793b309f41d174c14534bd6d4acdacc2a57636`, and distribution/runtime version through the tag is `0.6.0`. The public GitHub Release `CatalysisWorkbench v0.6.0` is published from that existing tag. PyPI/package publication remains deferred.

1. **Electronic-structure + volumetric semantics/adapters — complete through #150 / #151.**
   - CatalysisWorkbench-owned immutable energy/DOS/volumetric state, lazy `pymatgen-core` VASP adapters, explicit source-energy/Fermi/spin/projection semantics, and regression-verified CHGCAR `1/angstrom^3` conversion.
2. **DOS / PDOS processing + passive publication plotting — complete through #154 / #155.**
   - immutable `DOSTrace`, exact retained-channel selection, compatible explicit aggregation, explicit idempotent `E-E_F` referencing, source-grid-only crop, detached reporting, passive `FigureSpec` plotting, renderer-only spin-down mirroring, canonical aggregation provenance, and fail-closed cross-source source-native overlays.
3. **Band-center analysis — complete through #158 / #159.**
   - immutable `BandCenterResult`, explicit retained-grid trapezoidal first moment, caller-selected numeric window and denominator tolerance, auditable numerator/denominator/reference/normalization/projection/spin provenance, and no hidden projection, spin, reference, interpolation, smoothing, broadening or normalization transform.
4. **Bader-result parsing + explicit charge accounting — complete through #162 / #163.**
   - immutable raw and reference-derived Bader state, standard `ACF.dat` parsing, retained source 1-based indices and raw `bader_electrons`, strict direct-order `AtomicStructure` mapping with caller-supplied Cartesian tolerance, explicit `electron_transfer` / `partial_charge` sign conventions from caller-supplied references, and no external partitioner or hidden POTCAR/ZVAL/oxidation-state inference.
5. **COHP / ICOHP parsing + bonding analysis — complete through #166 / #167.**
   - immutable source-sign COHP/ICOHP state, already-Fermi-referenced LOBSTER energy semantics with no double shift, physical total/up/down spin handling, deterministic bond/orbital identities, explicit ICOHP spin sum, exact multiplicity retention, lazy `pymatgen-core` adapters, and no automatic strongest-bond thresholding or chemistry inference.
6. **Geometry–bonding correlations — complete through #170 / #171.**
   - immutable explicit x/y correlation points and datasets with caller-visible source keys/digests and mapping provenance; separate exclusion state; source-sign ICOHP bond-length convenience with explicit spin selection/canonicalization and multiplicity retained only as provenance; no hidden matching, automatic statistics, ranking, or causal interpretation.
7. **CHE / free-energy thermodynamics — complete through #174 / #175.**
   - explicit thermodynamic correction/availability state on top of the reviewed DFT ledger; caller-selected free-energy recipes; explicit SHE/RHE CHE conversion and pH/potential contributions; products-positive/reactants-negative reaction free-energy arithmetic; no hidden thermochemical lookup, chemistry/pathway inference, or plotting.
8. **Free-energy diagrams — complete through #178 / #179.**
   - immutable caller-ordered absolute/reference-relative pathway state with explicit reference, exact thermodynamic/CHE provenance, fail-closed comparison semantics, detached reporting, and passive horizontal-level/straight-connector rendering; no hidden reference, CHE recomputation, transition-state/barrier semantics, or pathway inference.
9. **Charge-density-difference calculation with lattice/grid/component validation — complete through #182 / #183.**
   - immutable explicit combined/reference volumetric state with caller-visible coefficients, common registration identity, exact grid/unit/component checks, direct lattice-tolerance validation, provenance-rich difference state and detached reporting; no hidden interpolation, resampling, alignment, remapping, unit/component conversion, or CHGCAR re-normalization.

Release-gate evidence:

- Gate A / #186 / #187: final head `a72be9f227f92b94df11b40c0bd77bd97933ecdb`, CI #451 / run `32844596642`, reviews `5018578746`, `5018579676`, squash merge `c70481e34f6e3f2bf81724f4a30370fec58c1e7b`, version retained at `0.5.0`.
- Gate B / #188 / #189: final head `4544a464ab54e13408e3db23a68acf565f764328`, CI #453 / run `32845155122`, reviews `5018619904`, `5018620923`, squash merge/reviewed release commit `c7793b309f41d174c14534bd6d4acdacc2a57636`, distribution/runtime version finalized to `0.6.0`.
- Gate C / #192: tag `v0.6.0` created and reverse-verified exactly on `c7793b309f41d174c14534bd6d4acdacc2a57636`; distribution/runtime through the tag is `0.6.0`.
- GitHub Release / #193: `CatalysisWorkbench v0.6.0` publicly published from the existing tag with reviewed release notes.
- Final post-release documentation synchronization / #195 / #196: complete at `fcc8c0ce73953c8d7468a58dcb0c172e520c4202`; it does not alter the release tag or release commit.

Charge-density-difference visualization remains v0.7, and VASP/HPC job management remains outside the current project scope.

## v0.7.0 — Advanced computational visualization — released 2026-08-26

The reviewed v0.7 architecture, scientific/visualization contracts, dependency order, prior-art/license decisions, and testing strategy are frozen in [`V0_7_PLAN.md`](V0_7_PLAN.md). Architecture checkpoint Issue #197 / PR #198 is complete at squash merge `a854b5d4ab6168d857f9f783c9b4c1827e064972`; final head `d15fd0ab0d86901846c46d7cd09837c9dbf8d9d7` passed CI #460 / run `32850343815` and exact-head reviews `5019179196`, `5019180975`. Architecture central-document sync Issue #199 / PR #201 is complete at `7f04e1312a67417ea9b1ddd10482722c599040d4`. Block 1 is complete through Issue #202 / PR #203 at squash merge `4a101337f7822c4d687dd2edf3cc12168278619b`; final head `db0526cfca5b6cc540ac8198b9fd2a02754ba391` passed CI #474 / run `32855491587` and exact-head reviews `5019699984`, `5019702262`. Block-1 completion-state sync Issue #204 / PR #205 is complete at `ff263c20b8986c65a47dfdd544ca712a8e3f3cd8`. Block 2 is complete through Issue #206 / PR #207 at expected-head squash merge `b9e3e27c667df9afc6060e387ad0ca4510a73d78`; final head `c3a952f9aad9535cfc7b2a88413527fd40487cfe` passed CI #486 / run `32862918547` and exact-head reviews `5020510393`, `5020512056`. Block-2 completion-state sync Issue #208 / PR #209 is complete at `bf80f9bb3ffa1d1a764ff71a5202c05e4b5e827e`. Block 3 is complete through Issue #210 / PR #211 at expected-head squash merge `4a4b1329cbd8153f868cdc2d353dfc0c613778a4`; final head `b1f1dca77b469f6d3fb4524f7c51f719fa9350e4` passed CI #490 / run `32867366543` and exact-head reviews `5020939345`, `5020940558`. Block-3 completion-state sync Issue #212 / PR #213 is complete at `fa29a40f465fa41afa7620d1dad9cce22720ee06`. Block 4 is complete through Issue #214 / PR #216 at expected-head squash merge `28852bb7ef6f7c23319d5a6442659f55516eed59`; final head `fef79825073ecb6bf5be834db8bd441c69f99191` passed CI #504 / run `32872508844` and exact-head reviews `5021426413`, `5021427725`. Block-4 completion-state sync Issue #217 / PR #218 is complete at `d1bd5d710f4353b76bf1dd3f3e0a9a49a288353d`. Block 5 is complete through Issue #219 / PR #220 at expected-head squash merge `ab4b8c6f5445920124c2a61799e189ae25b8d404`; final head `34cf2253bf9744149d498edecf186d5fe04e6afe` passed CI #515 / run `32876765592` and exact-head reviews `5021836289`, `5021837599`. Block-5 completion-state sync Issue #221 / PR #222 is complete at `51b04e9b7a63b200c6679d83730e49451f9bee64`. Block 6 is complete through Issue #223 / PR #224 at expected-head squash merge `7a80b99bc513b7a6b33d1a9481ff25c1c4d95b85`; final head `5aa1926e7125c49950589553b8463e5ecfb936fd` passed CI #521 / run `32879644216` and exact-head reviews `5022088404`, `5022089761`. Block-6 completion-state sync Issue #225 / PR #226 is complete at `0e433d55f7d08632e590a9be495cb10128a7a0d6`. Block 7 is complete through Issue #227 / PR #228 at expected-head squash merge `24d3a8e67e4ef996125e575308b88ab6f9532448`; final head `6dc1472b9157151d67b20f8b359542e103d5f6c2` passed CI #526 / run `32882938623` and exact-head reviews `5022437132`, `5022439286`. Issue #229 / PR #230 synchronized scientific completion before Gate A. Gate A #231/#232 completed frozen-scope release hardening; Gate B #233/#234 finalized and exact-wheel validated `0.7.0` at release commit `e3062fc12c794f54c7b7613875ec73608a587a59`; Gate C #237/#238 created and reverse-verified `v0.7.0` on that exact commit. The public GitHub Release was published and its evidence synchronized through #243/#244.

1. **Shared scalar-field state + renderer-neutral volumetric scene/slice/isosurface specifications — complete through #202 / #203.**
   - immutable unit-generic `ScalarField`, exact source-grid `ScalarFieldSlice`, full-lattice fractional/Cartesian grid geometry including skew cells, narrow v0.6 density/difference adapters, explicit renderer-neutral isosurface/slice/scene state, strict compatibility and no hidden normalization/interpolation/resampling/alignment/mesh extraction; reviewed domain contract in [`VOLUMETRIC_VISUALIZATION.md`](VOLUMETRIC_VISUALIZATION.md).
2. **Charge-density-difference + electron-density + ELF visualization — complete through #206 / #207.**
   - explicit signed difference scenes consume the reviewed v0.6 result without repeated arithmetic; total electron-density scenes preserve canonical `1/angstrom^3` state and caller-supplied finite thresholds without hidden transforms; lazy optional ELFCAR parsing returns one dimensionless ELF `ScalarField` per explicit physical channel with current direct-spin semantics and version-guarded historical direct-spin keys; exact source-grid Matplotlib slice rendering retains explicit display ranges and deterministic skew-cell/full-lattice geometry; installed-wheel and real current `pymatgen-core` ELFCAR round-trip audits pass; no PyVista/VTK/scikit-image or other new runtime dependency is added.
3. **Band-structure state/adapters + passive band plotting — complete through #210 / #211.**
   - immutable ordinary band state retains exact ordered reciprocal k-points, full reciprocal matrix and explicit `2*pi` convention, physical spin and source band order, source labels/segments and Fermi/reference state; path distance uses the retained reciprocal matrix literally and excludes discontinuity jumps; explicit idempotent Fermi referencing is separate from parser/renderer; the lazy optional VASP line-mode adapter maps spin from `ISPIN`, reconciles every explicit path point, and fails closed on hybrid-like/SOC/noncollinear ambiguity; passive plotting keeps every band/spin/segment separate with no gap/metallicity/path/band-reconnection inference; reviewed domain contract in [`BAND_STRUCTURE.md`](BAND_STRUCTURE.md); no new runtime dependency is added.
4. **PROCAR projection processing + fat-band plotting — complete through #214 / #216.**
   - immutable projection state is bound to one reviewed Block-3 band source; canonical `(band, kpoint, site, orbital)` weights retain exact physical-spin/site/orbital provenance; explicit aggregation requires caller-selected spin/sites/orbitals and fails closed on spoofed site identity; the lazy current `pymatgen-core.Procar` adapter uses caller-visible k-point/energy tolerances, does not reorder/repair band paths, records the backend's five-decimal k-point behavior and omission of raw terminal `tot`, and rejects SOC/vector ambiguity; passive fat-band scaling is presentation-only and discontinuous segments stay separate; reviewed domain contract in [`PROCAR_FAT_BANDS.md`](PROCAR_FAT_BANDS.md); PyProcar is GPLv3 reference-only and no new runtime dependency is added.
5. **LOCPOT planar-potential/work-function processing + plotting — complete through #219 / #220.**
   - lazy optional `read_locpot_field(...)` preserves one exact finite LOCPOT grid as an eV local-potential `ScalarField` with no CHGCAR-style volume normalization or hidden unit/reference transform; exact planar averaging uses only retained source-grid samples, retains `i/n` coordinates, and computes skew-cell physical normal height from the full lattice as `V_cell / A_opposite_face`; vacuum level requires an explicit half-open retained-index window and no automatic plateau/side inference; Fermi input is explicit and calculation-bound, with the Block-3 convenience using retained `source_fermi_ev`; work function is transparent `Phi = V_vacuum - E_F` under matching `calculation_id`, negative arithmetic is retained, and passive plotting never recomputes scientific state; reviewed domain contract in [`LOCPOT_WORK_FUNCTION.md`](LOCPOT_WORK_FUNCTION.md); current `pymatgen-core.Locpot` round-trip/exact-value/skew-cell smoke passes and no new runtime dependency is added.
6. **NEB/barrier retained state + passive plotting — complete through #223 / #224.**
   - immutable `NEBImageState`, exact ordered `NEBPath`, and explicit `NEBBarrierResult` preserve literal absolute eV/provenance, exact caller/source image order, ordinal or caller-supplied finite reaction coordinates, and only explicit-reference `E_i - E_ref` path energies; barrier arithmetic requires caller-visible retained initial/saddle/final keys and computes only discrete `E_saddle - E_initial` / `E_saddle - E_final`, preserving negative results; passive plotting uses retained coordinates/energies with straight source-order connections and optional saddle highlighting only from an explicitly compatible result; no automatic highest-image saddle selection, spline/smoothing/interpolation, atom correspondence/alignment, IDPP, optimizer/force/HPC semantics, ASE/full-pymatgen dependency, or continuous transition-state inference is introduced; reviewed domain contract in [`NEB_BARRIERS.md`](NEB_BARRIERS.md).
7. **Advanced volumetric 3D backend/rendering/export — complete through #227 / #228.**
   - the renderer-neutral `VolumetricScene` remains authoritative while the heavy PyVista/VTK backend is isolated behind the lazy `volumetric3d` optional extra; full-lattice skew-cell `StructuredGrid` coordinates are constructed from exact source indices with `r=f@L`, scalar ordering is preserved explicitly, and isosurfaces use only retained caller thresholds with contour interpolation treated as presentation mesh geometry; exact retained `ScalarFieldSlice` planes are rendered without backend scientific slicing, full-lattice fractional clipping is explicit and presentation-only, retained `StructureScene`/camera state is used without inferred bonds or alignment, and the public result contains only an immutable screenshot plus digests/backend versions with no PyVista/VTK object leakage; static off-screen PNG export and fresh-wheel headless PyVista/VTK CI are verified; interactive GUI/browser/Jupyter editing, scientific resampling/alignment, automatic thresholds, periodic seam welding/supercell replication, and VASP/HPC execution remain out of scope; reviewed domain contract in [`VOLUMETRIC_3D.md`](VOLUMETRIC_3D.md).

All seven v0.7 implementation blocks, scientific-completion synchronization, Gate A/B/C, tag verification, GitHub Release publication, and publication-evidence synchronization are complete. Post-release Issue #245 / PR #246 added the backwards-compatible `symmetric_color_limits()` maintenance primitive as future v0.8 heatmap groundwork without changing version, tag, release, or package-registry state. Tag `v0.7.0` remains fixed on `e3062fc12c794f54c7b7613875ec73608a587a59`; distribution/runtime release version is `0.7.0`; PyPI remains deferred.

VASP/HPC job submission and complete workflow management remain outside the current project scope.

## v0.8.x — Operando and time-resolved data — architecture frozen; Blocks 1-3 complete

The six-block architecture is frozen in [`V0_8_PLAN.md`](V0_8_PLAN.md) through Issue #249 / PR #250 at `fa7baaf8ce68369b0e732faf4e7621a818db92b6`; post-merge CI #550 / run `32920821932` passed. Block 1 is complete through Issue #253 / PR #254 at expected-head squash merge `45d0515dd5c1c70f15f4d5cd76ba2a359dc66bb2`; final head `eadf5b2e6630b137922f365a88f4b9ef3c43b12b` passed CI #561 / run `32922150384` and formal reviews `5026150379`, `5026170031`, and post-merge main CI #562 / run `32922349620` passed on the merge commit. Block 2 is complete through Issue #257 / PR #258 at expected-head squash merge `86cd463e288eca08c7917945fafbf630493ede92`; final exact head `9fc8e372f15015de1d65705cedd0ad68414613b7` passed CI #580 / run `32925586441`, the review-1 fail-closed result-state blocker was fixed and regression-tested, formal review 2 `5026418909` found no blockers with zero unresolved threads, and post-merge main CI #581 / run `32925811342` passed. Block 3 is complete through Issue #263 / PR #264 at expected-head squash merge `4a5b5ee0f75321dbf3a679ab616ac69972e34575`; final exact head `37c69c18e3e81bd228eadf3c4c2e3b5b8540a8a1` passed CI #594 / run `32927718634`, formal reviews `5026595721`, `5026596493` found no blockers with zero unresolved threads, and post-merge main CI #595 / run `32928011235` passed.

1. **Shared immutable frame-coordinate and operando-stack foundation — complete through #253 / #254.**
   - immutable frame coordinates and exact-grid `OperandoStack` state on top of released core `Axis` / `Series` / `Dataset`;
   - deterministic source/stack digests, reconstruction validation, preserved frame/signal order, increasing/decreasing signal support, explicit primary coordinates, and fresh-wheel public API audit;
   - no interpolation, resampling, alignment, sorting, hidden processing, unit conversion, or automatic coordinate inference.
2. **Exact measured-point operations, derived traces, and explicit cross-modal comparison — complete through #257 / #258.**
   - exact retained-key/index and explicit coordinate-comparison frame selection without sorting or automatic coordinate choice;
   - measured-point signal cropping plus exact frame/signal-position cuts with no synthesized values or nearest-neighbor lookup;
   - immutable derived traces, fail-closed exact trace pairing, and explicit ordinary Pearson correlation with retained coefficient, two-sided p-value, paired values, and provenance.
3. **Passive waterfall, heatmap, cut, and trace visualization — complete through #263 / #264.**
   - exact retained frames/matrices/traces are rendered without scientific recalculation; waterfall offsets and axis reversal are display-only; ordinal heatmaps preserve repeated/non-monotonic selected coordinates in retained order, while coordinate heatmaps require unique strictly monotonic retained coordinates and fail closed rather than sorting/deduplicating; explicit value limits/colormap and optional caller-requested `symmetric_color_limits()` preserve the no-hidden-range contract; fresh-wheel Block-3 and exact-size export coverage are verified.
4. Operando Raman and FTIR adapters with caller-specified band/peak trajectories.
5. Operando XAS/XANES adapters, mapping, and explicit descriptor trajectories.
6. Operando XRD adapters, mapping, and caller-window/peak trajectories.

The frozen contract requires literal common grids, explicit coordinates/units/provenance, retained acquisition order, passive renderers, and fail-closed incompatibility. It performs no hidden alignment, interpolation, smoothing, baseline correction, normalization, chemical assignment, XAS species inference, XRD phase inference, or causal interpretation. Block 4 — operando Raman and FTIR adapters with caller-specified band/peak trajectories — is the next implementation work package.

## v0.9.x — Reproducible and interactive workflows

- Batch processing.
- Publication figure presets.
- Reusable analysis recipes.
- Scientific QA checks.
- Processing metadata and reproducibility records.
- First interactive plot editor prototype using the existing `FigureSpec` model for immediate redraw when style/layout parameters change.

## v1.0.0 — Personal catalysis data workbench

- Stable Python API.
- Project workspace for processed experimental, characterization, and computational data.
- Local GUI with file import, parameter controls, real-time figure preview, style-template selection, per-parameter override, and export.
- Real-time controls should include font size, line width/style, marker symbol/size, axis dimensions/aspect ratio, margins, ticks, legends, limits and related publication parameters without changing the scientific analysis pipeline.

## Explicitly out of scope

- Synthesis management and electronic laboratory notebooks.
- TEM/SEM image processing and STEM atom recognition.
- Instrument control.
- Full Rietveld refinement engine.
- Full Artemis-class EXAFS fitting engine.
- HPC job submission or complete VASP workflow management.
