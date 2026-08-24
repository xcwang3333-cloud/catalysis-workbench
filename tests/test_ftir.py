from __future__ import annotations

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.experimental.characterization import (
    FTIRBand,
    FTIRBaselineWindow,
    FTIRError,
    FTIRProcessingConfig,
    fit_ftir_baseline,
    measure_ftir_band,
    process_ftir,
    process_ftir_dataset,
    stack_ftir_dataset,
    subtract_ftir_baseline,
    transmittance_to_absorbance,
    validate_ftir_overlay,
    validate_ftir_series,
)


def _absorbance(
    *,
    key="sample",
    x=(1000.0, 1100.0, 1200.0, 1300.0, 1400.0),
    y=(0.0, 1.0, 2.0, 1.0, 0.0),
    x_name="wavenumber",
    x_unit="cm^-1",
    y_name="absorbance",
    y_unit=None,
    y_metadata=None,
):
    return Series(
        x=x,
        y=y,
        label=key,
        key=key,
        x_axis=Axis(x_name, unit=x_unit, label="Wavenumber"),
        y_axis=Axis(
            y_name,
            unit=y_unit,
            label="Absorbance",
            metadata={} if y_metadata is None else y_metadata,
        ),
    )


def _transmittance(*, unit="%", y=(100.0, 50.0, 10.0)):
    return Series(
        x=(1000.0, 1100.0, 1200.0),
        y=y,
        label="T",
        key="T",
        x_axis=Axis("wavenumber", unit="cm^-1"),
        y_axis=Axis("transmittance", unit=unit),
    )


@pytest.mark.parametrize("name", ["wavenumber", "Wavenumber", "wn"])
@pytest.mark.parametrize("unit", ["cm^-1", "cm-1", "1/cm", "cm⁻¹", "cm−1"])
def test_validate_ftir_accepts_common_wavenumber_aliases_and_both_directions(name, unit):
    validate_ftir_series(_absorbance(x_name=name, x_unit=unit))
    validate_ftir_series(
        _absorbance(
            x_name=name,
            x_unit=unit,
            x=(1400.0, 1300.0, 1200.0, 1100.0, 1000.0),
            y=(0.0, 1.0, 2.0, 1.0, 0.0),
        )
    )


def test_validate_ftir_rejects_wrong_semantics_unit_and_nonmonotonic_grid():
    with pytest.raises(FTIRError, match="x_axis.name"):
        validate_ftir_series(_absorbance(x_name="raman_shift"))
    with pytest.raises(FTIRError, match="wavenumber unit"):
        validate_ftir_series(_absorbance(x_unit="nm"))
    with pytest.raises(FTIRError, match="strictly monotonic"):
        validate_ftir_series(
            _absorbance(x=(1000.0, 1100.0, 1100.0, 1300.0, 1400.0))
        )
    with pytest.raises(FTIRError, match="y_axis.name"):
        validate_ftir_series(_absorbance(y_name="intensity"))


def test_transmittance_to_absorbance_requires_explicit_consistent_scale():
    percent = transmittance_to_absorbance(_transmittance(), input_scale="percent")
    np.testing.assert_allclose(percent.y, (0.0, np.log10(2.0), 1.0))
    assert percent.y_axis.name == "absorbance"
    assert percent.y_axis.metadata["transmittance_input_scale"] == "percent"
    assert percent.metadata["processing_history"][-1]["operation"] == (
        "transmittance_to_absorbance"
    )

    fraction = transmittance_to_absorbance(
        _transmittance(unit="1", y=(1.0, 0.5, 0.1)),
        input_scale="fraction",
    )
    np.testing.assert_allclose(fraction.y, percent.y)

    with pytest.raises(FTIRError, match="conflicts"):
        transmittance_to_absorbance(_transmittance(), input_scale="fraction")
    with pytest.raises(FTIRError, match="values are not clipped"):
        transmittance_to_absorbance(
            _transmittance(y=(100.0, 0.0, 10.0)),
            input_scale="percent",
        )
    with pytest.raises(FTIRError, match="values are not clipped"):
        transmittance_to_absorbance(
            _transmittance(y=(100.0, 110.0, 10.0)),
            input_scale="percent",
        )


def _baseline_spectrum(*, descending=False, key="baseline-source", middle_scale=1.0):
    x = np.array([1000.0, 1200.0, 1400.0, 1600.0, 1800.0, 2000.0])
    baseline = 0.001 * x + 0.2
    peak = np.array([0.0, 0.0, 1.0, 2.0, 0.0, 0.0]) * middle_scale
    y = baseline + peak
    if descending:
        x = x[::-1]
        y = y[::-1]
    return _absorbance(key=key, x=x, y=y)


