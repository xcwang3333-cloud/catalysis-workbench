# CatalysisWorkbench v1.2 Block 2 — Home / Recent Projects / New Analysis

## Scope

Block 2 productizes the startup surface established by the v1.2 App Shell without changing the reviewed v1.1 scientific or persistence contracts.

The Home page now presents one primary `New Analysis` action, one secondary `Open Project…` action, and a structured Recent Projects section. The three stable analysis tasks move into a dedicated `NewAnalysisDialog` while retaining the existing `HomePage.task_buttons` compatibility surface and task-selection signal wiring.

## Product structure

### Home

Home is a centered startup dashboard rather than a duplicate application title page. It provides:

- `New Analysis` as the primary action;
- `Open Project…` as the secondary action;
- a Recent Projects section;
- a restrained empty state when no history exists.

The App Shell remains the owner of the product identity, global navigation, global commands, and status bar.

### New Analysis

`NewAnalysisDialog` presents the existing closed task catalog only:

- LSV / Polarization;
- FE & Partial Current;
- Generic XY Plot.

The dialog selects a task only. It does not choose data files, create a project directory, infer a task from file extensions, or create a second analysis state machine. `Start Analysis` continues to route through the retained `start_analysis(task_id)` lifecycle.

### Recent Projects

Recent project presentation now separates:

- project title;
- task badge;
- project path;
- primary `Open` row action;
- tertiary `Remove` action.

Unavailable entries remain visible, preserve their recorded path, disable `Open`, and keep `Remove` available. Block 2 does not automatically delete, relocate, discover, or watch recent projects.

The existing `RecentProjectsStore` remains authoritative for desktop history semantics:

- QSettings only;
- path-normalized and deduplicated;
- at most 10 stored entries;
- at most 5 displayed entries;
- excluded from project and scientific identity.

## Compatibility boundary

Block 2 deliberately preserves:

- the closed v1.1 task IDs and catalog;
- `HomePage.task_selected`;
- `HomePage.open_project_requested`;
- `HomePage.recent_project_requested`;
- `HomePage.recent_remove_requested`;
- `HomePage.task_buttons` keys and `taskCard_<task_id>` object names;
- `AnalysisSession` as the only analysis lifecycle authority;
- the existing save/discard/cancel transition guards;
- project/workspace schema and persistence;
- scientific evaluation, mapping, provenance, FigureDraft/FigureSpec, Figure Package, and export behavior;
- the explicit legacy v1.0 desktop path;
- the Stable v1.1 `>=1200x760` main-window minimum contract;
- distribution/runtime version `1.1.0` while the v1.2 presentation redesign is in development.

## Visual boundary

Home, recent-project rows, task cards, and the New Analysis dialog use the Block-1 semantic spacing and theme foundation. No page-local light/dark color constants are introduced. Full System/Light/Dark visual QA remains Block 7 scope.

## Explicit non-scope

Block 2 does not add or modify:

- scientific task types or task discovery;
- data parsers, mapping semantics, or analysis processing;
- project creation-on-start behavior;
- automatic recent-project cleanup or relocation;
- responsive minimum-window compatibility policy;
- signing-provider enrollment, certificate/private-key handling, signed candidates, installer publication, Release asset publication, tag mutation, or PyPI/package-registry publication.

## Validation

The cumulative installed-wheel desktop gate adds `installed_v12_block2_desktop_smoke.py`, covering:

- productized Home labels and actions;
- retained three-task compatibility surface;
- New Analysis selection and `Start Analysis` wiring;
- Recent Projects empty state;
- saved-project title/task/path presentation;
- recent-project open behavior;
- unavailable-project disabled `Open` state;
- unavailable-project removal;
- semantic Home/Recent theme selectors;
- cumulative v1.0/v1.1/v1.2 Block-1 desktop compatibility through the existing CI sequence.
