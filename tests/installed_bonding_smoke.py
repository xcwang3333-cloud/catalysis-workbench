from __future__ import annotations

from catalysis_workbench import computation
from catalysis_workbench import io as cw_io
from pymatgen.io.lobster import Cohpcar, Icohplist


def main() -> None:
    assert Cohpcar.__name__ == "Cohpcar"
    assert Icohplist.__name__ == "Icohplist"
    assert issubclass(computation.BondingError, ValueError)
    assert issubclass(cw_io.LobsterIOError, ValueError)
    assert callable(cw_io.read_lobster_cohp)
    assert callable(cw_io.read_lobster_icohp)

    energy = computation.ElectronicEnergyAxis(
        (-2.0, 0.0, 2.0),
        reference_kind="fermi",
        source_fermi_ev=0.0,
        applied_shift_ev=0.0,
    )
    channel = computation.COHPChannel(
        key="bond:1:spin:total",
        bond_key="bond:1",
        source_label="1",
        spin="total",
        cohp=(-1.0, -0.5, 0.2),
        integrated_cohp=(-0.1, -0.7, -0.4),
        bond_length_angstrom=2.1,
        source_site_indices=(0, 1),
    )
    cohp = computation.COHPResult(
        energy=energy,
        channels=(channel,),
        producer_fermi_ev=5.5,
    )
    assert cohp.energy.reference_kind == "fermi"
    assert cohp.channels[0].cohp[0] == -1.0
    assert len(computation.cohp_channels_frame(cohp)) == 3

    summary = computation.ICOHPBondSummary(
        bond_key="bond:1",
        source_label="1",
        bond_length_angstrom=2.1,
        number_of_bonds=1,
        icohp_by_spin={"up": -1.0, "down": -0.5},
    )
    result = computation.ICOHPResult(bonds=(summary,))
    summed = computation.sum_icohp_spins(summary, spins=("up", "down"))
    assert summed.value == -1.5
    assert list(computation.icohp_bonds_frame(result)["source_label"]) == ["1"]
    print("installed v0.6 COHP/ICOHP public API + pymatgen-core backend smoke: ok")


if __name__ == "__main__":
    main()
