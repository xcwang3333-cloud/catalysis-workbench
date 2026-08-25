from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from catalysis_workbench.computation import (
    COHPChannel,
    COHPResult,
    ICOHPBondSummary,
    ICOHPResult,
    BondingError,
    ElectronicEnergyAxis,
    cohp_channels_frame,
    icohp_bonds_frame,
    select_cohp_channels,
    select_icohp_bonds,
    sum_icohp_spins,
)
from catalysis_workbench.io.lobster import (
    LobsterIOError,
    _convert_cohpcar,
    _convert_icohplist,
    read_lobster_icohp,
)


def _energy() -> ElectronicEnergyAxis:
    return ElectronicEnergyAxis(
        (-2.0, 0.0, 2.0),
        reference_kind="fermi",
        source_fermi_ev=0.0,
        applied_shift_ev=0.0,
    )


def _cohp_result() -> COHPResult:
    channels = (
        COHPChannel(
            key="bond:1:spin:up",
            bond_key="bond:1",
            source_label="1",
            spin="up",
            cohp=(-1.0, -0.5, 0.25),
            integrated_cohp=(-0.2, -0.8, -0.4),
            bond_length_angstrom=2.1,
            source_site_indices=(0, 1),
        ),
        COHPChannel(
            key="bond:1:spin:down",
            bond_key="bond:1",
            source_label="1",
            spin="down",
            cohp=(-0.8, -0.4, 0.1),
            integrated_cohp=(-0.1, -0.6, -0.3),
            bond_length_angstrom=2.1,
            source_site_indices=(0, 1),
        ),
    )
    return COHPResult(energy=_energy(), channels=channels, producer_fermi_ev=5.4)


def test_cohp_state_preserves_source_sign_and_is_immutable() -> None:
    result = _cohp_result()
    assert result.energy.reference_kind == "fermi"
    assert result.energy.source_fermi_ev == 0.0
    assert result.producer_fermi_ev == pytest.approx(5.4)
    assert result.channels[0].cohp.tolist() == [-1.0, -0.5, 0.25]
    assert result.channels[0].integrated_cohp.tolist() == [-0.2, -0.8, -0.4]
    assert not result.channels[0].cohp.flags.writeable
    with pytest.raises(ValueError):
        result.channels[0].cohp[0] = 99.0


def test_cohp_channel_validation_rejects_misaligned_arrays() -> None:
    with pytest.raises(BondingError, match="identical shapes"):
        COHPChannel(
            key="x",
            bond_key="bond:1",
            source_label="1",
            spin="total",
            cohp=(1.0, 2.0),
            integrated_cohp=(1.0,),
        )


def test_cohp_result_requires_already_fermi_referenced_axis() -> None:
    axis = ElectronicEnergyAxis((-1.0, 0.0), reference_kind="source-native")
    channel = COHPChannel(
        key="x",
        bond_key="bond:1",
        source_label="1",
        spin="total",
        cohp=(1.0, 2.0),
        integrated_cohp=(0.1, 0.2),
    )
    with pytest.raises(BondingError, match="already Fermi-referenced"):
        COHPResult(energy=axis, channels=(channel,))


def test_select_cohp_channels_preserves_source_order_and_empty_fails() -> None:
    result = _cohp_result()
    selected = select_cohp_channels(result, spins=("down",))
    assert [channel.spin for channel in selected] == ["down"]
    with pytest.raises(BondingError, match="matched no"):
        select_cohp_channels(result, source_labels=("missing",))


def test_orbital_identity_is_all_or_none() -> None:
    with pytest.raises(BondingError, match="must be supplied together"):
        COHPChannel(
            key="x",
            bond_key="bond:1",
            source_label="1",
            spin="total",
            cohp=(1.0, 2.0),
            integrated_cohp=(0.1, 0.2),
            orbital_key="orbital:dxy",
        )


def test_icohp_summary_requires_complete_physical_spin_state() -> None:
    with pytest.raises(BondingError, match="both up and down"):
        ICOHPBondSummary(
            bond_key="bond:1",
            source_label="1",
            bond_length_angstrom=2.0,
            number_of_bonds=1,
            icohp_by_spin={"up": -1.0},
        )
    summary = ICOHPBondSummary(
        bond_key="bond:1",
        source_label="1",
        bond_length_angstrom=2.0,
        number_of_bonds=2,
        icohp_by_spin={"up": -1.2, "down": -0.8},
    )
    assert summary.spins == ("up", "down")
    with pytest.raises(TypeError):
        summary.icohp_by_spin["up"] = 0.0


