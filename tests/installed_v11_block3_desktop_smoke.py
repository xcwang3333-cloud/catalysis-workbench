"""Fresh-wheel offscreen smoke for v1.1 Block-3 live analysis UX."""

from __future__ import annotations

import importlib
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
            argv=("cw-v11-block3-desktop-smoke",),
            recent_store=recent_module.RecentProjectsStore(settings),
        )
        window = handle.window
        qt_app = handle.application

        lsv_path = base / "lsv.csv"
        lsv_path.write_text(
            "Potential,Current\n0.0,-2.0\n0.5,-4.0\n",
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
        window.add_data_items([(lsv, lsv_path)])
        panel = window.analysis_page.processing_panel
        assert panel.potential_box.isVisible()
        assert not panel.pair_box.isVisible()
        assert window.analysis_page.continue_button.isEnabled() is False

        processing = application.LSVAnalysisSpec(
            common=application.LSVProcessingSpec(
                rhe_mode="direct",
                rhe_offset_v=0.2,
                electrode_area_cm2=2.0,
                normalize_to_current_density=True,
            ),
            analysis_range=application.AnalysisRange(x_min=0.1, x_max=0.8),
        )
        window._replace_analysis_spec_ui(processing)
        assert window._last_valid_result is not None
        assert window.analysis_page.view_combo.findData("raw") >= 0
        assert window.analysis_page.view_combo.findData("processed") >= 0
        committed_sha = window.session.state.document.document_sha256
        last_run_sha = window._last_valid_result.workflow_run.content_sha256

        direct_index = panel.rhe_mode_combo.findData("direct")
        panel.rhe_mode_combo.setCurrentIndex(direct_index)
        panel.rhe_offset_edit.setText("")
        panel._apply_draft_now()
        assert panel.has_unapplied_draft is True
        assert window.session.state.document.document_sha256 == committed_sha
        assert window._last_valid_result.workflow_run.content_sha256 == last_run_sha
        assert "Previous valid result" in window.analysis_page.preview_note.text()
        panel.discard_draft()
        window._refresh_data_preview()

        window.go_home(discard_changes=True)
        current_path = base / "current.csv"
        current_path.write_text(
            "Potential,CurrentDensity\n-0.5,-2.0\n-0.6,-4.0\n",
            encoding="utf-8",
        )
        fe_path = base / "fe.csv"
        fe_path.write_text(
            "Potential,FE\n-0.5,50\n-0.6,25\n",
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
        window.add_data_items([(current, current_path), (fe, fe_path)])
        fe_panel = window.analysis_page.processing_panel
        assert fe_panel.pair_box.isVisible()
        window._replace_analysis_spec_ui(
            application.FEPartialCurrentAnalysisSpec(
                pairs=(application.PartialCurrentPair(current.data_id, fe.data_id),)
            )
        )
        assert window._last_valid_result is not None
        assert window.analysis_page.view_combo.findData("fe") >= 0
        assert window.analysis_page.view_combo.findData("partial_current") >= 0
        assert window.analysis_page.view_combo.findData("raw") == -1

        window.go_home(discard_changes=True)
        window.close()
        qt_app.processEvents()

    print("installed v1.1 Block-3 desktop smoke: ok")


if __name__ == "__main__":
    main()
