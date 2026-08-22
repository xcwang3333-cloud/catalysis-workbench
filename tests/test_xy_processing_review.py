import numpy as np
import pytest

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.processing import (
    ProcessingError,
    integrate,
    interpolate,
    normalize,
    subtract_baseline,
)


def _series(*, x=(0.0, 1.0, 2.0), y=(1.0, 2.0, 3.0), key="sample"):
    return Series(
        x=x,
        y=y,
        label="Sample",
        x_axis=Axis("potential", unit="V"),
        y_axis=Axis("current", unit="mA"),
        key=key,
    )


def test_absolute_integration_uses_integral_of_magnitude_without_cancellation():
    series = _series(y=(1.0, -1.0, 1.0))

    signed = integrate(series)
    absolute = integrate(series, absolute=True)

    assert signed.value == pytest.approx(0.0)
    assert absolute.value == pytest.approx(2.0)


def test_area_normalization_has_explicit_absolute_and_net_modes():
    series = _series(y=(1.0, -0.5, 1.0))

    absolute = normalize(series, method="area", area_mode="absolute")
    net = normalize(series, method="area", area_mode="net")

    assert abs(np.trapezoid(np.abs(absolute.y), x=absolute.x)) == pytest.approx(1.0)
    assert abs(np.trapezoid(net.y, x=net.x)) == pytest.approx(1.0)
    assert absolute.metadata["processing_history"][-1]["parameters"]["area_mode"] == "absolute"
    assert net.metadata["processing_history"][-1]["parameters"]["area_mode"] == "net"


def test_area_normalization_net_mode_exposes_complete_cancellation():
    series = _series(y=(1.0, -1.0, 1.0))

    with pytest.raises(ProcessingError, match="zero"):
        normalize(series, method="area", area_mode="net")


def test_max_normalization_rejects_all_non_positive_trace():
    series = _series(y=(-5.0, -2.0, -3.0))

    with pytest.raises(ProcessingError, match="positive maximum"):
        normalize(series, method="max")

    scaled = normalize(series, method="max_abs")
    assert np.max(np.abs(scaled.y)) == pytest.approx(1.0)
    assert np.all(scaled.y <= 0)


def test_interpolation_requires_monotonic_target_but_allows_descending_target():
    series = _series(y=(0.0, 2.0, 4.0))

    with pytest.raises(ProcessingError, match="target grid"):
        interpolate(series, [0.5, 1.5, 1.0])

    descending = interpolate(series, [1.5, 1.0, 0.5])
    np.testing.assert_allclose(descending.y, [3.0, 2.0, 1.0])
    assert descending.metadata["processing_history"][-1]["parameters"]["target_direction"] == -1


def test_baseline_series_requires_matching_axis_semantics_and_units():
    source = _series(y=(5.0, 6.0, 7.0))
    wrong_y_unit = Series(
        x=source.x,
        y=(1.0, 1.0, 1.0),
        x_axis=source.x_axis,
        y_axis=Axis("current", unit="A"),
    )
    wrong_x_unit = Series(
        x=source.x,
        y=(1.0, 1.0, 1.0),
        x_axis=Axis("potential", unit="mV"),
        y_axis=source.y_axis,
    )

    with pytest.raises(ProcessingError, match="y-axis unit"):
        subtract_baseline(source, wrong_y_unit)
    with pytest.raises(ProcessingError, match="x-axis unit"):
        subtract_baseline(source, wrong_x_unit)


def test_integration_result_contains_deterministic_source_provenance_without_key():
    source = _series(x=(2.0, 1.0, 0.0), y=(1.0, 2.0, 3.0), key="")
    first = integrate(source)
    second = integrate(source)

    assert first.source_key == ""
    assert first.n_points == 3
    assert first.x_start == pytest.approx(2.0)
    assert first.x_end == pytest.approx(0.0)
    assert first.x_axis_name == "potential"
    assert first.y_axis_name == "current"
    assert len(first.source_sha256) == 64
    assert first.source_sha256 == second.source_sha256

    changed = integrate(_series(x=(2.0, 1.0, 0.0), y=(1.0, 2.0, 4.0), key=""))
    assert changed.source_sha256 != first.source_sha256
