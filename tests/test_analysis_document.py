from __future__ import annotations

import subprocess
import sys
from dataclasses import FrozenInstanceError

import pytest

from catalysis_workbench.application import (
    AnalysisDocument,
    AnalysisDocumentError,
    DataSeriesSpec,
    TabularMappingSpec,
    analysis_task_catalog,
    get_analysis_task_descriptor,
    source_spec_from_file,
)


def test_application_analysis_import_is_headless() -> None:
    code = """
import sys
import catalysis_workbench.application
assert "matplotlib.pyplot" not in sys.modules
assert "PySide6" not in sys.modules
assert "PyQt6" not in sys.modules
"""
    subprocess.run([sys.executable, "-c", code], check=True)


def test_analysis_task_catalog_is_exact_closed_set_and_ordered() -> None:
    tasks = analysis_task_catalog()
    assert tuple(task.task_id for task in tasks) == (
        "lsv",
        "fe_partial_current",
        "generic_xy",
    )
    assert get_analysis_task_descriptor("lsv") is tasks[0]
    with pytest.raises(ValueError, match="unknown analysis task_id"):
        get_analysis_task_descriptor("xrd")


def test_analysis_document_is_immutable_deterministic_and_normalizes_v1() -> None:
    first = AnalysisDocument(schema_version=1, task_id="lsv", title="Pb₃-N/C LSV")
    second = AnalysisDocument(schema_version=2, task_id="lsv", title="Pb₃-N/C LSV")
    changed = AnalysisDocument(schema_version=1, task_id="lsv", title="Pb₂-N/C LSV")

    assert first.schema_version == 2
    assert first == second
    assert first.document_sha256 == second.document_sha256
    assert changed.document_sha256 != first.document_sha256
    with pytest.raises(FrozenInstanceError):
        first.title = "mutated"  # type: ignore[misc]


def test_analysis_document_data_series_is_ordered_and_changes_document_identity(tmp_path) -> None:
    source = tmp_path / "data.csv"
    source.write_text("Potential,Current\n0,1\n1,2\n", encoding="utf-8")
    source_spec = source_spec_from_file(source)
    first_series = DataSeriesSpec(
        source=source_spec,
        mapping=TabularMappingSpec(
            delimiter=",",
            x_column=0,
            y_column=1,
            x_role="potential",
            y_role="current",
        ),
        display_name="Pb₃-N/C",
    )
    document = AnalysisDocument(
        schema_version=2,
        task_id="lsv",
        title="LSV",
        data_series=(first_series,),
    )
    empty = AnalysisDocument(schema_version=2, task_id="lsv", title="LSV")

    assert document.data_series == (first_series,)
    assert document.document_sha256 != empty.document_sha256
    with pytest.raises(AnalysisDocumentError, match="duplicate scientific inputs"):
        AnalysisDocument(
            schema_version=2,
            task_id="lsv",
            title="LSV",
            data_series=(first_series, first_series),
        )


def test_analysis_document_rejects_invalid_schema_task_and_title() -> None:
    with pytest.raises(AnalysisDocumentError, match="schema_version"):
        AnalysisDocument(schema_version=3, task_id="lsv", title="LSV")
    with pytest.raises(AnalysisDocumentError, match="unknown analysis task_id"):
        AnalysisDocument(schema_version=2, task_id="unknown", title="LSV")
    with pytest.raises(AnalysisDocumentError, match="non-empty"):
        AnalysisDocument(schema_version=2, task_id="lsv", title="")
    with pytest.raises(AnalysisDocumentError, match="surrounding whitespace"):
        AnalysisDocument(schema_version=2, task_id="lsv", title=" LSV ")
