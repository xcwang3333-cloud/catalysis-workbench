from __future__ import annotations

from dataclasses import dataclass
from math import pi

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.echem import (
    FARADAY_CONSTANT_C_MOL,
    AnalysisProvenance,
    EchemQuantityError,
    FitWindow,
    SourceDataRef,
    amount_to_mol,
    area_to_cm2,
    charge_to_c,
    current_density_to_a_cm2,
    current_to_a,
    electron_number,
    loading_to_g_cm2,
    make_analysis_provenance,
    mass_to_g,
    molar_rate_to_mol_s,
    normalize_reference_name,
    potential_to_v,
    rotation_rate_to_rad_s,
    same_reference,
    scan_rate_to_v_s,
    series_data_sha256,
    source_data_ref,
    time_to_s,
)


def _series(*, y=(1.0, 2.0, 3.0), key="cat-a", label="Cat A") -> Series:
    return Series(
        x=(0.1, 0.2, 0.3),
        y=y,
        key=key,
        label=label,
        x_axis=Axis("potential", unit="V", metadata={"reference": "RHE"}),
        y_axis=Axis("current_density", unit="mA/cm^2"),
    )


@pytest.mark.parametrize(
    ("unit", "expected"),
    [
        ("V", [0.1, 0.2]),
        ("mV", [0.0001, 0.0002]),
    ],
)
def test_potential_to_v(unit, expected):
    np.testing.assert_allclose(potential_to_v([0.1, 0.2], unit), expected)


@pytest.mark.parametrize(
    ("unit", "expected"),
    [
        ("A", [1.0, -2.0]),
        ("mA", [1e-3, -2e-3]),
        ("µA", [1e-6, -2e-6]),
    ],
)
def test_current_to_a_preserves_sign(unit, expected):
    np.testing.assert_allclose(current_to_a([1.0, -2.0], unit), expected)


@pytest.mark.parametrize(
    "unit",
    ["mA/cm^2", "mA/cm2", "mA cm^-2", "mA cm⁻²"],
)
def test_current_density_aliases_are_equivalent(unit):
    np.testing.assert_allclose(
        current_density_to_a_cm2([2.0, -3.0], unit),
        [2e-3, -3e-3],
    )


def test_missing_and_unsupported_units_fail_explicitly():
    with pytest.raises(EchemQuantityError, match="unit is required"):
        potential_to_v([0.1], None)
    with pytest.raises(EchemQuantityError, match="unsupported current"):
        current_to_a([1.0], "C/s")
    with pytest.raises(EchemQuantityError, match="unsupported current density"):
        current_density_to_a_cm2([1.0], "A/m^2")


def test_quantity_helpers_reject_complex_infinite_and_missing_when_required():
    with pytest.raises(EchemQuantityError, match="real-valued"):
        current_to_a(np.array([1.0 + 1.0j]), "A")
    with pytest.raises(EchemQuantityError, match="inf"):
        current_to_a([np.inf], "A")
    with pytest.raises(EchemQuantityError, match="missing"):
        potential_to_v([np.nan], "V")
    np.testing.assert_allclose(current_to_a([np.nan], "A"), [np.nan], equal_nan=True)


def test_charge_to_c_supports_coulomb_and_ampere_hour_units():
    np.testing.assert_allclose(charge_to_c([1.0], "mC"), [1e-3])
    np.testing.assert_allclose(charge_to_c([2.0], "mAh"), [7.2])


def test_time_to_s_and_scan_rate_to_v_s():
    np.testing.assert_allclose(time_to_s([2.0], "min"), [120.0])
    np.testing.assert_allclose(time_to_s([0.5], "h"), [1800.0])
    np.testing.assert_allclose(scan_rate_to_v_s([50.0], "mV/s"), [0.05])
    np.testing.assert_allclose(scan_rate_to_v_s([6.0], "V/min"), [0.1])


def test_area_mass_and_loading_conversions():
    np.testing.assert_allclose(area_to_cm2([100.0], "mm^2"), [1.0])
    np.testing.assert_allclose(area_to_cm2([1e-4], "m²"), [1.0])
    np.testing.assert_allclose(mass_to_g([5.0], "mg"), [5e-3])
    np.testing.assert_allclose(mass_to_g([250.0], "µg"), [250e-6])
    np.testing.assert_allclose(loading_to_g_cm2([0.5], "mg/cm²"), [5e-4])


def test_amount_and_molar_rate_conversions():
    np.testing.assert_allclose(amount_to_mol([2.0], "µmol"), [2e-6])
    np.testing.assert_allclose(amount_to_mol([500.0], "nmol"), [5e-7])
    np.testing.assert_allclose(molar_rate_to_mol_s([60.0], "µmol/min"), [1e-6])


