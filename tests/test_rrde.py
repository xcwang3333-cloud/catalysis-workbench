import numpy as np
import pytest

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.echem.rrde import (
    RRDEError,
    rrde_metrics,
    rrde_result_series,
)


def _pair(
    *,
    disk_y=(-1.0, -2.0),
    ring_y=(100.0, 200.0),
    disk_unit="mA",
    ring_unit="uA",
    disk_x=(0.8, 0.7),
    ring_x=(0.8, 0.7),
    disk_key="disk",
    ring_key="ring",
):
    x_axis = Axis("potential", unit="V", metadata={"reference": "RHE"})
    disk = Series(
        x=disk_x,
        y=disk_y,
        key=disk_key,
        label="sample",
        x_axis=x_axis,
        y_axis=Axis("current", unit=disk_unit),
    )
    ring = Series(
        x=ring_x,
        y=ring_y,
        key=ring_key,
        label="ring",
        x_axis=x_axis,
        y_axis=Axis("current", unit=ring_unit),
    )
    return disk, ring


def test_rrde_magnitude_hand_calculation_and_unit_conversion():
    disk, ring = _pair()
    result = rrde_metrics(
        disk,
        ring,
        collection_efficiency=0.5,
        current_mode="magnitude",
    )

    np.testing.assert_allclose(result.disk_current_a, [-1e-3, -2e-3])
    np.testing.assert_allclose(result.ring_current_a, [1e-4, 2e-4])
    np.testing.assert_allclose(result.electron_number, [10.0 / 3.0, 10.0 / 3.0])
    np.testing.assert_allclose(result.peroxide_percent, [100.0 / 3.0, 100.0 / 3.0])
    assert result.collection_efficiency == 0.5
    assert result.current_mode == "magnitude"
    assert result.disk_source.key == "disk"
    assert result.ring_source.key == "ring"


def test_rrde_nonnegative_mode_requires_prepared_nonnegative_currents():
    disk, ring = _pair()
    with pytest.raises(RRDEError, match="nonnegative"):
        rrde_metrics(
            disk,
            ring,
            collection_efficiency=0.5,
            current_mode="nonnegative",
        )

    positive_disk, positive_ring = _pair(
        disk_y=(1.0, 2.0),
        ring_y=(0.1, 0.2),
        disk_unit="mA",
        ring_unit="mA",
    )
    result = rrde_metrics(
        positive_disk,
        positive_ring,
        collection_efficiency=0.5,
        current_mode="nonnegative",
    )
    np.testing.assert_allclose(result.electron_number, [10.0 / 3.0, 10.0 / 3.0])


def test_rrde_does_not_clip_out_of_range_derived_values():
    disk, ring = _pair(
        disk_y=(0.0, 0.0),
        ring_y=(1.0, 2.0),
        disk_unit="mA",
        ring_unit="mA",
    )
    result = rrde_metrics(
        disk,
        ring,
        collection_efficiency=0.5,
        current_mode="nonnegative",
    )
    np.testing.assert_allclose(result.electron_number, [0.0, 0.0])
    np.testing.assert_allclose(result.peroxide_percent, [200.0, 200.0])


def test_rrde_zero_denominator_rejected():
    disk, ring = _pair(
        disk_y=(0.0, 1.0),
        ring_y=(0.0, 1.0),
        disk_unit="mA",
        ring_unit="mA",
    )
    with pytest.raises(RRDEError, match="denominator"):
        rrde_metrics(
            disk,
            ring,
            collection_efficiency=0.5,
            current_mode="nonnegative",
        )


@pytest.mark.parametrize("efficiency", [0.0, -0.1, 1.1, np.nan, np.inf, True])
def test_rrde_collection_efficiency_validation(efficiency):
    disk, ring = _pair()
    with pytest.raises(RRDEError):
        rrde_metrics(
            disk,
            ring,
            collection_efficiency=efficiency,
            current_mode="magnitude",
        )


def test_rrde_requires_exact_condition_alignment_without_interpolation():
    disk, ring = _pair(ring_x=(0.8, 0.69))
    with pytest.raises(RRDEError, match="exactly aligned"):
        rrde_metrics(
            disk,
            ring,
            collection_efficiency=0.5,
            current_mode="magnitude",
        )


def test_rrde_requires_matching_condition_reference():
    disk, ring = _pair()
    ring = Series(
        x=ring.x,
        y=ring.y,
        key=ring.key,
        x_axis=Axis("potential", unit="V", metadata={"reference": "Ag/AgCl"}),
        y_axis=ring.y_axis,
    )
    with pytest.raises(RRDEError, match="reference"):
        rrde_metrics(
            disk,
            ring,
            collection_efficiency=0.5,
            current_mode="magnitude",
        )


def test_rrde_rejects_current_density_and_duplicate_or_missing_keys():
    disk, ring = _pair()
    disk_density = Series(
        x=disk.x,
        y=disk.y,
        key=disk.key,
        x_axis=disk.x_axis,
        y_axis=Axis(
            "current_density",
            unit="mA/cm^2",
            metadata={"normalization": "geometric_area"},
        ),
    )
    with pytest.raises(RRDEError, match="y_axis.name"):
        rrde_metrics(
            disk_density,
            ring,
            collection_efficiency=0.5,
            current_mode="magnitude",
        )

    duplicate_disk, duplicate_ring = _pair(disk_key="same", ring_key="same")
    with pytest.raises(RRDEError, match="distinct"):
        rrde_metrics(
            duplicate_disk,
            duplicate_ring,
            collection_efficiency=0.5,
            current_mode="magnitude",
        )

    missing_disk, missing_ring = _pair(disk_key="", ring_key="ring")
    with pytest.raises(RRDEError, match="stable keys"):
        rrde_metrics(
            missing_disk,
            missing_ring,
            collection_efficiency=0.5,
            current_mode="magnitude",
        )


def test_rrde_result_series_carries_provenance_and_semantics():
    disk, ring = _pair()
    result = rrde_metrics(
        disk,
        ring,
        collection_efficiency=0.5,
        current_mode="magnitude",
    )
    electron_series = rrde_result_series(result, "electron_number")
    peroxide_series = rrde_result_series(result, "peroxide_percent")

    assert electron_series.y_axis.name == "electron_number"
    assert electron_series.y_axis.metadata["collection_efficiency"] == 0.5
    assert electron_series.y_axis.metadata["current_mode"] == "magnitude"
    assert peroxide_series.y_axis.name == "peroxide_yield"
    assert peroxide_series.y_axis.unit == "%"
    assert electron_series.metadata["disk_source_sha256"] == result.disk_source.sha256
    assert electron_series.metadata["ring_source_sha256"] == result.ring_source.sha256
