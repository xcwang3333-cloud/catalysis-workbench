# Releasing CatalysisWorkbench v0.4

v0.4 release work is deliberately separated from scientific implementation. Completion of the reviewed v0.4 scientific scope does not itself authorize a version bump, Git tag, GitHub Release, or package-registry publication.

This document records the v0.4 Gate A release-hardening contract. Gate B final-version work, Gate C tagging, GitHub Release creation, and package-registry publication remain separate later boundaries.

## Frozen v0.4 scientific scope

The v0.4 scientific scope is frozen to the seven reviewed implementation blocks already merged before Gate A:

1. shared constrained peak fitting — Issue #75 / PR #76;
2. XPS preparation — Issue #79 / PR #80;
3. constrained XPS fitting — Issue #83 / PR #84;
4. XPS publication plotting and diagnostics — Issue #87 / PR #88;
5. EIS semantics, circuit fitting, Nyquist/Bode plotting and diagnostics — Issue #91 / PR #92;
6. quantitative BET fitting — Issue #95 / PR #96;
7. product calibration and inverse sample quantification — Issue #99 / PR #100.

The scientific-completion documentation checkpoint is Issue #101 / PR #102. Gate A begins from reviewed `main` commit `a02df77d078671e24b07b37f6196204e312c9146`.

No new scientific algorithm, hidden scientific default, data-model reinterpretation, or visualization framework belongs in Gate A.

## Immutable prior release and current version state

At Gate-A entry:

- distribution metadata reports `0.3.0`;
- runtime `catalysis_workbench.__version__` reports `0.3.0`;
- tag `v0.3.0` resolves exactly to `845ac4c15d399a8816c7ba66d61ea6ec4cc11293` and must not move;
- no v0.4 tag exists;
- no v0.4 GitHub Release exists;
- no package-registry publication is authorized by this gate.

Gate A intentionally keeps both distribution and runtime versions at `0.3.0`. A future `0.3.0 -> 0.4.0` transition belongs only to a separately authorized Gate B final-version candidate.

## Gate A — frozen-scope release hardening

Gate A is tracked by Issue #103 on branch `release/v0.4-gate-a`. Its purpose is to prove that the frozen source can be built, installed, imported, and exercised through the documented public surfaces independently of an editable checkout.

The Gate-A PR must satisfy all of the following on its final exact head:

1. Ruff passes across the repository.
2. The complete pytest suite passes.
3. A wheel builds from `pyproject.toml`.
4. A fresh virtual environment installs that wheel.
5. `python -m pip check` reports no broken requirements.
6. Installed imports are proven to resolve outside the repository `src/` tree.
7. Installed distribution metadata and runtime `catalysis_workbench.__version__` agree exactly and remain `0.3.0`.
8. Every documented package-level `__all__` surface is non-empty, duplicate-free, contains only valid string names, and every exported name resolves from the installed wheel.
9. The documented public-module audit includes `catalysis_workbench.experimental.product` in addition to the previously released public modules.
10. The declared `catalysis-workbench` console entry point resolves from installed distribution metadata and executes successfully from the installed wheel.
11. `tests/installed_v04_release_smoke.py` orchestrates the retained v0.3 release audit plus the reviewed installed-wheel v0.4 peak-fitting, XPS, EIS, quantitative-BET, and product-calibration smokes.
12. Existing module-specific installed smokes and documented quickstarts remain green.
13. Numerical processing/electrochemistry/characterization/product imports remain Matplotlib-lazy before plotting is requested.
14. Release documentation describes a pre-version/pre-tag Gate-A state and does not claim that v0.4 is released.
15. Formal release/API/packaging/compatibility review has no unresolved blockers.
16. If the PR head changes after any finding is fixed, CI and review evidence from the old head becomes stale and must be rerun.
17. A second formal review is performed on the final exact head.
18. The merge gate confirms the PR is not behind `main`, is mergeable, has no unresolved review threads, and uses the exact head SHA that passed the final evidence.
19. Merge is an expected-head squash merge, followed by direct `main` verification and Issue #103 closure.

