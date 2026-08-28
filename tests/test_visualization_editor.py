from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.visualization.editor import (
    FigureEditorState,
    FigureSpecEditorController,
    open_figure_spec_editor,
)
from catalysis_workbench.visualization.specs import (
    AnnotationSpec,
    FigureSpec,
    LayoutSpec,
    PlotStyle,
    VisualizationError,
)


def _curve(*, key: str = "a", y=(1.0, 2.0, 3.0)) -> Series:
    return Series(
        x=(0.0, 1.0, 2.0),
        y=y,
        key=key,
        label=key.upper(),
        x_axis=Axis("potential", unit="V", label="Potential"),
        y_axis=Axis("current_density", unit="mA/cm^2", label="Current density"),
    )


def test_editor_state_is_frozen_and_validates_revision() -> None:
    spec = FigureSpec()
    state = FigureEditorState(initial_spec=spec, spec=spec)

    with pytest.raises(FrozenInstanceError):
        state.revision = 1  # type: ignore[misc]
    with pytest.raises(VisualizationError, match="revision"):
        FigureEditorState(initial_spec=spec, spec=spec, revision=-1)
    with pytest.raises(VisualizationError, match="revision"):
        FigureEditorState(initial_spec=spec, spec=spec, revision=True)


def test_controller_rejects_non_scientific_data_and_invalid_spec() -> None:
    with pytest.raises(TypeError, match="Series or Dataset"):
        FigureSpecEditorController(object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="FigureSpec"):
        FigureSpecEditorController(_curve(), object())  # type: ignore[arg-type]


def test_controller_updates_create_new_immutable_specs_and_track_revision() -> None:
    initial = FigureSpec(
        layout=LayoutSpec(figure_width_in=4.0),
        style=PlotStyle(font_size=8.0),
        title="Initial",
    )
    controller = FigureSpecEditorController(_curve(), initial)

    controller.update(title="Edited", xlabel="E / V")
    controller.update_style(font_size=9.0, line_width=1.5)
    controller.update_layout(figure_width_in=5.0)
    controller.update_export(dpi=450)

    assert controller.state.revision == 4
    assert controller.spec.title == "Edited"
    assert controller.spec.xlabel == "E / V"
    assert controller.spec.style.font_size == pytest.approx(9.0)
    assert controller.spec.style.line_width == pytest.approx(1.5)
    assert controller.spec.layout.figure_width_in == pytest.approx(5.0)
    assert controller.spec.export.dpi == 450
    assert initial.title == "Initial"
    assert initial.style.font_size == pytest.approx(8.0)
    assert initial.layout.figure_width_in == pytest.approx(4.0)


def test_noop_update_does_not_increment_revision() -> None:
    initial = FigureSpec(title="Same")
    controller = FigureSpecEditorController(_curve(), initial)

    state = controller.update(title="Same")

    assert state.revision == 0
    assert controller.state is state


def test_failed_update_has_zero_partial_state_mutation() -> None:
    controller = FigureSpecEditorController(_curve(), FigureSpec())
    before = controller.state

    with pytest.raises(VisualizationError):
        controller.update_layout(figure_width_in=-1.0)

    assert controller.state is before
    assert controller.state.revision == 0


def test_controller_supports_existing_series_category_and_annotation_bridges() -> None:
    controller = FigureSpecEditorController(_curve())
    annotation = AnnotationSpec("a", 0.04, 0.96)

    controller.update_series_style("a", color="#222222", marker="o")
    controller.update_category_style("group", color="#999999")
    controller.add_annotation(annotation)

    assert controller.spec.series_styles["a"].color == "#222222"
    assert controller.spec.series_styles["a"].marker == "o"
    assert controller.spec.category_styles["group"].color == "#999999"
    assert controller.spec.annotations == (annotation,)

    controller.remove_series_style("a")
    controller.remove_category_style("group")
    assert "a" not in controller.spec.series_styles
    assert "group" not in controller.spec.category_styles


def test_reset_restores_exact_initial_spec_without_mutating_it() -> None:
    initial = FigureSpec(title="Initial", xscale="linear")
    controller = FigureSpecEditorController(_curve(), initial)
    controller.update(title="Changed", xscale="log")
    before_reset_revision = controller.state.revision

    state = controller.reset()

    assert state.spec == initial
    assert state.initial_spec == initial
    assert state.revision == before_reset_revision + 1
    assert initial.title == "Initial"
    assert initial.xscale == "linear"


def test_preview_uses_existing_curve_renderer_and_does_not_mutate_data() -> None:
    first = _curve(key="first", y=(1.0, 2.0, 3.0))
    second = _curve(key="second", y=(3.0, 2.0, 1.0))
    dataset = Dataset((first, second))
    first_x = first.x.copy()
    first_y = first.y.copy()
    second_x = second.x.copy()
    second_y = second.y.copy()
    controller = FigureSpecEditorController(dataset, FigureSpec(title="Preview"))
    controller.update_series_style("first", color="#111111", line_width=2.0)

    figure, ax = controller.preview()

    assert ax.get_title() == "Preview"
    assert len(ax.lines) == 2
    assert ax.lines[0].get_color() == "#111111"
    assert ax.lines[0].get_linewidth() == pytest.approx(2.0)
    np.testing.assert_array_equal(first.x, first_x)
    np.testing.assert_array_equal(first.y, first_y)
    np.testing.assert_array_equal(second.x, second_x)
    np.testing.assert_array_equal(second.y, second_y)
    assert figure.canvas is not None


def test_open_editor_builds_matplotlib_widgets_headlessly() -> None:
    import matplotlib.pyplot as plt

    controller = open_figure_spec_editor(
        _curve(),
        FigureSpec(title="Headless", show_legend=True),
        show=False,
    )
    try:
        assert isinstance(controller, FigureSpecEditorController)
        assert controller.spec.title == "Headless"
        assert controller.spec.show_legend is True
        assert controller.state.revision == 0
        assert controller._ui is not None
        assert controller._ui.control_figure.canvas is not None
    finally:
        plt.close("all")


@pytest.mark.parametrize("show", [1, None, "yes"])
def test_open_editor_requires_explicit_boolean_show(show: object) -> None:
    with pytest.raises(TypeError, match="bool"):
        open_figure_spec_editor(_curve(), show=show)  # type: ignore[arg-type]


def test_editor_module_has_no_top_level_pyplot_widgets_or_gui_framework_import() -> None:
    source = (
        Path(__file__).parents[1]
        / "src"
        / "catalysis_workbench"
        / "visualization"
        / "editor.py"
    )
    tree = ast.parse(source.read_text(encoding="utf-8"))
    top_level_imports: set[str] = set()
    all_imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            all_imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            all_imports.add(node.module)
    for node in tree.body:
        if isinstance(node, ast.Import):
            top_level_imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            top_level_imports.add(node.module)

    assert "matplotlib.pyplot" not in top_level_imports
    assert "matplotlib.widgets" not in top_level_imports
    assert not any(
        name.startswith(("PySide", "PyQt", "tkinter", "wx")) for name in all_imports
    )
