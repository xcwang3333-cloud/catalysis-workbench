# v1.2 Block 4 — Analysis Workspace

## Scope

Block 4 productizes the retained v1.1 analysis surface as a three-part desktop workspace:

```text
Data Navigator | Scientific Canvas | Processing Inspector
```

The block is presentation architecture only. It does not add scientific transforms, task discovery, data inference, evaluator behavior, or project-schema state.

## Data Navigator

The left pane retains the existing mapped-series lifecycle:

- add explicitly mapped data files;
- select one mapped series;
- rename and reorder mapped series;
- edit its explicit mapping;
- preview its materialized data;
- remove the selected series.

The existing `series_list`, mapping actions, drag/drop behavior, source ownership, `data_id`, `input_sha256`, and mapping semantics remain unchanged.

## Scientific Canvas

The center pane retains the existing Matplotlib scientific-result renderer and view selection. It adds explicit presentation states:

- `empty` — waiting for mapped data;
- `incomplete` — mapped input exists but the current task still needs valid input/configuration;
- `success` — the current scientific evaluation is valid;
- `error` — no valid current result is available;
- `stale` — a previous valid result is displayed while current processing fields are invalid and unapplied.

Large-series sampling remains display-only. It does not alter the materialized scientific arrays or workflow result. FE and partial-current views remain separate and preserve the reviewed no-interpolation behavior.

`Continue to Figure` remains enabled only for a current successful scientific result. This preserves both the existing Figure Workbench prerequisite and the outer v1.2 App Shell Figure gate.

## Processing Inspector

The right pane retains the existing `ProcessingPanel` scientific controls and is wrapped in a vertical scroll surface for ordinary laptop windows.

The reviewed processing contract is unchanged:

- the 200 ms debounce remains;
- only valid candidate settings can be committed;
- invalid drafts remain outside the `AnalysisDocument`;
- a previous valid result may remain visible as explicitly stale;
- per-series overrides use the existing task restrictions;
- FE/current pairing remains explicit;
- analysis ranges and electrochemical processing fields retain their existing types and validation.

## App Shell and compatibility bridge

The v1.2 App Shell is now the visible owner of cross-page navigation and global Undo, Redo, and Save commands. The old Analysis-page Home/Undo/Redo/Save widgets are therefore hidden from the product surface, but their widget attributes and signal wiring are retained as a compatibility bridge for the v1.1 desktop contract.

`title_edit` remains visible because the App Shell title is a status display rather than an editor. Existing public desktop attributes used by installed compatibility smokes remain available, including `title_edit`, `add_files_button`, `series_list`, `view_combo`, `preview_note`, `processing_panel`, `axes`, and `continue_button`.

## Presentation state boundary

Workspace state labels and semantic QSS are derived from existing session/evaluation state only. They do not enter `AnalysisDocument`, `workspace.json`, `project.json`, scientific hashes, FigureDraft, or FigureSpec.

Block 7 remains responsible for complete System/Light/Dark visual QA, high-DPI review, and responsive hardening. Block 4 does not lower the Stable v1.1 `>=1200x760` main-window minimum.

## Explicit non-scope

Block 4 does not change:

- `application.analysis` models or task IDs;
- `AnalysisSession` or `AnalysisEvaluator`;
- parser/mapping semantics or supported data suffixes;
- processing formulas, FE/current pairing semantics, or interpolation rules;
- project/workspace schema or persistence identities;
- FigureDraft, FigureSpec, Figure Workbench, or export semantics;
- runtime package version (`1.1.0`);
- signing-provider, certificate/private-key, installer publication, Release assets, tags, or PyPI/package-registry state.

## Validation

The cumulative installed-wheel desktop gate must retain all Stable v1.0/v1.1 and previous v1.2 smokes and add Block-4 coverage for:

- hidden legacy global chrome with compatibility attributes retained;
- visible Analysis title editing;
- Data Navigator and scrollable Processing Inspector composition;
- empty → success scientific-canvas transition;
- invalid processing draft → stale previous-valid-result state without document mutation;
- recovery to current success after discarding the draft;
- explicit error presentation state;
- Figure eligibility synchronized between `Continue to Figure` and the outer App Shell;
- Stable v1.1 `>=1200x760` minimum-window contract.
