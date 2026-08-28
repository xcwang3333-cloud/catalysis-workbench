"""Lazy desktop presentation entry points for CatalysisWorkbench."""

from __future__ import annotations

from importlib.util import find_spec
from typing import Any


class DesktopDependencyError(RuntimeError):
    """Raised when the optional desktop toolkit is not installed."""


def desktop_available() -> bool:
    """Return whether the approved optional PySide6 desktop toolkit is importable."""

    try:
        return find_spec("PySide6") is not None and find_spec("PySide6.QtWidgets") is not None
    except (ImportError, ModuleNotFoundError):
        return False


def _dependency_error(exc: ModuleNotFoundError) -> DesktopDependencyError:
    return DesktopDependencyError(
        "CatalysisWorkbench desktop support requires the optional 'desktop' extra "
        "(PySide6-Essentials>=6.11.2,<6.12)"
    )


def launch_desktop(*args: Any, **kwargs: Any):
    """Launch the Qt desktop shell, importing PySide6 only on explicit use."""

    try:
        from .app import launch_desktop as _launch_desktop
    except ModuleNotFoundError as exc:
        if exc.name == "PySide6" or (exc.name or "").startswith("PySide6."):
            raise _dependency_error(exc) from exc
        raise
    return _launch_desktop(*args, **kwargs)


def __getattr__(name: str):
    if name == "CatalysisWorkbenchMainWindow":
        try:
            from .window import CatalysisWorkbenchMainWindow
        except ModuleNotFoundError as exc:
            if exc.name == "PySide6" or (exc.name or "").startswith("PySide6."):
                raise _dependency_error(exc) from exc
            raise
        return CatalysisWorkbenchMainWindow
    raise AttributeError(name)


__all__ = [
    "CatalysisWorkbenchMainWindow",
    "DesktopDependencyError",
    "desktop_available",
    "launch_desktop",
]
