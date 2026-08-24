# Open-source reference survey

CatalysisWorkbench should not reimplement mature scientific algorithms or visualization ideas without first surveying existing open-source work.

## Development rule

Before implementing a scientific or visualization module:

1. Search GitHub and the relevant scientific Python ecosystem for comparable projects.
2. Inspect the data model, numerical methods, validation strategy, plotting/interaction design, tests, and documentation.
3. Record useful ideas here, including the upstream license.
4. Prefer depending on a mature library when it provides a reliable scientific implementation.
5. If adapting code, preserve required attribution/license notices and add focused tests against known results.
6. Do not copy implementation merely because a similar project exists; keep CatalysisWorkbench's scope centered on catalysis post-processing, cross-sample comparison, and SCI figures.

## Initial reference set

| Area | Project | Why it is relevant | Initial use in CatalysisWorkbench |
| --- | --- | --- | --- |
| Crystal visualization | `songfeitong/pretty-lattice` | Publication-oriented local browser GUI; attractive material/color defaults; adjustable colors, radii, materials, opacity, orientation and export; separates mature structure parsing from rendering. Uses pymatgen for structure handling and a browser 3D renderer. | Major UX/architecture reference for the later structure viewer. Study scene/data contracts, connectivity/periodic-image handling, presets and real-time visual controls. Do not couple core DFT analysis to the renderer. |
| Scientific figure styles | `garrettj403/SciencePlots` | Reusable Matplotlib scientific style sheets and publication-oriented defaults. | Reference for preset organization. CatalysisWorkbench presets remain editable rather than being fixed final styles. |
| Baseline correction | `derb12/pybaselines` | Dedicated baseline-correction algorithms for spectroscopy/materials data. BSD-3-Clause licensed. | Prefer a dependency/adapter for validated general spectroscopy baseline methods instead of rewriting complex algorithms; do not assume it supplies XPS-specific Shirley/Tougaard backgrounds. |
| Curve fitting | `lmfit/lmfit-py` | Flexible constrained nonlinear least-squares fitting on top of SciPy. BSD-3-Clause verified from upstream LICENSE. | Preferred backend candidate for v0.4 shared constrained peak fitting, parameter ties/bounds, spectroscopy components and uncertainty reporting; CatalysisWorkbench should wrap scientific contracts/provenance rather than reimplement optimization. |
| Electrochemical experimental data | `ixdat/ixdat` | In-situ experimental data architecture and electrochemistry-oriented scientific data handling. `DataSeries` wraps NumPy data together with unit/axis context and higher-level fields reference explicit axes. MIT licensed. | Core-model reference for keeping numerical values attached to scientific metadata while avoiding ixdat's database/persistence layer. Also relevant to future time/potential-resolved workflows. |
| Labeled scientific arrays | `pydata/xarray` | General labeled N-D arrays and datasets. Xarray explicitly separates raw NumPy-like values from dimensions, coordinates and arbitrary attributes, and uses a Dataset as a container for labeled arrays. Apache-2.0 licensed. | Conceptual reference for labels/metadata and Dataset semantics. Do not add xarray as a v0.1 dependency; CatalysisWorkbench starts with a deliberately lightweight 1-D XY model and can add adapters later if N-D operando data justify it. |
| Tabular I/O | `pandas-dev/pandas` | Mature CSV and Excel parsers with explicit sheet, header, selected-column, missing-value, delimiter, and dtype controls. BSD-3-Clause licensed. | Use pandas as the parsing backend rather than rebuilding CSV/Excel parsing. CatalysisWorkbench adds the catalysis-specific conversion into `Axis`/`Series`/`Dataset`, source metadata, validation, and deterministic keys. |
| Scientific reader patterns | `ixdat/ixdat` readers | Dedicated format readers keep parsing separate from scientific objects; the CSV reader retains header/column/unit context, while the XRD XY reader performs conservative header/comment detection and leaves domain data in explicit series/fields. MIT licensed. | Follow the parser-adapter pattern: parse file structure first, then construct standard core objects. Avoid silently skipping malformed selected values; CatalysisWorkbench raises explicit validation errors for user-selected scientific columns. |
| Electrochemical impedance | `ECSHackWeek/impedance.py` | Mature electrochemical-impedance workflow/circuit-fitting package; current GitHub repository metadata reports the MIT License. | v0.4 EIS workflow/API/test reference only; no implementation is copied and the package is not added as a dependency. |
| Electrochemical impedance | `vyrjana/pyimpspec` | Rich impedance parsing, validation, circuit analysis/simulation, and plotting; current GitHub repository metadata reports GPL-3.0. | Architecture/validation reference only for v0.4 EIS. No GPL implementation is copied/adapted and no dependency is added. |
| XAS | `xraypy/xraylarch` | Mature X-ray spectroscopy/XAS processing ecosystem. | Reference/dependency candidate for XANES/EXAFS algorithms; CatalysisWorkbench should emphasize comparison, result integration and publication figures rather than replace the mature XAS stack. |
| Electronic structure | `romerogroup/pyprocar` | Electronic-structure parsing/visualization, including projected electronic data. | Reference for DOS/PDOS parsing and projection-selection concepts in v0.6. |
| Chemical bonding | `JaGeo/LobsterPy` | Analysis of LOBSTER bonding output. | Reference/dependency candidate for COHP/ICOHP parsing and bonding analysis in v0.6. |
| Matplotlib extensions | `nschloe/matplotx` | Small composable style/palette extensions on Matplotlib. MIT licensed. | Architectural reference only for v0.1: keep extensions narrow and composable; do not add an extra plotting dependency for capabilities already represented in `FigureSpec`. |

