from __future__ import annotations

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.experimental.characterization import (
    RamanBand,
    RamanError,
    RamanProcessingConfig,
    id_ig_ratio,
    measure_raman_band,
    process_raman,
    process_raman_dataset,
    raman_ratio,
    stack_raman_dataset,
    validate_raman_series,
)
from catalysis_workbench.processing import ProcessingError


def _spectrum(
    *,
    key="sample",
    x=(1000.0, 1100.0, 1200.0, 1300.0, 1400.0),
    y=(2.0, 4.0, 8.0, 4.0, 2.0),
    x_name="raman_shift",
    x_unit="cm^-1",
    y_name="intensity",
    y_unit="counts",
):
    return Series(
        x=x,
        y=y,
        label=key,
        key=key,
        x_axis=Axis(x_name, unit=x_unit, label="Raman shift"),
        y_axis=Axis(y_name, unit=y_unit, label="Intensity"),
    )


@pytest.mark.parametrize("name", ["raman_shift", "Raman shift", "shift"])
@pytest.mark.parametrize("unit", ["cm^-1", "cm-1", "1/cm", "cm⁻¹", "cm−1"])
def test_validate_raman_accepts_common_shift_aliases(name, unit):
    validate_raman_series(_spectrum(x_name=name, x_unit=unit))


def test_validate_raman_rejects_absolute_wavenumber_bad_unit_and_bad_grid():
    with pytest.raises(RamanError, match="x_axis.name"):
        validate_raman_series(_spectrum(x_name="wavenumber"))
    with pytest.raises(RamanError, match="Raman-shift unit"):
        validate_raman_series(_spectrum(x_unit="nm"))
    with pytest.raises(RamanError, match="strictly increasing"):
        validate_raman_series(
            _spectrum(x=(1000.0, 1100.0, 1100.0, 1300.0, 1400.0))
        )


def test_validate_raman_enforces_intensity_basis():
    validate_raman_series(_spectrum(y_unit="count"))
    validate_raman_series(_spectrum(y_unit="cps"))
    validate_raman_series(_spectrum(y_unit="a.u."))
    with pytest.raises(RamanError, match="unsupported Raman intensity unit"):
        validate_raman_series(_spectrum(y_unit="mA"))
    with pytest.raises(RamanError, match="normalized_intensity"):
        validate_raman_series(_spectrum(y_name="normalized_intensity", y_unit="counts"))


def test_process_raman_reuses_baseline_crop_normalize_and_offset():
    source = _spectrum()
    result = process_raman(
        source,
        RamanProcessingConfig(
            shift_min_cm1=1100.0,
            shift_max_cm1=1300.0,
            normalization="max",
            vertical_offset=0.5,
        ),
        baseline=1.0,
    )

    np.testing.assert_allclose(result.x, (1100.0, 1200.0, 1300.0))
    np.testing.assert_allclose(result.y, (0.5 + 3 / 7, 1.5, 0.5 + 3 / 7))
    assert result.y_axis.name == "normalized_intensity"
    assert result.y_axis.unit == "a.u."
    assert result.y_axis.metadata["normalization_method"] == "max"
    assert [item["operation"] for item in result.metadata["processing_history"]] == [
        "subtract_baseline",
        "crop",
        "normalize",
        "offset",
    ]
    np.testing.assert_allclose(source.y, (2.0, 4.0, 8.0, 4.0, 2.0))


def test_process_raman_savgol_reuses_shared_uniform_spacing_guard():
    source = _spectrum(
        x=(1000.0, 1010.0, 1020.0, 1030.0, 1040.0, 1050.0, 1060.0),
        y=(0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0),
    )
    result = process_raman(
        source,
        RamanProcessingConfig(savgol_window_length=5, savgol_polyorder=2),
    )
    np.testing.assert_allclose(result.y, source.y, atol=1e-12)
    assert result.metadata["processing_history"][-1]["operation"] == "savgol"

    irregular = _spectrum(
        x=(1000.0, 1010.0, 1021.0, 1030.0, 1040.0),
    )
    with pytest.raises(ProcessingError, match="uniform x spacing"):
        process_raman(
            irregular,
            RamanProcessingConfig(savgol_window_length=5, savgol_polyorder=2),
        )


def test_raman_baseline_series_accepts_semantic_aliases_but_not_different_basis():
    source = _spectrum()
    baseline = _spectrum(
        key="baseline",
        y=(1.0, 1.0, 1.0, 1.0, 1.0),
        x_name="Shift",
        x_unit="cm⁻¹",
        y_unit="count",
    )
    result = process_raman(source, RamanProcessingConfig(), baseline=baseline)
    np.testing.assert_allclose(result.y, (1.0, 3.0, 7.0, 3.0, 1.0))

    bad = _spectrum(
        key="baseline",
        y=(1.0, 1.0, 1.0, 1.0, 1.0),
        y_unit="cps",
    )
    with pytest.raises(RamanError, match="intensity basis"):
        process_raman(source, RamanProcessingConfig(), baseline=bad)


def test_raman_normalization_requires_positive_target_and_records_recipe_signature():
    with pytest.raises(RamanError, match="greater than zero"):
        RamanProcessingConfig(normalization="max", normalization_target=0.0)

    one = process_raman(
        _spectrum(),
        RamanProcessingConfig(normalization="max", normalization_target=1.0),
    )
    hundred = process_raman(
        _spectrum(),
        RamanProcessingConfig(normalization="max", normalization_target=100.0),
    )
    assert one.y_axis.metadata["normalization"] != hundred.y_axis.metadata["normalization"]


