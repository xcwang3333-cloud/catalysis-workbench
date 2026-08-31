"""Unified v1.2 desktop shell for navigation, commands, and status."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .ui_foundation import (
    DesktopUiSettings,
    SPACING,
    ThemeMode,
    apply_theme,
    refresh_widget_style,
)


_ICON_ROLES: Mapping[str, QStyle.StandardPixmap] = {
    "home": QStyle.StandardPixmap.SP_DirHomeIcon,
    "analysis": QStyle.StandardPixmap.SP_FileDialogDetailedView,
    "figure": QStyle.StandardPixmap.SP_FileDialogContentsView,
    "export": QStyle.StandardPixmap.SP_DialogSaveButton,
}


class ShellSidebar(QWidget):
    """Persistent product navigation with compact laptop mode."""

    route_requested = Signal(str)
    collapse_toggle_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("cwSidebar")
        self._buttons: dict[str, QPushButton] = {}
        self._labels: dict[str, str] = {}
        self._compact = False

        root = QVBoxLayout(self)
        root.setContentsMargins(
            SPACING.control,
            SPACING.control,
            SPACING.control,
            SPACING.control,
        )
        root.setSpacing(SPACING.compact)

        header = QHBoxLayout()
        self.product_label = QLabel("CatalysisWorkbench")
        self.product_label.setObjectName("cwProductName")
        header.addWidget(self.product_label, 1)
        self.collapse_button = QToolButton()
        self.collapse_button.setObjectName("cwSidebarToggle")
        self.collapse_button.setToolTip("Collapse navigation")
        self.collapse_button.clicked.connect(self.collapse_toggle_requested.emit)
        header.addWidget(self.collapse_button)
        root.addLayout(header)

        self.nav_layout = QVBoxLayout()
        self.nav_layout.setSpacing(SPACING.micro)
        root.addLayout(self.nav_layout)
        root.addStretch(1)
        self._refresh_collapse_icon()
        self.setMinimumWidth(208)
        self.setMaximumWidth(232)

    @property
    def is_compact(self) -> bool:
        return self._compact

    @property
    def page_ids(self) -> tuple[str, ...]:
        return tuple(self._buttons)

    def register_page(self, page_id: str, label: str) -> None:
        if not page_id or not label:
            raise ValueError("page_id and label must be non-empty")
        if page_id in self._buttons:
            raise ValueError(f"page already registered: {page_id!r}")
        button = QPushButton(label)
        button.setObjectName("cwNavButton")
        button.setCheckable(False)
        button.setProperty("active", False)
        icon_role = _ICON_ROLES.get(page_id)
        if icon_role is not None:
            button.setIcon(self.style().standardIcon(icon_role))
            button.setIconSize(QSize(18, 18))
        button.clicked.connect(
            lambda _checked=False, route=page_id: self.route_requested.emit(route)
        )
        self._buttons[page_id] = button
        self._labels[page_id] = label
        self.nav_layout.addWidget(button)
        self._apply_compact_state(button, page_id)

    def set_page_enabled(self, page_id: str, enabled: bool) -> None:
        button = self._buttons.get(page_id)
        if button is None:
            return
        button.setEnabled(enabled)

    def page_enabled(self, page_id: str) -> bool:
        button = self._buttons.get(page_id)
        return bool(button is not None and button.isEnabled())

    def set_current_page(self, page_id: str | None) -> None:
        for current_id, button in self._buttons.items():
            button.setProperty("active", current_id == page_id)
            refresh_widget_style(button)

    def set_compact(self, compact: bool) -> None:
        if type(compact) is not bool:
            raise TypeError("compact must be bool")
        if compact == self._compact:
            return
        self._compact = compact
        if compact:
            self.setFixedWidth(62)
        else:
            self.setMaximumWidth(232)
            self.setMinimumWidth(208)
        self.product_label.setVisible(not compact)
        for page_id, button in self._buttons.items():
            self._apply_compact_state(button, page_id)
        self._refresh_collapse_icon()

    def _apply_compact_state(self, button: QPushButton, page_id: str) -> None:
        label = self._labels[page_id]
        button.setText("" if self._compact else label)
        button.setToolTip(label if self._compact else "")
        if self._compact:
            button.setMinimumHeight(38)
            button.setMaximumWidth(38)
        else:
            button.setMinimumHeight(36)
            button.setMaximumWidth(16777215)

    def _refresh_collapse_icon(self) -> None:
        role = (
            QStyle.StandardPixmap.SP_ArrowRight
            if self._compact
            else QStyle.StandardPixmap.SP_ArrowLeft
        )
        self.collapse_button.setIcon(self.style().standardIcon(role))
        self.collapse_button.setIconSize(QSize(16, 16))
        self.collapse_button.setToolTip(
            "Expand navigation" if self._compact else "Collapse navigation"
        )


class ShellCommandBar(QWidget):
    """Cross-page project identity and semantic editing commands."""

    undo_requested = Signal()
    redo_requested = Signal()
    save_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("cwCommandBar")
        root = QHBoxLayout(self)
        root.setContentsMargins(
            SPACING.normal,
            SPACING.compact,
            SPACING.normal,
            SPACING.compact,
        )
        root.setSpacing(SPACING.compact)

        self.project_title = QLabel("Home")
        self.project_title.setObjectName("cwProjectTitle")
        root.addWidget(self.project_title)

        self.task_pill = QLabel()
        self.task_pill.setObjectName("cwTaskPill")
        self.task_pill.setVisible(False)
        root.addWidget(self.task_pill)

        self.dirty_pill = QLabel("Modified")
        self.dirty_pill.setObjectName("cwDirtyPill")
        self.dirty_pill.setVisible(False)
        root.addWidget(self.dirty_pill)
        root.addStretch(1)

        self.undo_button = self._command_button(
            "Undo",
            QStyle.StandardPixmap.SP_ArrowBack,
            self.undo_requested.emit,
        )
        self.redo_button = self._command_button(
            "Redo",
            QStyle.StandardPixmap.SP_ArrowForward,
            self.redo_requested.emit,
        )
        self.save_button = self._command_button(
            "Save",
            QStyle.StandardPixmap.SP_DialogSaveButton,
            self.save_requested.emit,
            object_name="cwSaveButton",
        )
        root.addWidget(self.undo_button)
        root.addWidget(self.redo_button)
        root.addWidget(self.save_button)

    def _command_button(
        self,
        text: str,
        icon_role: QStyle.StandardPixmap,
        callback: Callable[[], object],
        *,
        object_name: str = "cwCommandButton",
    ) -> QToolButton:
        button = QToolButton()
        button.setObjectName(object_name)
        button.setText(text)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        button.setIcon(self.style().standardIcon(icon_role))
        button.setIconSize(QSize(16, 16))
        button.clicked.connect(lambda _checked=False: callback())
        return button

    def apply_state(
        self,
        *,
        title: str | None,
        task_name: str | None,
        dirty: bool,
        save_enabled: bool,
        can_undo: bool,
        can_redo: bool,
    ) -> None:
        self.project_title.setText(title or "Home")
        self.task_pill.setText(task_name or "")
        self.task_pill.setVisible(bool(task_name))
        self.dirty_pill.setVisible(dirty)
        self.save_button.setEnabled(save_enabled)
        self.undo_button.setEnabled(can_undo)
        self.redo_button.setEnabled(can_redo)


class AppShell(QWidget):
    """Composition shell around the retained v1.1 task pages."""

    route_requested = Signal(str)
    undo_requested = Signal()
    redo_requested = Signal()
    save_requested = Signal()

    _COMPACT_WIDTH = 1180

    def __init__(
        self,
        stack: QStackedWidget,
        *,
        settings: DesktopUiSettings | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        if not isinstance(stack, QStackedWidget):
            raise TypeError("stack must be a QStackedWidget")
        self.setObjectName("cwAppShell")
        self.stack = stack
        self.settings = settings or DesktopUiSettings()
        self.sidebar = ShellSidebar()
        self.command_bar = ShellCommandBar()
        self.status_bar = QStatusBar()
        self.status_bar.setObjectName("cwStatusBar")
        self.status_bar.setSizeGripEnabled(False)
        self._page_ids_by_widget: dict[QWidget, str] = {}
        self._page_widgets: dict[str, QWidget] = {}

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.sidebar)

        content = QFrame()
        content.setFrameShape(QFrame.Shape.NoFrame)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self.command_bar)
        content_layout.addWidget(self.stack, 1)
        content_layout.addWidget(self.status_bar)
        root.addWidget(content, 1)

        self.sidebar.route_requested.connect(self.route_requested.emit)
        self.sidebar.collapse_toggle_requested.connect(self._toggle_sidebar_preference)
        self.command_bar.undo_requested.connect(self.undo_requested.emit)
        self.command_bar.redo_requested.connect(self.redo_requested.emit)
        self.command_bar.save_requested.connect(self.save_requested.emit)
        self.stack.currentChanged.connect(self._sync_current_page)

        apply_theme(self, self.settings.theme_mode())
        self._update_sidebar_compact()

    @property
    def page_ids(self) -> tuple[str, ...]:
        return tuple(self._page_widgets)

    def register_page(
        self,
        page_id: str,
        label: str,
        widget: QWidget,
        *,
        enabled: bool = True,
    ) -> None:
        if page_id in self._page_widgets:
            raise ValueError(f"page already registered: {page_id!r}")
        if self.stack.indexOf(widget) < 0:
            raise ValueError("registered page must already belong to the shell stack")
        self._page_widgets[page_id] = widget
        self._page_ids_by_widget[widget] = page_id
        self.sidebar.register_page(page_id, label)
        self.sidebar.set_page_enabled(page_id, enabled)
        self._sync_current_page(self.stack.currentIndex())

    def set_page_enabled(self, page_id: str, enabled: bool) -> None:
        if page_id not in self._page_widgets:
            return
        self.sidebar.set_page_enabled(page_id, enabled)

    def page_enabled(self, page_id: str) -> bool:
        return self.sidebar.page_enabled(page_id)

    def set_status(self, message: str) -> None:
        self.status_bar.showMessage(message)

    def apply_state(
        self,
        *,
        title: str | None,
        task_name: str | None,
        dirty: bool,
        save_enabled: bool,
        can_undo: bool,
        can_redo: bool,
        status: str,
    ) -> None:
        self.command_bar.apply_state(
            title=title,
            task_name=task_name,
            dirty=dirty,
            save_enabled=save_enabled,
            can_undo=can_undo,
            can_redo=can_redo,
        )
        self.set_status(status)

    def set_theme_mode(self, mode: ThemeMode | str) -> None:
        resolved = ThemeMode(mode)
        self.settings.set_theme_mode(resolved)
        apply_theme(self, resolved)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 - Qt override
        super().resizeEvent(event)
        self._update_sidebar_compact()

    def _sync_current_page(self, _index: int) -> None:
        widget = self.stack.currentWidget()
        self.sidebar.set_current_page(self._page_ids_by_widget.get(widget))

    def _toggle_sidebar_preference(self) -> None:
        self.settings.set_sidebar_collapsed(not self.settings.sidebar_collapsed())
        self._update_sidebar_compact()

    def _update_sidebar_compact(self) -> None:
        compact = self.width() < self._COMPACT_WIDTH or self.settings.sidebar_collapsed()
        self.sidebar.set_compact(compact)


__all__ = ["AppShell", "ShellCommandBar", "ShellSidebar"]
