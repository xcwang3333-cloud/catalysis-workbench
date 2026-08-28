"""v1.1 task-first Home page."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from catalysis_workbench.application import analysis_task_catalog


@dataclass(frozen=True, slots=True)
class RecentProjectDisplay:
    path: str
    title: str
    task_name: str
    available: bool


class HomePage(QWidget):
    """Select a scientific task before any project directory is required."""

    task_selected = Signal(str)
    open_project_requested = Signal()
    recent_project_requested = Signal(str)
    recent_remove_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.task_buttons: dict[str, QPushButton] = {}
        self._recent_layout = QVBoxLayout()
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        title = QLabel("CatalysisWorkbench")
        title.setObjectName("homeTitle")
        subtitle = QLabel("Choose an analysis task to start. A project is created only when you save.")
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        task_row = QHBoxLayout()
        for task in analysis_task_catalog():
            card = QPushButton(f"{task.display_name}\n\n{task.description}")
            card.setObjectName(f"taskCard_{task.task_id}")
            card.setMinimumHeight(120)
            card.clicked.connect(
                lambda _checked=False, task_id=task.task_id: self.task_selected.emit(task_id)
            )
            self.task_buttons[task.task_id] = card
            task_row.addWidget(card)
        root.addLayout(task_row)

        open_button = QPushButton("Open Project…")
        open_button.clicked.connect(self.open_project_requested.emit)
        root.addWidget(open_button)

        root.addWidget(QLabel("Recent Projects"))
        recent_container = QWidget()
        recent_container.setLayout(self._recent_layout)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(recent_container)
        root.addWidget(scroll, 1)
        self.set_recent_projects(())

    def set_recent_projects(self, projects: Sequence[RecentProjectDisplay]) -> None:
        while self._recent_layout.count():
            item = self._recent_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        if not projects:
            self._recent_layout.addWidget(QLabel("No recent projects."))
            self._recent_layout.addStretch(1)
            return
        for project in projects[:5]:
            row = QFrame()
            layout = QHBoxLayout(row)
            if project.available:
                label = QLabel(f"{project.title}\n{project.task_name}\n{project.path}")
            else:
                label = QLabel(f"Unavailable\n{project.path}")
            label.setWordWrap(True)
            layout.addWidget(label, 1)
            open_button = QPushButton("Open")
            open_button.setEnabled(project.available)
            open_button.clicked.connect(
                lambda _checked=False, path=project.path: self.recent_project_requested.emit(path)
            )
            layout.addWidget(open_button)
            remove_button = QPushButton("Remove")
            remove_button.clicked.connect(
                lambda _checked=False, path=project.path: self.recent_remove_requested.emit(path)
            )
            layout.addWidget(remove_button)
            self._recent_layout.addWidget(row)
        self._recent_layout.addStretch(1)


__all__ = ["HomePage", "RecentProjectDisplay"]