## Core data-model decision for v0.1

The first core model follows a deliberately narrow contract:

- `Axis`: semantic axis name, optional semantic label, unit string and lightweight metadata. Final rendered forms such as `Potential (V)` or `Potential / V` belong to the visualization layer rather than the core model.
- `Series`: one numerical `y(x)` trace plus its two axes, display label, optional stable non-display key, and metadata. `key` is keyword-only so introducing it does not disturb the pre-existing positional constructor order for axes and metadata.
- `Dataset`: ordered collection of `Series` objects; it also serves the multi-catalyst collection role in v0.1, so a separate `SeriesCollection` type is intentionally avoided.
- Scientific x/y arrays are detached from caller-owned memory and stored on immutable byte-backed NumPy arrays. The WRITEABLE flag therefore cannot be re-enabled by callers, and processing functions must return new objects instead of mutating source data in place.
- Real numeric input is normalized to float64; complex numeric input is preserved as complex128 so future EIS data are not silently truncated.
- Duplicate series labels are allowed so replicate measurements of the same catalyst can coexist.
- Non-empty `Series.key` values must be unique within a `Dataset`, allowing later GUI/style controls to address repeated labels independently.
- NaN is preserved as explicit missing data for later cleaning policies; malformed arrays and +/-inf are rejected.
- Units are explicit strings in v0.1. General unit arithmetic/conversion is not part of the core; domain-specific conversions belong in analysis modules.

This takes the useful metadata-coupling idea from ixdat and the label/attribute separation idea from xarray without importing either project's full object model.

## Tabular reader decision for v0.1

The first reader layer uses pandas as a backend and adds a deliberately small scientific contract:

- `read_csv`, `read_txt`, `read_excel`, and extension-dispatching `read_tabular` return core `Dataset` objects directly.
- x/y columns can be selected by exact header or zero-based position; several y columns can share one x column for multi-catalyst comparison.
- Excel integer sheet selectors are resolved to canonical sheet names before keys/metadata are generated, so keys are independent of whether the user selected `1` or `"Sheet2"`.
- Reader-generated keys use a source identity, canonical sheet name, and x/y column positions. By default the source identity is the normalized source path so same-named files in different folders do not collide when datasets are combined. Users can provide an explicit `source_id` for portable project-level identifiers.
- Units are conservatively inferred only from trailing square brackets such as `Potential [V]`; users can override units, axis labels, axis names, and series labels explicitly.
- Selected non-numeric cells raise `TabularReadError` instead of being silently discarded. Explicit missing values remain NaN for later cleaning policy.
- Duplicate y-column selection and zero-sheet Excel selection are rejected explicitly in the reader layer.
- Reader source metadata records source id/path, filename, sheet, column headers, and column positions without introducing sample-registry or experiment-management concepts.

This keeps the I/O layer format-oriented and leaves LSV/XRD/Raman semantics to their later domain modules.

## Visualization design principle

Publication presets are **starting templates**, not locked themes. From the first plotting API, visual parameters are represented explicitly in a `FigureSpec` / `PlotStyle` model so the same scientific data can later be redrawn interactively without changing analysis code.

The v0.1 shared renderer follows these reviewed rules:

- whole-figure physical size and axes drawing-region size are separate `LayoutSpec` concerns;
- `FigureSpec` and nested specs are immutable and dictionary-serializable for future GUI state;
- generic presets (`publication`, `compact`, `wide`) are editable starting points rather than hidden global styles;
- rendering starts from Matplotlib defaults inside a local `rc_context`, then applies explicit `FigureSpec` settings, so unrelated ambient rcParams such as grids or axes face colors do not alter the result and are restored afterwards;
- multi-Series overlays require matching axis names/units and matching compatibility-critical axis metadata for `reference` and `normalization`; provenance-only metadata such as `source_reference` and `electrode_area_cm2` may differ when the final physical basis is compatible;
- complex curves are rejected by the generic 2-D renderer instead of silently dropping an imaginary component;
- `None` means automatic axis-label generation, while an explicit empty label suppresses rendering of that axis label;
- stable `Series.key` values, not display labels, address per-Series visual overrides;
- exact-size export avoids `bbox_inches="tight"`; PNG uses explicit DPI, while SVG/PDF preserve vector artists and configured font embedding;
- export settings are applied without closing the figure, leaking global rc state, or permanently changing a live figure's preview size; if the complete layout recipe changes, callers should rerender through the same renderer before export.

