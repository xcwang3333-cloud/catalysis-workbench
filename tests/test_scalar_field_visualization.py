from __future__ import annotations

import numpy as np
import pytest

from catalysis_workbench.computation.charge_density_difference import (
    ChargeDensityReferenceTerm,
    ChargeDensitySource,
    calculate_charge_density_difference,
)
from catalysis_workbench.computation.electronic_structure import VolumetricGrid
from catalysis_workbench.computation.scalar_field import (
    ScalarField,
    ScalarFieldError,
    cartesian_grid_coordinate,
    fractional_grid_coordinate,
    scalar_field_from_charge_density_difference,
    scalar_field_from_volumetric_grid,
    slice_cartesian_coordinate_grid,
    slice_fractional_coordinate_grid,
    slice_scalar_field,
)
from catalysis_workbench.computation.structure import AtomicStructure
from catalysis_workbench.computation.structure_scene import build_structure_scene
from catalysis_workbench.visualization.volumetric import (
    IsosurfaceLayerSpec,
    SliceLayerSpec,
    VolumetricScene,
    VolumetricSceneError,
)


def _structure(*, skew: bool = False, key: str = "site-H") -> AtomicStructure:
    lattice = (
        np.array(
            [
                [2.0, 0.5, 0.0],
                [0.0, 3.0, 0.75],
                [0.25, 0.0, 4.0],
            ]
        )
        if skew
        else np.diag([2.0, 3.0, 4.0])
    )
    return AtomicStructure(
        species=("H",),
        elements=("H",),
        cartesian_coordinates=((0.0, 0.0, 0.0),),
        lattice_angstrom=lattice,
        pbc=(True, True, True),
        site_keys=(key,),
    )


def _field(
    *,
    skew: bool = False,
    registration: str | None = "frame-A",
) -> ScalarField:
    return ScalarField(
        structure=_structure(skew=skew),
        values=np.arange(24.0).reshape(2, 3, 4),
        field_kind="electron-density",
        value_unit="1/angstrom^3",
        source_type="fixture",
        source_key="density",
        source_digest="source-digest",
        registration_id=registration,
        metadata={"nested": {"values": [1, 2]}},
    )


def test_scalar_field_volume_immutability_metadata_and_digest() -> None:
    field = _field()
    assert field.grid_shape == (2, 3, 4)
    assert field.cell_volume_angstrom3 == pytest.approx(24.0)
    assert field.voxel_volume_angstrom3 == pytest.approx(1.0)
    assert field.values[1, 2, 3] == 23.0
    with pytest.raises(ValueError):
        field.values[0, 0, 0] = 99.0

    detached = field.metadata_dict()
    detached["nested"]["values"][0] = 99
    assert field.metadata["nested"]["values"][0] == 1

    changed = ScalarField(
        structure=field.structure,
        values=field.values + 1.0,
        field_kind=field.field_kind,
        value_unit=field.value_unit,
        source_type=field.source_type,
        source_key=field.source_key,
        source_digest=field.source_digest,
        registration_id=field.registration_id,
    )
    assert changed.digest != field.digest


def test_scalar_field_rejects_invalid_foundation_state() -> None:
    nonperiodic = AtomicStructure(
        species=("H",),
        elements=("H",),
        cartesian_coordinates=((0.0, 0.0, 0.0),),
    )
    with pytest.raises(ScalarFieldError, match="fully periodic"):
        ScalarField(
            nonperiodic,
            np.ones((2, 2, 2)),
            "density",
            "u",
            "x",
            "k",
            "d",
        )

    for values in (np.ones((2, 2)), np.array([[[np.nan]]])):
        with pytest.raises(ScalarFieldError):
            ScalarField(
                _structure(),
                values,
                "density",
                "u",
                "x",
                "k",
                "d",
            )

    with pytest.raises(ScalarFieldError, match="field_kind"):
        ScalarField(
            _structure(),
            np.ones((1, 1, 1)),
            " ",
            "u",
            "x",
            "k",
            "d",
        )

    with pytest.raises(ScalarFieldError, match="registration_id"):
        ScalarField(
            _structure(),
            np.ones((1, 1, 1)),
            "density",
            "u",
            "x",
            "k",
            "d",
            registration_id=" ",
        )


def test_volumetric_adapter_preserves_exact_values_and_provenance() -> None:
    values = np.arange(8.0).reshape(2, 2, 2)
    grid = VolumetricGrid(
        structure=_structure(),
        components={"total": values},
    )
    field = scalar_field_from_volumetric_grid(
        grid,
        "total",
        field_kind="electron-density",
        registration_id="frame-A",
    )
    assert np.array_equal(field.values, grid.components["total"])
    assert field.value_unit == grid.density_unit
    assert field.source_digest == grid.digest
    assert field.structure == grid.structure
    assert field.metadata["component"] == "total"


