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

## Gate B — final-version candidate — active

Tracking: Issue #138. Branch: `release/v0.5-gate-b`. Exact base: `0ffcd7e4a89340d993468039ba83b44bc7638050`.

Gate B is explicitly authorized and owns final candidate version synchronization to `0.5.0`.

Gate B core actions:

- synchronize `[project].version` and runtime `__version__` to `0.5.0`;
- update the unified v0.5 expected-version value in CI to `0.5.0`;
- update direct release/changelog candidate state;
- build the exact candidate wheel in a fresh environment;
- run the unified v0.5 release audit, optional structure adapter audit, full tests, Ruff, `pip check`, and documented quickstarts;
- perform formal release/API/packaging review on the final exact head;
- merge only with behind=0, mergeable=true, unresolved review threads=0, and expected-head protection.

Broad README/MASTER_PLAN/ROADMAP/V0_5_PLAN overview-state synchronization is handled as a routine docs-only checkpoint immediately after Gate B merges and before Gate C.

Gate B does **not** create a tag, GitHub Release, or package-registry artifact.

### Gate B evidence

| Evidence | State |
| --- | --- |
| exact base | `0ffcd7e4a89340d993468039ba83b44bc7638050` |
| candidate version | `0.5.0` |
| final Gate-B head | pending |
| exact-head CI | pending |
| release/API/packaging review | pending |
| second final-head review | pending |
| merge gate | pending |
| squash merge / post-merge main | pending |
| `v0.4.0` invariant | must remain `bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6` |

## Gate C — tag creation and reverse verification

Gate C is a separate explicit authorization boundary. Do not infer authorization from completion of Gate A or Gate B.

After separate user authorization, Gate C may create the `v0.5.0` tag only on the exact reviewed Gate-B release commit. After the tag is pushed, reverse-verify:

- `v0.5.0` resolves exactly to the intended release commit;
- reads through the tag report distribution/runtime version `0.5.0`;
- `main` and prior immutable tags remain consistent;
- `v0.4.0` remains exactly `bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6`.

Do not move or recreate a release tag after verification.

## Post-tag actions

A Git tag does not itself create a GitHub Release or publish a Python package.

After Gate C, post-tag documentation synchronization may be handled as routine docs-only maintenance. GitHub Release creation is a separate release action. PyPI/package-registry publication remains deferred unless explicitly reauthorized in a future decision.

## Mandatory evidence discipline

For every gate:

1. record the exact head under review;
2. treat CI/reviews from older heads as stale after any head change;
3. require fresh exact-head CI before final review/merge;
4. keep scientific/API/version/tag/publication boundaries explicit;
5. use expected-head squash merge;
6. re-read `main` after merge;
7. never relabel PR CI as main-push CI evidence.
