"""v1.1 desktop window extension that adds Figure Package Export."""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QMessageBox

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
        self._recent_display_cache_key: tuple[tuple[str, str], ...] | None = None
        self._recent_display_cache: tuple[object, ...] | None = None
        super().__init__(session=session, recent_store=recent_store)
        self.export_page = FigurePackageExportPage()
        self.stack.addWidget(self.export_page)
        self.figure_page.continue_export_button.setToolTip(
            "Open Figure Package Export for the current publication figure."
        )
        self.figure_page.continue_export_button.clicked.connect(self._show_export_ui)
        self.export_page.back_requested.connect(self._back_to_figure_ui)
        self.export_page.browse_requested.connect(self._browse_export_destination)
        self.export_page.save_requested.connect(self._save_export_project_ui)
        self.export_page.export_requested.connect(self._export_package_ui)
        self.export_page.open_folder_requested.connect(self._open_export_folder)
        self.figure_page.continue_export_button.setEnabled(False)

    def _recent_displays(self):
        """Avoid reopening recent projects for unrelated presentation refreshes."""

        entries = self.recent_store.entries()
        key = tuple((entry.path, entry.last_opened) for entry in entries)
        if key == self._recent_display_cache_key and self._recent_display_cache is not None:
            return self._recent_display_cache
        displays = super()._recent_displays()
        self._recent_display_cache_key = key
        self._recent_display_cache = displays
        return displays

    @staticmethod
    def _error_presentation(exc: BaseException) -> tuple[str, str, str]:
        message = str(exc).strip() or repr(exc)
        lowered = message.casefold()
        details = f"{type(exc).__name__}: {message}"
        if (
            "changed outside" in lowered
            or "concurrent" in lowered
            or "expected manifest" in lowered
        ):
            return (
                "Project changed outside CatalysisWorkbench.",
                "Reopen the project before trying this action again.",
                details,
            )
        if "legacy" in lowered and "workspace" in lowered:
            return (
                "This project uses the legacy v1.0 workspace format.",
                (
                    "Open it through the explicit v1.0 compatibility path "
                    "or create a v1.1 analysis project."
                ),
                details,
            )
        if "font" in lowered and "unavailable" in lowered:
            return (
                "The selected figure font is unavailable.",
                "Choose an available font family in Figure Workbench before export.",
                details,
            )
        return (
            "CatalysisWorkbench could not complete this action.",
            message,
            details,
        )

    def _display_error(self, exc: BaseException) -> None:
        summary, guidance, details = self._error_presentation(exc)
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle("CatalysisWorkbench")
        box.setText(summary)
        box.setInformativeText(guidance)
        box.setDetailedText(details)
        box.exec()

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

    def _apply_export_preflight(
        self,
        view_id: str,
        *,
        report_errors: bool = True,
    ) -> bool:
        try:
            state, _document, result, draft, _source, stale, font_available = (
                self._export_context(view_id)
            )
            view = next(item for item in result.views if item.view_id == view_id)
        except (OSError, TypeError, ValueError, RuntimeError) as exc:
            if report_errors:
                self._display_error(exc)
            return False
        self.export_page.apply_preflight(
            figure_label=view.label,
            project_saved=state.project_root is not None and not state.is_dirty,
            figure_current=not stale,
            font_available=font_available,
            visible_trace_count=self._visible_trace_count(draft),
        )
        return True

    def _show_export_ui(self) -> None:
        active = self.figure_page.active_view_id
        if active is None:
            self._display_error(AnalysisSessionError("no Figure Workbench result is selected"))
            return
        if not self._apply_export_preflight(active):
            return
        self.export_page.show_error("")
        self.stack.setCurrentWidget(self.export_page)

    def _back_to_figure_ui(self) -> None:
        self.stack.setCurrentWidget(self.figure_page)
        self._refresh_figure_workbench(self.figure_page.active_view_id)

    def _save_export_project_ui(self) -> None:
        active = self.figure_page.active_view_id
        if active is None:
            return
        if not self._save_interactive():
            return
        self._apply_export_preflight(active)

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

    def _open_export_folder(self, package_path: str) -> None:
        folder = Path(package_path)
        if not folder.is_dir():
            self.export_page.show_error("The exported package folder is no longer available.")
            return
        opened = QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(folder.resolve(strict=False)))
        )
        if not opened:
            self.export_page.show_error("The operating system could not open the package folder.")

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
        self._apply_export_preflight(active, report_errors=False)


__all__ = ["CatalysisWorkbenchWindow"]
