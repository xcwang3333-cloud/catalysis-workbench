from __future__ import annotations

import matplotlib
import numpy as np
import pytest

matplotlib.use("Agg")

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.experimental.characterization import (
    FTIRError,
    FTIRPeakAnnotation,
    plot_ftir,
)
from catalysis_workbench.visualization import get_preset


def _spectrum(*, key="a", descending=False, normalized=False):
    x = np.array([1000.0, 1100.0, 1200.0, 1300.0, 1400.0])
    y = np.array([0.0, 1.0, 2.0, 1.0, 0.0])
    if descending:
        x = x[::-1]
        y = y[::-1]
    if normalized:
        y_axis = Axis(
            "normalized_absorbance",
            unit="a.u.",
            metadata={"normalization": "ftir:max:target=1.0"},
        )
    else:
        y_axis = Axis("absorbance")
    return Series(
        x=x,
        y=y,
        key=key,
        label=key,
        x_axis=Axis("wavenumber", unit="cm^-1"),
        y_axis=y_axis,
    )


def test_plot_ftir_defaults_to_conventional_descending_display_without_mutating_data():
    source = _spectrum(descending=False)
    original = np.array(source.x, copy=True)
    fig, ax = plot_ftir(source)
    assert ax.get_xlim()[0] > ax.get_xlim()[1]
    np.testing.assert_allclose(source.x, original)
    assert "Wavenumber" in ax.get_xlabel()
    fig.canvas.draw()


def test_plot_ftir_preserves_explicit_empty_axis_label_contract():
    spec = get_preset("publication").updated(xlabel="")
    fig, ax = plot_ftir(_spectrum(), spec)
    assert ax.get_xlabel() == ""
    fig.canvas.draw()


def test_plot_ftir_preserves_explicit_xlim_while_applying_display_direction():
    spec = get_preset("publication").updated(xlim=(1050.0, 1350.0))
    fig_desc, ax_desc = plot_ftir(
        _spectrum(),
        spec,
        wavenumber_direction="descending",
    )
    assert ax_desc.get_xlim() == pytest.approx((1350.0, 1050.0))
    fig_desc.canvas.draw()

    fig_asc, ax_asc = plot_ftir(
        _spectrum(descending=True),
        spec,
        wavenumber_direction="ascending",
    )
    assert ax_asc.get_xlim() == pytest.approx((1050.0, 1350.0))
    fig_asc.canvas.draw()


def test_plot_ftir_can_follow_source_or_force_ascending_direction():
    descending = _spectrum(descending=True)
    fig_source, ax_source = plot_ftir(descending, wavenumber_direction="source")
    assert ax_source.get_xlim()[0] > ax_source.get_xlim()[1]
    fig_source.canvas.draw()

    fig_ascending, ax_ascending = plot_ftir(
        descending,
        wavenumber_direction="ascending",
    )
    assert ax_ascending.get_xlim()[0] < ax_ascending.get_xlim()[1]
    fig_ascending.canvas.draw()


def test_plot_ftir_source_direction_rejects_mixed_storage_directions():
    data = Dataset([_spectrum(key="a"), _spectrum(key="b", descending=True)])
    with pytest.raises(FTIRError, match="share source direction"):
        plot_ftir(data, wavenumber_direction="source")


def test_plot_ftir_annotations_use_stable_keys_and_work_on_descending_data():
    data = Dataset([_spectrum(key="a", descending=True), _spectrum(key="b", descending=True)])
    fig, ax = plot_ftir(
        data,
        peak_annotations=(
            FTIRPeakAnnotation(1200.0, "band", series_key="b", rotation=0.0),
        ),
    )
    assert len(ax.texts) == 1
    assert ax.texts[0].get_text() == "band"
    fig.canvas.draw()

    with pytest.raises(FTIRError, match="require an explicit series_key"):
        plot_ftir(data, peak_annotations=(FTIRPeakAnnotation(1200.0, "band"),))


def test_plot_ftir_rejects_mixed_normalization_state_before_rendering():
    data = Dataset([_spectrum(key="a"), _spectrum(key="b", normalized=True)])
    with pytest.raises(FTIRError, match="matching y semantic"):
        plot_ftir(data)


def test_plot_ftir_stacking_uses_shared_figure_spec():
    data = Dataset([_spectrum(key="a"), _spectrum(key="b")])
    spec = get_preset("publication").with_layout(
        figure_width_in=4.0,
        figure_height_in=3.0,
    )
    fig, ax = plot_ftir(data, spec, stack_step=2.5, stack_start=0.5)
    width, height = fig.get_size_inches()
    assert width == pytest.approx(4.0)
    assert height == pytest.approx(3.0)
    assert len(ax.lines) == 2
    fig.canvas.draw()
