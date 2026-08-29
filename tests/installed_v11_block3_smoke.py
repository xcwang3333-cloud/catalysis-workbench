"""Fresh-wheel headless smoke for v1.1 Block-3 live scientific analysis."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np

from catalysis_workbench.application import (
    AnalysisRange,
    AnalysisSession,
    DataSeriesSpec,
    FEPartialCurrentAnalysisSpec,
    LSVAnalysisSpec,
    LSVProcessingSpec,
    PartialCurrentPair,
    TabularMappingSpec,
    source_spec_from_file,
)
from catalysis_workbench.workflow import list_recipe_operations


def _spec(
    path: Path,
    *,
    name: str,
    y_role: str,
    y_unit: str,
    reference: str = "RHE",
) -> DataSeriesSpec:
    return DataSeriesSpec(
        source=source_spec_from_file(path),
        mapping=TabularMappingSpec(
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
    assert "PySide6" not in sys.modules
    assert "PyQt6" not in sys.modules
    assert "matplotlib.pyplot" not in sys.modules
    assert tuple(item.operation_id for item in list_recipe_operations()) == (
        "catalysis.processing.crop.v1",
        "catalysis.processing.offset.v1",
        "catalysis.processing.normalize.v1",
    )

    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        lsv_path = base / "lsv.csv"
        lsv_path.write_text(
            "Potential,Current\n0.0,-2.0\n0.5,-4.0\n",
            encoding="utf-8",
        )
        lsv = _spec(
            lsv_path,
            name="Pb3",
            y_role="current",
            y_unit="mA",
            reference="Ag/AgCl",
        )
        session = AnalysisSession()
        session.new_analysis("lsv")
        session.add_data_series(lsv, lsv_path)
        session.replace_analysis_spec(
            LSVAnalysisSpec(
                common=LSVProcessingSpec(
                    rhe_mode="direct",
                    rhe_offset_v=0.2,
                    electrode_area_cm2=2.0,
                    normalize_to_current_density=True,
                ),
                analysis_range=AnalysisRange(x_min=0.1, x_max=0.8),
            )
        )
        evaluation = session.evaluate_analysis()
        assert evaluation.status == "success"
        assert evaluation.result is not None
        series = evaluation.result.views[0].series[0]
        np.testing.assert_allclose(series.x, [0.2, 0.7])
        np.testing.assert_allclose(series.y, [-1.0, -2.0])
        run_sha = evaluation.result.workflow_run.content_sha256

        session.rename_data_series(lsv.data_id, "Pb₃-N/C")
        renamed = session.evaluate_analysis()
        assert renamed.status == "success"
        assert renamed.result is not None
        assert renamed.result.workflow_run.content_sha256 == run_sha

        project = base / "lsv-project"
        session.save_project_as(project)
        payload = json.loads((project / "project.json").read_text(encoding="utf-8"))
        assert payload["document"]["schema_version"] == 3
        assert "analysis" in payload["document"]
        reopened = AnalysisSession()
        reopened.open_project(project)
        assert reopened.state.document is not None
        assert reopened.state.document.schema_version == 3
        assert reopened.evaluate_analysis().status == "success"

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
        current = _spec(
            current_path,
            name="total current",
            y_role="current_density",
            y_unit="mA/cm^2",
        )
        fe = _spec(
            fe_path,
            name="FECO",
            y_role="faradaic_efficiency",
            y_unit="%",
        )
        partial = AnalysisSession()
        partial.new_analysis("fe_partial_current")
        partial.add_data_series_batch(
            ((current, current_path), (fe, fe_path))
        )
        assert partial.evaluate_analysis().status == "incomplete"
        partial.replace_analysis_spec(
            FEPartialCurrentAnalysisSpec(
                pairs=(PartialCurrentPair(current.data_id, fe.data_id),)
            )
        )
        partial_evaluation = partial.evaluate_analysis()
        assert partial_evaluation.status == "success"
        assert partial_evaluation.result is not None
        assert tuple(view.view_id for view in partial_evaluation.result.views) == (
            "fe",
            "partial_current",
        )
        np.testing.assert_allclose(
            partial_evaluation.result.views[1].series[0].y,
            [-1.0, -1.0],
        )

    print("installed v1.1 Block-3 smoke: ok")


if __name__ == "__main__":
    main()
