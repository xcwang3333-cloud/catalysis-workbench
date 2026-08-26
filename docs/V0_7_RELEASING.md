# CatalysisWorkbench v0.7 Release Procedure

This document records release-hardening procedure and evidence for the frozen v0.7 advanced computational visualization scope. GitHub remains the operational source of truth; this file must be synchronized to merged reality as each gate completes.

## Frozen release baseline

- Final v0.7 scientific implementation merge: `24d3a8e67e4ef996125e575308b88ab6f9532448` (Issue #227 / PR #228).
- Scientific-completion documentation merge and Gate-A exact baseline: `8dc651fd87c18b1710258a26b88aaf76878240a8` (Issue #229 / PR #230).
- Gate-A merge and Gate-B exact baseline: `d718df1338b5a84d71c43a09a41c855c43cbacda` (Issue #231 / PR #232).
- Gate-B reviewed release commit: `e3062fc12c794f54c7b7613875ec73608a587a59` (Issue #233 / PR #234).
- Release tag: `v0.7.0 -> e3062fc12c794f54c7b7613875ec73608a587a59`, independently reverse-verified.
- Distribution/runtime release version through `v0.7.0`: `0.7.0`.
- Prior release tag: `v0.6.0 -> c7793b309f41d174c14534bd6d4acdacc2a57636`, immutable.
- The public `CatalysisWorkbench v0.6.0` GitHub Release is published from that existing tag.
- A public GitHub Release for `v0.7.0` has not yet been published and remains a separate explicit decision.
- PyPI/package-registry publication remains deferred.

The frozen v0.7 implementation blocks are:

1. Shared scalar-field state + renderer-neutral volumetric scene foundation — #202 / #203.
2. Charge-density-difference + electron-density + ELF visualization — #206 / #207.
3. Band-structure state/adapters + passive plotting — #210 / #211.
4. PROCAR projection processing + fat-band plotting — #214 / #216.
5. LOCPOT planar-potential/work-function processing + plotting — #219 / #220.
6. Explicit NEB image-energy state + discrete barrier plotting — #223 / #224.
7. Advanced volumetric 3-D rendering + static export — #227 / #228.

All seven blocks and scientific-completion synchronization are complete. Operando/time-resolved work remains the v0.8 boundary.

## Gate A — frozen-scope release hardening — complete

Tracking: Issue #231 / PR #232. Exact base: `8dc651fd87c18b1710258a26b88aaf76878240a8`.

Gate A deliberately did not change the version. Distribution metadata, runtime `__version__`, and the Gate-A expected installed version remained `0.6.0`.

Gate A established a unified fresh-wheel v0.7 release audit that:

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
| final Gate-A head | `af2b5736558d436c6a5464f21d31debaa94b2f3f` |
| exact-head CI | CI #530 / run `32884936791` — success |
| release/API/packaging review | `5025441754` — no blockers |
| compatibility/dependency-boundary review | `5025442740` — no blockers |
| merge gate | behind=0, mergeable=true, unresolved review threads=0 |
| squash merge / post-merge main | `d718df1338b5a84d71c43a09a41c855c43cbacda` |
| version after Gate A | `0.6.0` |
| `v0.6.0` invariant | `c7793b309f41d174c14534bd6d4acdacc2a57636` |

## Gate B — final-version candidate — complete

Tracking: Issue #233 / PR #234. Exact base: `d718df1338b5a84d71c43a09a41c855c43cbacda`.

Gate B performed only final candidate synchronization and exact-wheel validation:

- `[project].version`: `0.6.0` -> `0.7.0`;
- runtime `__version__`: `0.6.0` -> `0.7.0`;
- unified v0.7 release-audit expected version in CI: `0.6.0` -> `0.7.0`;
- no scientific/API/dependency/optional-backend expansion.

The exact Gate-B candidate passed Ruff/full pytest, fresh exact `0.7.0` base-wheel build/install/`pip check`, the unified v0.7 release audit, the retained fresh `[structure]` adapter audit, the retained separate `[volumetric3d]` PyVista/VTK headless rendering/PNG-export audit, and documented quickstarts.

### Gate B evidence

| Evidence | State |
| --- | --- |
| exact base | `d718df1338b5a84d71c43a09a41c855c43cbacda` |
| candidate version | `0.7.0` |
| final Gate-B head | `1f468f0875c5d71ffe1b475432d40d2f6a0cb19f` |
| exact-head CI | CI #532 / run `32912897877` — success |
| release/API/packaging review | `5025475440` — no blockers |
| compatibility/release-boundary review | `5025476096` — no blockers |
| merge gate | behind=0, mergeable=true, unresolved review threads=0 |
| squash merge / reviewed release commit | `e3062fc12c794f54c7b7613875ec73608a587a59` |
| `v0.6.0` invariant | `c7793b309f41d174c14534bd6d4acdacc2a57636` |

Gate B created no tag, GitHub Release, or package-registry artifact.

## Gate C — tag creation and reverse verification — complete

User explicitly authorized Gate C on 2026-08-26. The sole authorized release target was the reviewed Gate-B release commit:

`e3062fc12c794f54c7b7613875ec73608a587a59`

The connected GitHub mutation surface did not expose a direct `refs/tags/*` creation endpoint, so Gate C used a reviewed one-shot GitHub Actions workflow rather than misusing branch refs.

### Gate C evidence

| Evidence | State |
| --- | --- |
| authorization | explicit user authorization on 2026-08-26 |
| tracking | Issue #237 / PR #238 |
| carrier exact base | `281f5e7e51cc6e80f116742706e7a08f2cf5112e` |
| carrier final head | `1ff5fb863db6cf5824f0a5169baefe4a4f548054` |
| carrier exact-head CI | CI #536 / run `32915040785` — success |
| Gate-C workflow/tag-semantics review | `5025613183` — no blockers |
| release-boundary/compatibility review | `5025613986` — no blockers |
| carrier merge | `54100f27124d22efb5abdd40c1e818801019daed` |
| tag workflow run | `32915322619` / `create-and-verify-tag` — success |
| created tag | `v0.7.0 -> e3062fc12c794f54c7b7613875ec73608a587a59` |
| independent tag reverse verification | exact commit target confirmed through GitHub ref API |
| version through tag | `[project].version = 0.7.0`; runtime `__version__ = 0.7.0` |
| prior-tag invariant | `v0.6.0 -> c7793b309f41d174c14534bd6d4acdacc2a57636` |
| carrier main push CI | CI #537 / run `32915322601` — success |

The one-shot tag workflow was then removed as required:

- cleanup tracking: Issue #239 / PR #240;
- cleanup final head: `0b6f75287a1770e03607992e74b7e70341e0d145`;
- cleanup exact-head CI: CI #538 / run `32915523745` — success;
- cleanup reviews: `5025642265`, `5025642879` — no blockers;
- cleanup squash merge / post-cleanup main: `914a3b2db94f29fa302b45f90928006d594423c7`;
- `.github/workflows/gate-c-v07-tag.yml` is absent from post-cleanup `main`;
- neither cleanup nor this evidence synchronization may move or recreate `v0.7.0`.

## GitHub Release and package publication

Publishing a public GitHub Release for `v0.7.0` remains a separate explicit action after Gate C. The existing verified tag must be used as-is; publication does not authorize tag movement or recreation.

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
