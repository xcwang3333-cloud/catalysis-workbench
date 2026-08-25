"""Installed-wheel and backend-geometry smoke for v0.7 Block-7 3-D rendering."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import matplotlib.image as mpimg
import numpy as np
import pyvista as pv
import vtk

from catalysis_workbench.computation import (
    AtomicStructure,
    SiteImage,
    StructureBondSpec,
    StructureCameraSpec,
    build_structure_scene,
    slice_cartesian_coordinate_grid,
    slice_scalar_field,
)
from catalysis_workbench.computation.scalar_field import ScalarField
from catalysis_workbench.visualization import (
    IsosurfaceLayerSpec,
    SliceLayerSpec,
    Volumetric3DRenderSpec,
    VolumetricScene,
    export_volumetric_scene_3d,
    render_volumetric_scene_3d,
)
from catalysis_workbench.visualization.volumetric_3d import (
    _FIELD_SCALARS,
    _SLICE_SCALARS,
    _apply_fractional_clip,
    _field_cartesian_grid,
    _structured_grid_from_scalar_field,
    _structured_grid_from_slice,
)


def _fixture() -> tuple[ScalarField, VolumetricScene]:
    lattice = np.array(
        [
            [2.0, 0.0, 0.0],
            [0.55, 2.1, 0.0],
            [0.25, 0.35, 2.3],
        ],
        dtype=np.float64,
    )
    structure = AtomicStructure(
        species=("H", "H"),
        elements=("H", "H"),
        cartesian_coordinates=((0.35, 0.45, 0.55), (1.15, 0.85, 0.75)),
        lattice_angstrom=lattice,
        pbc=(True, True, True),
        site_keys=("H1", "H2"),
    )
    shape = (4, 3, 3)
    i = np.indices(shape, dtype=np.float64)[0]
    values = i / shape[0]
    field = ScalarField(
        structure=structure,
        values=values,
        field_kind="test-linear-fractional-a",
        value_unit="dimensionless",
        source_type="installed-smoke",
        source_key="linear-a",
        source_digest="installed-volumetric3d",
    )
    scalar_slice = slice_scalar_field(field, axis=2, index=1)
    structure_scene = build_structure_scene(
        structure,
        bonds=(StructureBondSpec(SiteImage("H1"), SiteImage("H2")),),
        camera=StructureCameraSpec(
            projection="orthographic",
            elevation_degrees=25.0,
            azimuth_degrees=-50.0,
            roll_degrees=5.0,
        ),
    )
    scene = VolumetricScene(
        layers=(
            IsosurfaceLayerSpec(
                scalar_field=field,
                threshold=0.375,
                color="#D95F02",
                opacity=0.62,
                label="f_a = 0.375",
            ),
            SliceLayerSpec(
                scalar_slice=scalar_slice,
                colormap="viridis",
                opacity=0.58,
                value_min=0.0,
                value_max=0.75,
                label="exact slice",
            ),
        ),
        structure_scene=structure_scene,
        camera=structure_scene.camera,
        background="#FFFFFF",
    )
    return field, scene


def _assert_backend_geometry(field: ScalarField, scene: VolumetricScene) -> None:
    lattice = np.asarray(field.structure.lattice_angstrom, dtype=np.float64)
    inverse = np.linalg.inv(lattice)
    cartesian = _field_cartesian_grid(field)
    grid = _structured_grid_from_scalar_field(field, pv)
    expected_points = np.column_stack(
        [cartesian[..., axis].ravel(order="F") for axis in range(3)]
    )
    assert np.allclose(grid.points, expected_points, rtol=0.0, atol=1e-12)
    assert np.array_equal(
        np.asarray(grid.point_data[_FIELD_SCALARS]),
        np.asarray(field.values).ravel(order="F"),
    )

    mesh = grid.contour(isosurfaces=[0.375], scalars=_FIELD_SCALARS)
    assert mesh.n_points > 0 and mesh.n_cells > 0
    fractional = np.asarray(mesh.points) @ inverse
    assert np.allclose(fractional[:, 0], 0.375, rtol=0.0, atol=1e-10)

    clipped = _apply_fractional_clip(
        mesh,
        lattice_angstrom=lattice,
        bounds=((0.35, 0.45), (0.15, 0.75), (0.0, 1.0)),
    )
    assert clipped.n_points > 0 and clipped.n_cells > 0
    clipped_fractional = np.asarray(clipped.points) @ inverse
    assert np.all(clipped_fractional[:, 0] >= 0.35 - 1e-10)
    assert np.all(clipped_fractional[:, 0] <= 0.45 + 1e-10)
    assert np.all(clipped_fractional[:, 1] >= 0.15 - 1e-10)
    assert np.all(clipped_fractional[:, 1] <= 0.75 + 1e-10)

    slice_layer = scene.layers[1]
    assert isinstance(slice_layer, SliceLayerSpec)
    slice_grid = _structured_grid_from_slice(slice_layer.scalar_slice, pv)
    expected_slice = slice_cartesian_coordinate_grid(slice_layer.scalar_slice)
    expected_slice_points = np.column_stack(
        [expected_slice[..., axis].ravel(order="F") for axis in range(3)]
    )
    assert np.allclose(slice_grid.points, expected_slice_points, rtol=0.0, atol=1e-12)
    assert np.array_equal(
        np.asarray(slice_grid.point_data[_SLICE_SCALARS]),
        np.asarray(slice_layer.scalar_slice.values).ravel(order="F"),
    )


def main() -> None:
    assert tuple(int(part) for part in pv.__version__.split(".")[:2]) >= (0, 48)
    vtk_version = tuple(int(part) for part in vtk.vtkVersion.GetVTKVersion().split(".")[:2])
    assert (9, 5) <= vtk_version < (9, 7), vtk_version

    field, scene = _fixture()
    _assert_backend_geometry(field, scene)
    field_before = np.array(field.values, copy=True)
    field_digest = field.digest
    scene_digest = scene.geometry_digest

    spec = Volumetric3DRenderSpec(
        window_size_px=(360, 280),
        anti_aliasing="none",
        show_scalar_bars=True,
        clip_fractional_bounds=((0.1, 0.7), (0.0, 1.0), (0.0, 1.0)),
    )
    result = render_volumetric_scene_3d(scene, spec)
    assert result.image.shape == (280, 360, 3)
    assert result.image.dtype == np.uint8
    assert not result.image.flags.writeable
    assert np.std(result.image.astype(np.float64)) > 0.0
    assert result.scene_geometry_digest == scene.geometry_digest
    assert result.render_spec_digest == spec.digest
    assert result.backend_name == "pyvista"
    assert result.backend_version == pv.__version__
    assert result.vtk_version == vtk.vtkVersion.GetVTKVersion()
    assert result.visible_layer_count == 2
    assert not hasattr(result, "plotter")
    assert not hasattr(result, "mesh")
    assert np.array_equal(field.values, field_before)
    assert field.digest == field_digest
    assert scene.geometry_digest == scene_digest

    perspective_scene = VolumetricScene(
        layers=scene.layers,
        structure_scene=scene.structure_scene,
        camera=StructureCameraSpec(
            projection="perspective",
            elevation_degrees=18.0,
            azimuth_degrees=35.0,
            roll_degrees=-7.0,
        ),
        background=scene.background,
    )
    perspective = render_volumetric_scene_3d(
        perspective_scene,
        Volumetric3DRenderSpec(
            window_size_px=(240, 180),
            anti_aliasing="none",
            show_scalar_bars=False,
        ),
    )
    assert perspective.image.shape == (180, 240, 3)
    assert np.std(perspective.image.astype(np.float64)) > 0.0

    with TemporaryDirectory() as temporary:
        output = Path(temporary) / "volumetric3d.png"
        exported = export_volumetric_scene_3d(scene, output, spec)
        assert exported == output
        assert output.is_file() and output.stat().st_size > 0
        decoded = mpimg.imread(output)
        assert decoded.shape[:2] == (280, 360)

    assert np.array_equal(field.values, field_before)
    assert field.digest == field_digest
    assert scene.geometry_digest == scene_digest
    print(
        "installed v0.7 Block-7 volumetric3d smoke: ok; "
        f"pyvista={pv.__version__}; vtk={vtk.vtkVersion.GetVTKVersion()}"
    )


if __name__ == "__main__":
    main()
