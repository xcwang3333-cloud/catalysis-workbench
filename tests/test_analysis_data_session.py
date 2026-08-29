from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import pytest

from catalysis_workbench.application import (
    AnalysisProjectError,
    AnalysisSession,
    AnalysisSessionError,
    DataSeriesSpec,
    TabularMappingSpec,
    open_analysis_project,
    source_spec_from_file,
)
from catalysis_workbench.workspace import create_workspace, open_workspace


def _source(tmp_path: Path, name: str, offset: int = 0) -> Path:
    path = tmp_path / name
    path.write_text(
        "Potential,Current\n"
        f"0,{1 + offset}\n"
        f"1,{2 + offset}\n",
        encoding="utf-8",
    )
    return path


def _spec(path: Path, name: str, *, y_unit: str = "mA") -> DataSeriesSpec:
    return DataSeriesSpec(
        source=source_spec_from_file(path),
        mapping=TabularMappingSpec(
            delimiter=",",
            x_column=0,
            y_column=1,
            x_role="potential",
            y_role="current",
            x_unit="V",
            y_unit=y_unit,
            x_reference="RHE",
        ),
        display_name=name,
    )


def test_batch_add_is_one_document_revision_and_one_undo(tmp_path: Path) -> None:
    first_path = _source(tmp_path, "Pb1.csv")
    second_path = _source(tmp_path, "Pb2.csv", 2)
    first = _spec(first_path, "Pb₁-N/C")
    second = _spec(second_path, "Pb₂-N/C")
    session = AnalysisSession()
    session.new_analysis("lsv")

    added = session.add_data_series_batch(((first, first_path), (second, second_path)))

    assert added.revision == 2
    assert tuple(item.display_name for item in added.document.data_series) == (  # type: ignore[union-attr]
        "Pb₁-N/C",
        "Pb₂-N/C",
    )
    assert added.can_undo is True
    undone = session.undo()
    assert undone.document.data_series == ()  # type: ignore[union-attr]
    assert undone.can_redo is True


def test_duplicate_input_rejected_but_rename_preserves_scientific_identity(tmp_path: Path) -> None:
    path = _source(tmp_path, "Pb3.csv")
    spec = _spec(path, "Pb₃-N/C")
    session = AnalysisSession()
    session.new_analysis("lsv")
    session.add_data_series(spec, path)

    with pytest.raises(AnalysisSessionError, match="already present"):
        session.add_data_series(spec, path)

    renamed = session.rename_data_series(spec.data_id, "Pb3 display")
    renamed_spec = renamed.document.data_series[0]  # type: ignore[union-attr]
    assert renamed_spec.data_id == spec.data_id
    assert renamed_spec.input_sha256 == spec.input_sha256


def test_edit_mapping_changes_identity_without_readding_raw_source(tmp_path: Path) -> None:
    path = _source(tmp_path, "Pb3.csv")
    spec = _spec(path, "Pb₃-N/C")
    session = AnalysisSession()
    session.new_analysis("lsv")
    session.add_data_series(spec, path)

    state = session.replace_data_mapping(
        spec.data_id,
        TabularMappingSpec(
            delimiter=",",
            x_column=0,
            y_column=1,
            x_role="potential",
            y_role="current",
            x_unit="V",
            y_unit="A",
            x_reference="RHE",
        ),
    )

    changed = state.document.data_series[0]  # type: ignore[union-attr]
    assert changed.source.content_sha256 == spec.source.content_sha256
    assert changed.data_id != spec.data_id
    assert session.materialize_data(changed.data_id).value.y_axis.unit == "A"


def test_first_save_copies_raw_then_external_source_can_be_deleted(tmp_path: Path) -> None:
    path = _source(tmp_path, "Pb₃ 数据.csv")
    spec = _spec(path, "Pb₃-N/C")
    root = tmp_path / "project"
    session = AnalysisSession()
    session.new_analysis("lsv")
    session.add_data_series(spec, path)

    saved = session.save_project_as(root)

    assert saved.is_dirty is False
    assert saved.project_root == root.resolve()
    raw = root / spec.source.workspace_destination
    assert raw.read_bytes() == path.read_bytes()
    path.unlink()
    materialized = session.materialize_data(spec.data_id)
    assert materialized.input_sha256 == spec.input_sha256
    assert tuple(materialized.value.y) == (1.0, 2.0)


def test_changed_source_before_first_save_fails_without_final_project(tmp_path: Path) -> None:
    path = _source(tmp_path, "Pb3.csv")
    spec = _spec(path, "Pb₃-N/C")
    root = tmp_path / "project"
    session = AnalysisSession()
    session.new_analysis("lsv")
    session.add_data_series(spec, path)
    path.write_text("Potential,Current\n0,999\n", encoding="utf-8")

    with pytest.raises(AnalysisProjectError, match="changed since mapping"):
        session.save_project_as(root)

    assert not root.exists()


def test_moved_project_reopens_and_raw_tampering_fails_closed(tmp_path: Path) -> None:
    source = _source(tmp_path, "Pb3.csv")
    spec = _spec(source, "Pb₃-N/C")
    root = tmp_path / "project"
    first = AnalysisSession()
    first.new_analysis("lsv")
    first.add_data_series(spec, source)
    first.save_project_as(root)
    first.close_analysis()

    moved = tmp_path / "moved-project"
    shutil.move(str(root), str(moved))
    session = AnalysisSession()
    reopened = session.open_project(moved)
    assert reopened.document.data_series[0].data_id == spec.data_id  # type: ignore[union-attr]
    assert session.materialize_data(spec.data_id).input_sha256 == spec.input_sha256

    raw = moved / spec.source.workspace_destination
    raw.write_text("tampered", encoding="utf-8")
    with pytest.raises(AnalysisSessionError, match="digest does not match"):
        session.materialize_data(spec.data_id)


def test_schema1_project_open_migrates_in_memory_without_rewriting_disk(tmp_path: Path) -> None:
    root = tmp_path / "project"
    create_workspace(root)
    payload = (
        b'{"document":{"schema_version":1,"task_id":"lsv","title":"Legacy Block 1"},'
        b'"schema_version":1}\n'
    )
    project_path = root / "project.json"
    project_path.write_bytes(payload)
    workspace_sha = open_workspace(root).manifest_sha256

    snapshot = open_analysis_project(root)

    assert project_path.read_bytes() == payload
    assert snapshot.project_file_sha256 == hashlib.sha256(payload).hexdigest()
    assert snapshot.document.schema_version == 2
    assert snapshot.document.data_series == ()
    session = AnalysisSession()
    state = session.open_project(root)
    assert state.is_dirty is False
    saved = session.save_project()
    assert saved.is_dirty is False
    assert open_workspace(root).manifest_sha256 == workspace_sha
    assert b'"schema_version":2' in project_path.read_bytes()
