"""Scientific-contract regressions for basic gas-sorption handling."""

from __future__ import annotations

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.experimental.characterization import (
    SorptionCondition,
    SorptionError,
    SorptionProcessingConfig,
    SorptionWindow,
    convert_relative_pressure,
    prepare_sorption_series,
    process_sorption,
    process_sorption_dataset,
    select_sorption_branch,
    summarize_sorption_window,
    validate_sorption_overlay,
)


def _raw(
    *,
    key: str = "sample-ads",
    x=(0.01, 0.10, 0.50, 0.90),
    y=(0.2, 1.0, 3.0, 5.0),
    x_name: str = "relative_pressure",
    x_unit: str = "1",
    y_unit: str = "mmol/g",
) -> Series:
    return Series(
        x=x,
        y=y,
        label=key,
        key=key,
        x_axis=Axis(x_name, unit=x_unit),
        y_axis=Axis("adsorbed_quantity", unit=y_unit),
    )


def _condition(
    branch: str = "adsorption",
    *,
    adsorbate: str = "N2",
    temperature: float = 77.0,
) -> SorptionCondition:
    return SorptionCondition(
        adsorbate=adsorbate,
        measurement_temperature_k=temperature,
        branch=branch,
    )


def test_relative_pressure_fraction_percent_conversion_is_explicit_and_reversible() -> None:
    source = prepare_sorption_series(_raw(), _condition())
    percent = convert_relative_pressure(source, target_unit="percent")
    np.testing.assert_allclose(percent.x, (1.0, 10.0, 50.0, 90.0))
    assert percent.x_axis.unit == "%"
    assert percent.key == source.key
    assert percent.metadata["sorption_branch"] == "adsorption"

    restored = convert_relative_pressure(percent, target_unit="fraction")
    np.testing.assert_allclose(restored.x, source.x)
    assert restored.x_axis.unit == "1"


def test_branch_is_declared_not_inferred_from_pressure_direction() -> None:
    ascending_desorption = prepare_sorption_series(
        _raw(key="des-up"),
        _condition("desorption"),
    )
    descending_adsorption = prepare_sorption_series(
        _raw(
            key="ads-down",
            x=(0.90, 0.50, 0.10, 0.01),
            y=(5.0, 3.0, 1.0, 0.2),
        ),
        _condition("adsorption"),
    )
    assert ascending_desorption.metadata["sorption_branch"] == "desorption"
    assert ascending_desorption.metadata["sorption_source_direction"] == "ascending"
    assert descending_adsorption.metadata["sorption_branch"] == "adsorption"
    assert descending_adsorption.metadata["sorption_source_direction"] == "descending"
    np.testing.assert_allclose(descending_adsorption.x, (0.90, 0.50, 0.10, 0.01))


def test_inverse_pressure_name_is_not_accepted_as_relative_pressure_alias() -> None:
    with pytest.raises(SorptionError, match="relative_pressure"):
        prepare_sorption_series(_raw(x_name="p0/p"), _condition())


@pytest.mark.parametrize(
    "x",
    [
        (0.01, 0.10, 0.10, 0.90),
        (0.01, 0.50, 0.10, 0.90),
        (-0.01, 0.10, 0.50, 0.90),
        (0.01, np.nan, 0.50, 0.90),
    ],
)
def test_invalid_relative_pressure_grids_fail_without_sorting_or_dropping(x) -> None:
    with pytest.raises(SorptionError):
        prepare_sorption_series(_raw(x=x), _condition())


def test_relative_pressure_above_one_is_preserved_not_clipped() -> None:
    source = prepare_sorption_series(
        _raw(x=(0.01, 0.50, 1.05, 1.10)),
        _condition(),
    )
    np.testing.assert_allclose(source.x, (0.01, 0.50, 1.05, 1.10))


def test_stp_volume_loading_requires_explicit_standard_condition() -> None:
    raw = _raw(y_unit="cm^3(STP)/g")
    with pytest.raises(SorptionError, match="standard_temperature_k"):
        prepare_sorption_series(raw, _condition())

    prepared = prepare_sorption_series(
        raw,
        SorptionCondition(
            adsorbate="N2",
            measurement_temperature_k=77.0,
            branch="adsorption",
            standard_temperature_k=273.15,
            standard_pressure_kpa=101.325,
        ),
    )
    assert prepared.y_axis.unit == "cm^3(STP)/g"
    assert prepared.metadata["sorption_standard_temperature_k"] == 273.15
    assert prepared.metadata["sorption_standard_pressure_kpa"] == 101.325