def test_explicit_icohp_spin_sum_is_source_sign_and_provenance_bearing() -> None:
    summary = ICOHPBondSummary(
        bond_key="bond:1",
        source_label="1",
        bond_length_angstrom=2.0,
        number_of_bonds=1,
        icohp_by_spin={"up": -1.2, "down": -0.8},
    )
    result = sum_icohp_spins(summary, spins=("up", "down"))
    assert result.value == pytest.approx(-2.0)
    assert result.contributing_spins == ("up", "down")
    assert result.source_summary_digest == summary.digest
    with pytest.raises(BondingError, match="not retained"):
        sum_icohp_spins(summary, spins=("total",))


def test_icohp_selection_and_frames_are_detached() -> None:
    bonds = (
        ICOHPBondSummary(
            bond_key="bond:1",
            source_label="1",
            bond_length_angstrom=2.0,
            number_of_bonds=1,
            icohp_by_spin={"total": -1.5},
        ),
        ICOHPBondSummary(
            bond_key="bond:2",
            source_label="2",
            bond_length_angstrom=2.2,
            number_of_bonds=2,
            icohp_by_spin={"total": -0.5},
        ),
    )
    result = ICOHPResult(bonds=bonds)
    assert [bond.source_label for bond in select_icohp_bonds(result, bond_keys=("bond:2",))] == [
        "2"
    ]
    with pytest.raises(BondingError):
        select_icohp_bonds(result, source_labels=("missing",))
    frame = icohp_bonds_frame(result)
    frame.loc[0, "icohp_total"] = 99.0
    assert result.bonds[0].icohp_by_spin["total"] == pytest.approx(-1.5)


def test_cohp_frame_is_pointwise_and_detached() -> None:
    result = _cohp_result()
    frame = cohp_channels_frame(result)
    assert len(frame) == 6
    assert set(frame["spin"]) == {"up", "down"}
    assert set(frame["energy_reference"]) == {"fermi"}
    frame.loc[0, "cohp"] = 99.0
    assert result.channels[0].cohp[0] == pytest.approx(-1.0)


def _fake_cohpcar(*, spin_polarized: bool = False, variant: str | None = None) -> object:
    if spin_polarized:
        cohp = {1: np.array([-1.0, -0.5, 0.2]), -1: np.array([-0.8, -0.4, 0.1])}
        icohp = {1: np.array([-0.1, -0.7, -0.4]), -1: np.array([-0.1, -0.5, -0.3])}
    else:
        cohp = {1: np.array([-1.0, -0.5, 0.2])}
        icohp = {1: np.array([-0.1, -0.7, -0.4])}
    bond = {
        "COHP": cohp,
        "ICOHP": icohp,
        "length": 2.1,
        "sites": (0, 1),
    }
    orbital = {
        "d-p": {
            "COHP": cohp,
            "ICOHP": icohp,
            "length": 2.1,
            "sites": (0, 1),
            "orbitals": ("Fe:dxy", "O:px"),
        }
    }
    parsed = SimpleNamespace(
        energies=np.array([-2.0, 0.0, 2.0]),
        efermi=5.6,
        is_spin_polarized=spin_polarized,
        cohp_data={"average": {"COHP": cohp, "ICOHP": icohp}, "1": bond},
        orb_res_cohp={"1": orbital},
        are_coops=False,
        are_cobis=False,
        are_multi_center_cobis=False,
        is_lcfo=False,
    )
    if variant == "coop":
        parsed.are_coops = True
    if variant == "cobi":
        parsed.are_cobis = True
    return parsed


