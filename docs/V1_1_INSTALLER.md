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

## Exact-source and provenance contract

The readiness workflow checks out two independent trees:

1. the Gate-D infrastructure head; and
2. the immutable `v1.1.0` tag as release source.

Before freezing, the workflow must verify that the tag and checked-out release
tree resolve to `80da57c65bb70f599c1e068f6fe71a1551eaa856`, and that installed
distribution/runtime identity is exactly `1.1.0`.

Every readiness artifact records the release commit separately from the
packaging-infrastructure commit. This prevents a later packaging change from
being mistaken for a product-code change.

## Readiness evidence

A passing Windows Installer Readiness run must prove all of the following:

1. exact release tag/SHA/version verification;
2. clean PyInstaller `onedir` build;
3. frozen offscreen task-first desktop construction;
4. third-party license/notice inventory generation;
5. per-user Inno Setup installer build;
6. silent install into an isolated test directory;
7. installed executable offscreen smoke;
8. silent uninstall;
9. SHA-256 generation;
10. upload to GitHub Actions artifacts only.

The expected installer filename is:

`CatalysisWorkbench-1.1.0-windows-x64-setup.exe`

## Licensing and redistribution review

Bundling is materially different from the existing wheel + optional-extra
model. Gate D therefore records rather than hides the redistribution boundary.

The artifact includes the project BSD-3-Clause license, an automated
third-party notice inventory, the bundled Python runtime license when
discoverable, and build provenance. PySide6/Qt and all other bundled
dependencies must remain covered by the publication-time compliance review.

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
