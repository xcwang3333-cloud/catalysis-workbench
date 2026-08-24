from __future__ import annotations

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.experimental.characterization import (
    ThermalError,
    ThermalProcessingConfig,
    ThermalWindow,
    convert_temperature,
    derive_dtg,
    measure_thermal_window,
    normalize_tga_mass,
    process_thermal,
    process_thermal_dataset,
    stack_thermal_dataset,
    validate_dtg_series,
    validate_temperature_programmed_series,
    validate_tga_series,
    validate_thermal_overlay,
)


def _tga(
    *,
    key: str = "sample",
    descending: bool = False,
    x_unit: str = "°C",
    y_name: str = "mass",
    y_unit: str = "mg",
    y=(10.0, 9.0, 8.0, 7.0),
    y_metadata=None,
) -> Series:
    x = np.array([100.0, 200.0, 300.0, 400.0])
    values = np.asarray(y, dtype=float)
    if descending:
        x = x[::-1]
        values = values[::-1]
    return Series(
        x=x,
        y=values,
        key=key,
        label=key,
        x_axis=Axis("temperature", unit=x_unit),
        y_axis=Axis(
            y_name,
            unit=y_unit,
            metadata={} if y_metadata is None else y_metadata,
        ),
    )


def _programmed(
    *,
    key: str = "signal",
    technique: str | None = None,
    unit: str = "a.u.",
    descending: bool = False,
) -> Series:
    x = np.array([100.0, 200.0, 300.0, 400.0, 500.0])
    y = np.array([0.0, 1.0, 3.0, 1.0, 0.0])
    if descending:
        x = x[::-1]
        y = y[::-1]
    metadata = {} if technique is None else {"thermal_technique": technique}
    return Series(
        x=x,
        y=y,
        key=key,
        label=key,
        x_axis=Axis("temperature", unit="°C"),
        y_axis=Axis("detector_signal", unit=unit, metadata=metadata),
    )


@pytest.mark.parametrize("unit", ["°C", "degC", "C", "celsius"])
def test_tga_accepts_explicit_celsius_aliases_and_both_storage_directions(unit):
    validate_tga_series(_tga(x_unit=unit))
    validate_tga_series(_tga(x_unit=unit, descending=True))


def test_tga_validation_rejects_implicit_or_invalid_scientific_semantics():
    with pytest.raises(ThermalError, match="x_axis.name"):
        bad = _tga()
        bad = Series(
            x=bad.x,
            y=bad.y,
            key=bad.key,
            x_axis=Axis("time", unit="s"),
            y_axis=bad.y_axis,
        )
        validate_tga_series(bad)
    with pytest.raises(ThermalError, match="temperature unit"):
        validate_tga_series(_tga(x_unit="F"))
    with pytest.raises(ThermalError, match="raw TGA mass"):
        validate_tga_series(_tga(y_unit=""))
    with pytest.raises(ThermalError, match="strictly monotonic"):
        source = _tga()
        validate_tga_series(
            Series(
                x=(100.0, 200.0, 200.0, 400.0),
                y=source.y,
                x_axis=source.x_axis,
                y_axis=source.y_axis,
            )
        )


def test_explicit_temperature_conversion_preserves_data_order_and_records_provenance():
    source = _tga(descending=True)
    kelvin = convert_temperature(source, target_unit="K")
    np.testing.assert_allclose(kelvin.x, np.asarray(source.x) + 273.15)
    np.testing.assert_allclose(kelvin.y, source.y)
    assert kelvin.x_axis.unit == "K"
    assert kelvin.metadata["processing_history"][-1]["operation"] == "convert_temperature"

    restored = convert_temperature(kelvin, target_unit="degC")
    np.testing.assert_allclose(restored.x, source.x)
    assert restored.x_axis.unit == "°C"


def test_temperature_conversion_rejects_unphysical_kelvin():
    source = Series(
        x=(-300.0, -280.0, -260.0),
        y=(1.0, 0.9, 0.8),
        x_axis=Axis("temperature", unit="°C"),
        y_axis=Axis("mass", unit="mg"),
    )
    with pytest.raises(ThermalError, match="below 0 K"):
        convert_temperature(source, target_unit="K")


