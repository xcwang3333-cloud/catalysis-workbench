"""Fresh-wheel offscreen smoke for v1.2 Analysis Workspace presentation."""

from __future__ import annotations

import importlib
import tempfile
from pathlib import Path


def main() -> None:
    application = importlib.import_module("catalysis_workbench.application")
    desktop_app = importlib.import_module("catalysis_workbench.desktop.app")
    recent_module = importlib.import_module(
        "catalysis_workbench.desktop.recent_projects"
    )
    ui_module = importlib.import_module("catalysis_workbench.desktop.ui_foundation")
    qtcore = importlib.import_module("PySide6.QtCore")

    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        source = base / "lsv.csv"
        source.write_text(
            "Potential,Current\n0.0,-2.0\n0.5,-4.0\n",
            encoding="utf-8",
        )
        settings = qtcore.QSettings(
            str(base / "settings.ini"),
            qtcore.QSettings.Format.IniFormat,
        )
        handle = desktop_app.create_workbench_desktop(
            argv=("cw-v12-block4-desktop-smoke",),
            recent_store=recent_module.RecentProjectsStore(settings),
            ui_settings=ui_module.DesktopUiSettings(settings),
        )
        window = handle.window
        qt_app = handle.application

        window.start_analysis("lsv")
        page = window.analysis_page
        panel = page.processing_panel
        assert page.objectName() == "cwAnalysisWorkspace"
        assert page._legacy_chrome.isHidden()
        assert not page.title_edit.isHidden()
        assert page.processing_scroll.widget() is panel
        assert page.continue_button.text() == "Continue to Figure"
        assert not page.continue_button.isEnabled()
        assert page.canvas_state_label.property("state") == "empty"
        assert page.canvas_state_label.text() == "Waiting for data"
        assert not window.app_shell.page_enabled("figure")

        page.title_edit.setText("Block 4 analysis")
        assert window._commit_title_editor() is True
        assert window.session.state.document is not None
        assert window.session.state.document.title == "Block 4 analysis"

        spec = application.DataSeriesSpec(
            source=application.source_spec_from_file(source),
            mapping=application.TabularMappingSpec(
                delimiter=",",
                x_column=0,
                y_column=1,
                x_role="potential",
                y_role="current",
                x_unit="V",
                y_unit="mA",
                x_reference="RHE",
            ),
            display_name="LSV",
        )
        window.add_data_items([(spec, source)])
        qt_app.processEvents()
        assert page.series_list.count() == 1
        assert len(page.axes.lines) == 1
        assert page.canvas_state_label.property("state") == "success"
        assert page.canvas_state_label.text() == "Analysis current"
        assert page.continue_button.isEnabled()
        assert window.app_shell.page_enabled("figure")
        assert page.view_combo.findData("raw") >= 0

        document = window.session.state.document
        assert document is not None
        committed_sha = document.document_sha256
        direct_index = panel.rhe_mode_combo.findData("direct")
        panel.rhe_mode_combo.setCurrentIndex(direct_index)
        panel.rhe_offset_edit.setText("")
        panel._apply_draft_now()
        qt_app.processEvents()
        assert panel.has_unapplied_draft
        assert window.session.state.document is not None
        assert window.session.state.document.document_sha256 == committed_sha
        assert page.canvas_state_label.property("state") == "stale"
        assert "Previous valid result" in page.preview_note.text()
        assert not page.continue_button.isEnabled()
        assert not window.app_shell.page_enabled("figure")

        panel.discard_draft()
        window._refresh_data_preview()
        qt_app.processEvents()
        assert page.canvas_state_label.property("state") == "success"
        assert page.continue_button.isEnabled()
        assert window.app_shell.page_enabled("figure")

        page.set_live_analysis(
            None,
            status="error",
            message="synthetic presentation error",
            stale=False,
        )
        assert page.canvas_state_label.property("state") == "error"
        assert "synthetic presentation error" in page.preview_note.text()
        window._refresh_data_preview()
        assert page.canvas_state_label.property("state") == "success"

        stylesheet = window.app_shell.styleSheet()
        for selector in (
            "cwAnalysisWorkspace",
            "cwScientificCanvas",
            "cwCanvasState",
            "cwProcessingScroll",
            "cwProcessingStatus",
        ):
            assert selector in stylesheet

        assert window.minimumWidth() >= 1200
        assert window.minimumHeight() >= 760
        window.go_home(discard_changes=True)
        window.close()
        qt_app.processEvents()

    print("installed v1.2 Block-4 desktop smoke: ok")


if __name__ == "__main__":
    main()
