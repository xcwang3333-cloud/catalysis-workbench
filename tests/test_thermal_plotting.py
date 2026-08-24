from __future__ import annotations

import matplotlib
import numpy as np
import pytest

matplotlib.use("Agg")

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.experimental.characterization import (
    ThermalAnnotation,
    ThermalError,
    derive_dtg,
    plot_thermal,
)
from catalysis_workbench.visualization import get_preset


def _tga(*, key="a"):
    return Series(
        x=(100.0, 200.0, 300.0, 400.0),
        y=(10.0, 9.0, 8.0, 7.0),
        key=key,
        label=key,
        x_axis=Axis("temperature", unit="°C"),
        y_axis=Axis("mass", unit="mg"),
    )


def _tpr(*, key="a", descending=False):
    x = np.array([100.0, 200.0, 300.0, 400.0, 500.0])
    y = np.array([0.0, 1.0, 3.0, 1.0, 0.0])
    if descending:
        x = x[::-1]
        y = y[::-1]
    return Series(
        x=x,
        y=y,
        key=key,
        label=key,
        x_axis=Axis("temperature", unit="°C"),
        y_axis=Axis("detector_signal", unit="a.u."),
    )


def test_plot_thermal_uses_shared_auto_axis_labels_without_mutating_source():
    source = _tga()
    original_x = np.array(source.x, copy=True)
    original_y = np.array(source.y, copy=True)
    fig, ax = plot_thermal(source, technique="tga")
    assert "Temperature" in ax.get_xlabel()
    assert "Mass" in ax.get_ylabel()
    np.testing.assert_allclose(source.x, original_x)
    np.testing.assert_allclose(source.y, original_y)
    fig.canvas.draw()


def test_plot_thermal_preserves_explicit_empty_label_and_explicit_limits():
    spec = get_preset("publication").updated(
        xlabel="",
        xlim=(150.0, 350.0),
        ylim=(7.5, 9.5),
    )
    fig, ax = plot_thermal(_tga(), spec, technique="tga")
    assert ax.get_xlabel() == ""
    assert ax.get_xlim() == pytest.approx((150.0, 350.0))
    assert ax.get_ylim() == pytest.approx((7.5, 9.5))
    fig.canvas.draw()


def test_plot_thermal_annotations_use_stable_series_keys_and_descending_sources():
    data = Dataset([_tpr(key="a", descending=True), _tpr(key="b", descending=True)])
    fig, ax = plot_thermal(
        data,
        technique="tpr",
        annotations=(ThermalAnnotation(300.0, "peak", series_key="b", rotation=0.0),),
    )
    assert len(ax.texts) == 1
    assert ax.texts[0].get_text() == "peak"
    fig.canvas.draw()

    with pytest.raises(ThermalError, match="require an explicit series_key"):
        plot_thermal(
            data,
            technique="tpr",
            annotations=(ThermalAnnotation(300.0, "peak"),),
        )


def test_plot_thermal_annotation_interpolation_rejects_missing_brackets():
    source = Series(
        x=(100.0, 200.0, 300.0, 400.0),
        y=(0.0, np.nan, 2.0, 0.0),
        key="a",
        x_axis=Axis("temperature", unit="°C"),
        y_axis=Axis("detector_signal", unit="a.u."),
    )
    with pytest.raises(ThermalError, match="finite bracketing"):
        plot_thermal(
            source,
            technique="tpr",
            annotations=(ThermalAnnotation(150.0, "bad"),),
        )


def test_plot_thermal_stacking_uses_shared_figure_spec_and_stable_order():
    data = Dataset([_tpr(key="a"), _tpr(key="b")])
    spec = get_preset("publication").with_layout(
        figure_width_in=4.2,
        figure_height_in=3.1,
    )
    fig, ax = plot_thermal(
        data,
        spec,
        technique="tpr",
        stack_step=2.0,
        stack_start=0.5,
    )
    width, height = fig.get_size_inches()
    assert width == pytest.approx(4.2)
    assert height == pytest.approx(3.1)
    assert len(ax.lines) == 2
    np.testing.assert_allclose(ax.lines[0].get_ydata(), np.asarray(data[0].y) + 0.5)
    np.testing.assert_allclose(ax.lines[1].get_ydata(), np.asarray(data[1].y) + 2.5)
    fig.canvas.draw()


def test_plot_thermal_rejects_incompatible_dtg_sign_state_before_rendering():
    signed = derive_dtg(_tga(key="a"), sign_mode="signed")
    positive = derive_dtg(_tga(key="b"), sign_mode="mass_loss_positive")
    with pytest.raises(ThermalError, match="thermal overlay"):
        plot_thermal(Dataset([signed, positive]), technique="dtg")
