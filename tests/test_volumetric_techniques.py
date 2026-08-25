from __future__ import annotations

import numpy as np
import pytest

from catalysis_workbench.computation import (
    AtomicStructure,
    ChargeDensityReferenceTerm,
    ChargeDensitySource,
    ScalarField,
    VolumetricGrid,
    calculate_charge_density_difference,
    slice_scalar_field,
)
from catalysis_workbench.visualization import (
    FigureSpec,
    SliceLayerSpec,
    VisualizationError,
    VolumetricSceneError,
    build_charge_density_difference_scene,
    build_electron_density_scene,
    build_elf_scene,
    build_symmetric_charge_density_difference_scene,
    plot_scalar_field_slice,
)


def _structure(*, skew: bool = False) -> AtomicStructure:
    lattice = (
        np.array([[2.0, 0.0, 0.0], [1.0, 2.0, 0.0], [0.0, 0.0, 3.0]])
        if skew
        else np.diag([2.0, 2.0, 2.0])
    )
    return AtomicStructure(
        species=("H",),
        elements=("H",),
        cartesian_coordinates=((0.0, 0.0, 0.0),),
        lattice_angstrom=lattice,
        pbc=(True, True, True),
        site_keys=("site-H",),
    )


def _difference_result():
    structure = _structure()
    combined = ChargeDensitySource(
        key="combined",
        grid=VolumetricGrid(
            structure=structure,
            components={"total": np.full((2, 2, 2), 5.0)},
        ),
        component="total",
        registration_id="frame-A",
    )
    reference = ChargeDensityReferenceTerm(
        source=ChargeDensitySource(
            key="reference",
            grid=VolumetricGrid(
                structure=structure,
                components={"total": np.ones((2, 2, 2))},
            ),
            component="total",
            registration_id="frame-A",
        ),
        coefficient=2.0,
    )
    return calculate_charge_density_difference(
        combined,
        (reference,),
        lattice_tolerance_angstrom=0.0,
    )


def test_charge_density_difference_scene_preserves_result_and_layer_order() -> None:
    result = _difference_result()
    before = np.array(result.difference, copy=True)

    scene = build_charge_density_difference_scene(
        result,
        positive_threshold=0.04,
        negative_threshold=-0.03,
    )

    assert [layer.threshold for layer in scene.layers] == [0.04, -0.03]
    assert scene.layers[0].source_field_digest == scene.layers[1].source_field_digest
    field = scene.layers[0].scalar_field
    assert field.registration_id == result.registration_id
    assert field.source_digest == result.digest
    assert field.metadata["difference_grid_digest"] == result.difference_grid.digest
    assert np.array_equal(field.values, result.difference)
    assert np.array_equal(result.difference, before)


def test_difference_threshold_signs_and_symmetric_magnitude_fail_closed() -> None:
    result = _difference_result()
    with pytest.raises(VolumetricSceneError, match="positive_threshold"):
        build_charge_density_difference_scene(
            result,
            positive_threshold=0.0,
            negative_threshold=-0.03,
        )
    with pytest.raises(VolumetricSceneError, match="negative_threshold"):
        build_charge_density_difference_scene(
            result,
            positive_threshold=0.03,
            negative_threshold=0.0,
        )
    with pytest.raises(VolumetricSceneError, match="magnitude"):
        build_symmetric_charge_density_difference_scene(result, magnitude=-0.1)

    scene = build_symmetric_charge_density_difference_scene(result, magnitude=0.07)
    assert [layer.threshold for layer in scene.layers] == [0.07, -0.07]


def test_presentation_style_does_not_change_difference_field_identity() -> None:
    result = _difference_result()
    first = build_charge_density_difference_scene(
        result,
        positive_threshold=0.04,
        negative_threshold=-0.04,
        positive_color="#111111",
        negative_color="#222222",
        opacity=0.2,
    )
    second = build_charge_density_difference_scene(
        result,
        positive_threshold=0.04,
        negative_threshold=-0.04,
        positive_color="#AAAAAA",
        negative_color="#BBBBBB",
        opacity=0.8,
    )
    assert first.layers[0].source_field_digest == second.layers[0].source_field_digest
    assert first.layers[0].geometry_digest == second.layers[0].geometry_digest
    assert first.geometry_digest == second.geometry_digest