Parameters that remain user-adjustable include figure/axes dimensions, margins, typography, line/marker settings, spines, ticks, legend settings, limits/scales, annotations, and export DPI/font behavior. A later local GUI (target v0.9-v1.0) should bind controls directly to the same specification objects and request deterministic redraws.

## Structure-visualization note

`pretty-lattice` is particularly relevant to the desired structure-figure experience. Its useful high-level choices include:

- keep structure analysis/parsing separate from visual styling;
- rely on a mature structure library instead of rebuilding crystallographic parsing;
- construct an intermediate scene representation between structure data and the renderer;
- provide attractive defaults but expose fine-grained atom/bond/material controls;
- make preview and export part of the same rendering model while keeping output dimensions independent from the interactive viewport.

CatalysisWorkbench should follow these principles while preserving its own role: DFT/geometry analysis lives in the computation layer, while publication-oriented structure rendering lives in the visualization layer.

## XY processing decision for v0.1

The shared processing layer deliberately wraps mature numerical primitives instead of reimplementing them.

- `scipy/scipy` (BSD-3-Clause) is the backend for Savitzky-Golay filtering. CatalysisWorkbench exposes explicit window length, polynomial order, edge mode and constant-padding value, and filters real/imaginary components separately for complex data so SciPy's float conversion cannot silently discard an EIS-like imaginary component.
- `numpy/numpy` supplies linear interpolation and trapezoidal integration primitives. CatalysisWorkbench adds stricter scientific guards around source-axis monotonicity, duplicate x values, missing data and extrapolation.
- `derb12/pybaselines` (BSD-3-Clause) is the preferred later backend for baseline estimation. Its 50+ algorithms include literature-based AsLS, airPLS, ModPoly, SNIP and related methods across Raman, FTIR, XRD and other experimental techniques. v0.1 therefore implements only explicit baseline subtraction and does not clone baseline-estimation algorithms.
- `lmfit/lmfit-py` remains relevant to later constrained peak fitting but is not needed for crop/normalize/offset/smoothing/interpolation/integration primitives.

Processing semantics are kept deterministic and non-mutating:

- every Series-to-Series operation preserves axes, stable key and existing source metadata;
- an ordered `processing_history` record stores operation names and user-controlled parameters without timestamps;
- missing y values are not silently dropped; algorithms that cannot safely propagate them raise a processing error;
- interpolation does not extrapolate in v0.1; both source and multi-point target grids must be strictly monotonic, while increasing and decreasing order are both supported;
- `normalize(method="max")` requires a positive maximum; non-positive or complex traces use explicit alternatives such as `max_abs` rather than silently flipping sign;
- area normalization records an explicit `area_mode`: `absolute` (default) scales by the positive trapezoidal integral of `abs(y)`, while `net` scales by the magnitude of the net signed/complex integral and can expose cancellation;
- integration is signed/complex by default; `absolute=True` means positive absolute area `integral(abs(y), x)`, not merely `abs(integral(y, x))`;
- baseline subtraction using another `Series` requires the same x grid and matching x/y axis names and units, preventing silent subtraction across incompatible physical quantities;
- integration results carry point count, x orientation, axis names/units and a deterministic source-data SHA-256 in addition to optional key/label provenance;
- interpolation grids and array/Series baselines are represented in provenance by deterministic SHA-256 digests while transformed Series retain the actual numerical data.

## LSV / polarization processing and plotting decision for v0.1

`ixdat/ixdat` (MIT) is the main architecture and equation reference for the first electrochemistry layer. Its `ECCalibration` stores reference-electrode offset, electrode area, and uncompensated resistance explicitly. The calibrated potential adds the reference-to-RHE offset, ohmic correction subtracts signed current times resistance, and current normalization divides total current by electrode area. CatalysisWorkbench adopts those transparent numerical semantics while keeping a lighter stateless post-processing API.

The reviewed v0.1 LSV contract is deliberately explicit:

