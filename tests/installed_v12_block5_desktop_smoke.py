"""Fresh-wheel offscreen smoke for the v1.2 Figure Workbench presentation."""

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


def main() -> None:
    application = importlib.import_module("catalysis_workbench.application")
    desktop_app = importlib.import_module("catalysis_workbench.desktop.app")
    recent_module = importlib.import_module(
        "catalysis_workbench.desktop.recent_projects"
    )
    qtcore = importlib.import_module("PySide6.QtCore")
    qtwidgets = importlib.import_module("PySide6.QtWidgets")

    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        settings = qtcore.QSettings(
            str(base / "settings.ini"),
            qtcore.QSettings.Format.IniFormat,
        )
        handle = desktop_app.create_workbench_desktop(
            argv=("cw-v12-block5-smoke",),
            recent_store=recent_module.RecentProjectsStore(settings),
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
        window.add_data_items([(first, first_path), (second, second_path)])
        assert window.app_shell.page_enabled("figure") is True
        window._show_figure_ui()

        page = window.figure_page
        assert window.stack.currentWidget() is page
        assert page.active_view_id == "processed"
        assert page.undo_button.isHidden()
        assert page.redo_button.isHidden()
        assert page.save_button.isHidden()
        back_buttons = [
            item
            for item in page.findChildren(qtwidgets.QPushButton)
            if item.text() == "← Back to Analysis"
        ]
        assert len(back_buttons) == 1 and back_buttons[0].isHidden()
        assert page.properties_scroll.widget().title() == "PROPERTIES"
        assert page.canvas_state_label.property("state") == "empty"
        assert page.canvas_state_label.text() == "Create a figure"
        assert page.create_button.isEnabled()
        assert page.trace_list.count() == 0

        window._create_figure_ui("processed", "publication")
        document = window.session.state.document
        assert document is not None
        assert document.schema_version == 4
        assert page.trace_list.count() == 2
        assert page.canvas_state_label.property("state") == "success"
        assert page.create_button.isEnabled() is False
        assert page.refresh_button.isEnabled() is False
        assert page.continue_export_button.isEnabled() is True
        assert window.app_shell.page_enabled("export") is True

        draft = window.session.figure_draft("processed")
        original_family = draft.figure_spec.style.font_family
        edited = draft.figure_spec.updated(xlim=(0.5, 1.5)).with_series_style(
            first.data_id,
            label="Pb₁-N/C",
        )
        window._replace_figure_spec_ui("processed", edited)
        current = window.session.figure_draft("processed")
        assert current.figure_spec.xlim == (0.5, 1.5)
        assert current.figure_spec.series_styles[first.data_id].label == "Pb₁-N/C"

        one_visible = current.figure_spec.with_series_style(second.data_id, visible=False)
        window._replace_figure_spec_ui("processed", one_visible)
        assert page.continue_export_button.isEnabled() is True
        none_visible = window.session.figure_draft("processed").figure_spec.with_series_style(
            first.data_id,
            visible=False,
        )
        window._replace_figure_spec_ui("processed", none_visible)
        assert page.continue_export_button.isEnabled() is False
        assert window.app_shell.page_enabled("export") is False
        visible_again = window.session.figure_draft(
            "processed"
        ).figure_spec.with_series_style(first.data_id, visible=True)
        window._replace_figure_spec_ui("processed", visible_again)
        assert page.continue_export_button.isEnabled() is True

        window.show_analysis()
        window._replace_analysis_spec_ui(
            application.GenericXYAnalysisSpec(
                analysis_range=application.AnalysisRange(x_min=0.75, x_max=2.0)
            )
        )
        window._show_figure_ui()
        assert page.canvas_state_label.property("state") == "stale"
        assert page.refresh_button.isEnabled() is True
        assert page.trace_list.isEnabled() is False
        assert page.continue_export_button.isEnabled() is False

        window._refresh_figure_ui("processed")
        assert page.canvas_state_label.property("state") == "success"
        assert page.refresh_button.isEnabled() is False
        assert page.trace_list.isEnabled() is True
        assert window.session.figure_draft("processed").figure_spec.series_styles[
            first.data_id
        ].label == "Pb₁-N/C"

        missing_font = window.session.figure_draft("processed").figure_spec.with_style(
            font_family="__CatalysisWorkbench_Missing_Font__"
        )
        window._replace_figure_spec_ui("processed", missing_font)
        assert page.canvas_state_label.property("state") == "error"
        assert "unavailable" in page.preview_note.text().casefold()
        assert page.continue_export_button.isEnabled() is False
        assert window.app_shell.page_enabled("export") is False

        restored = window.session.figure_draft("processed").figure_spec.with_style(
            font_family=original_family
        )
        window._replace_figure_spec_ui("processed", restored)
        assert page.canvas_state_label.property("state") == "success"
        assert page.continue_export_button.isEnabled() is True

        assert window.minimumWidth() >= 1200
        assert window.minimumHeight() >= 760
        window.go_home(discard_changes=True)
        window.close()
        qt_app.processEvents()

    print("installed v1.2 Block-5 desktop smoke: ok")


if __name__ == "__main__":
    main()
