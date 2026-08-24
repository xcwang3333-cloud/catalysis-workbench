# Releasing CatalysisWorkbench v0.2

v0.2 release work is deliberately separated from scientific feature implementation. Completing Issues #19-#28 does not by itself authorize a final version bump or Git tag.

This document applies to the v0.2 release line. The historical [`RELEASING.md`](RELEASING.md) remains the reviewed v0.1 release policy.

## Completed release state

The v0.2 release sequence is complete as of 2026-08-24:

- Gate A / Issue #43 / PR #44 completed release hardening at `0.2.0.dev0`;
- Gate B / Issue #45 / PR #46 finalized and validated distribution/runtime version `0.2.0`;
- Gate C / Issue #47 received explicit release authorization, created tag `v0.2.0`, and independently verified that the tag resolves exactly to reviewed release commit `1f7f4057397c61ef2f771b96fceadc8a529b62d9`;
- the changelog release date is `2026-08-24`;
- package-registry publication remains outside this release policy and is not authorized by the Git tag.

The Gate A/B/C sections below are retained as the reviewed procedure and audit record for how v0.2 was released.

## Historical starting state

At the start of Issue #43:

- the planned v0.2 feature sequence #19-#28 was complete on `main`;
- distribution metadata and runtime `__version__` both remained `0.2.0.dev0`;
- README, master plan, v0.2 plan, and changelog had been synchronized to the merged feature state;
- no `v0.2.0` tag existed as a consequence of feature completion;
- package-registry publication was not part of the gate.

## Gate A — release hardening at `0.2.0.dev0`

The release-hardening PR must keep both version declarations at `0.2.0.dev0` and satisfy all of the following on its exact reviewed head:

1. Ruff passes across the repository.
2. The complete pytest suite passes.
3. A wheel builds from `pyproject.toml`.
4. A fresh virtual environment installs that wheel.
5. `python -m pip check` reports no broken requirements.
6. `tests/installed_api_smoke.py` proves imports resolve from the installed wheel rather than the repository `src/` tree.
7. Installed distribution metadata and runtime `catalysis_workbench.__version__` agree exactly.
8. Every documented package-level `__all__` surface is non-empty, contains no duplicate/invalid export names, and every exported name resolves.
9. The installed-wheel smoke executes representative v0.2 electrochemistry calculations, not only import/name resolution. Compact synthetic checks cover Tafel, Faradaic efficiency, product partial-current density, activity normalization, TOF/TOFapp, Cdl/ECSA, stability, RRDE, and Koutecky-Levich with explicit scientific metadata/inputs.
10. The reviewed v0.1 LSV/XRD/Raman installed-wheel workflows and documented examples still run successfully.
11. README, CHANGELOG, MASTER_PLAN, V0_2_PLAN, and module documentation do not claim a final `0.2.0` release while the package remains a development version.
12. Formal release/API/packaging review has no unresolved blockers.
13. The release-hardening PR is squash-merged and `main` is rechecked before any final-version branch is created.

Gate A may strengthen tests/documentation/package validation, but it must not change reviewed scientific algorithms merely to make release checks pass.

## Gate B — final version candidate

Only after Gate A is complete may a separate final-version PR be created. That PR changes both version declarations together:

- `[project].version`: `0.2.0.dev0` -> `0.2.0`;
- `catalysis_workbench.__version__`: `0.2.0.dev0` -> `0.2.0`.

The final-version PR should contain no unrelated scientific feature work. Before it may merge:

1. Ruff and the complete pytest suite pass again with the final version in the source tree.
2. The built artifact is a `catalysis_workbench-0.2.0-*.whl` wheel.
3. A fresh environment installs the final-version wheel and `pip check` succeeds.
4. Installed distribution metadata and runtime `__version__` both report exactly `0.2.0`.
5. All public `__all__` surfaces resolve from the installed wheel.
6. The representative v0.2 installed-wheel smoke calculations pass unchanged with the final version.
7. The documented LSV/XRD/Raman installed workflows/examples pass unchanged.
8. `CHANGELOG.md` converts the v0.2 work from `[Unreleased]` into an explicit `[0.2.0]` candidate section with the intended release date, while README/release documents describe the candidate consistently and do not claim that a tag already exists.
9. Formal release/API/packaging/version review has no unresolved blockers.
10. The PR head SHA used by the merge gate is exactly the head that passed CI and review, and it is not behind `main`.

Merging Gate B establishes a reviewed `main` commit that reports `0.2.0`; it still does not itself create a Git tag.

## Gate C — explicit tag authorization

A `v0.2.0` tag may be created only after all of the following are true:

1. Gate B has been squash-merged to `main`.
2. The intended tag commit is re-read directly from `main` and reports runtime/distribution version `0.2.0`.
3. The exact release commit is the reviewed Gate-B merge result; no unreviewed release-critical change has intervened.
4. The changelog release date matches the actual tag date. If the date changed, update it in a reviewed commit and rerun the required gate before tagging.
5. Explicit release authorization has been given for creating `v0.2.0`.

Tagging is therefore a separate operation from both release-hardening and the version bump.

## Package-registry boundary

A Git tag does not authorize package publication. PyPI or other package-registry distribution requires a separately reviewed policy covering at minimum:

- repository/package licensing and distributability;
- credentials and account ownership;
- build artifact provenance and reproducibility;
- signing/attestation policy where applicable;
- the intended public/private distribution model.

Until that policy exists, the release process stops at the reviewed Git tag.

## Failure and drift policy

If a release-gate head changes after review or CI, the previous exact-head evidence is stale and must not be reused. Rerun the affected gate on the new head.

If `main` moves while a release PR is under review, re-check merge base and behind count before Ready/merge. Resolve drift explicitly rather than merging a stale release branch.

If a release check exposes a scientific/API defect, fix it through the normal reviewed feature/compatibility process; do not weaken the smoke gate or silently change semantics inside release plumbing.

## What not to do

- Do not change only one of the two version declarations.
- Do not tag a commit that still reports `0.2.0.dev0` as the final v0.2 release.
- Do not reuse a successful Gate-A development-version wheel as evidence for Gate B.
- Do not treat editable-install success as proof that the wheel is installable.
- Do not remove or weaken explicit scientific metadata from smoke fixtures to make the release test shorter.
- Do not mix v0.3 feature work into the v0.2 final-version PR.
- Do not create or publish a package-registry release without the separate distribution policy.