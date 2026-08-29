"""Fresh-wheel offscreen smoke for v1.1 Block-4 Figure Workbench UX."""

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

    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        settings = qtcore.QSettings(
            str(base / "settings.ini"),
            qtcore.QSettings.Format.IniFormat,
        )
        handle = desktop_app.create_workbench_desktop(
            argv=("cw-v11-block4-desktop-smoke",),
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
        assert window.analysis_page.continue_button.isEnabled() is True
        assert window.figure_page.continue_export_button.isEnabled() is False

        window._show_figure_ui()
        assert window.stack.currentWidget() is window.figure_page
        assert window.figure_page.active_view_id == "processed"
        assert window.figure_page.create_button.isEnabled() is True
        assert window.figure_page.trace_list.count() == 0

        window._create_figure_ui("processed", "publication")
        document = window.session.state.document
        assert document is not None
        assert document.schema_version == 4
        assert len(document.figures) == 1
        assert window.figure_page.trace_list.count() == 2
        assert window.figure_page.create_button.isEnabled() is False
        assert window.figure_page.refresh_button.isEnabled() is False
        assert window.figure_page.continue_export_button.isEnabled() is False
        assert "Figure up to date" in window.figure_page.status_label.text()

        draft = window.session.figure_draft("processed")
        edited = draft.figure_spec.updated(xlim=(0.5, 1.5)).with_series_style(
            first.data_id,
            label="Pb₁-N/C",
        )
        window._replace_figure_spec_ui("processed", edited)
        current = window.session.figure_draft("processed")
        assert current.figure_spec.xlim == (0.5, 1.5)
        assert current.figure_spec.series_styles[first.data_id].label == "Pb₁-N/C"

        window.show_analysis()
        window._replace_analysis_spec_ui(
            application.GenericXYAnalysisSpec(
                analysis_range=application.AnalysisRange(x_min=0.75, x_max=2.0)
            )
        )
        window._show_figure_ui()
        assert "refresh this figure" in window.figure_page.status_label.text().lower()
        assert window.figure_page.refresh_button.isEnabled() is True
        assert window.figure_page.trace_list.isEnabled() is False

        window._refresh_figure_ui("processed")
        assert window.figure_page.refresh_button.isEnabled() is False
        assert window.figure_page.trace_list.isEnabled() is True
        assert window.session.figure_draft("processed").figure_spec.series_styles[
            first.data_id
        ].label == "Pb₁-N/C"

        window.show_analysis()
        assert window.stack.currentWidget() is window.analysis_page
        window.close()
        qt_app.processEvents()

    print("installed v1.1 Block-4 desktop smoke: ok")


if __name__ == "__main__":
    main()
