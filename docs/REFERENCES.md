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
| Electrochemical impedance | `ECSHackWeek/impedance.py` | Mature Python package for electrochemical impedance data and circuit fitting. | Reference/dependency candidate when EIS is implemented in v0.4. |
| XAS | `xraypy/xraylarch` | Mature X-ray spectroscopy/XAS processing ecosystem. | Reference/dependency candidate for XANES/EXAFS algorithms; CatalysisWorkbench should emphasize comparison, result integration and publication figures rather than replace the mature XAS stack. |
| Electronic structure | `romerogroup/pyprocar` | Electronic-structure parsing/visualization, including projected electronic data. | Reference for DOS/PDOS parsing and projection-selection concepts in v0.6. |
| Chemical bonding | `JaGeo/LobsterPy` | Analysis of LOBSTER bonding output. | Reference/dependency candidate for COHP/ICOHP parsing and bonding analysis in v0.6. |

## Core data-model decision for v0.1

The first core model follows a deliberately narrow contract:

- `Axis`: axis name, display label, unit string and lightweight metadata.
- `Series`: one numerical `y(x)` trace plus its two axes, display label and metadata.
- `Dataset`: ordered collection of `Series` objects; it also serves the multi-catalyst collection role in v0.1, so a separate `SeriesCollection` type is intentionally avoided.
- Numerical arrays are copied on construction and exposed read-only so processing functions return new objects instead of mutating source data in place.
- Duplicate series labels are allowed so replicate measurements of the same catalyst can coexist.
- NaN is preserved as explicit missing data for later cleaning policies; malformed arrays and +/-inf are rejected.
- Units are explicit strings in v0.1. General unit arithmetic/conversion is not part of the core; domain-specific conversions belong in analysis modules.

This takes the useful metadata-coupling idea from ixdat and the label/attribute separation idea from xarray without importing either project's full object model.

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
