from __future__ import annotations

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.experimental.characterization import (
    XRDError,
    XRDProcessingConfig,
    XRDReferencePattern,
    process_xrd,
    process_xrd_dataset,
    stack_xrd_dataset,
    validate_xrd_series,
)


def _pattern(
    *,
    key="sample",
    x=(10.0, 20.0, 30.0, 40.0),
    y=(2.0, 4.0, 8.0, 4.0),
    x_name="two_theta",
    x_unit="deg",
    y_name="intensity",
    y_unit="counts",
):
    return Series(
        x=x,
        y=y,
        label=key,
        key=key,
        x_axis=Axis(x_name, unit=x_unit, label="2theta"),
        y_axis=Axis(y_name, unit=y_unit, label="Intensity"),
    )


@pytest.mark.parametrize("name", ["two_theta", "2theta", "2_theta", "2θ"])
@pytest.mark.parametrize("unit", ["deg", "degree", "degrees", "°"])
def test_validate_xrd_accepts_common_two_theta_semantics(name, unit):
    validate_xrd_series(_pattern(x_name=name, x_unit=unit))


def test_validate_xrd_rejects_bad_semantics_units_and_grid():
    with pytest.raises(XRDError, match="x_axis.name"):
        validate_xrd_series(_pattern(x_name="time"))
    with pytest.raises(XRDError, match="2theta unit"):
        validate_xrd_series(_pattern(x_unit="rad"))
    with pytest.raises(XRDError, match="y_axis.name"):
        validate_xrd_series(_pattern(y_name="current"))
    with pytest.raises(XRDError, match="strictly increasing"):
        validate_xrd_series(_pattern(x=(10.0, 20.0, 20.0, 40.0)))


def test_process_xrd_reuses_shared_baseline_crop_normalize_and_offset():
    source = _pattern()
    result = process_xrd(
        source,
        XRDProcessingConfig(
            x_min_deg=20.0,
            x_max_deg=40.0,
            normalization="max",
            vertical_offset=0.5,
        ),
        baseline=2.0,
    )

    np.testing.assert_allclose(result.x, (20.0, 30.0, 40.0))
    np.testing.assert_allclose(result.y, (0.5 + 2 / 6, 1.5, 0.5 + 2 / 6))
    assert result.y_axis.name == "normalized_intensity"
    assert result.y_axis.unit == "a.u."
    assert result.y_axis.metadata["normalization_method"] == "max"
    assert [item["operation"] for item in result.metadata["processing_history"]] == [
        "subtract_baseline",
        "crop",
        "normalize",
        "offset",
    ]
    np.testing.assert_allclose(source.y, (2.0, 4.0, 8.0, 4.0))


def test_process_xrd_dataset_supports_keyed_overrides_and_baselines():
    dataset = Dataset(
        [
            _pattern(key="a"),
            _pattern(key="b", y=(5.0, 10.0, 15.0, 10.0)),
        ],
        metadata={"campaign": "demo"},
    )
    result = process_xrd_dataset(
        dataset,
        XRDProcessingConfig(normalization="max"),
        overrides={
            "b": XRDProcessingConfig(normalization="max", vertical_offset=2.0)
        },
        baselines={"a": 1.0},
    )

    assert result.keys == ("a", "b")
    assert result.metadata["campaign"] == "demo"
    np.testing.assert_allclose(result[0].y, (1 / 7, 3 / 7, 1.0, 3 / 7))
    np.testing.assert_allclose(
        result[1].y,
        (2 + 1 / 3, 2 + 2 / 3, 3.0, 2 + 2 / 3),
    )


def test_process_xrd_dataset_rejects_unknown_keys():
    dataset = Dataset([_pattern(key="a")])
    with pytest.raises(XRDError, match="override keys not present"):
        process_xrd_dataset(
            dataset,
            XRDProcessingConfig(),
            overrides={"missing": XRDProcessingConfig()},
        )
    with pytest.raises(XRDError, match="baseline keys not present"):
        process_xrd_dataset(
            dataset,
            XRDProcessingConfig(),
            baselines={"missing": 1.0},
        )


def test_stack_xrd_dataset_is_non_mutating_and_records_provenance():
    dataset = Dataset(
        [
            _pattern(key="a", y=(0.0, 1.0, 2.0, 1.0)),
            _pattern(key="b", y=(0.0, 2.0, 4.0, 2.0)),
        ]
    )
    stacked = stack_xrd_dataset(dataset, step=3.0, start=1.0)

    np.testing.assert_allclose(stacked[0].y, (1.0, 2.0, 3.0, 2.0))
    np.testing.assert_allclose(stacked[1].y, (4.0, 6.0, 8.0, 6.0))
    np.testing.assert_allclose(dataset[0].y, (0.0, 1.0, 2.0, 1.0))
    assert stacked.metadata["xrd_stack_history"][-1]["step"] == 3.0
    assert stacked[1].metadata["processing_history"][-1]["operation"] == "offset"


def test_reference_pattern_validation():
    reference = XRDReferencePattern(
        [20.0, 30.0],
        [20.0, 100.0],
        label="reference",
    )
    assert reference.positions_deg == (20.0, 30.0)
    assert reference.intensities == (20.0, 100.0)
    with pytest.raises(XRDError, match="match reference positions"):
        XRDReferencePattern([20.0, 30.0], [1.0])
    with pytest.raises(XRDError, match="between 0 and 180"):
        XRDReferencePattern([181.0])
