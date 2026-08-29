from __future__ import annotations

from dataclasses import replace

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


def _mapped_series(
    path,
    *,
    display_name: str,
    y_role: str,
    y_unit: str,
    x_reference: str = "RHE",
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
            x_reference=x_reference,
        ),
        display_name=display_name,
    )


def test_lsv_live_evaluation_reuses_reviewed_processing_and_stable_identity(tmp_path) -> None:
    source = tmp_path / "lsv.csv"
    source.write_text(
        "Potential,Current\n0.0,-2.0\n0.5,-4.0\n",
        encoding="utf-8",
    )
    spec = _mapped_series(
        source,
        display_name="Pb3",
        y_role="current",
        y_unit="mA",
        x_reference="Ag/AgCl",
    )
    session = AnalysisSession()
    session.new_analysis("lsv")
    session.add_data_series(spec, source)
    processing = LSVAnalysisSpec(
        common=LSVProcessingSpec(
            rhe_mode="direct",
            rhe_offset_v=0.2,
            electrode_area_cm2=2.0,
            normalize_to_current_density=True,
        ),
        analysis_range=AnalysisRange(x_min=0.1, x_max=0.8),
    )
    session.replace_analysis_spec(processing)

    evaluation = session.evaluate_analysis()
    assert evaluation.status == "success"
    assert evaluation.result is not None
    result = evaluation.result
    assert tuple(view.view_id for view in result.views) == ("processed",)
    series = result.views[0].series[0]
    np.testing.assert_allclose(series.x, [0.2, 0.7])
    np.testing.assert_allclose(series.y, [-1.0, -2.0])
    assert series.x_axis.metadata["reference"] == "RHE"
    assert series.y_axis.name == "current_density"
    first_run_sha = result.workflow_run.content_sha256

    session.rename_data_series(spec.data_id, "Pb₃-N/C")
    renamed = session.evaluate_analysis()
    assert renamed.status == "success"
    assert renamed.result is not None
    assert renamed.result.workflow_run.content_sha256 == first_run_sha
    assert renamed.result.views[0].series[0].label == "Pb₃-N/C"

    changed_processing = replace(
        processing,
        analysis_range=AnalysisRange(x_min=0.3, x_max=0.8),
    )
    session.replace_analysis_spec(changed_processing)
    changed = session.evaluate_analysis()
    assert changed.status == "success"
    assert changed.result is not None
    assert changed.result.workflow_run.content_sha256 != first_run_sha
    np.testing.assert_allclose(changed.result.views[0].series[0].x, [0.7])


def test_fe_partial_current_requires_explicit_pair_and_never_interpolates(tmp_path) -> None:
    current_path = tmp_path / "current.csv"
    current_path.write_text(
        "Potential,CurrentDensity\n-0.5,-2.0\n-0.6,-4.0\n",
        encoding="utf-8",
    )
    fe_path = tmp_path / "fe.csv"
    fe_path.write_text(
        "Potential,FE\n-0.5,50\n-0.6,25\n",
        encoding="utf-8",
    )
    current = _mapped_series(
        current_path,
        display_name="total current",
        y_role="current_density",
        y_unit="mA/cm^2",
    )
    fe = _mapped_series(
        fe_path,
        display_name="FECO",
        y_role="faradaic_efficiency",
        y_unit="%",
    )
    session = AnalysisSession()
    session.new_analysis("fe_partial_current")
    session.add_data_series_batch(((current, current_path), (fe, fe_path)))

    incomplete = session.evaluate_analysis()
    assert incomplete.status == "incomplete"
    pair = PartialCurrentPair(current.data_id, fe.data_id)
    session.replace_analysis_spec(FEPartialCurrentAnalysisSpec(pairs=(pair,)))
    evaluation = session.evaluate_analysis()
    assert evaluation.status == "success"
    assert evaluation.result is not None
    assert tuple(view.view_id for view in evaluation.result.views) == (
        "fe",
        "partial_current",
    )
    np.testing.assert_allclose(evaluation.result.views[1].series[0].y, [-1.0, -1.0])
    stable_sha = evaluation.result.workflow_run.content_sha256

    session.rename_data_series(fe.data_id, "CO")
    renamed = session.evaluate_analysis()
    assert renamed.status == "success"
    assert renamed.result is not None
    assert renamed.result.workflow_run.content_sha256 == stable_sha

    mismatched_path = tmp_path / "fe_mismatch.csv"
    mismatched_path.write_text(
        "Potential,FE\n-0.5,50\n-0.61,25\n",
        encoding="utf-8",
    )
    mismatched_fe = _mapped_series(
        mismatched_path,
        display_name="FECO mismatch",
        y_role="faradaic_efficiency",
        y_unit="%",
    )
    other = AnalysisSession()
    other.new_analysis("fe_partial_current")
    other.add_data_series_batch(
        ((current, current_path), (mismatched_fe, mismatched_path))
    )
    other.replace_analysis_spec(
        FEPartialCurrentAnalysisSpec(
            pairs=(PartialCurrentPair(current.data_id, mismatched_fe.data_id),)
        )
    )
    failed = other.evaluate_analysis()
    assert failed.status == "error"
    assert failed.message is not None
    assert "match exactly" in failed.message


