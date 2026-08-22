import numpy as np
import pytest

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.processing import (
    ProcessingError,
    crop,
    integrate,
    interpolate,
    map_dataset,
    normalize,
    offset,
    savgol,
    subtract_baseline,
)


def _series(*, x=(0, 1, 2, 3, 4), y=(0, 1, 4, 9, 16), key="sample"):
    return Series(
        x=x,
        y=y,
        label="Sample",
        x_axis=Axis("x", unit="V", label="Potential"),
        y_axis=Axis("y", unit="mA", label="Current"),
        metadata={"source": {"file_name": "data.csv"}},
        key=key,
    )


def test_crop_is_non_mutating_preserves_order_and_records_provenance():
    source = _series()
    result = crop(source, x_min=1, x_max=3)

    np.testing.assert_allclose(result.x, [1, 2, 3])
    np.testing.assert_allclose(result.y, [1, 4, 9])
    np.testing.assert_allclose(source.x, [0, 1, 2, 3, 4])
    assert result.key == source.key
    assert result.x_axis == source.x_axis
    assert result.metadata["source"]["file_name"] == "data.csv"
    record = result.metadata["processing_history"][-1]
    assert record["operation"] == "crop"
    assert record["parameters"]["x_min"] == 1
    assert record["parameters"]["x_max"] == 3


def test_crop_supports_descending_x_without_reordering():
    source = _series(x=(4, 3, 2, 1, 0), y=(16, 9, 4, 1, 0))
    result = crop(source, x_min=1, x_max=3)

    np.testing.assert_allclose(result.x, [3, 2, 1])
    np.testing.assert_allclose(result.y, [9, 4, 1])


def test_crop_rejects_empty_or_invalid_range():
    source = _series()
    with pytest.raises(ProcessingError, match="requires"):
        crop(source)
    with pytest.raises(ProcessingError, match="x_min"):
        crop(source, x_min=3, x_max=1)
    with pytest.raises(ProcessingError, match="no points"):
        crop(source, x_min=10, x_max=20)


def test_offset_preserves_missing_values_and_appends_history():
    source = _series(y=(1, np.nan, 3, 4, 5))
    first = offset(source, 2)
    second = offset(first, -1)

    assert np.isnan(first.y[1])
    np.testing.assert_allclose(second.y[[0, 2]], [2, 4])
    history = second.metadata["processing_history"]
    assert [item["operation"] for item in history] == ["offset", "offset"]


def test_normalize_max_and_minmax():
    source = _series(y=(2, 4, 6, 8, 10))
    max_norm = normalize(source, method="max")
    minmax_norm = normalize(source, method="minmax")

    np.testing.assert_allclose(max_norm.y, [0.2, 0.4, 0.6, 0.8, 1.0])
    np.testing.assert_allclose(minmax_norm.y, [0.0, 0.25, 0.5, 0.75, 1.0])


def test_normalize_max_abs_preserves_complex_values():
    source = _series(y=(1 + 1j, 2 + 2j, 1 - 1j, 0 + 1j, 0 + 0j))
    result = normalize(source, method="max_abs")

    assert np.iscomplexobj(result.y)
    assert np.max(np.abs(result.y)) == pytest.approx(1.0)


def test_normalize_area_handles_descending_axis_without_sign_flip():
    source = _series(x=(4, 3, 2, 1, 0), y=(1, 1, 1, 1, 1))
    result = normalize(source, method="area")

    assert abs(np.trapezoid(result.y, x=result.x)) == pytest.approx(1.0)


def test_normalize_rejects_missing_or_undefined_denominator():
    with pytest.raises(ProcessingError, match="missing"):
        normalize(_series(y=(1, 2, np.nan, 4, 5)))
    with pytest.raises(ProcessingError, match="zero"):
        normalize(_series(y=(0, 0, 0, 0, 0)), method="max_abs")
    with pytest.raises(ProcessingError, match="complex"):
        normalize(_series(y=(1 + 1j, 2 + 0j, 3 + 0j, 4 + 0j, 5 + 0j)), method="max")


def test_savgol_preserves_quadratic_and_records_parameters():
    source = _series()
    result = savgol(source, window_length=5, polyorder=2)

    np.testing.assert_allclose(result.y, source.y, atol=1e-12)
    record = result.metadata["processing_history"][-1]
    assert record["operation"] == "savgol"
    assert record["parameters"]["window_length"] == 5
    assert record["parameters"]["polyorder"] == 2


def test_savgol_processes_complex_components_without_truncation():
    x = np.arange(7, dtype=float)
    y = x**2 + 1j * (2 * x + 1)
    source = _series(x=x, y=y)
    result = savgol(source, window_length=5, polyorder=2)

    assert np.iscomplexobj(result.y)
    np.testing.assert_allclose(result.y, y, atol=1e-12)