def test_tga_mass_normalization_is_explicit_and_reference_traceable():
    source = _tga()
    percent = normalize_tga_mass(source, output="percent", reference="first_point")
    np.testing.assert_allclose(percent.y, (100.0, 90.0, 80.0, 70.0))
    assert percent.y_axis.name == "mass_percent"
    assert percent.y_axis.unit == "%"
    assert percent.y_axis.metadata["normalization_reference_basis"] == "first_point"
    assert percent.y_axis.metadata["normalization_reference_value"] == pytest.approx(10.0)

    fraction = normalize_tga_mass(source, output="fraction", reference=20.0)
    np.testing.assert_allclose(fraction.y, (0.5, 0.45, 0.4, 0.35))
    assert fraction.y_axis.name == "mass_fraction"
    assert fraction.y_axis.unit == "1"
    assert fraction.y_axis.metadata["normalization_reference_basis"] == "explicit"

    with pytest.raises(ThermalError, match="already normalized"):
        normalize_tga_mass(percent)
    with pytest.raises(ThermalError, match="greater than zero"):
        normalize_tga_mass(source, reference=0.0)


def test_dtg_linear_mass_curve_has_hand_verifiable_sign_modes():
    source = _tga()
    signed = derive_dtg(source, sign_mode="signed")
    loss_positive = derive_dtg(source, sign_mode="mass_loss_positive")
    np.testing.assert_allclose(signed.y, -0.01)
    np.testing.assert_allclose(loss_positive.y, 0.01)
    assert signed.y_axis.unit == "mg/°C"
    assert signed.y_axis.metadata["dtg_sign_mode"] == "signed"
    assert loss_positive.y_axis.metadata["dtg_sign_mode"] == "mass_loss_positive"
    validate_dtg_series(signed)
    validate_dtg_series(loss_positive)


def test_dtg_derivative_is_independent_of_ascending_or_descending_storage():
    ascending = derive_dtg(_tga(), sign_mode="mass_loss_positive")
    descending = derive_dtg(_tga(descending=True), sign_mode="mass_loss_positive")
    np.testing.assert_allclose(descending.x[::-1], ascending.x)
    np.testing.assert_allclose(descending.y[::-1], ascending.y)
    assert ascending.metadata["processing_history"][-1]["parameters"]["source_direction"] == (
        "ascending"
    )
    assert descending.metadata["processing_history"][-1]["parameters"]["source_direction"] == (
        "descending"
    )


def test_dtg_requires_three_finite_points_and_never_hides_missing_data():
    two_point = Series(
        x=(100.0, 200.0),
        y=(10.0, 9.0),
        x_axis=Axis("temperature", unit="°C"),
        y_axis=Axis("mass", unit="mg"),
    )
    with pytest.raises(ThermalError, match="at least 3"):
        derive_dtg(two_point)
    with pytest.raises(ThermalError, match="does not silently discard"):
        derive_dtg(_tga(y=(10.0, np.nan, 8.0, 7.0)))


def test_tpr_tpd_validation_requires_explicit_detector_semantics_and_respects_technique():
    validate_temperature_programmed_series(_programmed(), technique="tpr")
    validate_temperature_programmed_series(_programmed(technique="tpd"), technique="tpd")
    with pytest.raises(ThermalError, match="conflicts"):
        validate_temperature_programmed_series(_programmed(technique="tpd"), technique="tpr")
    with pytest.raises(ThermalError, match="explicit unit"):
        validate_temperature_programmed_series(_programmed(unit=""), technique="tpr")


def test_thermal_window_extremum_and_area_are_hand_verifiable_and_direction_independent():
    window = ThermalWindow(150.0, 450.0, "main")
    ascending = measure_thermal_window(
        _programmed(),
        window,
        technique="tpr",
        extremum_mode="maximum",
        area_mode="net",
    )
    descending = measure_thermal_window(
        _programmed(descending=True),
        window,
        technique="tpr",
        extremum_mode="maximum",
        area_mode="net",
    )
    assert ascending.extremum_temperature == pytest.approx(300.0)
    assert ascending.extremum_value == pytest.approx(3.0)
    assert ascending.area == pytest.approx(475.0)
    assert ascending.n_measured_points == 3
    assert ascending.integration_n_points == 5
    assert ascending.boundary_mode == "linear"
    assert ascending.source_direction == "ascending"
    assert descending.source_direction == "descending"
    assert descending.area == pytest.approx(ascending.area)
    assert descending.window_sha256 == ascending.window_sha256