def test_polynomial_baseline_uses_only_explicit_windows_and_returns_baseline_separately():
    source = _baseline_spectrum()
    fit = fit_ftir_baseline(
        source,
        (FTIRBaselineWindow(1000.0, 1200.0), (1800.0, 2000.0)),
        degree=1,
    )
    expected = 0.001 * np.asarray(source.x) + 0.2
    np.testing.assert_allclose(fit.baseline.y, expected, atol=1e-12)
    assert fit.degree == 1
    assert fit.n_fit_points == 4
    assert fit.source_key == "baseline-source"
    assert fit.baseline.metadata["processing_history"][-1]["operation"] == (
        "fit_ftir_baseline"
    )

    corrected = subtract_ftir_baseline(source, fit)
    np.testing.assert_allclose(corrected.y, (0.0, 0.0, 1.0, 2.0, 0.0, 0.0), atol=1e-12)
    np.testing.assert_allclose(source.y, expected + (0.0, 0.0, 1.0, 2.0, 0.0, 0.0))


def test_baseline_fit_is_direction_agnostic_but_preserves_source_order():
    ascending = fit_ftir_baseline(
        _baseline_spectrum(),
        ((1000.0, 1200.0), (1800.0, 2000.0)),
        degree=1,
    )
    descending_source = _baseline_spectrum(descending=True)
    descending = fit_ftir_baseline(
        descending_source,
        ((1000.0, 1200.0), (1800.0, 2000.0)),
        degree=1,
    )
    np.testing.assert_allclose(descending.baseline.x, descending_source.x)
    np.testing.assert_allclose(descending.baseline.y[::-1], ascending.baseline.y)


def test_baseline_rejects_automatic_or_incompatible_use():
    with pytest.raises(FTIRError, match="at least one baseline window"):
        fit_ftir_baseline(_baseline_spectrum(), (), degree=1)
    with pytest.raises(FTIRError, match="fully contained"):
        fit_ftir_baseline(_baseline_spectrum(), ((900.0, 1200.0),), degree=1)
    with pytest.raises(FTIRError, match="convert transmittance explicitly"):
        fit_ftir_baseline(_transmittance(), ((1000.0, 1200.0),), degree=1)

    first = _baseline_spectrum(key="first")
    fit = fit_ftir_baseline(first, ((1000.0, 1200.0), (1800.0, 2000.0)))
    changed = _baseline_spectrum(key="first", middle_scale=2.0)
    with pytest.raises(FTIRError, match="different source data"):
        subtract_ftir_baseline(changed, fit)


def test_process_ftir_reuses_crop_baseline_normalization_and_offset_explicitly():
    source = _baseline_spectrum()
    fit = fit_ftir_baseline(source, ((1000.0, 1200.0), (1800.0, 2000.0)))
    result = process_ftir(
        source,
        FTIRProcessingConfig(
            wavenumber_min_cm1=1200.0,
            wavenumber_max_cm1=1800.0,
            normalization="max",
            vertical_offset=0.5,
        ),
        baseline=fit,
    )
    np.testing.assert_allclose(result.x, (1200.0, 1400.0, 1600.0, 1800.0))
    np.testing.assert_allclose(result.y, (0.5, 1.0, 1.5, 0.5), atol=1e-12)
    assert result.y_axis.name == "normalized_absorbance"
    assert result.y_axis.unit == "a.u."
    assert [entry["operation"] for entry in result.metadata["processing_history"]][-4:] == [
        "subtract_baseline",
        "crop",
        "normalize",
        "offset",
    ]


def test_process_ftir_does_not_silently_convert_or_normalize_transmittance():
    raw = process_ftir(_transmittance(), FTIRProcessingConfig())
    assert raw.y_axis.name == "transmittance"
    np.testing.assert_allclose(raw.y, (100.0, 50.0, 10.0))
    with pytest.raises(FTIRError, match="convert transmittance explicitly"):
        process_ftir(
            _transmittance(),
            FTIRProcessingConfig(normalization="max"),
        )


def test_process_ftir_dataset_uses_stable_keys_and_rejects_unknown_mappings():
    dataset = Dataset(
        [
            _absorbance(key="a"),
            _absorbance(key="b", y=(0.0, 2.0, 4.0, 2.0, 0.0)),
        ]
    )
    processed = process_ftir_dataset(
        dataset,
        FTIRProcessingConfig(normalization="max"),
        overrides={
            "b": FTIRProcessingConfig(normalization="max", vertical_offset=1.0)
        },
    )
    assert processed.keys == ("a", "b")
    assert processed[1].metadata["processing_history"][-1]["operation"] == "offset"

    with pytest.raises(FTIRError, match="override keys not present"):
        process_ftir_dataset(
            dataset,
            FTIRProcessingConfig(),
            overrides={"missing": FTIRProcessingConfig()},
        )


