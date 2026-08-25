from __future__ import annotations

import subprocess
import sys

import numpy as np

from catalysis_workbench.computation import AtomicStructure, StructureError
from catalysis_workbench.io import (
    StructureIOError,
    read_cif_structure,
    read_contcar,
    read_poscar,
    read_xyz_structure,
)

subprocess.run(
    [
        sys.executable,
        "-c",
        (
            "import sys; "
            "assert 'pymatgen' not in sys.modules; "
            "import catalysis_workbench.computation; "
            "import catalysis_workbench.io; "
            "assert 'pymatgen' not in sys.modules"
        ),
    ],
    check=True,
)

structure = AtomicStructure(
    species=("Pt", "O"),
    elements=("Pt", "O"),
    cartesian_coordinates=((0.0, 0.0, 0.0), (1.5, 0.0, 0.0)),
    lattice_angstrom=np.eye(3) * 8.0,
    pbc=(True, True, True),
    metadata={"installed": True},
)
assert structure.site_count == 2
assert structure.digest
assert not structure.cartesian_coordinates.flags.writeable
assert not structure.lattice_angstrom.flags.writeable
assert structure.metadata_dict() == {"installed": True}

for symbol in (
    AtomicStructure,
    StructureError,
    StructureIOError,
    read_poscar,
    read_contcar,
    read_cif_structure,
    read_xyz_structure,
):
    assert symbol is not None
