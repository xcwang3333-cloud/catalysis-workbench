"""Installed-wheel smoke for v0.7 Block-4 projected-band public API."""

from __future__ import annotations

import sys

import numpy as np

from catalysis_workbench.computation import (
    AtomicStructure,
    BandEnergyChannel,
    BandPathSegment,
    BandProjectionChannel,
    BandProjectionState,
    BandStructureState,
    aggregate_band_projection,
)
from catalysis_workbench.io import read_procar_projection
from catalysis_workbench.visualization import plot_fat_band


def main() -> None:
    assert callable(read_procar_projection)
    loaded_backend = [
        name
        for name in sys.modules
        if name == "pymatgen" or name.startswith("pymatgen.")
    ]
    assert not loaded_backend, loaded_backend

    structure = AtomicStructure(
        species=("H", "He"),
        elements=("H", "He"),
        cartesian_coordinates=((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)),
        lattice_angstrom=np.diag([2.0, 2.0, 2.0]),
        pbc=(True, True, True),
        site_keys=("site-H", "site-He"),
    )
    band = BandStructureState(
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
        source_digest="installed-block4-band",
        source_fermi_ev=5.0,
    )
    projection = BandProjectionState(
        band_structure=band,
        orbitals=("s", "pz", "tot"),
        channels=(
            BandProjectionChannel(
                "total",
                (np.arange(2 * 4 * 2 * 3).reshape(2, 4, 2, 3) + 1.0) / 100.0,
            ),
        ),
        source_digest="installed-block4-procar",
    )
    aggregated = aggregate_band_projection(
        projection,
        spin="total",
        site_indices=(0, 1),
        orbitals=("s", "pz"),
    )
    expected = projection.channel("total").weights[:, :, :, (0, 1)].sum(axis=(2, 3))
    assert np.array_equal(aggregated.weights, expected)

    figure, ax = plot_fat_band(aggregated, marker_area_scale=10.0)
    assert len(ax.lines) == 4
    assert len(ax.collections) == 4
    assert figure.axes == [ax]
    assert np.array_equal(ax.collections[0].get_sizes(), aggregated.weights[0, :2] * 10.0)

    loaded_backend = [
        name
        for name in sys.modules
        if name == "pymatgen" or name.startswith("pymatgen.")
    ]
    assert not loaded_backend, loaded_backend
    print("installed v0.7 Block-4 projected-band smoke: ok")


if __name__ == "__main__":
    main()
