from __future__ import annotations

import subprocess
import sys


def test_application_import_does_not_load_matplotlib_modules() -> None:
    code = """
import sys
import catalysis_workbench.application
forbidden = sorted(
    name for name in sys.modules
    if name == "matplotlib" or name.startswith("matplotlib.")
)
assert not forbidden, forbidden
"""
    subprocess.run([sys.executable, "-c", code], check=True)
