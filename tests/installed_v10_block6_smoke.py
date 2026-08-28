from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import catalysis_workbench
import catalysis_workbench.application as application
import catalysis_workbench.desktop as desktop

EXPECTED_VERSION = "1.0.0.dev0"

assert catalysis_workbench.__version__ == EXPECTED_VERSION
assert not any(name == "PySide6" or name.startswith("PySide6.") for name in sys.modules)
assert "CatalysisWorkbenchMainWindow" in desktop.__all__
assert "launch_desktop" in desktop.__all__
assert desktop.desktop_available() is False

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

print("installed v1.0 Block 6 core/lazy desktop smoke: ok")
