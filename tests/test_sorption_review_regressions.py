"""Review-gate regressions for the gas-sorption public contract."""

from __future__ import annotations

import subprocess
import sys


def test_characterization_import_keeps_matplotlib_lazy() -> None:
    script = """
import sys
import catalysis_workbench.experimental.characterization as characterization
assert 'matplotlib' not in sys.modules
assert callable(characterization.plot_sorption)
assert 'matplotlib' not in sys.modules
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
