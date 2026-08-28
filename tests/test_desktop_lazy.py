from __future__ import annotations

import subprocess
import sys


def test_desktop_package_import_is_qt_lazy() -> None:
    command = """
import sys
import catalysis_workbench
import catalysis_workbench.application
import catalysis_workbench.desktop
assert not any(name == "PySide6" or name.startswith("PySide6.") for name in sys.modules)
"""
    completed = subprocess.run(
        [sys.executable, "-c", command],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
