# CatalysisWorkbench v1.0 Release Procedure

This document defines the release-maturity process for the frozen v1.0 local-workbench implementation. GitHub is the operational source of truth. Every gate must be reviewed and validated on its exact head; evidence from an older head becomes stale after any change.

## Frozen development baseline

- completion-checkpoint main: `079f472fe53c2c1386677299c8708ab2f0ee681d`;
- development version: `1.0.0.dev0`;
- v1.0 Blocks 1–6: complete and merged;
- completion checkpoint: PR #295;
- post-checkpoint main CI: #738 / run `33157868457`, success;
- retained stable tag/Release: `v0.7.0 -> e3062fc12c794f54c7b7613875ec73608a587a59`;
- Gate-A tracking: Issue #296;
- Gate-A branch: `chore/v10-stable-readiness`.

Stable `1.0.0`, a `v1.0.0` tag, GitHub Release publication, and PyPI/package-registry publication are not implied by this baseline.

## Release gate model

The established v0.7 release discipline remains authoritative in structure.

### Gate A — frozen-scope release hardening

Gate A retains version `1.0.0.dev0` and may only harden release readiness. It must not add scientific functionality or expand application/desktop semantics.

Gate A must establish:

- a unified installed-wheel audit for the documented v1.0 public surface;
- continued reuse of the reviewed historical scientific installed-wheel audits;
- clean base-package isolation from optional Qt/PySide6, pymatgen, PyVista, and VTK backends;
- fresh exact-wheel base and `[desktop]` installation checks on Linux, Windows, and macOS;
- lower/current Python validation at Python 3.11 and 3.14;
- wheel and sdist build/metadata validation without publication;
- release-oriented package metadata that does not invent legal or author information;
- a documented desktop/Qt distribution boundary;
- draft v1.0 release notes;
- final public-API and compatibility review.

Gate A is not complete while any explicit release blocker remains unresolved.

### Gate B — final-version candidate

Gate B is a later, separately scoped change. Only after Gate A is merged and post-merge validated may Gate B synchronize the reviewed candidate from `1.0.0.dev0` to `1.0.0`.

Gate B must limit version-sensitive changes to the distribution/runtime version and exact release-audit expectations, plus any documentation status that must describe the final candidate. It must repeat exact-wheel, cross-platform and artifact validation on the final version.

Gate B creates no tag, GitHub Release, or registry artifact.

### Gate C — tag creation and reverse verification

Creating `v1.0.0` requires separate explicit authorization after a reviewed Gate-B release commit exists. The tag target must be an exact immutable commit SHA and must be independently reverse-verified after creation.

No tag may be created, moved, recreated, or inferred as a side effect of Gate A or Gate B.

### GitHub Release publication

A GitHub Release from an already verified `v1.0.0` tag is a separate publication decision. Release notes must describe the reviewed scientific, workflow, workspace, application and optional desktop scope without claiming functionality that is not in the tagged commit.

### PyPI/package-registry publication

Registry publication is a separate decision from GitHub Release publication. Package-name availability, credentials, provenance/trusted-publishing configuration, final artifact hashes and the exact registry target must be checked immediately before any publication attempt.

## Explicit project-license blocker

The public repository currently has no root `LICENSE` file and GitHub reports no detected project license. Gate A must not silently choose a license.

Before Gate A can be promoted to Ready, the repository owner must explicitly choose the project license. The resulting change must then be reviewed as part of the exact Gate-A head, including package metadata and distribution implications.

The project-license choice is separate from third-party dependency licenses. See [`DESKTOP_DISTRIBUTION.md`](DESKTOP_DISTRIBUTION.md) for the optional Qt/PySide6 boundary.

## Public API freeze

For stable 1.0, supported public imports are the package-level names intentionally listed by each documented package's `__all__`. Gate A audits these surfaces from an installed wheel.

Implementation-only modules and names that are not documented/publicly exported are not promoted merely because they are importable from a source checkout.

The dependency direction remains:

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

Stable release hardening must not invert this direction.

## Platform support evidence

Gate A validates installation on GitHub-hosted Linux, Windows, and macOS runners using Python 3.11 and 3.14. This is release-candidate installation evidence, not a claim that every possible OS/Python/environment combination is supported indefinitely.

The existing Ubuntu jobs remain the deeper behavior gates:

- full Ruff + pytest;
- cumulative base-wheel/public-API/scientific adapter/examples audit;
- PyVista/VTK headless volumetric 3-D smoke;
- Qt offscreen desktop behavioral smoke.

The cross-platform release matrix adds isolated exact-wheel base + desktop installation/import checks rather than duplicating the full scientific suite on every runner.

## Artifact gate

Gate A and Gate B must both build a wheel and source distribution from the exact reviewed head, run package metadata validation, and prove the sdist can be used to rebuild a wheel. Building artifacts does not authorize uploading them anywhere.

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
