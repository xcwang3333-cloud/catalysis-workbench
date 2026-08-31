# Desktop Dependency and Distribution Boundary

CatalysisWorkbench keeps the desktop toolkit outside the base Python runtime. The optional desktop extra is:

```text
PySide6-Essentials>=6.11.2,<6.12
```

This document records the reviewed dependency/distribution boundary for the stable Python package and the post-release v1.1 Windows installer readiness work. It is not a substitute for upstream license texts or legal advice.

## Python package boundary

`catalysis-workbench` does not vendor PySide6 or Qt binaries into its own source tree or wheel. Installing the optional `[desktop]` extra asks the Python package installer to resolve the separately distributed `PySide6-Essentials` dependency.

Base installation remains Qt-free:

```bash
python -m pip install .
```

Desktop installation is explicit:

```bash
python -m pip install ".[desktop]"
```

Importing `catalysis_workbench.desktop` remains lazy and does not itself load PySide6. Qt is loaded only when an actual desktop class or launcher is requested.

## Upstream licensing

PySide6 is the official Qt for Python binding. Qt publishes the applicable Qt for Python licensing information and component license notices through its official documentation:

- https://doc.qt.io/qtforpython-6/licenses.html
- https://www.qt.io/licensing/open-source-lgpl-obligations

The upstream licensing options and obligations belong to the corresponding Qt/PySide6 distributions and must be checked against the exact version and distribution method used by a downstream redistributor.

## Stable wheel/sdist distribution model

For the stable Python-package model:

- CatalysisWorkbench declares PySide6-Essentials only as an optional dependency;
- CatalysisWorkbench does not embed Qt binaries into its own wheel;
- the base package works without Qt;
- CI validates a fresh `[desktop]` dependency installation separately from the base wheel;
- Linux, Windows, and macOS exact-wheel installation remain part of the Stable 1.1 release-readiness evidence.

This separation reduces coupling but does not remove a redistributor's responsibility to comply with all applicable third-party licenses.

## Gate D standalone Windows boundary

After `v1.1.0` was tagged and published, Gate D begins a materially different distribution-readiness model for a Windows x64 standalone installer.

The Gate-D build:

- freezes only the immutable `v1.1.0` release source, not later packaging-branch product code;
- bundles the base package plus `[desktop]`;
- excludes `[structure]` and `[volumetric3d]`;
- uses PyInstaller `onedir` rather than `onefile`;
- creates a per-user Windows installer;
- includes the project `LICENSE`, generated third-party notice inventory, and build provenance;
- validates frozen and installed desktop startup offscreen;
- uploads unsigned readiness artifacts to GitHub Actions only.

The exact Gate-D architecture and evidence requirements are recorded in [`V1_1_INSTALLER.md`](V1_1_INSTALLER.md).

## Redistribution/compliance review

Bundling Qt/PySide6 libraries requires a distribution-specific review. The readiness evidence therefore addresses at least:

- the exact release source and resolved dependency inventory;
- the bundled Python runtime and its license;
- the exact Qt/PySide6 versions and discovered license texts;
- installer/bundle layout;
- Qt plugins and other binaries collected by the freezer;
- project and third-party notices;
- artifact provenance and SHA-256;
- platform-specific redistribution requirements.

The generated notice inventory is deliberately conservative and is evidence for review, not a legal conclusion. Publication must also re-check any source/relinking obligations applicable to the exact redistributed Qt/PySide6 components.

The Inno Setup compiler is packaging tooling with its own licensing terms. Its intended use must be checked separately, particularly for commercial distribution.

## Signing boundary

Gate D readiness builds are explicitly unsigned. Windows code signing, certificate custody, timestamping, SmartScreen/reputation expectations, and the decision to distribute an unsigned artifact are not silently inferred from a successful build.

Attaching a Windows installer to an existing GitHub Release is a separate publication gate requiring explicit authorization after readiness evidence is complete.

## Project license

CatalysisWorkbench itself is licensed under BSD 3-Clause. The canonical project terms are recorded in the root [`LICENSE`](../LICENSE) file.

Python distribution metadata uses the SPDX expression `BSD-3-Clause` and declares `LICENSE` as a distributed license file. This project-license choice applies to CatalysisWorkbench's own distribution; it does not replace, relicense, or override third-party dependency licenses, including the licenses applicable to Qt/PySide6.
