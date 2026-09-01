"""v1.2 theme, responsive, and accessibility hardening for the product shell."""

from __future__ import annotations

from collections.abc import Mapping

from PySide6.QtCore import QEvent, QObject, QTimer, Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget

from .ui_foundation import ThemeMode, _DARK, _LIGHT, resolved_theme

_A11Y_MARKER = "/* cw-block7-a11y:"
_COMPACT_WIDTH = 1320
_ROUTE_SHORTCUTS: Mapping[str, str] = {
    "home": "Ctrl+1",
    "analysis": "Ctrl+2",
    "figure": "Ctrl+3",
    "export": "Ctrl+4",
}


def accessibility_stylesheet(mode: ThemeMode | str) -> str:
    """Return focus/contrast overrides layered on the semantic v1.2 theme."""

    resolved = resolved_theme(mode)
    palette = _DARK if resolved is ThemeMode.DARK else _LIGHT
    primary_text = palette.window if resolved is ThemeMode.DARK else palette.surface
    return f"""
/* cw-block7-a11y:{resolved.value} */
QPushButton#cwPrimaryButton,
QToolButton#cwSaveButton {{
    color: {primary_text};
}}
QPushButton#cwNavButton:focus,
QToolButton#cwSidebarToggle:focus,
QToolButton#cwCommandButton:focus {{
    border: 2px solid {palette.accent};
    background: {palette.accent_soft};
}}
QToolButton#cwSaveButton:focus,
QPushButton#cwPrimaryButton:focus {{
    border: 2px solid {palette.accent_hover};
}}
QPushButton#cwSecondaryButton:focus,
QPushButton#cwTertiaryButton:focus {{
    border: 2px solid {palette.accent};
    background: {palette.accent_soft};
}}
QListWidget#cwImportFileList:focus,
QTableWidget#cwPreviewTable:focus,
QListWidget#cwDataNavigatorList:focus,
QListWidget#cwInspectorPairList:focus {{
    border: 2px solid {palette.accent};
}}
QLineEdit:focus,
QComboBox:focus,
QSpinBox:focus,
QDoubleSpinBox:focus {{
    border: 2px solid {palette.accent};
}}
QCheckBox:focus,
QRadioButton:focus {{
    color: {palette.accent};
}}
"""


