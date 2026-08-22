from __future__ import annotations

import subprocess
import sys

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.experimental.characterization import (
    RamanError,
    RamanPeakAnnotation,
    RamanProcessingConfig,
    plot_raman,
    process_raman,
)
from catalysis_workbench.visualization import FigureSpec, PlotStyle, VisualizationError


def _spectrum(
    *,
    key="sample",
    x_name="raman_shift",
    x_unit="cm^-1",
    y=(1.0, 4.0, 2.0, 5.0),
    y_unit="counts",
):
    return Series(
        x=(1000.0, 1200.0, 1400.0, 1600.0),
        y=y,
        label=key,
        key=key,
        x_axis=Axis(x_name, unit=x_unit, label="Raman shift"),
        y_axis=Axis("intensity", unit=y_unit, label="Intensity"),
    )


def test_plot_raman_uses_publication_label_and_preserves_data():
    source = _spectrum()
    _, ax = plot_raman(source)
    assert ax.get_xlabel() == "Raman shift (cm⁻¹)"
    assert ax.get_ylabel() == "Intensity (counts)"
    np.testing.assert_allclose(ax.lines[0].get_ydata(), source.y)
    np.testing.assert_allclose(source.y, (1.0, 4.0, 2.0, 5.0))


def test_plot_raman_respects_slash_and_blank_label_overrides():
    source = _spectrum()
    _, ax = plot_raman(source, FigureSpec(style=PlotStyle(axis_unit_format="slash")))
    assert ax.get_xlabel() == "Raman shift / cm⁻¹"

    _, ax_blank = plot_raman(source, FigureSpec(xlabel="", ylabel=""))
    assert ax_blank.get_xlabel() == ""
    assert ax_blank.get_ylabel() == ""


def test_plot_raman_canonicalizes_equivalent_aliases_without_mutating_sources():
    first = _spectrum(key="a", x_name="raman_shift", x_unit="cm^-1", y_unit="count")
    second = _spectrum(key="b", x_name="Shift", x_unit="cm⁻¹", y_unit="counts")
    dataset = Dataset([first, second])

    _, ax = plot_raman(dataset)
    assert len(ax.lines) == 2
    assert first.x_axis.name == "raman_shift"
    assert first.x_axis.unit == "cm^-1"
    assert second.x_axis.name == "Shift"
    assert second.x_axis.unit == "cm⁻¹"


def test_plot_raman_rejects_genuinely_different_intensity_bases():
    dataset = Dataset(
        [
            _spectrum(key="a", y_unit="counts"),
            _spectrum(key="b", y_unit="cps"),
        ]
    )
    with pytest.raises(VisualizationError, match="y-axis names and units"):
        plot_raman(dataset)


def test_plot_raman_rejects_different_normalization_recipes():
    one = process_raman(
        _spectrum(key="a"),
        RamanProcessingConfig(normalization="max", normalization_target=1.0),
    )
    hundred = process_raman(
        _spectrum(key="b"),
        RamanProcessingConfig(normalization="max", normalization_target=100.0),
    )
    with pytest.raises(VisualizationError, match="normalization"):
        plot_raman(Dataset([one, hundred]))


def test_plot_raman_stacked_dataset_is_non_mutating():
    dataset = Dataset(
        [
            _spectrum(key="a", y=(0.0, 1.0, 2.0, 1.0)),
            _spectrum(key="b", y=(0.0, 2.0, 4.0, 2.0)),
        ]
    )
    _, ax = plot_raman(dataset, stack_step=3.0, stack_start=1.0)
    np.testing.assert_allclose(ax.lines[0].get_ydata(), (1.0, 2.0, 3.0, 2.0))
    np.testing.assert_allclose(ax.lines[1].get_ydata(), (4.0, 6.0, 8.0, 6.0))
    np.testing.assert_allclose(dataset[1].y, (0.0, 2.0, 4.0, 2.0))


def test_raman_peak_annotations_require_stable_key_for_multi_spectrum_data():
    dataset = Dataset(
        [
            _spectrum(key="a"),
            _spectrum(key="b", y=(2.0, 5.0, 3.0, 6.0)),
        ]
    )
    with pytest.raises(RamanError, match="explicit series_key"):
        plot_raman(
            dataset,
            peak_annotations=[RamanPeakAnnotation(1400.0, "D")],
        )

    _, ax = plot_raman(
        dataset,
        peak_annotations=[RamanPeakAnnotation(1400.0, "D", series_key="b")],
    )
    assert any(text.get_text() == "D" for text in ax.texts)


def test_raman_peak_annotation_outside_range_fails_explicitly():
    with pytest.raises(RamanError, match="outside the spectrum range"):
        plot_raman(
            _spectrum(),
            peak_annotations=[RamanPeakAnnotation(2000.0, "outside")],
        )


def test_plot_raman_rejects_invalid_shift_unit():
    with pytest.raises(RamanError, match="Raman-shift unit"):
        plot_raman(_spectrum(x_unit="nm"))


def test_importing_characterization_keeps_matplotlib_lazy_with_raman_api():
    code = (
        "import sys; "
        "import catalysis_workbench.experimental.characterization; "
        "assert 'catalysis_workbench.visualization' not in sys.modules; "
        "assert 'matplotlib' not in sys.modules"
    )
    subprocess.run([sys.executable, "-c", code], check=True)
