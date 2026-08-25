from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np

from catalysis_workbench.computation import (
    DOSChannel,
    DOSProjection,
    ElectronicDOS,
    ElectronicEnergyAxis,
    ElectronicStructureError,
    VolumetricGrid,
)
from catalysis_workbench.io import (
    ElectronicStructureIOError,
    read_chgcar_density,
    read_vasprun_dos,
)

CHGCAR = """Known density
1.0
2.0 0.0 0.0
0.0 2.0 0.0
0.0 0.0 2.0
H
1
Direct
0.0 0.0 0.0

2 1 1
4.0 12.0
"""


def main() -> None:
    from pymatgen.io.vasp.outputs import Chgcar, Vasprun

    public_surface = (
        DOSChannel,
        DOSProjection,
        ElectronicDOS,
        ElectronicEnergyAxis,
        ElectronicStructureError,
        VolumetricGrid,
        ElectronicStructureIOError,
        read_chgcar_density,
        read_vasprun_dos,
    )
    assert all(item is not None for item in public_surface)
    assert callable(read_chgcar_density)
    assert callable(read_vasprun_dos)
    assert Vasprun is not None
    assert Chgcar is not None

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "CHGCAR"
        path.write_text(CHGCAR, encoding="utf-8")

        # Regression-lock the backend boundary itself: current pymatgen-core text
        # parsing preserves VASP's file grid values rather than volume-normalizing.
        raw = Chgcar.from_file(path)
        np.testing.assert_allclose(
            np.asarray(raw.data["total"], dtype=float).reshape(-1),
            [4.0, 12.0],
        )

        result = read_chgcar_density(path, source_id="installed-smoke")
        assert isinstance(result, VolumetricGrid)
        assert result.grid_shape == (2, 1, 1)
        assert np.isclose(result.cell_volume_angstrom3, 8.0)
        np.testing.assert_allclose(result.components["total"].reshape(-1), [0.5, 1.5])
        assert np.isclose(result.component_integrals["total"], 8.0)
        assert result.metadata["source_id"] == "installed-smoke"

    import sys

    assert "matplotlib.pyplot" not in sys.modules


if __name__ == "__main__":
    main()
