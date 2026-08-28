# Desktop Dependency and Distribution Boundary

CatalysisWorkbench keeps the desktop toolkit outside the base runtime. The optional desktop extra is:

```text
PySide6-Essentials>=6.11.2,<6.12
```

This document records the reviewed dependency/distribution boundary for Stable 1.0 readiness. It is not a substitute for the upstream license texts or legal advice.

## Package boundary

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

## Current v1.0 distribution model

For the current Python-package model:

- CatalysisWorkbench declares PySide6-Essentials only as an optional dependency;
- CatalysisWorkbench does not embed Qt binaries into its own wheel;
- the base package works without Qt;
- CI validates a fresh `[desktop]` dependency installation separately from the base wheel;
- no standalone executable, frozen application bundle, installer image, or vendored Qt runtime is part of Stable 1.0 Gate A.

This separation reduces coupling but does not remove a redistributor's responsibility to comply with all applicable third-party licenses.

## Standalone application boundary

If a future project phase distributes a standalone application that bundles Qt/PySide6 libraries, that is a materially different distribution model and requires a new license/compliance review before packaging or publication. Such a future review should address at least:

- the exact bundled Qt/PySide6 components and versions;
- corresponding license notices and source/relinking obligations where applicable;
- installer/bundle layout;
- any Qt plugins shipped with the application;
- third-party notices for all newly bundled components;
- platform-specific redistribution requirements.

Stable 1.0 Gate A does not authorize that distribution model.

## Project license

The repository owner selected the BSD 3-Clause License for CatalysisWorkbench during Stable 1.0 Gate A. The canonical project terms are recorded in the root [`LICENSE`](../LICENSE) file.

Python distribution metadata uses the SPDX expression `BSD-3-Clause` and declares `LICENSE` as a distributed license file. This project-license choice applies to CatalysisWorkbench's own distribution; it does not replace, relicense, or override third-party dependency licenses, including the licenses applicable to Qt/PySide6.
