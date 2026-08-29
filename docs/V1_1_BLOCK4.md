# CatalysisWorkbench v1.1 Block 4 — Figure Workbench

Block 4 adds the publication-presentation stage between live scientific analysis and the later Figure Package export stage. It is deliberately presentation-only: scientific processing remains owned by Block 3 and is never recomputed or mutated by Figure Workbench controls.

## User flow

```text
successful Analysis Workbench result
    -> Continue to Figure
    -> choose result view
    -> create FigureDraft explicitly
    -> edit publication presentation
    -> preview exact FigureSpec rendering
    -> Save Project
    -> Continue to Export (disabled until Block 5)
```

The Figure Workbench has three normal-user regions:

```text
CONTENT | PUBLICATION PREVIEW | PROPERTIES
```

It does not expose recipe IDs, workflow bindings, SHA fields, Evidence records, workspace assets, or scientific Processing controls.

## AnalysisDocument schema 4

Block 4 advances newly created and newly saved `AnalysisDocument` state to schema 4. Schemas 1, 2, and 3 remain readable and normalize in memory to schema 4 without rewriting the project merely because it was opened. The first explicit save persists the schema-4 representation.

Schema 4 adds an ordered `figures` collection. A task may persist at most one `FigureDraft` for each supported result view:

- LSV / Polarization: `processed`;
- Generic XY: `processed`;
- FE & Partial Current: independent `fe` and `partial_current` drafts.

Computed arrays remain runtime-only. A figure edit therefore changes the document/FigureDraft identity but not mapped input identities, workflow execution identities, or numerical `Series` arrays.

## FigureDraft identity

A `FigureDraft` contains:

- `schema_version`;
- `view_id`;
- a mapping from logical trace IDs to exact scientific-result identities;
- independent publication `trace_order`; and
- one immutable `FigureSpec`.

`source_view_sha256` and `figure_sha256` are derived rather than serialized.

The source-view identity is independent of display order. For processed LSV/Generic outputs and partial-current outputs, the scientific identities are the deterministic workflow output identities. FE-view identities are tied to the exact FE scientific input plus the scientific analysis-range state, without depending on unrelated total-current processing.

Publication ordering is independent from Analysis data ordering. Reordering inputs in Analysis does not silently reorder an existing FigureDraft.

## Frozen publication labels and styles

Creating a FigureDraft is explicit. At creation, the current result labels and preset colors are copied into per-trace `SeriesStyle` state. This freezes publication presentation independently from later Analysis display-name edits.

A later Analysis rename therefore does not silently change an already prepared legend. Users can deliberately edit the Figure trace label in PROPERTIES.

Figure editing uses the existing immutable `FigureSpec` model and existing reviewed renderers. Block 4 does not introduce a second plotting engine.

## Scientific stale and explicit refresh

A FigureDraft is current only while its persisted trace-to-scientific-identity mapping matches the selected live result view. When affected scientific results change, the FigureDraft becomes stale.

A stale draft is not presented as current and cannot be previewed or edited as if it represented the new scientific result. The user must choose `Refresh from Analysis` explicitly.

Refresh:

- rebinds the FigureDraft to current scientific identities;
- retains presentation order and styling for surviving logical trace IDs;
- removes styles for traces that no longer exist; and
- appends newly introduced traces with explicit frozen initial labels/colors.

No automatic refresh occurs during scientific processing edits.

## Analysis Range versus Display Range

These concepts are separate by design:

- **Analysis Range** is Block-3 scientific processing state and may change scientific outputs/identities.
- **Display Range** is `FigureSpec.xlim` / `FigureSpec.ylim` presentation state.

Changing display limits never crops, filters, resamples, or modifies scientific arrays. The renderer receives the complete current `Series` and applies limits only to the axes.

## Visible-trace compatibility

Only traces selected as visible participate in one-axes compatibility validation. This lets a user hide an incompatible trace and produce a valid single-quantity plot.

Re-enabling an incompatible trace fails closed through the existing renderer's axis-name/unit/reference/normalization validation. Block 4 never performs hidden unit conversion, interpolation, resampling, or semantic coercion.

At least one trace must remain visible.

## Figure properties

The normal properties surface includes:

- title;
- physical figure width/height;
- X/Y labels;
- X/Y display ranges and scales;
- axis unit-label format;
- legend visibility and location;
- font family and common typography sizes; and
- selected-trace label, color, line style/width, marker, and marker size.

Only font families reported by the local Matplotlib font manager are offered normally. A persisted font that is unavailable on another system is reported explicitly instead of silently claiming an exact publication preview.

Existing advanced `FigureSpec` capabilities remain available to lower-level APIs but are intentionally not all exposed by this first normal-user Figure Workbench.

## Session and persistence semantics

FigureDraft creation, refresh, presentation edits, and trace reorder are normal semantic `AnalysisDocument` revisions. They use the same `AnalysisSession` dirty state and 100-step Undo/Redo history as title, mapping, and processing edits.

Saving a project preserves the FigureDraft inside `project.json`. Reopening rematerializes/evaluates current scientific inputs and determines whether the persisted FigureDraft still matches the exact scientific view.

Preview/edit operations do not create workspace FigureSpec assets, exported-figure assets, `FigureComposition` records, or Evidence records. Those integrations belong to Block 5 export.

## Desktop compatibility

The v1.0 legacy desktop path remains available. The frozen top-level `catalysis_workbench.desktop.__all__` contract is unchanged.

The no-argument v1.1 workbench path now uses Home -> Analysis -> Figure. `Continue to Figure` is enabled only for a current successful scientific evaluation. `Continue to Export` remains disabled in Block 4.

`application.analysis` remains Qt-free and does not import PySide6, PyQt, or `matplotlib.pyplot`.

## Validation gates

Block 4 requires coverage for:

- schema 1/2/3 read compatibility and schema-4 round trips;
- deterministic FigureDraft/source-view identities;
- presentation changes leaving WorkflowRun scientific identities unchanged;
- Analysis display rename/order not silently changing frozen Figure labels/order;
- affected scientific changes making the corresponding draft stale;
- explicit refresh preserving surviving presentation state;
- display ranges leaving full scientific arrays unchanged;
- visible-only axes compatibility and all-hidden rejection;
- Undo/Redo and save/reopen FigureDraft behavior;
- fresh-wheel headless Block-4 smoke;
- fresh-wheel offscreen Desktop Figure Workbench smoke;
- regular CI; and
- the full frozen v1.0 Stable Readiness compatibility matrix.

## Block 4 non-scope

Block 4 does not implement multi-panel/subplot composition, secondary Y axes, scientific smoothing/fitting/baseline correction, interpolation/resampling, automatic unit conversion, arbitrary annotation editing, journal-specific preset libraries, external font packaging, PNG/SVG/PDF export dialogs, XLSX/TXT source-data export, Figure Package transactions, Evidence recording, Git tags, GitHub Releases, or PyPI publication.
