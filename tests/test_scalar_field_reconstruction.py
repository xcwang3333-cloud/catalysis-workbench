from __future__ import annotations

import numpy as np
import pytest

from catalysis_workbench.computation import AtomicStructure
from catalysis_workbench.computation.scalar_field import (
    ScalarField,
    ScalarFieldSlice,
)
from catalysis_workbench.visualization.volumetric import (
    IsosurfaceLayerSpec,
    VolumetricScene,
)


def _structure() -> AtomicStructure:
    return AtomicStructure(
        species=("H",),
        elements=("H",),
        cartesian_coordinates=((0.0, 0.0, 0.0),),
        lattice_angstrom=np.diag([2.0, 2.0, 2.0]),
        pbc=(True, True, True),
        site_keys=("site-H",),
    )


def _field() -> ScalarField:
    return ScalarField(
        structure=_structure(),
        values=np.ones((2, 2, 2)),
        field_kind="density",
        value_unit="u",
        source_type="fixture",
        source_key="field",
        source_digest="source",
        metadata={"tags": {"a", "b"}},
    )


def test_nested_set_metadata_is_frozen() -> None:
    field = _field()
    assert field.metadata["tags"] == frozenset({"a", "b"})

    scene = VolumetricScene(
        (IsosurfaceLayerSpec(field, threshold=0.5),),
        metadata={"tags": {"scene"}},
    )
    assert scene.metadata["tags"] == frozenset({"scene"})


def test_direct_slice_reconstruction_requires_integer_shape_and_axes() -> None:
    field = _field()
    lattice = field.structure.lattice_angstrom
    assert lattice is not None

    common = {
        "source_field_digest": field.digest,
        "structure_digest": field.structure.digest,
        "lattice_angstrom": lattice,
        "field_kind": field.field_kind,
        "value_unit": field.value_unit,
        "registration_id": field.registration_id,
        "axis": 0,
        "index": 0,
        "fractional_coordinate": 0.0,
        "values": np.ones((2, 2)),
    }

    with pytest.raises(TypeError, match="grid_shape"):
        ScalarFieldSlice(
            **common,
            grid_shape=(2.0, 2, 2),
            in_plane_axes=(1, 2),
        )

    with pytest.raises(TypeError, match="in_plane_axes"):
        ScalarFieldSlice(
            **common,
            grid_shape=(2, 2, 2),
            in_plane_axes=(1.0, 2),
        )
