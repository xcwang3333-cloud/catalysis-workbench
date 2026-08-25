from __future__ import annotations

import numpy as np

from catalysis_workbench.computation import (
    AtomicStructure,
    PeriodicImage,
    SiteImage,
    SiteMapping,
    compare_structures,
    coordination_by_cutoff,
    site_distance,
)


structure = AtomicStructure(
    species=("C", "O"),
    elements=("C", "O"),
    cartesian_coordinates=((0.1, 0.0, 0.0), (2.9, 0.0, 0.0)),
    lattice_angstrom=((3.0, 0.0, 0.0), (0.0, 3.0, 0.0), (0.0, 0.0, 3.0)),
    pbc=(True, True, True),
    site_keys=("c", "o"),
)

direct = site_distance(structure, SiteImage("c"), SiteImage("o"))
image = site_distance(
    structure,
    SiteImage("c"),
    SiteImage("o", PeriodicImage(-1, 0, 0)),
)
assert np.isclose(direct.distance_angstrom, 2.8)
assert np.isclose(image.distance_angstrom, 0.2)

neighbors = coordination_by_cutoff(structure, "c", 0.25, image_range=(1, 0, 0))
assert neighbors.coordination_number == 1
assert neighbors.neighbors[0].site_key == "o"
assert neighbors.neighbors[0].image == PeriodicImage(-1, 0, 0)

comparison = compare_structures(
    structure,
    structure,
    (SiteMapping("c", "c"), SiteMapping("o", "o")),
)
assert np.isclose(comparison.rmsd_angstrom, 0.0)
assert comparison.displacement_vectors_angstrom.flags.writeable is False
