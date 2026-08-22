from __future__ import annotations

import subprocess
import sys

import matplotlib.image as mpimg
import numpy as np
import pytest

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.experimental.echem import LSVError, plot_lsv
from catalysis_workbench.visualization import (
    ExportSpec,
    FigureSpec,
    LayoutSpec,
    PlotStyle,
    VisualizationError,
    export_figure,
)


def _lsv(
    *,
    key: str = "pb3",
    label: str = "Pb3-N/C",
    reference: str | None = "RHE",
    x_name: str = "potential",
    y_name: str = "current_density",
    y_unit: str = "mA/cm^2",
    y: tuple[float, ...] = (-1.0, -2.0, -3.0),
) -> Series:
    x_metadata: dict[str, object] = {}
    if reference is not None:
        x_metadata["reference"] = reference
    y_metadata: dict[str, object] = {}
    if y_name == "current_density":
        y_metadata["normalization"] = "geometric_area"
    return Series(
        x=(0.2, 0.5, 0.8),
        y=y,
        label=label,
        key=key,
        x_axis=Axis(
            x_name,
            unit="V",
            label="Potential",
            metadata=x_metadata,
        ),
        y_axis=Axis(
            y_name,
            unit=y_unit,
            label="Current density" if y_name == "current_density" else "Current",
            metadata=y_metadata,
        ),
    )


def test_plot_lsv_adds_reference_to_automatic_potential_label_and_preserves_sign():
    source = _lsv(y=(-2.0, -4.0, -7.0))

    _, ax = plot_lsv(source)

    assert ax.get_xlabel() == "Potential (V vs RHE)"
    assert ax.get_ylabel() == "Current density (mA/cm^2)"
    np.testing.assert_allclose(ax.lines[0].get_ydata(), (-2.0, -4.0, -7.0))
    np.testing.assert_allclose(source.y, (-2.0, -4.0, -7.0))


def test_plot_lsv_respects_slash_unit_format_and_raw_reference_metadata():
    source = _lsv(reference="Ag/AgCl")
    spec = FigureSpec(style=PlotStyle(axis_unit_format="slash"))

    _, ax = plot_lsv(source, spec)

    assert ax.get_xlabel() == "Potential / V vs Ag/AgCl"
    assert ax.get_ylabel() == "Current density / mA/cm^2"


def test_plot_lsv_without_reference_uses_shared_generic_axis_label():
    source = _lsv(reference=None)

    _, ax = plot_lsv(source)

    assert ax.get_xlabel() == "Potential (V)"


def test_plot_lsv_preserves_explicit_blank_and_custom_axis_labels():
    source = _lsv()
    spec = FigureSpec(xlabel="", ylabel=r"$j$ / mA cm$^{-2}$")

    _, ax = plot_lsv(source, spec)

    assert ax.get_xlabel() == ""
    assert ax.get_ylabel() == r"$j$ / mA cm$^{-2}$"


def test_plot_lsv_rejects_non_lsv_axis_semantics():
    with pytest.raises(LSVError, match="x_axis.name='potential'"):
        plot_lsv(_lsv(x_name="time"))
    with pytest.raises(LSVError, match="y_axis.name='current'"):
        plot_lsv(_lsv(y_name="absorbance", y_unit="a.u."))


def test_plot_lsv_dataset_inherits_shared_reference_compatibility_guard():
    dataset = Dataset(
        [
            _lsv(key="rhe", reference="RHE"),
            _lsv(key="agcl", reference="Ag/AgCl", y=(-2.0, -3.0, -4.0)),
        ]
    )

    with pytest.raises(VisualizationError, match="reference"):
        plot_lsv(dataset)


def test_plot_lsv_integrates_with_exact_size_publication_export(tmp_path):
    source = _lsv()
    spec = FigureSpec(
        layout=LayoutSpec(
            figure_width_in=2.0,
            figure_height_in=1.5,
            left_margin_in=0.35,
            right_margin_in=0.10,
            bottom_margin_in=0.30,
            top_margin_in=0.10,
        ),
        export=ExportSpec(dpi=120),
    )

    figure, _ = plot_lsv(source, spec)
    output = export_figure(figure, tmp_path / "lsv.png", spec=spec)
    image = mpimg.imread(output)

    assert image.shape[:2] == (180, 240)


def test_importing_echem_keeps_visualization_and_matplotlib_lazy():
    code = (
        "import sys; "
        "import catalysis_workbench.experimental.echem; "
        "assert 'catalysis_workbench.visualization' not in sys.modules; "
        "assert 'matplotlib' not in sys.modules"
    )

    subprocess.run([sys.executable, "-c", code], check=True)