def test_band_measurement_is_independent_of_source_wavenumber_direction():
    ascending = _absorbance()
    descending = _absorbance(
        x=(1400.0, 1300.0, 1200.0, 1100.0, 1000.0),
        y=(0.0, 1.0, 2.0, 1.0, 0.0),
    )
    band = FTIRBand(1000.0, 1400.0, "band")
    one = measure_ftir_band(ascending, band)
    two = measure_ftir_band(descending, band)
    assert one.area == pytest.approx(400.0)
    assert two.area == pytest.approx(400.0)
    assert one.peak_position_cm1 == pytest.approx(1200.0)
    assert two.peak_position_cm1 == pytest.approx(1200.0)
    assert one.source_direction == "ascending"
    assert two.source_direction == "descending"
    assert one.integration_direction == "low_to_high_wavenumber"
    assert two.integration_direction == "low_to_high_wavenumber"
    assert one.window_sha256 == two.window_sha256


def test_band_measurement_interpolates_only_explicit_window_boundaries():
    result = measure_ftir_band(_absorbance(), FTIRBand(1050.0, 1350.0, "inner"))
    assert result.area == pytest.approx(375.0)
    assert result.n_points == 3
    assert result.integration_n_points == 5


def test_band_measurement_rejects_nan_needed_for_boundary_interpolation():
    source = _absorbance(y=(np.nan, 1.0, 2.0, 1.0, 0.0))
    with pytest.raises(FTIRError, match="boundary interpolation"):
        measure_ftir_band(source, FTIRBand(1050.0, 1350.0, "inner"))


def test_band_measurement_keeps_net_sign_and_absolute_mode_explicit():
    negative = _absorbance(y=(0.0, -1.0, -2.0, -1.0, 0.0))
    band = FTIRBand(1000.0, 1400.0)
    net = measure_ftir_band(negative, band, area_mode="net")
    absolute = measure_ftir_band(negative, band, area_mode="absolute")
    assert net.area == pytest.approx(-400.0)
    assert absolute.area == pytest.approx(400.0)


def test_band_measurement_requires_absorbance_and_complete_window():
    with pytest.raises(FTIRError, match="convert transmittance explicitly"):
        measure_ftir_band(_transmittance(), FTIRBand(1000.0, 1200.0))
    with pytest.raises(FTIRError, match="fully contained"):
        measure_ftir_band(_absorbance(), FTIRBand(900.0, 1200.0))
    missing = _absorbance(y=(0.0, 1.0, np.nan, 1.0, 0.0))
    with pytest.raises(FTIRError, match="missing absorbance"):
        measure_ftir_band(missing, FTIRBand(1000.0, 1400.0))


def test_overlay_rejects_mixed_semantics_units_and_normalization_recipe():
    with pytest.raises(FTIRError, match="matching y semantic"):
        validate_ftir_overlay(Dataset([_absorbance(key="a"), _transmittance()]))

    normalized_one = process_ftir(
        _absorbance(key="a"),
        FTIRProcessingConfig(normalization="max", normalization_target=1.0),
    )
    normalized_hundred = process_ftir(
        _absorbance(key="b"),
        FTIRProcessingConfig(normalization="max", normalization_target=100.0),
    )
    with pytest.raises(FTIRError, match="matching y semantic"):
        validate_ftir_overlay(Dataset([normalized_one, normalized_hundred]))


def test_stack_ftir_dataset_is_explicit_non_mutating_and_records_provenance():
    dataset = Dataset(
        [
            _absorbance(key="a"),
            _absorbance(key="b", y=(0.0, 2.0, 4.0, 2.0, 0.0)),
        ]
    )
    stacked = stack_ftir_dataset(dataset, step=3.0, start=1.0)
    np.testing.assert_allclose(stacked[0].y, (1.0, 2.0, 3.0, 2.0, 1.0))
    np.testing.assert_allclose(stacked[1].y, (4.0, 6.0, 8.0, 6.0, 4.0))
    np.testing.assert_allclose(dataset[1].y, (0.0, 2.0, 4.0, 2.0, 0.0))
    assert stacked.metadata["ftir_stack_history"][-1]["keys"] == ("a", "b")
