# CatalysisWorkbench v1.1 Windows installer — Gate D

## Status and purpose

`v1.1.0` is already an immutable tagged and published GitHub release. Gate D is
therefore a **post-release distribution-readiness gate**. It may add packaging
infrastructure to `main`, but the Windows executable must always be built from
the exact release source:

`v1.1.0 -> 80da57c65bb70f599c1e068f6fe71a1551eaa856`

No Gate-D commit is allowed to become product input for the v1.1.0 installer.

## Frozen scope

The first native installer target is Windows x64 only.

- Python build interpreter: CPython 3.11 x64.
- Freezer: PyInstaller 6.22.2.
- Freeze mode: `onedir`; `onefile` is intentionally not used.
- Installer compiler: Inno Setup 6.7.3.
- Installed location: per-user under local application data.
- Python extras: base + `[desktop]`.
- Excluded extras: `[structure]`, `[volumetric3d]`.
- Installer signing: not configured in Gate D.

PyInstaller and Inno Setup are build/distribution tooling and are not added to
the package runtime dependencies.

## Exact-source and exact-infrastructure contract

The readiness workflow checks out two independent trees:

1. the exact Gate-D infrastructure PR head (or exact dispatched commit); and
2. the immutable `v1.1.0` tag as release source.

The workflow must not use GitHub's synthetic pull-request merge ref as the
packaging-infrastructure provenance identity. Before freezing, it verifies both
checkout SHAs and verifies that the release tag resolves to
`80da57c65bb70f599c1e068f6fe71a1551eaa856` with distribution/runtime identity
exactly `1.1.0`.

Every readiness artifact records the release commit separately from the
packaging-infrastructure commit. This prevents a later packaging change from
being mistaken for a product-code change.

## Reproducible dependency resolution

The first isolated Windows x64 installation of exact `v1.1.0[desktop]` completed
successfully before the initial installer-tool bootstrap failure. The exact
resolver result from that run is committed as:

`packaging/windows/constraints-v1.1.0-windows-x64.txt`

Subsequent Gate-D runs install the immutable release and PyInstaller through
that constraints file, then require `pip check` to succeed before freezing.
The build records both the constraints SHA-256 and the actual sorted resolved
requirements SHA-256 in `BUILD_PROVENANCE.json`.

This lock is specific to the Windows x64 v1.1.0 standalone build. It does not
change the public wheel/sdist dependency declarations.

## Readiness evidence

A passing Windows Installer Readiness run must prove all of the following:

1. exact infrastructure-head and release-tag/SHA/version verification;
2. constrained dependency installation and `pip check`;
3. clean PyInstaller `onedir` build;
4. frozen offscreen task-first desktop construction;
5. third-party license/notice inventory generation;
6. per-user Inno Setup installer build;
7. silent install into an isolated test directory;
8. installed executable offscreen smoke;
9. silent uninstall;
10. provenance and SHA-256 generation;
11. upload to GitHub Actions artifacts only.

The expected installer filename is:

`CatalysisWorkbench-1.1.0-windows-x64-setup.exe`

## Licensing and redistribution review

Bundling is materially different from the existing wheel + optional-extra
model. Gate D therefore records rather than hides the redistribution boundary.

The artifact includes the project BSD-3-Clause license, an automated
third-party notice inventory, the bundled Python runtime license when
discoverable, exact dependency evidence, and build provenance. PySide6/Qt and
all other bundled dependencies must remain covered by the publication-time
compliance review.

The notice inventory is not legal advice and is not a substitute for counsel
where required. If the installer is used commercially, the license terms of
the installer compiler itself must also be checked for the intended use.

## Signing and publication boundary

Gate D does not claim that an unsigned Windows executable is suitable for broad
distribution. Code signing, certificate custody, timestamping, Windows
SmartScreen/reputation expectations, and final artifact provenance are part of
the later **installer publication gate**.

Until that separate gate is explicitly authorized:

- do not attach installer artifacts to the `v1.1.0` GitHub Release;
- do not replace or move `v1.1.0`;
- do not publish to PyPI or any package registry.
