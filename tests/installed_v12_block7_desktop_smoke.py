"""Fresh-wheel offscreen smoke for v1.2 theme/responsive/a11y dogfooding."""

from __future__ import annotations

import importlib
import tempfile
from importlib.metadata import version
from pathlib import Path


def _mapped(
    application,
    path: Path,
    *,
    name: str,
    y_role: str,
    y_unit: str,
    reference: str = "RHE",
):
    return application.DataSeriesSpec(
        source=application.source_spec_from_file(path),
        mapping=application.TabularMappingSpec(
            delimiter=",",
            x_column=0,
            y_column=1,
            x_role="potential",
            y_role=y_role,
            x_unit="V",
            y_unit=y_unit,
            x_reference=reference,
        ),
        display_name=name,
    )


def _minimal_export(page) -> None:
    page.svg_check.setChecked(True)
    page.pdf_check.setChecked(False)
    page.png_check.setChecked(False)
    page.xlsx_check.setChecked(False)
    page.txt_check.setChecked(True)


def _export_current(window, target: Path) -> None:
    window._show_export_ui()
    page = window.export_page
    _minimal_export(page)
    page.set_location(target)
    assert page.export_button.isEnabled()
    window._export_package_ui(str(target), page.options())
    assert (target / "figure.svg").is_file()
    assert (target / "source-data" / "trace-001.txt").is_file()


