"""Installed-wheel smoke for v0.7 Block-5 LOCPOT/work-function public API."""

from __future__ import annotations

import sys

import numpy as np

from catalysis_workbench.computation import (
    AtomicStructure,
    FermiLevelSource,
    ScalarField,
    calculate_work_function,
    planar_average_potential,
    vacuum_level_from_profile,
)
from catalysis_workbench.io import read_locpot_field
from catalysis_workbench.visualization import plot_planar_potential


def main() -> None:
    assert callable(read_locpot_field)
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
    field = ScalarField(
        structure=structure,
        values=np.arange(24.0).reshape(2, 3, 4),
        field_kind="local-potential",
        value_unit="eV",
        source_type="LOCPOT",
        source_key="locpot:total",
        source_digest="installed-locpot",
        metadata={"calculation_id": "calc-installed"},
    )
    profile = planar_average_potential(field, axis=2)
    assert np.isclose(profile.normal_height_angstrom, 4.0, rtol=0.0, atol=1e-12)
    assert np.array_equal(profile.potential_ev, np.array([10.0, 11.0, 12.0, 13.0]))
    vacuum = vacuum_level_from_profile(profile, start_index=2, stop_index=4, side_id="top")
    fermi = FermiLevelSource(
        fermi_ev=5.0,
        source_digest="installed-fermi",
        calculation_id="calc-installed",
    )
    work = calculate_work_function(vacuum, fermi)
    assert work.work_function_ev == 7.5
    figure, ax = plot_planar_potential(
        profile,
        vacuum_level=vacuum,
        fermi_source=fermi,
        work_function=work,
    )
    assert figure.axes == [ax]
    assert len(ax.lines) == 3

    loaded_backend = [
        name
        for name in sys.modules
        if name == "pymatgen" or name.startswith("pymatgen.")
    ]
    assert not loaded_backend, loaded_backend
    print("installed v0.7 Block-5 LOCPOT/work-function smoke: ok")


if __name__ == "__main__":
    main()
