"""Qt application bootstrap for CatalysisWorkbench desktop shells."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtWidgets import QApplication

from catalysis_workbench.application import AnalysisSession, ApplicationSession

from .export_window import CatalysisWorkbenchWindow
from .recent_projects import RecentProjectsStore
from .window import CatalysisWorkbenchMainWindow


@dataclass(frozen=True, slots=True)
class DesktopHandle:
    """Live legacy v1.0 Qt application/window pair for compatibility."""

    application: QApplication
    window: CatalysisWorkbenchMainWindow


@dataclass(frozen=True, slots=True)
class WorkbenchDesktopHandle:
    """Live v1.1 task-first Qt application/window pair."""

    application: QApplication
    window: CatalysisWorkbenchWindow


def _qt_application(argv: Sequence[str] | None = None) -> QApplication:
    existing = QApplication.instance()
    if existing is None:
        application = QApplication(list(argv or ()))
        application.setApplicationName("CatalysisWorkbench")
        application.setOrganizationName("CatalysisWorkbench")
        return application
    if not isinstance(existing, QApplication):
        raise RuntimeError("existing Qt application is not a QApplication")
    return existing


def create_desktop(
    root: str | Path | None = None,
    *,
    session: ApplicationSession | None = None,
    argv: Sequence[str] | None = None,
) -> DesktopHandle:
    """Create the legacy v1.0 desktop shell without entering the Qt event loop."""

    if session is not None and not isinstance(session, ApplicationSession):
        raise TypeError("session must be an ApplicationSession or None")
    application = _qt_application(argv)
    window = CatalysisWorkbenchMainWindow(session=session)
    if root is not None:
        window.open_workspace_path(root)
    return DesktopHandle(application=application, window=window)


def create_workbench_desktop(
    root: str | Path | None = None,
    *,
    session: AnalysisSession | None = None,
    argv: Sequence[str] | None = None,
    recent_store: RecentProjectsStore | None = None,
) -> WorkbenchDesktopHandle:
    """Create the v1.1 Home/Analysis/Figure/Export shell without entering Qt."""

    if session is not None and not isinstance(session, AnalysisSession):
        raise TypeError("session must be an AnalysisSession or None")
    application = _qt_application(argv)
    window = CatalysisWorkbenchWindow(session=session, recent_store=recent_store)
    if root is not None:
        window.open_project_path(root)
    return WorkbenchDesktopHandle(application=application, window=window)


def launch_desktop(
    root: str | Path | None = None,
    *,
    session: ApplicationSession | AnalysisSession | None = None,
    argv: Sequence[str] | None = None,
    show: bool = True,
    execute: bool = True,
):
    """Launch Home by default while preserving explicit legacy v1.0 launch paths."""

    if type(show) is not bool or type(execute) is not bool:
        raise TypeError("show and execute must be bool values")

    if session is None and root is None:
        handle = create_workbench_desktop(argv=argv)
    elif isinstance(session, AnalysisSession):
        handle = create_workbench_desktop(root, session=session, argv=argv)
    elif session is None or isinstance(session, ApplicationSession):
        handle = create_desktop(root, session=session, argv=argv)
    else:
        raise TypeError("session must be an ApplicationSession, AnalysisSession, or None")

    if show:
        handle.window.show()
    if execute:
        return handle.application.exec()
    return handle


__all__ = [
    "DesktopHandle",
    "WorkbenchDesktopHandle",
    "create_desktop",
    "create_workbench_desktop",
    "launch_desktop",
]
