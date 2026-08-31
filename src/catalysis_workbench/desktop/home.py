"""v1.2 productized Home page over the retained v1.1 task-first lifecycle."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .new_analysis import NewAnalysisDialog
from .ui_foundation import SPACING


@dataclass(frozen=True, slots=True)
class RecentProjectDisplay:
    path: str
    title: str
    task_name: str
    available: bool


class RecentProjectRow(QFrame):
    """One presentation-only recent-project row."""

    open_requested = Signal(str)
    remove_requested = Signal(str)

    def __init__(
        self,
        project: RecentProjectDisplay,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.project = project
        self.setObjectName("cwRecentProjectRow")

        root = QHBoxLayout(self)
        root.setContentsMargins(
            SPACING.normal,
            SPACING.control,
            SPACING.normal,
            SPACING.control,
        )
        root.setSpacing(SPACING.normal)

        text_column = QVBoxLayout()
        text_column.setSpacing(SPACING.micro)

        self.title_label = QLabel(
            project.title if project.available else "Unavailable project"
        )
        self.title_label.setObjectName("cwRecentProjectTitle")
        text_column.addWidget(self.title_label)

        metadata = QHBoxLayout()
        metadata.setSpacing(SPACING.compact)
        self.task_badge = QLabel(
            project.task_name if project.available else "Unavailable"
        )
        self.task_badge.setObjectName(
            "cwTaskBadge" if project.available else "cwUnavailableBadge"
        )
        metadata.addWidget(self.task_badge)
        metadata.addStretch(1)
        text_column.addLayout(metadata)

        self.path_label = QLabel(project.path)
        self.path_label.setObjectName("cwPathText")
        self.path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.path_label.setWordWrap(True)
        text_column.addWidget(self.path_label)
        root.addLayout(text_column, 1)

        self.open_button = QPushButton("Open")
        self.open_button.setObjectName("cwSecondaryButton")
        self.open_button.setEnabled(project.available)
        self.open_button.clicked.connect(
            lambda _checked=False: self.open_requested.emit(project.path)
        )
        root.addWidget(self.open_button)

        self.remove_button = QPushButton("Remove")
        self.remove_button.setObjectName("cwTertiaryButton")
        self.remove_button.clicked.connect(
            lambda _checked=False: self.remove_requested.emit(project.path)
        )
        root.addWidget(self.remove_button)


class HomePage(QWidget):
    """Start a new analysis or continue one recent project."""

    task_selected = Signal(str)
    open_project_requested = Signal()
    recent_project_requested = Signal(str)
    recent_remove_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("cwHomePage")
        self.new_analysis_dialog = NewAnalysisDialog(self)
        self.task_buttons = self.new_analysis_dialog.task_buttons
        self.recent_rows: list[RecentProjectRow] = []
        self.empty_state: QFrame | None = None
        self.empty_state_label: QLabel | None = None
        self._recent_layout = QVBoxLayout()
        self._build_ui()
        self.new_analysis_dialog.task_selected.connect(self.task_selected.emit)

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(
            SPACING.page,
            SPACING.page,
            SPACING.page,
            SPACING.page,
        )
        outer.setSpacing(0)

        center_row = QHBoxLayout()
        center_row.setSpacing(SPACING.normal)
        center_row.addStretch(1)

        content = QWidget()
        content.setObjectName("cwHomeContent")
        content.setMaximumWidth(1080)
        content.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        root = QVBoxLayout(content)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(SPACING.section)

        intro = QFrame()
        intro.setObjectName("cwHomeIntro")
        intro_layout = QVBoxLayout(intro)
        intro_layout.setContentsMargins(
            SPACING.section,
            SPACING.section,
            SPACING.section,
            SPACING.section,
        )
        intro_layout.setSpacing(SPACING.control)

        self.headline_label = QLabel("Start your analysis")
        self.headline_label.setObjectName("cwHomeHeadline")
        intro_layout.addWidget(self.headline_label)

        self.subtitle_label = QLabel(
            "Start a new scientific workflow or continue a recent project. "
            "A project directory is created only when you save."
        )
        self.subtitle_label.setObjectName("cwHomeSubtitle")
        self.subtitle_label.setWordWrap(True)
        intro_layout.addWidget(self.subtitle_label)

        actions = QHBoxLayout()
        actions.setSpacing(SPACING.compact)
        self.new_analysis_button = QPushButton("New Analysis")
        self.new_analysis_button.setObjectName("cwPrimaryButton")
        self.new_analysis_button.setMinimumWidth(150)
        self.new_analysis_button.clicked.connect(self._show_new_analysis)
        actions.addWidget(self.new_analysis_button)

        self.open_project_button = QPushButton("Open Project…")
        self.open_project_button.setObjectName("cwSecondaryButton")
        self.open_project_button.clicked.connect(self.open_project_requested.emit)
        actions.addWidget(self.open_project_button)
        actions.addStretch(1)
        intro_layout.addLayout(actions)
        root.addWidget(intro)

        recent_section = QVBoxLayout()
        recent_section.setSpacing(SPACING.control)
        recent_title = QLabel("Recent Projects")
        recent_title.setObjectName("cwSectionTitle")
        recent_section.addWidget(recent_title)

        recent_container = QWidget()
        recent_container.setObjectName("cwRecentContainer")
        self._recent_layout.setContentsMargins(0, 0, 0, 0)
        self._recent_layout.setSpacing(SPACING.compact)
        recent_container.setLayout(self._recent_layout)

        scroll = QScrollArea()
        scroll.setObjectName("cwRecentScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.setWidget(recent_container)
        recent_section.addWidget(scroll, 1)
        root.addLayout(recent_section, 1)

        center_row.addWidget(content, 8)
        center_row.addStretch(1)
        outer.addLayout(center_row, 1)
        self.set_recent_projects(())

    def _show_new_analysis(self) -> None:
        self.new_analysis_dialog.reset_selection()
        self.new_analysis_dialog.exec()

    def set_recent_projects(self, projects: Sequence[RecentProjectDisplay]) -> None:
        while self._recent_layout.count():
            item = self._recent_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.recent_rows.clear()
        self.empty_state = None
        self.empty_state_label = None

        if not projects:
            empty = QFrame()
            empty.setObjectName("cwHomeEmptyState")
            layout = QVBoxLayout(empty)
            layout.setContentsMargins(
                SPACING.section,
                SPACING.section,
                SPACING.section,
                SPACING.section,
            )
            label = QLabel("Your recently opened projects will appear here.")
            label.setObjectName("cwMutedText")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)
            self.empty_state = empty
            self.empty_state_label = label
            self._recent_layout.addWidget(empty)
            self._recent_layout.addStretch(1)
            return

        for project in projects[:5]:
            row = RecentProjectRow(project)
            row.open_requested.connect(self.recent_project_requested.emit)
            row.remove_requested.connect(self.recent_remove_requested.emit)
            self.recent_rows.append(row)
            self._recent_layout.addWidget(row)
        self._recent_layout.addStretch(1)


__all__ = ["HomePage", "RecentProjectDisplay", "RecentProjectRow"]
