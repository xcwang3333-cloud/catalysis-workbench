# ICP / elemental-composition integration contract

Issue #62 adds a conservative scalar elemental-composition layer for ICP-OES/ICP-MS-style reported results, explicit solution-to-bulk mass balance, replicate statistics, tidy CSV/Excel import, and publication summaries. It starts from already reported concentrations or already measured bulk-composition values; it does not perform raw instrument signal calibration.

## Design boundary

ICP/composition data are categorical scalar measurements rather than one-dimensional `y(x)` traces. The module therefore introduces a narrow immutable `CompositionMeasurement` / `CompositionTable` model instead of pretending element names are numeric `Series.x` values.

The initial contract requires:

- stable non-display measurement and sample keys;
- explicit element identity and optional analyte/channel text;
- explicit numerical value, unit, and physical basis;
- deterministic source identity/digests;
- explicit replicate membership where supplied;
- no hidden unit conversion, averaging, closure normalization, outlier removal, calibration, blank correction, or recovery correction.

## Quantity bases and units

Two quantity bases are supported.

### Bulk mass fraction

`bulk_mass_fraction` means analyte mass divided by the original bulk sample mass. Supported representations are:

- dimensionless fraction: `1`;
- weight percent: `wt%`;
- `mg/g`;
- `ug/g`;
- `mg/kg`.

The exact relationships are:

\[
1\;\mathrm{wt\%}=0.01=10\;\mathrm{mg\,g^{-1}}
=10^4\;\mathrm{\mu g\,g^{-1}}
=10^4\;\mathrm{mg\,kg^{-1}}.
\]

### Solution concentration

`solution_concentration` means analyte mass divided by measured solution volume. Supported representations are:

- `g/L`;
- `mg/L`;
- `ug/L`.

Conversion occurs only through explicit `convert_composition_unit(...)` or `convert_composition_table(...)` calls. Plotting and replicate summaries do not convert units automatically.

Bare `ppm` is deliberately rejected. In laboratory exports it can mean a mass fraction or a solution concentration depending on context; CatalysisWorkbench requires the caller to state the physical basis directly.

## Element versus analyte/channel identity

`element` is explicit scientific identity used for grouping and publication summaries. Optional `analyte` text may retain an instrument channel such as `208Pb`, `56Fe`, or a wavelength identifier.

The library never parses the element from the analyte string. This prevents an isotope/wavelength naming convention from silently becoming chemistry metadata.

## Explicit solution-to-bulk mass balance

For a common digestion-and-dilution ICP workflow, `solution_concentration_to_bulk_mass_fraction()` evaluates only the caller-declared mass balance:

\[
w = \frac{C_{\mathrm{measured}}\,D\,V_{\mathrm{digest}}}{m_{\mathrm{sample}}},
\]

where:

- `C_measured` is concentration in the actually measured solution;
- `D` is the cumulative dimensionless dilution factor mapping that measured concentration back to the final digest concentration;
- `V_digest` is the final digest volume;
- `m_sample` is original sample mass.

Example: `10 mg/L`, dilution factor `2`, final digest volume `25 mL`, and sample mass `50 mg` gives `0.5 mg / 50 mg = 1 wt%`.

The helper records the explicit mass, volume, dilution factor, source value, and source unit in deterministic metadata. It does **not** perform or infer:

- calibration-curve fitting;
- blank subtraction;
- spike/recovery correction;
- digestion recovery;
- sample-density conversion;
- internal-standard correction;
- stoichiometric or 100% closure.

## Replicates and uncertainty

Replicates remain separate `CompositionMeasurement` objects until `summarize_composition_replicates()` is called explicitly.

A replicate group is defined by the same explicit sample key and element and must already share the same basis, unit, and analyte declaration. No conversion is performed just to make a group compatible.

The summary reports:

- arithmetic mean;
- sample standard deviation with `ddof=1`;
- relative standard deviation, `100 × SD / mean`;
- replicate count `n`;
- ordered source measurement keys and a deterministic source digest.

