"""Qt Figure Workbench for presentation-only publication figure editing."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from matplotlib import font_manager
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
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

from catalysis_workbench.application import FigureDraft, FigureSourceView
from catalysis_workbench.visualization.specs import (
    FigureSpec,
    SeriesStyle,
    VisualizationError,
)


class FigureWorkbenchPage(QWidget):
    """Three-column publication presentation editor with immutable FigureSpec updates."""

    back_requested = Signal()
    save_requested = Signal()
    undo_requested = Signal()
    redo_requested = Signal()
    view_selected = Signal(str)
    create_requested = Signal(str, str)
    refresh_requested = Signal(str)
    reset_requested = Signal(str, str)
    figure_spec_changed = Signal(str, object)
    trace_moved = Signal(str, str, int)

    _LINE_STYLES = ("-", "--", "-.", ":")
    _MARKERS = ("None", "o", "s", "^", "v", "D", "x", "+", ".")
    _SCALES = ("linear", "log", "symlog", "logit")
    _LEGEND_LOCATIONS = (
        "best",
        "upper right",
        "upper left",
        "lower left",
        "lower right",
        "center left",
        "center right",
        "lower center",
        "upper center",
        "center",
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._syncing = False
        self._draft: FigureDraft | None = None
        self._source: FigureSourceView | None = None
        self._stale = False
        self._available_views: tuple[tuple[str, str], ...] = ()
        self._fonts = tuple(
            sorted(
                {
                    entry.name
                    for entry in font_manager.fontManager.ttflist
                    if isinstance(entry.name, str) and entry.name.strip()
                },
                key=str.casefold,
            )
        )
        self._build_ui()
        self._show_placeholder("Create a figure from the current analysis result.")

    @property
    def active_view_id(self) -> str | None:
        value = self.view_combo.currentData()
        return value if isinstance(value, str) and value else None

    @property
    def draft(self) -> FigureDraft | None:
        return self._draft

    def font_available(self, family: str) -> bool:
        return family in self._fonts

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        back = QPushButton("← Back to Analysis")
        back.clicked.connect(self.back_requested.emit)
        toolbar.addWidget(back)
        self.status_label = QLabel("No figure")
        toolbar.addWidget(self.status_label, 1)
        undo = QPushButton("Undo")
        undo.clicked.connect(self.undo_requested.emit)
        toolbar.addWidget(undo)
        redo = QPushButton("Redo")
        redo.clicked.connect(self.redo_requested.emit)
        toolbar.addWidget(redo)
        save = QPushButton("Save Project")
        save.clicked.connect(self.save_requested.emit)
        toolbar.addWidget(save)
        self.undo_button = undo
        self.redo_button = redo
        self.save_button = save
        root.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_content_panel())
        splitter.addWidget(self._build_preview_panel())
        splitter.addWidget(self._build_properties_panel())
        splitter.setSizes([300, 760, 380])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        root.addWidget(splitter, 1)

        self.continue_export_button = QPushButton("Continue to Export")
        self.continue_export_button.setEnabled(False)
        self.continue_export_button.setToolTip(
            "Figure Package export is implemented in v1.1 Block 5."
        )
        root.addWidget(self.continue_export_button)

    def _build_content_panel(self) -> QWidget:
        box = QGroupBox("CONTENT")
        layout = QVBoxLayout(box)
        row = QHBoxLayout()
        row.addWidget(QLabel("Result"))
        self.view_combo = QComboBox()
        self.view_combo.currentIndexChanged.connect(self._view_changed)
        row.addWidget(self.view_combo, 1)
        layout.addLayout(row)

        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Preset"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(("publication", "compact", "wide"))
        preset_row.addWidget(self.preset_combo, 1)
        layout.addLayout(preset_row)

        self.create_button = QPushButton("Create figure from this result")
        self.create_button.clicked.connect(self._emit_create)
        layout.addWidget(self.create_button)
        self.refresh_button = QPushButton("Refresh from Analysis")
        self.refresh_button.clicked.connect(self._emit_refresh)
        layout.addWidget(self.refresh_button)
        self.reset_button = QPushButton("Reset styling")
        self.reset_button.clicked.connect(self._emit_reset)
        layout.addWidget(self.reset_button)

        layout.addWidget(QLabel("Traces"))
        self.trace_list = QListWidget()
        self.trace_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.trace_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.trace_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.trace_list.itemSelectionChanged.connect(self._selected_trace_changed)
        self.trace_list.itemChanged.connect(self._trace_item_changed)
        self.trace_list.model().rowsMoved.connect(self._trace_rows_moved)
        layout.addWidget(self.trace_list, 1)
        return box

    def _build_preview_panel(self) -> QWidget:
        box = QGroupBox("PUBLICATION PREVIEW")
        self.preview_layout = QVBoxLayout(box)
        self.preview_note = QLabel("Presentation preview")
        self.preview_note.setWordWrap(True)
        self.preview_layout.addWidget(self.preview_note)
        self._canvas: FigureCanvasQTAgg | None = None
        return box

    @staticmethod
    def _spin(
        minimum: float,
        maximum: float,
        value: float,
        *,
        decimals: int = 3,
        step: float = 0.1,
    ) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setDecimals(decimals)
        spin.setSingleStep(step)
        spin.setValue(value)
        return spin

    def _build_properties_panel(self) -> QWidget:
        box = QGroupBox("PROPERTIES")
        layout = QVBoxLayout(box)

        figure_group = QGroupBox("Figure")
        figure_form = QFormLayout(figure_group)
        self.title_edit = QLineEdit()
        self.width_spin = self._spin(0.5, 30.0, 3.5)
        self.height_spin = self._spin(0.5, 30.0, 2.625)
        figure_form.addRow("Title", self.title_edit)
        figure_form.addRow("Width (in)", self.width_spin)
        figure_form.addRow("Height (in)", self.height_spin)
        layout.addWidget(figure_group)

        axis_group = QGroupBox("Axis / display range")
        axis_form = QFormLayout(axis_group)
        self.xlabel_edit = QLineEdit()
        self.ylabel_edit = QLineEdit()
        self.xscale_combo = QComboBox()
        self.xscale_combo.addItems(self._SCALES)
        self.yscale_combo = QComboBox()
        self.yscale_combo.addItems(self._SCALES)
        self.unit_format_combo = QComboBox()
        self.unit_format_combo.addItem("Label (unit)", "parentheses")
        self.unit_format_combo.addItem("Label / unit", "slash")
        self.unit_format_combo.addItem("Label only", "none")
        self.x_auto = QCheckBox("Auto")
        self.y_auto = QCheckBox("Auto")
        self.x_min = self._spin(-1e9, 1e9, 0.0, decimals=6)
        self.x_max = self._spin(-1e9, 1e9, 1.0, decimals=6)
        self.y_min = self._spin(-1e9, 1e9, 0.0, decimals=6)
        self.y_max = self._spin(-1e9, 1e9, 1.0, decimals=6)
        x_range = QWidget()
        x_row = QHBoxLayout(x_range)
        x_row.setContentsMargins(0, 0, 0, 0)
        x_row.addWidget(self.x_auto)
        x_row.addWidget(self.x_min)
        x_row.addWidget(self.x_max)
        y_range = QWidget()
        y_row = QHBoxLayout(y_range)
        y_row.setContentsMargins(0, 0, 0, 0)
        y_row.addWidget(self.y_auto)
        y_row.addWidget(self.y_min)
        y_row.addWidget(self.y_max)
        axis_form.addRow("X label", self.xlabel_edit)
        axis_form.addRow("Y label", self.ylabel_edit)
        axis_form.addRow("X display", x_range)
        axis_form.addRow("Y display", y_range)
        axis_form.addRow("X scale", self.xscale_combo)
        axis_form.addRow("Y scale", self.yscale_combo)
        axis_form.addRow("Unit style", self.unit_format_combo)
        layout.addWidget(axis_group)

        legend_group = QGroupBox("Legend")
        legend_form = QFormLayout(legend_group)
        self.legend_combo = QComboBox()
        self.legend_combo.addItem("Auto", None)
        self.legend_combo.addItem("Show", True)
        self.legend_combo.addItem("Hide", False)
        self.legend_location = QComboBox()
        self.legend_location.addItems(self._LEGEND_LOCATIONS)
        legend_form.addRow("Visibility", self.legend_combo)
        legend_form.addRow("Location", self.legend_location)
        layout.addWidget(legend_group)

        typography_group = QGroupBox("Typography")
        typography_form = QFormLayout(typography_group)
        self.font_combo = QComboBox()
        self.font_combo.addItems(self._fonts)
        self.axis_label_size = self._spin(1.0, 72.0, 8.0, decimals=1, step=0.5)
        self.tick_label_size = self._spin(1.0, 72.0, 7.0, decimals=1, step=0.5)
        self.legend_font_size = self._spin(1.0, 72.0, 7.0, decimals=1, step=0.5)
        typography_form.addRow("Font family", self.font_combo)
        typography_form.addRow("Axis label size", self.axis_label_size)
        typography_form.addRow("Tick size", self.tick_label_size)
        typography_form.addRow("Legend size", self.legend_font_size)
        layout.addWidget(typography_group)

        trace_group = QGroupBox("Selected trace")
        trace_form = QFormLayout(trace_group)
        self.trace_label = QLineEdit()
        self.color_button = QPushButton("Choose…")
        self.line_style_combo = QComboBox()
        self.line_style_combo.addItems(self._LINE_STYLES)
        self.line_width_spin = self._spin(0.0, 20.0, 1.2, decimals=2, step=0.1)
        self.marker_combo = QComboBox()
        self.marker_combo.addItems(self._MARKERS)
        self.marker_size_spin = self._spin(0.0, 50.0, 4.0, decimals=2, step=0.5)
        trace_form.addRow("Label", self.trace_label)
        trace_form.addRow("Color", self.color_button)
        trace_form.addRow("Line style", self.line_style_combo)
        trace_form.addRow("Line width", self.line_width_spin)
        trace_form.addRow("Marker", self.marker_combo)
        trace_form.addRow("Marker size", self.marker_size_spin)
        layout.addWidget(trace_group)
        layout.addStretch(1)

        self._property_widgets: Sequence[QWidget] = (
            self.title_edit,
            self.width_spin,
            self.height_spin,
            self.xlabel_edit,
            self.ylabel_edit,
            self.x_auto,
            self.x_min,
            self.x_max,
            self.y_auto,
            self.y_min,
            self.y_max,
            self.xscale_combo,
            self.yscale_combo,
            self.unit_format_combo,
            self.legend_combo,
            self.legend_location,
            self.font_combo,
            self.axis_label_size,
            self.tick_label_size,
            self.legend_font_size,
            self.trace_label,
            self.color_button,
            self.line_style_combo,
            self.line_width_spin,
            self.marker_combo,
            self.marker_size_spin,
        )
        self._trace_property_widgets: Sequence[QWidget] = (
            self.trace_label,
            self.color_button,
            self.line_style_combo,
            self.line_width_spin,
            self.marker_combo,
            self.marker_size_spin,
        )
        self._connect_property_signals()
        return box

    def _connect_property_signals(self) -> None:
        self.title_edit.editingFinished.connect(
            lambda: self._update_spec(title=self.title_edit.text() or None)
        )
        self.xlabel_edit.editingFinished.connect(
            lambda: self._update_spec(xlabel=self.xlabel_edit.text() or None)
        )
        self.ylabel_edit.editingFinished.connect(
            lambda: self._update_spec(ylabel=self.ylabel_edit.text() or None)
        )
        self.width_spin.editingFinished.connect(
            lambda: self._update_layout(figure_width_in=self.width_spin.value())
        )
        self.height_spin.editingFinished.connect(
            lambda: self._update_layout(figure_height_in=self.height_spin.value())
        )
        self.xscale_combo.currentTextChanged.connect(
            lambda value: self._update_spec(xscale=value)
        )
        self.yscale_combo.currentTextChanged.connect(
            lambda value: self._update_spec(yscale=value)
        )
        self.unit_format_combo.currentIndexChanged.connect(
            lambda _index: self._update_style(
                axis_unit_format=self.unit_format_combo.currentData()
            )
        )
        self.legend_combo.currentIndexChanged.connect(
            lambda _index: self._update_spec(show_legend=self.legend_combo.currentData())
        )
        self.legend_location.currentTextChanged.connect(
            lambda value: self._update_style(legend_location=value)
        )
        self.font_combo.currentTextChanged.connect(
            lambda value: self._update_style(font_family=value)
        )
        self.axis_label_size.editingFinished.connect(
            lambda: self._update_style(axis_label_size=self.axis_label_size.value())
        )
        self.tick_label_size.editingFinished.connect(
            lambda: self._update_style(tick_label_size=self.tick_label_size.value())
        )
        self.legend_font_size.editingFinished.connect(
            lambda: self._update_style(legend_font_size=self.legend_font_size.value())
        )
        self.x_auto.toggled.connect(lambda _checked: self._update_display_range("x"))
        self.y_auto.toggled.connect(lambda _checked: self._update_display_range("y"))
        self.x_min.editingFinished.connect(lambda: self._update_display_range("x"))
        self.x_max.editingFinished.connect(lambda: self._update_display_range("x"))
        self.y_min.editingFinished.connect(lambda: self._update_display_range("y"))
        self.y_max.editingFinished.connect(lambda: self._update_display_range("y"))
        self.trace_label.editingFinished.connect(self._update_selected_trace)
        self.color_button.clicked.connect(self._choose_trace_color)
        self.line_style_combo.currentTextChanged.connect(
            lambda _value: self._update_selected_trace()
        )
        self.line_width_spin.editingFinished.connect(self._update_selected_trace)
        self.marker_combo.currentTextChanged.connect(
            lambda _value: self._update_selected_trace()
        )
        self.marker_size_spin.editingFinished.connect(self._update_selected_trace)

    def _view_changed(self, _index: int) -> None:
        if self._syncing:
            return
        view_id = self.active_view_id
        if view_id is not None:
            self.view_selected.emit(view_id)

    def _emit_create(self) -> None:
        view_id = self.active_view_id
        if view_id is not None:
            self.create_requested.emit(view_id, self.preset_combo.currentText())

    def _emit_refresh(self) -> None:
        view_id = self.active_view_id
        if view_id is not None:
            self.refresh_requested.emit(view_id)

    def _emit_reset(self) -> None:
        view_id = self.active_view_id
        if view_id is not None:
            self.reset_requested.emit(view_id, self.preset_combo.currentText())

    def _selected_trace_id(self) -> str | None:
        item = self.trace_list.currentItem()
        if item is None:
            return None
        value = item.data(Qt.ItemDataRole.UserRole)
        return value if isinstance(value, str) and value else None

    def _trace_item_changed(self, item: QListWidgetItem) -> None:
        if self._syncing or self._draft is None or self._stale:
            return
        trace_id = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(trace_id, str) or not trace_id:
            return
        visible = item.checkState() == Qt.CheckState.Checked
        spec = self._draft.figure_spec.with_series_style(trace_id, visible=visible)
        self.figure_spec_changed.emit(self._draft.view_id, spec)

    def _trace_rows_moved(
        self,
        source_parent: object,
        source_start: int,
        source_end: int,
        destination_parent: object,
        destination_row: int,
    ) -> None:
        del source_parent, destination_parent
        if self._syncing or self._draft is None or source_start != source_end:
            return
        new_index = destination_row - 1 if destination_row > source_start else destination_row
        QTimer.singleShot(0, lambda: self._emit_trace_move(new_index))

    def _emit_trace_move(self, new_index: int) -> None:
        if self._draft is None or not 0 <= new_index < self.trace_list.count():
            return
        item = self.trace_list.item(new_index)
        trace_id = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(trace_id, str) and trace_id:
            self.trace_moved.emit(self._draft.view_id, trace_id, new_index)

    def _selected_trace_changed(self) -> None:
        self._sync_trace_properties()

    def _choose_trace_color(self) -> None:
        if self._draft is None or self._stale:
            return
        trace_id = self._selected_trace_id()
        if trace_id is None:
            return
        style = self._draft.figure_spec.series_styles.get(trace_id, SeriesStyle())
        initial = QColor(style.color) if style.color else QColor("black")
        selected = QColorDialog.getColor(initial, self, "Trace color")
        if not selected.isValid():
            return
        spec = self._draft.figure_spec.with_series_style(
            trace_id,
            color=selected.name(),
        )
        self.figure_spec_changed.emit(self._draft.view_id, spec)

    def _update_selected_trace(self) -> None:
        if self._syncing or self._draft is None or self._stale:
            return
        trace_id = self._selected_trace_id()
        if trace_id is None:
            return
        marker_text = self.marker_combo.currentText()
        marker = None if marker_text == "None" else marker_text
        try:
            spec = self._draft.figure_spec.with_series_style(
                trace_id,
                label=self.trace_label.text(),
                line_style=self.line_style_combo.currentText(),
                line_width=self.line_width_spin.value(),
                marker=marker,
                marker_size=self.marker_size_spin.value(),
            )
        except (TypeError, ValueError, VisualizationError) as exc:
            self.preview_note.setText(f"Invalid presentation value: {exc}")
            return
        self.figure_spec_changed.emit(self._draft.view_id, spec)

    def _emit_candidate(self, spec: FigureSpec) -> None:
        if self._draft is None or self._stale or self._syncing:
            return
        self.figure_spec_changed.emit(self._draft.view_id, spec)

    def _update_spec(self, **changes: object) -> None:
        if self._draft is None or self._stale or self._syncing:
            return
        try:
            self._emit_candidate(self._draft.figure_spec.updated(**changes))
        except (TypeError, ValueError, VisualizationError) as exc:
            self.preview_note.setText(f"Invalid presentation value: {exc}")

    def _update_layout(self, **changes: object) -> None:
        if self._draft is None or self._stale or self._syncing:
            return
        try:
            self._emit_candidate(self._draft.figure_spec.with_layout(**changes))
        except (TypeError, ValueError, VisualizationError) as exc:
            self.preview_note.setText(f"Invalid presentation value: {exc}")

    def _update_style(self, **changes: object) -> None:
        if self._draft is None or self._stale or self._syncing:
            return
        try:
            self._emit_candidate(self._draft.figure_spec.with_style(**changes))
        except (TypeError, ValueError, VisualizationError) as exc:
            self.preview_note.setText(f"Invalid presentation value: {exc}")

    def _update_display_range(self, axis: str) -> None:
        if self._draft is None or self._stale or self._syncing:
            return
        if axis == "x":
            limits = (
                None
                if self.x_auto.isChecked()
                else (self.x_min.value(), self.x_max.value())
            )
            self._update_spec(xlim=limits)
        else:
            limits = (
                None
                if self.y_auto.isChecked()
                else (self.y_min.value(), self.y_max.value())
            )
            self._update_spec(ylim=limits)

    def _source_bounds(self, axis: str) -> tuple[float, float]:
        if self._source is None:
            return (0.0, 1.0)
        arrays = [item.x if axis == "x" else item.y for item in self._source.series]
        values = np.concatenate(tuple(np.asarray(item, dtype=float) for item in arrays))
        finite = values[np.isfinite(values)]
        if finite.size == 0:
            return (0.0, 1.0)
        lower = float(np.min(finite))
        upper = float(np.max(finite))
        if lower == upper:
            upper = lower + 1.0
        return lower, upper

    def _sync_trace_properties(self) -> None:
        self._syncing = True
        try:
            trace_id = self._selected_trace_id()
            enabled = (
                trace_id is not None and self._draft is not None and not self._stale
            )
            for widget in self._trace_property_widgets:
                widget.setEnabled(enabled)
            if not enabled or self._draft is None or trace_id is None:
                self.trace_label.clear()
                return
            style = self._draft.figure_spec.series_styles.get(trace_id, SeriesStyle())
            self.trace_label.setText(style.label or "")
            if style.color:
                self.color_button.setText(style.color)
            else:
                self.color_button.setText("Choose…")
            self.line_style_combo.setCurrentText(
                style.line_style or self._draft.figure_spec.style.line_style
            )
            self.line_width_spin.setValue(
                self._draft.figure_spec.style.line_width
                if style.line_width is None
                else style.line_width
            )
            marker = style.marker
            if marker is None:
                marker = self._draft.figure_spec.style.marker
            self.marker_combo.setCurrentText("None" if marker is None else marker)
            self.marker_size_spin.setValue(
                self._draft.figure_spec.style.marker_size
                if style.marker_size is None
                else style.marker_size
            )
        finally:
            self._syncing = False

    def _sync_properties(self) -> None:
        self._syncing = True
        try:
            draft = self._draft
            enabled = draft is not None and not self._stale
            for widget in self._property_widgets:
                widget.setEnabled(enabled)
            self.reset_button.setEnabled(enabled)
            if draft is None:
                return
            spec = draft.figure_spec
            self.title_edit.setText(spec.title or "")
            self.width_spin.setValue(spec.layout.figure_width_in)
            self.height_spin.setValue(spec.layout.figure_height_in)
            self.xlabel_edit.setText(spec.xlabel or "")
            self.ylabel_edit.setText(spec.ylabel or "")
            self.xscale_combo.setCurrentText(spec.xscale)
            self.yscale_combo.setCurrentText(spec.yscale)
            unit_index = self.unit_format_combo.findData(spec.style.axis_unit_format)
            self.unit_format_combo.setCurrentIndex(max(0, unit_index))
            legend_index = self.legend_combo.findData(spec.show_legend)
            self.legend_combo.setCurrentIndex(max(0, legend_index))
            self.legend_location.setCurrentText(spec.style.legend_location)
            if self.font_combo.findText(spec.style.font_family) < 0:
                self.font_combo.insertItem(0, spec.style.font_family)
            self.font_combo.setCurrentText(spec.style.font_family)
            self.axis_label_size.setValue(spec.style.axis_label_size)
            self.tick_label_size.setValue(spec.style.tick_label_size)
            self.legend_font_size.setValue(spec.style.legend_font_size)
            x_default = self._source_bounds("x")
            y_default = self._source_bounds("y")
            self.x_auto.setChecked(spec.xlim is None)
            self.y_auto.setChecked(spec.ylim is None)
            xlim = x_default if spec.xlim is None else spec.xlim
            ylim = y_default if spec.ylim is None else spec.ylim
            self.x_min.setValue(xlim[0])
            self.x_max.setValue(xlim[1])
            self.y_min.setValue(ylim[0])
            self.y_max.setValue(ylim[1])
            self.x_min.setEnabled(enabled and not self.x_auto.isChecked())
            self.x_max.setEnabled(enabled and not self.x_auto.isChecked())
            self.y_min.setEnabled(enabled and not self.y_auto.isChecked())
            self.y_max.setEnabled(enabled and not self.y_auto.isChecked())
        finally:
            self._syncing = False
        self._sync_trace_properties()

    def _rebuild_traces(self) -> None:
        selected = self._selected_trace_id()
        self._syncing = True
        try:
            self.trace_list.clear()
            if self._draft is None:
                return
            for index, trace_id in enumerate(self._draft.trace_order):
                style = self._draft.figure_spec.series_styles.get(trace_id, SeriesStyle())
                label = style.label or trace_id
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, trace_id)
                item.setCheckState(
                    Qt.CheckState.Checked if style.visible else Qt.CheckState.Unchecked
                )
                item.setFlags(
                    item.flags()
                    | Qt.ItemFlag.ItemIsUserCheckable
                    | Qt.ItemFlag.ItemIsDragEnabled
                )
                self.trace_list.addItem(item)
                if trace_id == selected:
                    self.trace_list.setCurrentRow(index)
            if self.trace_list.currentRow() < 0 and self.trace_list.count():
                self.trace_list.setCurrentRow(0)
        finally:
            self._syncing = False
        self._sync_trace_properties()

    def apply_state(
        self,
        *,
        available_views: Sequence[tuple[str, str]],
        active_view_id: str,
        draft: FigureDraft | None,
        source: FigureSourceView | None,
        stale: bool,
        can_undo: bool,
        can_redo: bool,
        is_dirty: bool,
    ) -> None:
        self._available_views = tuple(available_views)
        self._draft = draft
        self._source = source
        self._stale = stale
        self._syncing = True
        try:
            self.view_combo.clear()
            for view_id, label in self._available_views:
                self.view_combo.addItem(label, view_id)
            index = self.view_combo.findData(active_view_id)
            self.view_combo.setCurrentIndex(max(0, index))
        finally:
            self._syncing = False
        self.undo_button.setEnabled(can_undo)
        self.redo_button.setEnabled(can_redo)
        self.save_button.setEnabled(True)
        self.create_button.setEnabled(draft is None and source is not None)
        self.refresh_button.setEnabled(
            draft is not None and source is not None and stale
        )
        self.trace_list.setEnabled(draft is not None and not stale)
        if draft is None:
            self.status_label.setText("No figure draft for this result")
        elif stale:
            self.status_label.setText("Analysis changed — refresh this figure")
        else:
            marker = " · Unsaved changes" if is_dirty else ""
            self.status_label.setText(f"Figure up to date{marker}")
        self._rebuild_traces()
        self._sync_properties()

    def set_preview_figure(self, figure: Figure) -> None:
        if self._canvas is not None:
            self.preview_layout.removeWidget(self._canvas)
            self._canvas.setParent(None)
            self._canvas.deleteLater()
        self._canvas = FigureCanvasQTAgg(figure)
        self.preview_layout.addWidget(self._canvas, 1)
        self._canvas.draw_idle()
        self.preview_note.setText(
            "Publication preview · display range and styling do not modify scientific arrays."
        )

    def _show_placeholder(self, message: str) -> None:
        figure = Figure(figsize=(6.5, 4.5))
        ax = figure.add_subplot(111)
        ax.set_axis_off()
        ax.text(0.5, 0.5, message, ha="center", va="center", transform=ax.transAxes)
        self.set_preview_figure(figure)
        self.preview_note.setText(message)

    def set_preview_message(self, message: str) -> None:
        self._show_placeholder(message)


__all__ = ["FigureWorkbenchPage"]
