# CatalysisWorkbench v1.0 Release Procedure

This document defines the release-maturity process for the frozen v1.0 local-workbench implementation. GitHub is the operational source of truth. Every gate must be reviewed and validated on its exact head; evidence from an older head becomes stale after any change.

## Frozen release baseline

- completion-checkpoint main before Gate A: `079f472fe53c2c1386677299c8708ab2f0ee681d`;
- v1.0 Blocks 1–6: complete and merged;
- completion checkpoint: PR #295;
- Gate A tracking: Issue #296 / PR #297;
- Gate A reviewed head: `8e152eb25f9fd32b4ed17b3353e0c3d6bffb35dc`;
- Gate A squash merge / Gate-B exact baseline: `1e98dd25f7e9e0ba9d89ab86e7551b6a2da96307`;
- Gate A post-merge CI: #743 / run `33161697186`, 4/4 jobs success;
- Gate A post-merge Stable 1.0 Readiness: #5 / run `33161697170`, 8/8 jobs success;
- project license: `BSD-3-Clause`;
- Gate-B tracking: Issue #298;
- Gate-B branch: `release/v1.0.0-final-candidate`;
- Gate-B candidate version: `1.0.0`;
- retained stable tag/GitHub Release before v1.0: `v0.7.0 -> e3062fc12c794f54c7b7613875ec73608a587a59`.

Gate B creates a reviewed final-version candidate only. A `v1.0.0` tag, GitHub Release, and PyPI/package-registry publication remain separately authorized operations.

## Gate A — frozen-scope release hardening — complete

Gate A retained version `1.0.0.dev0` and introduced no scientific or application/desktop runtime-semantic expansion.

Gate A established:

- a unified installed-wheel audit for the documented v1.0 public surface;
- continued reuse of reviewed historical scientific installed-wheel audits;
- clean base-package isolation from optional Qt/PySide6, pymatgen, PyVista and VTK backends;
- fresh exact-wheel base and `[desktop]` checks on Linux, Windows and macOS;
- Python 3.11 and 3.14 platform validation;
- wheel and sdist build/metadata validation without publication;
- BSD-3-Clause project licensing with PEP 639 `License-Expression` / `License-File` validation;
- release-oriented package metadata;
- documented desktop/Qt distribution boundaries;
- draft v1.0 release notes;
- final public-API and compatibility review.

### Gate A evidence

| Evidence | State |
| --- | --- |
| exact base | `079f472fe53c2c1386677299c8708ab2f0ee681d` |
| final reviewed head | `8e152eb25f9fd32b4ed17b3353e0c3d6bffb35dc` |
| final PR CI | CI #742 / run `33160697408` — 4/4 success |
| final PR Stable Readiness | #4 / run `33160697543` — 8/8 success |
| formal review | `5049957692` — no remaining blocker |
| merge gate | behind=0, mergeable=true, unresolved review threads=0 |
| squash merge / Gate-B baseline | `1e98dd25f7e9e0ba9d89ab86e7551b6a2da96307` |
| post-merge CI | CI #743 / run `33161697186` — 4/4 success |
| post-merge Stable Readiness | #5 / run `33161697170` — 8/8 success |
| version after Gate A | `1.0.0.dev0` |
| project license | `BSD-3-Clause` |

## Gate B — final-version candidate — in progress

Tracking: Issue #298. Branch: `release/v1.0.0-final-candidate`. Exact base: `1e98dd25f7e9e0ba9d89ab86e7551b6a2da96307`.

Gate B owns only final candidate synchronization and exact-wheel validation:

- `[project].version`: `1.0.0.dev0` -> `1.0.0`;
- runtime `__version__`: `1.0.0.dev0` -> `1.0.0`;
- Stable 1.0 Readiness expected version/artifact checks: `1.0.0.dev0` -> `1.0.0`;
- distribution Development Status: Beta -> Production/Stable, with installed-wheel assertion;
- version-sensitive release-procedure/release-note status synchronization;
- no scientific/API/dependency/optional-backend/runtime-semantic expansion.

The exact Gate-B candidate must pass the ordinary CI suite plus the complete Stable 1.0 Readiness workflow: unified release audit, artifact validation, and Linux/Windows/macOS × Python 3.11/3.14 isolated base + `[desktop]` checks.

### Gate B evidence

| Evidence | State |
| --- | --- |
| exact base | `1e98dd25f7e9e0ba9d89ab86e7551b6a2da96307` |
| candidate version | `1.0.0` |
| final Gate-B head | pending |
| exact-head ordinary CI | pending |
| exact-head Stable 1.0 Readiness | pending |
| formal release/API/packaging review | pending |
| unresolved review threads | pending |
| merge gate | pending |
| squash merge / reviewed release commit | pending |
| retained `v0.7.0` invariant | `e3062fc12c794f54c7b7613875ec73608a587a59` |

Gate B creates no tag, GitHub Release, or package-registry artifact.

## Gate C — tag creation and reverse verification

Creating `v1.0.0` requires a new explicit authorization after Gate B is merged and its reviewed release commit is post-merge validated. The tag target must be an exact immutable commit SHA and must be independently reverse-verified after creation.

No tag may be created, moved, recreated, or inferred as a side effect of Gate A or Gate B.

## GitHub Release publication

A GitHub Release from an already verified `v1.0.0` tag is a separate publication decision. Release notes must describe the reviewed scientific, workflow, workspace, application and optional desktop scope without claiming functionality absent from the tagged commit.

## PyPI/package-registry publication

Registry publication is separate from GitHub Release publication. Package-name availability, credentials, provenance/trusted-publishing configuration, final artifact hashes and the exact registry target must be checked immediately before any publication attempt.

## Public API freeze

For Stable 1.0, supported public imports are the package-level names intentionally listed by each documented package's `__all__`. Implementation-only modules and names are not promoted merely because they are importable from a source checkout.

Dependency direction remains:

```text
core / processing / io / experimental / computation / visualization
                              ↓
                           workflow
                              ↓
                          workspace
                              ↓
                         application
                              ↓
                     desktop presentation
```

Release hardening must not invert this direction.

## Platform and artifact evidence

Stable 1.0 release gates validate exact candidate wheels on GitHub-hosted Linux, Windows and macOS runners using Python 3.11 and 3.14. The deeper Ubuntu behavior gates remain Ruff/full pytest, cumulative installed public/scientific API audits, optional scientific adapter checks, examples, volumetric 3-D smoke and Qt offscreen desktop smoke.

Gate A and Gate B must both build wheel and sdist artifacts from the exact reviewed head, run metadata validation, and prove that the sdist can rebuild a wheel. Building artifacts never authorizes uploading them.

## Mandatory evidence discipline

For every release gate:

1. record the exact base and exact head;
2. invalidate CI/reviews from older heads after any change;
3. require exact-head CI before final review and promotion;
4. require unresolved review threads = 0;
5. preserve scientific/API/dependency/version/tag/publication boundaries;
6. use expected-head squash merge after separate merge authorization;
7. re-read `main` after merge and validate post-merge push CI;
8. never relabel PR CI as main-push CI evidence;
9. treat version finalization, tag creation, GitHub Release, PyPI publication and branch deletion as distinct authorization gates.