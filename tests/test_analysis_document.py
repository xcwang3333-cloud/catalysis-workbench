from __future__ import annotations

import subprocess
import sys
from dataclasses import FrozenInstanceError

import pytest

from catalysis_workbench.application import (
    AnalysisDocument,
    AnalysisDocumentError,
    analysis_task_catalog,
    get_analysis_task_descriptor,
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


def test_analysis_document_is_immutable_and_deterministic() -> None:
    first = AnalysisDocument(schema_version=1, task_id="lsv", title="Pb₃-N/C LSV")
    second = AnalysisDocument(schema_version=1, task_id="lsv", title="Pb₃-N/C LSV")
    changed = AnalysisDocument(schema_version=1, task_id="lsv", title="Pb₂-N/C LSV")

    assert first == second
    assert first.document_sha256 == second.document_sha256
    assert changed.document_sha256 != first.document_sha256
    with pytest.raises(FrozenInstanceError):
        first.title = "mutated"  # type: ignore[misc]


def test_analysis_document_rejects_invalid_schema_task_and_title() -> None:
    with pytest.raises(AnalysisDocumentError, match="schema_version"):
        AnalysisDocument(schema_version=2, task_id="lsv", title="LSV")
    with pytest.raises(AnalysisDocumentError, match="unknown analysis task_id"):
        AnalysisDocument(schema_version=1, task_id="unknown", title="LSV")
    with pytest.raises(AnalysisDocumentError, match="non-empty"):
        AnalysisDocument(schema_version=1, task_id="lsv", title="")
    with pytest.raises(AnalysisDocumentError, match="surrounding whitespace"):
        AnalysisDocument(schema_version=1, task_id="lsv", title=" LSV ")
