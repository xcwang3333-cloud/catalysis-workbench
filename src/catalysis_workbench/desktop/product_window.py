"""v1.2 composition shell around the retained v1.1 task-first desktop."""

from __future__ import annotations

from catalysis_workbench.application import AnalysisResult, AnalysisSession, get_analysis_task_descriptor

from .app_shell import AppShell
from .export_window import CatalysisWorkbenchWindow as _V11TaskWindow
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
        self.setMinimumSize(1024, 640)
        self.resize(1440, 900)

        self.app_shell.route_requested.connect(self._shell_route_requested)
        self.app_shell.undo_requested.connect(self._undo_ui)
        self.app_shell.redo_requested.connect(self._redo_ui)
        self.app_shell.save_requested.connect(self._save_interactive)
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
        if not hasattr(self, "app_shell"):
            return
        self.app_shell.set_page_enabled(
            "export",
            self.figure_page.continue_export_button.isEnabled(),
        )
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
