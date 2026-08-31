"""v1.2 Analysis Workspace presentation over retained scientific behavior."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from catalysis_workbench.application import (
    AnalysisResult,
    AnalysisSessionState,
    MaterializedInput,
    get_analysis_task_descriptor,
)

from .processing_controls import ProcessingPanel
from .ui_foundation import SPACING, refresh_widget_style


class AnalysisShellPage(QWidget):
    """Task-driven Data Navigator / Scientific Canvas / Processing Inspector."""

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
    analysis_spec_changed = Signal(object)

    _SUPPORTED_SUFFIXES = {".csv", ".txt", ".tsv", ".dat", ".xlsx", ".xlsm"}

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rebuilding_series = False
        self._series_by_id = {}
        self._task_id: str | None = None
        self._raw_inputs: tuple[MaterializedInput, ...] = ()
        self._analysis_result: AnalysisResult | None = None
        self._analysis_status = "incomplete"
        self._analysis_message: str | None = None
        self._analysis_stale = False
        self.setObjectName("cwAnalysisWorkspace")
        self.setAcceptDrops(True)
        self._build_ui()

    @property
    def has_unapplied_processing_draft(self) -> bool:
        return self.processing_panel.has_unapplied_draft

    def discard_processing_draft(self) -> None:
        self.processing_panel.discard_draft()

    def mark_processing_commit_error(self, message: str) -> None:
        self.processing_panel.mark_commit_error(message)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(
            SPACING.normal,
            SPACING.normal,
            SPACING.normal,
            SPACING.normal,
        )
        root.setSpacing(SPACING.normal)

        # Retain the v1.1 page-local command widgets as a hidden compatibility
        # bridge. The v1.2 App Shell is the visible owner of these global actions.
        self._legacy_chrome = QWidget(self)
        self._legacy_chrome.setObjectName("cwLegacyAnalysisChrome")
        legacy = QHBoxLayout(self._legacy_chrome)
        legacy.setContentsMargins(0, 0, 0, 0)
        self.home_button = QPushButton("← Home")
        self.home_button.clicked.connect(self.home_requested.emit)
        legacy.addWidget(self.home_button)
        self.task_label = QLabel("No task")
        legacy.addWidget(self.task_label)
        self.undo_button = QPushButton("Undo")
        self.undo_button.clicked.connect(self.undo_requested.emit)
        legacy.addWidget(self.undo_button)
        self.redo_button = QPushButton("Redo")
        self.redo_button.clicked.connect(self.redo_requested.emit)
        legacy.addWidget(self.redo_button)
        self.save_button = QPushButton("Save Project")
        self.save_button.clicked.connect(self.save_requested.emit)
        legacy.addWidget(self.save_button)
        self._legacy_chrome.setVisible(False)
        root.addWidget(self._legacy_chrome)

        context = QFrame()
        context.setObjectName("cwAnalysisContext")
        context_layout = QHBoxLayout(context)
        context_layout.setContentsMargins(
            SPACING.control,
            SPACING.compact,
            SPACING.control,
            SPACING.compact,
        )
        context_layout.setSpacing(SPACING.control)
        title_label = QLabel("Analysis title")
        title_label.setObjectName("cwWorkspaceFieldLabel")
        context_layout.addWidget(title_label)
        self.title_edit = QLineEdit()
        self.title_edit.setObjectName("cwAnalysisTitleEdit")
        self.title_edit.editingFinished.connect(
            lambda: self.title_changed.emit(self.title_edit.text())
        )
        context_layout.addWidget(self.title_edit, 1)
        self.status_label = QLabel("No analysis")
        self.status_label.setObjectName("cwWorkspaceStatus")
        context_layout.addWidget(self.status_label)
        root.addWidget(context)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("cwAnalysisSplitter")

        data_box = QGroupBox("DATA NAVIGATOR")
        data_box.setObjectName("cwAnalysisPane")
        data_layout = QVBoxLayout(data_box)
        data_layout.setSpacing(SPACING.compact)
        self.add_files_button = QPushButton("+ Add files")
        self.add_files_button.setObjectName("cwPrimaryButton")
        self.add_files_button.clicked.connect(self.add_files_requested.emit)
        data_layout.addWidget(self.add_files_button)
        helper = QLabel(
            "Mapped scientific inputs. Rename or drag to reorder; mapping changes "
            "remain explicit."
        )
        helper.setObjectName("cwWorkspaceHelp")
        helper.setWordWrap(True)
        data_layout.addWidget(helper)

        self.data_state_label = QLabel("No mapped data yet")
        self.data_state_label.setObjectName("cwDataState")
        data_layout.addWidget(self.data_state_label)

        self.series_list = QListWidget()
        self.series_list.setObjectName("cwDataNavigatorList")
        self.series_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.series_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.series_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.series_list.itemSelectionChanged.connect(self._update_selection)
        self.series_list.itemChanged.connect(self._series_item_changed)
        self.series_list.model().rowsMoved.connect(self._series_rows_moved)
        data_layout.addWidget(self.series_list, 1)

        button_row = QHBoxLayout()
        button_row.setSpacing(SPACING.compact)
        self.edit_mapping_button = QPushButton("Edit mapping")
        self.edit_mapping_button.setObjectName("cwSecondaryButton")
        self.edit_mapping_button.clicked.connect(self._emit_edit_mapping)
        button_row.addWidget(self.edit_mapping_button)
        self.preview_data_button = QPushButton("Preview data")
        self.preview_data_button.setObjectName("cwSecondaryButton")
        self.preview_data_button.clicked.connect(self._emit_preview_data)
        button_row.addWidget(self.preview_data_button)
        data_layout.addLayout(button_row)
        self.remove_series_button = QPushButton("Remove selected")
        self.remove_series_button.setObjectName("cwTertiaryButton")
        self.remove_series_button.clicked.connect(self._emit_remove_series)
        data_layout.addWidget(self.remove_series_button)

        self.mapping_summary = QLabel("No data selected.")
        self.mapping_summary.setObjectName("cwMappingSummary")
        self.mapping_summary.setWordWrap(True)
        data_layout.addWidget(self.mapping_summary)
        splitter.addWidget(data_box)

        preview_box = QGroupBox("SCIENTIFIC CANVAS")
        preview_box.setObjectName("cwScientificCanvas")
        preview_layout = QVBoxLayout(preview_box)
        preview_layout.setSpacing(SPACING.compact)
        view_row = QHBoxLayout()
        view_row.setSpacing(SPACING.compact)
        view_label = QLabel("View")
        view_label.setObjectName("cwWorkspaceFieldLabel")
        view_row.addWidget(view_label)
        self.view_combo = QComboBox()
        self.view_combo.setObjectName("cwAnalysisViewCombo")
        self.view_combo.currentIndexChanged.connect(self._render_current_view)
        view_row.addWidget(self.view_combo, 1)
        self.canvas_state_label = QLabel("Waiting for data")
        self.canvas_state_label.setObjectName("cwCanvasState")
        self.canvas_state_label.setProperty("state", "empty")
        view_row.addWidget(self.canvas_state_label)
        preview_layout.addLayout(view_row)

        self.preview_note = QLabel(
            "Add mapped data to begin live scientific analysis."
        )
        self.preview_note.setObjectName("cwCanvasNote")
        self.preview_note.setProperty("state", "empty")
        self.preview_note.setWordWrap(True)
        preview_layout.addWidget(self.preview_note)

        self.figure = Figure(figsize=(6.5, 4.5), constrained_layout=True)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setObjectName("cwAnalysisCanvas")
        self.axes = self.figure.add_subplot(111)
        preview_layout.addWidget(self.canvas, 1)

        canvas_action_row = QHBoxLayout()
        canvas_action_row.addStretch(1)
        self.continue_button = QPushButton("Continue to Figure")
        self.continue_button.setObjectName("cwPrimaryButton")
        self.continue_button.setEnabled(False)
        self.continue_button.setToolTip(
            "Open Figure Workbench using the current successful scientific result."
        )
        canvas_action_row.addWidget(self.continue_button)
        preview_layout.addLayout(canvas_action_row)
        splitter.addWidget(preview_box)

        processing_box = QGroupBox("PROCESSING INSPECTOR")
        processing_box.setObjectName("cwAnalysisPane")
        processing_layout = QVBoxLayout(processing_box)
        processing_layout.setContentsMargins(
            SPACING.compact,
            SPACING.compact,
            SPACING.compact,
            SPACING.compact,
        )
        self.processing_panel = ProcessingPanel()
        self.processing_panel.analysis_spec_changed.connect(
            self.analysis_spec_changed.emit
        )
        self.processing_scroll = QScrollArea()
        self.processing_scroll.setObjectName("cwProcessingScroll")
        self.processing_scroll.setWidgetResizable(True)
        self.processing_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.processing_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.processing_scroll.setWidget(self.processing_panel)
        processing_layout.addWidget(self.processing_scroll)
        splitter.addWidget(processing_box)

        splitter.setSizes([300, 700, 360])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        root.addWidget(splitter, 1)
        self._update_selection()

    def _set_workspace_status(self, text: str, state: str) -> None:
        self.status_label.setProperty("state", state)
        self.status_label.setText(text)
        refresh_widget_style(self.status_label)

    def _set_canvas_state(self, state: str, label: str, note: str) -> None:
        self.canvas_state_label.setProperty("state", state)
        self.canvas_state_label.setText(label)
        self.preview_note.setProperty("state", state)
        self.preview_note.setText(note)
        refresh_widget_style(self.canvas_state_label)
        refresh_widget_style(self.preview_note)

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
        new_index = destination_row - 1 if destination_row > source_start else destination_row
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
        self.processing_panel.set_selected_data_id(data_id)
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

    def _raw_series(self) -> tuple[object, ...]:
        return tuple(item.value for item in self._raw_inputs)

    def _series_for_view(self, view_id: str) -> tuple[object, ...]:
        if view_id == "raw":
            return self._raw_series()
        if self._analysis_result is None:
            return ()
        for view in self._analysis_result.views:
            if view.view_id == view_id:
                return tuple(view.series)
        return ()

    def _rebuild_view_choices(self) -> None:
        previous = self.view_combo.currentData()
        self.view_combo.blockSignals(True)
        self.view_combo.clear()
        if self._task_id == "fe_partial_current" and self._analysis_result is not None:
            for view in self._analysis_result.views:
                self.view_combo.addItem(view.label, view.view_id)
        else:
            self.view_combo.addItem("Raw", "raw")
            if self._analysis_result is not None:
                for view in self._analysis_result.views:
                    self.view_combo.addItem(view.label, view.view_id)
        index = self.view_combo.findData(previous)
        if index < 0 and self.view_combo.count() > 0:
            index = 0
        self.view_combo.setCurrentIndex(index)
        self.view_combo.blockSignals(False)
        self._render_current_view()

    def _render_current_view(self, *_args: object) -> None:
        self.axes.clear()
        view_id = self.view_combo.currentData()
        values = self._series_for_view(view_id if isinstance(view_id, str) else "raw")
        if not values:
            self.axes.set_xlabel("x")
            self.axes.set_ylabel("y")
            self.canvas.draw_idle()
            self._update_preview_note()
            return
        for series in values:
            stride = max(1, (series.n_points + 4999) // 5000)
            self.axes.plot(
                series.x[::stride],
                series.y[::stride],
                label=series.label or series.key,
            )
        first = values[0]
        self.axes.set_xlabel(self._axis_label(first.x_axis))
        self.axes.set_ylabel(self._axis_label(first.y_axis))
        if len(values) > 1:
            self.axes.legend()
        self.canvas.draw_idle()
        self._update_preview_note()

    def _update_preview_note(self) -> None:
        if self._analysis_stale:
            text = "Previous valid result — current settings are not applied"
            if self._analysis_message:
                text += f": {self._analysis_message}"
            self._set_canvas_state("stale", "Previous valid result", text)
            return
        if self._analysis_status == "success":
            view_id = self.view_combo.currentData()
            if view_id == "raw":
                note = (
                    "Mapped raw values · display sampling only for large series; "
                    "scientific data are unchanged."
                )
            elif self._task_id == "fe_partial_current":
                note = (
                    "Live scientific result · FE and partial current use separate "
                    "views and no interpolation."
                )
            else:
                note = (
                    "Live scientific result · committed processing settings are current."
                )
            self._set_canvas_state("success", "Analysis current", note)
            return
        if self._analysis_status == "error":
            self._set_canvas_state(
                "error",
                "Analysis error",
                f"Analysis error: {self._analysis_message or 'live analysis failed'}",
            )
            return
        if not self._raw_inputs:
            self._set_canvas_state(
                "empty",
                "Waiting for data",
                f"Needs input: {self._analysis_message or 'analysis is incomplete'}",
            )
            return
        self._set_canvas_state(
            "incomplete",
            "Needs input",
            f"Needs input: {self._analysis_message or 'analysis is incomplete'}",
        )

    def set_materialized_inputs(
        self,
        inputs: Sequence[MaterializedInput],
        *,
        warning: str | None = None,
    ) -> None:
        if warning is not None:
            self._raw_inputs = ()
            if self._analysis_result is None:
                self._analysis_status = "error"
                self._analysis_message = warning
            self._rebuild_view_choices()
            return
        self._raw_inputs = tuple(inputs)
        self._rebuild_view_choices()

    def set_live_analysis(
        self,
        result: AnalysisResult | None,
        *,
        status: str,
        message: str | None = None,
        stale: bool = False,
    ) -> None:
        self._analysis_result = result
        self._analysis_status = status
        self._analysis_message = message
        self._analysis_stale = stale
        self.processing_panel.set_evaluation_status(status, message, stale=stale)
        self._rebuild_view_choices()

    def apply_state(self, state: AnalysisSessionState) -> None:
        document = state.document
        self.processing_panel.apply_state(state)
        selected_id = self._selected_data_id()
        if document is None:
            self._task_id = None
            self.task_label.setText("No task")
            self.title_edit.clear()
            self._set_workspace_status("No analysis", "empty")
            self.undo_button.setEnabled(False)
            self.redo_button.setEnabled(False)
            self.save_button.setEnabled(False)
            self.add_files_button.setEnabled(False)
            self.data_state_label.setText("No mapped data yet")
            self._series_by_id = {}
            self._rebuild_series(())
            self._raw_inputs = ()
            self._analysis_result = None
            self._rebuild_view_choices()
            return

        self._task_id = document.task_id
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
        self.data_state_label.setText(
            f"{count} mapped series" if count else "No mapped data yet"
        )
        if state.is_dirty:
            storage = "Unsaved changes"
            storage_state = "dirty"
        elif state.is_unsaved:
            storage = "Not saved yet"
            storage_state = "unsaved"
        else:
            storage = "Saved"
            storage_state = "saved"
        self._set_workspace_status(
            f"{count} mapped series · {storage}",
            storage_state,
        )

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
