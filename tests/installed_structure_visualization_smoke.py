from __future__ import annotations

import sys

import numpy as np

from catalysis_workbench.computation import (
    AtomicStructure,
    SiteImage,
    StructureBondSpec,
    build_structure_scene,
)

assert "matplotlib.pyplot" not in sys.modules

structure = AtomicStructure(
    species=("C", "O"),
    elements=("C", "O"),
    cartesian_coordinates=((0.0, 0.0, 0.0), (1.2, 0.0, 0.0)),
    lattice_angstrom=((3.0, 0.0, 0.0), (0.0, 3.0, 0.0), (0.0, 0.0, 3.0)),
    pbc=(True, True, True),
    site_keys=("c", "o"),
)
scene = build_structure_scene(
    structure,
    bonds=(StructureBondSpec(SiteImage("c"), SiteImage("o")),),
)
assert len(scene.atoms) == 2
assert len(scene.bonds) == 1
assert len(scene.cell_edges_angstrom) == 12
assert scene.atoms[0].position_angstrom.flags.writeable is False

from catalysis_workbench.visualization import plot_structure

figure, ax = plot_structure(scene)
assert ax.name == "3d"
assert len(ax.collections) == 2
assert len(ax.lines) == 13
np.testing.assert_allclose(scene.atoms[1].position_angstrom, [1.2, 0.0, 0.0])
figure.canvas.draw()
