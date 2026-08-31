"""Desktop-only v1.2 visual foundation and presentation settings."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication, QWidget


class ThemeMode(StrEnum):
    """Presentation-only desktop theme preference."""

    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


@dataclass(frozen=True, slots=True)
class SpacingTokens:
    micro: int = 4
    compact: int = 8
    control: int = 12
    normal: int = 16
    section: int = 24
    page: int = 32


@dataclass(frozen=True, slots=True)
class ThemePalette:
    window: str
    surface: str
    surface_alt: str
    border: str
    text: str
    muted: str
    accent: str
    accent_hover: str
    accent_soft: str
    success: str
    warning: str
    danger: str


SPACING = SpacingTokens()

_LIGHT = ThemePalette(
    window="#f5f7fa",
    surface="#ffffff",
    surface_alt="#eef2f6",
    border="#d7dde5",
    text="#1f2937",
    muted="#667085",
    accent="#2563eb",
    accent_hover="#1d4ed8",
    accent_soft="#e8f0ff",
    success="#15803d",
    warning="#b45309",
    danger="#b42318",
)

_DARK = ThemePalette(
    window="#171a1f",
    surface="#20242b",
    surface_alt="#292e36",
    border="#3a414c",
    text="#f1f5f9",
    muted="#a8b0bd",
    accent="#7aa2ff",
    accent_hover="#9ab8ff",
    accent_soft="#273653",
    success="#5fd28a",
    warning="#f3b562",
    danger="#ff8a80",
)


class DesktopUiSettings:
    """QSettings-backed presentation preferences excluded from project identity."""

    _THEME_KEY = "v1_2/ui/theme"
    _SIDEBAR_KEY = "v1_2/ui/sidebar_collapsed"

    def __init__(self, settings: QSettings | None = None) -> None:
        self._settings = (
            settings
            if settings is not None
            else QSettings("CatalysisWorkbench", "CatalysisWorkbench")
        )

    def theme_mode(self) -> ThemeMode:
        raw = self._settings.value(self._THEME_KEY, ThemeMode.SYSTEM.value)
        try:
            return ThemeMode(str(raw))
        except ValueError:
            return ThemeMode.SYSTEM

    def set_theme_mode(self, mode: ThemeMode | str) -> None:
        value = ThemeMode(mode)
        self._settings.setValue(self._THEME_KEY, value.value)
        self._settings.sync()

    def sidebar_collapsed(self) -> bool:
        raw = self._settings.value(self._SIDEBAR_KEY, False)
        if isinstance(raw, bool):
            return raw
        return str(raw).strip().casefold() in {"1", "true", "yes", "on"}

    def set_sidebar_collapsed(self, collapsed: bool) -> None:
        if type(collapsed) is not bool:
            raise TypeError("collapsed must be bool")
        self._settings.setValue(self._SIDEBAR_KEY, collapsed)
        self._settings.sync()


def _system_uses_dark_theme() -> bool:
    app = QApplication.instance()
    if app is None:
        return False
    try:
        return app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except (AttributeError, RuntimeError):
        return False


def resolved_theme(mode: ThemeMode | str) -> ThemeMode:
    requested = ThemeMode(mode)
    if requested is ThemeMode.SYSTEM:
        return ThemeMode.DARK if _system_uses_dark_theme() else ThemeMode.LIGHT
    return requested


def theme_stylesheet(mode: ThemeMode | str) -> str:
    """Return shell-scoped QSS generated from semantic v1.2 color tokens."""

    palette = _DARK if resolved_theme(mode) is ThemeMode.DARK else _LIGHT
    return f"""
QWidget#cwAppShell {{
    background: {palette.window};
    color: {palette.text};
}}
QWidget#cwSidebar,
QWidget#cwCommandBar,
QStatusBar#cwStatusBar {{
    background: {palette.surface};
    color: {palette.text};
}}
QWidget#cwSidebar {{
    border-right: 1px solid {palette.border};
}}
QWidget#cwCommandBar {{
    border-bottom: 1px solid {palette.border};
}}
QStatusBar#cwStatusBar {{
    border-top: 1px solid {palette.border};
}}
QLabel#cwProductName {{
    font-size: 15px;
    font-weight: 600;
}}
QLabel#cwProjectTitle {{
    font-size: 14px;
    font-weight: 600;
}}
QLabel#cwTaskPill,
QLabel#cwDirtyPill {{
    border: 1px solid {palette.border};
    border-radius: 9px;
    padding: 2px 7px;
    background: {palette.surface_alt};
    color: {palette.muted};
}}
QLabel#cwDirtyPill {{
    color: {palette.warning};
}}
QPushButton#cwNavButton {{
    border: 0;
    border-radius: 6px;
    padding: 8px 10px;
    text-align: left;
    background: transparent;
    color: {palette.text};
}}
QPushButton#cwNavButton:hover {{
    background: {palette.surface_alt};
}}
QPushButton#cwNavButton[active="true"] {{
    background: {palette.accent_soft};
    color: {palette.accent};
    font-weight: 600;
}}
QPushButton#cwNavButton:disabled {{
    color: {palette.muted};
}}
QToolButton#cwSidebarToggle,
QToolButton#cwCommandButton {{
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 5px;
    background: transparent;
    color: {palette.text};
}}
QToolButton#cwSidebarToggle:hover,
QToolButton#cwCommandButton:hover {{
    border-color: {palette.border};
    background: {palette.surface_alt};
}}
QToolButton#cwCommandButton:disabled {{
    color: {palette.muted};
}}
QToolButton#cwSaveButton {{
    border: 1px solid {palette.accent};
    border-radius: 6px;
    padding: 5px 10px;
    background: {palette.accent};
    color: white;
}}
QToolButton#cwSaveButton:hover {{
    background: {palette.accent_hover};
}}
QToolButton#cwSaveButton:disabled {{
    border-color: {palette.border};
    background: {palette.surface_alt};
    color: {palette.muted};
}}
"""


def apply_theme(root: QWidget, mode: ThemeMode | str) -> None:
    """Apply presentation theme only to the v1.2 shell subtree."""

    if not isinstance(root, QWidget):
        raise TypeError("root must be a QWidget")
    root.setStyleSheet(theme_stylesheet(mode))


def refresh_widget_style(widget: QWidget) -> None:
    """Re-evaluate Qt property selectors after presentation state changes."""

    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


__all__ = [
    "DesktopUiSettings",
    "SPACING",
    "SpacingTokens",
    "ThemeMode",
    "ThemePalette",
    "apply_theme",
    "refresh_widget_style",
    "resolved_theme",
    "theme_stylesheet",
]
