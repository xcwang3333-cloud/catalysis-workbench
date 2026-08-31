# CatalysisWorkbench v1.1 Release Procedure

This document defines the release-maturity process for the reviewed v1.1 task-first workbench. GitHub is the operational source of truth. Every gate is bound to its exact head; evidence from an older head becomes stale after any change.

## Frozen implementation baseline

- v1.1 Blocks 1–6: complete and merged;
- Block-6 PR: #305;
- Block-6 squash merge / Gate-A exact baseline: `c81ee2e1aa8767e1560a14c5f7f4c1209fc4b6f9`;
- Block-6 post-merge CI: #851 — 4/4 jobs success;
- Block-6 post-merge Stable 1.0 Readiness: #113 — 8/8 jobs success;
- current candidate development version: `1.1.0.dev0`;
- project license: `BSD-3-Clause`;
- retained stable release before v1.1: `v1.0.0 -> 22b944992bfd3791f91cc951f89eb22e8bf47325`;
- Gate-A branch: `release/v1.1.0-gate-a`.

Gate A creates release-readiness evidence only. It does not finalize the version or publish any artifact.

## Gate A — Stable 1.1 release hardening — in progress

Gate A retains `1.1.0.dev0` and owns only release validation/documentation:

- a unified Stable 1.1 installed-wheel audit that first re-runs the frozen Stable 1.0 audit and then all reviewed v1.1 headless installed smokes;
- explicit verification of the `catalysis-workbench` console entry point and Qt-free `--version` path;
- exact-wheel isolated base and `[desktop]` installs on Linux, Windows and macOS;
- Python 3.11 and 3.14 platform validation;
- exact wheel/sdist naming, metadata validation, and sdist-to-wheel rebuild;
- continued ordinary CI, including the full v1.1 offscreen desktop dogfood journeys;
- release procedure and draft release-note synchronization;
- no scientific, workflow, workspace, application, desktop-semantic, dependency, public-API, schema, or version change.

### Gate A evidence

| Evidence | State |
| --- | --- |
| exact base | `c81ee2e1aa8767e1560a14c5f7f4c1209fc4b6f9` |
| candidate version | `1.1.0.dev0` |
| final Gate-A head | pending |
| exact-head ordinary CI | pending |
| exact-head Stable 1.0 Readiness | pending |
| exact-head Stable 1.1 Readiness | pending |
| formal release/API/packaging review | pending |
| unresolved review threads | pending |
| merge gate | pending |
| squash merge / Gate-B baseline | pending |

Ready status never authorizes merge. Gate A must be squash-merged only after a separate explicit merge authorization and expected-head verification.

## Gate B — final-version candidate

Gate B may start only from the exact post-merge Gate-A main after all Gate-A push workflows are green.

Gate B owns mechanical final-version synchronization only:

- `[project].version`: `1.1.0.dev0` -> `1.1.0`;
- runtime `__version__`: `1.1.0.dev0` -> `1.1.0`;
- ordinary CI and both release-readiness workflows' expected-version checks -> exact `1.1.0`;
- exact wheel/sdist artifact names -> final `1.1.0` names;
- version-sensitive installed-smoke and workflow-evidence assertions -> `1.1.0`;
- release-status documentation -> final candidate;
- no feature, scientific, dependency, schema, public-API, or runtime-semantic change.

The exact Gate-B head must pass ordinary CI, Stable 1.0 Readiness, and Stable 1.1 Readiness before final review.

## Gate C — immutable tag

Creating `v1.1.0` is allowed only after Gate B is merged and its exact reviewed release commit passes post-merge validation. The tag target must be specified as an immutable commit SHA and reverse-verified after creation. A tag must never be moved or recreated as a side effect of another gate.

## GitHub Release publication

A GitHub Release may be published only from an already verified `v1.1.0` tag. Release notes must describe only behavior present in that tagged commit. Release publication does not imply package-registry publication.

## Installer/distribution packaging

Native installers or additional distribution bundles are optional and separate from the Python wheel/sdist release evidence. They require a separately reviewed packaging design, signing/provenance plan, platform matrix, and artifact-verification gate before publication.

## PyPI/package-registry publication

Registry publication is a separate operation after the final tag is verified. Package-name availability, credentials or trusted-publishing configuration, provenance, exact artifact hashes, and the intended registry target must be re-checked immediately before upload. Building artifacts never authorizes uploading them.

## Mandatory evidence discipline

For every v1.1 release gate:

1. record exact base and exact head;
2. invalidate CI/review evidence from older heads after any change;
3. require ordinary CI plus both Stable 1.0 and Stable 1.1 readiness on the exact candidate;
4. require unresolved review threads = 0;
5. preserve scientific/API/dependency/version/tag/publication boundaries;
6. use expected-head squash merge only after separate merge authorization;
7. re-read `main` after merge and validate post-merge push workflows;
8. treat final-version synchronization, tag creation, GitHub Release, installers, and registry publication as distinct gates.