- an LSV trace is a normal core `Series` whose canonical x axis is `potential` and whose y axis is `current` or `current_density`;
- RHE conversion uses an explicit additive `offset_v`; a helper derives that offset from a user-supplied reference potential versus SHE, pH, and temperature using the Nernst pH term, while v0.1 intentionally has no embedded reference-electrode lookup table;
- ohmic-drop correction is `E_corrected = E - fraction * I * R` using signed **total current in amperes**; current-density input requires an explicit geometric electrode area before Ohm's law is applied;
- current-density normalization uses explicit geometric area in cm^2 and refuses double normalization; library-generated density records the area so a later iR reconstruction cannot silently use a different electrode area;
- repeated/contradictory RHE conversion and repeated iR correction fail explicitly; source-reference declarations must agree with axis metadata;
- known non-geometric current-density normalization such as ECSA normalization is rejected when geometric-area reconstruction is required;
- only common V/mV, A/mA/uA, and corresponding per-cm^2 units are interpreted by the processing layer. Missing or unsupported units fail instead of being guessed;
- electrochemical transformations are non-mutating, preserve stable keys/source metadata, update changed axis semantics, and append deterministic `echem.*` entries to the shared `processing_history`;
- `LSVProcessingConfig` records the correction/normalization recipe, and Dataset processing can apply stable-key-specific overrides for catalysts measured under different resistance/area/reference conditions;
- publication rendering is a thin adapter over the shared visualization engine rather than a second electrochemistry-specific Matplotlib stack. `plot_lsv()` performs no numerical correction, smoothing, resampling, or sign inversion; it validates canonical LSV axis semantics, adds reference metadata such as RHE to automatic potential labels, and delegates artists/layout/export behavior to `FigureSpec` and `render_curves`;
- importing the numerical `experimental.echem` API keeps visualization/Matplotlib lazy; the plotting dependency is imported only when `plot_lsv()` is actually called;
- multi-catalyst LSV plots inherit the shared renderer's compatibility guards, so equal units are not enough to overlay incompatible electrochemical references or current-density normalization bases.

## Shared electrochemistry quantity/provenance decision for v0.2

Issue #19 establishes one reusable numerical and provenance foundation before Tafel, FE, partial-current, activity, TOF, CV/ECSA, stability, RRDE and Koutecky-Levich modules are added.

Prior-art review for this layer:

- `ixdat/ixdat` (MIT) remains the main electrochemistry architecture reference. Its object-oriented model combines numerical arrays with unit/axis context and explicit electrochemical calibration state. CatalysisWorkbench retains the useful principles—scientific values stay attached to explicit units/references and calibration quantities stay explicit—but does not adopt ixdat's relational database/persistence model for this lightweight post-processing layer.
- `ECSHackWeek/impedance.py` (MIT) separates preprocessing, validation, model fitting and visualization behind a consistent scientific API. Its validation/fitting code is a useful reference for failing explicitly on invalid scientific inputs and for keeping fit choices visible. Issue #19 does not copy EIS algorithms or add `impedance.py` as a dependency.
- `ScottSoren/EC_MS` (MIT) is prior art for broad electrochemistry plus mass-spectrometry analysis and explicitly identifies ixdat as its successor. It informs scope/history only; no implementation is copied and no dependency is added.
- `echemdata/galvani` (GPL-3.0-or-later) is focused on reading proprietary electrochemical instrument formats. It is useful reader prior art but its copyleft license and reader-centric scope make it inappropriate as a shared quantity/provenance dependency here; no implementation is copied.

The v0.2 foundation therefore uses the following reviewed direction:

- units remain explicit strings; Pint/general dimensional algebra stays deferred until a concrete workflow justifies it;
- one conservative conversion layer owns supported electrochemical unit aliases and converts into canonical calculation bases: V, A, A/cm^2, C, s, V/s, cm^2, g, g/cm^2, mol, mol/s and rad/s;
- supported aliases are deliberately narrow and deterministic. Missing or unsupported units fail rather than being guessed, and numerical conversion never flips current sign;
- reference-electrode names are explicit caller metadata. Only whitespace/case normalization for comparison is provided; there is no built-in Ag/AgCl/SCE/reference-potential lookup table;
- electron stoichiometry is an explicit positive integer input. Product labels never imply an electron number;
- reusable `SourceDataRef`, `FitWindow` and `AnalysisProvenance` frozen dataclasses define how later result objects retain source key/label, numerical SHA-256, axis names/units, explicit fit range/point count, input basis, units and deterministic scalar parameters;
- the source digest hashes immutable numerical x/y data, while scientific axis semantics are retained separately in `SourceDataRef`; this makes data changes detectable without pretending that a byte digest itself represents electrochemical semantics;
- provenance mappings are restricted to deterministic scalar values and sorted keys in this foundation. Larger arrays or nested analysis products belong in explicit result fields rather than opaque metadata blobs;
- `Series`/`Dataset` remain the scientific data containers. Issue #19 does not introduce a global N-D/table/database core model;
- the existing reviewed LSV public API remains source-compatible. Its low-level potential/current/current-density conversions are delegated to the new shared foundation while `LSVError` and the existing transform semantics remain intact.

## Tafel analysis decision for v0.2

Issue #21 surveys focused Tafel implementations before adding its own electrochemical semantics and provenance contract.

- `ixdat/ixdat` (MIT) remains the architectural reference for explicit electrochemical calibration/reference state. Tafel fitting in CatalysisWorkbench therefore requires an explicit potential reference and current-density normalization basis rather than treating axis numbers as context-free values.
- `NordicEC/EC4py` (MIT) is practical electrochemistry post-processing prior art and includes Tafel-slope extraction in its analysis scope. It is used as workflow/API reference only; CatalysisWorkbench keeps its existing immutable `Series` and `AnalysisProvenance` contracts and copies no implementation code.
- PyPI `tafel` by Koki Muraoka (MIT, experimental) is a dedicated tool for extracting Tafel slopes from xy/CSV/BioLogic inputs. It confirms the usefulness of a focused explicit Tafel workflow, but its file/CLI assumptions are not adopted and no implementation code is copied.
- `scipy/scipy` (BSD-3-Clause) provides the mature `scipy.stats.linregress` kernel used for the actual linear regression. CatalysisWorkbench does not reimplement least squares/statistics; it owns the electrochemical validation, unit conversion, explicit fit-window/sign policy, provenance, immutable result object, Dataset orchestration, and publication adapter around SciPy.

