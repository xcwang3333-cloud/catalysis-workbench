"""Installed-wheel smoke for v0.7 Block-2 density and ELF visualization."""

from __future__ import annotations

import sys

import numpy as np

from catalysis_workbench.computation import (
    AtomicStructure,
    ScalarField,
    VolumetricGrid,
    slice_scalar_field,
)
from catalysis_workbench.io import read_elfcar_field
from catalysis_workbench.visualization import (
    SliceLayerSpec,
    build_electron_density_scene,
    build_elf_scene,
    plot_scalar_field_slice,
)


def main() -> None:
    assert callable(read_elfcar_field)
    loaded_backend = [
        name
        for name in sys.modules
        if name == "pymatgen" or name.startswith("pymatgen.")
    ]
    assert not loaded_backend, loaded_backend

    structure = AtomicStructure(
        species=("H",),
        elements=("H",),
        cartesian_coordinates=((0.0, 0.0, 0.0),),
        lattice_angstrom=np.array(
            [[2.0, 0.0, 0.0], [0.5, 2.0, 0.0], [0.0, 0.0, 3.0]]
        ),
        pbc=(True, True, True),
        site_keys=("site-H",),
    )
    density = VolumetricGrid(
        structure=structure,
        components={"total": np.arange(8.0).reshape(2, 2, 2) + 1.0},
    )
    density_scene = build_electron_density_scene(density, threshold=0.5)
    assert density_scene.layers[0].scalar_field.value_unit == "1/angstrom^3"

    elf = ScalarField(
        structure=structure,
        values=np.linspace(0.1, 0.8, 8).reshape(2, 2, 2),
        field_kind="elf",
        value_unit="dimensionless",
        source_type="installed-smoke",
        source_key="elf",
        source_digest="installed-elf-source",
    )
    elf_scene = build_elf_scene(elf, threshold=0.6)
    assert elf_scene.layers[0].threshold == 0.6

    layer = SliceLayerSpec(
        scalar_slice=slice_scalar_field(elf, axis=2, index=0),
        value_min=0.0,
        value_max=1.0,
        label="ELF",
    )
    figure, ax = plot_scalar_field_slice(layer, show_colorbar=False)
    assert len(ax.collections) == 1
    assert figure.axes == [ax]
    print("installed v0.7 Block-2 density/ELF visualization smoke: ok")


if __name__ == "__main__":
    main()
