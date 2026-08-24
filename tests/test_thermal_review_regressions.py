from __future__ import annotations

import pytest

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.experimental.characterization import (
    ThermalError,
    ThermalWindow,
    convert_temperature,
    derive_dtg,
    measure_thermal_window,
    normalize_tga_mass,
    validate_dtg_series,
    validate_thermal_overlay,
)


def _raw_mass(key: str, scale: float) -> Series:
    return Series(
        x=(100.0, 200.0, 300.0, 400.0),
        y=(10.0 * scale, 9.0 * scale, 8.0 * scale, 7.0 * scale),
        key=key,
        x_axis=Axis("temperature", unit="°C"),
        y_axis=Axis("mass", unit="mg"),
    )


def test_first_point_normalized_tga_overlay_ignores_sample_specific_reference_value():
    ten_mg = normalize_tga_mass(
        _raw_mass("ten", 1.0),
        output="percent",
        reference="first_point",
    )
    twenty_mg = normalize_tga_mass(
        _raw_mass("twenty", 2.0),
        output="percent",
        reference="first_point",
    )

    assert ten_mg.y_axis.metadata["normalization"] == (
        twenty_mg.y_axis.metadata["normalization"]
    )
    assert ten_mg.y_axis.metadata["normalization_reference_value"] == pytest.approx(10.0)
    assert twenty_mg.y_axis.metadata["normalization_reference_value"] == pytest.approx(20.0)
    validate_thermal_overlay(Dataset([ten_mg, twenty_mg]), technique="tga")


def test_quantitative_window_requires_at_least_one_measured_point():
    source = Series(
        x=(100.0, 200.0, 300.0),
        y=(0.0, 1.0, 0.0),
        x_axis=Axis("temperature", unit="°C"),
        y_axis=Axis("detector_signal", unit="a.u."),
    )
    with pytest.raises(ThermalError, match="no measured temperature points"):
        measure_thermal_window(
            source,
            ThermalWindow(120.0, 180.0),
            technique="tpr",
        )


def test_normalized_percent_dtg_validates_measures_and_converts_temperature():
    normalized = normalize_tga_mass(
        _raw_mass("normalized", 1.0),
        output="percent",
        reference="first_point",
    )
    dtg = derive_dtg(normalized, sign_mode="mass_loss_positive")

    assert dtg.y_axis.unit == "%/°C"
    assert dtg.y_axis.metadata["source_mass_semantic"] == "mass_percent"
    validate_dtg_series(dtg)

    measured = measure_thermal_window(
        dtg,
        ThermalWindow(150.0, 350.0),
        technique="dtg",
        extremum_mode="maximum",
        area_mode="net",
    )
    assert measured.n_measured_points == 2
    assert measured.signal_unit == "%/°C"

    kelvin = convert_temperature(dtg, target_unit="K")
    assert kelvin.y_axis.unit == "%/K"
    validate_dtg_series(kelvin)