def test_rotation_rate_conversion_is_explicit():
    np.testing.assert_allclose(rotation_rate_to_rad_s([60.0], "rpm"), [2 * pi])
    np.testing.assert_allclose(rotation_rate_to_rad_s([1.0], "rps"), [2 * pi])
    np.testing.assert_allclose(rotation_rate_to_rad_s([2.0], "rad/s"), [2.0])
    with pytest.raises(EchemQuantityError, match="rotation rate"):
        rotation_rate_to_rad_s([1600.0], "Hz")


def test_electron_number_requires_positive_integer():
    assert electron_number(4) == 4
    assert electron_number(2.0) == 2
    for invalid in (0, -1, 2.5, np.nan, True, "two"):
        with pytest.raises(EchemQuantityError, match="positive integer"):
            electron_number(invalid)


def test_reference_names_are_explicit_and_case_insensitive_only_for_comparison():
    assert normalize_reference_name("  Ag/AgCl   (3 M KCl)  ") == "Ag/AgCl (3 M KCl)"
    assert same_reference("RHE", "rhe")
    assert not same_reference("RHE", "SHE")
    with pytest.raises(EchemQuantityError, match="must not be empty"):
        normalize_reference_name("   ")


def test_faraday_constant_is_exposed_for_later_echem_equations():
    assert FARADAY_CONSTANT_C_MOL == pytest.approx(96485.33212)


def test_series_data_digest_is_deterministic_and_data_sensitive():
    first = _series()
    same = _series()
    changed = _series(y=(1.0, 2.0, 4.0))
    assert series_data_sha256(first) == series_data_sha256(same)
    assert series_data_sha256(first) != series_data_sha256(changed)
    assert len(series_data_sha256(first)) == 64


def test_source_data_ref_retains_key_label_axes_units_and_digest():
    source = _series()
    ref = source_data_ref(source)
    assert ref == SourceDataRef(
        key="cat-a",
        label="Cat A",
        sha256=series_data_sha256(source),
        x_name="potential",
        x_unit="V",
        y_name="current_density",
        y_unit="mA/cm^2",
    )


def test_fit_window_requires_explicit_order_unit_and_point_count():
    window = FitWindow(0.2, 0.4, "V", 5)
    assert window.lower == pytest.approx(0.2)
    assert window.upper == pytest.approx(0.4)
    assert window.unit == "V"
    assert window.n_points == 5

    with pytest.raises(EchemQuantityError, match="smaller"):
        FitWindow(0.4, 0.2, "V", 5)
    with pytest.raises(EchemQuantityError, match="unit"):
        FitWindow(0.2, 0.4, "", 5)
    with pytest.raises(EchemQuantityError, match="n_points"):
        FitWindow(0.2, 0.4, "V", 1)


def test_make_analysis_provenance_is_deterministic_and_sorts_metadata():
    source = _series()
    window = FitWindow(0.1, 0.3, "V vs RHE", 3)
    one = make_analysis_provenance(
        source,
        input_basis="geometric_current_density",
        fit_window=window,
        units={"slope": "mV/dec", "current": "mA/cm^2"},
        parameters={"branch": "cathodic", "magnitude": True},
    )
    two = make_analysis_provenance(
        source,
        input_basis="geometric_current_density",
        fit_window=window,
        units={"current": "mA/cm^2", "slope": "mV/dec"},
        parameters={"magnitude": True, "branch": "cathodic"},
    )
    assert one == two
    assert one.units == (("current", "mA/cm^2"), ("slope", "mV/dec"))
    assert one.parameters == (("branch", "cathodic"), ("magnitude", True))


def test_analysis_provenance_rejects_empty_basis_and_non_scalar_metadata():
    source = _series()
    with pytest.raises(EchemQuantityError, match="input_basis"):
        make_analysis_provenance(source, input_basis="  ")
    with pytest.raises(EchemQuantityError, match="scalar"):
        make_analysis_provenance(
            source,
            input_basis="current_density",
            parameters={"bad": [1, 2]},
        )


@dataclass(frozen=True, slots=True)
class _ExampleFitResult:
    slope: float
    intercept: float
    r_squared: float
    provenance: AnalysisProvenance


def test_result_dataclass_fixture_demonstrates_shared_provenance_contract():
    source = _series()
    provenance = make_analysis_provenance(
        source,
        input_basis="geometric_current_density",
        fit_window=FitWindow(0.1, 0.3, "V vs RHE", 3),
        units={"slope": "mV/dec"},
        parameters={"branch": "cathodic"},
    )
    result = _ExampleFitResult(
        slope=72.1,
        intercept=0.33,
        r_squared=0.998,
        provenance=provenance,
    )
    assert result.provenance.source.sha256 == series_data_sha256(source)
    assert result.provenance.source.key == "cat-a"
    assert result.provenance.fit_window.n_points == 3
