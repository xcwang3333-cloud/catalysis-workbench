# CatalysisWorkbench Roadmap

CatalysisWorkbench is developed through staged scientific and product-maturity milestones. Stable GitHub Releases are intentionally infrequent and are not implied by a development version number.

## Release retention policy

- `v1.0.0` is the current stable baseline and resolves exactly to `22b944992bfd3791f91cc951f89eb22e8bf47325`.
- A public GitHub Release named `CatalysisWorkbench v1.0.0` exists for the stable v1.0 line.
- `v0.7.0` remains a retained historical stable Release/tag at `e3062fc12c794f54c7b7613875ec73608a587a59`.
- v0.8 and v0.9 are completed development milestones without routine standalone tags/Releases.
- the active v1.1 release-candidate development identity is `1.1.0.dev0`.
- PyPI/package-registry publication has not been performed.
- Stable 1.1 Gate A is in progress; final `1.1.0`, the v1.1 tag, GitHub Release, installers, and any registry publication remain later verified gates.

## v0.1–v0.4 — Core experimental analysis — historical complete

These milestones established immutable common XY data models and tabular IO; publication figure specifications; quantitative electrochemistry; extended characterization; constrained peak fitting; XPS; EIS; quantitative BET; and product calibration/quantification.

## v0.5 — Structures, XAS and basic DFT — historical complete

Delivered XAS/XANES, FT-/WT-EXAFS, neutral EXAFS fit summaries, immutable structures/adapters, explicit periodic geometry/coordination/comparison, static structure visualization, and explicit DFT energy bookkeeping.

## v0.6 — Electronic structure and catalysis thermodynamics — historical complete

Delivered DOS/PDOS and volumetric state, band centers, Bader accounting, COHP/ICOHP, geometry-bonding correlations, CHE/free-energy bookkeeping, and charge-density-difference arithmetic with strict compatibility/co-registration rules.

## v0.7 — Advanced computational visualization — retained historical stable release

`v0.7.0` remains retained at `e3062fc12c794f54c7b7613875ec73608a587a59`.

The reviewed scope includes scalar-field/volumetric scenes, density/ELF visualization, band structure, PROCAR/fat bands, LOCPOT/work functions, NEB barriers, and optional PyVista/VTK static volumetric 3-D rendering/export.

## v0.8 — Operando/time-resolved science — development milestone complete

Completed scope includes immutable exact-grid frame/stack state, exact measured-point operations, explicit cross-modal Pearson comparison, passive waterfall/heatmap/cut/trace visualization, and reviewed Raman/FTIR/XAS/XANES/XRD operando adapters and descriptor trajectories.

No routine v0.8 tag/GitHub Release was created.

## v0.9 — Reproducible workflows — development milestone complete

The v0.9 foundation established explicit sequential `WorkflowRecipe` state and serialization, literal fail-closed execution through source-controlled reviewed operations, deterministic workflow-run evidence, batching, scientific QA, publication presets, and reusable FigureSpec state.

Literal recipe order remains authoritative. The v0.9 foundation is not a DAG engine and does not authorize dynamic operation discovery or arbitrary serialized callables.

## v1.0 — Reproducible local catalysis workbench — stable

The six v1.0 development blocks delivered:

1. strict local workspace-manifest persistence and path confinement;
2. explicit asset import/catalog with content digests;
3. persistent evidence associations;
4. recipe/FigureSpec/preset composition state;
5. a GUI-neutral transaction-safe application/session controller; and
6. an optional lazy PySide6 desktop shell plus API/install hardening.

Stable 1.0 maturity gates then finalized and published `v1.0.0` at `22b944992bfd3791f91cc951f89eb22e8bf47325` with the corresponding GitHub Release. PyPI remained deferred.

The stable v1.0 public/application/workspace/desktop compatibility surfaces remain active regression gates during v1.1 development.

## v1.1 — Task-first research workbench — release hardening

Architecture authority is split between:

- [`V1_1_PLAN.md`](V1_1_PLAN.md) for Blocks 1–5; and
- [`V1_1_BLOCK6.md`](V1_1_BLOCK6.md) for final dogfooding/hardening.

The product goal is to make the ordinary desktop path task-driven rather than workspace-administration-driven:

