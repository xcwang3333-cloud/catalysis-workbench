"""Packaging-only entry point for the immutable CatalysisWorkbench v1.1.0 desktop."""

from __future__ import annotations

import os
import sys

_EXPECTED_VERSION_ENV = "CATALYSIS_WORKBENCH_EXPECTED_VERSION"
_SMOKE_ARG = "--installer-smoke"


def _run_installer_smoke() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    expected_version = os.environ.get(_EXPECTED_VERSION_ENV)
    if not expected_version:
        return 90

    from catalysis_workbench import __version__

    if __version__ != expected_version:
        return 91

    from catalysis_workbench.desktop.app import create_workbench_desktop

    handle = create_workbench_desktop(argv=("CatalysisWorkbench",))
    handle.window.show()
    handle.application.processEvents()
    if not handle.window.isVisible():
        handle.window.close()
        handle.application.processEvents()
        return 92
    handle.window.close()
    handle.application.processEvents()
    return 0


def main() -> int:
    if _SMOKE_ARG in sys.argv[1:]:
        return _run_installer_smoke()

    from catalysis_workbench.desktop.cli import main as desktop_main

    return int(desktop_main())


if __name__ == "__main__":
    raise SystemExit(main())