def test_charge_density_difference_adapter_does_not_recalculate() -> None:
    structure = _structure()
    combined_grid = VolumetricGrid(
        structure=structure,
        components={"total": np.full((2, 2, 2), 5.0)},
    )
    reference_grid = VolumetricGrid(
        structure=structure,
        components={"total": np.ones((2, 2, 2))},
    )
    combined = ChargeDensitySource(
        "combined",
        combined_grid,
        "total",
        "frame-A",
    )
    reference = ChargeDensityReferenceTerm(
        ChargeDensitySource(
            "reference",
            reference_grid,
            "total",
            "frame-A",
        ),
        coefficient=2.0,
    )
    result = calculate_charge_density_difference(
        combined,
        (reference,),
        lattice_tolerance_angstrom=0.0,
    )
    field = scalar_field_from_charge_density_difference(result)
    assert np.array_equal(field.values, result.difference)
    assert field.source_digest == result.digest
    assert field.registration_id == result.registration_id
    assert (
        field.metadata["difference_grid_digest"]
        == result.difference_grid.digest
    )


def test_exact_source_grid_slices_preserve_axis_order_and_fraction() -> None:
    field = _field()
    for axis, index in ((0, 1), (1, 2), (2, 3)):
        scalar_slice = slice_scalar_field(field, axis=axis, index=index)
        assert np.array_equal(
            scalar_slice.values,
            np.take(field.values, index, axis=axis),
        )
        assert scalar_slice.fractional_coordinate == pytest.approx(
            index / field.grid_shape[axis]
        )
        assert scalar_slice.in_plane_axes == tuple(
            value for value in range(3) if value != axis
        )

    with pytest.raises(ScalarFieldError):
        slice_scalar_field(field, axis=3, index=0)
    with pytest.raises(ScalarFieldError):
        slice_scalar_field(field, axis=0, index=2)


def test_fractional_and_cartesian_coordinates_use_full_skew_lattice() -> None:
    field = _field(skew=True)
    fractional = fractional_grid_coordinate(field, (1, 2, 3))
    expected_fractional = np.array([0.5, 2.0 / 3.0, 0.75])
    assert np.allclose(fractional, expected_fractional)

    expected_cartesian = (
        expected_fractional @ field.structure.lattice_angstrom
    )
    assert np.allclose(
        cartesian_grid_coordinate(field, (1, 2, 3)),
        expected_cartesian,
    )

    scalar_slice = slice_scalar_field(field, axis=1, index=2)
    fractional_grid = slice_fractional_coordinate_grid(scalar_slice)
    cartesian_grid = slice_cartesian_coordinate_grid(scalar_slice)
    assert fractional_grid.shape == (2, 4, 3)
    assert np.allclose(
        cartesian_grid,
        fractional_grid @ field.structure.lattice_angstrom,
    )
    assert np.allclose(fractional_grid[..., 1], 2.0 / 3.0)


def test_isosurfaces_are_explicit_and_style_is_geometry_neutral() -> None:
    field = _field()
    positive = IsosurfaceLayerSpec(
        field,
        threshold=0.02,
        color="#AA0000",
    )
    positive_restyled = IsosurfaceLayerSpec(
        field,
        threshold=0.02,
        color="#00AA00",
        opacity=0.2,
    )
    negative = IsosurfaceLayerSpec(
        field,
        threshold=-0.02,
        color="#0000AA",
    )
    assert positive.geometry_digest == positive_restyled.geometry_digest
    assert positive.geometry_digest != negative.geometry_digest
    assert positive.value_unit == "1/angstrom^3"

    with pytest.raises(VolumetricSceneError, match="finite"):
        IsosurfaceLayerSpec(field, threshold=np.nan)


def test_scene_preserves_order_and_rejects_incompatible_geometry() -> None:
    field = _field()
    scalar_slice = slice_scalar_field(field, axis=2, index=1)
    iso = IsosurfaceLayerSpec(field, threshold=0.5)
    slice_layer = SliceLayerSpec(scalar_slice)
    structure_scene = build_structure_scene(field.structure)
    scene = VolumetricScene(
        (slice_layer, iso),
        structure_scene=structure_scene,
    )
    assert scene.layers == (slice_layer, iso)

    wrong_registration = _field(registration="frame-B")
    with pytest.raises(VolumetricSceneError, match="registration_id"):
        VolumetricScene(
            (
                iso,
                IsosurfaceLayerSpec(
                    wrong_registration,
                    threshold=0.5,
                ),
            )
        )

    wrong_shape = ScalarField(
        structure=field.structure,
        values=np.ones((2, 3, 5)),
        field_kind="electron-density",
        value_unit="1/angstrom^3",
        source_type="fixture",
        source_key="other",
        source_digest="other",
        registration_id="frame-A",
    )
    with pytest.raises(VolumetricSceneError, match="grid_shape"):
        VolumetricScene(
            (iso, IsosurfaceLayerSpec(wrong_shape, threshold=0.5))
        )

    other_structure = _structure(key="other-site")
    other_scene = build_structure_scene(other_structure)
    with pytest.raises(VolumetricSceneError, match="structure_scene"):
        VolumetricScene((iso,), structure_scene=other_scene)
