# Releasing CatalysisWorkbench v0.3

v0.3 release work is deliberately separated from scientific feature implementation. Completing the reviewed v0.3 modules does not itself authorize a version bump, Git tag, or package-registry publication.

This document records the completed v0.3 Gate A / Gate B / Gate C procedure. The completed v0.2 procedure remains in [`V0_2_RELEASING.md`](V0_2_RELEASING.md).

## Frozen v0.3 scientific scope

The v0.3 release scope is frozen to four reviewed experimental-processing additions on top of the released v0.2 electrochemistry baseline:

1. FTIR / ATR-FTIR — Issue #50 / PR #51.
2. TGA / DTG / TPR / TPD thermal analysis — Issue #54 / PR #55.
3. Basic gas-sorption isotherm semantics and publication plotting — Issue #58 / PR #59.
4. ICP / elemental-composition integration — Issue #62 / PR #63.

The explicit scope decision after Issue #64 / PR #65 is to **defer shared peak-fitting to v0.4 and design it together with constrained XPS/spectroscopy consumers**. This avoids freezing model families, baseline coupling, parameter constraints/ties, uncertainty/covariance semantics, and fitting provenance before a concrete downstream consumer exists.

Quantitative BET fitting, XPS fitting, EIS fitting, product-calibration workflows, XAS, and other later-roadmap algorithms are not part of v0.3 release hardening.

## Completed v0.3 release state

The v0.3 Git release is complete as of 2026-08-24:

- Gate A / Issue #66 / PR #67 was squash-merged to `main` at `8a3ae75f43ffa7d808f2a431f6326912a5dff9c6` after exact-head CI and two-pass release/API/packaging/compatibility review while intentionally retaining version `0.2.0`.
- Gate B / Issue #68 / PR #69 was squash-merged to `main` at `845ac4c15d399a8816c7ba66d61ea6ec4cc11293` after the final `0.3.0` exact-wheel audit and two-pass release review.
- Gate C / Issue #70 was explicitly authorized, and tag `v0.3.0` was created and reverse-verified to resolve exactly to `845ac4c15d399a8816c7ba66d61ea6ec4cc11293`.
- Tagged distribution metadata and runtime `__version__` both report exactly `0.3.0`.
- `CHANGELOG.md` records release date `2026-08-24`.
- No scientific/API implementation changed during Gate C.
- No package-registry publication was performed; package publication remains a separate policy decision.

The `v0.3.0` tag is immutable release evidence for the reviewed Gate-B commit. Post-release documentation changes must not move or recreate that tag.

## Gate A completed state

Gate A / Issue #66 / PR #67 was squash-merged to `main` at `8a3ae75f43ffa7d808f2a431f6326912a5dff9c6` after exact-head CI and two-pass release/API/packaging/compatibility review. It hardened the complete frozen v0.3 scope while intentionally keeping distribution metadata and runtime `__version__` at `0.2.0`.

Gate A added and audited the unified installed-wheel v0.3 numerical smoke, the existing v0.2 electrochemistry installed API audit, module-specific thermal/sorption/composition installed smokes, all seven quickstarts, installed-source verification, `pip check`, complete documented `__all__` resolution, and Matplotlib-lazy numerical characterization imports. It did not create a `v0.3.0` tag or publish a package.

## Gate A — release hardening while version remains `0.2.0`

Gate A strengthens release evidence without changing the reviewed scientific scope. The Gate-A PR must keep both distribution and runtime versions at `0.2.0` and satisfy all of the following on its exact reviewed head:

1. Ruff passes across the repository.
2. The complete pytest suite passes.
3. A wheel builds from `pyproject.toml`.
4. A fresh virtual environment installs that wheel.
5. `python -m pip check` reports no broken requirements.
6. Installed imports are proven to resolve from the wheel rather than the repository `src/` tree.
7. Installed distribution metadata and runtime `catalysis_workbench.__version__` agree exactly and remain `0.2.0`.
8. Every documented package-level `__all__` surface is non-empty, contains no duplicate or invalid export names, and every exported name resolves.
9. `tests/installed_v03_release_smoke.py` executes representative, hand-verifiable numerical paths for all four frozen v0.3 modules from the installed wheel.
10. Existing v0.2 electrochemistry installed-wheel calculations continue to pass unchanged.
11. Existing module-specific thermal, sorption, and composition installed-wheel smokes continue to pass.
12. All seven documented quickstarts run successfully from the installed wheel.
13. Importing the numerical characterization surface remains Matplotlib-lazy before plotting is requested.
14. README, CHANGELOG, MASTER_PLAN, ROADMAP, and this release document consistently describe a pre-release Gate-A state and do not claim that `v0.3.0` is already released or tagged.
15. Formal release/API/packaging/compatibility review has no unresolved blockers.
16. A second independent review is performed on the final exact head after any fixes.
17. The PR is squash-merged and `main` is rechecked before a Gate-B final-version branch is created.

Gate A may strengthen tests, documentation, public-API validation, packaging checks, or release plumbing. It must not add new scientific features or silently change reviewed scientific semantics merely to satisfy a release check.

### Unified v0.3 installed-wheel audit

The Gate-A unified smoke is numerical rather than import-only. It verifies, at minimum:

- FTIR: explicit percent-transmittance to absorbance conversion plus the reviewed caller-window baseline/direct-band behavior;
- thermal analysis: explicit TGA reference normalization, DTG sign semantics, and measured-window TPR result;
- gas sorption: explicit adsorption-branch metadata, source direction, relative-pressure representation conversion, and measured-point window summary without BET fitting;
- ICP/composition: explicit solution-to-bulk mass balance, explicit mass-fraction unit conversion, and arithmetic mean/sample-SD/RSD replicate statistics without closure normalization.

