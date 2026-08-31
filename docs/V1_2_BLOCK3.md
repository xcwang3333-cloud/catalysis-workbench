# CatalysisWorkbench v1.2 Block 3 — Data Intake & Mapping

## Scope

Block 3 redesigns the existing v1.1 tabular Data Intake surface without changing scientific-input identity, supported formats, mapping semantics, source ownership, or fail-closed validation.

The retained import model remains:

```text
FILES | PREVIEW | MAPPING
```

The dialog continues to require explicit confirmation for every selected file before data can be added to an analysis.

## Presentation structure

### Files

The Files pane remains a selectable list of the chosen sources and retains the stable v1.1 status prefixes:

- `✓` mapping confirmed;
- `⚠` review required;
- `✕` source/preview unavailable.

A presentation-only summary reports how many mappings are confirmed and which entries still require attention. Multi-file selection and the existing `file_list` compatibility surface are retained.

### Preview

Preview remains bounded and read-only. It now makes source metadata, preview row/column count, and truncation status more legible while continuing to use the existing GUI-neutral `inspect_tabular()` path.

A preview is a configuration aid only. Display truncation never truncates scientific data.

### Parser controls

Block 3 exposes parser fields that were already part of `TabularMappingSpec` and the existing preview/materialization path:

- Excel sheet;
- text delimiter;
- header row, including explicit no-header mode;
- rows skipped before parsing;
- text encoding.

Changing any parser setting invalidates the current mapping confirmation. The user must reload the preview before confirmation can succeed. A successful reload still does not auto-confirm the scientific mapping.

Text delimiter auto-detection remains only a configuration aid: the resolved delimiter is persisted explicitly in the existing mapping. Excel continues to persist an explicit sheet and never a delimiter.

### Scientific mapping

The scientific mapping section retains the existing fields and semantics:

- series display name;
- X column;
- X meaning;
- X unit;
- optional X reference;
- Y column;
- Y meaning;
- Y unit.

Task defaults remain exactly the existing closed rules: LSV uses potential/current, FE & Partial Current uses potential/response, and Generic XY uses x/y. Unit text inferred from headers remains an aid only and is never a unit conversion.

## Batch compatibility

`Apply to compatible files` preserves the v1.1 compatibility test exactly. A mapping is propagated only when the target preview has the same selected X/Y positions, exact X/Y column names, and exact conservatively inferred units.

Block 3 does not guess across incompatible files and does not change parser settings on other files as part of mapping propagation.

## Stable compatibility surface

Block 3 deliberately retains the v1.1 desktop API used by installed-wheel compatibility checks, including:

- `ImportDataDialog`;
- `file_list`;
- `confirm_current_mapping()`;
- `apply_current_mapping_to_compatible()`;
- `mapped_items()`;
- `x_reference`;
- edit mode and `edited_mapping()`;
- `SeriesPreviewDialog`.

The existing `AnalysisSession.add_data_series_batch`, `replace_data_mapping`, materialization, project Save As staging, owned-source copying, content-digest checks, and dependency refresh path remain authoritative.

## Scientific and persistence boundary

Block 3 does not modify:

- `SourceSpec`, `TabularMappingSpec`, or `DataSeriesSpec` fields or hashing;
- AnalysisDocument schema;
- `AnalysisSession`;
- application analysis evaluator behavior;
- scientific processing semantics;
- raw-source ownership or workspace destinations;
- supported suffixes: `.csv`, `.txt`, `.tsv`, `.dat`, `.xlsx`, `.xlsm`;
- path-independent source identity;
- materialized scientific values;
- batch duplicate-input checks.

The runtime/distribution version remains `1.1.0` during the v1.2 presentation redesign.

## Explicit non-scope

Block 3 does not add:

- `.xls` or other new file formats;
- recursive directory import;
- external-reference mode for normal users;
- multi-X or multi-Y mapping;
- automatic task discovery or task inference from file names/extensions;
- automatic scientific-role inference beyond the existing task defaults;
- unit conversion;
- decimal-locale conversion;
- whitespace stripping/simplification;
- dtype coercion controls;
- row filtering or scientific transforms during import;
- changes to the overall Analysis Workspace layout, which belongs to Block 4;
- a lower main-window minimum;
- signing, installer publication, Release assets, tag mutation, or PyPI publication.

## Open-source reference boundary

Orange3's CSV import design is used only as a presentation reference for colocating explicit parser options with a bounded preview and disabling acceptance on preview errors. SciDAVis is used only as a reference for visually separating advanced import options.

Their broader column typing, locale/numeric conversion, whitespace transformations, and import-mode mutation features are intentionally not adopted because they would expand CatalysisWorkbench's frozen parser/scientific semantics.

## Validation

The cumulative installed-wheel Block-3 desktop smoke covers:

- retained v1.1 import dialog APIs;
- multi-file compatible mapping propagation;
- parser-dirty fail-closed behavior;
- explicit reload before confirmation;
- skipped-row/header persistence;
- explicit text-encoding recovery from an initial decode failure;
- inferred-unit display without conversion;
- semantic Data Intake theme selectors;
- continued cumulative v1.0/v1.1/v1.2 Block-1/2 compatibility.