def test_process_raman_dataset_supports_keyed_overrides_and_baselines():
    dataset = Dataset(
        [
            _spectrum(key="a"),
            _spectrum(key="b", y=(5.0, 10.0, 15.0, 10.0, 5.0)),
        ],
        metadata={"campaign": "demo"},
    )
    result = process_raman_dataset(
        dataset,
        RamanProcessingConfig(normalization="max"),
        overrides={
            "b": RamanProcessingConfig(normalization="max", vertical_offset=2.0)
        },
        baselines={"a": 1.0},
    )
    assert result.keys == ("a", "b")
    assert result.metadata["campaign"] == "demo"
    assert result[0].y_axis.name == "normalized_intensity"
    assert result[1].metadata["processing_history"][-1]["operation"] == "offset"


def test_process_raman_dataset_rejects_unknown_keys():
    dataset = Dataset([_spectrum(key="a")])
    with pytest.raises(RamanError, match="override keys not present"):
        process_raman_dataset(
            dataset,
            RamanProcessingConfig(),
            overrides={"missing": RamanProcessingConfig()},
        )
    with pytest.raises(RamanError, match="baseline keys not present"):
        process_raman_dataset(
            dataset,
            RamanProcessingConfig(),
            baselines={"missing": 1.0},
        )


def test_stack_raman_dataset_is_non_mutating_and_records_provenance():
    dataset = Dataset(
        [
            _spectrum(key="a", y=(0.0, 1.0, 2.0, 1.0, 0.0)),
            _spectrum(key="b", y=(0.0, 2.0, 4.0, 2.0, 0.0)),
        ]
    )
    stacked = stack_raman_dataset(dataset, step=3.0, start=1.0)
    np.testing.assert_allclose(stacked[0].y, (1.0, 2.0, 3.0, 2.0, 1.0))
    np.testing.assert_allclose(stacked[1].y, (4.0, 6.0, 8.0, 6.0, 4.0))
    np.testing.assert_allclose(dataset[1].y, (0.0, 2.0, 4.0, 2.0, 0.0))
    assert stacked.metadata["raman_stack_history"][-1]["step"] == 3.0


def _carbon_spectrum(*, y=None):
    x = (1200.0, 1300.0, 1350.0, 1400.0, 1500.0, 1580.0, 1600.0, 1620.0, 1700.0)
    values = (0.0, 1.0, 4.0, 1.0, 0.0, 2.0, 8.0, 2.0, 0.0) if y is None else y
    return _spectrum(key="carbon", x=x, y=values)


def test_measure_raman_band_reports_direct_peak_and_area():
    spectrum = _carbon_spectrum()
    d_band = RamanBand(1250.0, 1450.0, "D")
    measurement = measure_raman_band(spectrum, d_band)
    assert measurement.peak_position_cm1 == pytest.approx(1350.0)
    assert measurement.peak_intensity == pytest.approx(4.0)
    assert measurement.area == pytest.approx(250.0)
    assert measurement.n_points == 3
    assert measurement.source_key == "carbon"


def test_raman_ratio_and_id_ig_require_explicit_bands_and_metric():
    spectrum = _carbon_spectrum()
    d_band = RamanBand(1250.0, 1450.0, "D")
    g_band = RamanBand(1550.0, 1650.0, "G")

    height = raman_ratio(spectrum, d_band, g_band, metric="height")
    area = id_ig_ratio(spectrum, d_band, g_band, metric="area")
    assert height.value == pytest.approx(0.5)
    assert area.value == pytest.approx(1.25)
    assert height.numerator.band.label == "D"
    assert height.denominator.band.label == "G"


def test_raman_band_metrics_reject_missing_values_and_display_offsets():
    spectrum = _carbon_spectrum(
        y=(0.0, 1.0, np.nan, 1.0, 0.0, 2.0, 8.0, 2.0, 0.0)
    )
    with pytest.raises(RamanError, match="missing y values"):
        measure_raman_band(spectrum, RamanBand(1250.0, 1450.0, "D"))

    offset_spectrum = process_raman(
        _carbon_spectrum(),
        RamanProcessingConfig(vertical_offset=1.0),
    )
    with pytest.raises(RamanError, match="vertical offset"):
        raman_ratio(
            offset_spectrum,
            RamanBand(1250.0, 1450.0, "D"),
            RamanBand(1550.0, 1650.0, "G"),
        )


def test_raman_ratio_rejects_minmax_and_non_positive_denominator():
    minmax = process_raman(
        _carbon_spectrum(),
        RamanProcessingConfig(normalization="minmax"),
    )
    with pytest.raises(RamanError, match="min-max-normalized"):
        raman_ratio(
            minmax,
            RamanBand(1250.0, 1450.0, "D"),
            RamanBand(1550.0, 1650.0, "G"),
        )

    zero_g = _carbon_spectrum(
        y=(0.0, 1.0, 4.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    )
    with pytest.raises(RamanError, match="denominator metric"):
        raman_ratio(
            zero_g,
            RamanBand(1250.0, 1450.0, "D"),
            RamanBand(1550.0, 1650.0, "G"),
        )
