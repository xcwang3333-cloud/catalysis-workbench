"""Installed optional-backend smoke for current pymatgen-core PROCAR surface."""

from __future__ import annotations

import inspect
from importlib.metadata import version
from types import SimpleNamespace

import numpy as np
from pymatgen.io.vasp.outputs import Procar

from catalysis_workbench.computation import (
    AtomicStructure,
    BandEnergyChannel,
    BandPathSegment,
    BandStructureState,
)
from catalysis_workbench.io.procar import _convert_procar_result


def main() -> None:
    assert Procar.__name__ == "Procar"
    assert callable(Procar)
    assert hasattr(Procar, "read")
    assert hasattr(Procar, "_parse_kpoint_line")
    parse_source = inspect.getsource(Procar._parse_kpoint_line)
    assert "round(float(val), 5)" in parse_source
    read_source = inspect.getsource(Procar.read)
    assert "headers.pop(0)" in read_source
    assert "headers.pop(-1)" in read_source

    structure = AtomicStructure(
        species=("H",),
        elements=("H",),
        cartesian_coordinates=((0.0, 0.0, 0.0),),
        lattice_angstrom=np.diag([2.0, 2.0, 2.0]),
        pbc=(True, True, True),
        site_keys=("site-H",),
    )
    band = BandStructureState(
        structure=structure,
        kpoints_fractional=np.array([[0.0, 0.0, 0.0], [0.333333, 0.0, 0.0]]),
        reciprocal_lattice_cartesian=np.diag([2.0, 3.0, 4.0]),
        reciprocal_unit="1/angstrom",
        reciprocal_cartesian_includes_2pi=True,
        channels=(
            BandEnergyChannel(
                spin="total",
                energies_ev=np.array([[4.0, 4.5], [6.0, 6.5]]),
                band_indices=(0, 1),
            ),
        ),
        path_segments=(BandPathSegment("G-X", 0, 1, "G", "X"),),
        source_digest="installed-procar-band",
        source_fermi_ev=5.0,
    )

    source_projection = np.array(
        [
            [[[0.20, 0.80]], [[0.30, 0.70]]],
            [[[0.40, 0.60]], [[0.50, 0.50]]],
        ],
        dtype=float,
    )
    parsed = SimpleNamespace(
        is_soc=False,
        xyz_data=None,
        orbitals=["s", "pz"],
        kpoints=np.array([[0.0, 0.0, 0.0], [0.33333, 0.0, 0.0]]),
        data={1: source_projection},
        eigenvalues={1: band.channel("total").energies_ev.T},
        occupancies={1: np.ones((2, 2))},
        nions=1,
        weights=np.array([1.0, 0.0]),
    )
    state = _convert_procar_result(
        parsed,
        band_structure=band,
        path="PROCAR",
        source_id="installed-current-procar",
        kpoint_atol=1e-5,
        energy_atol_ev=1e-4,
        backend_version=version("pymatgen-core"),
    )
    assert state.orbitals == ("s", "pz")
    assert "tot" not in state.orbitals
    assert state.channels[0].spin == "total"
    assert np.array_equal(
        state.channels[0].weights,
        np.transpose(source_projection, (1, 0, 2, 3)),
    )
    assert state.metadata["pymatgen_core_version"] == version("pymatgen-core")
    print("installed current pymatgen-core PROCAR smoke: ok")


if __name__ == "__main__":
    main()
