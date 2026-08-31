"""v1.2 New Analysis task chooser."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from catalysis_workbench.application import analysis_task_catalog

from .ui_foundation import SPACING, refresh_widget_style


class NewAnalysisDialog(QDialog):
    """Choose one stable analysis task before creating any project state."""

    task_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("cwNewAnalysisDialog")
        self.setWindowTitle("New Analysis")
        self.setModal(True)
        self.setMinimumWidth(620)
        self.task_buttons: dict[str, QPushButton] = {}
        self._selected_task_id: str | None = None
        self._build_ui()

    @property
    def selected_task_id(self) -> str | None:
        return self._selected_task_id

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(
            SPACING.section,
            SPACING.section,
            SPACING.section,
            SPACING.section,
        )
        root.setSpacing(SPACING.normal)

        title = QLabel("Choose an analysis type")
        title.setObjectName("cwDialogTitle")
        root.addWidget(title)

        subtitle = QLabel(
            "Select the scientific workflow that matches your data. "
            "You can add files after the analysis opens."
        )
        subtitle.setObjectName("cwMutedText")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        task_layout = QVBoxLayout()
        task_layout.setSpacing(SPACING.compact)
        for task in analysis_task_catalog():
            card = QPushButton(f"{task.display_name}\n{task.description}")
            card.setObjectName(f"taskCard_{task.task_id}")
            card.setProperty("cwRole", "taskCard")
            card.setProperty("selected", False)
            card.setCheckable(True)
            card.setMinimumHeight(88)
            card.clicked.connect(
                lambda _checked=False, task_id=task.task_id: self.select_task(task_id)
            )
            self.task_buttons[task.task_id] = card
            task_layout.addWidget(card)
        root.addLayout(task_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.start_button = QPushButton("Start Analysis")
        self.start_button.setObjectName("cwPrimaryButton")
        self.start_button.setEnabled(False)
        buttons.addButton(self.start_button, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.rejected.connect(self.reject)
        self.start_button.clicked.connect(self._start_selected)
        root.addWidget(buttons)

    def select_task(self, task_id: str) -> None:
        if task_id not in self.task_buttons:
            raise ValueError(f"unknown analysis task_id: {task_id!r}")
        self._selected_task_id = task_id
        for current_id, button in self.task_buttons.items():
            selected = current_id == task_id
            button.setChecked(selected)
            button.setProperty("selected", selected)
            refresh_widget_style(button)
        self.start_button.setEnabled(True)

    def reset_selection(self) -> None:
        self._selected_task_id = None
        for button in self.task_buttons.values():
            button.setChecked(False)
            button.setProperty("selected", False)
            refresh_widget_style(button)
        self.start_button.setEnabled(False)

    def _start_selected(self) -> None:
        if self._selected_task_id is None:
            return
        self.task_selected.emit(self._selected_task_id)
        self.accept()


__all__ = ["NewAnalysisDialog"]
