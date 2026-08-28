from __future__ import annotations

from pathlib import Path

import pytest

from catalysis_workbench.application import AnalysisSession, AnalysisSessionError


def test_new_analysis_is_unsaved_but_clean_and_does_not_create_files(tmp_path: Path) -> None:
    session = AnalysisSession()
    before = tuple(tmp_path.iterdir())

    state = session.new_analysis("lsv")

    assert state.document is not None
    assert state.document.title == "Untitled LSV analysis"
    assert state.project_root is None
    assert state.is_unsaved is True
    assert state.is_dirty is False
    assert state.revision == 1
    assert tuple(tmp_path.iterdir()) == before


def test_invalid_new_task_does_not_mutate_state() -> None:
    session = AnalysisSession()
    before = session.state

    with pytest.raises(ValueError, match="unknown analysis task_id"):
        session.new_analysis("unknown")

    assert session.state is before


def test_rename_undo_redo_and_baseline_dirty_semantics() -> None:
    session = AnalysisSession()
    clean = session.new_analysis("lsv")
    baseline_sha = clean.document.document_sha256  # type: ignore[union-attr]

    edited = session.rename_analysis("Pb nuclearity CO₂RR")
    assert edited.is_dirty is True
    assert edited.can_undo is True
    assert edited.can_redo is False

    undone = session.undo()
    assert undone.document.document_sha256 == baseline_sha  # type: ignore[union-attr]
    assert undone.is_dirty is False
    assert undone.can_redo is True

    redone = session.redo()
    assert redone.document.title == "Pb nuclearity CO₂RR"  # type: ignore[union-attr]
    assert redone.is_dirty is True


def test_new_edit_after_undo_clears_redo() -> None:
    session = AnalysisSession()
    session.new_analysis("generic_xy")
    session.rename_analysis("A")
    session.undo()
    assert session.state.can_redo is True

    state = session.rename_analysis("B")

    assert state.can_redo is False
    assert state.document.title == "B"  # type: ignore[union-attr]


def test_save_preserves_undo_history_and_exact_baseline(tmp_path: Path) -> None:
    session = AnalysisSession()
    session.new_analysis("lsv")
    session.rename_analysis("Saved title")
    saved = session.save_project_as(tmp_path / "project")

    assert saved.is_dirty is False
    assert saved.can_undo is True
    assert saved.project_root == (tmp_path / "project").resolve()

    undone = session.undo()
    assert undone.is_dirty is True
    assert undone.document.title == "Untitled LSV analysis"  # type: ignore[union-attr]

    redone = session.redo()
    assert redone.is_dirty is False
    assert redone.document.title == "Saved title"  # type: ignore[union-attr]


def test_dirty_close_requires_explicit_discard_but_untouched_unsaved_does_not() -> None:
    session = AnalysisSession()
    session.new_analysis("lsv")
    closed = session.close_analysis()
    assert closed.document is None

    session.new_analysis("lsv")
    session.rename_analysis("Changed")
    dirty = session.state
    with pytest.raises(AnalysisSessionError, match="explicitly discard"):
        session.close_analysis()
    assert session.state is dirty
    discarded = session.close_analysis(discard_changes=True)
    assert discarded.document is None
