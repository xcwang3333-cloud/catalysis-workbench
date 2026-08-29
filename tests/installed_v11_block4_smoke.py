"""Fresh-wheel headless smoke for v1.1 Block-4 Figure Workbench state."""

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
    GenericXYAnalysisSpec,
    TabularMappingSpec,
    source_spec_from_file,
)


def _spec(path: Path, *, name: str) -> DataSeriesSpec:
    return DataSeriesSpec(
        source=source_spec_from_file(path),
        mapping=TabularMappingSpec(
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
    assert "PySide6" not in sys.modules
    assert "PyQt6" not in sys.modules
    assert "matplotlib.pyplot" not in sys.modules

    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        first_path = base / "first.csv"
        second_path = base / "second.csv"
        first_path.write_text("x,y\n0,1\n1,2\n2,3\n", encoding="utf-8")
        second_path.write_text("x,y\n0,3\n1,2\n2,1\n", encoding="utf-8")
        first = _spec(first_path, name="Pb1")
        second = _spec(second_path, name="Pb2")

        session = AnalysisSession()
        session.new_analysis("generic_xy")
        session.add_data_series_batch(
            ((first, first_path), (second, second_path))
        )
        evaluation = session.evaluate_analysis()
        assert evaluation.status == "success"
        assert evaluation.result is not None
        scientific_sha = evaluation.result.workflow_run.content_sha256

        state = session.create_figure("processed")
        assert state.document is not None
        assert state.document.schema_version == 4
        draft = session.figure_draft("processed")
        assert draft.trace_order == (first.data_id, second.data_id)
        assert draft.figure_spec.series_styles[first.data_id].label == "Pb1"
        assert session.figure_is_stale("processed") is False

        edited = draft.figure_spec.updated(xlim=(0.5, 1.5)).with_series_style(
            first.data_id,
            label="Pb₁-N/C",
            line_width=2.0,
        )
        session.replace_figure_spec("processed", edited)
        figure, axes = session.render_figure("processed")
        assert figure.canvas is not None
        assert tuple(axes.get_xlim()) == (0.5, 1.5)
        np.testing.assert_allclose(axes.lines[0].get_xdata(), [0.0, 1.0, 2.0])
        assert axes.lines[0].get_label() == "Pb₁-N/C"
        rerun = session.evaluate_analysis()
        assert rerun.status == "success"
        assert rerun.result is not None
        assert rerun.result.workflow_run.content_sha256 == scientific_sha

        session.rename_data_series(first.data_id, "analysis-only rename")
        assert session.figure_is_stale("processed") is False
        assert session.figure_draft("processed").figure_spec.series_styles[
            first.data_id
        ].label == "Pb₁-N/C"

        session.replace_analysis_spec(
            GenericXYAnalysisSpec(
                analysis_range=AnalysisRange(x_min=0.75, x_max=2.0)
            )
        )
        assert session.figure_is_stale("processed") is True
        session.refresh_figure("processed")
        assert session.figure_is_stale("processed") is False
        assert session.figure_draft("processed").figure_spec.series_styles[
            first.data_id
        ].label == "Pb₁-N/C"

        project = base / "project"
        session.save_project_as(project)
        payload = json.loads((project / "project.json").read_text(encoding="utf-8"))
        assert payload["document"]["schema_version"] == 4
        assert len(payload["document"]["figures"]) == 1

        reopened = AnalysisSession()
        reopened.open_project(project)
        assert reopened.figure_is_stale("processed") is False
        reopened_figure, reopened_axes = reopened.render_figure("processed")
        assert reopened_figure.canvas is not None
        assert tuple(reopened_axes.get_xlim()) == (0.5, 1.5)

    print("installed v1.1 Block-4 smoke: ok")


if __name__ == "__main__":
    main()
