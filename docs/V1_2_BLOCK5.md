# v1.2 Block 5 — Figure Workbench

## Scope

Block 5 productizes the retained v1.1 Figure Workbench as a presentation-focused
`CONTENT | PUBLICATION CANVAS | PROPERTIES` workspace inside the v1.2 App Shell.
It is a presentation architecture block, not a new plotting or scientific-analysis engine.

### Content

- Preserve the existing result/view selector and publication presets.
- Preserve Create Figure, Refresh from Analysis, and Reset Styling semantics.
- Preserve trace visibility, ordering, and selected-trace styling behavior.
- Surface no-draft/current/stale states with clearer action hierarchy.

### Publication Canvas

- Rename the center surface from `PUBLICATION PREVIEW` to `PUBLICATION CANVAS`.
- Keep the Matplotlib render as a read-only publication preview of the retained
  `FigureDraft` / `FigureSpec` state.
- Surface presentation-only states for no draft, current figure, stale analysis,
  missing font, and render/preview errors.
- Do not introduce a second mutable canvas model, interactive scientific edits,
  annotations, secondary axes, multi-panel composition, or new curve derivations.

### Properties

- Preserve the existing FigureSpec-editable fields only: figure size/title,
  axis labels/ranges/scales/unit format, legend, typography, and selected-trace style.
- Keep immutable FigureSpec replacement through the existing session/window wiring.
- Make the existing property groups vertically scrollable for ordinary desktop use.
- Continue to use system fonts only; no font files are bundled or distributed.

## v1.2 composition boundary

The retained v1.1 FigureWorkbenchPage and Figure window orchestration remain the
behavioral implementation. A v1.2-only presentation composition layer is applied by
`product_window.py`. This keeps the legacy v1.1 constructor and compatibility path
unchanged while removing duplicate page-local Back/Undo/Redo/Save controls from the
visible v1.2 product surface. Their existing widgets/signals remain intact as a hidden
compatibility bridge; the App Shell remains the visible global command owner.

The Block-4 semantic QSS components are reused for pane, state, list, button, and
scroll presentation. No page-local light/dark color constants are introduced.

## Frozen contracts

Block 5 does not change:

- AnalysisSession or evaluator behavior;
- scientific arrays, processing formulas, task IDs, or allowed figure views;
- FigureDraft or FigureSpec schema/identity;
- figure creation, refresh, reset, trace-order, or immutable spec replacement semantics;
- stale detection or the requirement that Refresh from Analysis preserves presentation styling;
- renderer behavior or publication data sampling semantics;
- Figure → Export gate: figure must be current, use an available font, and contain at least one visible trace;
- Export preflight requirement that the project is saved and clean;
- project/workspace persistence or schema version;
- runtime package version (`1.1.0`);
- Stable v1.1 minimum window contract (`>=1200x760`).

Signing-provider enrollment, certificates/private keys, signed artifacts, installer
publication, Release assets, tag mutation, and PyPI/package-registry publication remain
outside v1.2 Block 5.

## Open-source architecture references

- Veusz: its tree/object editing surface is used only as a reference for separating
  content selection from property editing.
- KDE LabPlot: its Project Explorer and plot-specific Properties dock are used only as
  a reference for content/canvas/properties separation.

No dock/plugin framework, external object model, or interactive plotting engine is
ported into CatalysisWorkbench.

## Validation

The cumulative installed-wheel desktop smoke must verify:

1. v1.2 hides duplicate Figure page Back/Undo/Redo/Save controls while retaining their widgets;
2. no-draft → create → current presentation transitions;
3. FigureSpec edits and trace visibility continue to use retained immutable session updates;
4. stale analysis disables editing and requires Refresh from Analysis;
5. refresh preserves custom trace presentation;
6. an unavailable font fails closed for preview/export;
7. the Figure → Export gate remains current + font available + visible traces;
8. schema version 4 and the `>=1200x760` compatibility contract remain unchanged;
9. all earlier v1.0/v1.1 and v1.2 Block 1–4 installed-wheel desktop smokes remain green.
