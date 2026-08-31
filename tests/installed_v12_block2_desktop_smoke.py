"""Fresh-wheel offscreen smoke for the v1.2 Home and New Analysis surface."""

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
            argv=("cw-v12-block2-smoke",),
            recent_store=recent_store,
            ui_settings=ui_settings,
        )
        window = handle.window
        application = handle.application
        home = window.home_page

        assert window.stack.currentWidget() is home
        assert home.headline_label.text() == "Start your analysis"
        assert home.new_analysis_button.text() == "New Analysis"
        assert home.open_project_button.text() == "Open Project…"
        assert tuple(home.task_buttons) == (
            "lsv",
            "fe_partial_current",
            "generic_xy",
        )
        assert home.empty_state_label is not None
        assert (
            home.empty_state_label.text()
            == "Your recently opened projects will appear here."
        )
        assert home.recent_rows == []

        dialog = home.new_analysis_dialog
        assert dialog.selected_task_id is None
        assert not dialog.start_button.isEnabled()
        dialog.select_task("lsv")
        assert dialog.selected_task_id == "lsv"
        assert dialog.start_button.isEnabled()
        assert home.task_buttons["lsv"].property("selected") is True
        assert home.task_buttons["fe_partial_current"].property("selected") is False
        dialog.start_button.click()
        application.processEvents()

        assert window.session.state.document is not None
        assert window.session.state.document.task_id == "lsv"
        assert window.stack.currentWidget() is window.analysis_page
        window.go_home()

        window.start_analysis("generic_xy")
        window.rename_analysis("Recent project smoke")
        project = base / "recent-project"
        window.save_project_path(project)
        window.go_home()
        application.processEvents()

        assert len(home.recent_rows) == 1
        row = home.recent_rows[0]
        assert row.project.available is True
        assert row.title_label.text() == "Recent project smoke"
        assert row.task_badge.text() == "Generic XY Plot"
        assert row.path_label.text() == str(project.resolve())
        assert row.open_button.isEnabled()

        row.open_button.click()
        application.processEvents()
        assert window.session.state.project_root == project.resolve()
        assert window.stack.currentWidget() is window.analysis_page
        window.go_home()

        missing = base / "missing-project"
        recent_store.add(missing)
        window.refresh_views()
        application.processEvents()
        assert len(home.recent_rows) == 2
        unavailable = home.recent_rows[0]
        assert unavailable.project.available is False
        assert unavailable.title_label.text() == "Unavailable project"
        assert unavailable.task_badge.text() == "Unavailable"
        assert unavailable.path_label.text() == str(missing.resolve())
        assert not unavailable.open_button.isEnabled()
        assert unavailable.remove_button.isEnabled()

        unavailable.remove_button.click()
        application.processEvents()
        assert all(entry.path != str(missing.resolve()) for entry in recent_store.entries())
        assert len(home.recent_rows) == 1

        window.app_shell.set_theme_mode("dark")
        assert ui_settings.theme_mode() is ui_module.ThemeMode.DARK
        assert "cwHomeIntro" in window.app_shell.styleSheet()
        assert "cwRecentProjectRow" in window.app_shell.styleSheet()

        window.close()
        application.processEvents()

    print("installed v1.2 Block-2 desktop smoke: ok")


if __name__ == "__main__":
    main()
