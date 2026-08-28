"""Presentation-only interactive editing for immutable :class:`FigureSpec` state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from catalysis_workbench.core import Dataset, Series

from .curves import render_curves
from .presets import get_preset
from .specs import (
    AnnotationSpec,
    CategoryStyle,
    FigureSpec,
    SeriesStyle,
    VisualizationError,
)


@dataclass(frozen=True, slots=True)
class FigureEditorState:
    """Immutable editor state detached from scientific data."""

    initial_spec: FigureSpec
    spec: FigureSpec
    revision: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.initial_spec, FigureSpec):
            raise TypeError("initial_spec must be a FigureSpec")
        if not isinstance(self.spec, FigureSpec):
            raise TypeError("spec must be a FigureSpec")
        if type(self.revision) is not int or self.revision < 0:
            raise VisualizationError("editor revision must be a non-negative integer")


@dataclass(slots=True)
class _EditorUI:
    control_figure: Any
    textboxes: dict[str, Any]
    scale_buttons: dict[str, Any]
    legend_check: Any
    status_text: Any


class FigureSpecEditorController:
    """Headless-testable controller for presentation-only FigureSpec updates."""

    def __init__(
        self,
        data: Series | Dataset,
        spec: FigureSpec | None = None,
        *,
        preset: str = "publication",
    ) -> None:
        if not isinstance(data, (Series, Dataset)):
            raise TypeError("editor data must be a Series or Dataset")
        selected = get_preset(preset) if spec is None else spec
        if not isinstance(selected, FigureSpec):
            raise TypeError("spec must be a FigureSpec")
        self._data = data
        self._state = FigureEditorState(initial_spec=selected, spec=selected)
        self._ui: _EditorUI | None = None

    @property
    def data(self) -> Series | Dataset:
        """Return the read-only scientific input referenced by the editor."""
        return self._data

    @property
    def state(self) -> FigureEditorState:
        """Return the current immutable editor state."""
        return self._state

    @property
    def spec(self) -> FigureSpec:
        """Return the current immutable FigureSpec."""
        return self._state.spec

    def _commit(self, candidate: FigureSpec) -> FigureEditorState:
        if not isinstance(candidate, FigureSpec):
            raise TypeError("candidate must be a FigureSpec")
        if candidate == self._state.spec:
            return self._state
        self._state = FigureEditorState(
            initial_spec=self._state.initial_spec,
            spec=candidate,
            revision=self._state.revision + 1,
        )
        return self._state

    def update(self, **changes: Any) -> FigureEditorState:
        """Update validated top-level presentation fields."""
        return self._commit(self.spec.updated(**changes))

    def update_layout(self, **changes: Any) -> FigureEditorState:
        """Update validated physical layout fields."""
        return self._commit(self.spec.with_layout(**changes))

    def update_style(self, **changes: Any) -> FigureEditorState:
        """Update validated global style fields."""
        return self._commit(self.spec.with_style(**changes))

    def update_export(self, **changes: Any) -> FigureEditorState:
        """Update validated export presentation fields."""
        return self._commit(self.spec.with_export(**changes))

    def update_series_style(
        self,
        key: str,
        style: SeriesStyle | None = None,
        **changes: Any,
    ) -> FigureEditorState:
        """Add or update one stable-key-specific series presentation override."""
        return self._commit(self.spec.with_series_style(key, style, **changes))

    def remove_series_style(self, key: str) -> FigureEditorState:
        """Remove one stable-key-specific series presentation override."""
        return self._commit(self.spec.without_series_style(key))

    def update_category_style(
        self,
        key: str,
        style: CategoryStyle | None = None,
        **changes: Any,
    ) -> FigureEditorState:
        """Add or update one stable-key-specific category presentation override."""
        return self._commit(self.spec.with_category_style(key, style, **changes))

    def remove_category_style(self, key: str) -> FigureEditorState:
        """Remove one stable-key-specific category presentation override."""
        return self._commit(self.spec.without_category_style(key))

    def add_annotation(self, annotation: AnnotationSpec) -> FigureEditorState:
        """Append one validated presentation annotation."""
        return self._commit(self.spec.with_annotation(annotation))

    def reset(self) -> FigureEditorState:
        """Return to the exact FigureSpec supplied when the controller was created."""
        if self.spec == self._state.initial_spec:
            return self._state
        self._state = FigureEditorState(
            initial_spec=self._state.initial_spec,
            spec=self._state.initial_spec,
            revision=self._state.revision + 1,
        )
        return self._state

    def preview(self):
        """Render a new preview through the existing generic curve renderer."""
        return render_curves(self._data, self.spec)


def _display_text(value: str | None) -> str:
    return "" if value is None else value


def _sync_ui(controller: FigureSpecEditorController) -> None:
    ui = controller._ui
    if ui is None:
        return
    spec = controller.spec
    values = {
        "title": _display_text(spec.title),
        "xlabel": _display_text(spec.xlabel),
        "ylabel": _display_text(spec.ylabel),
        "font_size": str(spec.style.font_size),
        "line_width": str(spec.style.line_width),
        "marker_size": str(spec.style.marker_size),
        "figure_width_in": str(spec.layout.figure_width_in),
        "figure_height_in": str(spec.layout.figure_height_in),
    }
    for name, value in values.items():
        box = ui.textboxes[name]
        eventson = box.eventson
        box.eventson = False
        try:
            box.set_val(value)
        finally:
            box.eventson = eventson

    for axis, scale in (("x", spec.xscale), ("y", spec.yscale)):
        buttons = ui.scale_buttons[axis]
        labels = [item.get_text() for item in buttons.labels]
        index = labels.index(scale)
        eventson = buttons.eventson
        buttons.eventson = False
        try:
            buttons.set_active(index)
        finally:
            buttons.eventson = eventson

    desired_legend = bool(spec.show_legend)
    current_legend = bool(ui.legend_check.get_status()[0])
    if current_legend != desired_legend:
        eventson = ui.legend_check.eventson
        ui.legend_check.eventson = False
        try:
            ui.legend_check.set_active(0)
        finally:
            ui.legend_check.eventson = eventson


def _build_matplotlib_ui(controller: FigureSpecEditorController) -> _EditorUI:
    import matplotlib.pyplot as plt
    from matplotlib.widgets import Button, CheckButtons, RadioButtons, TextBox

    control_figure = plt.figure(figsize=(7.2, 7.4))
    control_figure.canvas.manager.set_window_title("CatalysisWorkbench FigureSpec editor")
    control_figure.suptitle("FigureSpec presentation editor", fontsize=12)

    status_text = control_figure.text(0.05, 0.025, "Ready", fontsize=8)

    def status(message: str) -> None:
        status_text.set_text(message)
        control_figure.canvas.draw_idle()

    def safe_update(action) -> None:
        try:
            action()
        except (TypeError, ValueError, VisualizationError) as exc:
            status(f"Invalid presentation value: {exc}")
            _sync_ui(controller)
            return
        status(f"Revision {controller.state.revision}")

    fields = (
        ("title", "Title", 0.88),
        ("xlabel", "X label", 0.82),
        ("ylabel", "Y label", 0.76),
        ("font_size", "Font size", 0.68),
        ("line_width", "Line width", 0.62),
        ("marker_size", "Marker size", 0.56),
        ("figure_width_in", "Figure width (in)", 0.48),
        ("figure_height_in", "Figure height (in)", 0.42),
    )
    textboxes: dict[str, Any] = {}
    for name, label, y in fields:
        ax = control_figure.add_axes((0.29, y, 0.62, 0.045))
        textboxes[name] = TextBox(ax, label, initial="")

    textboxes["title"].on_submit(
        lambda value: safe_update(lambda: controller.update(title=value or None))
    )
    textboxes["xlabel"].on_submit(
        lambda value: safe_update(lambda: controller.update(xlabel=value or None))
    )
    textboxes["ylabel"].on_submit(
        lambda value: safe_update(lambda: controller.update(ylabel=value or None))
    )
    textboxes["font_size"].on_submit(
        lambda value: safe_update(lambda: controller.update_style(font_size=float(value)))
    )
    textboxes["line_width"].on_submit(
        lambda value: safe_update(lambda: controller.update_style(line_width=float(value)))
    )
    textboxes["marker_size"].on_submit(
        lambda value: safe_update(lambda: controller.update_style(marker_size=float(value)))
    )
    textboxes["figure_width_in"].on_submit(
        lambda value: safe_update(
            lambda: controller.update_layout(figure_width_in=float(value))
        )
    )
    textboxes["figure_height_in"].on_submit(
        lambda value: safe_update(
            lambda: controller.update_layout(figure_height_in=float(value))
        )
    )

    scale_labels = ("linear", "log", "symlog", "logit")
    xscale_ax = control_figure.add_axes((0.08, 0.17, 0.18, 0.19))
    yscale_ax = control_figure.add_axes((0.31, 0.17, 0.18, 0.19))
    xscale = RadioButtons(xscale_ax, scale_labels)
    yscale = RadioButtons(yscale_ax, scale_labels)
    xscale_ax.set_title("X scale", fontsize=9)
    yscale_ax.set_title("Y scale", fontsize=9)
    xscale.on_clicked(lambda value: safe_update(lambda: controller.update(xscale=value)))
    yscale.on_clicked(lambda value: safe_update(lambda: controller.update(yscale=value)))

    legend_ax = control_figure.add_axes((0.55, 0.27, 0.16, 0.07))
    legend = CheckButtons(legend_ax, ("Legend",), (False,))
    legend.on_clicked(
        lambda _label: safe_update(
            lambda: controller.update(show_legend=bool(legend.get_status()[0]))
        )
    )

    preview_ax = control_figure.add_axes((0.55, 0.17, 0.16, 0.065))
    reset_ax = control_figure.add_axes((0.75, 0.17, 0.16, 0.065))
    preview_button = Button(preview_ax, "Preview")
    reset_button = Button(reset_ax, "Reset")

    def preview(_event) -> None:
        try:
            figure, _ = controller.preview()
        except (TypeError, ValueError, VisualizationError) as exc:
            status(f"Preview failed: {exc}")
            return
        figure.show()
        status(f"Preview revision {controller.state.revision}")

    def reset(_event) -> None:
        controller.reset()
        _sync_ui(controller)
        status(f"Reset at revision {controller.state.revision}")

    preview_button.on_clicked(preview)
    reset_button.on_clicked(reset)

    ui = _EditorUI(
        control_figure=control_figure,
        textboxes=textboxes,
        scale_buttons={"x": xscale, "y": yscale},
        legend_check=legend,
        status_text=status_text,
    )
    # Matplotlib widgets must remain strongly referenced for callbacks to stay active.
    ui.control_figure._catalysis_workbench_editor_widgets = (  # type: ignore[attr-defined]
        *textboxes.values(),
        xscale,
        yscale,
        legend,
        preview_button,
        reset_button,
    )
    return ui


def open_figure_spec_editor(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
    show: bool = True,
) -> FigureSpecEditorController:
    """Open a lightweight Matplotlib presentation editor and return its controller.

    Scientific data are retained read-only. The editor changes only immutable
    :class:`FigureSpec` presentation state and previews through ``render_curves``.
    ``show=False`` is intended for headless testing and scripted integration.
    """

    if type(show) is not bool:
        raise TypeError("show must be a bool")
    controller = FigureSpecEditorController(data, spec, preset=preset)
    controller._ui = _build_matplotlib_ui(controller)
    _sync_ui(controller)
    if show:
        import matplotlib.pyplot as plt

        plt.show(block=False)
    return controller
