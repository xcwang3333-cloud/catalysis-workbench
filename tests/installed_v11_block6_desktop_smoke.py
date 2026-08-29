"""Fresh-wheel offscreen dogfood smoke for the complete v1.1 desktop path."""

from __future__ import annotations

import importlib
import json
import tempfile
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


def _package_sha(path: Path) -> str:
    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    return manifest["package_sha256"]


def _assert_reopen(window, project: Path, document_sha: str, run_sha: str, views) -> None:
    window.go_home(discard_changes=True)
    window.open_project_path(project)
    state = window.session.state
    assert state.document is not None
    assert state.document.document_sha256 == document_sha
    evaluation = window.session.evaluate_analysis()
    assert evaluation.status == "success"
    assert evaluation.result is not None
    assert evaluation.result.workflow_run.content_sha256 == run_sha
    for view_id in views:
        assert window.session.figure_is_stale(view_id) is False


def main() -> None:
    application = importlib.import_module("catalysis_workbench.application")
    desktop_app = importlib.import_module("catalysis_workbench.desktop.app")
    recent_module = importlib.import_module("catalysis_workbench.desktop.recent_projects")
    workbench_module = importlib.import_module("catalysis_workbench.desktop.workbench_window")
    qtcore = importlib.import_module("PySide6.QtCore")

    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        settings = qtcore.QSettings(
            str(base / "settings.ini"),
            qtcore.QSettings.Format.IniFormat,
        )
        store = recent_module.RecentProjectsStore(settings)
        handle = desktop_app.create_workbench_desktop(
            argv=("cw-v11-block6-desktop-smoke",),
            recent_store=store,
        )
        window = handle.window
        qt_app = handle.application
        assert window.stack.currentWidget() is window.home_page

        # Generic XY: unsaved Figure -> explicit Save from Export -> package -> reopen.
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
        window._show_figure_ui()
        window._create_figure_ui("processed", "publication")
        window._show_export_ui()
        assert window.stack.currentWidget() is window.export_page
        assert window.export_page.save_project_button.isVisible()
        assert window.export_page.export_button.isEnabled() is False

        generic_project = base / "generic-project"
        original_save = window._save_interactive

        def save_generic() -> bool:
            window.save_project_path(generic_project)
            return True

        window._save_interactive = save_generic
        try:
            window.export_page.save_requested.emit()
        finally:
            window._save_interactive = original_save
        assert window.session.state.project_root == generic_project.resolve(strict=False)
        assert window.export_page.save_project_button.isHidden()

        _minimal_export(window.export_page)
        generic_package = base / "generic-package"
        window.export_page.set_location(generic_package)
        assert window.export_page.export_button.isEnabled()
        generic_state = window.session.state
        assert generic_state.document is not None
        generic_document_sha = generic_state.document.document_sha256
        generic_eval = window.session.evaluate_analysis()
        assert generic_eval.result is not None
        generic_run_sha = generic_eval.result.workflow_run.content_sha256
        window._export_package_ui(str(generic_package), window.export_page.options())
        assert (generic_package / "figure.svg").is_file()
        assert (generic_package / "source-data" / "trace-001.txt").is_file()
        assert window.export_page.success_actions.isVisible()
        generic_package_sha = _package_sha(generic_package)
        window.export_page._prepare_another_export()
        assert window.export_page.location_edit.text() == ""
        assert window.export_page.success_actions.isHidden()

        # Repeated presentation refreshes must not reopen unchanged Recent Projects.
        open_calls = 0
        original_open = workbench_module.open_analysis_project

        def counted_open(root):
            nonlocal open_calls
            open_calls += 1
            return original_open(root)

        workbench_module.open_analysis_project = counted_open
        try:
            window.refresh_views()
            window.refresh_views()
            assert open_calls == 0
            store.add(generic_project)
            window.refresh_views()
            assert open_calls == 1
            window.refresh_views()
            assert open_calls == 1
        finally:
            workbench_module.open_analysis_project = original_open

        _assert_reopen(
            window,
            generic_project,
            generic_document_sha,
            generic_run_sha,
            ("processed",),
        )
        window._show_figure_ui()
        window._refresh_figure_workbench("processed")
        window._show_export_ui()
        _minimal_export(window.export_page)
        generic_package_reopen = base / "generic-package-reopen"
        window.export_page.set_location(generic_package_reopen)
        window._export_package_ui(
            str(generic_package_reopen),
            window.export_page.options(),
        )
        assert _package_sha(generic_package_reopen) == generic_package_sha

        # LSV: explicit RHE offset and current-density normalization through package/reopen.
        window._back_to_figure_ui()
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
        lsv_project = base / "lsv-project"
        window.save_project_path(lsv_project)
        lsv_state = window.session.state
        assert lsv_state.document is not None
        lsv_document_sha = lsv_state.document.document_sha256
        lsv_eval = window.session.evaluate_analysis()
        assert lsv_eval.result is not None
        lsv_run_sha = lsv_eval.result.workflow_run.content_sha256
        window._refresh_figure_workbench("processed")
        window._show_export_ui()
        _minimal_export(window.export_page)
        lsv_package = base / "lsv-package"
        window.export_page.set_location(lsv_package)
        window._export_package_ui(str(lsv_package), window.export_page.options())
        assert (lsv_package / "figure.svg").is_file()
        _assert_reopen(
            window,
            lsv_project,
            lsv_document_sha,
            lsv_run_sha,
            ("processed",),
        )

        # FE & Partial Current: one explicit pair and two independently exportable views.
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
        fe_project = base / "fe-project"
        window.save_project_path(fe_project)
        fe_state = window.session.state
        assert fe_state.document is not None
        fe_document_sha = fe_state.document.document_sha256
        fe_eval = window.session.evaluate_analysis()
        assert fe_eval.result is not None
        fe_run_sha = fe_eval.result.workflow_run.content_sha256

        exported_shas: dict[str, str] = {}
        for view_id in ("fe", "partial_current"):
            window._refresh_figure_workbench(view_id)
            window._show_export_ui()
            _minimal_export(window.export_page)
            target = base / f"{view_id}-package"
            window.export_page.set_location(target)
            window._export_package_ui(str(target), window.export_page.options())
            assert (target / "figure.svg").is_file()
            exported_shas[view_id] = _package_sha(target)
            window._back_to_figure_ui()
        assert exported_shas["fe"] != exported_shas["partial_current"]

        _assert_reopen(
            window,
            fe_project,
            fe_document_sha,
            fe_run_sha,
            ("fe", "partial_current"),
        )

        summary, guidance, details = window._error_presentation(
            RuntimeError("workspace changed outside this session")
        )
        assert summary == "Project changed outside CatalysisWorkbench."
        assert "Reopen" in guidance
        assert "RuntimeError" in details

        window.go_home(discard_changes=True)
        window.close()
        qt_app.processEvents()

    print("installed v1.1 Block-6 desktop dogfood smoke: ok")


if __name__ == "__main__":
    main()
