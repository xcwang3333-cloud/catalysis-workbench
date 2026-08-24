# Changelog

All notable changes to CatalysisWorkbench are recorded here.

## [Unreleased]

### Added

- First v0.3 FTIR/ATR-FTIR workflow with explicit wavenumber and absorbance/transmittance semantics, explicit `A = -log10(T)` conversion, caller-window polynomial baseline fitting, direction-independent direct-window band integration, stable-key Dataset processing, shared publication plotting, deterministic provenance, installed-wheel smoke, and compact quickstart documentation.
- Reviewed TGA / DTG / TPR / TPD thermal-analysis foundation with explicit °C/K temperature semantics and conversion, raw-mass versus normalized TGA bases, explicit reference-mass normalization, measured-grid `numpy.gradient` DTG with caller-selected sign convention, TPR/TPD detector-signal semantics, measured-point-supported direct thermal-window extrema/integration, stable-key Dataset processing, compatibility guards, deterministic provenance, lazy shared publication plotting, installed-wheel thermal smoke, and compact quickstart documentation.
- Reviewed basic gas-sorption isotherm foundation with explicit `P/P0` fraction/percent semantics, explicit adsorbed-quantity units, caller-declared adsorbate/measurement temperature/adsorption-desorption branch, explicit standard-gas conditions for `cm^3(STP)/g`, branch-direction independence, stable-key Dataset processing, measured-point-only pressure-window summaries, strict overlay compatibility, lazy shared publication plotting, installed-wheel smoke, and compact quickstart documentation; quantitative BET/Rouquerol/pore-size fitting remains deferred.

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