The smoke intentionally does not perform hidden interpolation, smoothing, closure normalization, unit guessing, branch inference, peak fitting, BET fitting, calibration fitting, or other deferred analysis.

## Gate B completed state — final `0.3.0` version

Gate B / Issue #68 / PR #69 ran on branch `release/v0.3-gate-b`, created directly from the reviewed Gate-A `main` commit `8a3ae75f43ffa7d808f2a431f6326912a5dff9c6` after explicit user authorization. Its final exact PR head was `aa56cfe3d99f07a416bfcc8b199d5cbea34cbdc5`, and it was expected-head squash-merged to `main` as `845ac4c15d399a8816c7ba66d61ea6ec4cc11293`.

Gate B changed both version declarations together:

- `[project].version`: `0.2.0` -> `0.3.0`;
- `catalysis_workbench.__version__`: `0.2.0` -> `0.3.0`.

The exact-head CI built `catalysis_workbench-0.3.0-py3-none-any.whl`, installed it in a fresh environment, passed `pip check`, installed-source verification, all documented public `__all__` checks, the unified v0.3 numerical audit, existing v0.2 electrochemistry and module-specific smokes, and all seven documented quickstarts. Two formal release-review passes were anchored to the final exact head; the merge gate confirmed behind=0, mergeable state, and zero unresolved review threads.

The historical Gate-B acceptance contract was:

1. Ruff and the complete pytest suite pass again with the final version in the source tree.
2. The built artifact is a `catalysis_workbench-0.3.0-*.whl` wheel.
3. A fresh environment installs the final-version wheel and `pip check` succeeds.
4. Installed distribution metadata and runtime `__version__` both report exactly `0.3.0`.
5. All documented public `__all__` surfaces resolve from the installed wheel.
6. The unified v0.3 installed-wheel numerical audit passes unchanged except for the expected-version assertion being updated to `0.3.0`.
7. The existing v0.2 electrochemistry audit, module-specific v0.3 smokes, and all seven documented quickstarts pass unchanged.
8. `CHANGELOG.md` converts the current v0.3 `[Unreleased]` work into an explicit `[0.3.0]` candidate section with the intended release date.
9. README and release documents describe a final-version candidate consistently and do not claim that a tag already exists.
10. Formal release/API/packaging/version review has no unresolved blockers.
11. A second independent review is performed on the final exact head after any Gate-B fix; prior review evidence is stale if the head changes.
12. The PR head SHA used by the merge gate is exactly the head that passed CI and both review passes, it is not behind `main`, and no review threads remain unresolved.

Merging Gate B established the reviewed `0.3.0` release commit but did not itself create the Git tag.

## Gate C completed state — explicit `v0.3.0` tag authorization

Gate C / Issue #70 began only after explicit user authorization. Before tag creation, `main` was re-read and confirmed to remain exactly `845ac4c15d399a8816c7ba66d61ea6ec4cc11293`; distribution/runtime versions were both `0.3.0`; the changelog release date matched 2026-08-24; and `v0.3.0` did not pre-exist.

Tag `v0.3.0` was then created on the reviewed Gate-B merge commit. Reverse verification through GitHub resolved `v0.3.0` exactly to `845ac4c15d399a8816c7ba66d61ea6ec4cc11293`, and reads through the tag confirmed distribution/runtime version `0.3.0`. Issue #70 was closed completed only after this verification.

The historical Gate-C authorization criteria were:

1. Gate B has been squash-merged to `main`.
2. The intended tag commit is re-read directly from `main` and reports runtime/distribution version `0.3.0`.
3. The exact release commit is the reviewed Gate-B merge result; no unreviewed release-critical change has intervened.
4. The changelog release date matches the actual tag date. If the date changes, correct it in a reviewed commit and rerun the required gate before tagging.
5. **Explicit user authorization has been given for creating tag `v0.3.0`.**

Tagging remains a separate operation from both release hardening and the final version bump.

## Package-registry boundary

A Git tag does not authorize package publication. PyPI or any other package-registry distribution remains a separate policy decision covering at minimum:

- repository/package licensing and distributability;
- credentials and account ownership;
- build-artifact provenance and reproducibility;
- signing/attestation policy where applicable;
- intended public/private distribution model.

Until such a policy is reviewed and explicitly authorized, the v0.3 release process stops at the reviewed Git tag.

## Failure and drift policy

If a release-gate head changes after review or CI, the previous exact-head evidence is stale and must not be reused. Rerun the affected gate on the new head.

If `main` moves while a release PR is under review, re-check merge base and behind count before Ready/merge. Resolve drift explicitly rather than merging a stale release branch.

If a release check exposes a scientific/API defect, fix the defect explicitly with regression coverage through the normal compatibility process. Do not weaken the smoke gate, loosen scientific validation, or silently change semantics inside release plumbing.

## What not to do

- Do not add shared peak-fitting back into v0.3 after the scope freeze without a new explicit architecture decision.
- Do not change only one of the two version declarations in Gate B.
- Do not create `v0.3.0` from a commit that still reports `0.2.0`.
- Do not reuse a successful Gate-A `0.2.0` wheel as Gate-B evidence for `0.3.0`.
- Do not treat editable-install success as proof that the wheel is installable.
- Do not remove explicit scientific metadata from smoke fixtures to make the release audit shorter.
- Do not mix v0.4 XPS/BET/EIS or other new feature work into the v0.3 final-version PR.
- Do not move or recreate the existing `v0.3.0` tag during post-release documentation work.
- Do not create or publish a package-registry release without the separate distribution policy.