For `n = 1`, SD and RSD are undefined and remain `None`; the library does not invent zero uncertainty. When the mean is zero, RSD remains undefined even if SD is numerically zero.

There is no automatic outlier rejection, weighting, SEM substitution, confidence interval, or uncertainty propagation.

## Tidy CSV / Excel import

`read_composition_csv()` and `read_composition_excel()` use pandas only as a parser backend. The caller explicitly selects:

- sample column;
- element column;
- numerical value column;
- basis and unit;
- optional replicate, analyte, and sample-display-label columns.

Columns may be selected by exact header or zero-based position. Selected missing/non-numeric scientific values fail explicitly.

Reader-generated measurement keys are deterministic from source identity and row position. By default the normalized source path is the identity; `source_id` can be supplied for portable project-level keys. Excel integer sheet selection is resolved to the canonical sheet name before source keys are generated.

The reader does not guess units or basis from arbitrary column labels and does not parse proprietary vendor binaries.

## Selection and stable keys

`select_composition()` filters by explicit stable `sample_key` and/or element identity. Display labels are not accepted as substitutes for stable sample keys. Unknown selections fail rather than returning a misleading partial result.

## Publication plotting

`plot_composition()` is a lazy adapter over the existing shared grouped-bar renderer:

```python
fig, ax = plot_composition(summary_table, spec, error="sd")
```

Default structure is:

- samples as categorical x positions;
- elements as grouped bar series;
- optional sample-SD errors only after explicit replicate summarization.

Plotting requires one compatible basis and one compatible unit. It never:

- converts units;
- normalizes the displayed elements to 100%;
- interprets an incomplete measured subset as a closed composition;
- replaces a missing sample×element combination with zero;
- silently averages raw replicates.

Raw data with duplicate sample×element measurements must be summarized explicitly first. The initial plotting contract also requires a complete sample×element matrix; missing combinations fail visibly.

Element bar styles use stable keys such as `element:Pb`, while sample category styling uses `sample_key`. Shared `FigureSpec` settings remain authoritative for dimensions, fonts, colors, bar width, limits, legends, and export.

Importing `catalysis_workbench.experimental.characterization` remains Matplotlib-lazy. Matplotlib is loaded only when plotting is actually requested.

## Prior art and license decisions

The module was scoped after reviewing:

- `oscarbranson/latools` — MIT. Main ICP data-reduction architecture reference for analyte-aware, traceable reduction, reference-material state, and uncertainty retention. No implementation is copied and no dependency is added.
- `jlubbersgeo/laserTRAM-DB` — archived GitHub workflow reference, with current LaserTRAM development moved to USGS infrastructure. Useful for separating raw interval selection from subsequent concentration calculations and exposing calculation state/export. This Issue does not implement its time-resolved LA-ICP-MS pipeline.
- `djdt/spcal` — GPL-3.0. Reference only. Its separation of raw signal, concentration, particle mass/size, calibration, and detection thresholds helps define scope; no GPL code is copied or adapted.
- `jolespin/compositional` — Apache-2.0. Conceptual boundary reference: compositional-data methods intentionally close/transform vectors, whereas an ICP subset in CatalysisWorkbench is not silently closed to 100% or transformed with CLR/ILR.
- `materialsproject/pymatgen` — MIT. Terminology/data-model reference for keeping element/composition identity separate from presentation. It is not added merely for element-name validation.
- CatalysisWorkbench `BarData` / `render_bars` and `FigureSpec` remain the plotting backend.

No upstream implementation code is copied.

## Explicitly deferred

Issue #62 does not implement:

- calibration-curve fitting or raw cps/intensity reduction;
- blank subtraction or spike/recovery correction;
- digestion chemistry or recovery models;
- LOD/LOQ calculation;
- internal-standard or interference correction;
- proprietary ICP-OES/ICP-MS binary readers;
- single-particle/single-cell ICP event detection;
- automatic atomic-percent conversion;
- 100% closure or CLR/ILR transformations;
- cross-technique XPS/EDS/ICP composition fusion;
- GUI behavior;
- a `0.3.0` version bump, tag, release, or package-registry publication.
