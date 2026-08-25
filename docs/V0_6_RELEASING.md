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

## Gate B — final-version candidate — in progress

Tracking: Issue #188. Branch: `release/v0.6-gate-b`. Exact base: `c70481e34f6e3f2bf81724f4a30370fec58c1e7b`.

Gate B synchronizes `[project].version`, runtime `__version__`, and the unified installed-wheel expected version from `0.5.0` to the reviewed release candidate `0.6.0`, then validates the exact candidate wheel in fresh environments without changing the frozen scientific/API/dependency scope.

### Gate B evidence

| Evidence | State |
| --- | --- |
| exact base | `c70481e34f6e3f2bf81724f4a30370fec58c1e7b` |
| candidate version | `0.6.0` |
| final Gate-B head | pending |
| exact-head CI | pending |
| release/API/packaging review | pending |
| compatibility/release-boundary review | pending |
| merge gate | pending |
| squash merge / post-merge main | pending |
| `v0.5.0` invariant | `9400ac0044ac333d2cae228554c08d955a816a4c` |
| `v0.4.0` invariant | `bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6` |

Gate B does **not** create a tag, GitHub Release, or package-registry artifact. Final Gate-B SHA/CI/review/merge evidence is synchronized after the merge so recording the evidence cannot mutate the exact head it describes.

## Gate C — tag creation and reverse verification — separate authorization required

Gate C remains a separate explicit user-authorization boundary. No `v0.6.0` tag may be created, moved, or recreated during Gate A or Gate B.

After authorization, Gate C must create the release tag only on the exact reviewed Gate-B release commit and reverse-verify tag target, distribution version, runtime version, prior-tag invariants, and repository state.

## GitHub Release and package publication

Publishing a GitHub Release is a separate action after Gate C and does not authorize tag mutation or package-registry publication.

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
