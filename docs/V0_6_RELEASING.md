# CatalysisWorkbench v0.6 Release Procedure

This document records the release-hardening procedure and evidence for the frozen v0.6 electronic-structure and catalysis-thermodynamics scope. GitHub remains the operational source of truth; this file must be synchronized to merged reality when a gate completes.

## Frozen release baseline

- Final v0.6 scientific implementation merge: `f47d2165f282c8fe2745d1bd50ed32886b0f2054` (Issue #182 / PR #183).
- Scientific-completion documentation merge and Gate-A exact baseline: `f364e51de5eb2119a2495e93135572605dd8f926` (Issue #184 / PR #185).
- Distribution version before Gate A: `0.5.0`.
- Runtime `__version__` before Gate A: `0.5.0`.
- Prior release tag: `v0.5.0 -> 9400ac0044ac333d2cae228554c08d955a816a4c`, immutable.
- Earlier release tag: `v0.4.0 -> bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6`, immutable.
- The v0.5 GitHub Release is published from the existing verified tag.
- PyPI/package-registry publication remains deferred.

The frozen v0.6 scientific blocks are:

1. Electronic-structure and volumetric semantics/adapters — #150 / #151.
2. DOS/PDOS processing and passive plotting — #154 / #155.
3. Band-center / DOS first-moment analysis — #158 / #159.
4. Bader-result parsing and explicit charge accounting — #162 / #163.
5. COHP/ICOHP parsing and explicit bonding analysis — #166 / #167.
6. Explicit geometry–bonding correlation datasets — #170 / #171.
7. Explicit CHE/free-energy thermodynamics — #174 / #175.
8. Passive free-energy diagram state and plotting — #178 / #179.
9. Charge-density difference with strict co-registration validation — #182 / #183.

All nine blocks were complete before Gate A. Advanced computational visualization remains a v0.7 boundary.

## Gate A — frozen-scope release hardening — complete

Tracking: Issue #186 / PR #187. Branch: `release/v0.6-gate-a`. Exact base: `f364e51de5eb2119a2495e93135572605dd8f926`.

Gate A deliberately did not change the version. Distribution metadata, runtime `__version__`, and the Gate-A expected installed version remained `0.5.0`.

Gate A established a unified fresh-wheel v0.6 release audit that:

- proves imports come from the installed wheel rather than repository `src/`;
- verifies distribution metadata version == runtime `__version__` == the gate-supplied expected version;
- resolves every documented package-level public `__all__` and verifies representative reviewed v0.6 computation exports;
- verifies numerical public imports remain Matplotlib-lazy before visualization-specific smoke subprocesses execute;
- reuses the reviewed v0.5 unified release audit as an independent subprocess;
- reruns all reviewed base-environment v0.6 installed smokes as independent subprocesses;
- retains optional `[structure]` structure/electronic/bonding adapter audits in a separate fresh environment;
- retains documented LSV/XRD/Raman/FTIR/thermal/sorption/composition quickstarts.

### Gate A evidence

| Evidence | State |
| --- | --- |
| exact base | `f364e51de5eb2119a2495e93135572605dd8f926` |
| final Gate-A head | `a72be9f227f92b94df11b40c0bd77bd97933ecdb` |
| exact-head CI | CI #451 / run `32844596642` — success |
| release/API/packaging review | `5018578746` — pass |
| compatibility/release-boundary review | `5018579676` — pass |
| merge gate | behind=0; mergeable=true; unresolved threads=0 |
| squash merge / post-merge main | `c70481e34f6e3f2bf81724f4a30370fec58c1e7b` |
| version after Gate A | `0.5.0` |
| `v0.5.0` invariant | `9400ac0044ac333d2cae228554c08d955a816a4c` |
| `v0.4.0` invariant | `bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6` |

## Gate B — final-version candidate — complete

Tracking: Issue #188 / PR #189. Branch: `release/v0.6-gate-b`. Exact base: `c70481e34f6e3f2bf81724f4a30370fec58c1e7b`.

Gate B synchronized `[project].version`, runtime `__version__`, and the unified installed-wheel expected version from `0.5.0` to the reviewed release candidate `0.6.0`, then validated the exact candidate wheel in fresh environments without changing the frozen scientific/API/dependency scope.

### Gate B evidence

| Evidence | State |
| --- | --- |
| exact base | `c70481e34f6e3f2bf81724f4a30370fec58c1e7b` |
| candidate version | `0.6.0` |
| final Gate-B head | `4544a464ab54e13408e3db23a68acf565f764328` |
| exact-head CI | CI #453 / run `32845155122` — success |
| release/API/packaging review | `5018619904` — pass |
| compatibility/release-boundary review | `5018620923` — pass |
| merge gate | behind=0; mergeable=true; unresolved threads=0 |
| squash merge / reviewed release commit | `c7793b309f41d174c14534bd6d4acdacc2a57636` |
| distribution/runtime version after Gate B | `0.6.0` |
| `v0.5.0` invariant | `9400ac0044ac333d2cae228554c08d955a816a4c` |
| `v0.4.0` invariant | `bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6` |
| `v0.6.0` tag before Gate C | absent |

Gate B created no tag, GitHub Release, or package-registry artifact. The exact reviewed release candidate commit for Gate C is `c7793b309f41d174c14534bd6d4acdacc2a57636`. Later docs-only synchronization commits are not a substitute release target.

## Gate C — tag creation and reverse verification — complete

Tracking: Issue #192. Gate C was separately authorized on 2026-08-25.

The lightweight tag `v0.6.0` was created only on the reviewed Gate-B release commit `c7793b309f41d174c14534bd6d4acdacc2a57636` and then reverse-verified. The later docs-only main commit was not used as the release target.

### Gate C evidence

| Evidence | State |
| --- | --- |
| tag | `v0.6.0` |
| exact tag target | `c7793b309f41d174c14534bd6d4acdacc2a57636` |
| distribution version through tag | `0.6.0` |
| runtime `__version__` through tag | `0.6.0` |
| `v0.5.0` invariant | `9400ac0044ac333d2cae228554c08d955a816a4c` |
| `v0.4.0` invariant | `bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6` |
| tracking issue | #192 — completed |

## GitHub Release — complete

Tracking: Issue #193.

The public GitHub Release `CatalysisWorkbench v0.6.0` was published on 2026-08-25 from the existing verified `v0.6.0` tag. The Release is not a prerelease and does not move or recreate the tag. Post-publication verification confirmed that `v0.6.0` still resolves exactly to `c7793b309f41d174c14534bd6d4acdacc2a57636`, that distribution/runtime version through the tag remains `0.6.0`, and that prior release tags remain unchanged.

PyPI/package-registry publication is intentionally deferred and is not part of the v0.6 GitHub Release.

## Final v0.6 release state

v0.6 scientific implementation, Gate A, Gate B, Gate C, and GitHub Release publication are complete. The final public/current-state documentation synchronization is tracked separately as Issue #195 and does not change the immutable release tag or reviewed release commit.

Release identity:

- version: `0.6.0`;
- tag: `v0.6.0`;
- reviewed release commit: `c7793b309f41d174c14534bd6d4acdacc2a57636`;
- GitHub Release: `CatalysisWorkbench v0.6.0`;
- package registry / PyPI: deferred.

## Mandatory evidence discipline

For every gate:

1. record the exact head under review;
2. treat CI/reviews from older heads as stale after any head change;
3. require fresh exact-head CI before final review/merge;
4. keep scientific/API/version/tag/publication boundaries explicit;
5. use expected-head squash merge;
6. re-read `main` after merge;
7. never relabel PR CI as main-push CI evidence.
