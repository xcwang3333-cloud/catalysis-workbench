# CatalysisWorkbench v0.7 Release Procedure

This document records release-hardening procedure and evidence for the frozen v0.7 advanced computational visualization scope. GitHub remains the operational source of truth; this file must be synchronized to merged reality as each gate completes.

## Frozen release baseline

- Final v0.7 scientific implementation merge: `24d3a8e67e4ef996125e575308b88ab6f9532448` (Issue #227 / PR #228).
- Scientific-completion documentation merge and Gate-A exact baseline: `8dc651fd87c18b1710258a26b88aaf76878240a8` (Issue #229 / PR #230).
- Distribution version before Gate A: `0.6.0`.
- Runtime `__version__` before Gate A: `0.6.0`.
- Prior release tag: `v0.6.0 -> c7793b309f41d174c14534bd6d4acdacc2a57636`, immutable.
- The public `CatalysisWorkbench v0.6.0` GitHub Release is published from that existing tag.
- PyPI/package-registry publication remains deferred.

The frozen v0.7 implementation blocks are:

1. Shared scalar-field state + renderer-neutral volumetric scene foundation — #202 / #203.
2. Charge-density-difference + electron-density + ELF visualization — #206 / #207.
3. Band-structure state/adapters + passive plotting — #210 / #211.
4. PROCAR projection processing + fat-band plotting — #214 / #216.
5. LOCPOT planar-potential/work-function processing + plotting — #219 / #220.
6. Explicit NEB image-energy state + discrete barrier plotting — #223 / #224.
7. Advanced volumetric 3-D rendering + static export — #227 / #228.

All seven blocks and scientific-completion synchronization are complete before Gate A. Operando/time-resolved work remains the v0.8 boundary.

## Gate A — frozen-scope release hardening — in progress

Tracking: Issue #231. Branch: `release/v0.7-gate-a`. Exact base: `8dc651fd87c18b1710258a26b88aaf76878240a8`.

Gate A deliberately does not change the version. Distribution metadata, runtime `__version__`, and the Gate-A expected installed version remain `0.6.0`.

Gate A establishes a unified fresh-wheel v0.7 release audit that:

- proves imports come from the installed wheel rather than repository `src/`;
- verifies distribution metadata version == runtime `__version__` == the gate-supplied expected version;
- resolves every documented package-level public `__all__` and verifies representative reviewed v0.7 computation and visualization exports;
- verifies numerical public imports remain Matplotlib-lazy before visualization smoke subprocesses execute;
- proves public base imports do not load optional PyVista/VTK state;
- reuses the reviewed v0.6 unified release audit as an independent subprocess;
- reruns all reviewed v0.7 Block-1–7 base installed smokes as independent subprocesses;
- retains optional `[structure]` structure/electronic/bonding/ELFCAR/band/PROCAR/LOCPOT audits in a separate fresh environment;
- retains the separate `[volumetric3d]` PyVista/VTK headless skew-cell rendering and PNG-export audit;
- retains documented LSV/XRD/Raman/FTIR/thermal/sorption/composition quickstarts.

### Gate A evidence

| Evidence | State |
| --- | --- |
| exact base | `8dc651fd87c18b1710258a26b88aaf76878240a8` |
| final Gate-A head | pending |
| exact-head CI | pending |
| release/API/packaging review | pending |
| compatibility/dependency-boundary review | pending |
| merge gate | pending |
| squash merge / post-merge main | pending |
| version after Gate A | `0.6.0` |
| `v0.6.0` invariant | `c7793b309f41d174c14534bd6d4acdacc2a57636` |

If Gate A exposes a genuine frozen-scope compatibility or packaging blocker, only that blocker may be fixed in Gate A, with regression coverage and fresh exact-head evidence after any head change.

## Gate B — final-version candidate — pending

Gate B begins only after Gate A is merged and reverse-verified. Gate B owns synchronization of `[project].version`, runtime `__version__`, and the unified v0.7 release-audit expected version to the reviewed v0.7 candidate version, followed by exact-wheel validation in fresh base and optional-backend environments.

Gate B must not create a tag, GitHub Release, or package-registry artifact.

## Gate C — tag creation and reverse verification — separate authorization required

Gate C remains a separate explicit user-authorization boundary. No `v0.7.0` tag may be created during Gate A or Gate B. The existing `v0.6.0` tag must never move or be recreated.

After explicit authorization, Gate C must create the release tag only on the exact reviewed Gate-B release commit and reverse-verify tag target, distribution version, runtime version, prior-tag invariants, and repository state.

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
