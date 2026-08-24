"""Scientific-contract regressions for ICP/composition integration."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from catalysis_workbench.experimental.characterization import (
    CompositionError,
    CompositionMeasurement,
    CompositionTable,
    convert_composition_table,
    convert_composition_unit,
    read_composition_csv,
    read_composition_excel,
    select_composition,
    solution_concentration_to_bulk_mass_fraction,
    summarize_composition_replicates,
)


def _measurement(
    *,
    key: str = "m1",
    sample_key: str = "sample-a",
    element: str = "Pb",
    value: float = 1.0,
    unit: str = "wt%",
    basis: str = "bulk_mass_fraction",
    replicate_key: str = "",
    analyte: str = "208Pb",
    sample_label: str = "Sample A",
) -> CompositionMeasurement:
    return CompositionMeasurement(
        key=key,
        sample_key=sample_key,
        sample_label=sample_label,
        element=element,
        analyte=analyte,
        replicate_key=replicate_key,
        value=value,
        unit=unit,
        basis=basis,
    )


def test_bulk_mass_fraction_units_convert_explicitly() -> None:
    source = _measurement(value=1.0, unit="wt%")
    expected = {
        "1": 0.01,
        "mg/g": 10.0,
        "ug/g": 10000.0,
        "mg/kg": 10000.0,
    }
    for unit, value in expected.items():
        converted = convert_composition_unit(source, target_unit=unit)
        assert converted.unit == unit
        assert converted.basis == "bulk_mass_fraction"
        assert converted.value == pytest.approx(value)
        assert converted.key == source.key
        assert converted.metadata["composition_source_unit"] == "wt%"


def test_solution_concentration_units_convert_explicitly() -> None:
    source = _measurement(
        value=10.0,
        unit="mg/L",
        basis="solution_concentration",
    )
    assert convert_composition_unit(source, target_unit="g/L").value == pytest.approx(
        0.01
    )
    assert convert_composition_unit(source, target_unit="ug/L").value == pytest.approx(
        10000.0
    )


def test_bare_ppm_is_rejected_as_ambiguous() -> None:
    with pytest.raises(CompositionError, match="ppm"):
        _measurement(unit="ppm")
    with pytest.raises(CompositionError, match="ppm"):
        _measurement(unit="ppm", basis="solution_concentration")


def test_measurement_rejects_negative_nan_and_missing_identity() -> None:
    with pytest.raises(CompositionError, match="non-negative"):
        _measurement(value=-0.1)
    with pytest.raises(CompositionError, match="finite"):
        _measurement(value=np.nan)
    with pytest.raises(CompositionError, match="sample_key"):
        _measurement(sample_key=" ")
    with pytest.raises(CompositionError, match="element"):
        _measurement(element=" ")


def test_composition_table_requires_unique_measurement_keys() -> None:
    with pytest.raises(CompositionError, match="unique"):
        CompositionTable((_measurement(key="same"), _measurement(key="same")))


def test_convert_table_requires_one_basis() -> None:
    table = CompositionTable(
        (
            _measurement(key="a"),
            _measurement(
                key="b",
                value=10.0,
                unit="mg/L",
                basis="solution_concentration",
            ),
        )
    )
    with pytest.raises(CompositionError, match="one quantity basis"):
        convert_composition_table(table, target_unit="wt%")


def test_solution_concentration_mass_balance_to_wt_percent() -> None:
    measured = _measurement(
        key="pb-solution",
        value=10.0,
        unit="mg/L",
        basis="solution_concentration",
    )
    converted = solution_concentration_to_bulk_mass_fraction(
        measured,
        sample_mass=50.0,
        sample_mass_unit="mg",
        final_digest_volume=25.0,
        final_digest_volume_unit="mL",
        dilution_factor=2.0,
        target_unit="wt%",
    )
    # 10 mg/L * 2 * 0.025 L = 0.5 mg Pb; 0.5 mg / 50 mg = 1 wt%.
    assert converted.value == pytest.approx(1.0)
    assert converted.unit == "wt%"
    assert converted.basis == "bulk_mass_fraction"
    assert converted.key == measured.key
    assert converted.metadata["composition_sample_mass_g"] == pytest.approx(0.05)
    assert converted.metadata["composition_final_digest_volume_l"] == pytest.approx(
        0.025
    )
    assert converted.metadata["composition_dilution_factor"] == 2.0


def test_mass_balance_is_unit_consistent() -> None:
    measured = _measurement(
        value=0.01,
        unit="g/L",
        basis="solution_concentration",
    )
    converted = solution_concentration_to_bulk_mass_fraction(
        measured,
        sample_mass=0.05,
        sample_mass_unit="g",
        final_digest_volume=0.025,
        final_digest_volume_unit="L",
        dilution_factor=2,
        target_unit="mg/g",
    )
    assert converted.value == pytest.approx(10.0)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("sample_mass", 0.0, "greater than zero"),
        ("final_digest_volume", -1.0, "greater than zero"),
        ("dilution_factor", 0.0, "greater than zero"),
    ],
)
def test_mass_balance_rejects_nonpositive_inputs(field, value, message) -> None:
    measured = _measurement(
        value=10.0,
        unit="mg/L",
        basis="solution_concentration",
    )
    kwargs = {
        "sample_mass": 50.0,
        "sample_mass_unit": "mg",
        "final_digest_volume": 25.0,
        "final_digest_volume_unit": "mL",
        "dilution_factor": 2.0,
    }
    kwargs[field] = value
    with pytest.raises(CompositionError, match=message):
        solution_concentration_to_bulk_mass_fraction(measured, **kwargs)


def test_mass_balance_requires_solution_concentration_basis() -> None:
    with pytest.raises(CompositionError, match="solution_concentration"):
        solution_concentration_to_bulk_mass_fraction(
            _measurement(),
            sample_mass=50.0,
            final_digest_volume=25.0,
        )


def test_replicate_summary_reports_mean_sample_sd_rsd_and_n() -> None:
    table = CompositionTable(
        (
            _measurement(key="r1", value=0.9, replicate_key="1"),
            _measurement(key="r2", value=1.0, replicate_key="2"),
            _measurement(key="r3", value=1.1, replicate_key="3"),
        ),
        name="Pb loading",
    )
    summary_table = summarize_composition_replicates(table)
    assert len(summary_table) == 1
    summary = summary_table[0]
    assert summary.n == 3
    assert summary.mean == pytest.approx(1.0)
    assert summary.standard_deviation == pytest.approx(0.1)
    assert summary.rsd_percent == pytest.approx(10.0)
    assert summary.source_keys == ("r1", "r2", "r3")
    assert len(summary.source_sha256) == 64


def test_single_replicate_has_no_fabricated_sd_or_rsd() -> None:
    summary = summarize_composition_replicates(
        CompositionTable((_measurement(key="one", value=1.2),))
    )[0]
    assert summary.n == 1
    assert summary.standard_deviation is None
    assert summary.rsd_percent is None


def test_zero_mean_replicates_have_defined_sd_but_no_rsd() -> None:
    table = CompositionTable(
        (
            _measurement(key="z1", value=0.0, replicate_key="1"),
            _measurement(key="z2", value=0.0, replicate_key="2"),
        )
    )
    summary = summarize_composition_replicates(table)[0]
    assert summary.mean == 0.0
    assert summary.standard_deviation == 0.0
    assert summary.rsd_percent is None


def test_replicates_require_identical_basis_unit_and_analyte() -> None:
    incompatible_unit = CompositionTable(
        (
            _measurement(key="a", value=1.0, unit="wt%"),
            _measurement(key="b", value=10.0, unit="mg/g"),
        )
    )
    with pytest.raises(CompositionError, match="convert explicitly"):
        summarize_composition_replicates(incompatible_unit)

    incompatible_analyte = CompositionTable(
        (
            _measurement(key="a", analyte="208Pb"),
            _measurement(key="b", analyte="206Pb"),
        )
    )
    with pytest.raises(CompositionError, match="analyte"):
        summarize_composition_replicates(incompatible_analyte)


def test_duplicate_explicit_replicate_key_fails() -> None:
    table = CompositionTable(
        (
            _measurement(key="a", replicate_key="r1"),
            _measurement(key="b", replicate_key="r1"),
        )
    )
    with pytest.raises(CompositionError, match="duplicate replicate_key"):
        summarize_composition_replicates(table)


def test_selection_uses_stable_sample_keys_and_element_identity() -> None:
    table = CompositionTable(
        (
            _measurement(key="a-pb", sample_key="a", element="Pb"),
            _measurement(key="a-fe", sample_key="a", element="Fe"),
            _measurement(key="b-pb", sample_key="b", element="Pb"),
            _measurement(key="b-fe", sample_key="b", element="Fe"),
        )
    )
    selected = select_composition(table, sample_keys=("b",), elements=("Fe",))
    assert selected.keys == ("b-fe",)
    with pytest.raises(CompositionError, match="not present"):
        select_composition(table, sample_keys=("Sample A",))


def test_csv_reader_is_explicit_deterministic_and_source_id_portable(tmp_path) -> None:
    path = tmp_path / "icp.csv"
    pd.DataFrame(
        {
            "sample": ["a", "a", "b"],
            "element": ["Pb", "Fe", "Pb"],
            "rep": ["1", "1", "1"],
            "value": [1.0, 2.0, 3.0],
        }
    ).to_csv(path, index=False)

    first = read_composition_csv(
        path,
        sample="sample",
        element="element",
        value="value",
        replicate="rep",
        basis="bulk_mass_fraction",
        unit="wt%",
        source_id="portable-icp",
    )
    second = read_composition_csv(
        path,
        sample=0,
        element=1,
        value=3,
        replicate=2,
        basis="bulk_mass_fraction",
        unit="wt%",
        source_id="portable-icp",
    )
    assert first.keys == second.keys
    assert first.source_sha256 == second.source_sha256
    assert first.source_id == "portable-icp"
    assert first[0].metadata["composition_row_position"] == 0


def test_excel_sheet_index_and_name_produce_same_keys(tmp_path) -> None:
    path = tmp_path / "icp.xlsx"
    frame = pd.DataFrame(
        {"sample": ["a"], "element": ["Pb"], "value": [1.25]}
    )
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({"ignore": [1]}).to_excel(writer, sheet_name="Ignore", index=False)
        frame.to_excel(writer, sheet_name="Results", index=False)

    by_index = read_composition_excel(
        path,
        sample="sample",
        element="element",
        value="value",
        basis="bulk_mass_fraction",
        unit="wt%",
        sheet_name=1,
        source_id="portable-xlsx",
    )
    by_name = read_composition_excel(
        path,
        sample="sample",
        element="element",
        value="value",
        basis="bulk_mass_fraction",
        unit="wt%",
        sheet_name="Results",
        source_id="portable-xlsx",
    )
    assert by_index.keys == by_name.keys
    assert by_index.source_sha256 == by_name.source_sha256


def test_reader_rejects_missing_or_nonnumeric_selected_values(tmp_path) -> None:
    missing = tmp_path / "missing.csv"
    pd.DataFrame(
        {"sample": ["a"], "element": ["Pb"], "value": [np.nan]}
    ).to_csv(missing, index=False)
    with pytest.raises(CompositionError, match="missing"):
        read_composition_csv(
            missing,
            sample="sample",
            element="element",
            value="value",
            basis="bulk_mass_fraction",
            unit="wt%",
        )

    malformed = tmp_path / "malformed.csv"
    pd.DataFrame(
        {"sample": ["a"], "element": ["Pb"], "value": ["not-a-number"]}
    ).to_csv(malformed, index=False)
    with pytest.raises(CompositionError, match="not numeric"):
        read_composition_csv(
            malformed,
            sample="sample",
            element="element",
            value="value",
            basis="bulk_mass_fraction",
            unit="wt%",
        )


def test_source_digest_changes_when_scientific_value_changes() -> None:
    a = CompositionTable((_measurement(key="same", value=1.0),))
    b = CompositionTable((_measurement(key="same", value=1.1),))
    assert a.source_sha256 != b.source_sha256
    assert len(a.source_sha256) == 64
    assert not math.isnan(float(a[0].value))
