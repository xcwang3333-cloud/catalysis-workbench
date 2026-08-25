"""Installed optional-backend smoke for current pymatgen-core band semantics."""

from __future__ import annotations

from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from pymatgen.core import Lattice, Structure
from pymatgen.electronic_structure.core import Spin
from pymatgen.io.vasp.inputs import Kpoints

from catalysis_workbench.io.band_structure import _convert_vasprun_band_result


class _Run:
    def __init__(self, structure: Structure) -> None:
        self.parameters = {"ISPIN": 1, "LSORBIT": False, "LNONCOLLINEAR": False}
        self.actual_kpoints = np.array(
            [
                [0.0, 0.0, 0.0],
                [0.25, 0.0, 0.0],
                [0.5, 0.0, 0.0],
                [0.0, 0.5, 0.0],
                [0.0, 0.75, 0.0],
                [0.0, 1.0, 0.0],
            ]
        )
        values = np.zeros((6, 2, 2), dtype=np.float64)
        values[:, 0, 0] = np.arange(6.0) + 1.0
        values[:, 1, 0] = np.arange(6.0) + 11.0
        values[:, :, 1] = 0.5
        self.eigenvalues = {Spin.up: values}
        self.efermi = 5.0
        self.final_structure = structure


def main() -> None:
    backend_version = version("pymatgen-core")
    structure = Structure(
        Lattice.cubic(2.0),
        ["H"],
        [[0.0, 0.0, 0.0]],
    )
    reciprocal = structure.lattice.reciprocal_lattice.matrix
    assert np.allclose(reciprocal, np.diag([np.pi, np.pi, np.pi]))

    with TemporaryDirectory() as directory:
        kpoints_path = Path(directory) / "KPOINTS"
        kpoints_path.write_text(
            "Band path\n"
            "3\n"
            "Line-mode\n"
            "Reciprocal\n"
            "0.0 0.0 0.0 ! G\n"
            "0.5 0.0 0.0 ! X\n"
            "\n"
            "0.0 0.5 0.0 ! M\n"
            "0.0 1.0 0.0 ! Y\n",
            encoding="utf-8",
        )
        parsed_kpoints = Kpoints.from_file(kpoints_path)
        state = _convert_vasprun_band_result(
            _Run(structure),
            parsed_kpoints,
            path="vasprun.xml",
            kpoints_path=kpoints_path,
            source_id="installed-current-backend",
            backend_version=backend_version,
        )

    assert state.channels[0].spin == "total"
    assert state.reciprocal_cartesian_includes_2pi is True
    assert np.allclose(state.reciprocal_lattice_cartesian, reciprocal)
    assert [segment.start_label for segment in state.path_segments] == ["G", "M"]
    assert state.metadata["pymatgen_core_version"] == backend_version
    print("installed current pymatgen-core band-structure smoke: ok")


if __name__ == "__main__":
    main()
