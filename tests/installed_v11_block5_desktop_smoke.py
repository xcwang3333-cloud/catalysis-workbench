"""Fresh-wheel offscreen smoke for v1.1 Block-5 Figure Package UX."""

from __future__ import annotations

import importlib
import json
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
            argv=("cw-v11-block5-desktop-smoke",),
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
        window._show_figure_ui()
        window._create_figure_ui("processed", "publication")
        project = base / "project"
        window.save_project_path(project)
        window._refresh_figure_workbench("processed")
        assert window.session.state.is_dirty is False
        assert window.figure_page.continue_export_button.isEnabled() is True

        window._show_export_ui()
        assert window.stack.currentWidget() is window.export_page
        assert window.export_page.export_button.isEnabled() is False
        assert "Project saved and clean" in window.export_page.project_check.text()
        assert "Figure current" in window.export_page.figure_check.text()

        window.export_page.pdf_check.setChecked(False)
        window.export_page.png_check.setChecked(False)
        window.export_page.xlsx_check.setChecked(False)
        target = base / "publication-package"
        window.export_page.set_location(target)
        assert window.export_page.export_button.isEnabled() is True

        before_workspace = window.session.state.workspace_manifest_sha256
        window._export_package_ui(str(target), window.export_page.options())
        assert target.is_dir()
        assert (target / "figure.svg").is_file()
        assert (target / "source-data" / "trace-001.txt").is_file()
        assert (target / "manifest.json").is_file()
        manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["figure_formats"] == ["svg"]
        assert manifest["source_data_formats"] == ["txt"]
        assert "Package exported successfully" in window.export_page.message_label.text()
        assert window.session.state.is_dirty is False
        assert window.session.state.workspace_manifest_sha256 != before_workspace

        window._back_to_figure_ui()
        assert window.stack.currentWidget() is window.figure_page
        window.go_home(discard_changes=True)
        window.close()
        qt_app.processEvents()

    print("installed v1.1 Block-5 desktop smoke: ok")


if __name__ == "__main__":
    main()
