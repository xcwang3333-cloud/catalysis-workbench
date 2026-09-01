"""v1.2 presentation composition for the retained Figure Workbench."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QLabel,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .ui_foundation import SPACING, refresh_widget_style


def _toolbar_widgets(root: QVBoxLayout) -> tuple[QWidget, ...]:
    item = root.itemAt(0)
    layout = None if item is None else item.layout()
    if layout is None:
        return ()
    widgets: list[QWidget] = []
    for index in range(layout.count()):
        child = layout.itemAt(index).widget()
        if child is not None:
            widgets.append(child)
    return tuple(widgets)


def productize_figure_workbench(page: QWidget) -> None:
    """Apply the v1.2 Figure presentation without adding a second state engine."""

    root = page.layout()
    if not isinstance(root, QVBoxLayout):
        raise TypeError("Figure Workbench must use a QVBoxLayout root")

    page.setObjectName("cwFigureWorkbench")
    root.setContentsMargins(
        SPACING.normal,
        SPACING.normal,
        SPACING.normal,
        SPACING.normal,
    )
    root.setSpacing(SPACING.normal)

    status_label = page.status_label
    status_label.setObjectName("cwFigureStatus")
    for widget in _toolbar_widgets(root):
        if widget is not status_label:
            widget.setVisible(False)

    splitter_item = root.itemAt(1)
    splitter = None if splitter_item is None else splitter_item.widget()
    if not isinstance(splitter, QSplitter):
        raise TypeError("Figure Workbench must expose its three panes through QSplitter")
    splitter.setObjectName("cwFigureSplitter")

    content = splitter.widget(0)
    canvas = splitter.widget(1)
    properties = splitter.widget(2)
    if not all(isinstance(item, QGroupBox) for item in (content, canvas, properties)):
        raise TypeError("Figure Workbench panes must remain QGroupBox widgets")

    content.setObjectName("cwFigureContent")
    canvas.setObjectName("cwPublicationCanvas")
    canvas.setTitle("PUBLICATION CANVAS")
    properties.setObjectName("cwFigureProperties")

    page.view_combo.setObjectName("cwFigureViewCombo")
    page.preset_combo.setObjectName("cwFigurePresetCombo")
    page.create_button.setObjectName("cwPrimaryButton")
    page.refresh_button.setObjectName("cwSecondaryButton")
    page.reset_button.setObjectName("cwTertiaryButton")
    page.trace_list.setObjectName("cwFigureTraceList")
    page.preview_note.setObjectName("cwFigureCanvasNote")
    page.continue_export_button.setObjectName("cwPrimaryButton")

    state_label = QLabel("Create a figure", canvas)
    state_label.setObjectName("cwFigureCanvasState")
    state_label.setProperty("state", "empty")
    page.preview_layout.insertWidget(0, state_label)
    page.canvas_state_label = state_label

    for group in properties.findChildren(QGroupBox):
        if group is not properties:
            group.setObjectName("cwFigurePropertyGroup")

    properties.setParent(None)
    properties_scroll = QScrollArea(splitter)
    properties_scroll.setObjectName("cwFigurePropertiesScroll")
    properties_scroll.setWidgetResizable(True)
    properties_scroll.setFrameShape(QFrame.Shape.NoFrame)
    properties_scroll.setHorizontalScrollBarPolicy(
        properties_scroll.horizontalScrollBarPolicy().ScrollBarAlwaysOff
    )
    properties_scroll.setWidget(properties)
    splitter.insertWidget(2, properties_scroll)
    splitter.setSizes([300, 760, 380])
    splitter.setStretchFactor(0, 0)
    splitter.setStretchFactor(1, 1)
    splitter.setStretchFactor(2, 0)
    page.properties_scroll = properties_scroll

    root.removeWidget(page.continue_export_button)
    page.preview_layout.addWidget(page.continue_export_button)

    refresh_figure_presentation_state(page)


def refresh_figure_presentation_state(page: QWidget) -> None:
    """Mirror retained Figure state into semantic presentation-only properties."""

    label = getattr(page, "canvas_state_label", None)
    if not isinstance(label, QLabel):
        return

    note = page.preview_note.text().strip()
    status = page.status_label.text().strip()
    lowered_note = note.casefold()
    lowered_status = status.casefold()

    if page.draft is None:
        state = "empty"
        text = "Create a figure"
    elif "refresh this figure" in lowered_status or "results changed" in lowered_note:
        state = "stale"
        text = "Analysis changed"
    elif note.startswith("Publication preview"):
        state = "dirty" if "unsaved changes" in lowered_status else "current"
        text = "Current · unsaved changes" if state == "dirty" else "Figure current"
    else:
        state = "error"
        text = "Preview needs attention"

    label.setProperty("state", state)
    label.setText(text)
    page.preview_note.setProperty("state", state)
    page.status_label.setProperty("state", state)
    refresh_widget_style(label)
    refresh_widget_style(page.preview_note)
    refresh_widget_style(page.status_label)


__all__ = ["productize_figure_workbench", "refresh_figure_presentation_state"]
