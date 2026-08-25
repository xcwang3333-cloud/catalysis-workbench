from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from catalysis_workbench.computation.band_structure import (
    BandEnergyChannel,
    BandPathSegment,
    BandStructureState,
)
from catalysis_workbench.computation.structure import AtomicStructure
from catalysis_workbench.io.electronic_structure import ElectronicStructureIOError
from catalysis_workbench.io.procar import _convert_procar_result


def _structure() -> AtomicStructure:
    return AtomicStructure(
        species=("H", "He"),
        elements=("H", "He"),
        cartesian_coordinates=((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)),
        lattice_angstrom=np.diag([2.0, 2.0, 2.0]),
        pbc=(True, True, True),
        site_keys=("site-H", "site-He"),
    )


def _band_state(*, spin_polarized: bool = False) -> BandStructureState:
    kpoints = np.array(
        [
            [0.0, 0.0, 0.0],
            [0.333333, 0.0, 0.0],
            [0.0, 0.5, 0.0],
            [0.0, 1.0, 0.0],
        ]
    )
    up = np.array(
        [
            [4.0, 4.5, 5.0, 5.5],
            [6.0, 6.5, 7.0, 7.5],
        ]
    )
    channels = (
        (
            BandEnergyChannel("up", up, (0, 1)),
            BandEnergyChannel("down", up + 0.2, (0, 1)),
        )
        if spin_polarized
        else (BandEnergyChannel("total", up, (0, 1)),)
    )
    return BandStructureState(
        structure=_structure(),
        kpoints_fractional=kpoints,
        reciprocal_lattice_cartesian=np.diag([2.0, 3.0, 4.0]),
        reciprocal_unit="1/angstrom",
        reciprocal_cartesian_includes_2pi=True,
        channels=channels,
        path_segments=(
            BandPathSegment("a", 0, 1),
            BandPathSegment("b", 2, 3),
        ),
        source_digest="band-source-spin" if spin_polarized else "band-source-total",
        source_fermi_ev=5.0,
    )


def _projection_values(offset: float = 0.0) -> np.ndarray:
    return (
        np.arange(4 * 2 * 2 * 3, dtype=float).reshape(4, 2, 2, 3) + 1.0 + offset
    ) / 100.0


def _parsed_total(band: BandStructureState) -> SimpleNamespace:
    return SimpleNamespace(
        is_soc=False,
        xyz_data=None,
        orbitals=["s", "pz", "tot"],
        kpoints=np.array(band.kpoints_fractional, copy=True),
        data={1: _projection_values()},
        eigenvalues={1: np.array(band.channel("total").energies_ev.T, copy=True)},
        occupancies={1: np.ones((4, 2))},
        nions=2,
        weights=np.array([1.0, 1.0, 0.0, 0.0]),
    )


def _convert(parsed: SimpleNamespace, band: BandStructureState, **kwargs):
    return _convert_procar_result(
        parsed,
        band_structure=band,
        path="PROCAR",
        source_id="test-procar",
        kpoint_atol=kwargs.get("kpoint_atol", 1e-5),
        energy_atol_ev=kwargs.get("energy_atol_ev", 1e-4),
        backend_version="2026.8.25",
    )


def test_single_backend_spin_channel_maps_to_physical_total_and_transposes_axes() -> None:
    band = _band_state()
    parsed = _parsed_total(band)
    state = _convert(parsed, band)

    assert state.channels[0].spin == "total"
    assert state.orbitals == ("s", "pz", "tot")
    assert state.channels[0].weights.shape == (2, 4, 2, 3)
    assert np.array_equal(
        state.channels[0].weights,
        np.transpose(parsed.data[1], (1, 0, 2, 3)),
    )
    assert state.metadata["kpoint_atol"] == pytest.approx(1e-5)
    assert state.metadata["energy_atol_ev"] == pytest.approx(1e-4)
    assert state.metadata["occupancies_available"] is True
    assert state.metadata["source_kpoint_weights"] == (1.0, 1.0, 0.0, 0.0)