The resulting v0.2 Tafel policy is conservative: fit windows are caller-supplied, physical branch and numeric current sign are separate explicit declarations, the logarithm uses positive current-density magnitude after unit conversion, signed slope is retained, and no mechanism or rate-determining step is inferred automatically from a slope value. Full details are in `docs/TAFEL.md`.

## Activity-normalization decision for v0.2

Issue #24 surveys both reusable electrochemistry architectures and practical laboratory scripts before defining mass- and ECSA-normalized activity semantics.

- `ixdat/ixdat` (MIT) is the principal architecture reference for explicit electrochemical calibration state. The useful principle is that area and other calibration quantities are explicit state attached to a scientific transformation rather than inferred from labels. Issue #24 adopts that principle without adding ixdat as a dependency.
- `MyPyDavid/elchempy` (MIT) is useful architecture prior art because ORR analysis, RDE/RRDE submodules, plotting, and tests are separated. CatalysisWorkbench similarly keeps numerical normalization independent from publication rendering and does not infer denominator state from workflow conventions.
- `gcarrascohuertas/electrochemical_ORR_procesing_autolab` (GPL-3.0) is practical ORR reference-only prior art. Its script-level geometric electrode-area constant illustrates an approach CatalysisWorkbench deliberately avoids: scientific denominators and reconstruction areas must be caller-visible validated inputs, not hard-coded globals. No GPL code is copied or adapted.
- `gcarrascohuertas/electrochemical_ECSA_processing_autolab` (GPL-3.0) treats ECSA determination as a dedicated workflow. This supports the Issue #24/#26 boundary: #24 consumes an explicitly supplied ECSA denominator; CV/Cdl/ECSA derivation remains #26. No GPL code is copied or adapted.
- `emmo-repo/domain-sofc` (CC-BY-4.0) is terminology prior art showing that "specific activity" can be defined against different denominator bases. CatalysisWorkbench therefore treats bare `specific_activity` terminology as scientifically insufficient and records denominator basis explicitly.

The resulting Issue #24 direction is:

- built-in denominator bases are limited to `catalyst_mass`, `metal_mass`, and `ecsa`;
- catalyst mass and metal mass remain distinct semantic bases even though both have mass dimensions and may share output units;
- total current is the canonical numerator; geometric current density must be reconstructed with an explicit compatible geometric area before mass/ECSA normalization;
- signed current is preserved unless magnitude mode is explicitly requested;
- already mass-, metal-mass-, ECSA-, or otherwise non-geometrically normalized current is rejected before division;
- Dataset denominator mappings use stable `Series.key` values only;
- denominator basis is compatibility-critical metadata, while denominator numerical value remains provenance rather than an overlay incompatibility by itself;
- BET-specific-surface-area and arbitrary composite denominator units are deferred until their physical dimensions and conversion semantics are explicitly designed;
- plotting receives already normalized data and performs no denominator lookup, condition selection, interpolation, or aggregation.

Full scientific/API/test details are in `docs/ACTIVITY_NORMALIZATION.md`.

## FTIR / ATR-FTIR decision for v0.3

Issue #50 begins v0.3 with explicit one-dimensional FTIR/ATR-FTIR processing and publication plotting.

- `spectrochempy/spectrochempy` (CeCILL-B) is the main spectroscopy architecture reference: unit/coordinate-aware datasets, explicit baseline processors, separation of processing from plotting, and provenance-rich data state. Because CeCILL-B is not treated as the source license for this module, CatalysisWorkbench uses architecture/API ideas only and copies no implementation.
- `derb12/pybaselines` (BSD-3-Clause) is mature baseline-correction prior art with a unified API across many algorithms. It is a permissive future dependency/adapter candidate, but Issue #50 deliberately does not silently select AsLS, airPLS, SNIP, rubber-band, or any other automatic method.
- `uw-ssec/ProSpecPy` (BSD-3-Clause) is workflow prior art for modular FTIR processing and batch/per-sample configuration. CatalysisWorkbench adopts the principle of explicit reusable operations and stable-key overrides without copying implementation.
- RamPy (`charlesll/rampy`, GPL-2.0) provides useful spectroscopy workflow ideas including explicit baseline regions and stacking/resampling/smoothing. It is reference-only; no GPL implementation is copied or adapted.
- `JRay-Lin/SpectraLab` (MIT) is UI/data-state prior art for keeping raw, baseline, corrected data and baseline parameters explicit. Issue #50 uses that state-separation idea only; no GUI code is introduced.

