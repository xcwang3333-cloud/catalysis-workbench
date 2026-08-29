"""v1.1 desktop window extension that adds the Figure Workbench stage."""

from __future__ import annotations

from catalysis_workbench.application import (
    AnalysisResult,
    AnalysisSession,
    AnalysisSessionError,
    FigureDraft,
    allowed_figure_view_ids,
    create_figure_draft,
    figure_draft_is_stale,
    figure_source_view,
)

from .figure_workbench import FigureWorkbenchPage
from .recent_projects import RecentProjectsStore
from .workbench_window import CatalysisWorkbenchWindow as _AnalysisWorkbenchWindow


class CatalysisWorkbenchWindow(_AnalysisWorkbenchWindow):
    """Task-first Home → Analysis → Figure desktop shell for v1.1 Block 4."""

    def __init__(
        self,
        *,
        session: AnalysisSession | None = None,
        recent_store: RecentProjectsStore | None = None,
    ) -> None:
        super().__init__(session=session, recent_store=recent_store)
        self.figure_page = FigureWorkbenchPage()
        self.stack.addWidget(self.figure_page)
        self.analysis_page.continue_button.clicked.connect(self._show_figure_ui)
        self.analysis_page.continue_button.setToolTip(
            "Open Figure Workbench using the current successful scientific result."
        )
        self.figure_page.back_requested.connect(self.show_analysis)
        self.figure_page.save_requested.connect(self._save_interactive)
        self.figure_page.undo_requested.connect(self._undo_ui)
        self.figure_page.redo_requested.connect(self._redo_ui)
        self.figure_page.view_selected.connect(self._figure_view_selected)
        self.figure_page.create_requested.connect(self._create_figure_ui)
        self.figure_page.refresh_requested.connect(self._refresh_figure_ui)
        self.figure_page.reset_requested.connect(self._reset_figure_ui)
        self.figure_page.figure_spec_changed.connect(self._replace_figure_spec_ui)
        self.figure_page.trace_moved.connect(self._move_figure_trace_ui)
        self.analysis_page.continue_button.setEnabled(False)

    def _apply_evaluation(
        self,
        status: str,
        result: AnalysisResult | None,
        message: str | None,
    ) -> None:
        super()._apply_evaluation(status, result, message)
        if hasattr(self, "figure_page"):
            self.analysis_page.continue_button.setEnabled(
                status == "success" and result is not None
            )

    def _processing_draft_state_changed(self, invalid: bool, message: str) -> None:
        super()._processing_draft_state_changed(invalid, message)
        if invalid:
            self.analysis_page.continue_button.setEnabled(False)

    def _current_result(self) -> AnalysisResult:
        evaluation = self.session.evaluate_analysis()
        if evaluation.status != "success" or evaluation.result is None:
            raise AnalysisSessionError(
                evaluation.message
                or "analysis must be successful before opening Figure Workbench"
            )
        return evaluation.result

    @staticmethod
    def _draft_for_view(
        figures: tuple[FigureDraft, ...] | list[FigureDraft] | object,
        view_id: str,
    ) -> FigureDraft | None:
        try:
            values = tuple(figures)  # type: ignore[arg-type]
        except TypeError:
            return None
        return next((item for item in values if item.view_id == view_id), None)

    def _available_figure_views(
        self,
        result: AnalysisResult,
    ) -> tuple[tuple[str, str], ...]:
        document = self.session.state.document
        if document is None:
            return ()
        allowed = set(allowed_figure_view_ids(document.task_id))
        return tuple(
            (view.view_id, view.label)
            for view in result.views
            if view.view_id in allowed
        )

    def _initial_figure_view(
        self,
        available: tuple[tuple[str, str], ...],
        requested: str | None,
    ) -> str:
        ids = tuple(view_id for view_id, _label in available)
        if not ids:
            raise AnalysisSessionError(
                "successful analysis has no Figure Workbench result view"
            )
        if requested in ids:
            return requested  # type: ignore[return-value]
        current_analysis_view = self.analysis_page.view_combo.currentData()
        if isinstance(current_analysis_view, str) and current_analysis_view in ids:
            return current_analysis_view
        return ids[0]

    def _refresh_figure_workbench(self, view_id: str | None = None) -> None:
        state = self.session.state
        document = state.document
        if document is None:
            self.figure_page.set_preview_message("No analysis is open.")
            return
        try:
            result = self._current_result()
            available = self._available_figure_views(result)
            active = self._initial_figure_view(
                available,
                view_id or self.figure_page.active_view_id,
            )
            source = figure_source_view(document, result, active)
            draft = self._draft_for_view(document.figures, active)
            stale = (
                False
                if draft is None
                else figure_draft_is_stale(draft, document, result)
            )
        except (OSError, TypeError, ValueError, RuntimeError) as exc:
            self.figure_page.set_preview_message(str(exc))
            return

        self.figure_page.apply_state(
            available_views=available,
            active_view_id=active,
            draft=draft,
            source=source,
            stale=stale,
            can_undo=state.can_undo,
            can_redo=state.can_redo,
            is_dirty=state.is_dirty,
        )
        if draft is None:
            self.figure_page.set_preview_message(
                "Create a figure from this result to freeze publication labels and styling."
            )
            return
        if stale:
            self.figure_page.set_preview_message(
                "Analysis results changed — refresh this figure before previewing or editing."
            )
            return
        family = draft.figure_spec.style.font_family
        if not self.figure_page.font_available(family):
            self.figure_page.set_preview_message(
                f"Font {family!r} is unavailable on this system. Choose an available font family."
            )
            return
        try:
            figure, _axes = self.session.render_figure(active)
        except (OSError, TypeError, ValueError, RuntimeError) as exc:
            self.figure_page.set_preview_message(str(exc))
            return
        self.figure_page.set_preview_figure(figure)

    def _show_figure_ui(self) -> None:
        if not self._prepare_processing_draft() or not self._commit_title_editor():
            return
        try:
            self._current_result()
        except (OSError, TypeError, ValueError, RuntimeError) as exc:
            self._display_error(exc)
            self.analysis_page.continue_button.setEnabled(False)
            return
        self.stack.setCurrentWidget(self.figure_page)
        self.refresh_views()
        self._refresh_figure_workbench()

    def _figure_view_selected(self, view_id: str) -> None:
        if self.stack.currentWidget() is self.figure_page:
            self._refresh_figure_workbench(view_id)

    def _create_figure_ui(self, view_id: str, preset: str) -> None:
        try:
            self.session.create_figure(view_id, preset=preset)
        except (OSError, TypeError, ValueError, RuntimeError) as exc:
            self._display_error(exc)
            return
        self.refresh_views()
        self._refresh_figure_workbench(view_id)

    def _refresh_figure_ui(self, view_id: str) -> None:
        try:
            self.session.refresh_figure(view_id)
        except (OSError, TypeError, ValueError, RuntimeError) as exc:
            self._display_error(exc)
            return
        self.refresh_views()
        self._refresh_figure_workbench(view_id)

    def _reset_figure_ui(self, view_id: str, preset: str) -> None:
        state = self.session.state
        document = state.document
        if document is None:
            return
        try:
            result = self._current_result()
            fresh = create_figure_draft(document, result, view_id, preset=preset)
            self.session.replace_figure_spec(view_id, fresh.figure_spec)
        except (OSError, TypeError, ValueError, RuntimeError) as exc:
            self._display_error(exc)
            return
        self.refresh_views()
        self._refresh_figure_workbench(view_id)

    def _replace_figure_spec_ui(self, view_id: str, spec: object) -> None:
        try:
            self.session.replace_figure_spec(view_id, spec)  # type: ignore[arg-type]
        except (OSError, TypeError, ValueError, RuntimeError) as exc:
            self._display_error(exc)
            self._refresh_figure_workbench(view_id)
            return
        self.refresh_views()
        self._refresh_figure_workbench(view_id)

    def _move_figure_trace_ui(
        self,
        view_id: str,
        trace_id: str,
        new_index: int,
    ) -> None:
        try:
            self.session.move_figure_trace(view_id, trace_id, new_index)
        except (OSError, TypeError, ValueError, RuntimeError) as exc:
            self._display_error(exc)
            self._refresh_figure_workbench(view_id)
            return
        self.refresh_views()
        self._refresh_figure_workbench(view_id)

    def _undo_ui(self) -> None:
        if hasattr(self, "figure_page") and self.stack.currentWidget() is self.figure_page:
            active = self.figure_page.active_view_id
            self.session.undo()
            self.refresh_views()
            self._refresh_figure_workbench(active)
            return
        super()._undo_ui()

    def _redo_ui(self) -> None:
        if hasattr(self, "figure_page") and self.stack.currentWidget() is self.figure_page:
            active = self.figure_page.active_view_id
            self.session.redo()
            self.refresh_views()
            self._refresh_figure_workbench(active)
            return
        super()._redo_ui()


__all__ = ["CatalysisWorkbenchWindow"]
