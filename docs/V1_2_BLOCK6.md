# v1.2 Block 6 — Export + Dialog/State Integration

## Scope

Block 6 productizes the retained v1.1 Figure Package Export and integrates modal desktop state language across the v1.2 product shell. It is a presentation/orchestration block, not a new export engine or scientific-state layer.

### Export surface

The retained Figure Package behavior remains authoritative. The v1.2 product path presents the page as:

```text
SUMMARY
CONTENTS
DESTINATION
PREFLIGHT
RESULT
```

The existing export choices remain unchanged:

- figure files: SVG / PDF / PNG;
- source data: XLSX / TXT;
- a destination must be a new directory whose parent already exists;
- the project must be saved and clean;
- the selected Figure must be current;
- the selected Figure font must be available;
- at least one trace must remain visible.

Save Project, Open Folder, and Export Another retain their v1.1 behavior.

### Presentation states

Block 6 adds desktop-only Export presentation states:

- `empty`: no preflight has been applied yet;
- `blocked`: a retained preflight, format, or destination prerequisite is not satisfied;
- `ready`: retained preflight and options allow export;
- `exporting`: the existing synchronous exporter is executing;
- `success`: a package was exported successfully;
- `error`: the existing exporter or page validation reported an error.

`exporting` does not introduce a worker, background task, queue, or second export engine. The application processes one Qt paint/event cycle before invoking the retained synchronous exporter so the user can see the state transition.

### Dialog/state integration

The v1.2 product path centralizes presentation for:

- dirty Save / Discard / Cancel transition guards;
- invalid unapplied processing-draft Discard / Cancel guards;
- destructive data removal confirmation, including dependency impact;
- actionable errors with summary, guidance, and optional technical details.

Cancel is the safe default and Escape action for destructive/transition decisions. Decision outcomes and AnalysisSession behavior remain unchanged. The legacy v1.1 window continues to use its existing QMessageBox presentation.

### Cross-page status language

The App Shell status bar reflects the active scientific/product surface. Figure states report create/current/stale/error language and Export states report blocked/ready/exporting/success/error language. The global dirty indicator remains derived exclusively from AnalysisSession state.

## Architecture boundary

Block 6 changes desktop presentation/orchestration only. It does not change:

- `AnalysisSession`, evaluator behavior, task IDs, processing formulas, or scientific arrays;
- `FigureDraft`, `FigureSpec`, renderer semantics, stale/refresh semantics, or display-range separation;
- Figure Package writer behavior, manifest content, source-data rules, package SHA identity, or reproducibility;
- project/workspace persistence, concurrency checks, rollback, or schema version;
- the runtime package version (`1.1.0`);
- the Stable v1.1 `>=1200x760` main-window minimum contract.

Block 6 does not add autosave, package overwrite/merge, asynchronous/background export, cloud state, new task discovery, new scientific inference, or new persistent UI state.

Signing-provider enrollment, certificates/private keys, signed candidates, installer publication, Release assets, tag mutation, and PyPI/package-registry publication remain outside this block.

## Open-source architecture references

- napari's dedicated close-confirm dialog is used only as a reference for separating modal decision presentation from the main window and retaining a clear Cancel path.
- Spyder's reusable QMessageBox helper pattern is used only as a reference for centralizing dialog presentation instead of duplicating message-box styling across actions.

No plugin framework, persistent "do not ask again" behavior, external object model, or background task framework is introduced.

## Validation

The cumulative installed-wheel desktop smoke must verify:

1. the v1.2 Export page hides duplicate page-local Back chrome while retaining its signal/widget compatibility;
2. retained preflight rules continue to block export until project, Figure, font, visible-trace, format, and destination requirements are satisfied;
3. the Export state transitions through blocked → ready → exporting → success and supports Export Another;
4. the retained exporter writes the expected package while the presentation-only `exporting` state is active;
5. dirty, processing-draft, destructive-remove, and error dialogs use centralized v1.2 presentation with safe Cancel defaults and technical details where applicable;
6. App Shell status language follows Figure/Export state without altering AnalysisSession dirty identity;
7. schema version 4, runtime version 1.1.0, and the `>=1200x760` window contract remain unchanged;
8. all earlier Stable v1.0/v1.1 and v1.2 Block 1–5 installed-wheel desktop smokes remain green.