def test_collinear_source_requires_and_preserves_complete_up_down() -> None:
    band = _band_state(spin_polarized=True)
    parsed = SimpleNamespace(
        is_soc=False,
        xyz_data=None,
        orbitals=["s", "pz", "tot"],
        kpoints=np.array(band.kpoints_fractional, copy=True),
        data={1: _projection_values(), -1: _projection_values(100.0)},
        eigenvalues={
            1: np.array(band.channel("up").energies_ev.T, copy=True),
            -1: np.array(band.channel("down").energies_ev.T, copy=True),
        },
        occupancies={1: np.ones((4, 2)), -1: np.ones((4, 2))},
        nions=2,
        weights=np.ones(4),
    )
    state = _convert(parsed, band)
    assert tuple(channel.spin for channel in state.channels) == ("up", "down")
    assert np.array_equal(
        state.channel("down").weights,
        np.transpose(parsed.data[-1], (1, 0, 2, 3)),
    )

    parsed.data = {1: parsed.data[1]}
    with pytest.raises(ElectronicStructureIOError, match="complete PROCAR up/down"):
        _convert(parsed, band)


def test_current_procar_rounding_is_handled_only_by_caller_visible_kpoint_tolerance() -> None:
    band = _band_state()
    parsed = _parsed_total(band)
    parsed.kpoints[1, 0] = 0.33333
    state = _convert(parsed, band, kpoint_atol=1e-5)
    assert state.metadata["kpoint_atol"] == pytest.approx(1e-5)

    with pytest.raises(ElectronicStructureIOError, match="kpoint_atol"):
        _convert(parsed, band, kpoint_atol=1e-7)


def test_energy_reconciliation_uses_only_caller_visible_absolute_tolerance() -> None:
    band = _band_state()
    parsed = _parsed_total(band)
    parsed.eigenvalues[1][0, 0] += 5e-5
    state = _convert(parsed, band, energy_atol_ev=1e-4)
    assert state.metadata["energy_atol_ev"] == pytest.approx(1e-4)

    with pytest.raises(ElectronicStructureIOError, match="energy_atol_ev"):
        _convert(parsed, band, energy_atol_ev=1e-6)


def test_soc_or_vector_projection_state_fails_closed() -> None:
    band = _band_state()
    parsed = _parsed_total(band)
    parsed.is_soc = True
    with pytest.raises(ElectronicStructureIOError, match="SOC/non-collinear"):
        _convert(parsed, band)

    parsed.is_soc = False
    parsed.xyz_data = {"x": np.zeros((4, 2, 2, 3))}
    with pytest.raises(ElectronicStructureIOError, match="xyz/vector"):
        _convert(parsed, band)


def test_orbital_site_band_and_projection_shape_mismatches_fail_closed() -> None:
    band = _band_state()
    parsed = _parsed_total(band)
    parsed.orbitals = ["s", "s", "tot"]
    with pytest.raises(ElectronicStructureIOError, match="unique"):
        _convert(parsed, band)

    parsed = _parsed_total(band)
    parsed.nions = 3
    with pytest.raises(ElectronicStructureIOError, match="nions"):
        _convert(parsed, band)

    parsed = _parsed_total(band)
    parsed.data[1] = np.ones((4, 3, 2, 3))
    with pytest.raises(ElectronicStructureIOError, match="projection tensor"):
        _convert(parsed, band)

    parsed = _parsed_total(band)
    parsed.eigenvalues[1] = np.ones((4, 3))
    with pytest.raises(ElectronicStructureIOError, match="eigenvalues"):
        _convert(parsed, band)


def test_negative_projection_weight_is_never_clipped_or_repaired() -> None:
    band = _band_state()
    parsed = _parsed_total(band)
    parsed.data[1][0, 0, 0, 0] = -1e-6
    with pytest.raises(ElectronicStructureIOError, match="non-negative"):
        _convert(parsed, band)


def test_kpoint_count_or_order_mismatch_is_never_reordered_or_sliced() -> None:
    band = _band_state()
    parsed = _parsed_total(band)
    parsed.kpoints = parsed.kpoints[[1, 0, 2, 3]]
    with pytest.raises(ElectronicStructureIOError, match="order/coordinates"):
        _convert(parsed, band)

    parsed = _parsed_total(band)
    parsed.kpoints = parsed.kpoints[:3]
    with pytest.raises(ElectronicStructureIOError, match="count/shape"):
        _convert(parsed, band)
