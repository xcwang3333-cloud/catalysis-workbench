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

All nine blocks are complete before Gate A. Advanced computational visualization remains a v0.7 boundary.

## Gate A — frozen-scope release hardening — in progress

Tracking: Issue #186. Branch: `release/v0.6-gate-a`. Exact base: `f364e51de5eb2119a2495e93135572605dd8f926`.

Gate A deliberately does not change the version. Distribution metadata, runtime `__version__`, and the Gate-A expected installed version remain `0.5.0`.

Gate A establishes a unified fresh-wheel v0.6 release audit that:

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
| final Gate-A head | pending |
| exact-head CI | pending |
| release/API/packaging review | pending |
| second final-head review | pending |
| merge gate | pending |
| squash merge / post-merge main | pending |
| version after Gate A | `0.5.0` |
| `v0.5.0` invariant | `9400ac0044ac333d2cae228554c08d955a816a4c` |
| `v0.4.0` invariant | `bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6` |

If Gate A exposes a genuine frozen-scope compatibility or packaging blocker, only that blocker may be fixed in Gate A, with regression coverage and fresh exact-head evidence after any head change.

## Gate B — final-version candidate — pending

Gate B begins only after Gate A is merged and reverse-verified. Gate B owns synchronization of `[project].version`, runtime `__version__`, and the unified release-audit expected version to the reviewed v0.6 candidate version, followed by exact-wheel validation in a fresh environment.

Gate B must not create a tag, GitHub Release, or package-registry artifact.

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
