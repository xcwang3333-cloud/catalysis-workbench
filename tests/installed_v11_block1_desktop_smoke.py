"""Fresh-wheel offscreen smoke for the v1.1 Home and Analysis shell."""

from __future__ import annotations

import importlib
import tempfile
from pathlib import Path

from catalysis_workbench.application import ApplicationSession
from catalysis_workbench.workspace import create_workspace


def main() -> None:
    desktop_app = importlib.import_module("catalysis_workbench.desktop.app")
    recent_module = importlib.import_module("catalysis_workbench.desktop.recent_projects")
    qtcore = importlib.import_module("PySide6.QtCore")

    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        settings = qtcore.QSettings(
            str(base / "settings.ini"),
            qtcore.QSettings.Format.IniFormat,
        )
        store = recent_module.RecentProjectsStore(settings)
        handle = desktop_app.create_workbench_desktop(
            argv=("cw-v11-block1-smoke",),
            recent_store=store,
        )
        window = handle.window
        application = handle.application

        assert window.stack.currentWidget() is window.home_page
        assert tuple(window.home_page.task_buttons) == (
            "lsv",
            "fe_partial_current",
            "generic_xy",
        )

        window.start_analysis("lsv")
        state = window.session.state
        assert state.is_unsaved and not state.is_dirty
        assert state.project_root is None
        assert window.stack.currentWidget() is window.analysis_page

        window.rename_analysis("Desktop v1.1 LSV")
        assert window.session.state.is_dirty
        window.session.undo()
        window.refresh_views()
        assert not window.session.state.is_dirty
        window.session.redo()
        window.refresh_views()
        assert window.session.state.is_dirty

        project = base / "saved-project"
        window.save_project_path(project)
        assert not window.session.state.is_dirty
        assert (project / "project.json").is_file()
        assert len(store.entries()) == 1

        window.go_home()
        assert window.stack.currentWidget() is window.home_page
        window.open_project_path(project)
        assert window.session.state.document is not None
        assert window.session.state.document.title == "Desktop v1.1 LSV"

        legacy = base / "legacy-workspace"
        create_workspace(legacy)
        legacy_handle = desktop_app.create_desktop(
            legacy,
            session=ApplicationSession(),
            argv=("cw-v10-compat-smoke",),
        )
        assert legacy_handle.window.session.state.workspace_root == legacy.resolve()

        legacy_handle.window.close()
        window.close()
        application.processEvents()

    print("installed v1.1 Block-1 desktop smoke: ok")


if __name__ == "__main__":
    main()
