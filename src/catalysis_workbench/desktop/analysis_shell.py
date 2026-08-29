"""v1.1 Analysis Workbench shell with explicit data intake and raw preview."""

from __future__ import annotations

from collections.abc import Sequence

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from catalysis_workbench.application import (
    AnalysisSessionState,
    MaterializedInput,
    get_analysis_task_descriptor,
)


class AnalysisShellPage(QWidget):
    """Task-driven three-column Analysis Workbench for mapped scientific data."""

    home_requested = Signal()
    title_changed = Signal(str)
    save_requested = Signal()
    undo_requested = Signal()
    redo_requested = Signal()
    add_files_requested = Signal()
    files_dropped = Signal(object)
    edit_mapping_requested = Signal(str)
    preview_data_requested = Signal(str)
    remove_series_requested = Signal(str)
    series_renamed = Signal(str, str)
    series_moved = Signal(str, int)

    _SUPPORTED_SUFFIXES = {".csv", ".txt", ".tsv", ".dat", ".xlsx", ".xlsm"}

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rebuilding_series = False
        self._series_by_id = {}
        self.setAcceptDrops(True)
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

        splitter = QSplitter(Qt.Orientation.Horizontal)

        data_box = QGroupBox("DATA")
        data_layout = QVBoxLayout(data_box)
        self.add_files_button = QPushButton("+ Add files")
        self.add_files_button.clicked.connect(self.add_files_requested.emit)
        data_layout.addWidget(self.add_files_button)
        helper = QLabel(
            "Add CSV/TXT/TSV/DAT/Excel files. Each file is previewed and mapped explicitly."
        )
        helper.setWordWrap(True)
        data_layout.addWidget(helper)

        self.series_list = QListWidget()
        self.series_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.series_list.setDragDropMode(
            QAbstractItemView.DragDropMode.InternalMove
        )
        self.series_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.series_list.itemSelectionChanged.connect(self._update_selection)
        self.series_list.itemChanged.connect(self._series_item_changed)
        self.series_list.model().rowsMoved.connect(self._series_rows_moved)
        data_layout.addWidget(self.series_list, 1)

        button_row = QHBoxLayout()
        self.edit_mapping_button = QPushButton("Edit mapping")
        self.edit_mapping_button.clicked.connect(self._emit_edit_mapping)
        button_row.addWidget(self.edit_mapping_button)
        self.preview_data_button = QPushButton("Preview data")
        self.preview_data_button.clicked.connect(self._emit_preview_data)
        button_row.addWidget(self.preview_data_button)
        data_layout.addLayout(button_row)
        self.remove_series_button = QPushButton("Remove selected")
        self.remove_series_button.clicked.connect(self._emit_remove_series)
        data_layout.addWidget(self.remove_series_button)

        self.mapping_summary = QLabel("No data selected.")
        self.mapping_summary.setWordWrap(True)
        data_layout.addWidget(self.mapping_summary)
        splitter.addWidget(data_box)

        preview_box = QGroupBox("LIVE ANALYSIS PREVIEW")
        preview_layout = QVBoxLayout(preview_box)
        self.preview_note = QLabel(
            "Mapped raw values are shown here. Scientific processing is not applied in this block."
        )
        self.preview_note.setWordWrap(True)
        preview_layout.addWidget(self.preview_note)
        self.figure = Figure(figsize=(6.5, 4.5), constrained_layout=True)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.axes = self.figure.add_subplot(111)
        preview_layout.addWidget(self.canvas, 1)
        splitter.addWidget(preview_box)

        processing_box = QGroupBox("PROCESSING")
        processing_layout = QVBoxLayout(processing_box)
        processing_text = QLabel(
            "Data mapping is ready. Scientific processing controls are introduced "
            "in the next v1.1 block so import never silently changes measured values."
        )
        processing_text.setWordWrap(True)
        processing_layout.addWidget(processing_text)
        processing_layout.addStretch(1)
        splitter.addWidget(processing_box)

        splitter.setSizes([280, 720, 330])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        root.addWidget(splitter, 1)

        self.continue_button = QPushButton("Continue to Figure")
        self.continue_button.setEnabled(False)
        self.continue_button.setToolTip(
            "Figure Workbench remains disabled until scientific processing is valid."
        )
        root.addWidget(self.continue_button)
        self._update_selection()

    def _selected_data_id(self) -> str | None:
        item = self.series_list.currentItem()
        if item is None:
            return None
        value = item.data(Qt.ItemDataRole.UserRole)
        return value if isinstance(value, str) and value else None

    def _emit_edit_mapping(self) -> None:
        data_id = self._selected_data_id()
        if data_id is not None:
            self.edit_mapping_requested.emit(data_id)

    def _emit_preview_data(self) -> None:
        data_id = self._selected_data_id()
        if data_id is not None:
            self.preview_data_requested.emit(data_id)

    def _emit_remove_series(self) -> None:
        data_id = self._selected_data_id()
        if data_id is not None:
            self.remove_series_requested.emit(data_id)

    def _series_item_changed(self, item: QListWidgetItem) -> None:
        if self._rebuilding_series:
            return
        data_id = item.data(Qt.ItemDataRole.UserRole)
        previous_name = item.data(Qt.ItemDataRole.UserRole + 1)
        name = item.text().strip()
        if not isinstance(data_id, str) or not name or name == previous_name:
            return
        item.setData(Qt.ItemDataRole.UserRole + 1, name)
        self.series_renamed.emit(data_id, name)

    def _series_rows_moved(
        self,
        source_parent: object,
        source_start: int,
        source_end: int,
        destination_parent: object,
        destination_row: int,
    ) -> None:
        del source_parent, destination_parent
        if self._rebuilding_series or source_start != source_end:
            return
        new_index = (
            destination_row - 1
            if destination_row > source_start
            else destination_row
        )
        QTimer.singleShot(0, lambda: self._emit_moved_row(new_index))

    def _emit_moved_row(self, new_index: int) -> None:
        if new_index < 0 or new_index >= self.series_list.count():
            return
        item = self.series_list.item(new_index)
        data_id = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(data_id, str) and data_id:
            self.series_moved.emit(data_id, new_index)

    def _update_selection(self) -> None:
        data_id = self._selected_data_id()
        enabled = data_id is not None
        self.edit_mapping_button.setEnabled(enabled)
        self.preview_data_button.setEnabled(enabled)
        self.remove_series_button.setEnabled(enabled)
        if data_id is None:
            self.mapping_summary.setText("No data selected.")
            return
        spec = self._series_by_id.get(data_id)
        if spec is None:
            self.mapping_summary.setText("Mapped input")
            return
        mapping = spec.mapping
        x_unit = f" [{mapping.x_unit}]" if mapping.x_unit else ""
        y_unit = f" [{mapping.y_unit}]" if mapping.y_unit else ""
        reference = f" · ref {mapping.x_reference}" if mapping.x_reference else ""
        self.mapping_summary.setText(
            f"{spec.source.original_name}\n"
            f"X: column {mapping.x_column} → {mapping.x_role}{x_unit}{reference}\n"
            f"Y: column {mapping.y_column} → {mapping.y_role}{y_unit}"
        )

    @staticmethod
    def _axis_label(axis: object) -> str:
        label = axis.label or axis.name
        if axis.unit:
            return f"{label} ({axis.unit})"
        return label

    def set_materialized_inputs(
        self,
        inputs: Sequence[MaterializedInput],
        *,
        warning: str | None = None,
    ) -> None:
        self.axes.clear()
        if warning is not None:
            self.preview_note.setText(f"Preview unavailable: {warning}")
            self.canvas.draw_idle()
            return
        if not inputs:
            self.preview_note.setText(
                "Add one or more files, confirm X/Y mapping, and the mapped raw "
                "preview appears here."
            )
            self.axes.set_xlabel("x")
            self.axes.set_ylabel("y")
            self.canvas.draw_idle()
            return

        self.preview_note.setText(
            "Mapped raw values · display sampling only for large series; scientific "
            "data are unchanged."
        )
        for materialized in inputs:
            series = materialized.value
            stride = max(1, (series.n_points + 4999) // 5000)
            self.axes.plot(
                series.x[::stride],
                series.y[::stride],
                label=series.label or series.key,
            )
        first = inputs[0].value
        self.axes.set_xlabel(self._axis_label(first.x_axis))
        self.axes.set_ylabel(self._axis_label(first.y_axis))
        if len(inputs) > 1:
            self.axes.legend()
        self.canvas.draw_idle()

    def apply_state(self, state: AnalysisSessionState) -> None:
        document = state.document
        selected_id = self._selected_data_id()
        if document is None:
            self.task_label.setText("No task")
            self.title_edit.clear()
            self.status_label.setText("No analysis")
            self.undo_button.setEnabled(False)
            self.redo_button.setEnabled(False)
            self.save_button.setEnabled(False)
            self.add_files_button.setEnabled(False)
            self._series_by_id = {}
            self._rebuild_series(())
            return

        task = get_analysis_task_descriptor(document.task_id)
        self.task_label.setText(task.display_name)
        if self.title_edit.text() != document.title:
            self.title_edit.setText(document.title)
        self.undo_button.setEnabled(state.can_undo)
        self.redo_button.setEnabled(state.can_redo)
        self.save_button.setEnabled(True)
        self.add_files_button.setEnabled(True)

        self._series_by_id = {item.data_id: item for item in document.data_series}
        self._rebuild_series(document.data_series, selected_id=selected_id)

        count = len(document.data_series)
        if state.is_dirty:
            storage = "Unsaved changes"
        elif state.is_unsaved:
            storage = "Not saved yet"
        else:
            storage = "Saved"
        self.status_label.setText(f"{count} mapped series · {storage}")

    def _rebuild_series(
        self,
        data_series: Sequence[object],
        *,
        selected_id: str | None = None,
    ) -> None:
        self._rebuilding_series = True
        try:
            self.series_list.clear()
            selected_row = -1
            for index, spec in enumerate(data_series):
                item = QListWidgetItem(spec.display_name)
                item.setData(Qt.ItemDataRole.UserRole, spec.data_id)
                item.setData(Qt.ItemDataRole.UserRole + 1, spec.display_name)
                item.setToolTip(spec.source.original_name)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                self.series_list.addItem(item)
                if spec.data_id == selected_id:
                    selected_row = index
            if selected_row >= 0:
                self.series_list.setCurrentRow(selected_row)
            elif self.series_list.count() > 0:
                self.series_list.setCurrentRow(0)
        finally:
            self._rebuilding_series = False
        self._update_selection()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        urls = event.mimeData().urls()
        if urls and all(
            url.isLocalFile()
            and Path(url.toLocalFile()).suffix.lower() in self._SUPPORTED_SUFFIXES
            for url in urls
        ):
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        paths = tuple(
            url.toLocalFile()
            for url in event.mimeData().urls()
            if url.isLocalFile()
            and Path(url.toLocalFile()).suffix.lower() in self._SUPPORTED_SUFFIXES
        )
        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()
            return
        event.ignore()


__all__ = ["AnalysisShellPage"]