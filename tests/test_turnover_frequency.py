"""Scientific-contract tests for TOF and TOFapp analysis."""

from __future__ import annotations

import subprocess
import sys

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.experimental.echem import (
    AVOGADRO_CONSTANT_MOL_INV,
    FARADAY_CONSTANT_C_MOL,
    TurnoverFrequencyError,
    partial_current_density_series,
    series_data_sha256,
    turnover_frequency_from_partial_current,
    turnover_frequency_from_partial_current_dataset,
    turnover_frequency_from_partial_current_series,
    turnover_frequency_from_rate,
    turnover_frequency_from_rate_dataset,
    turnover_frequency_from_rate_series,
)


def _potential_axis() -> Axis:
    return Axis("potential", unit="V", metadata={"reference": "RHE"})


def _rate(key: str = "cat-a", value: float = 2.0) -> Series:
    return Series(
        x=(-0.7,),
        y=(value,),
        key=key,
        label=key,
        x_axis=_potential_axis(),
        y_axis=Axis("molar_rate", unit="umol/s", label="Product rate"),
    )


def _total_density(key: str = "total", *, area_cm2: float = 0.2) -> Series:
    return Series(
        x=(-0.7,),
        y=(-10.0,),
        key=key,
        label=key,
        x_axis=_potential_axis(),
        y_axis=Axis(
            "current_density",
            unit="mA/cm^2",
            metadata={
                "normalization": "geometric_area",
                "electrode_area_cm2": area_cm2,
            },
        ),
    )


def _partial(key: str = "CO", *, area_cm2: float = 0.2) -> Series:
    current = _total_density(area_cm2=area_cm2)
    fe = Series(
        x=current.x,
        y=(50.0,),
        key=key,
        label=key,
        x_axis=current.x_axis,
        y_axis=Axis("faradaic_efficiency", unit="%"),
    )
    return partial_current_density_series(current, fe)


def test_rate_based_active_site_tof_is_hand_calculated():
    result = turnover_frequency_from_rate(
        [2.0],
        rate_unit="umol/s",
        inventory_basis="active_sites",
        inventory_value=1.0,
        inventory_unit="umol",
    )
    assert result.metric_name == "TOF"
    assert result.axis_name == "turnover_frequency"
    assert result.product_rate_mol_s.tolist() == pytest.approx([2e-6])
    assert result.inventory_mol == pytest.approx(1e-6)
    assert result.values.tolist() == pytest.approx([2.0])


def test_discrete_site_count_is_converted_with_exact_avogadro_constant():
    result = turnover_frequency_from_rate(
        [2e-6],
        rate_unit="mol/s",
        inventory_basis="active_sites",
        inventory_value=AVOGADRO_CONSTANT_MOL_INV * 1e-6,
        inventory_unit="sites",
    )
    assert result.inventory_mol == pytest.approx(1e-6)
    assert result.values.tolist() == pytest.approx([2.0])


def test_total_metal_and_bulk_inventory_are_always_tofapp():
    total_metal = turnover_frequency_from_rate(
        [1.0],
        rate_unit="umol/s",
        inventory_basis="total_metal",
        inventory_value=1.0,
        inventory_unit="umol",
    )
    bulk = turnover_frequency_from_rate(
        [1.0],
        rate_unit="umol/s",
        inventory_basis="bulk_inventory",
        inventory_value=1.0,
        inventory_unit="umol",
    )
    assert total_metal.metric_name == bulk.metric_name == "TOFapp"
    assert total_metal.axis_name == bulk.axis_name == "apparent_turnover_frequency"


def test_current_based_tof_matches_faraday_hand_calculation():
    current_a = 2.0 * FARADAY_CONSTANT_C_MOL * 1e-6
    result = turnover_frequency_from_partial_current(
        [current_a],
        current_unit="A",
        electron_number=2,
        inventory_basis="active_sites",
        inventory_value=1.0,
        inventory_unit="umol",
        current_mode="nonnegative",
    )
    assert result.product_rate_mol_s.tolist() == pytest.approx([1e-6])
    assert result.values.tolist() == pytest.approx([1.0])