The reviewed FTIR direction is conservative: wavenumber units and absorbance/transmittance semantics are explicit; source order may be ascending or descending but is never silently reversed; transmittance conversion is an explicit `A = -log10(T)` operation; baseline fitting uses only caller-supplied windows and an explicit polynomial degree; band integration is low-to-high wavenumber and independent of storage direction; missing values that affect interpolation fail explicitly; plotting preserves the shared `FigureSpec` label/limit contract while allowing explicit FTIR display direction. Peak deconvolution, automatic baseline selection, atmospheric correction, vendor-binary readers, 2-D maps, and GUI work remain out of scope for Issue #50.

Full scientific/API/test details are in `docs/FTIR.md`.

## TGA / DTG / TPR / TPD thermal-analysis decision for v0.3

Issue #54 extends v0.3 with a conservative one-dimensional thermal-analysis foundation before BET/sorption, composition integration, or shared peak fitting.

- `MyonicS/pyTGA` (MIT) is the principal Python TGA workflow reference. Its explicit temperature/weight/time columns, staged experiment model, multi-manufacturer parser tests, quick plotting, and example data demonstrate useful separation between parsing and thermal processing. CatalysisWorkbench keeps its existing `Series`/`Dataset` model and generic tabular I/O; vendor-specific PerkinElmer, Mettler Toledo, Netzsch, and TA readers are deferred.
- `mayankskii/TGAnalysis` (MIT, MATLAB) is scope prior art covering TGA/DTG alongside later deconvolution and kinetic methods such as Coats–Redfern, Friedman, FWO, and KAS. It is used only to define the foundation/advanced-analysis boundary; no MATLAB implementation is copied.
- `lukasbaldauf/tga-kinetics` (MIT) is equation/workflow prior art for explicit `-dm/dt`, time/temperature/mass inputs, finite-difference rate handling, simulated test datasets, and sensitivity of kinetic fits to model/initial conditions. Issue #54 therefore makes DTG sign convention explicit but deliberately excludes kinetic parameter estimation.
- `Danilosauro/thermogravimetric-analysis` had no repository license detected during the survey. Its batch-treatment and automated-plotting ideas are reference-only; no code is reused.
- `numpy/numpy` (BSD-3-Clause), already a dependency, supplies `numpy.gradient` as the numerical derivative kernel on a measured strictly monotonic temperature grid. CatalysisWorkbench owns the temperature/mass semantics, unit validation, explicit DTG sign mode, source-direction handling, provenance, failure policy, and hand-verifiable regression tests around that kernel.

The reviewed direction keeps temperature conversion explicit (`°C`/K), never silently normalizes raw TGA mass, defines DTG as caller-selected signed `dy/dT` or positive mass-loss `-dy/dT`, treats TPR/TPD initially as calibrated-or-uncalibrated detector signals without inferring chemical amount, and limits direct feature quantification to explicit temperature windows with maximum/minimum selection plus net/absolute area. Window interpolation is restricted to the two requested boundaries and fails on missing bracketing data. Automatic peak detection, onset extrapolation, deconvolution, kinetic fitting, smoothing/baseline correction, vendor readers, and TPR/TPD calibration-to-amount remain outside Issue #54.

Full scientific/API/test details are in `docs/THERMAL_ANALYSIS.md`.

## Basic gas-sorption isotherm decision for v0.3

Issue #58 adds a conservative measured-isotherm foundation before any BET surface-area or pore-structure fitting.

- `pauliacomi/pyGAPS` (MIT) is the primary adsorption architecture/scientific reference. Its explicit pressure mode/unit, loading basis/unit, material basis/unit, adsorbate, temperature, point-isotherm representation, and adsorption/desorption-aware plotting are useful design prior art. CatalysisWorkbench keeps its existing `Series`/`Dataset` model instead of introducing a second isotherm hierarchy. pyGAPS can infer branch from pressure direction; Issue #58 deliberately rejects that behavior and requires caller-declared branch metadata.
- `hjkgrp/SESAMI_web` (MIT) is workflow/scope prior art demonstrating that BET region selection and surface-area determination require nontrivial consistency/linearity criteria and are a separate quantitative analysis problem. Issue #58 therefore does not hide BET fitting inside plotting or basic data preparation.
- `AIF-development-team/adsorptioninformationformat` (MIT) is interoperability/metadata prior art. It reinforces the need for explicit adsorbate, measurement conditions, pressure representation, and loading units. AIF and vendor-specific parser expansion are deferred.
- `nakulrampal/betsi-gui` reports a non-standard/`NOASSERTION` license in GitHub repository metadata. Its dedicated Rouquerol/BET workflow is useful scope reference only; no implementation is copied or adapted.

