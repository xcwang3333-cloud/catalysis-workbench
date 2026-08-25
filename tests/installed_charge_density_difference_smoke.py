from __future__ import annotations

import numpy as np

from catalysis_workbench.computation import (
    AtomicStructure,
    ChargeDensityDifferenceError,
    ChargeDensityDifferenceResult,
    ChargeDensityReferenceTerm,
    ChargeDensitySource,
    VolumetricGrid,
    calculate_charge_density_difference,
    charge_density_difference_frame,
)

assert ChargeDensityDifferenceError is not None
assert ChargeDensityDifferenceResult is not None

structure = AtomicStructure(
    species=("H",),
    elements=("H",),
    cartesian_coordinates=((0.0, 0.0, 0.0),),
    lattice_angstrom=((2.0, 0.0, 0.0), (0.0, 2.0, 0.0), (0.0, 0.0, 2.0)),
    pbc=(True, True, True),
    site_keys=("site-H",),
)
combined_grid = VolumetricGrid(
    structure=structure,
    components={"total": np.full((2, 2, 2), 4.0)},
)
reference_grid = VolumetricGrid(
    structure=structure,
    components={"total": np.ones((2, 2, 2))},
)
combined = ChargeDensitySource(
    key="combined",
    grid=combined_grid,
    component="total",
    registration_id="installed-frame",
)
reference = ChargeDensityReferenceTerm(
    ChargeDensitySource(
        key="reference",
        grid=reference_grid,
        component="total",
        registration_id="installed-frame",
    ),
    coefficient=1.0,
)
result = calculate_charge_density_difference(
    combined,
    (reference,),
    lattice_tolerance_angstrom=0.0,
)
assert np.array_equal(result.difference, np.full((2, 2, 2), 3.0))
assert result.integrated_difference_electrons == 24.0
frame = charge_density_difference_frame(result)
assert list(frame["role"]) == ["combined", "reference"]
assert list(frame["formula_coefficient"]) == [1.0, -1.0]
print("installed v0.6 charge-density difference smoke: ok")
