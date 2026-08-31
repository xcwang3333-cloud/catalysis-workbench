# Windows installer packaging

This directory contains **post-release packaging infrastructure** for the
immutable CatalysisWorkbench `v1.1.0` release. It does not change the scientific,
application, workspace, or desktop semantics of that tag.

The Windows readiness build has these fixed boundaries:

- target: Windows x64;
- release source: exact `v1.1.0` tag only;
- frozen application: PyInstaller `onedir`;
- installer: Inno Setup 6.7.3, per-user install;
- bundled Python application extras: base + `[desktop]`;
- intentionally excluded: `[structure]` and `[volumetric3d]`;
- signing state: unsigned readiness artifact;
- CI publication: GitHub Actions artifact only, never a GitHub Release asset.

`launcher.py` exists only to make the immutable desktop testable after freezing.
Its `--installer-smoke` path checks the embedded package version and constructs
the v1.1 task-first Qt shell offscreen, then exits. Normal launches delegate to
the reviewed `catalysis_workbench.desktop.cli` entry point.

`build_installer.ps1` fails closed if the release tag, release commit, runtime
version, or PyInstaller version differs from the expected values. The build
also emits:

- `BUILD_PROVENANCE.json`;
- `resolved-requirements.txt`;
- `THIRD_PARTY_NOTICES.txt`;
- `SHA256SUMS.txt`.

The generated notice inventory is compliance evidence, not legal advice.
Installer publication remains a separate release gate and must re-check
signing/SmartScreen policy and redistribution obligations before upload.