def test_savgol_rejects_missing_values_and_invalid_window():
    with pytest.raises(ProcessingError, match="missing"):
        savgol(_series(y=(1, 2, np.nan, 4, 5)), window_length=5, polyorder=2)
    with pytest.raises(ProcessingError):
        savgol(_series(), window_length=3, polyorder=3)


def test_interpolate_supports_descending_source_and_monotonic_target():
    source = _series(x=(4, 3, 2, 1, 0), y=(8, 6, 4, 2, 0))
    target = np.array([0.5, 1.5, 2.5])
    result = interpolate(source, target)

    np.testing.assert_allclose(result.x, target)
    np.testing.assert_allclose(result.y, [1, 3, 5])
    record = result.metadata["processing_history"][-1]
    assert record["parameters"]["method"] == "linear"
    assert record["parameters"]["target_direction"] == 1
    assert len(record["parameters"]["grid_sha256"]) == 64


def test_interpolate_preserves_complex_y():
    source = _series(x=(0, 1, 2), y=(0 + 0j, 2 + 2j, 4 + 4j))
    result = interpolate(source, [0.5, 1.5])

    np.testing.assert_allclose(result.y, [1 + 1j, 3 + 3j])


def test_interpolate_rejects_duplicate_nonmonotonic_and_extrapolated_x():
    with pytest.raises(ProcessingError, match="monotonic"):
        interpolate(_series(x=(0, 1, 1, 2, 3)), [0.5, 1.5])
    with pytest.raises(ProcessingError, match="monotonic"):
        interpolate(_series(x=(0, 2, 1, 3, 4)), [0.5, 1.5])
    with pytest.raises(ProcessingError, match="extrapolate"):
        interpolate(_series(), [-1, 1])


def test_integrate_reports_signed_and_absolute_area_with_units():
    ascending = _series(x=(0, 1, 2), y=(1, 1, 1))
    descending = _series(x=(2, 1, 0), y=(1, 1, 1))

    result = integrate(ascending)
    signed_desc = integrate(descending)
    absolute_desc = integrate(descending, absolute=True)

    assert result.value == pytest.approx(2.0)
    assert signed_desc.value == pytest.approx(-2.0)
    assert absolute_desc.value == pytest.approx(2.0)
    assert result.method == "trapezoid"
    assert result.source_key == "sample"
    assert result.x_unit == "V"
    assert result.y_unit == "mA"


def test_integrate_rejects_missing_or_nonmonotonic_data():
    with pytest.raises(ProcessingError, match="missing"):
        integrate(_series(x=(0, 1, 2), y=(1, np.nan, 1)))
    with pytest.raises(ProcessingError, match="monotonic"):
        integrate(_series(x=(0, 2, 1), y=(1, 1, 1)))


def test_subtract_baseline_supports_scalar_array_and_aligned_series():
    source = _series(y=(5, 6, 7, 8, 9))
    scalar = subtract_baseline(source, 1)
    array = subtract_baseline(source, [1, 2, 3, 4, 5])
    baseline = Series(
        source.x,
        [1, 1, 1, 1, 1],
        label="baseline",
        x_axis=source.x_axis,
        y_axis=source.y_axis,
        key="baseline",
    )
    aligned = subtract_baseline(source, baseline)

    np.testing.assert_allclose(scalar.y, [4, 5, 6, 7, 8])
    np.testing.assert_allclose(array.y, [4, 4, 4, 4, 4])
    np.testing.assert_allclose(aligned.y, [4, 5, 6, 7, 8])
    assert aligned.metadata["processing_history"][-1]["parameters"]["baseline_key"] == "baseline"


def test_subtract_baseline_rejects_misaligned_series_or_wrong_length():
    source = _series()
    baseline = Series([0, 1, 2, 3, 5], [0, 0, 0, 0, 0])
    with pytest.raises(ProcessingError, match="same x grid"):
        subtract_baseline(source, baseline)
    with pytest.raises(ProcessingError, match="match Series length"):
        subtract_baseline(source, [0, 1])


def test_map_dataset_applies_transform_and_preserves_dataset_metadata():
    first = _series(key="a", y=(1, 2, 3, 4, 5))
    second = _series(key="b", y=(2, 3, 4, 5, 6))
    dataset = Dataset([first, second], name="comparison", metadata={"technique": "generic"})

    result = map_dataset(dataset, offset, 10)

    assert result.name == "comparison"
    assert result.metadata["technique"] == "generic"
    assert result.keys == ("a", "b")
    np.testing.assert_allclose(result[0].y, [11, 12, 13, 14, 15])
    np.testing.assert_allclose(dataset[0].y, [1, 2, 3, 4, 5])


def test_map_dataset_rejects_non_series_transform_result():
    dataset = Dataset([_series()])
    with pytest.raises(TypeError, match="must return Series"):
        map_dataset(dataset, lambda item: integrate(item))