def test_overlay_rejects_adsorbate_temperature_pressure_unit_loading_and_stp_mismatch() -> None:
    base = prepare_sorption_series(_raw(key="a"), _condition())
    wrong_adsorbate = prepare_sorption_series(
        _raw(key="b"),
        _condition(adsorbate="Ar"),
    )
    with pytest.raises(SorptionError, match="overlay"):
        validate_sorption_overlay(Dataset(series=(base, wrong_adsorbate)))

    wrong_temperature = prepare_sorption_series(
        _raw(key="b"),
        _condition(temperature=87.0),
    )
    with pytest.raises(SorptionError, match="overlay"):
        validate_sorption_overlay(Dataset(series=(base, wrong_temperature)))

    percent = convert_relative_pressure(
        prepare_sorption_series(_raw(key="b"), _condition()),
        target_unit="%",
    )
    with pytest.raises(SorptionError, match="overlay"):
        validate_sorption_overlay(Dataset(series=(base, percent)))

    molkg = prepare_sorption_series(_raw(key="b", y_unit="mol/kg"), _condition())
    with pytest.raises(SorptionError, match="overlay"):
        validate_sorption_overlay(Dataset(series=(base, molkg)))

    stp_a = prepare_sorption_series(
        _raw(key="a", y_unit="cm3(STP)/g"),
        SorptionCondition("N2", 77.0, "adsorption", 273.15, 101.325),
    )
    stp_b = prepare_sorption_series(
        _raw(key="b", y_unit="cm3(STP)/g"),
        SorptionCondition("N2", 77.0, "desorption", 298.15, 101.325),
    )
    with pytest.raises(SorptionError, match="overlay"):
        validate_sorption_overlay(Dataset(series=(stp_a, stp_b)))


def test_dataset_processing_uses_stable_keys_and_rejects_unknown_keys() -> None:
    dataset = Dataset(series=(_raw(key="ads"), _raw(key="des")))
    conditions = {
        "ads": _condition("adsorption"),
        "des": _condition("desorption"),
    }
    processed = process_sorption_dataset(
        dataset,
        conditions=conditions,
        overrides={
            "des": SorptionProcessingConfig(
                relative_pressure_min=0.10,
                relative_pressure_max=0.90,
                vertical_offset=2.0,
            )
        },
    )
    assert processed.keys == ("ads", "des")
    np.testing.assert_allclose(processed["ads"].y, (0.2, 1.0, 3.0, 5.0))
    np.testing.assert_allclose(processed["des"].x, (0.10, 0.50, 0.90))
    np.testing.assert_allclose(processed["des"].y, (3.0, 5.0, 7.0))

    with pytest.raises(SorptionError, match="not present"):
        process_sorption_dataset(
            dataset,
            conditions=conditions,
            overrides={"display label": SorptionProcessingConfig()},
        )


def test_select_branch_filters_declared_metadata_only() -> None:
    adsorption = prepare_sorption_series(_raw(key="ads"), _condition("adsorption"))
    desorption = prepare_sorption_series(
        _raw(key="des", x=(0.01, 0.20, 0.60, 0.95)),
        _condition("desorption"),
    )
    dataset = Dataset(series=(adsorption, desorption))
    selected = select_sorption_branch(dataset, branch="desorption")
    assert isinstance(selected, Dataset)
    assert selected.keys == ("des",)
    assert selected["des"].metadata["sorption_source_direction"] == "ascending"


def test_window_summary_uses_only_measured_points_without_interpolation() -> None:
    source = prepare_sorption_series(_raw(), _condition())
    summary = summarize_sorption_window(source, SorptionWindow(0.05, 0.80, "middle"))
    assert summary.n_measured_points == 2
    assert summary.minimum_relative_pressure == 0.10
    assert summary.minimum_loading == 1.0
    assert summary.maximum_relative_pressure == 0.50
    assert summary.maximum_loading == 3.0
    assert summary.branch == "adsorption"
    assert len(summary.source_sha256) == 64

    with pytest.raises(SorptionError, match="no measured points"):
        summarize_sorption_window(source, SorptionWindow(0.02, 0.09))


def test_processing_crop_and_offset_are_explicit_and_preserve_source_condition() -> None:
    result = process_sorption(
        _raw(),
        condition=_condition(),
        config=SorptionProcessingConfig(
            relative_pressure_min=0.10,
            relative_pressure_max=0.90,
            vertical_offset=1.5,
        ),
    )
    np.testing.assert_allclose(result.x, (0.10, 0.50, 0.90))
    np.testing.assert_allclose(result.y, (2.5, 4.5, 6.5))
    assert result.metadata["sorption_adsorbate"] == "N2"
    assert result.metadata["sorption_branch"] == "adsorption"
