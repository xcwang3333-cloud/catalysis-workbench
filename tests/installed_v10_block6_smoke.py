from __future__ import annotations

import sys

import catalysis_workbench
import catalysis_workbench.application
import catalysis_workbench.desktop as desktop

EXPECTED_VERSION = "1.0.0.dev0"

assert catalysis_workbench.__version__ == EXPECTED_VERSION
assert not any(name == "PySide6" or name.startswith("PySide6.") for name in sys.modules)
assert "CatalysisWorkbenchMainWindow" in desktop.__all__
assert "launch_desktop" in desktop.__all__
assert desktop.desktop_available() is False

try:
    desktop.launch_desktop(show=False, execute=False)
except desktop.DesktopDependencyError:
    pass
else:
    raise AssertionError("base wheel unexpectedly launched desktop without the desktop extra")

print("installed v1.0 Block 6 core/lazy desktop smoke: ok")
