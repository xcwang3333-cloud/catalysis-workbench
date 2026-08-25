from __future__ import annotations

import numpy as np
import pytest

from catalysis_workbench.computation import (
    AtomicStructure,
    BandEnergyChannel,
    BandPathSegment,
    BandStructureState,
    FermiLevelSource,
    ScalarField,
    VacuumLevelResult,
    WorkFunctionError,
    calculate_work_function,
    fermi_source_from_band_structure,
    planar_average_potential,
    reference_band_structure_to_fermi,
    vacuum_level_from_profile,
)
from catalysis_workbench.visualization import plot_planar_potential


def _structure() -> AtomicStructure:
    return AtomicStructure(
        species=("H",),
        elements=("H",),
        cartesian_coordinates=((0.0, 0.0, 0.0),),
        lattice_angstrom=np.array(
            [
                [2.0, 0.0, 0.0],
                [0.0, 3.0, 0.0],
                [1.0, 0.0, 4.0],
            ]
        ),
        pbc=(True, True, True),
        site_keys=("site-H",),
    )


def _field() -> ScalarField:
    return ScalarField(
        structure=_structure(),
        values=np.arange(24, dtype=float).reshape(2, 3, 4),
        field_kind="local-potential",
        value_unit="eV",
        source_type="LOCPOT",
        source_key="locpot:total",
        source_digest="locpot-source",
        metadata={"calculation_id": "calc-1"},
    )


def test_planar_average_uses_exact_source_values_and_skew_normal_height() -> None:
    field = _field()
    profile = planar_average_potential(field, axis=2)
    expected = np.mean(field.values, axis=(0, 1))
    assert np.array_equal(profile.potential_ev, expected)
    assert np.array_equal(profile.fractional_coordinates, np.array([0.0, 0.25, 0.5, 0.75]))
    assert profile.normal_height_angstrom == pytest.approx(4.0, rel=0.0, abs=1e-12)
    assert np.linalg.norm(_structure().lattice_angstrom[2]) == pytest.approx(np.sqrt(17.0))
    assert profile.normal_height_angstrom != pytest.approx(np.sqrt(17.0))
    assert np.allclose(
        profile.normal_coordinates_angstrom,
        np.array([0.0, 1.0, 2.0, 3.0]),
        rtol=0.0,
        atol=1e-12,
    )
    assert profile.calculation_id == "calc-1"
    assert not profile.potential_ev.flags.writeable


def test_planar_average_rejects_nonpotential_field_and_bad_axis() -> None:
    field = ScalarField(
        structure=_structure(),
        values=np.ones((2, 2, 2)),
        field_kind="elf",
        value_unit="dimensionless",
        source_type="ELFCAR",
        source_key="elfcar:total",
        source_digest="elf",
    )
    with pytest.raises(WorkFunctionError, match="local-potential"):
        planar_average_potential(field, axis=2)
    with pytest.raises(WorkFunctionError, match="axis"):
        planar_average_potential(_field(), axis=3)


def test_explicit_vacuum_window_is_half_open_mean_with_retained_bounds() -> None:
    profile = planar_average_potential(_field(), axis=2)
    result = vacuum_level_from_profile(
        profile,
        start_index=2,
        stop_index=4,
        side_id="top",
    )
    assert result.profile_size == 4
    assert result.normal_height_angstrom == pytest.approx(4.0, rel=0.0, abs=1e-12)
    assert result.selected_indices == (2, 3)
    assert result.vacuum_ev == pytest.approx(12.5, abs=1e-15)
    assert result.fractional_start == 0.5
    assert result.fractional_stop == 1.0
    assert result.normal_start_angstrom == pytest.approx(2.0, rel=0.0, abs=1e-12)
    assert result.normal_stop_angstrom == pytest.approx(4.0, rel=0.0, abs=1e-12)
    assert result.side_id == "top"
    assert result.statistic == "mean"


def test_vacuum_result_direct_construction_fails_on_spoofed_bounds() -> None:
    profile = planar_average_potential(_field(), axis=2)
    valid = vacuum_level_from_profile(profile, start_index=2, stop_index=4)
    with pytest.raises(WorkFunctionError, match="fractional_start"):
        VacuumLevelResult(
            profile_digest=valid.profile_digest,
            source_field_digest=valid.source_field_digest,
            calculation_id=valid.calculation_id,
            side_id=valid.side_id,
            profile_size=valid.profile_size,
            normal_height_angstrom=valid.normal_height_angstrom,
            start_index=valid.start_index,
            stop_index=valid.stop_index,
            selected_indices=valid.selected_indices,
            fractional_start=0.25,
            fractional_stop=valid.fractional_stop,
            normal_start_angstrom=valid.normal_start_angstrom,
            normal_stop_angstrom=valid.normal_stop_angstrom,
            statistic=valid.statistic,
            vacuum_ev=valid.vacuum_ev,
        )