Gate A may strengthen tests, release documentation, public-API validation, installed-wheel evidence, or packaging plumbing. It must not weaken an existing smoke or silently alter scientific semantics to make a release check pass.

## Packaging defect found during Gate-A preflight

Live preflight found that `[project.scripts]` declared:

```toml
catalysis-workbench = "catalysis_workbench.cli:main"
```

while `src/catalysis_workbench/cli.py` did not exist on either the Gate-A starting `main` commit or the immutable `v0.3.0` tag. Wheel installation could therefore create a console script whose target module was missing.

Gate A repairs this as release plumbing rather than as a new user-facing scientific CLI. The minimal `catalysis_workbench.cli:main` implementation provides argument parsing and `--version` only; it adds no analysis command, file-format adapter, scientific default, or alternate workflow. Unit and installed-wheel checks prevent a dangling declared console entry point from passing a later release gate unnoticed.

This historical defect does not justify moving the `v0.3.0` tag. The tag remains immutable evidence of the already reviewed v0.3 release state.

## Unified installed-wheel v0.4 audit

`tests/installed_v04_release_smoke.py` runs inside a fresh environment containing the built wheel and its declared dependencies. It verifies packaging invariants before invoking the retained installed scientific smokes as independent subprocesses with the same installed interpreter.

The unified audit covers:

- installed-source location rather than editable checkout source;
- runtime/distribution version agreement and explicit expected Gate-A version;
- all documented public `__all__` surfaces, including product analysis;
- Matplotlib-lazy numerical public imports before plotting;
- installed console-entry-point metadata, target resolution, executable presence, and exact `--version` output;
- retained v0.3 release numerical audit;
- shared constrained peak fitting;
- XPS preparation, constrained fitting, plotting and diagnostics;
- EIS fitting/diagnostics/plotting;
- quantitative BET fitting/plotting;
- product calibration, inverse quantification, replicate summary and plotting.

The existing scientific smokes remain authoritative for their module-specific numerical assertions. The unified Gate-A program composes them rather than copying a second set of scientific equations into release plumbing.

## Gate B — future final-version candidate boundary

Gate B is **not authorized by Gate A**. If separately authorized after Gate A is squash-merged and `main` is reverified, Gate B is the stage that may propose changing both version declarations together from `0.3.0` to `0.4.0` and rerunning the exact-wheel audit on that final-version artifact.

No Gate-A commit may be treated as permission to perform this version transition.

## Gate C — future tag boundary

Creation of `v0.4.0` is a separate explicit authorization boundary after a reviewed Gate-B release commit exists. The intended tag target must be re-read directly from `main`, exact version state must be verified, and the tag must be reverse-verified after creation.

Gate A creates no tag and moves no existing tag.

## GitHub Release and package-registry boundaries

A Git tag does not authorize a GitHub Release, and neither a tag nor GitHub Release authorizes package-registry publication.

GitHub Release creation and PyPI/other registry publication remain separate policy/actions covering artifact provenance, credentials/account ownership, licensing/distributability, reproducibility, signing/attestation where applicable, and intended public/private distribution.

## Drift and failure policy

If the Gate-A head changes after CI or review, prior exact-head evidence is stale. Rerun the affected checks and review on the new head.

If `main` moves while the release PR is open, verify branch/base drift before merge and resolve it explicitly. Never merge a stale release head merely because an older CI run was green.

If release hardening exposes a real API or packaging defect, fix it explicitly with regression coverage. If it exposes a scientific defect, route the defect through normal scientific/API compatibility discipline rather than weakening the release audit.

## What Gate A must not do

- do not change `0.3.0` to `0.4.0`;
- do not create or move `v0.4.0`;
- do not move or recreate `v0.3.0`;
- do not create a GitHub Release;
- do not publish a package;
- do not add a new scientific module or scientific algorithm;
- do not hide or relax an incompatibility merely to satisfy CI;
- do not treat editable-install success as wheel-install evidence;
- do not reuse CI/review evidence after the PR head changes.