```text
choose analysis goal
-> import and map scientific data
-> configure explicit processing
-> inspect live analysis
-> create publication Figure
-> export Figure Package + full source data
```

### Block 1 — Analysis Document + Home shell — complete

Task catalog, deterministic `AnalysisDocument`, task-first Home, recent projects, and first-save project lifecycle.

### Block 2 — Data Intake & Mapping — complete

Real tabular file intake, bounded preview, explicit X/Y scientific semantics, deterministic raw/mapping identity, workspace-owned raw copies, and mapped raw preview.

### Block 3 — Live Scientific Analysis — complete

Task-specific LSV processing, explicit FE/current pairing and partial-current calculation, Generic XY analysis-range cropping, deterministic internal workflow evaluation, invalid-draft handling, and previous-valid stale labeling.

### Block 4 — Figure Workbench — complete

Presentation-only FigureDraft state bound to exact scientific trace identities, stale/refresh semantics, publication preview, physical sizing, axes/display ranges, legend, typography, line and marker controls.

### Block 5 — Figure Package Export — complete

SVG/PDF/PNG figures plus XLSX/TXT scientific source data, path-independent semantic package identity, exact file hashes, workspace provenance, fail-closed staging/publication/rollback, and ordinary-language export preflight.

Exact post-merge Block-5 baseline: `eec2f85d117902459178f65c4543b5674de54912`. CI #832 and Stable 1.0 Readiness #94 succeeded on that exact main commit.

### Block 6 — Dogfooding Hardening & Desktop Cleanup — complete

Block 6 is the final v1.1 development block, not a release publication step.

Scope:

- full fresh-wheel Generic XY, LSV, and FE/Partial Current desktop journeys through package export and reopen verification;
- explicit Save Project directly from Export preflight;
- post-export Open Folder and Export Another actions;
- actionable desktop error summaries with original technical details retained;
- Recent Projects display caching during unrelated UI refreshes;
- a normal-user `catalysis-workbench` console command with Qt-free `--version` and explicit v1.1 `--project` routing; and
- central documentation synchronization with actual stable-v1.0/current-v1.1 state.

Block 6 explicitly does not add scientific algorithms, a new `AnalysisDocument` schema, hidden interpolation/resampling, autosave, automatic stale-Figure refresh, package overwrite/merge, new dependencies, server/cloud/background services, final-version changes, tags, Releases, or PyPI publication.

## Stable 1.1 release hardening

Block 6 completed the real installed-wheel dogfooding review and was squash-merged as `c81ee2e1aa8767e1560a14c5f7f4c1209fc4b6f9`. Post-merge CI #851 and Stable 1.0 Readiness #113 both succeeded on that exact commit.

The active release path is now staged:

1. **Gate A — release hardening:** retain `1.1.0.dev0`, add Stable 1.1 exact-wheel audit, Linux/Windows/macOS base + desktop install checks, wheel/sdist validation, and release documentation;
2. **Gate B — final-version candidate:** synchronize distribution/runtime/gate expectations to exact `1.1.0` without feature changes;
3. **Gate C — immutable tag:** create and reverse-verify `v1.1.0` only on the reviewed Gate-B release commit;
4. **Publication:** publish the GitHub Release from the verified tag; installers and package-registry publication remain separately verified operations.

Each merge and publication boundary remains fail-closed and exact-head evidence from an older candidate becomes stale after any change.

## Long-range non-goals unless separately re-architected

Current roadmap does not implicitly include:

- synthesis management or a complete electronic laboratory notebook;
- instrument control;
- full Rietveld or Artemis-class fitting engines;
- HPC job submission/full VASP workflow management;
- a new DAG scheduler/distributed queue;
- cloud synchronization/collaborative server state;
- arbitrary third-party code execution from workspace files;
- automatic recursive file discovery;
- automatic chemistry/species/phase assignment; or
- silent scientific correction/cleaning.

## Development rule

Before each major scientific, workflow, workspace, application, or visualization module, survey relevant open-source projects and record useful architecture/test ideas and license constraints. Architecture references do not imply code reuse or dependency adoption.

Promotion remains:

```text
scoped branch
-> Draft PR
-> exact-head CI
-> review/fix
-> final exact-head review
-> Ready
-> STOP
-> separate merge authorization
-> expected-head squash merge
-> post-merge verification
```
