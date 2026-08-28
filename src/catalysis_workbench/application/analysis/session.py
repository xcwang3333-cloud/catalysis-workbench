"""GUI-neutral v1.1 analysis document/session lifecycle."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from .document import AnalysisDocument
from .persistence import create_analysis_project, open_analysis_project, save_analysis_project
from .tasks import get_analysis_task_descriptor


class AnalysisSessionError(RuntimeError):
    """Raised when an analysis-session transition would be unsafe or ambiguous."""


@dataclass(frozen=True, slots=True)
class AnalysisSessionState:
    """Immutable revisioned state for one Home/Analysis desktop document."""

    document: AnalysisDocument | None = None
    project_root: Path | None = None
    workspace_manifest_sha256: str | None = None
    project_file_sha256: str | None = None
    baseline_document_sha256: str | None = None
    revision: int = 0
    can_undo: bool = False
    can_redo: bool = False

    @property
    def is_unsaved(self) -> bool:
        return self.document is not None and self.project_root is None

    @property
    def is_dirty(self) -> bool:
        if self.document is None:
            return False
        return self.document.document_sha256 != self.baseline_document_sha256


class AnalysisSession:
    """Own deterministic document history separately from v1.0 workspace sessions."""

    _HISTORY_LIMIT = 100

    def __init__(self) -> None:
        self._state = AnalysisSessionState()
        self._undo: list[AnalysisDocument] = []
        self._redo: list[AnalysisDocument] = []

    @property
    def state(self) -> AnalysisSessionState:
        return self._state

    def _refuse_dirty_replacement(self) -> None:
        if self._state.is_dirty:
            raise AnalysisSessionError("save or explicitly discard analysis changes first")

    def _reset_history(self) -> None:
        self._undo.clear()
        self._redo.clear()

    def _with_history_flags(self, state: AnalysisSessionState) -> AnalysisSessionState:
        return replace(state, can_undo=bool(self._undo), can_redo=bool(self._redo))

    def new_analysis(self, task_id: str) -> AnalysisSessionState:
        """Start one clean untitled in-memory analysis without creating a directory."""

        self._refuse_dirty_replacement()
        task = get_analysis_task_descriptor(task_id)
        document = AnalysisDocument(
            schema_version=1,
            task_id=task.task_id,
            title=task.default_title,
        )
        self._reset_history()
        self._state = AnalysisSessionState(
            document=document,
            baseline_document_sha256=document.document_sha256,
            revision=self._state.revision + 1,
        )
        return self._state

    def rename_analysis(self, title: str) -> AnalysisSessionState:
        """Replace only the title and record one undoable semantic document revision."""

        current = self._state.document
        if current is None:
            raise AnalysisSessionError("no analysis document is open")
        candidate = AnalysisDocument(
            schema_version=current.schema_version,
            task_id=current.task_id,
            title=title,
        )
        if candidate == current:
            return self._state
        self._undo.append(current)
        if len(self._undo) > self._HISTORY_LIMIT:
            del self._undo[0]
        self._redo.clear()
        self._state = self._with_history_flags(
            replace(self._state, document=candidate, revision=self._state.revision + 1)
        )
        return self._state

    def undo(self) -> AnalysisSessionState:
        """Restore the previous semantic document without affecting file-system history."""

        current = self._state.document
        if current is None or not self._undo:
            return self._state
        previous = self._undo.pop()
        self._redo.append(current)
        self._state = self._with_history_flags(
            replace(self._state, document=previous, revision=self._state.revision + 1)
        )
        return self._state

    def redo(self) -> AnalysisSessionState:
        """Reapply the most recently undone semantic document revision."""

        current = self._state.document
        if current is None or not self._redo:
            return self._state
        following = self._redo.pop()
        self._undo.append(current)
        self._state = self._with_history_flags(
            replace(self._state, document=following, revision=self._state.revision + 1)
        )
        return self._state

    def open_project(self, root: str | Path) -> AnalysisSessionState:
        """Open an exact v1.1 project without silently replacing dirty state."""

        self._refuse_dirty_replacement()
        snapshot = open_analysis_project(root)
        self._reset_history()
        self._state = AnalysisSessionState(
            document=snapshot.document,
            project_root=snapshot.root,
            workspace_manifest_sha256=snapshot.workspace_manifest_sha256,
            project_file_sha256=snapshot.project_file_sha256,
            baseline_document_sha256=snapshot.document.document_sha256,
            revision=self._state.revision + 1,
        )
        return self._state

    def save_project(self) -> AnalysisSessionState:
        """Persist the current document to its existing project root."""

        state = self._state
        if state.document is None:
            raise AnalysisSessionError("no analysis document is open")
        if state.project_root is None:
            raise AnalysisSessionError("analysis has not been saved; use save_project_as")
        if state.workspace_manifest_sha256 is None or state.project_file_sha256 is None:
            raise AnalysisSessionError("saved analysis session is missing exact project identities")
        snapshot = save_analysis_project(
            state.document,
            state.project_root,
            expected_project_file_sha256=state.project_file_sha256,
            expected_workspace_manifest_sha256=state.workspace_manifest_sha256,
        )
        self._state = self._with_history_flags(
            replace(
                state,
                project_root=snapshot.root,
                workspace_manifest_sha256=snapshot.workspace_manifest_sha256,
                project_file_sha256=snapshot.project_file_sha256,
                baseline_document_sha256=state.document.document_sha256,
                revision=state.revision + 1,
            )
        )
        return self._state

    def save_project_as(self, root: str | Path) -> AnalysisSessionState:
        """Create a new project root and bind the current in-memory document to it."""

        state = self._state
        if state.document is None:
            raise AnalysisSessionError("no analysis document is open")
        snapshot = create_analysis_project(state.document, root)
        self._state = self._with_history_flags(
            replace(
                state,
                project_root=snapshot.root,
                workspace_manifest_sha256=snapshot.workspace_manifest_sha256,
                project_file_sha256=snapshot.project_file_sha256,
                baseline_document_sha256=state.document.document_sha256,
                revision=state.revision + 1,
            )
        )
        return self._state

    def close_analysis(self, *, discard_changes: bool = False) -> AnalysisSessionState:
        """Close the document, refusing dirty loss unless discard is explicit."""

        if type(discard_changes) is not bool:
            raise TypeError("discard_changes must be a bool")
        if self._state.is_dirty and not discard_changes:
            raise AnalysisSessionError("save or explicitly discard analysis changes first")
        revision = self._state.revision + 1
        self._reset_history()
        self._state = AnalysisSessionState(revision=revision)
        return self._state


__all__ = ["AnalysisSession", "AnalysisSessionError", "AnalysisSessionState"]
