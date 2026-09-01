"""Fresh-wheel offscreen smoke for v1.2 Export and dialog/state integration."""

from __future__ import annotations

import importlib
import tempfile
from pathlib import Path


def _mapped(application, path: Path, *, name: str):
    return application.DataSeriesSpec(
        source=application.source_spec_from_file(path),
        mapping=application.TabularMappingSpec(
            delimiter=",",
            x_column=0,
            y_column=1,
            x_role="potential",
            y_role="signal",
            x_unit="V",
            y_unit="a.u.",
            x_reference="RHE",
        ),
        display_name=name,
    )


def _minimal_export(page) -> None:
    page.svg_check.setChecked(True)
    page.pdf_check.setChecked(False)
    page.png_check.setChecked(False)
    page.xlsx_check.setChecked(False)
    page.txt_check.setChecked(True)


def main() -> None:
    application = importlib.import_module("catalysis_workbench.application")
    desktop_app = importlib.import_module("catalysis_workbench.desktop.app")
    dialog_module = importlib.import_module(
        "catalysis_workbench.desktop.dialog_presentation"
    )
    export_window = importlib.import_module(
        "catalysis_workbench.desktop.export_window"
    )
    product_window = importlib.import_module(
        "catalysis_workbench.desktop.product_window"
    )
    recent_module = importlib.import_module(
        "catalysis_workbench.desktop.recent_projects"
    )
    ui_module = importlib.import_module(
        "catalysis_workbench.desktop.ui_foundation"
    )
    qtcore = importlib.import_module("PySide6.QtCore")

    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        settings = qtcore.QSettings(
            str(base / "settings.ini"),
            qtcore.QSettings.Format.IniFormat,
        )
        ui_settings = ui_module.DesktopUiSettings(settings)
        handle = desktop_app.create_workbench_desktop(
            argv=("cw-v12-block6-smoke",),
            recent_store=recent_module.RecentProjectsStore(settings),
            ui_settings=ui_settings,
        )
        window = handle.window
        qt_app = handle.application

        first_path = base / "first.csv"
        second_path = base / "second.csv"
        first_path.write_text("x,y\n0,1\n1,2\n2,3\n", encoding="utf-8")
        second_path.write_text("x,y\n0,3\n1,2\n2,1\n", encoding="utf-8")
        first = _mapped(application, first_path, name="Pb1")
        second = _mapped(application, second_path, name="Pb2")

        window.start_analysis("generic_xy")
        window.add_data_items(((first, first_path), (second, second_path)))
        window._show_figure_ui()
        window._create_figure_ui("processed", "publication")
        project = base / "generic-project"
        window.save_project_path(project)
        assert window.session.state.is_dirty is False
        assert window.app_shell.page_enabled("export") is True

        window._show_export_ui()
        page = window.export_page
        assert window.stack.currentWidget() is page
        assert page.back_button.isHidden()
        assert page.summary_group.title() == "SUMMARY"
        assert page.figure_files_group.title() == "FIGURE FILES"
        assert page.source_files_group.title() == "SOURCE DATA"
        assert page.destination_group.title() == "DESTINATION"
        assert page.preflight_group.title() == "PREFLIGHT"
        assert page.presentation_state == "blocked"
        assert page.export_state_label.text() == "Choose a destination"
        assert page.export_button.isEnabled() is False
        assert window.app_shell.status_bar.currentMessage() == "Choose a destination"

        _minimal_export(page)
        package = base / "generic-package"
        page.set_location(package)
        assert page.presentation_state == "ready"
        assert page.export_state_label.text() == "Ready to export"
        assert page.export_button.isEnabled() is True
        assert window.app_shell.status_bar.currentMessage() == "Export ready"

        assert window._dirty_decision.__func__.__module__ == product_window.__name__
        assert (
            window._prepare_processing_draft.__func__.__module__
            == product_window.__name__
        )
        assert window._remove_series_ui.__func__.__module__ == product_window.__name__

        dirty_box, save_button, discard_button, cancel_button = (
            dialog_module.build_dirty_guard_dialog(
                window,
                mode=ui_module.ThemeMode.LIGHT,
            )
        )
        assert dirty_box.defaultButton() is cancel_button
        assert dirty_box.escapeButton() is cancel_button
        assert save_button.objectName() == "cwPrimaryButton"
        assert discard_button.objectName() == "cwSecondaryButton"
        assert cancel_button.objectName() == "cwTertiaryButton"
        dirty_box.close()

        processing_box, processing_discard, processing_cancel = (
            dialog_module.build_processing_draft_dialog(
                window,
                mode=ui_module.ThemeMode.LIGHT,
            )
        )
        assert processing_box.defaultButton() is processing_cancel
        assert processing_box.escapeButton() is processing_cancel
        assert processing_discard.objectName() == "cwSecondaryButton"
        processing_box.close()

        remove_box, remove_button, remove_cancel = (
            dialog_module.build_remove_data_dialog(
                window,
                display_name="Pb1",
                impact_lines=("• remove 1 explicit partial-current pair(s)",),
                mode=ui_module.ThemeMode.LIGHT,
            )
        )
        assert remove_box.defaultButton() is remove_cancel
        assert remove_box.escapeButton() is remove_cancel
        assert remove_button.text() == "Remove"
        assert "original raw file is not modified" in (
            remove_box.informativeText().casefold()
        )
        assert "partial-current" in remove_box.informativeText()
        remove_box.close()

        error_box = dialog_module.build_error_dialog(
            window,
            summary="Project changed outside CatalysisWorkbench.",
            guidance="Reopen the project before trying this action again.",
            details="RuntimeError: workspace changed outside this session",
            mode=ui_module.ThemeMode.LIGHT,
        )
        assert error_box.text() == "Project changed outside CatalysisWorkbench."
        assert "Reopen" in error_box.informativeText()
        assert "RuntimeError" in error_box.detailedText()
        error_box.close()

        original_export = export_window.export_session_figure_package
        observed_exporting = False

        def checked_export(*args, **kwargs):
            nonlocal observed_exporting
            observed_exporting = True
            assert page.presentation_state == "exporting"
            assert page.export_state_label.text() == "Exporting package…"
            assert page.export_button.isEnabled() is False
            assert (
                window.app_shell.status_bar.currentMessage()
                == "Exporting Figure Package…"
            )
            return original_export(*args, **kwargs)

        export_window.export_session_figure_package = checked_export
        try:
            window._export_package_ui(str(package), page.options())
        finally:
            export_window.export_session_figure_package = original_export

        assert observed_exporting
        assert (package / "figure.svg").is_file()
        assert (package / "source-data" / "trace-001.txt").is_file()
        assert page.presentation_state == "success"
        assert page.export_state_label.text() == "Package exported"
        assert not page.success_actions.isHidden()
        assert (
            window.app_shell.status_bar.currentMessage()
            == "Figure Package exported"
        )

        page._prepare_another_export()
        assert page.location_edit.text() == ""
        assert page.success_actions.isHidden()
        assert page.presentation_state == "blocked"
        assert page.export_state_label.text() == "Choose a destination"

        page.show_error("Synthetic export failure")
        assert page.presentation_state == "error"
        assert page.export_state_label.text() == "Export needs attention"
        assert window.app_shell.status_bar.currentMessage() == "Export needs attention"
        page.show_error("")
        assert page.presentation_state == "blocked"

        document = window.session.state.document
        assert document is not None
        assert document.schema_version == 4
        assert window.minimumWidth() >= 1200
        assert window.minimumHeight() >= 760

        window.go_home(discard_changes=True)
        window.close()
        qt_app.processEvents()

    print("installed v1.2 Block-6 desktop smoke: ok")


if __name__ == "__main__":
    main()
