# Releasing CatalysisWorkbench v0.4

v0.4 release work is deliberately separated from scientific implementation. Completion of the reviewed v0.4 scientific scope does not itself authorize a version bump, Git tag, GitHub Release, or package-registry publication.

This document records the v0.4 Gate A / Gate B / Gate C procedure. Gate A is complete. Gate B is the separately authorized final-version candidate. Gate C tagging, GitHub Release creation, and package-registry publication remain separate later boundaries.

## Frozen v0.4 scientific scope

The v0.4 scientific scope is frozen to the seven reviewed implementation blocks merged before release hardening:

1. shared constrained peak fitting — Issue #75 / PR #76;
2. XPS preparation — Issue #79 / PR #80;
3. constrained XPS fitting — Issue #83 / PR #84;
4. XPS publication plotting and diagnostics — Issue #87 / PR #88;
5. EIS semantics, circuit fitting, Nyquist/Bode plotting and diagnostics — Issue #91 / PR #92;
6. quantitative BET fitting — Issue #95 / PR #96;
7. product calibration and inverse sample quantification — Issue #99 / PR #100.

The scientific-completion documentation checkpoint is Issue #101 / PR #102. Gate A began from reviewed `main` commit `a02df77d078671e24b07b37f6196204e312c9146`.

No new scientific algorithm, hidden scientific default, data-model reinterpretation, or visualization framework belongs in the release gates.

## Immutable prior release

The existing `v0.3.0` tag remains immutable and resolves exactly to `845ac4c15d399a8816c7ba66d61ea6ec4cc11293`. v0.4 release work must not move or recreate that tag.

## Gate A — completed frozen-scope release hardening

Gate A / Issue #103 / PR #104 completed the frozen-scope installed-wheel/public-API audit while intentionally retaining distribution/runtime version `0.3.0`.

Final Gate-A evidence:

- branch base: `a02df77d078671e24b07b37f6196204e312c9146`;
- final PR head: `9d79845d6fae253b01a46794c3c055e4966c6e55`;
- exact-head CI #302 / run `32758548117`: success;
- formal reviews: `5010905065`, `5010908809`;
- merge gate: behind=0, mergeable=true, review threads=0;
- expected-head squash merge: `ce06abc11559fa7679869fc83a59356735ce6824`;
- Issue #103: completed/closed after direct `main` verification.

Gate A added the unified `tests/installed_v04_release_smoke.py` audit and wired it into CI. The audit proves a fresh wheel install independently of editable source, checks distribution/runtime version equality, checks every documented package-level `__all__` surface including `catalysis_workbench.experimental.product`, verifies numerical imports remain Matplotlib-lazy before plotting, and executes the retained v0.3 release audit plus reviewed v0.4 shared-fitting, XPS, EIS, quantitative-BET, and product-calibration installed smokes. Existing installed API/module smokes and all seven documented quickstarts remain enforced.

Gate A created no v0.4 tag, GitHub Release, or package publication and changed no scientific semantics.

## Gate B — authorized final `0.4.0` candidate

Gate B is tracked by Issue #105 on branch `release/v0.4-gate-b`, created directly from reviewed Gate-A `main` commit `ce06abc11559fa7679869fc83a59356735ce6824` after explicit user authorization.

Gate B changes both version declarations together:

- `[project].version`: `0.3.0` -> `0.4.0`;
- `catalysis_workbench.__version__`: `0.3.0` -> `0.4.0`.

Gate B contains no new scientific feature work. Before it may merge, the final exact head must satisfy all of the following:

1. Ruff and the complete pytest suite pass with `0.4.0` in the source tree.
2. CI builds the final `catalysis_workbench-0.4.0-*.whl` artifact from that exact head.
3. A fresh virtual environment installs the wheel and `pip check` succeeds.
4. Installed distribution metadata and runtime `__version__` both report exactly `0.4.0`.
5. Installed imports are proven to resolve outside the repository `src/` tree.
6. Every documented package-level `__all__` surface resolves from the installed wheel, including the product-analysis surface.
7. The unified v0.4 installed-wheel audit passes unchanged except for the expected release version being `0.4.0`.
8. The retained v0.3 numerical release audit, module-specific installed smokes, reviewed v0.4 smokes, and all seven documented quickstarts pass on the same installed `0.4.0` wheel.
9. Numerical processing/electrochemistry/characterization/product imports remain Matplotlib-lazy before plotting is requested.
10. `CHANGELOG.md` contains an explicit `[0.4.0]` candidate section with intended release date `2026-08-25`.
11. README and central release/status documentation describe the final-version candidate consistently and do not claim that tag `v0.4.0` already exists.
12. `v0.3.0` remains fixed on `845ac4c15d399a8816c7ba66d61ea6ec4cc11293`.
13. No `v0.4.0` tag, GitHub Release, or package-registry publication is created by Gate B.
14. Formal release/API/packaging/version review has no unresolved blockers.
15. If the PR head changes after a finding is fixed, previous CI and review evidence is stale and must be rerun.
16. A second formal review is performed on the final exact head.
17. The merge gate confirms behind=0, mergeable=true, review threads=0, and that the exact head being merged is the one that passed final CI/review.
18. Merge uses expected-head squash merge, followed by direct `main` verification and Issue #105 closure.

Merging Gate B will establish the reviewed `0.4.0` release commit on `main`; it will still not create a Git tag.

## Unified installed-wheel v0.4 audit

`tests/installed_v04_release_smoke.py` runs inside a fresh environment containing the built wheel and its declared dependencies. It verifies packaging/public-API invariants before invoking retained installed scientific smokes as independent subprocesses with the same installed interpreter.

The unified audit covers:

- installed-source location rather than editable checkout source;
- runtime/distribution version agreement and explicit expected gate version;
- all documented public `__all__` surfaces, including product analysis;
- Matplotlib-lazy numerical public imports before plotting;
- retained v0.3 release numerical audit;
- shared constrained peak fitting;
- XPS preparation, constrained fitting, plotting and diagnostics;
- EIS fitting/diagnostics/plotting;
- quantitative BET fitting/plotting;
- product calibration, inverse quantification, replicate summary and plotting.

The existing scientific smokes remain authoritative for their module-specific numerical assertions. The unified release program composes them rather than copying a second set of scientific equations into release plumbing.

## Gate C — separate `v0.4.0` tag boundary

Creation of tag `v0.4.0` is not authorized by Gate B. Gate C may begin only after Gate B is squash-merged and the intended release commit is re-read directly from `main`.

Before tag creation, Gate C must verify at minimum:

1. `main` is exactly the reviewed Gate-B merge commit;
2. distribution metadata and runtime `__version__` both report `0.4.0`;
3. `CHANGELOG.md` release date matches the actual tag date; if the date changes, correct it in a reviewed commit and rerun the required release gate;
4. no unreviewed release-critical change has intervened;
5. tag `v0.4.0` does not already exist;
6. explicit user authorization has been given for creating tag `v0.4.0`.

After creation, the tag must be reverse-verified to resolve exactly to the reviewed release commit and reads through the tag must report version `0.4.0`.

## GitHub Release and package-registry boundaries

A Git tag does not authorize a GitHub Release, and neither a tag nor GitHub Release authorizes package-registry publication.

GitHub Release creation and PyPI/other registry publication remain separate policy/actions covering artifact provenance, credentials/account ownership, licensing/distributability, reproducibility, signing/attestation where applicable, and intended public/private distribution.

## Drift and failure policy

If a release-gate head changes after CI or review, prior exact-head evidence is stale. Rerun the affected checks and review on the new head.

If `main` moves while a release PR is open, verify branch/base drift before merge and resolve it explicitly. Never merge a stale release head merely because an older CI run was green.

If release hardening exposes a real API or packaging defect, fix it explicitly with regression coverage. If it exposes a scientific defect, route the defect through normal scientific/API compatibility discipline rather than weakening the release audit.

## What Gate B must not do

- do not create or move `v0.4.0`;
- do not move or recreate `v0.3.0`;
- do not create a GitHub Release;
- do not publish a package;
- do not add a new scientific module or scientific algorithm;
- do not hide or relax an incompatibility merely to satisfy CI;
- do not treat editable-install success as wheel-install evidence;
- do not reuse CI/review evidence after the PR head changes.
