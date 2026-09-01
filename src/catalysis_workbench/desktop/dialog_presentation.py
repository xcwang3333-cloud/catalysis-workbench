"""Central v1.2 presentation helpers for modal desktop decisions."""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QPushButton, QWidget

from .ui_foundation import ThemeMode, apply_theme


def _prepare_dialog(
    box: QMessageBox,
    *,
    mode: ThemeMode | str,
    role: str,
) -> None:
    box.setObjectName("cwDataImportDialog")
    box.setProperty("dialogRole", role)
    apply_theme(box, mode)


def _style_button(button: QPushButton, object_name: str) -> QPushButton:
    button.setObjectName(object_name)
    return button


def build_error_dialog(
    parent: QWidget,
    *,
    summary: str,
    guidance: str,
    details: str,
    mode: ThemeMode | str,
) -> QMessageBox:
    """Build an actionable error dialog with optional technical details."""

    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Critical)
    box.setWindowTitle("CatalysisWorkbench")
    box.setText(summary)
    box.setInformativeText(guidance)
    box.setDetailedText(details)
    ok = _style_button(
        box.addButton(QMessageBox.StandardButton.Ok),
        "cwPrimaryButton",
    )
    box.setDefaultButton(ok)
    box.setEscapeButton(ok)
    _prepare_dialog(box, mode=mode, role="error")
    return box


def build_dirty_guard_dialog(
    parent: QWidget,
    *,
    mode: ThemeMode | str,
) -> tuple[QMessageBox, QPushButton, QPushButton, QPushButton]:
    """Build the v1.2 Save / Discard / Cancel transition guard."""

    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle("Save changes?")
    box.setText("Save changes before leaving this analysis?")
    box.setInformativeText(
        "Save keeps the current edits. Discard closes without saving. "
        "Cancel keeps the current analysis open."
    )
    save = _style_button(
        box.addButton(QMessageBox.StandardButton.Save),
        "cwPrimaryButton",
    )
    discard = _style_button(
        box.addButton(QMessageBox.StandardButton.Discard),
        "cwSecondaryButton",
    )
    cancel = _style_button(
        box.addButton(QMessageBox.StandardButton.Cancel),
        "cwTertiaryButton",
    )
    box.setDefaultButton(cancel)
    box.setEscapeButton(cancel)
    _prepare_dialog(box, mode=mode, role="dirtyGuard")
    return box, save, discard, cancel


def build_processing_draft_dialog(
    parent: QWidget,
    *,
    mode: ThemeMode | str,
) -> tuple[QMessageBox, QPushButton, QPushButton]:
    """Build the invalid processing-draft discard guard."""

    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle("Discard unapplied settings?")
    box.setText("Current processing fields are invalid and have not been applied.")
    box.setInformativeText(
        "Discard removes only the unapplied field values. Cancel keeps them for editing."
    )
    discard = _style_button(
        box.addButton(QMessageBox.StandardButton.Discard),
        "cwSecondaryButton",
    )
    cancel = _style_button(
        box.addButton(QMessageBox.StandardButton.Cancel),
        "cwPrimaryButton",
    )
    box.setDefaultButton(cancel)
    box.setEscapeButton(cancel)
    _prepare_dialog(box, mode=mode, role="processingDraft")
    return box, discard, cancel


def build_remove_data_dialog(
    parent: QWidget,
    *,
    display_name: str,
    impact_lines: tuple[str, ...],
    mode: ThemeMode | str,
) -> tuple[QMessageBox, QPushButton, QPushButton]:
    """Build a destructive data-removal confirmation without changing raw files."""

    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle("Remove data?")
    box.setText(f"Remove {display_name!r} from this analysis?")
    guidance = ["The original raw file is not modified."]
    if impact_lines:
        guidance.append("This also removes:\n" + "\n".join(impact_lines))
    box.setInformativeText("\n\n".join(guidance))
    remove = _style_button(
        box.addButton("Remove", QMessageBox.ButtonRole.DestructiveRole),
        "cwSecondaryButton",
    )
    cancel = _style_button(
        box.addButton(QMessageBox.StandardButton.Cancel),
        "cwPrimaryButton",
    )
    box.setDefaultButton(cancel)
    box.setEscapeButton(cancel)
    _prepare_dialog(box, mode=mode, role="destructive")
    return box, remove, cancel


__all__ = [
    "build_dirty_guard_dialog",
    "build_error_dialog",
    "build_processing_draft_dialog",
    "build_remove_data_dialog",
]