def test_processing_references_remap_and_remove_atomically_with_data_edits(tmp_path) -> None:
    current_path = tmp_path / "current.csv"
    current_path.write_text(
        "Potential,CurrentDensity\n-0.5,-2.0\n-0.6,-4.0\n",
        encoding="utf-8",
    )
    fe_path = tmp_path / "fe.csv"
    fe_path.write_text("Potential,FE\n-0.5,50\n-0.6,25\n", encoding="utf-8")
    current = _mapped_series(
        current_path,
        display_name="current",
        y_role="current_density",
        y_unit="mA/cm^2",
    )
    fe = _mapped_series(
        fe_path,
        display_name="FE",
        y_role="faradaic_efficiency",
        y_unit="%",
    )
    session = AnalysisSession()
    session.new_analysis("fe_partial_current")
    session.add_data_series_batch(((current, current_path), (fe, fe_path)))
    override = LSVProcessingSpec(electrode_area_cm2=1.0)
    session.replace_analysis_spec(
        FEPartialCurrentAnalysisSpec(
            current_overrides={current.data_id: override},
            pairs=(PartialCurrentPair(current.data_id, fe.data_id),),
        )
    )
    impact = session.analysis_dependency_impact(current.data_id)
    assert impact.override_count == 1
    assert impact.partial_current_pair_count == 1

    new_mapping = replace(current.mapping, y_unit="A/cm^2")
    remapped = session.replace_data_mapping(current.data_id, new_mapping)
    assert remapped.document is not None
    remapped_current = remapped.document.data_series[0].data_id
    assert remapped_current != current.data_id
    analysis = remapped.document.analysis
    assert isinstance(analysis, FEPartialCurrentAnalysisSpec)
    assert tuple(analysis.current_overrides) == (remapped_current,)
    assert analysis.pairs[0].current_data_id == remapped_current

    undone = session.undo()
    assert undone.document is not None
    restored = undone.document.analysis
    assert isinstance(restored, FEPartialCurrentAnalysisSpec)
    assert restored.pairs[0].current_data_id == current.data_id

    fe_impact = session.analysis_dependency_impact(fe.data_id)
    assert fe_impact.partial_current_pair_count == 1
    removed = session.remove_data_series(fe.data_id)
    assert removed.document is not None
    removed_analysis = removed.document.analysis
    assert isinstance(removed_analysis, FEPartialCurrentAnalysisSpec)
    assert removed_analysis.pairs == ()
    restored_again = session.undo()
    assert restored_again.document is not None
    assert isinstance(restored_again.document.analysis, FEPartialCurrentAnalysisSpec)
    assert len(restored_again.document.analysis.pairs) == 1
