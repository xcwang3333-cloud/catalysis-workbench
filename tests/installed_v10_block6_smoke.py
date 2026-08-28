from __future__ import annotations

import sys
import tempfile
from importlib import import_module
from pathlib import Path

import catalysis_workbench
import catalysis_workbench.application as application
import catalysis_workbench.desktop as desktop

EXPECTED_VERSION = "1.1.0.dev0"
PUBLIC_V10_MODULES = (
    "catalysis_workbench.workflow",
    "catalysis_workbench.workspace",
    "catalysis_workbench.application",
)

assert catalysis_workbench.__version__ == EXPECTED_VERSION
assert not any(name == "PySide6" or name.startswith("PySide6.") for name in sys.modules)

for module_name in PUBLIC_V10_MODULES:
    module = import_module(module_name)
    exports = tuple(getattr(module, "__all__", ()))
    assert exports, f"documented v1.0 public module has empty __all__: {module_name}"
    assert len(exports) == len(set(exports)), f"duplicate __all__ names: {module_name}"
    for name in exports:
        assert isinstance(name, str) and name, f"invalid __all__ entry in {module_name}"
        getattr(module, name)

assert not any(name == "PySide6" or name.startswith("PySide6.") for name in sys.modules)
assert "CatalysisWorkbenchMainWindow" in desktop.__all__
assert "launch_desktop" in desktop.__all__
assert len(desktop.__all__) == len(set(desktop.__all__))
assert desktop.desktop_available() is False
assert not any(name == "PySide6" or name.startswith("PySide6.") for name in sys.modules)

with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    root = base / "workspace"
    source = base / "raw.dat"
    source.write_bytes(b"raw")

    session = application.ApplicationSession()
    application.create_workspace_in_session(session, root)
    application.import_asset_in_session(
        session,
        source,
        asset_id="raw",
        asset_type="source_file",
        policy="reference",
    )
    snapshot = application.workspace_snapshot(session)
    assert tuple(asset.asset_id for asset in snapshot.manifest.assets) == ("raw",)
    application.close_workspace_in_session(session)
    assert session.state.workspace_root is None

try:
    desktop.launch_desktop(show=False, execute=False)
except desktop.DesktopDependencyError:
    pass
else:
    raise AssertionError("base wheel unexpectedly launched desktop without the desktop extra")

assert not any(name == "PySide6" or name.startswith("PySide6.") for name in sys.modules)

print("installed v1.0 Block 6 public API/lazy desktop smoke: ok")