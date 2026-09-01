"""v1.2 presentation composition for Figure Package Export."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QWidget,
)

from .ui_foundation import SPACING, refresh_widget_style


_STATE_TEXT = {
    "empty": "Waiting for export preflight",
    "ready": "Ready to export",
    "exporting": "Exporting package…",
    "success": "Package exported",
    "error": "Export needs attention",
}


def _section_label(text: str, parent: QWidget) -> QLabel:
    label = QLabel(text, parent)
    label.setObjectName("cwSectionTitle")
    return label


def productize_export_workbench(page: QWidget) -> None:
    """Apply v1.2 Export presentation without changing package semantics."""

    root = page.layout()
    if not isinstance(root, QVBoxLayout):
        raise TypeError("Figure Package Export must use a QVBoxLayout root")

    page.setObjectName("cwAnalysisWorkspace")
    root.setContentsMargins(
        SPACING.section,
        SPACING.normal,
        SPACING.section,
        SPACING.section,
    )
    root.setSpacing(SPACING.normal)

    page.back_button.setVisible(False)
    page.title_label.setText("Export Figure Package")
    page.title_label.setObjectName("cwImportTitle")

    subtitle = QLabel(
        "Validate the current publication figure, choose package contents, "
        "and export to a new directory.",
        page,
    )
    subtitle.setObjectName("cwWorkspaceHelp")
    subtitle.setWordWrap(True)
    root.insertWidget(1, subtitle)
    page.export_subtitle_label = subtitle

    state_label = QLabel(page)
    state_label.setObjectName("cwWorkspaceStatus")
    root.insertWidget(2, state_label)
    page.export_state_label = state_label

    for group, title in (
        (page.summary_group, "SUMMARY"),
        (page.figure_files_group, "FIGURE FILES"),
        (page.source_files_group, "SOURCE DATA"),
        (page.destination_group, "DESTINATION"),
        (page.preflight_group, "PREFLIGHT"),
    ):
        group.setTitle(title)
        group.setObjectName("cwInspectorSection")

    contents_label = _section_label("CONTENTS", page)
    root.insertWidget(root.indexOf(page.figure_files_group), contents_label)
    page.contents_section_label = contents_label

    result_label = _section_label("RESULT", page)
    root.insertWidget(root.indexOf(page.message_label), result_label)
    page.result_section_label = result_label

    page.location_edit.setObjectName("cwAnalysisTitleEdit")
    page.browse_button.setObjectName("cwSecondaryButton")
    page.save_project_button.setObjectName("cwSecondaryButton")
    page.open_folder_button.setObjectName("cwSecondaryButton")
    page.export_another_button.setObjectName("cwTertiaryButton")
    page.export_button.setObjectName("cwPrimaryButton")
    page.message_label.setObjectName("cwCanvasNote")

    page.presentation_state_changed.connect(
        lambda _state: refresh_export_presentation_state(page)
    )
    refresh_export_presentation_state(page)


def _blocked_text(page: QWidget) -> str:
    if not page._preflight_ready:
        return "Resolve preflight checks"
    if not any(
        checkbox.isChecked()
        for checkbox in (page.svg_check, page.pdf_check, page.png_check)
    ):
        return "Choose at least one figure format"
    if not any(checkbox.isChecked() for checkbox in (page.xlsx_check, page.txt_check)):
        return "Choose at least one source-data format"
    if not page.location_edit.text().strip():
        return "Choose a destination"
    return "Choose a new available destination"


def export_status_message(page: QWidget) -> str:
    """Return cross-page status language for the current Export state."""

    state = page.presentation_state
    if state == "empty":
        return "Export is waiting for preflight"
    if state == "blocked":
        return _blocked_text(page)
    if state == "ready":
        return "Export ready"
    if state == "exporting":
        return "Exporting Figure Package…"
    if state == "success":
        return "Figure Package exported"
    return "Export needs attention"


def refresh_export_presentation_state(page: QWidget) -> None:
    """Mirror retained export state into semantic presentation-only properties."""

    label = getattr(page, "export_state_label", None)
    if not isinstance(label, QLabel):
        return

    state = page.presentation_state
    if state == "blocked":
        text = _blocked_text(page)
        semantic_state = "incomplete"
    else:
        text = _STATE_TEXT.get(state, "Export needs attention")
        semantic_state = {
            "empty": "empty",
            "ready": "success",
            "exporting": "incomplete",
            "success": "success",
            "error": "error",
        }.get(state, "error")

    label.setText(text)
    label.setProperty("state", semantic_state)
    page.message_label.setProperty(
        "state",
        "error" if state == "error" else semantic_state,
    )
    refresh_widget_style(label)
    refresh_widget_style(page.message_label)


__all__ = [
    "export_status_message",
    "productize_export_workbench",
    "refresh_export_presentation_state",
]
