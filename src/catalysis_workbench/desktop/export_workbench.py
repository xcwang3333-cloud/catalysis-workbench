"""Qt Figure Package Export page for v1.1 Block 5."""

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
    export_requested = Signal(str, object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._preflight_ready = False
        self._build_ui()
        self._update_export_enabled()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        back = QPushButton("← Back to Figure")
        back.clicked.connect(self.back_requested.emit)
        toolbar.addWidget(back)
        title = QLabel("EXPORT FIGURE PACKAGE")
        toolbar.addWidget(title, 1)
        root.addLayout(toolbar)

        summary = QGroupBox("Figure")
        summary_form = QFormLayout(summary)
        self.figure_label = QLabel("No figure")
        self.figure_status = QLabel("Not ready")
        summary_form.addRow("Result", self.figure_label)
        summary_form.addRow("Status", self.figure_status)
        root.addWidget(summary)

        figure_files = QGroupBox("Figure files")
        figure_layout = QHBoxLayout(figure_files)
        self.svg_check = QCheckBox("SVG")
        self.pdf_check = QCheckBox("PDF")
        self.png_check = QCheckBox("PNG")
        for checkbox in (self.svg_check, self.pdf_check, self.png_check):
            checkbox.setChecked(True)
            checkbox.toggled.connect(self._update_export_enabled)
            figure_layout.addWidget(checkbox)
        figure_layout.addStretch(1)
        root.addWidget(figure_files)

        source_files = QGroupBox("Figure source data")
        source_layout = QHBoxLayout(source_files)
        self.xlsx_check = QCheckBox("XLSX")
        self.txt_check = QCheckBox("TXT")
        for checkbox in (self.xlsx_check, self.txt_check):
            checkbox.setChecked(True)
            checkbox.toggled.connect(self._update_export_enabled)
            source_layout.addWidget(checkbox)
        source_layout.addStretch(1)
        root.addWidget(source_files)

        destination = QGroupBox("Package location")
        destination_layout = QHBoxLayout(destination)
        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("Choose a new package directory")
        self.location_edit.textChanged.connect(self._update_export_enabled)
        destination_layout.addWidget(self.location_edit, 1)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self.browse_requested.emit)
        destination_layout.addWidget(browse)
        root.addWidget(destination)

        preflight = QGroupBox("Preflight")
        preflight_layout = QVBoxLayout(preflight)
        self.project_check = QLabel("○ Project saved")
        self.figure_check = QLabel("○ Figure current")
        self.font_check = QLabel("○ Font available")
        self.trace_check = QLabel("○ Visible traces")
        self.destination_check = QLabel("○ Destination available")
        for label in (
            self.project_check,
            self.figure_check,
            self.font_check,
            self.trace_check,
            self.destination_check,
        ):
            preflight_layout.addWidget(label)
        root.addWidget(preflight)

        self.message_label = QLabel("")
        self.message_label.setWordWrap(True)
        root.addWidget(self.message_label)
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

    def apply_preflight(
        self,
        *,
        figure_label: str,
        project_saved: bool,
        figure_current: bool,
        font_available: bool,
        visible_trace_count: int,
    ) -> None:
        self.figure_label.setText(figure_label)
        self.figure_status.setText("Up to date" if figure_current else "Needs attention")
        self.project_check.setText(
            "✓ Project saved and clean" if project_saved else "✕ Save the project before export"
        )
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
        self.message_label.setText(f"Package exported successfully:\n{package_path}")
        self._update_export_enabled()

    def show_error(self, message: str) -> None:
        self.message_label.setText(message)

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
            self._preflight_ready and figures and sources and destination
        )

    def _emit_export(self) -> None:
        try:
            options = self.options()
        except (TypeError, ValueError, RuntimeError) as exc:
            self.show_error(str(exc))
            return
        self.export_requested.emit(self.location_edit.text().strip(), options)


__all__ = ["FigurePackageExportPage"]
