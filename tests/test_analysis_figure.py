from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from catalysis_workbench.application import (
    AnalysisRange,
    AnalysisSession,
    DataSeriesSpec,
    LSVAnalysisSpec,
    TabularMappingSpec,
    source_spec_from_file,
)
from catalysis_workbench.visualization import VisualizationError


def _mapped(
    path,
    *,
    name: str,
    task_role: str = "signal",
    unit: str = "a.u.",
) -> DataSeriesSpec:
    return DataSeriesSpec(
        source=source_spec_from_file(path),
        mapping=TabularMappingSpec(
            delimiter=",",
            x_column=0,
            y_column=1,
            x_role="potential",
            y_role=task_role,
            x_unit="V",
            y_unit=unit,
            x_reference="RHE",
        ),
        display_name=name,
    )


def _generic_session(tmp_path) -> tuple[AnalysisSession, DataSeriesSpec, DataSeriesSpec]:
    first_path = tmp_path / "a.csv"
    first_path.write_text("x,y\n0,1\n1,2\n2,3\n", encoding="utf-8")
    second_path = tmp_path / "b.csv"
    second_path.write_text("x,y\n0,3\n1,2\n2,1\n", encoding="utf-8")
    first = _mapped(first_path, name="A")
    second = _mapped(second_path, name="B")
    session = AnalysisSession()
    session.new_analysis("generic_xy")
    session.add_data_series_batch(((first, first_path), (second, second_path)))
    return session, first, second


def test_figure_draft_is_presentation_only_and_survives_rename_reorder(tmp_path) -> None:
    session, first, second = _generic_session(tmp_path)
    evaluated = session.evaluate_analysis()
    assert evaluated.status == "success"
    assert evaluated.result is not None
    scientific_sha = evaluated.result.workflow_run.content_sha256

    created = session.create_figure("processed")
    assert created.document is not None
    assert created.document.schema_version == 4
    draft = created.document.figures[0]
    assert draft.view_id == "processed"
    assert draft.trace_order == (first.data_id, second.data_id)
    assert draft.figure_spec.series_styles[first.data_id].label == "A"
    figure_sha = draft.figure_sha256

    session.rename_data_series(first.data_id, "Renamed analysis label")
    assert session.figure_is_stale("processed") is False
    renamed = session.figure_draft("processed")
    assert renamed.figure_spec.series_styles[first.data_id].label == "A"
    assert renamed.figure_sha256 == figure_sha

    session.move_data_series(second.data_id, 0)
    assert session.figure_is_stale("processed") is False
    assert session.figure_draft("processed").trace_order == (
        first.data_id,
        second.data_id,
    )
    reevaluated = session.evaluate_analysis()
    assert reevaluated.status == "success"
    assert reevaluated.result is not None
    assert reevaluated.result.workflow_run.content_sha256 == scientific_sha


def test_scientific_processing_change_marks_figure_stale_until_explicit_refresh(tmp_path) -> None:
    source = tmp_path / "lsv.csv"
    source.write_text("x,y\n0,-1\n0.5,-2\n1,-3\n", encoding="utf-8")
    spec = _mapped(source, name="LSV", task_role="current_density", unit="mA/cm^2")
    session = AnalysisSession()
    session.new_analysis("lsv")
    session.add_data_series(spec, source)
    session.create_figure("processed")
    original = session.figure_draft("processed")

    session.replace_analysis_spec(
        LSVAnalysisSpec(analysis_range=AnalysisRange(x_min=0.4, x_max=1.0))
    )
    assert session.figure_is_stale("processed") is True
    with pytest.raises(RuntimeError, match="refresh"):
        session.render_figure("processed")

    session.refresh_figure("processed")
    refreshed = session.figure_draft("processed")
    assert refreshed.source_view_sha256 != original.source_view_sha256
    assert refreshed.figure_spec == original.figure_spec
    assert session.figure_is_stale("processed") is False