class DesktopHardeningController(QObject):
    """Presentation-only v1.2 hardening attached to the product window."""

    def __init__(self, window: QMainWindow) -> None:
        super().__init__(window)
        if not isinstance(window, QMainWindow):
            raise TypeError("window must be a QMainWindow")
        if not hasattr(window, "app_shell"):
            raise TypeError("window must expose the v1.2 app_shell")
        self.window = window
        self.shell = window.app_shell
        self.settings = self.shell.settings
        self.theme_actions: dict[ThemeMode, QAction] = {}
        self.navigation_actions: dict[str, QAction] = {}
        self._nav_buttons: set[QWidget] = set()

        self.shell._COMPACT_WIDTH = _COMPACT_WIDTH
        self._build_view_menu()
        self._install_accessibility_metadata()
        self.shell.installEventFilter(self)
        for button in self._nav_buttons:
            button.installEventFilter(self)
        self._ensure_theme_overlay()
        self.shell._update_sidebar_compact()
        self._sync_navigation_actions()
        self._connect_system_theme()

    @property
    def compact_width(self) -> int:
        return _COMPACT_WIDTH

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if watched is self.shell and event.type() is QEvent.Type.StyleChange:
            QTimer.singleShot(0, self._ensure_theme_overlay)
        elif watched in self._nav_buttons and event.type() is QEvent.Type.EnabledChange:
            QTimer.singleShot(0, self._sync_navigation_actions)
        return super().eventFilter(watched, event)

    def _build_view_menu(self) -> None:
        view_menu = self.window.menuBar().addMenu("&View")
        view_menu.setObjectName("cwViewMenu")

        theme_menu = view_menu.addMenu("Theme")
        theme_menu.setObjectName("cwThemeMenu")
        group = QActionGroup(self.window)
        group.setExclusive(True)
        current = self.settings.theme_mode()
        for mode, label in (
            (ThemeMode.SYSTEM, "System"),
            (ThemeMode.LIGHT, "Light"),
            (ThemeMode.DARK, "Dark"),
        ):
            action = QAction(label, self.window)
            action.setCheckable(True)
            action.setChecked(mode is current)
            action.setStatusTip(f"Use the {label.casefold()} application theme")
            action.triggered.connect(
                lambda _checked=False, selected=mode: self._set_theme(selected)
            )
            group.addAction(action)
            theme_menu.addAction(action)
            self.theme_actions[mode] = action
        self._theme_group = group

        view_menu.addSeparator()
        navigation_menu = view_menu.addMenu("Navigation")
        navigation_menu.setObjectName("cwNavigationMenu")
        labels = {
            "home": "Home",
            "analysis": "Data & Analysis",
            "figure": "Figure",
            "export": "Export",
        }
        for page_id, shortcut_text in _ROUTE_SHORTCUTS.items():
            action = QAction(labels[page_id], self.window)
            action.setShortcut(QKeySequence(shortcut_text))
            action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
            action.setStatusTip(f"Open {labels[page_id]} ({shortcut_text})")
            action.triggered.connect(
                lambda _checked=False, route=page_id: self.window._shell_route_requested(route)
            )
            navigation_menu.addAction(action)
            self.navigation_actions[page_id] = action

        toggle = QAction("Toggle Navigation", self.window)
        toggle.setShortcut(QKeySequence("Ctrl+Shift+B"))
        toggle.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        toggle.setStatusTip("Collapse or expand the primary navigation")
        toggle.triggered.connect(self.shell._toggle_sidebar_preference)
        navigation_menu.addSeparator()
        navigation_menu.addAction(toggle)
        self.toggle_navigation_action = toggle

    def _install_accessibility_metadata(self) -> None:
        shell = self.shell
        sidebar = shell.sidebar
        command = shell.command_bar

        self.window.setAccessibleName("CatalysisWorkbench")
        shell.setAccessibleName("CatalysisWorkbench application shell")
        sidebar.setAccessibleName("Primary navigation")
        sidebar.setAccessibleDescription(
            "Navigate between Home, Data and Analysis, Figure, and Export."
        )
        sidebar.collapse_button.setAccessibleName("Toggle primary navigation")
        sidebar.collapse_button.setAccessibleDescription(
            "Collapse or expand the primary navigation sidebar."
        )
        sidebar.collapse_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        ordered: list[QWidget] = [sidebar.collapse_button]
        for page_id in sidebar.page_ids:
            button = sidebar._buttons[page_id]
            label = sidebar._labels[page_id]
            shortcut = _ROUTE_SHORTCUTS.get(page_id, "")
            button.setAccessibleName(f"{label} navigation")
            button.setAccessibleDescription(f"Open the {label} page.")
            button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            if shortcut:
                button.setToolTip(f"{label} ({shortcut})")
            self._nav_buttons.add(button)
            ordered.append(button)

        command.setAccessibleName("Project command bar")
        command.project_title.setAccessibleName("Current project")
        command.task_pill.setAccessibleName("Current analysis task")
        command.dirty_pill.setAccessibleName("Project modified status")
        for button, label in (
            (command.undo_button, "Undo"),
            (command.redo_button, "Redo"),
            (command.save_button, "Save project"),
        ):
            button.setAccessibleName(label)
            button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            ordered.append(button)

        shell.status_bar.setAccessibleName("Application status")
        shell.status_bar.setAccessibleDescription(
            "Reports the current analysis, figure, or export state."
        )

        for first, second in zip(ordered, ordered[1:], strict=False):
            QWidget.setTabOrder(first, second)

    def _set_theme(self, mode: ThemeMode) -> None:
        self.shell.set_theme_mode(mode)
        self._ensure_theme_overlay()
        self._sync_theme_actions()

    def _ensure_theme_overlay(self) -> None:
        sheet = self.shell.styleSheet()
        if _A11Y_MARKER in sheet:
            self._sync_theme_actions()
            return
        self.shell.setStyleSheet(
            sheet.rstrip() + "\n" + accessibility_stylesheet(self.settings.theme_mode())
        )
        self._sync_theme_actions()

    def _sync_theme_actions(self) -> None:
        current = self.settings.theme_mode()
        for mode, action in self.theme_actions.items():
            action.setChecked(mode is current)

    def _sync_navigation_actions(self) -> None:
        for page_id, action in self.navigation_actions.items():
            action.setEnabled(page_id == "home" or self.shell.page_enabled(page_id))

    def _connect_system_theme(self) -> None:
        application = QApplication.instance()
        if application is None:
            return
        hints = application.styleHints()
        signal = getattr(hints, "colorSchemeChanged", None)
        if signal is not None:
            signal.connect(self._system_color_scheme_changed)

    def _system_color_scheme_changed(self, _scheme: object) -> None:
        if self.settings.theme_mode() is not ThemeMode.SYSTEM:
            return
        self.shell.set_theme_mode(ThemeMode.SYSTEM)
        self._ensure_theme_overlay()


def install_desktop_hardening(window: QMainWindow) -> DesktopHardeningController:
    """Install Block-7 hardening on the v1.2 product path only."""

    return DesktopHardeningController(window)


__all__ = [
    "DesktopHardeningController",
    "accessibility_stylesheet",
    "install_desktop_hardening",
]
