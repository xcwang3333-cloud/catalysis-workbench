"""v1.1 empty-state Analysis Workbench shell."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from catalysis_workbench.application import AnalysisSessionState, get_analysis_task_descriptor


class AnalysisShellPage(QWidget):
    """Three-column shell that receives scientific data in later v1.1 blocks."""

    home_requested = Signal()
    title_changed = Signal(str)
    save_requested = Signal()
    undo_requested = Signal()
    redo_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        self.home_button = QPushButton("← Home")
        self.home_button.clicked.connect(self.home_requested.emit)
        toolbar.addWidget(self.home_button)
        self.task_label = QLabel("No task")
        toolbar.addWidget(self.task_label)
        self.title_edit = QLineEdit()
        self.title_edit.editingFinished.connect(
            lambda: self.title_changed.emit(self.title_edit.text())
        )
        toolbar.addWidget(self.title_edit, 1)
        self.undo_button = QPushButton("Undo")
        self.undo_button.clicked.connect(self.undo_requested.emit)
        toolbar.addWidget(self.undo_button)
        self.redo_button = QPushButton("Redo")
        self.redo_button.clicked.connect(self.redo_requested.emit)
        toolbar.addWidget(self.redo_button)
        self.save_button = QPushButton("Save Project")
        self.save_button.clicked.connect(self.save_requested.emit)
        toolbar.addWidget(self.save_button)
        root.addLayout(toolbar)

        self.status_label = QLabel("No analysis")
        root.addWidget(self.status_label)

        columns = QHBoxLayout()
        for heading, message in (
            ("DATA", "No data yet."),
            ("LIVE ANALYSIS", "Add data in the next stage."),
            ("PROCESSING", "Controls become available after data is added."),
        ):
            box = QGroupBox(heading)
            box_layout = QVBoxLayout(box)
            text = QLabel(message)
            text.setWordWrap(True)
            box_layout.addWidget(text)
            box_layout.addStretch(1)
            columns.addWidget(box, 1)
        root.addLayout(columns, 1)

        self.continue_button = QPushButton("Continue to Figure")
        self.continue_button.setEnabled(False)
        root.addWidget(self.continue_button)

    def apply_state(self, state: AnalysisSessionState) -> None:
        document = state.document
        if document is None:
            self.task_label.setText("No task")
            self.title_edit.clear()
            self.status_label.setText("No analysis")
            self.undo_button.setEnabled(False)
            self.redo_button.setEnabled(False)
            self.save_button.setEnabled(False)
            return
        task = get_analysis_task_descriptor(document.task_id)
        self.task_label.setText(task.display_name)
        if self.title_edit.text() != document.title:
            self.title_edit.setText(document.title)
        self.undo_button.setEnabled(state.can_undo)
        self.redo_button.setEnabled(state.can_redo)
        self.save_button.setEnabled(True)
        if state.is_dirty:
            status = "Modified"
        elif state.is_unsaved:
            status = "Unsaved"
        else:
            status = str(state.project_root)
        self.status_label.setText(status)


__all__ = ["AnalysisShellPage"]
