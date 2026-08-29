"""Task-first v1.1 desktop window and analysis-document lifecycle."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
)

from catalysis_workbench.application import (
    AnalysisDocument,
    AnalysisEvaluator,
    AnalysisResult,
    AnalysisSession,
    AnalysisSessionError,
    DataSeriesSpec,
    get_analysis_task_descriptor,
    open_analysis_project,
)

from .analysis_shell import AnalysisShellPage
from .data_intake import ImportDataDialog, SeriesPreviewDialog
from .home import HomePage, RecentProjectDisplay
from .recent_projects import RecentProjectsStore


class CatalysisWorkbenchWindow(QMainWindow):
    """Task-first Home and Analysis workbench for the v1.1 desktop."""

    def __init__(
        self,
        *,
        session: AnalysisSession | None = None,
        recent_store: RecentProjectsStore | None = None,
    ) -> None:
        super().__init__()
        if session is not None and not isinstance(session, AnalysisSession):
            raise TypeError("session must be an AnalysisSession or None")
        self.session = session or AnalysisSession()
        self.recent_store = recent_store or RecentProjectsStore()
        self._last_valid_result: AnalysisResult | None = None
        self._last_valid_task_id: str | None = None
        self._suppress_processing_draft_signal = False
        self.home_page = HomePage()
        self.analysis_page = AnalysisShellPage()
        self.stack = QStackedWidget()
        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.analysis_page)
        self.setCentralWidget(self.stack)
        self.setWindowTitle("CatalysisWorkbench")
        self.setMinimumSize(1200, 760)
        self.resize(1440, 900)
        self._connect_signals()
        self._build_menu()
        self.refresh_views()
        self.show_home()

    def _connect_signals(self) -> None:
        self.home_page.task_selected.connect(self._start_analysis_ui)
        self.home_page.open_project_requested.connect(self._open_project_interactive)
        self.home_page.recent_project_requested.connect(self._open_project_ui)
        self.home_page.recent_remove_requested.connect(self._remove_recent)
        self.analysis_page.home_requested.connect(self._request_home)
        self.analysis_page.title_changed.connect(self._rename_analysis_ui)
        self.analysis_page.save_requested.connect(self._save_interactive)
        self.analysis_page.undo_requested.connect(self._undo_ui)
        self.analysis_page.redo_requested.connect(self._redo_ui)
        self.analysis_page.add_files_requested.connect(self._add_files_interactive)
        self.analysis_page.files_dropped.connect(self._add_files_ui)
        self.analysis_page.edit_mapping_requested.connect(self._edit_mapping_ui)
        self.analysis_page.preview_data_requested.connect(self._preview_data_ui)
        self.analysis_page.remove_series_requested.connect(self._remove_series_ui)
        self.analysis_page.series_renamed.connect(self._rename_series_ui)
        self.analysis_page.series_moved.connect(self._move_series_ui)
        self.analysis_page.analysis_spec_changed.connect(self._replace_analysis_spec_ui)
        self.analysis_page.processing_panel.draft_state_changed.connect(
            self._processing_draft_state_changed
        )

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("File")
        open_action = QAction("Open Project…", self)
        open_action.triggered.connect(self._open_project_interactive)
        file_menu.addAction(open_action)
        save_action = QAction("Save Project", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._save_interactive)
        file_menu.addAction(save_action)
        add_data_action = QAction("Add Data Files…", self)
        add_data_action.setShortcut(QKeySequence("Ctrl+Shift+O"))
        add_data_action.triggered.connect(self._add_files_interactive)
        file_menu.addAction(add_data_action)
        home_action = QAction("Home", self)
        home_action.triggered.connect(self._request_home)
        file_menu.addAction(home_action)
        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = self.menuBar().addMenu("Edit")
        undo_action = QAction("Undo", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self._undo_ui)
        edit_menu.addAction(undo_action)
        redo_action = QAction("Redo", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self._redo_ui)
        edit_menu.addAction(redo_action)
        self._save_action = save_action
        self._add_data_action = add_data_action
        self._undo_action = undo_action
        self._redo_action = redo_action

    def _display_error(self, exc: BaseException) -> None:
        QMessageBox.critical(self, "CatalysisWorkbench", str(exc))

    def _clear_last_valid(self) -> None:
        self._last_valid_result = None
        self._last_valid_task_id = None

    def _commit_title_editor(self) -> bool:
        """Flush buffered title text before any save/navigation/close decision."""

        state = self.session.state
        if state.document is None:
            return True
        title = self.analysis_page.title_edit.text()
        if title == state.document.title:
            return True
        try:
            self.rename_analysis(title)
        except (ValueError, RuntimeError) as exc:
            self._display_error(exc)
            self.refresh_views()
            return False
        return True

    def _recent_displays(self) -> tuple[RecentProjectDisplay, ...]:
        result: list[RecentProjectDisplay] = []
        for entry in self.recent_store.entries():
            try:
                snapshot = open_analysis_project(entry.path)
                task = get_analysis_task_descriptor(snapshot.document.task_id)
            except (OSError, ValueError):
                result.append(
                    RecentProjectDisplay(
                        path=entry.path,
                        title="Unavailable",
                        task_name="",
                        available=False,
                    )
                )
                continue
            result.append(
                RecentProjectDisplay(
                    path=entry.path,
                    title=snapshot.document.title,
                    task_name=task.display_name,
                    available=True,
                )
            )
        return tuple(result)

    def refresh_views(self) -> None:
        state = self.session.state
        self._suppress_processing_draft_signal = True
        try:
            self.analysis_page.apply_state(state)
        finally:
            self._suppress_processing_draft_signal = False
        self.home_page.set_recent_projects(self._recent_displays())
        enabled = state.document is not None
        self._save_action.setEnabled(enabled)
        self._add_data_action.setEnabled(enabled)
        self._undo_action.setEnabled(state.can_undo)
        self._redo_action.setEnabled(state.can_redo)
        if state.document is None:
            self.setWindowTitle("CatalysisWorkbench")
        else:
            marker = " *" if state.is_dirty else ""
            self.setWindowTitle(f"{state.document.title}{marker} — CatalysisWorkbench")

    def _materialize_all_inputs(self) -> None:
        state = self.session.state
        if state.document is None or not state.document.data_series:
            self.analysis_page.set_materialized_inputs(())
            return
        try:
            inputs = tuple(
                self.session.materialize_data(spec.data_id)
                for spec in state.document.data_series
            )
        except (OSError, ValueError, RuntimeError) as exc:
            self.analysis_page.set_materialized_inputs((), warning=str(exc))
            return
        self.analysis_page.set_materialized_inputs(inputs)

    def _apply_evaluation(self, status: str, result: AnalysisResult | None, message: str | None) -> None:
        state = self.session.state
        task_id = state.document.task_id if state.document is not None else None
        if status == "success" and result is not None:
            self._last_valid_result = result
            self._last_valid_task_id = task_id
            self.analysis_page.set_live_analysis(
                result,
                status="success",
                message=None,
                stale=False,
            )
            return
        if status == "incomplete":
            self._clear_last_valid()
            self.analysis_page.set_live_analysis(
                None,
                status="incomplete",
                message=message,
                stale=False,
            )
            return
        if self._last_valid_result is not None and self._last_valid_task_id == task_id:
            self.analysis_page.set_live_analysis(
                self._last_valid_result,
                status="error",
                message=message,
                stale=True,
            )
            return
        self.analysis_page.set_live_analysis(
            None,
            status="error",
            message=message,
            stale=False,
        )

    def _refresh_live_analysis(self) -> None:
        state = self.session.state
        self._materialize_all_inputs()
        if state.document is None:
            self._clear_last_valid()
            self.analysis_page.set_live_analysis(
                None,
                status="incomplete",
                message="No analysis is open.",
            )
            return
        evaluation = self.session.evaluate_analysis()
        self._apply_evaluation(
            evaluation.status,
            evaluation.result,
            evaluation.message,
        )

    def _processing_draft_state_changed(self, invalid: bool, message: str) -> None:
        if self._suppress_processing_draft_signal:
            return
        if invalid:
            task_id = (
                self.session.state.document.task_id
                if self.session.state.document is not None
                else None
            )
            stale_result = (
                self._last_valid_result
                if self._last_valid_task_id == task_id
                else None
            )
            self.analysis_page.set_live_analysis(
                stale_result,
                status="error",
                message=message,
                stale=stale_result is not None,
            )
            return
        self._refresh_live_analysis()

    def show_home(self) -> None:
        self.refresh_views()
        self.stack.setCurrentWidget(self.home_page)

    def show_analysis(self) -> None:
        self.refresh_views()
        self._refresh_live_analysis()
        self.stack.setCurrentWidget(self.analysis_page)

    def start_analysis(self, task_id: str) -> None:
        self._clear_last_valid()
        self.session.new_analysis(task_id)
        self.show_analysis()

    def rename_analysis(self, title: str) -> None:
        self.session.rename_analysis(title)
        self.refresh_views()

    def add_data_items(
        self,
        items: tuple[tuple[DataSeriesSpec, Path], ...]
        | list[tuple[DataSeriesSpec, Path]],
    ) -> None:
        self._clear_last_valid()
        self.session.add_data_series_batch(items)
        self.refresh_views()
        self._refresh_live_analysis()

    def remove_data_series(self, data_id: str) -> None:
        self._clear_last_valid()
        self.session.remove_data_series(data_id)
        self.refresh_views()
        self._refresh_live_analysis()

    def save_project_path(self, root: str | Path | None = None) -> None:
        state = self.session.state
        if state.document is None:
            raise AnalysisSessionError("no analysis document is open")
        if root is None:
            self.session.save_project()
        elif state.project_root is None or Path(root).resolve(strict=False) != state.project_root:
            self.session.save_project_as(root)
        else:
            self.session.save_project()
        if self.session.state.project_root is not None:
            self.recent_store.add(self.session.state.project_root)
        self.refresh_views()

    def open_project_path(self, root: str | Path) -> None:
        self._clear_last_valid()
        self.session.open_project(root)
        if self.session.state.project_root is not None:
            self.recent_store.add(self.session.state.project_root)
        self.show_analysis()

    def go_home(self, *, discard_changes: bool = False) -> None:
        self.session.close_analysis(discard_changes=discard_changes)
        self._clear_last_valid()
        self.show_home()

    def _candidate_evaluation(self, analysis: object):
        state = self.session.state
        if state.document is None:
            raise AnalysisSessionError("no analysis document is open")
        document = state.document
        candidate = AnalysisDocument(
            schema_version=3,
            task_id=document.task_id,
            title=document.title,
            data_series=document.data_series,
            analysis=analysis,
        )
        return AnalysisEvaluator().evaluate(candidate, self.session.materialize_data)

    def _replace_analysis_spec_ui(self, analysis: object) -> None:
        try:
            evaluation = self._candidate_evaluation(analysis)
            if evaluation.status == "error":
                self.analysis_page.mark_processing_commit_error(
                    evaluation.message or "scientific processing failed"
                )
                return
            self.session.replace_analysis_spec(analysis)  # type: ignore[arg-type]
        except (OSError, TypeError, ValueError, RuntimeError) as exc:
            self.analysis_page.mark_processing_commit_error(str(exc))
            return
        self.refresh_views()
        self._refresh_live_analysis()

    def _start_analysis_ui(self, task_id: str) -> None:
        try:
            self.start_analysis(task_id)
        except (OSError, ValueError, RuntimeError) as exc:
            self._display_error(exc)

    def _rename_analysis_ui(self, title: str) -> None:
        try:
            self.rename_analysis(title)
        except (ValueError, RuntimeError) as exc:
            self._display_error(exc)
            self.refresh_views()

    def _undo_ui(self) -> None:
        self._clear_last_valid()
        self.session.undo()
        self.refresh_views()
        self._refresh_live_analysis()

    def _redo_ui(self) -> None:
        self._clear_last_valid()
        self.session.redo()
        self.refresh_views()
        self._refresh_live_analysis()

    def _prepare_processing_draft(self) -> bool:
        if not self.analysis_page.has_unapplied_processing_draft:
            return True
        box = QMessageBox(self)
        box.setWindowTitle("Discard unapplied settings?")
        box.setText(
            "Current processing fields are invalid and have not been applied. "
            "Discard these unapplied values?"
        )
        discard_button = box.addButton(QMessageBox.StandardButton.Discard)
        cancel_button = box.addButton(QMessageBox.StandardButton.Cancel)
        box.setDefaultButton(cancel_button)
        box.exec()
        if box.clickedButton() is not discard_button:
            return False
        self.analysis_page.discard_processing_draft()
        self._refresh_live_analysis()
        return True

    def _add_files_interactive(self) -> None:
        if self.session.state.document is None or not self._prepare_processing_draft():
            return
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Add Data Files",
            "",
            "Tabular data (*.csv *.txt *.tsv *.dat *.xlsx *.xlsm)",
        )
        if paths:
            self._add_files_ui(tuple(paths), draft_prepared=True)

    def _add_files_ui(self, paths: object, *, draft_prepared: bool = False) -> None:
        state = self.session.state
        if state.document is None:
            return
        if not draft_prepared and not self._prepare_processing_draft():
            return
        if not isinstance(paths, (tuple, list)) or not paths:
            return
        try:
            dialog = ImportDataDialog(
                tuple(str(path) for path in paths),
                task_id=state.document.task_id,
                parent=self,
            )
        except (OSError, ValueError, RuntimeError) as exc:
            self._display_error(exc)
            return
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.add_data_items(list(dialog.mapped_items()))
        except (OSError, ValueError, RuntimeError) as exc:
            self._display_error(exc)

    def _data_spec(self, data_id: str) -> DataSeriesSpec:
        document = self.session.state.document
        if document is None:
            raise AnalysisSessionError("no analysis document is open")
        for spec in document.data_series:
            if spec.data_id == data_id:
                return spec
        raise AnalysisSessionError(f"unknown analysis data_id: {data_id!r}")

    def _edit_mapping_ui(self, data_id: str) -> None:
        state = self.session.state
        if state.document is None or not self._prepare_processing_draft():
            return
        try:
            spec = self._data_spec(data_id)
            path = self.session.data_source_path(data_id)
            dialog = ImportDataDialog(
                (path,),
                task_id=state.document.task_id,
                existing_spec=spec,
                parent=self,
            )
        except (OSError, ValueError, RuntimeError) as exc:
            self._display_error(exc)
            return
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self._clear_last_valid()
            self.session.replace_data_mapping(data_id, dialog.edited_mapping())
            self.refresh_views()
            self._refresh_live_analysis()
        except (OSError, ValueError, RuntimeError) as exc:
            self._display_error(exc)

    def _preview_data_ui(self, data_id: str) -> None:
        try:
            materialized = self.session.materialize_data(data_id)
        except (OSError, ValueError, RuntimeError) as exc:
            self._display_error(exc)
            return
        dialog = SeriesPreviewDialog(materialized, parent=self)
        dialog.exec()

    def _remove_series_ui(self, data_id: str) -> None:
        if not self._prepare_processing_draft():
            return
        spec = self._data_spec(data_id)
        impact = self.session.analysis_dependency_impact(data_id)
        impact_lines: list[str] = []
        if impact.partial_current_pair_count:
            impact_lines.append(
                f"• remove {impact.partial_current_pair_count} explicit partial-current pair(s)"
            )
        if impact.override_count:
            impact_lines.append(
                f"• remove {impact.override_count} selected-series processing override(s)"
            )
        impact_text = ""
        if impact_lines:
            impact_text = "\n\nThis also will:\n" + "\n".join(impact_lines)
        answer = QMessageBox.question(
            self,
            "Remove data?",
            f"Remove {spec.display_name!r} from this analysis?"
            f"{impact_text}\n\nThe original raw file is not modified.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.remove_data_series(data_id)
        except (OSError, ValueError, RuntimeError) as exc:
            self._display_error(exc)

    def _rename_series_ui(self, data_id: str, name: str) -> None:
        if not self._prepare_processing_draft():
            self.refresh_views()
            return
        try:
            self.session.rename_data_series(data_id, name)
            self.refresh_views()
            self._refresh_live_analysis()
        except (OSError, ValueError, RuntimeError) as exc:
            self._display_error(exc)
            self.refresh_views()

    def _move_series_ui(self, data_id: str, new_index: int) -> None:
        if not self._prepare_processing_draft():
            self.refresh_views()
            return
        try:
            self.session.move_data_series(data_id, new_index)
            self.refresh_views()
            self._refresh_live_analysis()
        except (OSError, ValueError, RuntimeError) as exc:
            self._display_error(exc)
            self.refresh_views()

    @staticmethod
    def _valid_directory_name(name: str) -> bool:
        return (
            bool(name)
            and name not in {".", ".."}
            and "/" not in name
            and "\\" not in name
        )

    def _save_interactive(self) -> bool:
        if not self._prepare_processing_draft() or not self._commit_title_editor():
            return False
        state = self.session.state
        if state.document is None:
            return False
        try:
            if state.project_root is not None:
                self.save_project_path()
                return True
            parent = QFileDialog.getExistingDirectory(
                self, "Choose Project Parent Directory"
            )
            if not parent:
                return False
            name, accepted = QInputDialog.getText(
                self, "Save Project", "Project directory name:"
            )
            if not accepted:
                return False
            name = name.strip()
            if not self._valid_directory_name(name):
                raise ValueError("project directory name must be one path component")
            self.save_project_path(Path(parent) / name)
            return True
        except (OSError, ValueError, RuntimeError) as exc:
            self._display_error(exc)
            return False

    def _dirty_decision(self) -> str:
        if not self.session.state.is_dirty:
            return "continue"
        box = QMessageBox(self)
        box.setWindowTitle("Save changes?")
        box.setText("Save changes to the current analysis?")
        save_button = box.addButton(QMessageBox.StandardButton.Save)
        discard_button = box.addButton(QMessageBox.StandardButton.Discard)
        cancel_button = box.addButton(QMessageBox.StandardButton.Cancel)
        box.setDefaultButton(save_button)
        box.exec()
        clicked = box.clickedButton()
        if clicked is save_button:
            return "save"
        if clicked is discard_button:
            return "discard"
        if clicked is cancel_button:
            return "cancel"
        return "cancel"

    def _prepare_transition(self) -> bool:
        if not self._prepare_processing_draft() or not self._commit_title_editor():
            return False
        decision = self._dirty_decision()
        if decision == "cancel":
            return False
        if decision == "save":
            return self._save_interactive()
        if decision == "discard":
            self.session.close_analysis(discard_changes=True)
            self._clear_last_valid()
        return True

    def _request_home(self) -> None:
        if not self._prepare_transition():
            return
        if self.session.state.document is not None:
            self.session.close_analysis()
            self._clear_last_valid()
        self.show_home()

    def _open_project_ui(self, root: str) -> None:
        if not self._prepare_transition():
            return
        try:
            self.open_project_path(root)
        except (OSError, ValueError, RuntimeError) as exc:
            self._display_error(exc)

    def _open_project_interactive(self) -> None:
        if not self._prepare_transition():
            return
        root = QFileDialog.getExistingDirectory(self, "Open CatalysisWorkbench Project")
        if not root:
            return
        try:
            self.open_project_path(root)
        except (OSError, ValueError, RuntimeError) as exc:
            self._display_error(exc)

    def _remove_recent(self, root: str) -> None:
        self.recent_store.remove(root)
        self.refresh_views()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt override
        if not self._prepare_processing_draft() or not self._commit_title_editor():
            event.ignore()
            return
        if not self.session.state.is_dirty:
            event.accept()
            return
        decision = self._dirty_decision()
        if decision == "cancel":
            event.ignore()
            return
        if decision == "save" and not self._save_interactive():
            event.ignore()
            return
        event.accept()


__all__ = ["CatalysisWorkbenchWindow"]
