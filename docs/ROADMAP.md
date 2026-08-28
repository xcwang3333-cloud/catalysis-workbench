# CatalysisWorkbench Roadmap

CatalysisWorkbench is developed through staged scientific and product-maturity milestones. Stable GitHub Releases are intentionally infrequent and are not implied by a development version number.

## Release retention policy

- `v0.7.0` is the only currently retained stable GitHub Release/tag.
- v0.1-v0.6 remain valid historical milestones; their old tag/Release artifacts were intentionally removed while implementation, Issue/PR, CI and documentation provenance remains retained.
- v0.8 and v0.9 are completed development milestones with no routine standalone tag/GitHub Release.
- the active v1.0 development identity is `1.0.0.dev0`.
- stable `1.0.0`, a v1.0 tag, GitHub Release and PyPI/package-registry publication are separate future decisions.

## v0.1-v0.4 — Core experimental analysis — historical complete

These milestones established:

- immutable common XY data models and tabular IO;
- reusable processing, publication figure specifications and exact-size export;
- quantitative electrochemistry including Tafel, FE, partial current, activity, TOF, CV/Cdl/ECSA, stability and RRDE/K-L;
- extended characterization including XRD, Raman, FTIR, thermal, sorption and ICP/composition;
- constrained peak fitting, XPS, EIS, quantitative BET and product calibration/quantification.

Detailed implementation and historical release evidence remains in the retained `V0_X_*` and technique-specific documents.

## v0.5 — Structures, XAS and basic DFT — historical complete

Delivered XAS/XANES, FT-/WT-EXAFS, neutral EXAFS fit summaries, immutable structures/adapters, explicit periodic geometry/coordination/comparison, static structure visualization and explicit DFT energy bookkeeping.

## v0.6 — Electronic structure and catalysis thermodynamics — historical complete

Delivered electronic DOS/PDOS and volumetric state, band centers, Bader accounting, COHP/ICOHP, geometry-bonding correlations, CHE/free-energy bookkeeping and charge-density-difference arithmetic with strict compatibility/co-registration rules.

## v0.7 — Advanced computational visualization — retained stable release

`v0.7.0` remains the retained stable GitHub Release/tag at `e3062fc12c794f54c7b7613875ec73608a587a59`.

The reviewed scope includes scalar-field/volumetric scenes, density/ELF visualization, band structure, PROCAR/fat bands, LOCPOT/work functions, NEB barriers and optional PyVista/VTK static volumetric 3-D rendering/export.

## v0.8 — Operando/time-resolved science — development milestone complete

Completed scope:

- immutable exact-grid frame/stack state;
- exact measured-point operations and derived traces;
- explicit cross-modal Pearson comparison;
- passive waterfall, heatmap, frame-cut and trace visualization;
- reviewed Raman/FTIR operando adapters and trajectories;
- reviewed XAS/XANES operando adapters and descriptor trajectories;
- reviewed XRD operando adapters, window integration, observed peak positions and compatible fit-derived trajectories.

No standalone v0.8 release cycle, `v0.8.0` tag or GitHub Release is planned.

## v0.9 — Reproducible workflows — development milestone complete

The v0.9 development line established the reproducibility foundation consumed by v1.0:

- explicit sequential `WorkflowRecipe` state and serialization;
- literal fail-closed recipe execution through source-controlled reviewed operations;
- deterministic workflow run evidence;
- batch execution/evidence;
- scientific QA findings/reports;
- publication presets and reusable figure state;
- first interactive FigureSpec editing integration.

Literal recipe order remains authoritative. The v0.9 foundation is not a DAG engine and does not authorize dynamic operation discovery or arbitrary serialized callables.

No routine `v0.9` tag/GitHub Release is planned.

## v1.0 — Personal local catalysis workbench — current development line

Architecture authority: [`V1_0_PLAN.md`](V1_0_PLAN.md).

The six-block v1.0 plan is:

1. **Workspace foundation — complete.** Strict local manifest persistence, deterministic identity and workspace-owned path confinement.
2. **Explicit asset import/catalog — complete.** Caller-selected sources, stable asset identity, explicit copy/reference policy and content digests.
3. **Persistent evidence ledger — complete.** File-backed associations among existing reviewed recipe/run/batch/QA/content identities.
4. **Workspace recipe/figure composition — complete.** Reproducible recipe/FigureSpec/preset/artifact associations with content/evidence digest pinning and literal ordered recipe edits.
5. **GUI-neutral application/session controller — complete.** Transaction-safe local session state, explicit workflow/QA orchestration and FigureSpec editing without GUI-toolkit coupling.
6. **Optional desktop shell + v1.0 API hardening — current/final development block.** Optional PySide6-Essentials Qt Widgets shell, explicit workspace/file interactions, recipe/evidence/QA/figure presentation, import laziness, installed-wheel desktop CI, compatibility review and documentation synchronization.

The v1.0 desktop is presentation over reviewed application/workflow/scientific contracts; it is not a new scientific execution engine.

## Stable 1.0 maturity gate — future and separately authorized

Completing the six development blocks does not itself create a stable release. A later stable-1.0 decision must separately review at least:

- final public API compatibility and documented surface;
- exact development-to-final version transition;
- optional desktop dependency/license/distribution state;
- fresh-wheel and optional-extra installation on supported platforms;
- release notes and retained release policy;
- exact tag target;
- GitHub Release publication; and
- whether PyPI/package-registry publication is desired.

No stable version, tag, Release or registry publication may happen as a side effect of a feature PR.

## Explicitly out of scope for current v1.0

Unless re-architected later, v1.0 does not include:

- synthesis management or a full electronic laboratory notebook;
- TEM/SEM image processing or atom recognition;
- instrument control;
- complete Rietveld or Artemis-class fitting engines;
- HPC job submission or full VASP workflow management;
- a new DAG scheduler, distributed queues or automatic parallel execution;
- cloud synchronization or collaborative server state;
- arbitrary third-party code execution from workspace files;
- automatic recursive file discovery;
- automatic chemistry/species/phase assignment;
- silent scientific correction/cleaning; or
- mandatory SQL/database infrastructure.

## Development rule

Before each major scientific, workflow, workspace, application or visualization module, survey relevant open-source projects and record useful architecture/test ideas and license constraints. Architecture references do not imply code reuse or dependency adoption.

Promotion remains:

```text
scoped branch → Draft PR → exact-head CI → review/fix → final exact-head review
→ Ready → separate merge authorization → expected-head merge → post-merge verification
```
