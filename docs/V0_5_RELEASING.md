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

## Gate A — frozen-scope release hardening

Tracking: Issue #136. Branch: `release/v0.5-gate-a`. Exact base: `8c958ffc29a36afa9340cada2239b51520c87a3d`.

Gate A is deliberately **not** a version-bump gate. Both distribution and runtime version remain `0.4.0` throughout Gate A.

Gate A must establish a unified fresh-wheel audit that:

- proves imports come from the installed wheel rather than repository `src/`;
- verifies distribution metadata version == runtime `__version__` == the gate-supplied expected version;
- resolves every documented package-level public `__all__`, including `catalysis_workbench.computation`;
- verifies numerical public imports remain Matplotlib-lazy;
- reuses the reviewed v0.4 unified installed-wheel audit;
- reruns all reviewed base-environment v0.5 installed smokes as independent subprocesses;
- retains the optional `[structure]` adapter audit in a separate fresh environment;
- retains the documented LSV/XRD/Raman/FTIR/thermal/sorption/composition quickstarts.

A real compatibility or packaging defect exposed by Gate A may be fixed on the Gate-A branch with regression coverage, but any head change invalidates older CI/review evidence.

### Gate A evidence

| Evidence | State |
| --- | --- |
| exact base | `8c958ffc29a36afa9340cada2239b51520c87a3d` |
| final Gate-A head | pending |
| exact-head CI | pending |
| release/API/packaging review | pending |
| second final-head review | pending |
| merge gate | pending |
| squash merge / post-merge main | pending |
| version after Gate A | must remain `0.4.0` |
| `v0.4.0` invariant | must remain `bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6` |

## Gate B — final-version candidate

Gate B begins only after Gate A is fully merged and reverified.

Gate B owns final candidate version synchronization. The intended v0.5 final candidate is `0.5.0`, but Gate B must still verify the live release state before changing anything.

Gate B should:

- update `[project].version` and runtime `__version__` together;
- update the Gate-A expected-version value in CI to the final candidate;
- update release/changelog/documentation candidate state consistently;
- build the exact candidate wheel in a fresh environment;
- run the unified v0.5 release audit, optional structure adapter audit, full tests, Ruff, `pip check`, and documented quickstarts;
- perform formal release/API/packaging review on the final exact head;
- merge only with behind=0, mergeable=true, unresolved review threads=0, and expected-head protection.

Gate B does **not** create a tag, GitHub Release, or package-registry artifact.

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
