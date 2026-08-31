# v1.2 Block 1 — UI Foundation & App Shell

## Scope

Block 1 establishes the presentation architecture for the v1.2 desktop redesign while retaining the complete v1.1 task-first page implementation underneath it.

Implemented:

- semantic spacing and theme tokens;
- desktop-only QSettings for theme and sidebar preference;
- unified product sidebar;
- cross-page command bar for project title/task/dirty state plus Undo/Redo/Save;
- global status bar;
- responsive sidebar compaction for ordinary laptop widths;
- composition-based product window hosting Home, Data & Analysis, Figure, and Export;
- page enablement tied to retained v1.1 prerequisites;
- reviewed 1024x640 shell minimum with 1440x900 default size;
- installed-wheel offscreen Block-1 shell smoke;
- v1.2 architecture and seven-block implementation plan.

## Compatibility strategy

The existing v1.1 `workbench_window -> figure_window -> export_window` chain is deliberately left intact in Block 1. The new `product_window` subclasses the completed v1.1 task window and wraps its existing `QStackedWidget` in the new composition shell.

This means Block 1 changes application chrome without rewriting the existing Home, Data Intake, Analysis, Figure, or Export page behavior. Those pages remain the responsibility of later v1.2 blocks.

The legacy v1.0 `create_desktop()` / `ApplicationSession` path remains unchanged.

## Scientific and persistence boundary

Block 1 does not change:

- scientific kernels or processing semantics;
- `AnalysisDocument` schemas;
- SourceSpec / mapping / data identities;
- task catalog or task IDs;
- workflow compilation or run identity;
- FigureDraft / FigureSpec semantics;
- stale Figure behavior;
- Figure Package export semantics;
- workspace or project persistence;
- provenance/evidence contracts;
- distribution version (`1.1.0`).

Theme and sidebar state are desktop-only QSettings and do not participate in project dirty state or any scientific/application identity.

## Release/distribution non-scope

Block 1 does not perform or authorize:

- signing-provider enrollment;
- certificate/private-key operations;
- Authenticode or SmartScreen work;
- signed candidate production;
- installer Release asset publication;
- tag mutation;
- PyPI or package-registry publication.

## Validation

The Block-1 Draft PR must pass on its exact head:

- regular CI;
- cumulative installed desktop smoke including `installed_v12_block1_desktop_smoke.py`;
- Stable 1.0 Readiness;
- Stable 1.1 Readiness;
- formal exact-head review;
- zero unresolved review threads.

After review the PR may be marked Ready for Review, then development stops pending separate merge authorization.
