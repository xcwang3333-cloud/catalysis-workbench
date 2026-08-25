"""Installed optional-backend smoke for current pymatgen-core ELFCAR semantics."""

from __future__ import annotations

from tempfile import TemporaryDirectory
from pathlib import Path

import numpy as np
from pymatgen.core import Lattice, Structure
from pymatgen.io.vasp.outputs import Elfcar

from catalysis_workbench.io import read_elfcar_field


def main() -> None:
    structure = Structure(Lattice.cubic(2.0), ["H"], [[0.0, 0.0, 0.0]])
    unpolarized = np.linspace(0.1, 0.8, 8).reshape(2, 2, 2)
    up = np.full((2, 2, 2), 0.8)
    down = np.full((2, 2, 2), 0.3)

    with TemporaryDirectory() as directory:
        root = Path(directory)
        unpolarized_path = root / "ELFCAR"
        Elfcar(structure, {"total": unpolarized}).write_file(unpolarized_path)
        parsed = Elfcar.from_file(unpolarized_path)
        assert set(dict(parsed.data)) == {"total"}
        field = read_elfcar_field(unpolarized_path, source_id="unpolarized")
        assert field.field_kind == "elf"
        assert field.value_unit == "dimensionless"
        assert np.allclose(field.values, unpolarized)

        spin_path = root / "ELFCAR.spin"
        Elfcar(structure, {"spin_up": up, "spin_down": down}).write_file(spin_path)
        parsed_spin = Elfcar.from_file(spin_path)
        assert set(dict(parsed_spin.data)) == {"spin_up", "spin_down"}
        up_field = read_elfcar_field(spin_path, spin="up", source_id="spin")
        down_field = read_elfcar_field(spin_path, spin="down", source_id="spin")
        assert np.allclose(up_field.values, up)
        assert np.allclose(down_field.values, down)
        assert up_field.metadata["channel_semantics"] == "direct-spin-channels"

    print("installed current pymatgen-core ELFCAR smoke: ok")


if __name__ == "__main__":
    main()
