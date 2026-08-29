"""Qt data-intake dialogs for explicit v1.1 tabular mapping."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from catalysis_workbench.application import (
    DataSeriesSpec,
    SourceSpec,
    TabularMappingSpec,
    source_spec_from_file,
)
from catalysis_workbench.io.tabular_preview import TabularPreview, inspect_tabular


@dataclass(slots=True)
class _ImportDraft:
    path: Path
    source: SourceSpec
    preview: TabularPreview | None
    preview_error: str | None
    display_name: str
    x_index: int
    y_index: int
    x_role: str
    y_role: str
    x_unit: str
    y_unit: str
    x_reference: str
    delimiter: str | None
    sheet: str | None
    header: int | None
    skip_rows: int
    encoding: str | None
    confirmed: bool = False

    def mapping(self) -> TabularMappingSpec:
        if self.preview is None:
            raise ValueError(self.preview_error or f"cannot preview {self.path.name!r}")
        if self.x_index < 0 or self.x_index >= len(self.preview.columns):
            raise ValueError("choose a valid X column")
        if self.y_index < 0 or self.y_index >= len(self.preview.columns):
            raise ValueError("choose a valid Y column")
        if self.x_index == self.y_index:
            raise ValueError("X and Y columns must be different")
        return TabularMappingSpec(
            sheet=self.sheet,
            delimiter=self.delimiter,
            header=self.header,
            skip_rows=self.skip_rows,
            encoding=self.encoding,
            x_column=self.x_index,
            y_column=self.y_index,
            x_role=self.x_role.strip(),
            y_role=self.y_role.strip(),
            x_unit=self.x_unit.strip() or None,
            y_unit=self.y_unit.strip() or None,
            x_reference=self.x_reference.strip() or None,
        )

    def series_spec(self) -> DataSeriesSpec:
        return DataSeriesSpec(
            source=self.source,
            mapping=self.mapping(),
            display_name=self.display_name.strip(),
        )


def _task_roles(task_id: str) -> tuple[str, str]:
    if task_id == "lsv":
        return "potential", "current"
    if task_id == "fe_partial_current":
        return "potential", "response"
    return "x", "y"


def _column_index(preview: TabularPreview, reference: str | int) -> int:
    if type(reference) is int:
        return reference
    for column in preview.columns:
        if column.name == reference:
            return column.index
    raise ValueError(f"mapped column {reference!r} is not present in the source preview")


def _initial_draft(
    path: str | Path,
    *,
    task_id: str,
    existing: DataSeriesSpec | None = None,
) -> _ImportDraft:
    source_path = Path(path).absolute()
    source = source_spec_from_file(source_path)
    if existing is not None and source.content_sha256 != existing.source.content_sha256:
        raise ValueError(f"source file changed since mapping: {source_path.name!r}")

    x_role, y_role = _task_roles(task_id)
    sheet = existing.mapping.sheet if existing is not None else None
    delimiter = existing.mapping.delimiter if existing is not None else None
    header = existing.mapping.header if existing is not None else 0
    skip_rows = existing.mapping.skip_rows if existing is not None else 0
    encoding = existing.mapping.encoding if existing is not None else "utf-8"
    try:
        preview = inspect_tabular(
            source_path,
            sheet=sheet,
            delimiter=delimiter,
            header=header,
            skip_rows=skip_rows,
            encoding=encoding,
            max_rows=100,
        )
        error = None
        sheet = preview.selected_sheet
        delimiter = preview.resolved_delimiter
        encoding = preview.encoding
        if existing is None:
            x_index = 0
            y_index = 1 if len(preview.columns) > 1 else -1
            x_unit = (preview.columns[0].inferred_unit or "") if preview.columns else ""
            y_unit = preview.columns[y_index].inferred_unit or "" if y_index >= 0 else ""
            display_name = source_path.stem
            x_reference = ""
        else:
            x_index = _column_index(preview, existing.mapping.x_column)
            y_index = _column_index(preview, existing.mapping.y_column)
            x_role = existing.mapping.x_role
            y_role = existing.mapping.y_role
            x_unit = existing.mapping.x_unit or ""
            y_unit = existing.mapping.y_unit or ""
            x_reference = existing.mapping.x_reference or ""
            display_name = existing.display_name
    except Exception as exc:
        preview = None
        error = str(exc)
        x_index = -1
        y_index = -1
        x_unit = ""
        y_unit = ""
        x_reference = ""
        display_name = existing.display_name if existing is not None else source_path.stem

    return _ImportDraft(
        path=source_path,
        source=source,
        preview=preview,
        preview_error=error,
        display_name=display_name,
        x_index=x_index,
        y_index=y_index,
        x_role=x_role,
        y_role=y_role,
        x_unit=x_unit,
        y_unit=y_unit,
        x_reference=x_reference,
        delimiter=delimiter,
        sheet=sheet,
        header=header,
        skip_rows=skip_rows,
        encoding=encoding,
        confirmed=existing is not None,
    )


class ImportDataDialog(QDialog):
    """Preview one or more files and require explicit mapping confirmation."""

    def __init__(
        self,
        paths: tuple[str | Path, ...] | list[str | Path],
        *,
        task_id: str,
        existing_spec: DataSeriesSpec | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        if not paths:
            raise ValueError("choose at least one data file")
        if existing_spec is not None and len(paths) != 1:
            raise ValueError("editing an existing mapping requires exactly one source file")
        self._edit_mode = existing_spec is not None
        self._drafts = [
            _initial_draft(
                path,
                task_id=task_id,
                existing=existing_spec if index == 0 else None,
            )
            for index, path in enumerate(paths)
        ]
        self._current_index = -1
        self._loading = False
        self.setWindowTitle("Edit data mapping" if self._edit_mode else "Import Data")
        self.resize(1120, 700)
        self._build_ui()
        self.file_list.setCurrentRow(0)
        self._refresh_all_statuses()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        intro = QLabel(
            "Confirm which columns and scientific meanings should be used. "
            "No scientific transformation is applied during import."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        files_box = QGroupBox("FILES")
        files_layout = QVBoxLayout(files_box)
        self.file_list = QListWidget()
        self.file_list.currentRowChanged.connect(self._select_file)
        files_layout.addWidget(self.file_list, 1)
        for draft in self._drafts:
            item = QListWidgetItem(draft.path.name)
            item.setToolTip(str(draft.path))
            self.file_list.addItem(item)
        splitter.addWidget(files_box)

        preview_box = QGroupBox("PREVIEW")
        preview_layout = QVBoxLayout(preview_box)
        self.preview_status = QLabel()
        self.preview_status.setWordWrap(True)
        preview_layout.addWidget(self.preview_status)
        self.preview_table = QTableWidget()
        self.preview_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.preview_table.setAlternatingRowColors(True)
        preview_layout.addWidget(self.preview_table, 1)
        splitter.addWidget(preview_box)

        mapping_box = QGroupBox("MAPPING")
        mapping_layout = QVBoxLayout(mapping_box)
        form = QFormLayout()
        self.series_name = QLineEdit()
        self.series_name.textEdited.connect(self._mapping_edited)
        form.addRow("Series name", self.series_name)

        self.sheet_combo = QComboBox()
        self.sheet_combo.currentIndexChanged.connect(self._sheet_changed)
        form.addRow("Excel sheet", self.sheet_combo)
        self.delimiter_edit = QLineEdit()
        self.delimiter_edit.setPlaceholderText("Detected delimiter")
        self.delimiter_edit.textEdited.connect(self._parser_edited)
        form.addRow("Text delimiter", self.delimiter_edit)
        self.reload_button = QPushButton("Reload preview")
        self.reload_button.clicked.connect(self.reload_current_preview)
        form.addRow("", self.reload_button)

        self.x_column = QComboBox()
        self.x_column.currentIndexChanged.connect(self._mapping_edited)
        form.addRow("X column", self.x_column)
        self.x_role = QLineEdit()
        self.x_role.textEdited.connect(self._mapping_edited)
        form.addRow("X meaning", self.x_role)
        self.x_unit = QLineEdit()
        self.x_unit.textEdited.connect(self._mapping_edited)
        form.addRow("X unit", self.x_unit)
        self.x_reference = QLineEdit()
        self.x_reference.setPlaceholderText("Optional, e.g. RHE")
        self.x_reference.textEdited.connect(self._mapping_edited)
        form.addRow("X reference", self.x_reference)

        self.y_column = QComboBox()
        self.y_column.currentIndexChanged.connect(self._mapping_edited)
        form.addRow("Y column", self.y_column)
        self.y_role = QLineEdit()
        self.y_role.textEdited.connect(self._mapping_edited)
        form.addRow("Y meaning", self.y_role)
        self.y_unit = QLineEdit()
        self.y_unit.textEdited.connect(self._mapping_edited)
        form.addRow("Y unit", self.y_unit)
        mapping_layout.addLayout(form)

        self.mapping_status = QLabel()
        self.mapping_status.setWordWrap(True)
        mapping_layout.addWidget(self.mapping_status)
        self.confirm_button = QPushButton("Confirm this mapping")
        self.confirm_button.clicked.connect(self.confirm_current_mapping)
        mapping_layout.addWidget(self.confirm_button)
        self.apply_button = QPushButton("Apply this mapping to compatible files")
        self.apply_button.clicked.connect(self.apply_current_mapping_to_compatible)
        self.apply_button.setVisible(not self._edit_mode and len(self._drafts) > 1)
        mapping_layout.addWidget(self.apply_button)
        mapping_layout.addStretch(1)
        splitter.addWidget(mapping_box)
        splitter.setSizes([240, 560, 320])
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 1)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok_button.setText("Save mapping" if self._edit_mode else "Add data")
        self.buttons.accepted.connect(self._accept_if_ready)
        self.buttons.rejected.connect(self.reject)
        root.addWidget(self.buttons)

    def _capture_current(self) -> None:
        if self._loading or self._current_index < 0:
            return
        draft = self._drafts[self._current_index]
        draft.display_name = self.series_name.text().strip()
        draft.x_index = self.x_column.currentData() if self.x_column.currentIndex() >= 0 else -1
        draft.y_index = self.y_column.currentData() if self.y_column.currentIndex() >= 0 else -1
        draft.x_role = self.x_role.text().strip()
        draft.y_role = self.y_role.text().strip()
        draft.x_unit = self.x_unit.text().strip()
        draft.y_unit = self.y_unit.text().strip()
        draft.x_reference = self.x_reference.text().strip()
        if draft.source.source_format == "delimited_text":
            text = self.delimiter_edit.text()
            draft.delimiter = text if text else None
        if draft.source.source_format == "excel" and self.sheet_combo.currentIndex() >= 0:
            draft.sheet = self.sheet_combo.currentText()
        self._refresh_status(self._current_index)

    def _select_file(self, index: int) -> None:
        self._capture_current()
        self._current_index = index
        if index >= 0:
            self._load_controls(self._drafts[index])

    def _load_controls(self, draft: _ImportDraft) -> None:
        self._loading = True
        try:
            self.series_name.setText(draft.display_name)
            self.series_name.setEnabled(not self._edit_mode)
            self.sheet_combo.clear()
            if draft.preview is not None:
                self.sheet_combo.addItems(draft.preview.available_sheets)
                if draft.sheet is not None:
                    position = self.sheet_combo.findText(draft.sheet)
                    if position >= 0:
                        self.sheet_combo.setCurrentIndex(position)
            self.sheet_combo.setEnabled(draft.source.source_format == "excel")
            self.delimiter_edit.setText(draft.delimiter or "")
            self.delimiter_edit.setEnabled(draft.source.source_format == "delimited_text")
            self.x_column.clear()
            self.y_column.clear()
            if draft.preview is not None:
                for column in draft.preview.columns:
                    label = f"{column.index}: {column.name}"
                    if column.inferred_unit:
                        label += f" [{column.inferred_unit}]"
                    self.x_column.addItem(label, column.index)
                    self.y_column.addItem(label, column.index)
                self._set_combo_data(self.x_column, draft.x_index)
                self._set_combo_data(self.y_column, draft.y_index)
            self.x_role.setText(draft.x_role)
            self.y_role.setText(draft.y_role)
            self.x_unit.setText(draft.x_unit)
            self.y_unit.setText(draft.y_unit)
            self.x_reference.setText(draft.x_reference)
            self._populate_preview_table(draft)
        finally:
            self._loading = False
        self._refresh_status(self._current_index)

    @staticmethod
    def _set_combo_data(combo: QComboBox, wanted: int) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == wanted:
                combo.setCurrentIndex(index)
                return
        combo.setCurrentIndex(-1)

    def _populate_preview_table(self, draft: _ImportDraft) -> None:
        self.preview_table.clear()
        if draft.preview is None:
            self.preview_table.setRowCount(0)
            self.preview_table.setColumnCount(0)
            self.preview_status.setText(draft.preview_error or "Preview unavailable")
            return
        preview = draft.preview
        self.preview_table.setColumnCount(len(preview.columns))
        self.preview_table.setHorizontalHeaderLabels(
            [
                column.name + (f" [{column.inferred_unit}]" if column.inferred_unit else "")
                for column in preview.columns
            ]
        )
        self.preview_table.setRowCount(len(preview.rows))
        for row_index, row in enumerate(preview.rows):
            for column_index, value in enumerate(row):
                self.preview_table.setItem(
                    row_index,
                    column_index,
                    QTableWidgetItem("" if value is None else value),
                )
        detail = f"{len(preview.rows)} preview rows"
        if preview.truncated:
            detail += " (preview truncated)"
        self.preview_status.setText(detail)
        self.preview_table.resizeColumnsToContents()

    def _mapping_edited(self, *args: object) -> None:
        if self._loading or self._current_index < 0:
            return
        self._drafts[self._current_index].confirmed = False
        self._capture_current()

    def _parser_edited(self, *args: object) -> None:
        if self._loading or self._current_index < 0:
            return
        self._drafts[self._current_index].confirmed = False
        self._capture_current()
        self.mapping_status.setText("Parser changed. Reload the preview before confirming.")

    def _sheet_changed(self, *args: object) -> None:
        if self._loading or self._current_index < 0:
            return
        self._drafts[self._current_index].confirmed = False
        self._capture_current()
        self.reload_current_preview()

    def reload_current_preview(self) -> None:
        if self._current_index < 0:
            return
        self._capture_current()
        draft = self._drafts[self._current_index]
        try:
            preview = inspect_tabular(
                draft.path,
                sheet=draft.sheet if draft.source.source_format == "excel" else None,
                delimiter=draft.delimiter if draft.source.source_format == "delimited_text" else None,
                header=draft.header,
                skip_rows=draft.skip_rows,
                encoding=draft.encoding,
                max_rows=100,
            )
        except Exception as exc:
            draft.preview = None
            draft.preview_error = str(exc)
            draft.confirmed = False
        else:
            draft.preview = preview
            draft.preview_error = None
            draft.sheet = preview.selected_sheet
            draft.delimiter = preview.resolved_delimiter
            draft.encoding = preview.encoding
            if draft.x_index < 0 or draft.x_index >= len(preview.columns):
                draft.x_index = 0 if preview.columns else -1
            if draft.y_index < 0 or draft.y_index >= len(preview.columns):
                draft.y_index = 1 if len(preview.columns) > 1 else -1
            draft.confirmed = False
        self._load_controls(draft)

    def _draft_error(self, draft: _ImportDraft) -> str | None:
        if draft.preview is None:
            return draft.preview_error or "preview unavailable"
        try:
            draft.series_spec()
        except Exception as exc:
            return str(exc)
        return None

    def _refresh_status(self, index: int) -> None:
        if index < 0:
            return
        draft = self._drafts[index]
        error = self._draft_error(draft)
        item = self.file_list.item(index)
        if error is not None:
            item.setText(f"✕ {draft.path.name}")
            item.setToolTip(error)
            if index == self._current_index:
                self.mapping_status.setText(error)
        elif draft.confirmed:
            item.setText(f"✓ {draft.path.name}")
            item.setToolTip("Mapping confirmed")
            if index == self._current_index:
                self.mapping_status.setText("✓ Mapping confirmed")
        else:
            item.setText(f"⚠ {draft.path.name}")
            item.setToolTip("Review and confirm this mapping")
            if index == self._current_index:
                self.mapping_status.setText("Review and confirm this mapping.")
        self._update_ok_button()

    def _refresh_all_statuses(self) -> None:
        for index in range(len(self._drafts)):
            self._refresh_status(index)

    def _update_ok_button(self) -> None:
        button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        button.setEnabled(
            all(draft.confirmed and self._draft_error(draft) is None for draft in self._drafts)
        )

    def confirm_current_mapping(self) -> bool:
        if self._current_index < 0:
            return False
        self._capture_current()
        draft = self._drafts[self._current_index]
        error = self._draft_error(draft)
        if error is not None:
            draft.confirmed = False
            self._refresh_status(self._current_index)
            return False
        draft.confirmed = True
        self._refresh_status(self._current_index)
        return True

    def apply_current_mapping_to_compatible(self) -> int:
        if self._current_index < 0 or not self.confirm_current_mapping():
            return 0
        source = self._drafts[self._current_index]
        applied = 0
        for index, draft in enumerate(self._drafts):
            if index == self._current_index or draft.preview is None:
                continue
            if source.x_index >= len(draft.preview.columns) or source.y_index >= len(draft.preview.columns):
                continue
            draft.x_index = source.x_index
            draft.y_index = source.y_index
            draft.x_role = source.x_role
            draft.y_role = source.y_role
            draft.x_unit = source.x_unit
            draft.y_unit = source.y_unit
            draft.x_reference = source.x_reference
            draft.confirmed = self._draft_error(draft) is None
            if draft.confirmed:
                applied += 1
            self._refresh_status(index)
        self._load_controls(self._drafts[self._current_index])
        return applied

    def mapped_items(self) -> tuple[tuple[DataSeriesSpec, Path], ...]:
        self._capture_current()
        result: list[tuple[DataSeriesSpec, Path]] = []
        seen: set[str] = set()
        for draft in self._drafts:
            if not draft.confirmed:
                raise ValueError(f"mapping is not confirmed for {draft.path.name!r}")
            spec = draft.series_spec()
            if spec.data_id in seen:
                raise ValueError(f"the selected files produce duplicate scientific input {spec.data_id}")
            seen.add(spec.data_id)
            result.append((spec, draft.path))
        return tuple(result)

    def edited_mapping(self) -> TabularMappingSpec:
        if not self._edit_mode:
            raise RuntimeError("edited_mapping is only available in edit mode")
        return self.mapped_items()[0][0].mapping

    def _accept_if_ready(self) -> None:
        try:
            self.mapped_items()
        except Exception as exc:
            self.mapping_status.setText(str(exc))
            return
        self.accept()


class SeriesPreviewDialog(QDialog):
    """Read-only bounded preview of one materialized scientific series."""

    def __init__(self, materialized: object, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        value = materialized.value
        self.setWindowTitle(value.label or "Data preview")
        self.resize(720, 560)
        root = QVBoxLayout(self)
        root.addWidget(QLabel(f"{value.n_points} points · input {materialized.input_sha256[:12]}…"))
        table = QTableWidget()
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setColumnCount(2)
        x_label = value.x_axis.label or value.x_axis.name
        y_label = value.y_axis.label or value.y_axis.name
        if value.x_axis.unit:
            x_label += f" [{value.x_axis.unit}]"
        if value.y_axis.unit:
            y_label += f" [{value.y_axis.unit}]"
        table.setHorizontalHeaderLabels([x_label, y_label])
        count = min(value.n_points, 500)
        table.setRowCount(count)
        for index in range(count):
            table.setItem(index, 0, QTableWidgetItem(str(value.x[index])))
            table.setItem(index, 1, QTableWidgetItem(str(value.y[index])))
        table.resizeColumnsToContents()
        root.addWidget(table, 1)
        if value.n_points > count:
            root.addWidget(QLabel(f"Showing first {count} rows; scientific data are not truncated."))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)


__all__ = ["ImportDataDialog", "SeriesPreviewDialog"]