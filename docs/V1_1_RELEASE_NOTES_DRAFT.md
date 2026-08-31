# CatalysisWorkbench v1.1 Release Notes — Draft

These notes describe the reviewed v1.1 release-candidate scope. Gate A release hardening is complete and Gate B now uses exact distribution/runtime identity `1.1.0`. This is still a final-version candidate: the `v1.1.0` tag, GitHub Release, installers, and registry publication remain later separately verified gates.

## Overview

CatalysisWorkbench v1.1 redesigns the optional desktop around a task-first research workflow while retaining the reviewed v1.0 scientific, workflow, provenance, workspace, and compatibility contracts.

The ordinary-user path is:

```text
Home
  -> choose LSV / FE & Partial Current / Generic XY
  -> Data Intake & Mapping
  -> Live Scientific Analysis
  -> Figure Workbench
  -> Figure Package Export
```

Projects remain local and explicit. Scientific transformations stay reviewable, deterministic where specified, and fail closed on incompatible state.

## Task-first project lifecycle

v1.1 adds a deterministic `AnalysisDocument` / `AnalysisSession` path alongside the retained v1.0 application compatibility surface. A task starts as a clean in-memory analysis; no project directory is created until an explicit Save Project action succeeds.

Saved v1.1 projects retain `workspace.json` plus `project.json`, deterministic document identities, explicit dirty/undo/redo behavior, concurrency checks, atomic control-file replacement, and fail-closed open/save semantics.

## Data intake and mapping

The reviewed desktop intake path supports `.csv`, `.txt`, `.tsv`, `.dat`, `.xlsx`, and `.xlsm` with bounded preview and explicit scientific X/Y mapping.

Raw byte identity, parser/mapping state, and scientific input identity are separated. Saved projects take verified ownership of raw copies. File paths do not become scientific identity, and the desktop does not recursively crawl directories or infer chemistry as authority.

## Live scientific analysis

The three v1.1 task families provide explicit reviewed processing:

- **LSV / Polarization:** explicit reference/RHE handling, iR correction, optional geometric-area normalization, output current-density unit, and scientific analysis range;
- **FE & Partial Current:** explicit current-series to FE-series pairing, compatible x-grid requirement, reviewed signed partial-current calculation, and independent FE/partial-current result views; and
- **Generic XY:** explicit scientific analysis-range cropping only.

Invalid processing drafts do not mutate committed scientific state. Hidden interpolation, resampling, nearest-match alignment, smoothing, baseline correction, fitting, normalization, automatic FE/current pairing, and silent scientific repair are not introduced.

## Figure Workbench

v1.1 adds presentation-only `FigureDraft` state bound to exact scientific trace identities. Users can control trace selection/order/labels, publication preset, physical figure size, axes/display ranges, legend, typography, lines, and markers without mutating scientific arrays or run identities.

Scientific analysis ranges and Figure display ranges remain separate. Stale figures are explicit and never silently refreshed.

## Figure Package export

Figure Packages export selected SVG/PDF/PNG figures together with full scientific source data in XLSX/TXT form. Packages retain path-independent semantic identity, exact file hashes, project/workspace provenance, and fail-closed staging/publication/rollback behavior.

Display limits do not crop the exported scientific source arrays. Existing destinations are not silently overwritten, merged, or auto-suffixed.

## Dogfooding hardening and desktop cleanup

The final v1.1 development block adds:

- complete fresh-wheel/offscreen Generic XY, LSV, and FE & Partial Current journeys from real files through package export and project reopen verification;
- explicit Save Project from export preflight;
- post-export Open Folder and Export Another actions;
- actionable ordinary-language errors with exact original exception text retained as technical details;
- presentation-only Recent Projects caching that avoids needless disk reopens;
- a normal-user `catalysis-workbench` command;
- explicit `--project PATH` launch into the v1.1 project path; and
- a Qt-free `--version` path that works from the base wheel.

## Compatibility and release hardening

Stable v1.0 public/application/workspace/desktop compatibility remains an active regression gate.

Stable 1.1 Gate A adds:

- a unified exact-wheel audit covering the frozen Stable 1.0 audit plus all reviewed v1.1 headless installed smokes;
- console-entry-point and Qt-free version verification;
- Linux/Windows/macOS isolated base and `[desktop]` installs on Python 3.11 and 3.14;
- exact wheel/sdist metadata and naming checks; and
- sdist-to-wheel rebuild validation.

The project remains BSD-3-Clause. The base package remains independent of optional Qt, pymatgen, PyVista, and VTK backends until those extras are explicitly used.

## Intentional non-goals

v1.1 does not add automatic chemistry/species/phase assignment, recursive project discovery, hidden scientific cleaning, workflow DAG inference, arbitrary serialized callable execution, database/server/cloud collaboration, background file watchers, automatic stale-Figure refresh, or implicit package overwrite/merge.

## Release status

Gate A proved release readiness at `1.1.0.dev0` and was merged as `843df51828d740405aa5365142541ed361e069cc`. Gate B synchronizes the exact candidate to `1.1.0` and must pass ordinary CI plus Stable 1.0 and Stable 1.1 readiness before review/merge. Tagging, GitHub Release publication, installers, and package-registry publication occur only after their own verification gates.
