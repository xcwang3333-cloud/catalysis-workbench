# CatalysisWorkbench v0.5 Release Procedure

This document records the release-hardening procedure and evidence for the frozen v0.5 XAS, structure, and basic DFT-energetics scope. GitHub remains the operational source of truth; this file must be synchronized to merged reality when a gate completes.

## Frozen release baseline

- Scientific-completion commit: `a7ebd009ec83b0aeb068ad2d2f6712c17a783f1f`.
- Completion-state documentation merge: `8c958ffc29a36afa9340cada2239b51520c87a3d` (Issue #134 / PR #135).
- Distribution version before Gate A: `0.4.0`.
- Runtime `__version__` before Gate A: `0.4.0`.
- Prior release tag: `v0.4.0 -> bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6`, immutable.
- The v0.4 GitHub Release is published from that existing tag.
- PyPI/package-registry publication is deferred; Issue #113 is closed `not_planned`.

The frozen v0.5 scientific blocks are:

1. XAS/XANES — #117 / #118.
2. FT-EXAFS — #119 / #120.
3. WT-EXAFS — #121 / #122.
4. EXAFS fitting-result summaries — #123 / #124.
5. Atomic structures and POSCAR/CONTCAR/CIF/XYZ adapters — #125 / #126.
6. Geometry/coordination/structure comparison — #127 / #129.
7. Static structure visualization — #130 / #131.
8. Basic DFT energetics — #132 / #133.

Issue #128 was a stale duplicate of the completed geometry block and was closed `duplicate` before Gate A.

## Gate A — frozen-scope release hardening — complete

Tracking: Issue #136 / PR #137. Branch: `release/v0.5-gate-a`. Exact base: `8c958ffc29a36afa9340cada2239b51520c87a3d`.

Gate A deliberately did not change the version. Both distribution and runtime version remained `0.4.0`.

Gate A established a unified fresh-wheel audit that:

- proves imports come from the installed wheel rather than repository `src/`;
- verifies distribution metadata version == runtime `__version__` == the gate-supplied expected version;
- resolves every documented package-level public `__all__`, including `catalysis_workbench.computation`;
- verifies numerical public imports remain Matplotlib-lazy;
- reuses the reviewed v0.4 unified installed-wheel audit;
- reruns all reviewed base-environment v0.5 installed smokes as independent subprocesses;
- retains the optional `[structure]` adapter audit in a separate fresh environment;
- retains the documented LSV/XRD/Raman/FTIR/thermal/sorption/composition quickstarts.

### Gate A evidence

| Evidence | State |
| --- | --- |
| exact base | `8c958ffc29a36afa9340cada2239b51520c87a3d` |
| final Gate-A head | `fb13cdbf633366a0840f5f2e21af215bee47b133` |
| exact-head CI | CI #358 / run `32799486710` — success |
| release/API/packaging review | `5014277750` — pass |
| second final-head review | `5014278425` — pass |
| merge gate | behind=0; mergeable=true; unresolved threads=0 |
| squash merge / post-merge main | `0ffcd7e4a89340d993468039ba83b44bc7638050` |
| version after Gate A | `0.4.0` |
| `v0.4.0` invariant | `bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6` |

## Gate B — final-version candidate — complete

Tracking: Issue #138 / PR #139. Branch: `release/v0.5-gate-b`. Exact base: `0ffcd7e4a89340d993468039ba83b44bc7638050`.

Gate B synchronized `[project].version`, runtime `__version__`, and the unified installed-wheel expected version to `0.5.0`, then validated the exact candidate wheel in a fresh environment.

### Gate B evidence

| Evidence | State |
| --- | --- |
| exact base | `0ffcd7e4a89340d993468039ba83b44bc7638050` |
| candidate version | `0.5.0` |
| final Gate-B head | `b95841ed472aff1fa4d05af7335547ee5c3cd611` |
| exact-head CI | CI #360 / run `32800514038` — success |
| release/API/packaging review | `5014348449` — pass |
| second final-head review | `5014349058` — pass |
| merge gate | behind=0; mergeable=true; unresolved threads=0 |
| squash merge / post-merge main | `9400ac0044ac333d2cae228554c08d955a816a4c` |
| distribution/runtime version | `0.5.0` |
| `v0.4.0` invariant | `bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6` |

The exact candidate wheel passed Ruff/full pytest, fresh installation, `pip check`, the unified v0.5 release audit, optional `[structure]` adapter audit, and all documented quickstarts.

Gate B did **not** create a tag, GitHub Release, or package-registry artifact.

Post-Gate-B overview/changelog synchronization completed through Issue #140 / PR #141, producing post-docs `main=85d19870ff6b117318f903d59a9e16b35ac19830` before Gate C.

## Gate C — tag creation and reverse verification — complete

Tracking: Issue #142.

After separate user authorization, lightweight tag `v0.5.0` was created and pushed exactly on the reviewed Gate-B release commit `9400ac0044ac333d2cae228554c08d955a816a4c`.

### Gate C evidence

| Evidence | State |
| --- | --- |
| authorized tag | `v0.5.0` |
| exact target commit | `9400ac0044ac333d2cae228554c08d955a816a4c` |
| reverse verification | tag and target commit are identical |
| distribution version through tag | `0.5.0` |
| runtime `__version__` through tag | `0.5.0` |
| post-Gate-B-docs `main` after tag push | `85d19870ff6b117318f903d59a9e16b35ac19830` |
| `v0.4.0` invariant | `bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6` |
| tracking Issue | #142 — completed |

The release tag must not be moved or recreated after verification.

## GitHub Release — complete

Tracking: Issue #144.

The public GitHub Release `CatalysisWorkbench v0.5.0` was published from the existing verified `v0.5.0` tag on 2026-08-25. The Release is not a draft or prerelease, and its release notes record the reviewed v0.5 scientific scope plus Gate A/B/C validation evidence.

Publishing the GitHub Release did not move the tag or publish a Python package-registry artifact.

## Post-release state

Final post-release documentation synchronization is tracked by Issue #143 and is docs/changelog only.

PyPI/package-registry publication remains deferred unless explicitly reauthorized in a future decision.

## Mandatory evidence discipline

For every gate:

1. record the exact head under review;
2. treat CI/reviews from older heads as stale after any head change;
3. require fresh exact-head CI before final review/merge;
4. keep scientific/API/version/tag/publication boundaries explicit;
5. use expected-head squash merge;
6. re-read `main` after merge;
7. never relabel PR CI as main-push CI evidence.
