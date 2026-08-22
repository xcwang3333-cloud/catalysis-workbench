from __future__ import annotations

import subprocess
import sys

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.experimental.characterization import (
    PeakAnnotation,
    XRDError,
    XRDProcessingConfig,
    XRDReferencePattern,
    plot_xrd,
    process_xrd,
)
from catalysis_workbench.visualization import FigureSpec, PlotStyle, VisualizationError


def _pattern(
    *,
    key="sample",
    y=(1.0, 4.0, 2.0, 5.0),
    y_unit="counts",
    y_name="intensity",
    x_unit="deg",
    x_name="two_theta",
):
    return Series(
        x=(10.0, 20.0, 30.0, 40.0),
        y=y,
        label=key,
        key=key,
        x_axis=Axis(x_name, unit=x_unit, label="2theta"),
        y_axis=Axis(y_name, unit=y_unit, label="Intensity"),
    )


def test_plot_xrd_uses_publication_two_theta_label_and_preserves_data():
    source = _pattern()
    _, ax = plot_xrd(source)

    assert ax.get_xlabel() == "2θ (°)"
    assert ax.get_ylabel() == "Intensity (counts)"
    np.testing.assert_allclose(ax.lines[0].get_ydata(), source.y)
    np.testing.assert_allclose(source.y, (1.0, 4.0, 2.0, 5.0))


def test_plot_xrd_respects_slash_and_blank_label_overrides():
    source = _pattern()
    _, ax = plot_xrd(source, FigureSpec(style=PlotStyle(axis_unit_format="slash")))
    assert ax.get_xlabel() == "2θ / °"

    _, ax_blank = plot_xrd(source, FigureSpec(xlabel="", ylabel=""))
    assert ax_blank.get_xlabel() == ""
    assert ax_blank.get_ylabel() == ""


def test_plot_xrd_canonicalizes_equivalent_axis_and_unit_spellings():
    first = _pattern(key="a", x_name="two_theta", x_unit="degree", y_unit="count")
    second = _pattern(
        key="b",
        y=(2.0, 5.0, 3.0, 6.0),
        x_name="2θ",
        x_unit="°",
        y_unit="counts",
    )
    _, ax = plot_xrd(Dataset([first, second]))

    assert len(ax.lines) == 2
    assert ax.get_xlabel() == "2θ (°)"
    assert ax.get_ylabel() == "Intensity (counts)"
    assert first.x_axis.name == "two_theta"
    assert first.x_axis.unit == "degree"
    assert second.x_axis.name == "2θ"
    assert second.x_axis.unit == "°"


def test_plot_xrd_stacked_dataset_is_non_mutating():
    dataset = Dataset(
        [
            _pattern(key="a", y=(0.0, 1.0, 2.0, 1.0)),
            _pattern(key="b", y=(0.0, 2.0, 4.0, 2.0)),
        ]
    )
    _, ax = plot_xrd(dataset, stack_step=3.0, stack_start=1.0)

    np.testing.assert_allclose(ax.lines[0].get_ydata(), (1.0, 2.0, 3.0, 2.0))
    np.testing.assert_allclose(ax.lines[1].get_ydata(), (4.0, 6.0, 8.0, 6.0))
    np.testing.assert_allclose(dataset[1].y, (0.0, 2.0, 4.0, 2.0))


def test_peak_annotations_require_stable_key_for_multi_pattern_data():
    dataset = Dataset(
        [
            _pattern(key="a"),
            _pattern(key="b", y=(2.0, 5.0, 3.0, 6.0)),
        ]
    )
    with pytest.raises(XRDError, match="require an explicit series_key"):
        plot_xrd(dataset, peak_annotations=[PeakAnnotation(20.0, "(111)")])

    _, ax = plot_xrd(
        dataset,
        peak_annotations=[PeakAnnotation(20.0, "(111)", series_key="b")],
    )
    assert any(text.get_text() == "(111)" for text in ax.texts)


def test_peak_annotation_outside_pattern_range_fails_explicitly():
    with pytest.raises(XRDError, match="outside the selected pattern range"):
        plot_xrd(_pattern(), peak_annotations=[PeakAnnotation(50.0, "outside")])


def test_reference_sticks_do_not_change_experimental_limits_and_are_range_filtered():
    source = _pattern()
    spec = FigureSpec(xlim=(15.0, 35.0), ylim=(0.0, 6.0))
    _, ax = plot_xrd(
        source,
        spec,
        reference_patterns=[
            XRDReferencePattern(
                [5.0, 25.0, 50.0],
                [10.0, 100.0, 50.0],
                label="phase A",
            )
        ],
    )

    assert ax.get_xlim() == pytest.approx((15.0, 35.0))
    assert ax.get_ylim() == pytest.approx((0.0, 6.0))
    assert any(text.get_text() == "phase A" for text in ax.texts)
    assert len(ax.collections) == 1
    segments = ax.collections[0].get_segments()
    assert len(segments) == 1
    assert segments[0][0, 0] == pytest.approx(25.0)


def test_plot_xrd_inherits_shared_unit_compatibility_guard():
    dataset = Dataset(
        [
            _pattern(key="a", y_unit="counts"),
            _pattern(key="b", y_unit="cps"),
        ]
    )
    with pytest.raises(VisualizationError, match="y-axis names and units"):
        plot_xrd(dataset)


def test_plot_xrd_rejects_incompatible_normalization_recipes():
    source_a = _pattern(key="a")
    source_b = _pattern(key="b", y=(2.0, 8.0, 4.0, 10.0))
    max_one = process_xrd(
        source_a,
        XRDProcessingConfig(normalization="max", normalization_target=1.0),
    )
    max_hundred = process_xrd(
        source_b,
        XRDProcessingConfig(normalization="max", normalization_target=100.0),
    )
    with pytest.raises(VisualizationError, match="normalization"):
        plot_xrd(Dataset([max_one, max_hundred]))

    area_one = process_xrd(
        source_b,
        XRDProcessingConfig(normalization="area", normalization_target=1.0),
    )
    with pytest.raises(VisualizationError, match="normalization"):
        plot_xrd(Dataset([max_one, area_one]))


def test_plot_xrd_rejects_invalid_two_theta_and_intensity_units():
    with pytest.raises(XRDError, match="2theta unit"):
        plot_xrd(_pattern(x_unit="rad"))
    with pytest.raises(XRDError, match="unsupported XRD intensity unit"):
        plot_xrd(_pattern(y_unit="mA"))
    with pytest.raises(XRDError, match="normalized_intensity"):
        plot_xrd(_pattern(y_name="normalized_intensity", y_unit="counts"))


def test_importing_characterization_keeps_matplotlib_lazy():
    code = (
        "import sys; "
        "import catalysis_workbench.experimental.characterization; "
        "assert 'catalysis_workbench.visualization' not in sys.modules; "
        "assert 'matplotlib' not in sys.modules"
    )
    subprocess.run([sys.executable, "-c", code], check=True)