def test_electron_density_scene_uses_exact_total_component_only() -> None:
    total = np.arange(8.0).reshape(2, 2, 2) + 1.0
    magnetization = np.full((2, 2, 2), -9.0)
    grid = VolumetricGrid(
        structure=_structure(),
        components={"total": total, "magnetization_z": magnetization},
    )
    scene = build_electron_density_scene(
        grid,
        threshold=0.5,
        registration_id="density-frame",
    )
    field = scene.layers[0].scalar_field
    assert field.field_kind == "electron-density"
    assert field.value_unit == "1/angstrom^3"
    assert field.registration_id == "density-frame"
    assert np.array_equal(field.values, total)
    assert not np.array_equal(field.values, magnetization)

    only_magnetic = VolumetricGrid(
        structure=_structure(),
        components={"magnetization_z": magnetization},
    )
    with pytest.raises(VolumetricSceneError, match="'total'"):
        build_electron_density_scene(only_magnetic, threshold=0.5)


def test_elf_scene_requires_explicit_elf_semantics() -> None:
    field = ScalarField(
        structure=_structure(),
        values=np.full((2, 2, 2), 0.7),
        field_kind="elf-spin-up",
        value_unit="dimensionless",
        source_type="ELFCAR",
        source_key="elfcar:up",
        source_digest="source-digest",
    )
    scene = build_elf_scene(field, threshold=0.65)
    assert scene.layers[0].threshold == pytest.approx(0.65)
    assert scene.layers[0].scalar_field is field

    wrong_kind = ScalarField(
        structure=_structure(),
        values=np.ones((2, 2, 2)),
        field_kind="potential",
        value_unit="dimensionless",
        source_type="fixture",
        source_key="fixture",
        source_digest="fixture",
    )
    with pytest.raises(VolumetricSceneError, match="field_kind"):
        build_elf_scene(wrong_kind, threshold=0.5)


def test_slice_renderer_uses_explicit_range_and_exact_values() -> None:
    values = np.arange(8.0).reshape(2, 2, 2)
    field = ScalarField(
        structure=_structure(skew=True),
        values=values,
        field_kind="elf",
        value_unit="dimensionless",
        source_type="fixture",
        source_key="elf",
        source_digest="elf-source",
    )
    scalar_slice = slice_scalar_field(field, axis=2, index=0)
    layer = SliceLayerSpec(
        scalar_slice=scalar_slice,
        colormap="viridis",
        value_min=0.0,
        value_max=6.0,
        label="ELF",
    )
    before = np.array(scalar_slice.values, copy=True)
    figure, ax = plot_scalar_field_slice(
        layer,
        FigureSpec(show_legend=False),
        coordinate_mode="angstrom",
    )

    assert np.array_equal(scalar_slice.values, before)
    assert len(ax.collections) == 1
    mesh = ax.collections[0]
    assert mesh.get_clim() == pytest.approx((0.0, 6.0))
    coordinates = mesh.get_coordinates()
    assert coordinates.shape == (3, 3, 2)
    assert coordinates[-1, -1] == pytest.approx((3.0, 2.0))
    assert len(figure.axes) == 2


def test_slice_renderer_never_infers_display_range() -> None:
    field = ScalarField(
        structure=_structure(),
        values=np.ones((2, 2, 2)),
        field_kind="electron-density",
        value_unit="1/angstrom^3",
        source_type="fixture",
        source_key="density",
        source_digest="density-source",
    )
    layer = SliceLayerSpec(scalar_slice=slice_scalar_field(field, axis=0, index=0))
    with pytest.raises(VisualizationError, match="explicit value_min and value_max"):
        plot_scalar_field_slice(layer)


def test_fractional_slice_rendering_uses_exact_unit_cell_edges() -> None:
    field = ScalarField(
        structure=_structure(skew=True),
        values=np.ones((2, 3, 4)),
        field_kind="elf",
        value_unit="dimensionless",
        source_type="fixture",
        source_key="elf",
        source_digest="elf-source",
    )
    layer = SliceLayerSpec(
        scalar_slice=slice_scalar_field(field, axis=0, index=1),
        value_min=0.0,
        value_max=1.0,
    )
    _, ax = plot_scalar_field_slice(
        layer,
        coordinate_mode="fractional",
        show_colorbar=False,
    )
    coordinates = ax.collections[0].get_coordinates()
    assert coordinates[0, 0] == pytest.approx((0.0, 0.0))
    assert coordinates[-1, -1] == pytest.approx((1.0, 1.0))
