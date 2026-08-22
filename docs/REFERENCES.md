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
| Baseline correction | `derb12/pybaselines` | Dedicated baseline-correction algorithms for spectroscopy/materials data. | Prefer a dependency/adapter for validated baseline methods instead of rewriting complex algorithms. |
| Curve fitting | `lmfit/lmfit-py` | Flexible constrained nonlinear least-squares fitting on top of SciPy. | Reference/dependency candidate for peak fitting, constrained XPS components, spectroscopy fitting and uncertainty reporting. Verify license terms before direct code reuse. |
| Electrochemical experimental data | `ixdat/ixdat` | In-situ experimental data architecture and electrochemistry-oriented scientific data handling. `DataSeries` wraps NumPy data together with unit/axis context and higher-level fields reference explicit axes. MIT licensed. | Core-model reference for keeping numerical values attached to scientific metadata while avoiding ixdat's database/persistence layer. Also relevant to future time/potential-resolved workflows. |
| Labeled scientific arrays | `pydata/xarray` | General labeled N-D arrays and datasets. Xarray explicitly separates raw NumPy-like values from dimensions, coordinates and arbitrary attributes, and uses a Dataset as a container for labeled arrays. Apache-2.0 licensed. | Conceptual reference for labels/metadata and Dataset semantics. Do not add xarray as a v0.1 dependency; CatalysisWorkbench starts with a deliberately lightweight 1-D XY model and can add adapters later if N-D operando data justify it. |
| Tabular I/O | `pandas-dev/pandas` | Mature CSV and Excel parsers with explicit sheet, header, selected-column, missing-value, delimiter, and dtype controls. BSD-3-Clause licensed. | Use pandas as the parsing backend rather than rebuilding CSV/Excel parsing. CatalysisWorkbench adds the catalysis-specific conversion into `Axis`/`Series`/`Dataset`, source metadata, validation, and deterministic keys. |
| Scientific reader patterns | `ixdat/ixdat` readers | Dedicated format readers keep parsing separate from scientific objects; the CSV reader retains header/column/unit context, while the XRD XY reader performs conservative header/comment detection and leaves domain data in explicit series/fields. MIT licensed. | Follow the parser-adapter pattern: parse file structure first, then construct standard core objects. Avoid silently skipping malformed selected values; CatalysisWorkbench raises explicit validation errors for user-selected scientific columns. |
| Electrochemical impedance | `ECSHackWeek/impedance.py` | Mature Python package for electrochemical impedance data and circuit fitting. | Reference/dependency candidate when EIS is implemented in v0.4. |
| XAS | `xraypy/xraylarch` | Mature X-ray spectroscopy/XAS processing ecosystem. | Reference/dependency candidate for XANES/EXAFS algorithms; CatalysisWorkbench should emphasize comparison, result integration and publication figures rather than replace the mature XAS stack. |
| Electronic structure | `romerogroup/pyprocar` | Electronic-structure parsing/visualization, including projected electronic data. | Reference for DOS/PDOS parsing and projection-selection concepts in v0.6. |
| Chemical bonding | `JaGeo/LobsterPy` | Analysis of LOBSTER bonding output. | Reference/dependency candidate for COHP/ICOHP parsing and bonding analysis in v0.6. |

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

Publication presets are **starting templates**, not locked themes. From the first plotting API, visual parameters should be represented explicitly in a `FigureSpec` / `PlotStyle` model so the same figure can later be adjusted interactively without changing the scientific analysis code.

Parameters that should remain user-adjustable include:

- figure width and height;
- axes width/height or aspect ratio;
- plot margins;
- font family and font sizes;
- axis-label and tick-label sizes;
- line width and line style;
- marker symbol and marker size;
- axis-spine width;
- tick length and tick width;
- legend location and typography;
- x/y limits and scales;
- annotation size/position;
- export format, physical size and DPI.

The v0.1 API should expose these values programmatically. A later local GUI (target v0.9-v1.0) should bind controls directly to the same parameter object and redraw the figure immediately.

## Structure-visualization note

`pretty-lattice` is particularly relevant to the desired structure-figure experience. Its useful high-level choices include:

- keep structure analysis/parsing separate from visual styling;
- rely on a mature structure library instead of rebuilding crystallographic parsing;
- construct an intermediate scene representation between structure data and the renderer;
- provide attractive defaults but expose fine-grained atom/bond/material controls;
- make preview and export part of the same rendering model.

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

## LSV / polarization processing decision for v0.1

`ixdat/ixdat` (MIT) is the main architecture and equation reference for the first electrochemistry layer. Its `ECCalibration` stores reference-electrode offset, electrode area, and uncompensated resistance explicitly. The calibrated potential adds the reference-to-RHE offset, ohmic correction subtracts signed current times resistance, and current normalization divides total current by electrode area. CatalysisWorkbench adopts those transparent numerical semantics while keeping a much lighter post-processing API.

The v0.1 LSV contract is deliberately explicit:

- an LSV trace is a normal core `Series` whose x values are potential and y values are either total current or current density;
- RHE conversion uses an explicit additive `offset_v`; a helper can derive that offset from a user-supplied reference potential versus SHE, pH, and temperature using the Nernst pH term, but v0.1 does not embed a reference-electrode lookup table;
- ohmic-drop correction is `E_corrected = E - fraction * I * R` using signed **total current in amperes**; if the input y data are current density, geometric electrode area is mandatory before applying Ohm's law;
- current-density normalization uses explicit geometric area in cm^2 and refuses to normalize an already-normalized current-density trace again;
- only common electrochemical V/mV, A/mA/uA, and corresponding per-cm^2 units are interpreted in v0.1. Missing or unsupported units fail rather than being guessed;
- electrochemical transformations are non-mutating, preserve stable keys/source metadata, update changed axis semantics, and append deterministic `echem.*` entries to the shared `processing_history`;
- `LSVProcessingConfig` records the complete correction/normalization recipe. Dataset processing can apply one common recipe with stable-key-specific overrides for catalysts measured under different resistance/area/reference conditions;
- plotting is intentionally not implemented inside the electrochemistry module. LSV rendering must consume the shared `FigureSpec`/curve renderer from Issue #7 so LSV, XRD, and Raman do not develop separate Matplotlib style systems.
