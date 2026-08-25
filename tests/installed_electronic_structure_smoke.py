from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np

from catalysis_workbench.computation import (
    DOSChannel,
    DOSProjection,
    ElectronicDOS,
    ElectronicEnergyAxis,
    VolumetricGrid,
)
from catalysis_workbench.io import read_chgcar_density

assert "matplotlib.pyplot" not in sys.modules

from pymatgen.io.vasp.outputs import Chgcar, Vasprun  # noqa: E402

CHGCAR = """fixture
1.0
2.0 0.0 0.0
0.0 2.0 0.0
0.0 0.0 2.0
H
1
Direct
0.0 0.0 0.0

2 1 1
8.0 16.0
"""


def main() -> None:
    assert Vasprun is not None
    assert Chgcar is not None
    projection = DOSProjection(key="total", kind="total")
    dos = ElectronicDOS(
        energy=ElectronicEnergyAxis([-1.0, 0.0, 1.0], source_fermi_ev=0.2),
        channels=[DOSChannel(projection, "total", [1.0, 2.0, 1.0])],
    )
    assert dos.energy.reference_kind == "source-native"

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "CHGCAR"
        path.write_text(CHGCAR, encoding="utf-8")
        parsed = Chgcar.from_file(path)
        raw = np.asarray(parsed.data["total"], dtype=float).reshape(-1)
        np.testing.assert_allclose(raw, [8.0, 16.0])

        result = read_chgcar_density(path, source_id="installed-smoke")
        assert isinstance(result, VolumetricGrid)
        np.testing.assert_allclose(
            result.components["total"].reshape(-1),
            [1.0, 2.0],
        )
        assert result.cell_volume_angstrom3 == 8.0
        assert result.voxel_volume_angstrom3 == 4.0
        assert result.component_integrals["total"] == 12.0
        assert result.metadata["source_id"] == "installed-smoke"


if __name__ == "__main__":
    main()
