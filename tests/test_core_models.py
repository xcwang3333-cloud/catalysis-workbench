import numpy as np
import pytest

from catalysis_workbench.core import Axis, Dataset, Series


def test_axis_keeps_semantic_label_unit_and_metadata_separate():
    source = {"reference": "RHE", "tags": ["corrected"]}
    axis = Axis("potential", unit="V", label="Potential", metadata=source)

    source["tags"].append("mutated")

    assert axis.name == "potential"
    assert axis.label == "Potential"
    assert axis.unit == "V"
    assert axis.metadata["reference"] == "RHE"
    assert axis.metadata["tags"] == ("corrected",)

    with pytest.raises(TypeError):
        axis.metadata["new"] = "value"


def test_series_coerces_real_numeric_input_and_detaches_source_memory():
    source_x = [0, 1, 2]
    source_y = np.array([3, 4, 5], dtype=float)
    series = Series(source_x, source_y, label="Pb3-N/C")

    source_y[0] = 99

    assert series.n_points == 3
    assert series.label == "Pb3-N/C"
    assert series.x.dtype == np.float64
    assert series.y.dtype == np.float64
    np.testing.assert_allclose(series.x, [0.0, 1.0, 2.0])
    np.testing.assert_allclose(series.y, [3.0, 4.0, 5.0])
    assert not series.x.flags.writeable
    assert not series.y.flags.writeable

    with pytest.raises(ValueError):
        series.y[0] = 1.0


def test_series_backing_arrays_cannot_be_made_writeable():
    series = Series([0, 1], [2, 3])

    with pytest.raises(ValueError):
        series.x.setflags(write=True)
    with pytest.raises(ValueError):
        series.y.setflags(write=True)

    np.testing.assert_allclose(series.x, [0, 1])
    np.testing.assert_allclose(series.y, [2, 3])


def test_series_preserves_complex_values_without_silent_truncation():
    impedance = np.array([10 + 2j, 8 - 3j], dtype=np.complex128)
    series = Series(x=[1, 10], y=impedance, label="EIS")

    assert series.y.dtype == np.complex128
    np.testing.assert_allclose(series.y, impedance)
    assert np.any(np.imag(series.y) != 0)

    with pytest.raises(ValueError):
        series.y.setflags(write=True)


@pytest.mark.parametrize(
    ("x", "y", "error_type"),
    [
        ([0, 1], [1], ValueError),
        ([[0, 1]], [1, 2], ValueError),
        ([0, np.inf], [1, 2], ValueError),
        (["not-a-number"], [1], TypeError),
    ],
)
def test_series_validation(x, y, error_type):
    with pytest.raises(error_type):
        Series(x=x, y=y)


def test_series_allows_nan_and_reports_missing_values():
    series = Series(x=[0, 1, 2], y=[1.0, np.nan, 3.0])
    assert series.has_missing


def test_with_data_preserves_axes_and_metadata():
    x_axis = Axis("potential", unit="V vs RHE", label="Potential")
    y_axis = Axis("current_density", unit="mA cm^-2", label="Current density")
    series = Series(
        x=[0, 1],
        y=[2, 3],
        label="Pb3-N/C",
        x_axis=x_axis,
        y_axis=y_axis,
        metadata={"reaction": "CO2RR"},
    )

    transformed = series.with_data(y=[4, 5])

    assert transformed is not series
    assert transformed.x_axis == x_axis
    assert transformed.y_axis == y_axis
    assert transformed.metadata["reaction"] == "CO2RR"
    np.testing.assert_allclose(transformed.y, [4, 5])
    np.testing.assert_allclose(series.y, [2, 3])


def test_with_metadata_returns_new_series_without_mutating_original():
    series = Series([0, 1], [2, 3], metadata={"step": "raw"})
    updated = series.with_metadata(step="normalized", factor=2.0)

    assert series.metadata["step"] == "raw"
    assert updated.metadata["step"] == "normalized"
    assert updated.metadata["factor"] == 2.0


def test_dataset_supports_multi_catalyst_comparison_and_duplicate_labels():
    pb1 = Series([0, 1], [1, 2], label="Pb1-N/C")
    pb3_a = Series([0, 1], [3, 4], label="Pb3-N/C", metadata={"replicate": 1})
    pb3_b = Series([0, 1], [3.1, 4.1], label="Pb3-N/C", metadata={"replicate": 2})

    dataset = Dataset([pb1, pb3_a, pb3_b], name="LSV comparison")

    assert len(dataset) == 3
    assert dataset.labels == ("Pb1-N/C", "Pb3-N/C", "Pb3-N/C")
    assert dataset.by_label("Pb3-N/C") == (pb3_a, pb3_b)


def test_dataset_transformations_are_non_mutating_and_preserve_metadata():
    pb1 = Series([0, 1], [1, 2], label="Pb1-N/C")
    pb3 = Series([0, 1], [3, 4], label="Pb3-N/C")
    dataset = Dataset([pb1], name="LSV", metadata={"electrolyte": "0.1 M KHCO3"})

    extended = dataset.append(pb3)
    selected = extended.select(["Pb3-N/C"])

    assert len(dataset) == 1
    assert len(extended) == 2
    assert selected.labels == ("Pb3-N/C",)
    assert selected.metadata["electrolyte"] == "0.1 M KHCO3"


def test_dataset_slice_returns_dataset():
    series = [
        Series([0, 1], [index, index + 1], label=str(index))
        for index in range(3)
    ]
    dataset = Dataset(series, name="comparison")

    sliced = dataset[1:]

    assert isinstance(sliced, Dataset)
    assert sliced.labels == ("1", "2")
    assert sliced.name == "comparison"


def test_series_value_equality_handles_numpy_arrays_and_nan():
    first = Series(
        [0, 1],
        [1.0, np.nan],
        label="same",
        metadata={"vector": np.array([1, 2])},
    )
    second = Series(
        [0, 1],
        [1.0, np.nan],
        label="same",
        metadata={"vector": np.array([1, 2])},
    )

    assert first == second
    assert first.equals(second)


def test_series_value_equality_handles_complex_values():
    first = Series([0, 1], [1 + 2j, 3 - 4j], label="EIS")
    second = Series([0, 1], [1 + 2j, 3 - 4j], label="EIS")

    assert first == second


def test_dataset_value_equality_is_order_sensitive():
    a = Series([0, 1], [1, 2], label="A")
    b = Series([0, 1], [3, 4], label="B")

    assert Dataset([a, b]) == Dataset([a.copy(), b.copy()])
    assert Dataset([a, b]) != Dataset([b, a])