def test_thermal_window_signed_vs_absolute_area_and_minimum_are_explicit():
    negative = Series(
        x=(100.0, 200.0, 300.0),
        y=(0.0, -2.0, 0.0),
        x_axis=Axis("temperature", unit="°C"),
        y_axis=Axis("detector_signal", unit="a.u."),
    )
    window = ThermalWindow(100.0, 300.0)
    net = measure_thermal_window(
        negative,
        window,
        technique="tpd",
        extremum_mode="minimum",
        area_mode="net",
    )
    absolute = measure_thermal_window(
        negative,
        window,
        technique="tpd",
        extremum_mode="minimum",
        area_mode="absolute",
    )
    assert net.extremum_temperature == pytest.approx(200.0)
    assert net.extremum_value == pytest.approx(-2.0)
    assert net.area == pytest.approx(-200.0)
    assert absolute.area == pytest.approx(200.0)


def test_window_interpolation_fails_when_required_bracketing_data_are_missing():
    missing = Series(
        x=(100.0, 200.0, 300.0, 400.0),
        y=(0.0, np.nan, 2.0, 0.0),
        x_axis=Axis("temperature", unit="°C"),
        y_axis=Axis("detector_signal", unit="a.u."),
    )
    with pytest.raises(ThermalError, match="finite bracketing"):
        measure_thermal_window(
            missing,
            ThermalWindow(150.0, 350.0),
            technique="tpr",
        )


def test_process_thermal_and_dataset_use_only_explicit_operations_and_stable_keys():
    raw = _tga()
    unchanged = process_thermal(raw, technique="tga")
    np.testing.assert_allclose(unchanged.y, raw.y)
    assert unchanged.y_axis.name == "mass"

    processed = process_thermal(
        raw,
        technique="tga",
        config=ThermalProcessingConfig(
            temperature_min=200.0,
            temperature_max=400.0,
            tga_normalization="percent",
            vertical_offset=5.0,
        ),
    )
    np.testing.assert_allclose(processed.x, (200.0, 300.0, 400.0))
    np.testing.assert_allclose(processed.y, (95.0, 85.0, 75.0))
    assert [entry["operation"] for entry in processed.metadata["processing_history"]][-3:] == [
        "normalize_tga_mass",
        "crop",
        "offset",
    ]

    dataset = Dataset([_tga(key="a"), _tga(key="b", y=(20.0, 18.0, 16.0, 14.0))])
    mapped = process_thermal_dataset(
        dataset,
        technique="tga",
        config=ThermalProcessingConfig(tga_normalization="percent"),
        overrides={"b": ThermalProcessingConfig(tga_normalization="fraction")},
    )
    assert mapped.keys == ("a", "b")
    assert mapped[0].y_axis.name == "mass_percent"
    assert mapped[1].y_axis.name == "mass_fraction"
    with pytest.raises(ThermalError, match="override keys not present"):
        process_thermal_dataset(
            dataset,
            technique="tga",
            overrides={"missing": ThermalProcessingConfig()},
        )


def test_overlay_guard_rejects_units_normalization_and_dtg_sign_mismatches():
    with pytest.raises(ThermalError, match="thermal overlay"):
        validate_thermal_overlay(
            Dataset([_tga(key="a", y_unit="mg"), _tga(key="b", y_unit="g")]),
            technique="tga",
        )

    normalized_first = normalize_tga_mass(_tga(key="a"), reference="first_point")
    normalized_explicit = normalize_tga_mass(_tga(key="b"), reference=20.0)
    with pytest.raises(ThermalError, match="thermal overlay"):
        validate_thermal_overlay(
            Dataset([normalized_first, normalized_explicit]),
            technique="tga",
        )

    signed = derive_dtg(_tga(key="a"), sign_mode="signed")
    positive = derive_dtg(_tga(key="b"), sign_mode="mass_loss_positive")
    with pytest.raises(ThermalError, match="thermal overlay"):
        validate_thermal_overlay(Dataset([signed, positive]), technique="dtg")


def test_explicit_stacking_is_non_mutating_and_records_ordered_stable_keys():
    dataset = Dataset([_programmed(key="a"), _programmed(key="b")])
    stacked = stack_thermal_dataset(dataset, technique="tpr", step=2.0, start=1.0)
    np.testing.assert_allclose(stacked[0].y, np.asarray(dataset[0].y) + 1.0)
    np.testing.assert_allclose(stacked[1].y, np.asarray(dataset[1].y) + 3.0)
    np.testing.assert_allclose(dataset[0].y, (0.0, 1.0, 3.0, 1.0, 0.0))
    assert stacked.metadata["thermal_stack_history"][-1]["keys"] == ("a", "b")
