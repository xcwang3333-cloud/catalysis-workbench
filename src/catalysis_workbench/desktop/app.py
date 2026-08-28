"""Qt application bootstrap for the optional CatalysisWorkbench desktop shell."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtWidgets import QApplication

from catalysis_workbench.application import ApplicationSession

from .window import CatalysisWorkbenchMainWindow


@dataclass(frozen=True, slots=True)
class DesktopHandle:
    """Live Qt application/window pair returned for scripted or test integration."""

    application: QApplication
    window: CatalysisWorkbenchMainWindow


def create_desktop(
    root: str | Path | None = None,
    *,
    session: ApplicationSession | None = None,
    argv: Sequence[str] | None = None,
) -> DesktopHandle:
    """Create the desktop shell without entering the Qt event loop."""

    if session is not None and not isinstance(session, ApplicationSession):
        raise TypeError("session must be an ApplicationSession or None")
    existing = QApplication.instance()
    if existing is None:
        application = QApplication(list(argv or ()))
        application.setApplicationName("CatalysisWorkbench")
        application.setOrganizationName("CatalysisWorkbench")
    else:
        if not isinstance(existing, QApplication):
            raise RuntimeError("existing Qt application is not a QApplication")
        application = existing

    window = CatalysisWorkbenchMainWindow(session=session)
    if root is not None:
        window.open_workspace_path(root)
    return DesktopHandle(application=application, window=window)


def launch_desktop(
    root: str | Path | None = None,
    *,
    session: ApplicationSession | None = None,
    argv: Sequence[str] | None = None,
    show: bool = True,
    execute: bool = True,
):
    """Create and optionally run the desktop event loop."""

    if type(show) is not bool or type(execute) is not bool:
        raise TypeError("show and execute must be bool values")
    handle = create_desktop(root, session=session, argv=argv)
    if show:
        handle.window.show()
    if execute:
        return handle.application.exec()
    return handle


__all__ = ["DesktopHandle", "create_desktop", "launch_desktop"]
