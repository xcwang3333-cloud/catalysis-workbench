"""Installed optional-backend smoke for current pymatgen-core LOCPOT semantics."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from pymatgen.core import Lattice, Structure
from pymatgen.io.vasp.outputs import Locpot

from catalysis_workbench.computation import planar_average_potential
from catalysis_workbench.io import read_locpot_field


def main() -> None:
    lattice = Lattice(
        np.array(
            [
                [2.0, 0.0, 0.0],
                [0.0, 3.0, 0.0],
                [1.0, 0.0, 4.0],
            ]
        )
    )
    structure = Structure(lattice, ["H"], [[0.0, 0.0, 0.0]])
    values = np.arange(24.0).reshape(2, 3, 4) + 0.125

    with TemporaryDirectory() as directory:
        path = Path(directory) / "LOCPOT"
        Locpot(structure, {"total": values}).write_file(path)
        parsed = Locpot.from_file(path)
        assert set(dict(parsed.data)) == {"total"}
        assert np.allclose(parsed.data["total"], values, rtol=0.0, atol=1e-12)

        field = read_locpot_field(
            path,
            source_id="installed-locpot",
            calculation_id="calc-installed",
        )
        assert field.field_kind == "local-potential"
        assert field.value_unit == "eV"
        assert np.allclose(field.values, values, rtol=0.0, atol=1e-12)
        assert field.metadata["volume_normalized"] is False

        profile = planar_average_potential(field, axis=2)
        expected = np.mean(values, axis=(0, 1))
        assert np.allclose(profile.potential_ev, expected, rtol=0.0, atol=1e-12)
        assert np.isclose(profile.normal_height_angstrom, 4.0, rtol=0.0, atol=1e-12)

        backend_axis = np.asarray(parsed.get_axis_grid(2), dtype=float)
        assert np.isclose(backend_axis[1], np.sqrt(17.0) / 4.0, rtol=0.0, atol=1e-12)
        assert not np.isclose(
            backend_axis[1],
            profile.normal_coordinates_angstrom[1],
            rtol=0.0,
            atol=1e-12,
        )

    print("installed current pymatgen-core LOCPOT smoke: ok")


if __name__ == "__main__":
    main()
