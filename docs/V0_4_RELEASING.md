# Releasing CatalysisWorkbench v0.4

v0.4 release work is deliberately separated from scientific implementation. Completion of the reviewed v0.4 scientific scope does not itself authorize a version bump, Git tag, GitHub Release, or package-registry publication.

This document records the v0.4 Gate A / Gate B / Gate C procedure and completed evidence. Gate A, Gate B, and Gate C are complete. Tag `v0.4.0` was created on 2026-08-25 and reverse-verified on the reviewed release commit. GitHub Release creation is a later separate action; package-registry publication remains a still-later independent boundary.

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

## Gate B — completed final `0.4.0` candidate

Gate B / Issue #105 / PR #106 was performed on branch `release/v0.4-gate-b`, created directly from reviewed Gate-A `main` commit `ce06abc11559fa7679869fc83a59356735ce6824` after explicit user authorization.

Gate B changed both version declarations together:

- `[project].version`: `0.3.0` -> `0.4.0`;
- `catalysis_workbench.__version__`: `0.3.0` -> `0.4.0`.

Gate B contained no new scientific feature work. The final exact head satisfied all release criteria: Ruff/full pytest, wheel build/install, `pip check`, exact distribution/runtime version equality, installed-source verification, all documented package-level `__all__` surfaces including product analysis, Matplotlib-lazy numerical imports, the retained v0.3 numerical release audit, all reviewed v0.4 installed smokes, and all seven documented quickstarts.

Final Gate-B evidence:

- branch base: `ce06abc11559fa7679869fc83a59356735ce6824`;
- final PR head: `ae3dc21b1a3a4e907d8c39eb85d3dbebefd8fbb4`;
- exact-head CI #304 / run `32759679632`: success;
- formal reviews: `5011014348`, `5011017132`;
- merge gate: behind=0, mergeable=true, review threads=0;
- expected-head squash merge / reviewed release commit: `bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6`;
- `main` was directly re-read and verified at the same commit;
- Issue #105: completed/closed.

Gate B established the reviewed `0.4.0` release commit on `main` but intentionally created no Git tag, GitHub Release, or package-registry publication.

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

## Gate C — completed `v0.4.0` tag boundary

Gate C began only after Gate B was squash-merged and the intended release commit was re-read directly from `main`. Explicit user authorization was given before tag creation.

Pre-tag verification confirmed:

1. `main` was exactly `bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6`;
2. distribution metadata and runtime `__version__` both reported `0.4.0`;
3. `CHANGELOG.md` release date `2026-08-25` matched the actual local tag date;
4. no unreviewed release-critical change had intervened;
5. tag `v0.4.0` did not already exist;
6. prior tag `v0.3.0` remained fixed on `845ac4c15d399a8816c7ba66d61ea6ec4cc11293`.

Gate C / Issue #107 then created tag `v0.4.0`. Reverse verification proved:

- `v0.4.0` resolves exactly to `bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6` with no ahead/behind drift;
- `pyproject.toml` read through the tag reports `0.4.0`;
- `src/catalysis_workbench/__init__.py` read through the tag reports `__version__ = "0.4.0"`;
- `main` remained unchanged by tag creation;
- `v0.3.0` remained unchanged;
- Issue #107 was closed as completed after all reverse checks passed.

Gate C created no GitHub Release and performed no package-registry publication.

## Post-tag documentation synchronization

Issue #108 is the routine docs-only checkpoint that replaces stale Gate-B/tag-pending wording with the verified tagged `v0.4.0` state. Its scope is restricted to README/release-plan/roadmap/changelog status synchronization; it must not alter scientific code, public API, dependencies, version declarations, or either immutable tag.

After #108 merges, `main` and `v0.4.0` must be reverified before the next release action.

## GitHub Release and package-registry boundaries

A Git tag does not itself publish a GitHub Release, and neither a tag nor GitHub Release authorizes package-registry publication.

The user's current `继续推进` instruction explicitly authorizes creation of the GitHub Release for the existing, already verified `v0.4.0` tag after Issue #108 is merged and reverified. Package-registry publication remains a separate policy/action and is not authorized.

GitHub Release and any later PyPI/other registry publication must preserve artifact provenance, credentials/account ownership, licensing/distributability, reproducibility, signing/attestation where applicable, and intended public/private distribution.

## Drift and failure policy

If a release-gate head changes after CI or review, prior exact-head evidence is stale. Rerun the affected checks and review on the new head.

If `main` moves while a release PR is open, verify branch/base drift before merge and resolve it explicitly. Never merge a stale release head merely because an older CI run was green.

If release hardening exposes a real API or packaging defect, fix it explicitly with regression coverage. If it exposes a scientific defect, route the defect through normal scientific/API compatibility discipline rather than weakening the release audit.

## Historical Gate-B non-actions

Gate B was required to:

- not create or move `v0.4.0`;
- not move or recreate `v0.3.0`;
- not create a GitHub Release;
- not publish a package;
- not add a new scientific module or scientific algorithm;
- not hide or relax an incompatibility merely to satisfy CI;
- not treat editable-install success as wheel-install evidence;
- not reuse CI/review evidence after the PR head changed.

Those constraints were satisfied. The later Gate C tag action and current post-tag documentation synchronization are separate, audited steps.