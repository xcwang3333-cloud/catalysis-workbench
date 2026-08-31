"""Fresh-wheel offscreen smoke for the v1.2 UI foundation and product shell."""

from __future__ import annotations

import importlib
import tempfile
from pathlib import Path


def main() -> None:
    desktop_app = importlib.import_module("catalysis_workbench.desktop.app")
    recent_module = importlib.import_module("catalysis_workbench.desktop.recent_projects")
    ui_module = importlib.import_module("catalysis_workbench.desktop.ui_foundation")
    qtcore = importlib.import_module("PySide6.QtCore")

    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        settings = qtcore.QSettings(
            str(base / "settings.ini"),
            qtcore.QSettings.Format.IniFormat,
        )
        recent_store = recent_module.RecentProjectsStore(settings)
        ui_settings = ui_module.DesktopUiSettings(settings)
        handle = desktop_app.create_workbench_desktop(
            argv=("cw-v12-block1-smoke",),
            recent_store=recent_store,
            ui_settings=ui_settings,
        )
        window = handle.window
        application = handle.application

        assert window.centralWidget() is window.app_shell
        assert window.app_shell.stack is window.stack
        assert window.app_shell.page_ids == (
            "home",
            "analysis",
            "figure",
            "export",
        )
        assert window.stack.currentWidget() is window.home_page
        assert window.app_shell.page_enabled("analysis") is False
        assert window.app_shell.page_enabled("figure") is False
        assert window.app_shell.page_enabled("export") is False
        assert window.minimumWidth() == 1024
        assert window.minimumHeight() == 640

        window.start_analysis("lsv")
        assert window.stack.currentWidget() is window.analysis_page
        assert window.app_shell.page_enabled("analysis") is True
        assert window.app_shell.command_bar.project_title.text() == "Untitled LSV analysis"
        assert window.app_shell.command_bar.task_pill.text() == "LSV / Polarization"
        assert window.app_shell.command_bar.save_button.isEnabled()
        assert window.app_shell.command_bar.dirty_pill.isHidden()

        window.rename_analysis("v1.2 shell smoke")
        assert window.session.state.is_dirty
        assert window.app_shell.command_bar.project_title.text() == "v1.2 shell smoke"
        assert not window.app_shell.command_bar.dirty_pill.isHidden()
        assert window.app_shell.command_bar.undo_button.isEnabled()

        window.app_shell.command_bar.undo_button.click()
        application.processEvents()
        assert window.session.state.document is not None
        assert window.session.state.document.title == "Untitled LSV analysis"
        assert not window.session.state.is_dirty

        window.app_shell.resize(1100, 700)
        application.processEvents()
        assert window.app_shell.sidebar.is_compact
        window.app_shell.resize(1400, 800)
        application.processEvents()
        assert not window.app_shell.sidebar.is_compact

        window.app_shell.set_theme_mode("dark")
        assert ui_settings.theme_mode() is ui_module.ThemeMode.DARK
        assert window.app_shell.styleSheet()

        window.go_home()
        assert window.stack.currentWidget() is window.home_page
        assert window.app_shell.page_enabled("analysis") is False
        assert window.app_shell.command_bar.project_title.text() == "Home"

        window.close()
        application.processEvents()

    print("installed v1.2 Block-1 desktop smoke: ok")


if __name__ == "__main__":
    main()
