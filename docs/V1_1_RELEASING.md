# CatalysisWorkbench v1.1 Release Procedure

This document defines the release-maturity process for the reviewed v1.1 task-first workbench. GitHub is the operational source of truth. Every gate is bound to its exact head; evidence from an older head becomes stale after any change.

## Stable v1.1 release baseline

- v1.1 Blocks 1–6: complete and merged;
- Block-6 PR: #305;
- Block-6 squash merge: `c81ee2e1aa8767e1560a14c5f7f4c1209fc4b6f9`;
- Gate-A squash merge: `843df51828d740405aa5365142541ed361e069cc`;
- Gate-B final release commit: `80da57c65bb70f599c1e068f6fe71a1551eaa856`;
- stable version: `1.1.0`;
- immutable lightweight tag: `v1.1.0 -> 80da57c65bb70f599c1e068f6fe71a1551eaa856`;
- GitHub Release: `CatalysisWorkbench v1.1.0`;
- project license: `BSD-3-Clause`;
- PyPI/package-registry publication: not performed.

## Gate A — Stable 1.1 release hardening — complete

Gate A retained `1.1.0.dev0` and added release validation/documentation only.

### Gate A evidence

| Evidence | State |
| --- | --- |
| exact base | `c81ee2e1aa8767e1560a14c5f7f4c1209fc4b6f9` |
| candidate version | `1.1.0.dev0` |
| final Gate-A head | `edf7c8554177e6bf25a146085633a047f0744e7a` |
| exact-head ordinary CI | #853 — success |
| exact-head Stable 1.0 Readiness | #115 — success |
| exact-head Stable 1.1 Readiness | #2 — success |
| formal release/API/packaging review | `5062533798` — clean |
| unresolved review threads | 0 |
| squash merge | `843df51828d740405aa5365142541ed361e069cc` |
| post-merge ordinary CI | #854 — success |
| post-merge Stable 1.0 Readiness | #116 — success |
| post-merge Stable 1.1 Readiness | #3 — success |

## Gate B — final-version candidate — complete

Gate B started from exact post-merge Gate-A main `843df51828d740405aa5365142541ed361e069cc` and performed mechanical final-version synchronization only:

- `[project].version`: `1.1.0.dev0` -> `1.1.0`;
- runtime `__version__`: `1.1.0.dev0` -> `1.1.0`;
- ordinary CI and both release-readiness workflows' expected-version checks -> exact `1.1.0`;
- exact wheel/sdist artifact names -> final `1.1.0` names;
- version-sensitive installed-smoke and workflow-evidence assertions -> `1.1.0`;
- release-status documentation -> final candidate;
- no feature, scientific, dependency, schema, public-API, or runtime-semantic change.

### Gate B evidence

| Evidence | State |
| --- | --- |
| exact base | `843df51828d740405aa5365142541ed361e069cc` |
| candidate version | `1.1.0` |
| Gate-B branch | `release/v1.1.0-gate-b` |
| final Gate-B head | `5645a1855f80451c2e8f224285ef7c2b039fb1ac` |
| exact-head ordinary CI | #855 — success |
| exact-head Stable 1.0 Readiness | #117 — success |
| exact-head Stable 1.1 Readiness | #4 — success |
| formal release/API/packaging review | `5062851406` — clean |
| unresolved review threads | 0 |
| squash merge | `80da57c65bb70f599c1e068f6fe71a1551eaa856` |
| post-merge ordinary CI | #856 — success |
| post-merge Stable 1.0 Readiness | #118 — success |
| post-merge Stable 1.1 Readiness | #5 — success |

## Gate C — immutable tag — complete

The lightweight tag `v1.1.0` was created only after the Gate-B release commit passed post-merge validation. It was reverse-verified to point directly to:

`80da57c65bb70f599c1e068f6fe71a1551eaa856`

The tag must never be moved or recreated.

## GitHub Release publication — complete

The GitHub Release `CatalysisWorkbench v1.1.0` was published from the already verified `v1.1.0` tag. It is a normal stable release, not a draft or prerelease. Installer and registry publication were intentionally excluded.

## Gate D — Windows installer readiness — in progress

Gate D is post-release packaging infrastructure. It must not alter the immutable v1.1.0 product source.

The first target is Windows x64 and is defined in [`V1_1_INSTALLER.md`](V1_1_INSTALLER.md). The readiness workflow must build from the exact `v1.1.0` tag and record the packaging-infrastructure commit separately.

Gate D may prove an unsigned installer build through GitHub Actions, including silent install/smoke/uninstall and provenance/hash evidence. A successful Gate D does **not** authorize attaching the installer to the existing GitHub Release.

Installer publication requires a later explicit authorization and a current signing/SmartScreen/compliance decision.

## PyPI/package-registry publication

Registry publication remains a separate operation. Package-name availability, credentials or trusted-publishing configuration, provenance, exact artifact hashes, and the intended registry target must be re-checked immediately before upload. Building artifacts or publishing a GitHub Release never authorizes uploading to a package registry.

## Mandatory evidence discipline

For every v1.1 release/distribution gate:

1. record exact base and exact head;
2. invalidate CI/review evidence from older heads after any change;
3. require ordinary CI plus Stable 1.0 and Stable 1.1 readiness on the exact candidate when repository changes are proposed;
4. require unresolved review threads = 0;
5. preserve scientific/API/dependency/version/tag/publication boundaries;
6. use expected-head squash merge only after separate merge authorization;
7. re-read `main` after merge and validate post-merge workflows;
8. treat final-version synchronization, tag creation, GitHub Release, installer readiness/publication, and registry publication as distinct gates;
9. never use a post-release packaging commit as the v1.1.0 product source;
10. never move or recreate the immutable `v1.1.0` tag.
