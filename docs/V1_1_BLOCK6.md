# CatalysisWorkbench v1.1 Block 6 — Dogfooding Hardening & Desktop Cleanup

## Purpose

Block 6 is the final v1.1 development hardening block. It does not add new scientific algorithms or a new analysis-document schema. Its job is to prove that the task-first path delivered by Blocks 1–5 works as an ordinary-user desktop product from real tabular input through saved publication output.

The frozen user path is:

```text
Home
  -> Data Intake & Mapping
  -> Live Scientific Analysis
  -> Figure Workbench
  -> Figure Package Export
```

The development version remains `1.1.0.dev0` throughout Block 6.

## Exact implementation baseline

Block 6 starts from the exact Block-5 post-merge main commit:

`eec2f85d117902459178f65c4543b5674de54912`

Block-5 post-merge CI #832 and Stable 1.0 Readiness #94 succeeded on that exact main SHA before Block 6 implementation started.

## Scope

### 1. End-to-end installed-wheel dogfooding

The final fresh-wheel desktop smoke must cover all three reviewed v1.1 tasks with real file-backed inputs:

- Generic XY;
- LSV / Polarization; and
- FE & Partial Current.

Each journey must reach a saved Figure Package. Saved projects are then closed and reopened, and the dogfood gate verifies deterministic scientific run identity, document identity, and current FigureDraft state after reopen.

FE and partial-current publication views remain independent outputs. They are not collapsed into one mixed-axis figure or one inferred scientific identity.

The cumulative negative gates from Blocks 2–5 remain active for invalid mapping, invalid processing drafts, stale figures, unsaved/dirty export, existing destinations, raw/workspace tampering, and publication rollback.

### 2. Export-page friction cleanup

The Figure Package page gains an explicit `Save Project` action when export preflight reports an unsaved or dirty project. Saving remains explicit: first save still requires a user-selected project location and there is no hidden autosave.

After a successful package export, the page exposes:

- `Open Folder` — asks the operating system to reveal/open the exported package directory; and
- `Export Another` — clears only the destination/success presentation state while retaining the user's selected export formats.

Block 6 does not add overwrite, merge, automatic suffixing, or stale-Figure auto-refresh behavior.

### 3. Actionable desktop errors

The final v1.1 desktop presents ordinary-language error summaries and keeps the exact original exception text in expandable technical details. This is presentation only and does not reinterpret or repair scientific/application state.

Known high-value cases include:

- project/workspace changed outside the current session;
- legacy v1.0 workspace opened through the v1.1 project path; and
- unavailable figure fonts.

Unknown errors retain the exact underlying message.

### 4. Recent Projects presentation cache

Recent Projects remains desktop-only `QSettings` history and is not scientific state. Block 6 caches the resolved recent-project display list while the stored `(path, last_opened)` records remain unchanged.

Ordinary processing/Figure refreshes therefore do not reopen every recent project from disk. Saving/opening/removing a recent project changes the settings fingerprint and naturally invalidates the cache.

### 5. Ordinary-user console command

The wheel exposes:

```text
catalysis-workbench
catalysis-workbench --project PATH
catalysis-workbench --version
```

`catalysis-workbench` starts the task-first v1.1 Home shell. `--project` explicitly opens a v1.1 analysis project. `--version` is Qt-free and must work from a base wheel without the `[desktop]` extra.

The existing Python `launch_desktop(root)` compatibility behavior is not changed. In particular, explicit legacy v1.0 launch paths remain available for integrations and the frozen top-level `desktop.__all__` contract is not widened.

If the user starts the graphical command without the desktop extra, the CLI returns an actionable installation message rather than an import traceback.

## Scientific and persistence invariants

Block 6 preserves all existing reviewed invariants:

- no new scientific processing;
- no hidden interpolation, resampling, smoothing, normalization, fitting, or unit conversion;
- no automatic FE/current pairing;
- no Figure display-range influence on exported scientific source arrays;
- no automatic stale-Figure refresh;
- no new `AnalysisDocument` schema version;
- no changes to scientific run/document identity from presentation-only operations;
- no automatic overwrite/merge of Figure Packages;
- no new runtime or optional dependency; and
- no database, server, cloud, watcher, or background-worker architecture.

## Validation gates

Block 6 is complete only when the final exact PR head satisfies all of the following:

| Gate | Requirement |
| --- | --- |
| B6-JOURNEY-01 | Generic XY real-file -> analysis -> Figure -> package -> reopen succeeds |
| B6-JOURNEY-02 | LSV real-file -> explicit processing -> Figure -> package -> reopen succeeds |
| B6-JOURNEY-03 | FE and partial-current views both export independently and reopen current |
| B6-UX-01 | Export preflight provides explicit Save Project and rechecks state after save |
| B6-UX-02 | Successful export provides Open Folder and Export Another |
| B6-UX-03 | Desktop errors provide actionable summary plus exact technical details |
| B6-UX-04 | Unchanged Recent Projects are not reopened on every presentation refresh |
| B6-CLI-01 | Fresh base wheel `catalysis-workbench --version` succeeds without Qt |
| B6-CLI-02 | Desktop creation still enters v1.1 Home by default |
| B6-CLI-03 | CLI `--project` routes explicitly to the v1.1 workbench path |
| B6-COMPAT-01 | Frozen v1.0 desktop/public compatibility gates remain green |
| B6-DOC-01 | Central docs describe stable v1.0 and current `1.1.0.dev0` truthfully |
| B6-CI | Regular CI and Stable 1.0 Readiness both succeed on the final exact head |

The final promotion loop remains Draft PR -> exact-head CI -> formal review -> Ready -> STOP. Ready status is not merge authorization.

## Release boundary

Block 6 does not authorize any of the following:

- changing `1.1.0.dev0` to final `1.1.0`;
- creating or moving a `v1.1.0` tag;
- creating a v1.1 GitHub Release; or
- publishing to PyPI or another package registry.

Those remain separate release decisions after dogfooding review.