The reviewed v0.3 direction keeps `P/P0` explicit as fraction or percent, rejects the inverse `P0/P` as an alias, preserves ascending or descending measured branch order without branch inference, requires explicit loading units and standard-gas temperature/pressure for `cm^3(STP)/g`, addresses Dataset operations by stable `Series.key`, and permits only model-free measured-point summaries plus shared-renderer publication plotting. There is no hidden sorting, interpolation, alignment, clipping, smoothing, normalization, or unit conversion. BET linear-region selection, Rouquerol criteria, monolayer capacity, surface area, pore volume, pore-size distributions, t-plot/alpha-s/Dubinin/model fitting, hysteresis classification, and parser expansion remain outside Issue #58.

No upstream implementation code is copied and no new dependency is introduced. Full scientific/API/test details are in `docs/GAS_SORPTION.md`.

## ICP / elemental-composition integration decision for v0.3

Issue #62 adds a conservative scalar composition layer for reported ICP-OES/ICP-MS-style results, explicit digestion/dilution mass balance, replicate summaries, tidy tabular import, and publication bars.

- `oscarbranson/latools` (MIT) is the principal ICP data-reduction architecture reference. It demonstrates analyte-aware processing, explicit standards/reference-material state, retained uncertainty information, and traceable reduction steps rather than opaque spreadsheet-only transformations. Issue #62 uses those architecture ideas only; no implementation is copied and no dependency is added.
- `jlubbersgeo/laserTRAM-DB` is an archived LA-ICP-MS workflow reference whose current development moved to USGS infrastructure. Its useful ideas are the separation of raw interval/signal selection from later concentration calculation, explicit sample/analyte labels, inspectable calculation state, and exportable reduced tables. Issue #62 begins from already reported concentrations or bulk-composition values and does not implement time-resolved LA-ICP-MS reduction.
- `djdt/spcal` (GPL-3.0) is single-particle ICP-MS prior art that clearly separates raw signal, ionic concentration, particle mass/size, calibration input, detection threshold, and output summary state. It is reference only; no GPL code is copied or adapted, and event detection/LOD/LOQ workflows remain outside Issue #62.
- `jolespin/compositional` (Apache-2.0) is conceptual compositional-data-analysis prior art. Its closure and CLR/ILR-style transformations illustrate a scientifically important boundary: CatalysisWorkbench does not silently renormalize an incomplete measured elemental subset to 100% or treat it as a closed composition.
- `materialsproject/pymatgen` (MIT) is terminology/data-model prior art for separating element/composition identity from display and derived formula representations. It is not added as a dependency merely for element-name validation.
- Existing CatalysisWorkbench `BarData` / `render_bars` and `FigureSpec` remain the publication backend; no second Matplotlib stack is introduced.

The reviewed direction distinguishes `bulk_mass_fraction` from `solution_concentration`, requires explicit unit conversion, rejects ambiguous bare `ppm`, and exposes the common solution-to-bulk relation `C_measured × dilution_factor × final_digest_volume / original_sample_mass` without adding hidden calibration, blank, recovery, or digestion corrections. Replicate aggregation is explicit and reports arithmetic mean, sample SD (`ddof=1`), RSD, and n; single replicates do not fabricate uncertainty. Tidy CSV/Excel import uses caller-selected columns and deterministic source/row keys. Publication bars require one compatible basis/unit and a complete sample×element matrix; they do not replace missing combinations with zero, close values to 100%, convert units, or aggregate raw replicates silently.

No upstream implementation code is copied and no new dependency is introduced. Full scientific/API/test details are in `docs/ICP_COMPOSITION.md`.

## Shared constrained peak-fitting and XPS architecture decision for v0.4

Issue #73 starts v0.4 with an architecture checkpoint before any fitting or XPS implementation. The full dependency order and scientific/API contract are in `docs/V0_4_PLAN.md`.

Prior-art review for the first v0.4 block:

- `lmfit/lmfit-py` — **BSD-3-Clause verified from upstream LICENSE**. LMfit provides named parameters, fixed/varying state, bounds, expression constraints/ties, composite models, fit statistics, parameter standard errors/correlations and confidence-interval tooling on top of SciPy/NumPy. Its built-in model set includes the Gaussian/Lorentzian/Voigt/pseudo-Voigt family and Doniach-style asymmetric support relevant to spectroscopy. Decision: preferred backend candidate for the first implementation Issue; CatalysisWorkbench should wrap explicit scientific contracts and provenance rather than reimplement nonlinear least squares. The architecture-only Issue does not add the dependency yet.
- `derb12/pybaselines` — **BSD-3-Clause**. It remains the preferred general spectroscopy baseline dependency/adapter candidate. Upstream searches performed for this architecture checkpoint did not establish Shirley or Tougaard as provided XPS-specific backgrounds. Decision: do not treat pybaselines as a universal XPS-background backend; XPS background semantics remain separately contracted.
- `jacobdben/XPyS` — **MIT**. Its useful concepts include explicit orbital/doublet separation, caller-provided peak guesses, linear background, Shirley background and separate fitting/plotting operations. Decision: XPS scientific/workflow reference only; no code copy.
- `JulioAzcarate/pyFitXPS` — repository license metadata is **NOASSERTION/non-standard**. Its useful ideas include sequential-spectrum workflows, explicit energy-scale correction, separation of original/corrected/fit state, lmfit-backed fitting and physically motivated asymmetric/convolved XPS line shapes. Decision: architecture/scientific reference only; no implementation reuse without a separately verified compatible license.
- `Julian-Hochhaus/LG4X-V2` — top-level project text is MIT, but its LICENSE records mixed third-party provenance including **GPL-derived XPS/VAMAS code**. Its GUI demonstrates interactive lmfit parameter editing and fit-consistency checking. Decision: reference-only for workflow/UX; do not copy implementation or parsing/background code.