def test_display_range_changes_document_but_not_scientific_run_or_line_data(tmp_path) -> None:
    session, first, _second = _generic_session(tmp_path)
    before = session.evaluate_analysis()
    assert before.status == "success"
    assert before.result is not None
    run_sha = before.result.workflow_run.content_sha256
    session.create_figure("processed")
    draft = session.figure_draft("processed")
    changed_spec = draft.figure_spec.updated(xlim=(0.5, 1.5), ylim=(1.2, 2.8))
    session.replace_figure_spec("processed", changed_spec)

    after = session.evaluate_analysis()
    assert after.status == "success"
    assert after.result is not None
    assert after.result.workflow_run.content_sha256 == run_sha
    figure, ax = session.render_figure("processed")
    assert tuple(ax.get_xlim()) == pytest.approx((0.5, 1.5))
    np.testing.assert_allclose(ax.lines[0].get_xdata(), [0.0, 1.0, 2.0])
    np.testing.assert_allclose(ax.lines[0].get_ydata(), [1.0, 2.0, 3.0])
    assert first.data_id in session.figure_draft("processed").figure_spec.series_styles
    assert figure.canvas is not None


def test_only_visible_traces_participate_in_axis_compatibility(tmp_path) -> None:
    first_path = tmp_path / "current.csv"
    first_path.write_text("x,y\n0,1\n1,2\n", encoding="utf-8")
    second_path = tmp_path / "voltage.csv"
    second_path.write_text("x,y\n0,3\n1,4\n", encoding="utf-8")
    first = _mapped(first_path, name="Current", unit="A")
    second = _mapped(second_path, name="Voltage", unit="V")
    session = AnalysisSession()
    session.new_analysis("generic_xy")
    session.add_data_series_batch(((first, first_path), (second, second_path)))
    session.create_figure("processed")

    with pytest.raises((VisualizationError, RuntimeError), match="units"):
        session.render_figure("processed")

    draft = session.figure_draft("processed")
    hidden = draft.figure_spec.with_series_style(second.data_id, visible=False)
    session.replace_figure_spec("processed", hidden)
    figure, ax = session.render_figure("processed")
    assert len(ax.lines) == 1
    assert ax.lines[0].get_label() == "Current"
    assert figure.canvas is not None

    all_hidden = session.figure_draft("processed").figure_spec.with_series_style(
        first.data_id,
        visible=False,
    )
    session.replace_figure_spec("processed", all_hidden)
    with pytest.raises(RuntimeError, match="at least one"):
        session.render_figure("processed")


def test_schema4_project_round_trip_preserves_figure_draft(tmp_path) -> None:
    session, _first, _second = _generic_session(tmp_path)
    session.create_figure("processed")
    draft = session.figure_draft("processed")
    project = tmp_path / "project"
    session.save_project_as(project)

    reopened = AnalysisSession()
    state = reopened.open_project(project)
    assert state.document is not None
    assert state.document.schema_version == 4
    assert len(state.document.figures) == 1
    assert state.document.figures[0].figure_sha256 == draft.figure_sha256
    assert reopened.figure_is_stale("processed") is False


def test_figure_edits_are_undoable_without_reprocessing(tmp_path) -> None:
    session, first, _second = _generic_session(tmp_path)
    session.create_figure("processed")
    created = session.figure_draft("processed")
    run = session.evaluate_analysis()
    assert run.result is not None
    run_sha = run.result.workflow_run.content_sha256

    updated = created.figure_spec.with_series_style(
        first.data_id,
        color="#123456",
        line_width=2.0,
    )
    session.replace_figure_spec("processed", updated)
    assert session.figure_draft("processed").figure_sha256 != created.figure_sha256
    session.undo()
    assert session.figure_draft("processed").figure_sha256 == created.figure_sha256
    session.redo()
    assert session.figure_draft("processed").figure_spec.series_styles[first.data_id].color == "#123456"
    again = session.evaluate_analysis()
    assert again.result is not None
    assert again.result.workflow_run.content_sha256 == run_sha
