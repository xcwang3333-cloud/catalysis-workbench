"""Installed-wheel smoke for v0.7 Block-3 band-structure public API."""

from __future__ import annotations

import sys

import numpy as np

from catalysis_workbench.computation import (
    AtomicStructure,
    BandEnergyChannel,
    BandPathSegment,
    BandStructureState,
    band_path_coordinates,
    reference_band_structure_to_fermi,
)
from catalysis_workbench.io import read_vasprun_band_structure
from catalysis_workbench.visualization import plot_band_structure


def main() -> None:
    assert callable(read_vasprun_band_structure)
    loaded_backend = [
        name
        for name in sys.modules
        if name == "pymatgen" or name.startswith("pymatgen.")
    ]
    assert not loaded_backend, loaded_backend

    structure = AtomicStructure(
        species=("H",),
        elements=("H",),
        cartesian_coordinates=((0.0, 0.0, 0.0),),
        lattice_angstrom=np.diag([2.0, 2.0, 2.0]),
        pbc=(True, True, True),
        site_keys=("site-H",),
    )
    state = BandStructureState(
        structure=structure,
        kpoints_fractional=np.array(
            [
                [0.0, 0.0, 0.0],
                [0.5, 0.0, 0.0],
                [0.0, 0.5, 0.0],
                [0.0, 1.0, 0.0],
            ]
        ),
        reciprocal_lattice_cartesian=np.diag([2.0, 3.0, 4.0]),
        reciprocal_unit="1/angstrom",
        reciprocal_cartesian_includes_2pi=True,
        channels=(
            BandEnergyChannel(
                spin="total",
                energies_ev=np.array(
                    [[4.0, 4.5, 5.0, 5.5], [6.0, 6.5, 7.0, 7.5]]
                ),
                band_indices=(0, 1),
            ),
        ),
        path_segments=(
            BandPathSegment("G-X", 0, 1, "G", "X"),
            BandPathSegment("M-Y", 2, 3, "M", "Y"),
        ),
        source_digest="installed-band-source",
        source_fermi_ev=5.0,
    )
    path = band_path_coordinates(state)
    assert np.array_equal(path.segments[0].distances, np.array([0.0, 1.0]))
    assert np.array_equal(path.segments[1].distances, np.array([1.0, 2.5]))

    referenced = reference_band_structure_to_fermi(state)
    assert referenced.reference_kind == "fermi"
    assert referenced.channels[0].energies_ev[0, 0] == -1.0

    figure, ax = plot_band_structure(referenced)
    assert len(ax.lines) == 4
    assert figure.axes == [ax]
    print("installed v0.7 Block-3 band-structure smoke: ok")


if __name__ == "__main__":
    main()