The resulting v0.4 architecture is deliberately layered:

- the **shared fitting layer** owns stable parameter/component keys, explicit initial/fixed/bounded/tied parameter state, a small spectroscopy-relevant model set, exact fit recipes, deterministic provenance, fit/residual/component output, statistics and explicit uncertainty/covariance availability;
- the shared fitter does **not** automatically detect peaks, choose component count, smooth, normalize, select/estimate a background or make chemistry assignments;
- the **XPS layer** owns binding-energy/eV semantics, explicit energy calibration/reference correction, fit-region preparation, XPS-specific background state and domain constraints such as spin-orbit doublets;
- initial doublet separation, area/amplitude ratio and width ties are caller supplied. The first implementation does not silently look up textbook values from element/orbital names;
- component labels/chemical-state assignments are metadata, not evidence that a fit proves oxidation state or speciation;
- general spectroscopy baseline estimation and XPS-specific background algorithms are separate responsibilities. Linear and Shirley backgrounds may be the initial XPS scope; Tougaard requires a separately contracted equation/parameter/numerical-validation Issue;
- numerical fitting/preprocessing stays separate from a later Matplotlib-lazy XPS publication adapter built on existing `FigureSpec` rendering;
- version metadata remains `0.3.0` during architecture and ordinary v0.4 feature work until a later reviewed release gate explicitly changes it.

No upstream implementation code is copied by Issue #73 and no new runtime dependency is introduced by the architecture checkpoint.

## EIS semantics, basic circuit fitting, and plotting decision for v0.4

Issue #91 implements the first EIS-specific consumer on top of the existing immutable complex-capable `Series` model and the already-installed NumPy/SciPy/Matplotlib stack.

Fresh prior-art/license review:

- `ECSHackWeek/impedance.py` — **MIT** according to current GitHub repository metadata. Useful high-level references include separation of preprocessing/fitting/visualization, explicit complex-impedance fitting, circuit-parameter workflows, and Nyquist/Bode presentation. Decision: workflow/API/test reference only. CatalysisWorkbench copies no circuit parser, element implementation, fitting code, or plotting implementation and does not add `impedance.py` as a dependency.
- `vyrjana/pyimpspec` — **GPL-3.0** according to current GitHub repository metadata. Its rich circuit validation, impedance QA, simulation, and plotting concepts are useful architecture references. Decision: reference only; no GPL code is copied/adapted and no dependency is added.
- `scipy/scipy` — **BSD-3-Clause**, already a reviewed runtime dependency. Issue #91 uses `scipy.optimize.least_squares` as the numerical optimizer behind CatalysisWorkbench-owned EIS scientific/API contracts rather than introducing another EIS package.

The initial EIS direction is deliberately conservative:

- one core `Series` stores explicit positive monotonic frequency in Hz and literal complex impedance in ohm as `Z = Z' + jZ''`; no sorting, resampling, sign conversion, phase unwrapping, or silent unit conversion occurs;
- the project-owned typed circuit graph contains only ideal `R`, `C`, and `CPE` leaves plus explicit series/parallel composition; element keys and `element.parameter` names remain stable mathematical identities;
- CPE uses the explicit convention `Z = 1 / [Q (j 2π f)^n]` with `Q > 0` and `0 < n <= 1`;
- caller-visible parameter initial values, fixed/vary state, and bounds are validated against element physical domains;
- fitting stacks the exact real and imaginary residual channels deterministically; optional weights are explicit positive per-frequency residual multipliers applied equally to both channels;
- the public physical complex residual remains exactly `Z_observed - Z_best_fit` regardless of objective weighting, and the first stage does not fabricate covariance or standard errors;
- Nyquist rendering derives `Re(Z)` and caller-selected raw `Im(Z)` or conventional `-Im(Z)` only at display time; Bode rendering derives exact `|Z|` and principal phase without unwrap/reordering;
- EIS plotting remains Matplotlib-lazy and uses the existing `FigureSpec`/isolated rendering infrastructure rather than a parallel style system;
- automatic topology/model selection, automatic initial guesses/weighting, circuit-string parsing, parameter-expression ties, Warburg/finite-diffusion/transmission-line elements, DRT, mechanism assignment, and proprietary vendor readers remain deferred.

No upstream EIS implementation code is copied and no new runtime dependency is introduced by Issue #91.