def test_current_sign_handling_is_explicit_not_hidden():
    with pytest.raises(TurnoverFrequencyError, match="non-negative"):
        turnover_frequency_from_partial_current(
            [-1.0],
            current_unit="mA",
            electron_number=2,
            inventory_basis="active_sites",
            inventory_value=1.0,
            inventory_unit="umol",
            current_mode="nonnegative",
        )
    magnitude = turnover_frequency_from_partial_current(
        [-1.0],
        current_unit="mA",
        electron_number=2,
        inventory_basis="active_sites",
        inventory_value=1.0,
        inventory_unit="umol",
        current_mode="magnitude",
    )
    expected = 1e-3 / (2 * FARADAY_CONSTANT_C_MOL) / 1e-6
    assert magnitude.values.tolist() == pytest.approx([expected])


def test_negative_product_rate_is_rejected_instead_of_abs_converted():
    with pytest.raises(TurnoverFrequencyError, match="non-negative"):
        turnover_frequency_from_rate(
            [-1.0],
            rate_unit="umol/s",
            inventory_basis="active_sites",
            inventory_value=1.0,
            inventory_unit="umol",
        )


@pytest.mark.parametrize("bad", [0.0, -1.0, np.nan, np.inf, True, "1"])
def test_invalid_inventory_values_fail_explicitly(bad):
    with pytest.raises(TurnoverFrequencyError, match="inventory_value"):
        turnover_frequency_from_rate(
            [1.0],
            rate_unit="umol/s",
            inventory_basis="active_sites",
            inventory_value=bad,  # type: ignore[arg-type]
            inventory_unit="umol",
        )


def test_invalid_units_electron_number_and_output_unit_fail_explicitly():
    with pytest.raises(TurnoverFrequencyError, match="inventory_unit"):
        turnover_frequency_from_rate(
            [1.0],
            rate_unit="umol/s",
            inventory_basis="active_sites",
            inventory_value=1.0,
            inventory_unit="mg",
        )
    with pytest.raises(TurnoverFrequencyError, match="electron_number"):
        turnover_frequency_from_partial_current(
            [1.0],
            current_unit="mA",
            electron_number=0,
            inventory_basis="active_sites",
            inventory_value=1.0,
            inventory_unit="umol",
            current_mode="magnitude",
        )
    with pytest.raises(TurnoverFrequencyError, match="output_unit"):
        turnover_frequency_from_rate(
            [1.0],
            rate_unit="umol/s",
            inventory_basis="active_sites",
            inventory_value=1.0,
            inventory_unit="umol",
            output_unit="Hz",
        )


def test_frequency_output_units_are_explicit_and_equivalent():
    common = dict(
        rate=[1.0],
        rate_unit="umol/s",
        inventory_basis="active_sites",
        inventory_value=1.0,
        inventory_unit="umol",
    )
    assert turnover_frequency_from_rate(**common, output_unit="s^-1").values.item() == pytest.approx(1)
    assert turnover_frequency_from_rate(**common, output_unit="min^-1").values.item() == pytest.approx(60)
    assert turnover_frequency_from_rate(**common, output_unit="h^-1").values.item() == pytest.approx(3600)


def test_rate_series_records_metric_axis_and_deterministic_provenance():
    source = _rate()
    result = turnover_frequency_from_rate_series(
        source,
        inventory_basis="active_sites",
        inventory_value=1.0,
        inventory_unit="umol",
    )
    assert result.key == source.key
    assert result.y_axis.name == "turnover_frequency"
    assert result.y_axis.metadata["normalization"] == "active_sites"
    assert result.metadata["metric"] == "TOF"
    assert result.metadata["source"]["sha256"] == series_data_sha256(source)
    assert result.metadata["provenance"].source.sha256 == series_data_sha256(source)


