"""GUI-neutral v1.1 analysis document/session lifecycle."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from catalysis_workbench.workspace.assets import verify_copy_asset
from catalysis_workbench.workspace.manifest import WorkspaceError

from .data import DataSeriesSpec, TabularMappingSpec
from .document import AnalysisDocument
from .evaluator import AnalysisEvaluation, AnalysisEvaluator
from .materialization import (
    AnalysisMaterializationError,
    MaterializedInput,
    materialize_data_series,
    verify_source_bytes,
)
from .persistence import create_analysis_project, open_analysis_project, save_analysis_project
from .processing import (
    AnalysisDependencyImpact,
    AnalysisSpec,
    dependency_impact,
    remap_analysis_data_id,
    remove_analysis_data_id,
    validate_analysis_spec,
)
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


_UNSET = object()


class AnalysisSession:
    """Own deterministic document history and transient unsaved source locations."""

    _HISTORY_LIMIT = 100
    _RAW_ASSET_TYPE = "analysis_raw_tabular"

    def __init__(self) -> None:
        self._state = AnalysisSessionState()
        self._undo: list[AnalysisDocument] = []
        self._redo: list[AnalysisDocument] = []
        self._source_locations: dict[str, Path] = {}

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

    def _replace_document(self, candidate: AnalysisDocument) -> AnalysisSessionState:
        current = self._state.document
        if current is None:
            raise AnalysisSessionError("no analysis document is open")
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

    def _document_with(
        self,
        *,
        title: str | None = None,
        data_series: Sequence[DataSeriesSpec] | None = None,
        analysis: AnalysisSpec | object = _UNSET,
    ) -> AnalysisDocument:
        current = self._state.document
        if current is None:
            raise AnalysisSessionError("no analysis document is open")
        candidate_analysis = current.analysis if analysis is _UNSET else analysis
        return AnalysisDocument(
            schema_version=3,
            task_id=current.task_id,
            title=current.title if title is None else title,
            data_series=current.data_series if data_series is None else data_series,
            analysis=candidate_analysis,  # type: ignore[arg-type]
        )

    def _series_index(self, data_id: str) -> int:
        current = self._state.document
        if current is None:
            raise AnalysisSessionError("no analysis document is open")
        for index, item in enumerate(current.data_series):
            if item.data_id == data_id:
                return index
        raise AnalysisSessionError(f"unknown analysis data_id: {data_id!r}")

    def new_analysis(self, task_id: str) -> AnalysisSessionState:
        """Start one clean untitled in-memory analysis without creating a directory."""

        self._refuse_dirty_replacement()
        task = get_analysis_task_descriptor(task_id)
        document = AnalysisDocument(
            schema_version=3,
            task_id=task.task_id,
            title=task.default_title,
            data_series=(),
        )
        self._reset_history()
        self._source_locations.clear()
        self._state = AnalysisSessionState(
            document=document,
            baseline_document_sha256=document.document_sha256,
            revision=self._state.revision + 1,
        )
        return self._state

    def rename_analysis(self, title: str) -> AnalysisSessionState:
        """Replace only the title and record one undoable semantic document revision."""

        return self._replace_document(self._document_with(title=title))

    def replace_analysis_spec(self, analysis: AnalysisSpec) -> AnalysisSessionState:
        """Commit one already-valid task-specific processing state as one undo revision."""

        current = self._state.document
        if current is None:
            raise AnalysisSessionError("no analysis document is open")
        try:
            checked = validate_analysis_spec(current.task_id, analysis)
        except (TypeError, ValueError) as exc:
            raise AnalysisSessionError(str(exc)) from exc
        return self._replace_document(self._document_with(analysis=checked))

    def add_data_series_batch(
        self,
        items: Sequence[tuple[DataSeriesSpec, str | Path]],
    ) -> AnalysisSessionState:
        """Validate and add several mapped inputs as exactly one undoable revision."""

        current = self._state.document
        if current is None:
            raise AnalysisSessionError("no analysis document is open")
        if isinstance(items, (str, bytes)) or not isinstance(items, Sequence):
            raise TypeError("items must be an ordered sequence")
        entries = tuple(items)
        if not entries:
            return self._state
        if not all(
            isinstance(entry, tuple)
            and len(entry) == 2
            and isinstance(entry[0], DataSeriesSpec)
            for entry in entries
        ):
            raise TypeError("items must contain (DataSeriesSpec, source_path) pairs")

        existing_ids = {item.data_id for item in current.data_series}
        new_ids: set[str] = set()
        staged_locations: dict[str, Path] = {}
        specs: list[DataSeriesSpec] = []
        for spec, raw_path in entries:
            if spec.data_id in existing_ids or spec.data_id in new_ids:
                raise AnalysisSessionError(
                    f"scientific input is already present: {spec.data_id}"
                )
            try:
                source = verify_source_bytes(spec, raw_path)
            except (AnalysisMaterializationError, OSError, ValueError) as exc:
                raise AnalysisSessionError(str(exc)) from exc
            source_sha = spec.source.content_sha256
            location = source.absolute()
            existing_location = staged_locations.get(source_sha)
            if existing_location is not None and existing_location != location:
                try:
                    verify_source_bytes(spec, existing_location)
                except (AnalysisMaterializationError, OSError, ValueError) as exc:
                    raise AnalysisSessionError(str(exc)) from exc
            staged_locations.setdefault(source_sha, location)
            new_ids.add(spec.data_id)
            specs.append(spec)

        candidate = self._document_with(data_series=(*current.data_series, *specs))
        state = self._replace_document(candidate)
        self._source_locations.update(staged_locations)
        return state

    def add_data_series(
        self,
        spec: DataSeriesSpec,
        source_path: str | Path,
    ) -> AnalysisSessionState:
        return self.add_data_series_batch(((spec, source_path),))

    def analysis_dependency_impact(self, data_id: str) -> AnalysisDependencyImpact:
        """Return processing references that a data removal would remove atomically."""

        current = self._state.document
        if current is None or current.analysis is None:
            raise AnalysisSessionError("no analysis document is open")
        self._series_index(data_id)
        return dependency_impact(current.analysis, data_id)

    def remove_data_series(self, data_id: str) -> AnalysisSessionState:
        current = self._state.document
        if current is None or current.analysis is None:
            raise AnalysisSessionError("no analysis document is open")
        index = self._series_index(data_id)
        updated = (*current.data_series[:index], *current.data_series[index + 1 :])
        analysis = remove_analysis_data_id(current.analysis, data_id)
        return self._replace_document(
            self._document_with(data_series=updated, analysis=analysis)
        )

    def rename_data_series(self, data_id: str, display_name: str) -> AnalysisSessionState:
        current = self._state.document
        if current is None:
            raise AnalysisSessionError("no analysis document is open")
        index = self._series_index(data_id)
        previous = current.data_series[index]
        replacement = DataSeriesSpec(
            source=previous.source,
            mapping=previous.mapping,
            display_name=display_name,
        )
        updated = list(current.data_series)
        updated[index] = replacement
        return self._replace_document(self._document_with(data_series=updated))

    def replace_data_mapping(
        self,
        data_id: str,
        mapping: TabularMappingSpec,
    ) -> AnalysisSessionState:
        if not isinstance(mapping, TabularMappingSpec):
            raise TypeError("mapping must be a TabularMappingSpec")
        current = self._state.document
        if current is None or current.analysis is None:
            raise AnalysisSessionError("no analysis document is open")
        index = self._series_index(data_id)
        previous = current.data_series[index]
        replacement = DataSeriesSpec(
            source=previous.source,
            mapping=mapping,
            display_name=previous.display_name,
        )
        if any(
            item.data_id == replacement.data_id and offset != index
            for offset, item in enumerate(current.data_series)
        ):
            raise AnalysisSessionError(
                f"scientific input is already present: {replacement.data_id}"
            )
        updated = list(current.data_series)
        updated[index] = replacement
        try:
            analysis = remap_analysis_data_id(
                current.analysis,
                data_id,
                replacement.data_id,
            )
        except (TypeError, ValueError) as exc:
            raise AnalysisSessionError(str(exc)) from exc
        return self._replace_document(
            self._document_with(data_series=updated, analysis=analysis)
        )

    def move_data_series(self, data_id: str, new_index: int) -> AnalysisSessionState:
        current = self._state.document
        if current is None:
            raise AnalysisSessionError("no analysis document is open")
        if type(new_index) is not int or new_index < 0 or new_index >= len(current.data_series):
            raise AnalysisSessionError("new data-series index is out of range")
        old_index = self._series_index(data_id)
        if old_index == new_index:
            return self._state
        updated = list(current.data_series)
        item = updated.pop(old_index)
        updated.insert(new_index, item)
        return self._replace_document(self._document_with(data_series=updated))

    def data_source_path(self, data_id: str) -> Path:
        """Return the verified raw path behind one mapped input.

        Unsaved analyses resolve the transient original source. Saved analyses
        resolve the workspace-owned copy. Exact bytes are reverified before the
        path is returned so desktop mapping editors fail closed on mutation.
        """

        current = self._state.document
        if current is None:
            raise AnalysisSessionError("no analysis document is open")
        spec = current.data_series[self._series_index(data_id)]
        if self._state.project_root is None:
            path = self._source_locations.get(spec.source.content_sha256)
            if path is None:
                raise AnalysisSessionError(
                    "raw source is no longer available in this unsaved analysis; re-add it"
                )
        else:
            try:
                _, path = verify_copy_asset(
                    self._state.project_root,
                    spec.source.workspace_asset_id,
                    expected_type=self._RAW_ASSET_TYPE,
                )
            except (WorkspaceError, OSError) as exc:
                raise AnalysisSessionError(str(exc)) from exc
        try:
            return verify_source_bytes(spec, path)
        except (AnalysisMaterializationError, OSError, ValueError) as exc:
            raise AnalysisSessionError(str(exc)) from exc

    def materialize_data(self, data_id: str) -> MaterializedInput:
        """Materialize from transient unsaved bytes or a verified workspace-owned copy."""

        current = self._state.document
        if current is None:
            raise AnalysisSessionError("no analysis document is open")
        spec = current.data_series[self._series_index(data_id)]
        path = self.data_source_path(data_id)
        try:
            return materialize_data_series(spec, path)
        except (AnalysisMaterializationError, OSError) as exc:
            raise AnalysisSessionError(str(exc)) from exc

    def evaluate_analysis(self) -> AnalysisEvaluation:
        """Evaluate the current committed scientific document without mutating session state."""

        current = self._state.document
        if current is None:
            raise AnalysisSessionError("no analysis document is open")
        return AnalysisEvaluator().evaluate(current, self.materialize_data)

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
        self._source_locations.clear()
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
        """Persist the current document and any missing raw copies to the existing root."""

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
            source_locations=self._source_locations,
        )
        self._source_locations.clear()
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
        snapshot = create_analysis_project(
            state.document,
            root,
            source_locations=self._source_locations,
        )
        self._source_locations.clear()
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
        self._source_locations.clear()
        self._state = AnalysisSessionState(revision=revision)
        return self._state


__all__ = ["AnalysisSession", "AnalysisSessionError", "AnalysisSessionState"]
