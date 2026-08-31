"""Installed-wheel smoke for v0.9 Block 6 FigureSpec editor."""

from __future__ import annotations

import importlib.metadata
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")

import catalysis_workbench
import catalysis_workbench.visualization as visualization
from catalysis_workbench.core import Axis, Series

EXPECTED_VERSION = "1.1.0"
EXPECTED_PUBLIC_API = {
    "FigureEditorState",
    "FigureSpecEditorController",
    "open_figure_spec_editor",
}
SOURCE_TREE = Path(__file__).resolve().parents[1] / "src"


def main() -> None:
    assert importlib.metadata.version("catalysis-workbench") == EXPECTED_VERSION
    assert catalysis_workbench.__version__ == EXPECTED_VERSION
    visualization_path = Path(visualization.__file__).resolve()
    assert not visualization_path.is_relative_to(SOURCE_TREE)
    assert "site-packages" in {part.lower() for part in visualization_path.parts}
    assert EXPECTED_PUBLIC_API.issubset(set(visualization.__all__))
    assert all(hasattr(visualization, name) for name in EXPECTED_PUBLIC_API)

    source = Series(
        x=(0.0, 1.0, 2.0),
        y=(1.0, 2.0, 3.0),
        key="installed-editor",
        label="Installed editor",
        x_axis=Axis("potential", unit="V", label="Potential"),
        y_axis=Axis("current_density", unit="mA/cm^2", label="Current density"),
    )
    x_before = source.x.copy()
    y_before = source.y.copy()

    controller = visualization.FigureSpecEditorController(
        source,
        visualization.FigureSpec(title="Installed preview"),
    )
    controller.update_style(font_size=9.0, line_width=1.5)
    controller.update_layout(figure_width_in=4.0)
    figure, ax = controller.preview()
    assert controller.state.revision == 2
    assert ax.get_title() == "Installed preview"
    assert ax.lines[0].get_linewidth() == 1.5
    np.testing.assert_array_equal(source.x, x_before)
    np.testing.assert_array_equal(source.y, y_before)
    assert figure.canvas is not None

    opened = visualization.open_figure_spec_editor(
        source,
        visualization.FigureSpec(title="Headless editor"),
        show=False,
    )
    assert isinstance(opened, visualization.FigureSpecEditorController)
    assert opened.spec.title == "Headless editor"
    assert opened.state.revision == 0

    import matplotlib.pyplot as plt

    plt.close("all")
    for optional_name in ("pymatgen", "pyvista", "vtk"):
        assert optional_name not in sys.modules

    print("installed v0.9 Block 6 smoke passed")


if __name__ == "__main__":
    main()
