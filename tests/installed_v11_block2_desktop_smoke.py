"""Fresh-wheel offscreen smoke for v1.1 Block-2 data intake and mapping."""

from __future__ import annotations

import importlib
import tempfile
from pathlib import Path


def main() -> None:
    desktop_app = importlib.import_module("catalysis_workbench.desktop.app")
    data_intake = importlib.import_module("catalysis_workbench.desktop.data_intake")
    qtcore = importlib.import_module("PySide6.QtCore")

    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        first = base / "Pb1.csv"
        second = base / "Pb2.csv"
        first.write_text(
            "Potential [V],Current [mA]\n-0.8,-2.0\n-0.7,-1.2\n-0.6,-0.5\n",
            encoding="utf-8",
        )
        second.write_text(
            "Potential [V],Current [mA]\n-0.8,-3.0\n-0.7,-1.8\n-0.6,-0.7\n",
            encoding="utf-8",
        )

        settings = qtcore.QSettings(
            str(base / "settings.ini"),
            qtcore.QSettings.Format.IniFormat,
        )
        recent_module = importlib.import_module(
            "catalysis_workbench.desktop.recent_projects"
        )
        store = recent_module.RecentProjectsStore(settings)
        handle = desktop_app.create_workbench_desktop(
            argv=("cw-v11-block2-desktop-smoke",),
            recent_store=store,
        )
        window = handle.window
        application = handle.application
        window.start_analysis("lsv")

        assert window.minimumWidth() >= 1200
        assert window.analysis_page.add_files_button.isEnabled()
        assert window.analysis_page.series_list.count() == 0

        dialog = data_intake.ImportDataDialog(
            (first, second),
            task_id="lsv",
            parent=window,
        )
        assert dialog.file_list.count() == 2
        assert dialog.confirm_current_mapping() is True
        assert dialog.apply_current_mapping_to_compatible() == 1
        items = dialog.mapped_items()
        assert len(items) == 2
        assert items[0][0].mapping.x_role == "potential"
        assert items[0][0].mapping.y_role == "current"
        assert items[0][0].mapping.x_unit == "V"
        assert items[0][0].mapping.y_unit == "mA"

        window.add_data_items(list(items))
        state = window.session.state
        assert state.document is not None
        assert len(state.document.data_series) == 2
        assert window.analysis_page.series_list.count() == 2
        assert len(window.analysis_page.axes.lines) == 2

        project = base / "saved-project"
        window.save_project_path(project)
        assert (project / "project.json").is_file()
        first.unlink()
        second.unlink()

        first_spec = window.session.state.document.data_series[0]
        materialized = window.session.materialize_data(first_spec.data_id)
        assert materialized.value.n_points == 3
        owned_source = window.session.data_source_path(first_spec.data_id)
        assert owned_source.is_file()
        assert project.resolve() in owned_source.resolve().parents

        editor = data_intake.ImportDataDialog(
            (owned_source,),
            task_id="lsv",
            existing_spec=first_spec,
            parent=window,
        )
        editor.x_reference.setText("RHE")
        assert editor.confirm_current_mapping() is True
        replacement = editor.edited_mapping()
        assert replacement.x_reference == "RHE"
        window.session.replace_data_mapping(first_spec.data_id, replacement)
        window.refresh_views()
        window._refresh_data_preview()
        assert (
            window.session.state.document.data_series[0].mapping.x_reference == "RHE"
        )

        selected = window.session.state.document.data_series[0]
        preview = data_intake.SeriesPreviewDialog(
            window.session.materialize_data(selected.data_id),
            parent=window,
        )
        assert preview.windowTitle()
        preview.close()
        editor.close()
        dialog.close()
        window.go_home(discard_changes=True)
        window.close()
        application.processEvents()

    print("installed v1.1 Block-2 desktop smoke: ok")


if __name__ == "__main__":
    main()
