"""Fresh-wheel offscreen smoke for v1.2 Data Intake & Mapping presentation."""

from __future__ import annotations

import importlib
import tempfile
from pathlib import Path


def main() -> None:
    desktop_app = importlib.import_module("catalysis_workbench.desktop.app")
    data_intake = importlib.import_module("catalysis_workbench.desktop.data_intake")
    recent_module = importlib.import_module(
        "catalysis_workbench.desktop.recent_projects"
    )
    ui_module = importlib.import_module("catalysis_workbench.desktop.ui_foundation")
    qtcore = importlib.import_module("PySide6.QtCore")
    qtwidgets = importlib.import_module("PySide6.QtWidgets")

    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        first = base / "first.csv"
        second = base / "second.csv"
        preamble = base / "preamble.csv"
        latin = base / "latin.csv"

        first.write_text(
            "Potential [V],Current [mA]\n-0.8,-2.0\n-0.7,-1.2\n",
            encoding="utf-8",
        )
        second.write_text(
            "Potential [V],Current [mA]\n-0.8,-3.0\n-0.7,-1.8\n",
            encoding="utf-8",
        )
        preamble.write_text(
            "instrument metadata\n"
            "Potential [V],Current [mA]\n"
            "-0.8,-2.0\n"
            "-0.7,-1.2\n",
            encoding="utf-8",
        )
        latin.write_bytes(
            "Potential [V],Signal [µA]\n-0.8,12\n-0.7,18\n".encode("latin-1")
        )

        settings = qtcore.QSettings(
            str(base / "settings.ini"),
            qtcore.QSettings.Format.IniFormat,
        )
        store = recent_module.RecentProjectsStore(settings)
        ui_settings = ui_module.DesktopUiSettings(settings)
        handle = desktop_app.create_workbench_desktop(
            argv=("cw-v12-block3-desktop-smoke",),
            recent_store=store,
            ui_settings=ui_settings,
        )
        window = handle.window
        application = handle.application
        window.start_analysis("lsv")

        batch = data_intake.ImportDataDialog(
            (first, second),
            task_id="lsv",
            parent=window,
        )
        assert batch.objectName() == "cwDataImportDialog"
        assert batch.file_list.count() == 2
        assert batch.preview_table.objectName() == "cwPreviewTable"
        assert batch.header_spin.value() == 0
        assert batch.skip_rows_spin.value() == 0
        assert batch.encoding_combo.currentText() == "utf-8"
        ok_button = batch.buttons.button(
            qtwidgets.QDialogButtonBox.StandardButton.Ok
        )
        assert not ok_button.isEnabled()
        assert batch.confirm_current_mapping() is True
        assert batch.apply_current_mapping_to_compatible() == 1
        assert ok_button.isEnabled()
        mapped = batch.mapped_items()
        assert mapped[0][0].mapping.header == 0
        assert mapped[0][0].mapping.skip_rows == 0
        assert mapped[0][0].mapping.encoding == "utf-8"
        batch.close()

        parser = data_intake.ImportDataDialog(
            (preamble,),
            task_id="lsv",
            parent=window,
        )
        parser.skip_rows_spin.setValue(1)
        application.processEvents()
        assert parser.confirm_current_mapping() is False
        assert "reload preview" in parser.mapping_status.text().casefold()
        parser.reload_current_preview()
        assert parser.preview_table.columnCount() == 2
        assert parser.confirm_current_mapping() is True
        parser_item = parser.mapped_items()[0][0]
        assert parser_item.mapping.skip_rows == 1
        assert parser_item.mapping.header == 0
        assert parser_item.mapping.x_column == 0
        assert parser_item.mapping.y_column == 1
        parser.close()

        recovery = data_intake.ImportDataDialog(
            (latin,),
            task_id="generic_xy",
            parent=window,
        )
        assert recovery.preview_table.rowCount() == 0
        assert not recovery.confirm_current_mapping()
        recovery.encoding_combo.setCurrentText("latin-1")
        application.processEvents()
        assert not recovery.confirm_current_mapping()
        recovery.reload_current_preview()
        assert recovery.preview_table.columnCount() == 2
        assert "[V]" in recovery.preview_table.horizontalHeaderItem(0).text()
        assert "[µA]" in recovery.preview_table.horizontalHeaderItem(1).text()
        assert recovery.confirm_current_mapping() is True
        recovered = recovery.mapped_items()[0][0]
        assert recovered.mapping.encoding == "latin-1"
        recovery.close()

        stylesheet = window.app_shell.styleSheet()
        assert "cwDataImportDialog" in stylesheet
        assert "cwParserGroup" in stylesheet
        assert "cwScientificMappingGroup" in stylesheet
        assert "cwPreviewTable" in stylesheet

        window.go_home(discard_changes=True)
        window.close()
        application.processEvents()

    print("installed v1.2 Block-3 desktop smoke: ok")


if __name__ == "__main__":
    main()
