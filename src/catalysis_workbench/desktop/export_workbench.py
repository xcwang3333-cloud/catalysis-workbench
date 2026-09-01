"""Qt Figure Package Export page for the v1.1 task-first workbench."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from catalysis_workbench.application import FigurePackageOptions


class FigurePackageExportPage(QWidget):
    """Ordinary-user export surface with explicit preflight and no provenance IDs."""

    back_requested = Signal()
    browse_requested = Signal()
    save_requested = Signal()
    export_requested = Signal(str, object)
    open_folder_requested = Signal(str)
    export_another_requested = Signal()
    presentation_state_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._preflight_applied = False
        self._preflight_ready = False
        self._busy = False
        self._presentation_state = "empty"
        self._last_package_path: str | None = None
        self._build_ui()
        self._update_export_enabled()

    @property
    def presentation_state(self) -> str:
        """Return presentation-only export state without changing package semantics."""

        return self._presentation_state

    @property
    def is_busy(self) -> bool:
        return self._busy

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        self.root_layout = root
        toolbar = QHBoxLayout()
        self.toolbar_layout = toolbar
        self.back_button = QPushButton("← Back to Figure")
        self.back_button.clicked.connect(self.back_requested.emit)
        toolbar.addWidget(self.back_button)
        self.title_label = QLabel("EXPORT FIGURE PACKAGE")
        toolbar.addWidget(self.title_label, 1)
        root.addLayout(toolbar)

        self.summary_group = QGroupBox("Figure")
        summary_form = QFormLayout(self.summary_group)
        self.figure_label = QLabel("No figure")
        self.figure_status = QLabel("Not ready")
        summary_form.addRow("Result", self.figure_label)
        summary_form.addRow("Status", self.figure_status)
        root.addWidget(self.summary_group)

        self.figure_files_group = QGroupBox("Figure files")
        figure_layout = QHBoxLayout(self.figure_files_group)
        self.svg_check = QCheckBox("SVG")
        self.pdf_check = QCheckBox("PDF")
        self.png_check = QCheckBox("PNG")
        for checkbox in (self.svg_check, self.pdf_check, self.png_check):
            checkbox.setChecked(True)
            checkbox.toggled.connect(self._update_export_enabled)
            figure_layout.addWidget(checkbox)
        figure_layout.addStretch(1)
        root.addWidget(self.figure_files_group)

        self.source_files_group = QGroupBox("Figure source data")
        source_layout = QHBoxLayout(self.source_files_group)
        self.xlsx_check = QCheckBox("XLSX")
        self.txt_check = QCheckBox("TXT")
        for checkbox in (self.xlsx_check, self.txt_check):
            checkbox.setChecked(True)
            checkbox.toggled.connect(self._update_export_enabled)
            source_layout.addWidget(checkbox)
        source_layout.addStretch(1)
        root.addWidget(self.source_files_group)

        self.destination_group = QGroupBox("Package location")
        destination_layout = QHBoxLayout(self.destination_group)
        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("Choose a new package directory")
        self.location_edit.textChanged.connect(self._update_export_enabled)
        destination_layout.addWidget(self.location_edit, 1)
        self.browse_button = QPushButton("Browse…")
        self.browse_button.clicked.connect(self.browse_requested.emit)
        destination_layout.addWidget(self.browse_button)
        root.addWidget(self.destination_group)

        self.preflight_group = QGroupBox("Preflight")
        preflight_layout = QVBoxLayout(self.preflight_group)
        project_row = QHBoxLayout()
        self.project_check = QLabel("○ Project saved")
        project_row.addWidget(self.project_check, 1)
        self.save_project_button = QPushButton("Save Project")
        self.save_project_button.clicked.connect(self.save_requested.emit)
        project_row.addWidget(self.save_project_button)
        preflight_layout.addLayout(project_row)
        self.figure_check = QLabel("○ Figure current")
        self.font_check = QLabel("○ Font available")
        self.trace_check = QLabel("○ Visible traces")
        self.destination_check = QLabel("○ Destination available")
        for label in (
            self.figure_check,
            self.font_check,
            self.trace_check,
            self.destination_check,
        ):
            preflight_layout.addWidget(label)
        root.addWidget(self.preflight_group)

        self.message_label = QLabel("")
        self.message_label.setWordWrap(True)
        root.addWidget(self.message_label)

        self.success_actions = QWidget()
        success_layout = QHBoxLayout(self.success_actions)
        success_layout.setContentsMargins(0, 0, 0, 0)
        self.open_folder_button = QPushButton("Open Folder")
        self.open_folder_button.clicked.connect(self._emit_open_folder)
        success_layout.addWidget(self.open_folder_button)
        self.export_another_button = QPushButton("Export Another")
        self.export_another_button.clicked.connect(self._prepare_another_export)
        success_layout.addWidget(self.export_another_button)
        success_layout.addStretch(1)
        self.success_actions.setVisible(False)
        root.addWidget(self.success_actions)
        root.addStretch(1)

        self.export_button = QPushButton("Export Package")
        self.export_button.clicked.connect(self._emit_export)
        root.addWidget(self.export_button)

    def options(self) -> FigurePackageOptions:
        figure_formats = tuple(
            name
            for name, checkbox in (
                ("svg", self.svg_check),
                ("pdf", self.pdf_check),
                ("png", self.png_check),
            )
            if checkbox.isChecked()
        )
        source_formats = tuple(
            name
            for name, checkbox in (("xlsx", self.xlsx_check), ("txt", self.txt_check))
            if checkbox.isChecked()
        )
        return FigurePackageOptions(
            figure_formats=figure_formats,
            source_data_formats=source_formats,
        )

    def set_location(self, path: str | Path) -> None:
        self.location_edit.setText(str(path))

    def set_busy(self, busy: bool) -> None:
        """Expose synchronous export progress as presentation-only state."""

        if type(busy) is not bool:
            raise TypeError("busy must be bool")
        if busy == self._busy:
            return
        self._busy = busy
        self._update_export_enabled()

    def apply_preflight(
        self,
        *,
        figure_label: str,
        project_saved: bool,
        figure_current: bool,
        font_available: bool,
        visible_trace_count: int,
    ) -> None:
        self._preflight_applied = True
        self.figure_label.setText(figure_label)
        self.figure_status.setText("Up to date" if figure_current else "Needs attention")
        self.project_check.setText(
            "✓ Project saved and clean" if project_saved else "✕ Save the project before export"
        )
        self.save_project_button.setVisible(not project_saved)
        self.figure_check.setText(
            "✓ Figure current" if figure_current else "✕ Refresh the Figure from Analysis"
        )
        self.font_check.setText(
            "✓ Font available" if font_available else "✕ Figure font unavailable"
        )
        self.trace_check.setText(
            f"✓ {visible_trace_count} visible trace(s)"
            if visible_trace_count > 0
            else "✕ At least one visible trace is required"
        )
        self._preflight_ready = (
            project_saved
            and figure_current
            and font_available
            and visible_trace_count > 0
        )
        self._update_export_enabled()

    def show_success(self, package_path: str | Path) -> None:
        self._last_package_path = str(package_path)
        self.message_label.setText(f"Package exported successfully:\n{package_path}")
        self.success_actions.setVisible(True)
        self._update_export_enabled()

    def show_error(self, message: str) -> None:
        self.message_label.setText(message)
        self._last_package_path = None
        self.success_actions.setVisible(False)
        self._update_export_enabled()

    def _destination_available(self) -> bool:
        text = self.location_edit.text().strip()
        if not text:
            self.destination_check.setText("○ Destination available")
            return False
        path = Path(text)
        available = not path.exists() and not path.is_symlink() and path.parent.is_dir()
        self.destination_check.setText(
            "✓ Destination available"
            if available
            else "✕ Destination must be a new directory with an existing parent"
        )
        return available

    def _update_export_enabled(self, *_args: object) -> None:
        figures = any(
            checkbox.isChecked() for checkbox in (self.svg_check, self.pdf_check, self.png_check)
        )
        sources = any(checkbox.isChecked() for checkbox in (self.xlsx_check, self.txt_check))
        destination = self._destination_available()
        self.export_button.setEnabled(
            not self._busy
            and self._preflight_ready
            and figures
            and sources
            and destination
        )
        self._sync_presentation_state()

    def _sync_presentation_state(self) -> None:
        if self._busy:
            state = "exporting"
        elif self._last_package_path is not None:
            state = "success"
        elif self.message_label.text().strip():
            state = "error"
        elif not self._preflight_applied:
            state = "empty"
        elif self.export_button.isEnabled():
            state = "ready"
        else:
            state = "blocked"
        if state == self._presentation_state:
            return
        self._presentation_state = state
        self.presentation_state_changed.emit(state)

    def _emit_export(self) -> None:
        try:
            options = self.options()
        except (TypeError, ValueError, RuntimeError) as exc:
            self.show_error(str(exc))
            return
        self.export_requested.emit(self.location_edit.text().strip(), options)

    def _emit_open_folder(self) -> None:
        if self._last_package_path is not None:
            self.open_folder_requested.emit(self._last_package_path)

    def _prepare_another_export(self) -> None:
        self.location_edit.clear()
        self.message_label.clear()
        self._last_package_path = None
        self.success_actions.setVisible(False)
        self.export_another_requested.emit()
        self._update_export_enabled()


__all__ = ["FigurePackageExportPage"]
