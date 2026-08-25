"""Installed-wheel smoke for the v0.7 Block-1 scalar-field public surface."""

from __future__ import annotations

import sys

import numpy as np

from catalysis_workbench.computation import (
    AtomicStructure,
    ScalarField,
    cartesian_grid_coordinate,
    slice_scalar_field,
)
from catalysis_workbench.visualization import (
    IsosurfaceLayerSpec,
    SliceLayerSpec,
    VolumetricScene,
)


def main() -> None:
    loaded = [
        name
        for name in sys.modules
        if name == "pyvista"
        or name.startswith("pyvista.")
        or name == "vtk"
        or name.startswith("vtk.")
        or name == "skimage"
        or name.startswith("skimage.")
    ]
    assert not loaded, loaded

    structure = AtomicStructure(
        species=("H",),
        elements=("H",),
        cartesian_coordinates=((0.0, 0.0, 0.0),),
        lattice_angstrom=np.array(
            [[2.0, 0.5, 0.0], [0.0, 3.0, 0.75], [0.25, 0.0, 4.0]]
        ),
        pbc=(True, True, True),
        site_keys=("site-H",),
    )
    field = ScalarField(
        structure=structure,
        values=np.arange(24.0).reshape(2, 3, 4),
        field_kind="electron-density",
        value_unit="1/angstrom^3",
        source_type="installed-smoke",
        source_key="density",
        source_digest="installed-smoke-source",
        registration_id="frame-A",
    )
    scalar_slice = slice_scalar_field(field, axis=1, index=2)
    positive = IsosurfaceLayerSpec(field, threshold=0.02)
    negative = IsosurfaceLayerSpec(field, threshold=-0.02)
    slice_layer = SliceLayerSpec(scalar_slice)
    scene = VolumetricScene((positive, negative, slice_layer))

    expected = np.array([0.5, 2.0 / 3.0, 0.75]) @ structure.lattice_angstrom
    assert np.allclose(cartesian_grid_coordinate(field, (1, 2, 3)), expected)
    assert scalar_slice.fractional_coordinate == 2.0 / 3.0
    assert scene.layers == (positive, negative, slice_layer)
    assert positive.geometry_digest != negative.geometry_digest
    print("installed v0.7 Block-1 scalar-field smoke: ok")


if __name__ == "__main__":
    main()
