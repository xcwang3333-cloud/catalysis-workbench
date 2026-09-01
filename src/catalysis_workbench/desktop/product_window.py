"""v1.2 composition shell around the retained v1.1 task-first desktop."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from catalysis_workbench.application import (
    AnalysisResult,
    AnalysisSession,
    get_analysis_task_descriptor,
)

from .app_shell import AppShell
from .dialog_presentation import (
    build_dirty_guard_dialog,
    build_error_dialog,
    build_processing_draft_dialog,
    build_remove_data_dialog,
)
from .export_presentation import (
    export_status_message,
    productize_export_workbench,
    refresh_export_presentation_state,
)
from .export_window import CatalysisWorkbenchWindow as _V11TaskWindow
from .figure_presentation import (
    productize_figure_workbench,
    refresh_figure_presentation_state,
)
from .recent_projects import RecentProjectsStore
from .ui_foundation import DesktopUiSettings


class CatalysisWorkbenchWindow(_V11TaskWindow):
    """Unified product shell hosting the retained v1.1 task pages."""

    def __init__(
        self,
        *,
        session: AnalysisSession | None = None,
        recent_store: RecentProjectsStore | None = None,
        ui_settings: DesktopUiSettings | None = None,
    ) -> None:
        self._v12_ui_settings = ui_settings or DesktopUiSettings()
        super().__init__(session=session, recent_store=recent_store)
        productize_figure_workbench(self.figure_page)
        productize_export_workbench(self.export_page)

        self.takeCentralWidget()
        self.app_shell = AppShell(
            self.stack,
            settings=self._v12_ui_settings,
            parent=self,
        )
        self.app_shell.register_page("home", "Home", self.home_page, enabled=True)
        self.app_shell.register_page(
            "analysis",
            "Data & Analysis",
            self.analysis_page,
            enabled=self.session.state.document is not None,
        )
        self.app_shell.register_page("figure", "Figure", self.figure_page, enabled=False)
        self.app_shell.register_page("export", "Export", self.export_page, enabled=False)
        self.setCentralWidget(self.app_shell)
        self.resize(1440, 900)

        self.app_shell.route_requested.connect(self._shell_route_requested)
        self.app_shell.undo_requested.connect(self._undo_ui)
        self.app_shell.redo_requested.connect(self._redo_ui)
        self.app_shell.save_requested.connect(self._save_interactive)
        self.export_page.presentation_state_changed.connect(
            self._export_presentation_state_changed
        )
        self.stack.currentChanged.connect(self._shell_page_changed)
        self._refresh_shell_state()

    def refresh_views(self) -> None:
        super().refresh_views()
        if hasattr(self, "app_shell"):
            self._refresh_shell_state()

    def _apply_evaluation(
        self,
        status: str,
        result: AnalysisResult | None,
        message: str | None,
    ) -> None:
        super()._apply_evaluation(status, result, message)
        if not hasattr(self, "app_shell"):
            return
        current = status == "success" and result is not None
        self.app_shell.set_page_enabled("figure", current)
        if not current:
            self.app_shell.set_page_enabled("export", False)
        self._refresh_shell_state()

    def _processing_draft_state_changed(self, invalid: bool, message: str) -> None:
        super()._processing_draft_state_changed(invalid, message)
        if invalid and hasattr(self, "app_shell"):
            self.app_shell.set_page_enabled("figure", False)
            self.app_shell.set_page_enabled("export", False)
            self._refresh_shell_state()

    def _refresh_figure_workbench(self, view_id: str | None = None) -> None:
        super()._refresh_figure_workbench(view_id)
        refresh_figure_presentation_state(self.figure_page)
        if not hasattr(self, "app_shell"):
            return
        self.app_shell.set_page_enabled(
            "export",
            self.figure_page.continue_export_button.isEnabled(),
        )
        self._refresh_shell_state()

    def _display_error(self, exc: BaseException) -> None:
        summary, guidance, details = self._error_presentation(exc)
        build_error_dialog(
            self,
            summary=summary,
            guidance=guidance,
            details=details,
            mode=self._v12_ui_settings.theme_mode(),
        ).exec()

    def _dirty_decision(self) -> str:
        if not self.session.state.is_dirty:
            return "continue"
        box, save_button, discard_button, cancel_button = build_dirty_guard_dialog(
            self,
            mode=self._v12_ui_settings.theme_mode(),
        )
        box.exec()
        clicked = box.clickedButton()
        if clicked is save_button:
            return "save"
        if clicked is discard_button:
            return "discard"
        if clicked is cancel_button:
            return "cancel"
        return "cancel"

    def _prepare_processing_draft(self) -> bool:
        if not self.analysis_page.has_unapplied_processing_draft:
            return True
        box, discard_button, cancel_button = build_processing_draft_dialog(
            self,
            mode=self._v12_ui_settings.theme_mode(),
        )
        box.exec()
        if box.clickedButton() is not discard_button:
            return False
        self.analysis_page.discard_processing_draft()
        self._refresh_live_analysis()
        return True

    def _remove_series_ui(self, data_id: str) -> None:
        if not self._prepare_processing_draft():
            return
        try:
            spec = self._data_spec(data_id)
            impact = self.session.analysis_dependency_impact(data_id)
        except (OSError, ValueError, RuntimeError) as exc:
            self._display_error(exc)
            return

        impact_lines: list[str] = []
        if impact.partial_current_pair_count:
            impact_lines.append(
                "• remove "
                f"{impact.partial_current_pair_count} explicit partial-current pair(s)"
            )
        if impact.override_count:
            impact_lines.append(
                "• remove "
                f"{impact.override_count} selected-series processing override(s)"
            )
        box, remove_button, _cancel_button = build_remove_data_dialog(
            self,
            display_name=spec.display_name,
            impact_lines=tuple(impact_lines),
            mode=self._v12_ui_settings.theme_mode(),
        )
        box.exec()
        if box.clickedButton() is not remove_button:
            return
        try:
            self.remove_data_series(data_id)
        except (OSError, ValueError, RuntimeError) as exc:
            self._display_error(exc)

    def _show_export_ui(self) -> None:
        super()._show_export_ui()
        refresh_export_presentation_state(self.export_page)
        if hasattr(self, "app_shell"):
            self._refresh_shell_state()

    def _back_to_figure_ui(self) -> None:
        super()._back_to_figure_ui()
        if hasattr(self, "app_shell"):
            self._refresh_shell_state()

    def _export_package_ui(self, destination: str, options: object) -> None:
        self.export_page.set_busy(True)
        refresh_export_presentation_state(self.export_page)
        if hasattr(self, "app_shell"):
            self._refresh_shell_state()
        app = QApplication.instance()
        if app is not None:
            app.processEvents()
        try:
            super()._export_package_ui(destination, options)
        finally:
            self.export_page.set_busy(False)
            refresh_export_presentation_state(self.export_page)
            if hasattr(self, "app_shell"):
                self._refresh_shell_state()

    def _export_presentation_state_changed(self, _state: str) -> None:
        refresh_export_presentation_state(self.export_page)
        if hasattr(self, "app_shell"):
            self._refresh_shell_state()

    def _shell_page_changed(self, _index: int) -> None:
        if hasattr(self, "app_shell"):
            self._refresh_shell_state()

    def _refresh_shell_state(self) -> None:
        state = self.session.state
        document = state.document
        self.app_shell.set_page_enabled("analysis", document is not None)

        if document is None:
            self.app_shell.set_page_enabled("figure", False)
            self.app_shell.set_page_enabled("export", False)
            title = None
            task_name = None
            status = "Ready"
        else:
            task_name = get_analysis_task_descriptor(document.task_id).display_name
            title = document.title
            if state.is_dirty:
                status = "Modified — save to update the project baseline"
            elif state.project_root is None:
                status = "Unsaved analysis"
            elif self._last_valid_result is not None:
                status = "Analysis current"
            elif document.data_series:
                status = "Analysis needs valid processing state"
            else:
                status = "Waiting for data"

            current_widget = self.stack.currentWidget()
            if current_widget is self.export_page:
                status = export_status_message(self.export_page)
            elif current_widget is self.figure_page:
                figure_state = getattr(
                    self.figure_page,
                    "canvas_state_label",
                    None,
                )
                semantic_state = (
                    None if figure_state is None else figure_state.property("state")
                )
                if semantic_state == "empty":
                    status = "Create a publication figure"
                elif semantic_state == "stale":
                    status = "Figure needs refresh from Analysis"
                elif semantic_state == "error":
                    status = "Figure preview needs attention"
                elif semantic_state == "success":
                    status = "Figure current"

        self.app_shell.apply_state(
            title=title,
            task_name=task_name,
            dirty=state.is_dirty,
            save_enabled=document is not None,
            can_undo=state.can_undo,
            can_redo=state.can_redo,
            status=status,
        )

    def _shell_route_requested(self, page_id: str) -> None:
        if page_id == "home":
            self._request_home()
            return
        if page_id == "analysis":
            if self.session.state.document is not None:
                self.show_analysis()
            return
        if page_id == "figure":
            if self.app_shell.page_enabled("figure"):
                self._show_figure_ui()
            return
        if page_id == "export" and self.app_shell.page_enabled("export"):
            self._show_export_ui()


__all__ = ["CatalysisWorkbenchWindow"]
