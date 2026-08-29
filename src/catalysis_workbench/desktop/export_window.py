"""v1.1 desktop window extension that adds Figure Package Export."""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtWidgets import QFileDialog

from catalysis_workbench.application import (
    AnalysisSession,
    AnalysisSessionError,
    FigureDraft,
    FigurePackageOptions,
    export_session_figure_package,
    figure_draft_is_stale,
    figure_source_view,
)

from .export_workbench import FigurePackageExportPage
from .figure_window import CatalysisWorkbenchWindow as _FigureWorkbenchWindow
from .recent_projects import RecentProjectsStore


class CatalysisWorkbenchWindow(_FigureWorkbenchWindow):
    """Task-first Home → Analysis → Figure → Export desktop shell."""

    def __init__(
        self,
        *,
        session: AnalysisSession | None = None,
        recent_store: RecentProjectsStore | None = None,
    ) -> None:
        super().__init__(session=session, recent_store=recent_store)
        self.export_page = FigurePackageExportPage()
        self.stack.addWidget(self.export_page)
        self.figure_page.continue_export_button.setToolTip(
            "Open Figure Package Export for the current publication figure."
        )
        self.figure_page.continue_export_button.clicked.connect(self._show_export_ui)
        self.export_page.back_requested.connect(self._back_to_figure_ui)
        self.export_page.browse_requested.connect(self._browse_export_destination)
        self.export_page.export_requested.connect(self._export_package_ui)
        self.figure_page.continue_export_button.setEnabled(False)

    @staticmethod
    def _visible_trace_count(draft: FigureDraft) -> int:
        return sum(
            1
            for trace_id in draft.trace_order
            if draft.figure_spec.series_styles.get(trace_id) is None
            or draft.figure_spec.series_styles[trace_id].visible
        )

    def _export_context(self, view_id: str):
        state = self.session.state
        document = state.document
        if document is None:
            raise AnalysisSessionError("no analysis document is open")
        result = self._current_result()
        draft = self.session.figure_draft(view_id)
        source = figure_source_view(document, result, view_id)
        stale = figure_draft_is_stale(draft, document, result)
        family = draft.figure_spec.style.font_family
        font_available = self.figure_page.font_available(family)
        return state, document, result, draft, source, stale, font_available

    def _refresh_figure_workbench(self, view_id: str | None = None) -> None:
        super()._refresh_figure_workbench(view_id)
        button = self.figure_page.continue_export_button
        button.setEnabled(False)
        active = self.figure_page.active_view_id
        if active is None:
            return
        try:
            _state, _document, _result, draft, _source, stale, font_available = (
                self._export_context(active)
            )
        except (OSError, TypeError, ValueError, RuntimeError):
            return
        button.setEnabled(
            not stale and font_available and self._visible_trace_count(draft) > 0
        )

    def _show_export_ui(self) -> None:
        active = self.figure_page.active_view_id
        if active is None:
            self._display_error(AnalysisSessionError("no Figure Workbench result is selected"))
            return
        try:
            state, _document, result, draft, _source, stale, font_available = (
                self._export_context(active)
            )
        except (OSError, TypeError, ValueError, RuntimeError) as exc:
            self._display_error(exc)
            return
        view = next(item for item in result.views if item.view_id == active)
        self.export_page.apply_preflight(
            figure_label=view.label,
            project_saved=state.project_root is not None and not state.is_dirty,
            figure_current=not stale,
            font_available=font_available,
            visible_trace_count=self._visible_trace_count(draft),
        )
        self.export_page.show_error("")
        self.stack.setCurrentWidget(self.export_page)

    def _back_to_figure_ui(self) -> None:
        self.stack.setCurrentWidget(self.figure_page)
        self._refresh_figure_workbench(self.figure_page.active_view_id)

    @staticmethod
    def _safe_package_name(title: str, view_id: str) -> str:
        base = re.sub(r"[^A-Za-z0-9._-]+", "-", title.strip()).strip("-._")
        if not base:
            base = "figure"
        return f"{base}-{view_id}-package"

    def _browse_export_destination(self) -> None:
        state = self.session.state
        start = (
            str(state.project_root.parent)
            if state.project_root is not None
            else str(Path.home())
        )
        parent = QFileDialog.getExistingDirectory(
            self,
            "Choose Figure Package parent folder",
            start,
        )
        if not parent:
            return
        document = state.document
        active = self.figure_page.active_view_id or "figure"
        title = "figure" if document is None else document.title
        self.export_page.set_location(
            Path(parent) / self._safe_package_name(title, active)
        )

    def _export_package_ui(self, destination: str, options: object) -> None:
        active = self.figure_page.active_view_id
        if active is None:
            self.export_page.show_error("No Figure Workbench result is selected.")
            return
        if not isinstance(options, FigurePackageOptions):
            self.export_page.show_error("Invalid Figure Package options.")
            return
        try:
            exported = export_session_figure_package(
                self.session,
                active,
                destination,
                options=options,
            )
        except (OSError, TypeError, ValueError, RuntimeError) as exc:
            self.export_page.show_error(str(exc))
            return
        self.refresh_views()
        self.export_page.show_success(exported.package_path)
        try:
            state, _document, result, draft, _source, stale, font_available = (
                self._export_context(active)
            )
            view = next(item for item in result.views if item.view_id == active)
            self.export_page.apply_preflight(
                figure_label=view.label,
                project_saved=state.project_root is not None and not state.is_dirty,
                figure_current=not stale,
                font_available=font_available,
                visible_trace_count=self._visible_trace_count(draft),
            )
        except (OSError, TypeError, ValueError, RuntimeError):
            pass


__all__ = ["CatalysisWorkbenchWindow"]