@pytest.mark.parametrize(
    ("start", "stop"),
    [(-1, 2), (2, 2), (3, 2), (0, 5)],
)
def test_vacuum_window_rejects_invalid_bounds(start: int, stop: int) -> None:
    profile = planar_average_potential(_field(), axis=2)
    with pytest.raises(WorkFunctionError):
        vacuum_level_from_profile(profile, start_index=start, stop_index=stop)


def test_work_function_requires_matching_calculation_and_preserves_negative_value() -> None:
    profile = planar_average_potential(_field(), axis=2)
    vacuum = vacuum_level_from_profile(profile, start_index=2, stop_index=4)
    fermi = FermiLevelSource(
        fermi_ev=5.0,
        source_digest="fermi-source",
        calculation_id="calc-1",
    )
    result = calculate_work_function(vacuum, fermi)
    assert result.vacuum_ev == 12.5
    assert result.fermi_ev == 5.0
    assert result.work_function_ev == 7.5

    negative = calculate_work_function(
        vacuum,
        FermiLevelSource(
            fermi_ev=20.0,
            source_digest="fermi-high",
            calculation_id="calc-1",
        ),
    )
    assert negative.work_function_ev == -7.5

    with pytest.raises(WorkFunctionError, match="same calculation_id"):
        calculate_work_function(
            vacuum,
            FermiLevelSource(
                fermi_ev=5.0,
                source_digest="other",
                calculation_id="calc-2",
            ),
        )


def test_work_function_rejects_vacuum_without_calculation_identity() -> None:
    field = ScalarField(
        structure=_structure(),
        values=np.ones((2, 2, 2)),
        field_kind="local-potential",
        value_unit="eV",
        source_type="LOCPOT",
        source_key="locpot:total",
        source_digest="no-calc",
    )
    vacuum = vacuum_level_from_profile(
        planar_average_potential(field, axis=2),
        start_index=0,
        stop_index=2,
    )
    with pytest.raises(WorkFunctionError, match="calculation_id"):
        calculate_work_function(
            vacuum,
            FermiLevelSource(
                fermi_ev=0.0,
                source_digest="fermi",
                calculation_id="calc-1",
            ),
        )


def test_band_convenience_uses_retained_source_fermi_after_reference_shift() -> None:
    state = BandStructureState(
        structure=_structure(),
        kpoints_fractional=np.array([[0.0, 0.0, 0.0], [0.5, 0.0, 0.0]]),
        reciprocal_lattice_cartesian=np.eye(3),
        reciprocal_unit="1/angstrom",
        reciprocal_cartesian_includes_2pi=True,
        channels=(
            BandEnergyChannel(
                "total",
                np.array([[4.0, 6.0]]),
                (0,),
            ),
        ),
        path_segments=(BandPathSegment("G-X", 0, 1, "G", "X"),),
        source_digest="band-source",
        source_fermi_ev=5.0,
    )
    referenced = reference_band_structure_to_fermi(state)
    assert referenced.reference_kind == "fermi"
    assert np.array_equal(referenced.channels[0].energies_ev, np.array([[-1.0, 1.0]]))
    fermi = fermi_source_from_band_structure(referenced, calculation_id="calc-1")
    assert fermi.fermi_ev == 5.0
    assert fermi.metadata["reference_kind"] == "fermi"


def test_planar_plot_consumes_retained_state_without_mutation() -> None:
    profile = planar_average_potential(_field(), axis=2)
    vacuum = vacuum_level_from_profile(profile, start_index=2, stop_index=4)
    fermi = FermiLevelSource(
        fermi_ev=5.0,
        source_digest="fermi",
        calculation_id="calc-1",
    )
    work = calculate_work_function(vacuum, fermi)
    potential_before = np.array(profile.potential_ev, copy=True)
    digest_before = profile.digest

    figure, ax = plot_planar_potential(
        profile,
        vacuum_level=vacuum,
        fermi_source=fermi,
        work_function=work,
    )
    assert figure.axes == [ax]
    assert len(ax.lines) == 3
    assert len(ax.patches) == 1
    assert np.array_equal(profile.potential_ev, potential_before)
    assert profile.digest == digest_before
