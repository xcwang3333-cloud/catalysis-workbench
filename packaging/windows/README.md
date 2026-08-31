# Windows installer packaging

This directory contains **post-release packaging infrastructure** for the
immutable CatalysisWorkbench `v1.1.0` release. It does not change the scientific,
application, workspace, or desktop semantics of that tag.

The Windows readiness build has these fixed boundaries:

- target: Windows x64;
- release source: exact `v1.1.0` tag only;
- frozen application: PyInstaller 6.22.2 `onedir`;
- installer: Inno Setup 6.7.3, per-user install;
- bundled Python application extras: base + `[desktop]`;
- intentionally excluded: `[structure]` and `[volumetric3d]`;
- signing state: unsigned readiness artifact;
- CI publication: GitHub Actions artifact only, never a GitHub Release asset.

## Dependency lock

`constraints-v1.1.0-windows-x64.txt` records the exact Windows x64 dependency
set observed during the first successful isolated installation of the immutable
`v1.1.0[desktop]` source on GitHub Actions. Subsequent readiness builds install
through this constraints file and run `pip check` before freezing.

The constraints file does not replace the package's public dependency metadata.
It is packaging evidence for this specific frozen Windows build. The build also
emits a sorted `resolved-requirements.txt`; both its hash and the committed
constraints-file hash are recorded in `BUILD_PROVENANCE.json`.

## Exact-head / exact-tag split

The workflow checks out two independent trees:

- packaging infrastructure at the exact PR head (or exact dispatched commit);
- product source at immutable `v1.1.0`.

This avoids recording GitHub's synthetic pull-request merge commit as packaging
provenance and prevents packaging changes from becoming v1.1.0 product input.

`launcher.py` exists only to make the immutable desktop testable after freezing.
Its `--installer-smoke` path checks the embedded package version and constructs
the v1.1 task-first Qt shell offscreen, then exits. Normal launches delegate to
the reviewed `catalysis_workbench.desktop.cli` entry point.

`build_installer.ps1` fails closed if the release tag, release commit, runtime
version, PyInstaller version, or constraints file differs from the supplied
inputs. The build emits:

- `BUILD_PROVENANCE.json`;
- `constraints-v1.1.0-windows-x64.txt`;
- `resolved-requirements.txt`;
- `THIRD_PARTY_NOTICES.txt`;
- `SHA256SUMS.txt`.

The generated notice inventory is compliance evidence, not legal advice.
Installer publication remains a separate release gate and must re-check
signing/SmartScreen policy and redistribution obligations before upload.
