# CatalysisWorkbench v1.2 Desktop UI/UX Redesign

## Purpose

v1.2 is a presentation-architecture release. It productizes the existing task-first desktop without adding scientific transforms or changing the reviewed v1.1 analysis, workspace, provenance, figure, export, API, or schema contracts.

The stable product remains v1.1.0. Signing-provider enrollment, certificate/private-key operations, Authenticode/SmartScreen work, installer Release assets, and PyPI/package-registry publication remain stopped and are not part of v1.2 desktop development.

## Architecture boundary

The retained dependency direction remains:

```text
scientific -> workflow -> workspace -> application -> desktop
```

`application.analysis` remains GUI-neutral. Desktop presentation state must not become scientific identity or project state.

v1.2 does not bump `AnalysisDocument` schema merely for UI redesign. It preserves the reviewed v1.1 contracts for:

- task IDs and task catalog;
- SourceSpec / TabularMappingSpec / DataSeriesSpec identity;
- explicit LSV, FE/partial-current, and Generic XY processing semantics;
- AnalysisEvaluator and deterministic workflow execution/provenance;
- FigureDraft source binding and explicit stale behavior;
- FigureSpec presentation semantics;
- Figure Package source-data and publication semantics;
- workspace/project persistence, concurrency checks, rollback, and fail-closed behavior;
- legacy v1.0 compatibility entry points.

Presentation-only preferences such as theme and shell layout use desktop QSettings and must not dirty a project or enter `workspace.json`, `project.json`, FigureDraft, or scientific SHA identities.

## Information architecture

The product shell owns cross-page navigation and commands:

```text
CatalysisWorkbench
├── Home
└── Current Analysis
    ├── Data & Analysis
    ├── Figure
    └── Export
```

The existing task-first scientific journey remains:

```text
Home
  -> Data Intake & Mapping
  -> Live Scientific Analysis
  -> Figure Workbench
  -> Figure Package Export
```

The UI redesign must not bypass existing scientific prerequisites. Figure navigation is available only for a current successful scientific result. Export navigation is available only when the existing Figure Workbench export preflight path is eligible.

## Design system

v1.2 uses a desktop-only semantic design foundation:

- 4 px spacing grid with 4 / 8 / 12 / 16 / 24 / 32 px tokens;
- system UI typography rather than packaged fonts;
- semantic light/dark color tokens rather than page-local hard-coded colors;
- consistent navigation, command, status, card, state, and inspector components;
- semantic icon roles with implementation details kept presentation-only.

The theme preference supports `system`, `light`, and `dark`. Block 1 establishes the theme infrastructure; final dark-theme visual QA belongs to Block 7. Desktop theme must never change FigureSpec publication rendering.

## Responsive desktop targets

1920x1080 is the wide reference layout. Ordinary laptop windows are first-class targets rather than degraded fallbacks.

The shell uses a full navigation rail on wide windows and a compact icon rail below approximately 1180 px. The reviewed v1.2 shell minimum is 1024x640; later page blocks must remove page-local assumptions that prevent useful operation at that size.

## Block plan

### Block 1 — UI Foundation & App Shell

- semantic spacing/color/theme infrastructure;
- desktop-only UI settings;
- unified sidebar, command bar, and status bar;
- composition-based product window hosting the retained v1.1 Home/Analysis/Figure/Export pages;
- responsive shell navigation;
- retained page widgets and scientific behavior unchanged;
- cumulative offscreen installed-wheel shell smoke.

Block 1 deliberately does not redesign the contents of Home, Data Intake, Analysis, Figure, or Export. Existing page-local controls remain temporarily available until their owning page block replaces them.

### Block 2 — Home / Recent Projects / New Analysis

Redesign the startup surface around one clear New Analysis entry, Open Project, and productized Recent Projects presentation while retaining the closed three-task catalog and desktop-only recent-project state.

### Block 3 — Data Intake & Mapping

Redesign file state, bounded preview, parser controls, and explicit scientific mapping without changing mapping semantics, supported formats, source ownership, or fail-closed validation.

### Block 4 — Analysis Workspace

Productize the retained DATA / LIVE ANALYSIS / PROCESSING workflow into Data Navigator / Scientific Canvas / Processing Inspector with explicit empty, incomplete, error, dirty, and stale states.

### Block 5 — Figure Workbench

Productize CONTENT / PUBLICATION PREVIEW / PROPERTIES while retaining presentation-only edits, FigureDraft scientific binding, explicit refresh, and display-range separation from scientific data.

### Block 6 — Export + Dialog/State Integration

Unify Figure Package preflight, destination/options presentation, dirty guards, destructive confirmations, technical-details errors, empty/loading states, and cross-page state language.

### Block 7 — Theme / Responsive / Accessibility / Dogfooding

Complete System/Light/Dark visual QA, 1920/1440/1366/1280/compact-window behavior, high-DPI behavior, keyboard/focus review, and cumulative Generic XY / LSV / FE & Partial Current desktop journeys.

## Block workflow

Every implementation block starts from the then-current `main` on an independent feature branch and follows:

```text
architecture/scope lock
-> implementation
-> Draft PR
-> exact-head CI and compatibility gates
-> formal exact-head review
-> zero unresolved review threads
-> Ready for Review
-> STOP
```

Merge requires separate explicit authorization. No block directly pushes `main`.

## Block 1 implementation note

The v1.1 task window remains intact and is now hosted by an outer composition-based product shell. This deliberately avoids a high-risk rewrite of `workbench_window -> figure_window -> export_window` while establishing the target v1.2 shell architecture. Later page blocks can move page-owned chrome into the shell incrementally without changing the underlying scientific/session contracts.