def main() -> None:
    application = importlib.import_module("catalysis_workbench.application")
    desktop_app = importlib.import_module("catalysis_workbench.desktop.app")
    hardening_module = importlib.import_module(
        "catalysis_workbench.desktop.desktop_hardening"
    )
    recent_module = importlib.import_module("catalysis_workbench.desktop.recent_projects")
    ui_module = importlib.import_module("catalysis_workbench.desktop.ui_foundation")
    qtcore = importlib.import_module("PySide6.QtCore")

    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        settings = qtcore.QSettings(
            str(base / "settings.ini"),
            qtcore.QSettings.Format.IniFormat,
        )
        ui_settings = ui_module.DesktopUiSettings(settings)
        handle = desktop_app.create_workbench_desktop(
            argv=("cw-v12-block7-smoke",),
            recent_store=recent_module.RecentProjectsStore(settings),
            ui_settings=ui_settings,
        )
        window = handle.window
        qt_app = handle.application
        controller = window.v12_hardening
        assert isinstance(controller, hardening_module.DesktopHardeningController)
        assert version("catalysis-workbench") == "1.1.0"
        assert window.minimumWidth() >= 1200
        assert window.minimumHeight() >= 760

        window.show()
        qt_app.processEvents()
        for width, height, compact in (
            (1920, 1080, False),
            (1440, 900, False),
            (1366, 768, False),
            (1280, 760, True),
            (1200, 760, True),
        ):
            window.resize(width, height)
            qt_app.processEvents()
            assert window.app_shell.sidebar.is_compact is compact
        assert controller.compact_width == 1320
        window.resize(1440, 900)
        qt_app.processEvents()

        shell = window.app_shell
        assert shell.accessibleName() == "CatalysisWorkbench application shell"
        assert shell.sidebar.accessibleName() == "Primary navigation"
        assert shell.status_bar.accessibleName() == "Application status"
        assert shell.sidebar.collapse_button.accessibleName() == "Toggle primary navigation"
        assert shell.command_bar.save_button.accessibleName() == "Save project"
        assert (
            shell.sidebar.collapse_button.focusPolicy()
            == qtcore.Qt.FocusPolicy.StrongFocus
        )
        for page_id, shortcut in (
            ("home", "Ctrl+1"),
            ("analysis", "Ctrl+2"),
            ("figure", "Ctrl+3"),
            ("export", "Ctrl+4"),
        ):
            action = controller.navigation_actions[page_id]
            assert action.shortcut().toString() == shortcut
            assert shell.sidebar._buttons[page_id].accessibleName()
        stylesheet = shell.styleSheet()
        assert "cw-block7-a11y" in stylesheet
        assert "QPushButton#cwNavButton:focus" in stylesheet

        screen = window.screen() or qt_app.primaryScreen()
        assert screen is not None
        assert screen.logicalDotsPerInch() > 0
        assert screen.devicePixelRatio() > 0
        assert window.devicePixelRatioF() > 0

        # Generic XY: route shortcuts, theme identity, Figure and Export.
        generic_a_path = base / "generic-a.csv"
        generic_b_path = base / "generic-b.csv"
        generic_a_path.write_text("x,y\n0,1\n1,2\n2,3\n", encoding="utf-8")
        generic_b_path.write_text("x,y\n0,3\n1,2\n2,1\n", encoding="utf-8")
        generic_a = _mapped(
            application,
            generic_a_path,
            name="Pb1",
            y_role="signal",
            y_unit="a.u.",
        )
        generic_b = _mapped(
            application,
            generic_b_path,
            name="Pb2",
            y_role="signal",
            y_unit="a.u.",
        )
        window.start_analysis("generic_xy")
        window.add_data_items(((generic_a, generic_a_path), (generic_b, generic_b_path)))
        qt_app.processEvents()
        assert controller.navigation_actions["analysis"].isEnabled()
        assert controller.navigation_actions["figure"].isEnabled()
        controller.navigation_actions["figure"].trigger()
        qt_app.processEvents()
        assert window.stack.currentWidget() is window.figure_page
        window._create_figure_ui("processed", "publication")
        generic_project = base / "generic-project"
        window.save_project_path(generic_project)
        state = window.session.state
        assert state.document is not None
        document_sha = state.document.document_sha256
        figure_spec = window.session.figure_draft("processed").figure_spec
        assert not state.is_dirty

        controller.theme_actions[ui_module.ThemeMode.DARK].trigger()
        qt_app.processEvents()
        assert ui_settings.theme_mode() is ui_module.ThemeMode.DARK
        assert "cw-block7-a11y:dark" in shell.styleSheet()
        assert "color: #171a1f;" in shell.styleSheet()
        assert window.session.state.document.document_sha256 == document_sha
        assert window.session.figure_draft("processed").figure_spec == figure_spec
        assert not window.session.state.is_dirty

        controller.theme_actions[ui_module.ThemeMode.LIGHT].trigger()
        qt_app.processEvents()
        assert ui_settings.theme_mode() is ui_module.ThemeMode.LIGHT
        assert "cw-block7-a11y:light" in shell.styleSheet()
        assert "color: #ffffff;" in shell.styleSheet()
        assert window.session.state.document.document_sha256 == document_sha
        assert window.session.figure_draft("processed").figure_spec == figure_spec
        assert not window.session.state.is_dirty

        controller.theme_actions[ui_module.ThemeMode.SYSTEM].trigger()
        qt_app.processEvents()
        assert ui_settings.theme_mode() is ui_module.ThemeMode.SYSTEM
        assert not window.session.state.is_dirty
        window._refresh_figure_workbench("processed")
        qt_app.processEvents()
        assert controller.navigation_actions["export"].isEnabled()
        _export_current(window, base / "generic-package")

        # LSV: explicit processing survives the complete v1.2 path.
        window.go_home(discard_changes=True)
        lsv_path = base / "lsv.csv"
        lsv_path.write_text(
            "Potential,Current\n0.0,-2.0\n0.5,-4.0\n1.0,-6.0\n",
            encoding="utf-8",
        )
        lsv = _mapped(
            application,
            lsv_path,
            name="Pb3",
            y_role="current",
            y_unit="mA",
            reference="Ag/AgCl",
        )
        window.start_analysis("lsv")
        window.add_data_items(((lsv, lsv_path),))
        window._replace_analysis_spec_ui(
            application.LSVAnalysisSpec(
                common=application.LSVProcessingSpec(
                    rhe_mode="direct",
                    rhe_offset_v=0.2,
                    electrode_area_cm2=2.0,
                    normalize_to_current_density=True,
                ),
                analysis_range=application.AnalysisRange(x_min=0.1, x_max=1.1),
            )
        )
        window._show_figure_ui()
        window._create_figure_ui("processed", "publication")
        window.save_project_path(base / "lsv-project")
        window._refresh_figure_workbench("processed")
        _export_current(window, base / "lsv-package")

        # FE & Partial Current: two explicit views remain independently exportable.
        window.go_home(discard_changes=True)
        current_path = base / "current.csv"
        fe_path = base / "fe.csv"
        current_path.write_text(
            "Potential,CurrentDensity\n-0.5,-2.0\n-0.6,-4.0\n-0.7,-6.0\n",
            encoding="utf-8",
        )
        fe_path.write_text(
            "Potential,FE\n-0.5,50\n-0.6,25\n-0.7,20\n",
            encoding="utf-8",
        )
        current = _mapped(
            application,
            current_path,
            name="total current",
            y_role="current_density",
            y_unit="mA/cm^2",
        )
        fe = _mapped(
            application,
            fe_path,
            name="FECO",
            y_role="faradaic_efficiency",
            y_unit="%",
        )
        window.start_analysis("fe_partial_current")
        window.add_data_items(((current, current_path), (fe, fe_path)))
        window._replace_analysis_spec_ui(
            application.FEPartialCurrentAnalysisSpec(
                pairs=(application.PartialCurrentPair(current.data_id, fe.data_id),)
            )
        )
        window._show_figure_ui()
        window._create_figure_ui("fe", "publication")
        window._create_figure_ui("partial_current", "publication")
        window.save_project_path(base / "fe-project")
        for view_id in ("fe", "partial_current"):
            window._refresh_figure_workbench(view_id)
            _export_current(window, base / f"{view_id}-package")
            window._back_to_figure_ui()

        state = window.session.state
        assert state.document is not None
        assert state.document.schema_version == 4
        assert window.minimumWidth() >= 1200
        assert window.minimumHeight() >= 760

        window.go_home(discard_changes=True)
        window.close()
        qt_app.processEvents()

    print("installed v1.2 Block-7 desktop smoke: ok")


if __name__ == "__main__":
    main()
