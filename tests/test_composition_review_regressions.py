"""Review regressions for composition API compatibility and scientific invariants."""

from __future__ import annotations

import subprocess
import sys

import pandas as pd
import pytest

from catalysis_workbench.experimental.characterization import (
    CompositionError,
    CompositionMeasurement,
    CompositionSummary,
    convert_composition_unit,
    read_composition_csv,
    solution_concentration_to_bulk_mass_fraction,
)


def test_characterization_numerical_import_keeps_matplotlib_lazy() -> None:
    code = """
import sys
import catalysis_workbench.experimental.characterization
assert not any(name == 'matplotlib' or name.startswith('matplotlib.') for name in sys.modules)
"""
    subprocess.run([sys.executable, "-c", code], check=True)


def test_summary_rejects_fractional_n_instead_of_truncating() -> None:
    with pytest.raises((CompositionError, TypeError, ValueError)):
        CompositionSummary(
            sample_key="a",
            element="Pb",
            basis="bulk_mass_fraction",
            unit="wt%",
            n=1.5,  # type: ignore[arg-type]
            mean=1.0,
            standard_deviation=None,
            rsd_percent=None,
            source_keys=("a",),
            source_sha256="0" * 64,
        )


def test_summary_rejects_nonhex_sha256() -> None:
    with pytest.raises(CompositionError, match="SHA-256"):
        CompositionSummary(
            sample_key="a",
            element="Pb",
            basis="bulk_mass_fraction",
            unit="wt%",
            n=1,
            mean=1.0,
            standard_deviation=None,
            rsd_percent=None,
            source_keys=("a",),
            source_sha256="z" * 64,
        )


def test_summary_requires_sd_for_n_at_least_two() -> None:
    with pytest.raises(CompositionError, match="standard_deviation is required"):
        CompositionSummary(
            sample_key="a",
            element="Pb",
            basis="bulk_mass_fraction",
            unit="wt%",
            n=2,
            mean=1.0,
            standard_deviation=None,
            rsd_percent=None,
            source_keys=("a-1", "a-2"),
            source_sha256="0" * 64,
        )


def test_summary_rejects_rsd_inconsistent_with_mean_and_sd() -> None:
    with pytest.raises(CompositionError, match="100 \* standard_deviation / mean"):
        CompositionSummary(
            sample_key="a",
            element="Pb",
            basis="bulk_mass_fraction",
            unit="wt%",
            n=2,
            mean=1.0,
            standard_deviation=0.1,
            rsd_percent=9.0,
            source_keys=("a-1", "a-2"),
            source_sha256="0" * 64,
        )


def test_scientific_numeric_inputs_reject_booleans() -> None:
    with pytest.raises(TypeError, match="boolean"):
        CompositionMeasurement(
            key="bool",
            sample_key="a",
            element="Pb",
            value=True,
            unit="wt%",
            basis="bulk_mass_fraction",
        )

    solution = CompositionMeasurement(
        key="solution",
        sample_key="a",
        element="Pb",
        value=10.0,
        unit="mg/L",
        basis="solution_concentration",
    )
    with pytest.raises(TypeError, match="boolean"):
        solution_concentration_to_bulk_mass_fraction(
            solution,
            sample_mass=True,
            sample_mass_unit="mg",
            final_digest_volume=25.0,
            final_digest_volume_unit="mL",
        )
    with pytest.raises(TypeError, match="boolean"):
        solution_concentration_to_bulk_mass_fraction(
            solution,
            sample_mass=50.0,
            sample_mass_unit="mg",
            final_digest_volume=25.0,
            final_digest_volume_unit="mL",
            dilution_factor=True,
        )


def test_tidy_reader_rejects_boolean_scientific_values(tmp_path) -> None:
    path = tmp_path / "bool.csv"
    pd.DataFrame(
        {"sample": ["a"], "element": ["Pb"], "value": [True]}
    ).to_csv(path, index=False)
    with pytest.raises(CompositionError, match="must not be boolean"):
        read_composition_csv(
            path,
            sample="sample",
            element="element",
            value="value",
            basis="bulk_mass_fraction",
            unit="wt%",
        )


def test_mass_balance_provenance_survives_followup_unit_conversion() -> None:
    solution = CompositionMeasurement(
        key="solution",
        sample_key="a",
        element="Pb",
        value=10.0,
        unit="mg/L",
        basis="solution_concentration",
    )
    bulk = solution_concentration_to_bulk_mass_fraction(
        solution,
        sample_mass=50.0,
        sample_mass_unit="mg",
        final_digest_volume=25.0,
        final_digest_volume_unit="mL",
        dilution_factor=2.0,
        target_unit="wt%",
    )
    converted = convert_composition_unit(bulk, target_unit="mg/g")

    assert converted.value == pytest.approx(10.0)
    assert converted.metadata["composition_mass_balance_source_basis"] == (
        "solution_concentration"
    )
    assert converted.metadata["composition_mass_balance_source_value"] == pytest.approx(
        10.0
    )
    assert converted.metadata["composition_mass_balance_source_unit"] == "mg/L"
    assert converted.metadata["composition_unit_source_basis"] == "bulk_mass_fraction"
    assert converted.metadata["composition_unit_source_value"] == pytest.approx(1.0)
    assert converted.metadata["composition_unit_source_unit"] == "wt%"