def test_convert_cohpcar_nonspin_retains_fermi_zero_and_omits_average() -> None:
    result = _convert_cohpcar(_fake_cohpcar(), path="COHPCAR.lobster", source_id="fixture")
    assert result.energy.values_ev.tolist() == [-2.0, 0.0, 2.0]
    assert result.energy.reference_kind == "fermi"
    assert result.energy.source_fermi_ev == 0.0
    assert result.producer_fermi_ev == pytest.approx(5.6)
    assert len(result.channels) == 2
    assert {channel.source_label for channel in result.channels} == {"1"}
    assert {channel.spin for channel in result.channels} == {"total"}
    orbital = [channel for channel in result.channels if channel.orbital_key is not None][0]
    assert orbital.orbital_key == "orbital:d-p"
    assert orbital.orbital_descriptors == ("Fe:dxy", "O:px")


def test_convert_cohpcar_spin_polarized_retains_up_down_without_mirroring() -> None:
    result = _convert_cohpcar(
        _fake_cohpcar(spin_polarized=True),
        path="COHPCAR.lobster",
        source_id=None,
    )
    base = [channel for channel in result.channels if channel.orbital_key is None]
    assert [channel.spin for channel in base] == ["up", "down"]
    assert base[1].cohp.tolist() == [-0.8, -0.4, 0.1]


@pytest.mark.parametrize("variant", ["coop", "cobi"])
def test_convert_cohpcar_rejects_non_cohp_variants(variant: str) -> None:
    with pytest.raises(LobsterIOError, match="unsupported variant"):
        _convert_cohpcar(
            _fake_cohpcar(variant=variant),
            path="COHPCAR.lobster",
            source_id=None,
        )


def test_convert_cohpcar_rejects_incomplete_spin_state() -> None:
    parsed = _fake_cohpcar(spin_polarized=True)
    parsed.cohp_data["1"]["COHP"] = {1: np.array([-1.0, -0.5, 0.2])}
    with pytest.raises(LobsterIOError, match="both up and down"):
        _convert_cohpcar(parsed, path="COHPCAR.lobster", source_id=None)


def _fake_icohplist(*, spin_polarized: bool = False, variant: str | None = None) -> object:
    values = {1: -1.5, -1: -0.5} if spin_polarized else {1: -1.5}
    parsed = SimpleNamespace(
        is_spin_polarized=spin_polarized,
        icohplist={
            "1": {"length": 2.0, "number_of_bonds": 2, "icohp": values},
            "2": {"length": 2.2, "number_of_bonds": 1, "icohp": {**values}},
        },
        are_coops=False,
        are_cobis=False,
        are_multi_center_cobis=False,
        is_lcfo=False,
    )
    if variant == "coop":
        parsed.are_coops = True
    return parsed


def test_convert_icohplist_retains_multiplicity_and_source_sign() -> None:
    result = _convert_icohplist(
        _fake_icohplist(),
        path="ICOHPLIST.lobster",
        source_id="fixture",
    )
    assert [bond.number_of_bonds for bond in result.bonds] == [2, 1]
    assert result.bonds[0].icohp_by_spin["total"] == pytest.approx(-1.5)
    assert result.source_id == "fixture"


def test_convert_icohplist_rejects_fractional_multiplicity() -> None:
    parsed = _fake_icohplist()
    parsed.icohplist["1"]["number_of_bonds"] = 1.5
    with pytest.raises(LobsterIOError, match="exact integer"):
        _convert_icohplist(parsed, path="ICOHPLIST.lobster", source_id=None)


def test_convert_icohplist_spin_state_and_explicit_sum() -> None:
    result = _convert_icohplist(
        _fake_icohplist(spin_polarized=True),
        path="ICOHPLIST.lobster",
        source_id=None,
    )
    summary = result.bonds[0]
    assert summary.spins == ("up", "down")
    summed = sum_icohp_spins(summary, spins=("up", "down"))
    assert summed.value == pytest.approx(-2.0)


def test_read_icohp_requires_boolean_spin_mode_before_backend_import() -> None:
    with pytest.raises(TypeError, match="is_spin_polarized must be a bool"):
        read_lobster_icohp("does-not-matter", is_spin_polarized=1)  # type: ignore[arg-type]


def test_convert_icohplist_rejects_non_cohp_variant() -> None:
    with pytest.raises(LobsterIOError, match="unsupported variant"):
        _convert_icohplist(
            _fake_icohplist(variant="coop"),
            path="ICOHPLIST.lobster",
            source_id=None,
        )