def test_issue_23_partial_current_series_reconstructs_total_current_explicitly():
    source = _partial()
    result = turnover_frequency_from_partial_current_series(
        source,
        electron_number=2,
        inventory_basis="total_metal",
        inventory_value=10.0,
        inventory_unit="nmol",
        current_mode="magnitude",
        geometric_area_value=0.2,
        geometric_area_unit="cm^2",
    )
    expected = 1e-3 / (2 * FARADAY_CONSTANT_C_MOL) / 10e-9
    assert result.y.tolist() == pytest.approx([expected])
    assert result.y_axis.name == "apparent_turnover_frequency"
    assert result.y_axis.metadata["normalization"] == "total_metal"
    assert result.metadata["metric"] == "TOFapp"
    assert result.metadata["geometric_area_cm2"] == pytest.approx(0.2)
    assert result.metadata["upstream_sign_mode"] == "signed"
    assert result.metadata["current_source"]
    assert result.metadata["fe_source"]


def test_partial_current_series_requires_issue_23_provenance_and_matching_area():
    source = _partial()
    with pytest.raises(TurnoverFrequencyError, match="conflicts"):
        turnover_frequency_from_partial_current_series(
            source,
            electron_number=2,
            inventory_basis="active_sites",
            inventory_value=1.0,
            inventory_unit="umol",
            current_mode="magnitude",
            geometric_area_value=0.3,
            geometric_area_unit="cm^2",
        )
    fake = Series(
        x=source.x,
        y=source.y,
        key="fake",
        x_axis=source.x_axis,
        y_axis=source.y_axis,
    )
    with pytest.raises(TurnoverFrequencyError, match="Issue #23"):
        turnover_frequency_from_partial_current_series(
            fake,
            electron_number=2,
            inventory_basis="active_sites",
            inventory_value=1.0,
            inventory_unit="umol",
            current_mode="magnitude",
            geometric_area_value=0.2,
            geometric_area_unit="cm^2",
        )


def test_dataset_helpers_use_exact_stable_keys_not_labels():
    rate_dataset = Dataset(
        [
            Series(
                x=(-0.7,),
                y=(1.0,),
                key="a",
                label="Same",
                x_axis=_potential_axis(),
                y_axis=Axis("molar_rate", unit="umol/s"),
            ),
            Series(
                x=(-0.7,),
                y=(2.0,),
                key="b",
                label="Same",
                x_axis=_potential_axis(),
                y_axis=Axis("molar_rate", unit="umol/s"),
            ),
        ]
    )
    result = turnover_frequency_from_rate_dataset(
        rate_dataset,
        {"a": (1.0, "umol"), "b": (2.0, "umol")},
        inventory_basis="active_sites",
    )
    assert result.keys == ("a", "b")
    assert result.labels == ("Same", "Same")
    assert result[0].y.tolist() == pytest.approx([1.0])
    assert result[1].y.tolist() == pytest.approx([1.0])
    with pytest.raises(TurnoverFrequencyError, match="missing Series.key"):
        turnover_frequency_from_rate_dataset(
            rate_dataset,
            {"a": (1.0, "umol")},
            inventory_basis="active_sites",
        )


def test_partial_current_dataset_requires_exact_inventory_and_area_maps():
    dataset = Dataset([_partial("CO-a", area_cm2=0.2), _partial("CO-b", area_cm2=0.4)])
    result = turnover_frequency_from_partial_current_dataset(
        dataset,
        {"CO-a": (10.0, "nmol"), "CO-b": (20.0, "nmol")},
        {"CO-a": (0.2, "cm^2"), "CO-b": (0.4, "cm^2")},
        electron_number=2,
        inventory_basis="total_metal",
        current_mode="magnitude",
    )
    assert result.keys == ("CO-a", "CO-b")
    assert result.metadata["metric"] == "TOFapp"


def test_numerical_echem_import_remains_matplotlib_lazy_with_tof_api():
    code = (
        "import sys; "
        "import catalysis_workbench.experimental.echem as e; "
        "assert hasattr(e, 'turnover_frequency_from_rate'); "
        "assert 'matplotlib' not in sys.modules"
    )
    subprocess.run([sys.executable, "-c", code], check=True)
