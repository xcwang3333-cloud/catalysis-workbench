from __future__ import annotations

import numpy as np
import pytest

from catalysis_workbench.computation import AtomicStructure, ScalarField
from catalysis_workbench.computation.electronic_structure import VolumetricGrid
from catalysis_workbench.computation.scalar_field import (
    scalar_field_from_volumetric_grid,
)
from catalysis_workbench.visualization.volumetric import (
    IsosurfaceLayerSpec,
    VolumetricScene,
    VolumetricSceneError,
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


def test_adapter_metadata_cannot_overwrite_reserved_provenance() -> None:
    grid = VolumetricGrid(
        structure=_structure(),
        components={"total": np.ones((2, 2, 2))},
    )
    field = scalar_field_from_volumetric_grid(
        grid,
        "total",
        field_kind="electron-density",
        registration_id="frame-A",
        metadata={
            "volumetric_grid_digest": "contradiction",
            "component": "wrong",
        },
    )

    assert field.metadata["volumetric_grid_digest"] == grid.digest
    assert field.metadata["component"] == "total"
    assert (
        field.metadata["adapter_metadata"]["volumetric_grid_digest"]
        == "contradiction"
    )
    assert field.metadata["adapter_metadata"]["component"] == "wrong"


def test_multiple_distinct_source_fields_require_explicit_registration() -> None:
    structure = _structure()
    first = ScalarField(
        structure=structure,
        values=np.ones((2, 2, 2)),
        field_kind="density",
        value_unit="u",
        source_type="fixture",
        source_key="first",
        source_digest="first-source",
    )
    second = ScalarField(
        structure=structure,
        values=np.ones((2, 2, 2)),
        field_kind="density",
        value_unit="u",
        source_type="fixture",
        source_key="second",
        source_digest="second-source",
    )

    with pytest.raises(VolumetricSceneError, match="explicit shared"):
        VolumetricScene(
            (
                IsosurfaceLayerSpec(first, threshold=0.5),
                IsosurfaceLayerSpec(second, threshold=0.5),
            )
        )
