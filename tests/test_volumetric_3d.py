from __future__ import annotations

import importlib.util
import sys

import numpy as np
import pytest

from catalysis_workbench.visualization import (
    Volumetric3DBackendError,
    Volumetric3DRenderResult,
    Volumetric3DRenderSpec,
    Volumetric3DVisualizationError,
    export_volumetric_scene_3d,
    render_volumetric_scene_3d,
)


def test_public_import_does_not_eagerly_load_heavy_backend() -> None:
    assert "pyvista" not in sys.modules
    assert "vtk" not in sys.modules


def test_render_spec_retains_explicit_presentation_state_and_digest() -> None:
    spec = Volumetric3DRenderSpec(
        window_size_px=(640, 480),
        transparent_background=True,
        surface_lighting=False,
        slice_lighting=True,
        anti_aliasing="fxaa",
        show_scalar_bars=False,
        sphere_theta_resolution=20,
        sphere_phi_resolution=18,
        bond_radius_per_linewidth_angstrom=0.04,
        camera_distance_factor=3.2,
        perspective_view_angle_degrees=35.0,
        orthographic_scale_factor=0.75,
        clip_fractional_bounds=((0.1, 0.9), (0.0, 1.0), (0.2, 0.8)),
    )
    assert spec.window_size_px == (640, 480)
    assert spec.transparent_background is True
    assert spec.surface_lighting is False
    assert spec.slice_lighting is True
    assert spec.anti_aliasing == "fxaa"
    assert spec.show_scalar_bars is False
    assert spec.clip_fractional_bounds == ((0.1, 0.9), (0.0, 1.0), (0.2, 0.8))
    assert len(spec.digest) == 64
    duplicate = Volumetric3DRenderSpec(
        window_size_px=(640, 480),
        transparent_background=True,
        surface_lighting=False,
        slice_lighting=True,
        anti_aliasing="fxaa",
        show_scalar_bars=False,
        sphere_theta_resolution=20,
        sphere_phi_resolution=18,
        bond_radius_per_linewidth_angstrom=0.04,
        camera_distance_factor=3.2,
        perspective_view_angle_degrees=35.0,
        orthographic_scale_factor=0.75,
        clip_fractional_bounds=((0.1, 0.9), (0.0, 1.0), (0.2, 0.8)),
    )
    assert duplicate.digest == spec.digest


@pytest.mark.parametrize(
    "kwargs",
    [
        {"window_size_px": (0, 100)},
        {"window_size_px": (100, 2.5)},
        {"anti_aliasing": "magic"},
        {"sphere_theta_resolution": 7},
        {"sphere_phi_resolution": 0},
        {"bond_radius_per_linewidth_angstrom": 0.0},
        {"camera_distance_factor": np.inf},
        {"perspective_view_angle_degrees": 179.0},
        {"orthographic_scale_factor": -1.0},
        {"clip_fractional_bounds": ((0.2, 0.1), (0.0, 1.0), (0.0, 1.0))},
        {"clip_fractional_bounds": ((-0.1, 0.8), (0.0, 1.0), (0.0, 1.0))},
        {"clip_fractional_bounds": ((0.0, 1.0), (0.0, 1.1), (0.0, 1.0))},
    ],
)
def test_render_spec_fails_closed_on_invalid_state(kwargs: dict[str, object]) -> None:
    with pytest.raises((TypeError, Volumetric3DVisualizationError)):
        Volumetric3DRenderSpec(**kwargs)  # type: ignore[arg-type]


def test_render_result_is_backend_hidden_and_pixel_array_is_immutable() -> None:
    source = np.arange(4 * 5 * 3, dtype=np.uint8).reshape(4, 5, 3)
    result = Volumetric3DRenderResult(
        image=source,
        scene_geometry_digest="scene-digest",
        render_spec_digest="spec-digest",
        backend_name="pyvista",
        backend_version="0.48.4",
        vtk_version="9.6.2",
        visible_layer_count=2,
    )
    source[...] = 0
    assert result.width_px == 5
    assert result.height_px == 4
    assert result.channels == 3
    assert result.visible_layer_count == 2
    assert not result.image.flags.writeable
    assert np.any(result.image != 0)
    assert not hasattr(result, "plotter")
    assert not hasattr(result, "mesh")
    assert not hasattr(result, "actor")


def test_render_result_rejects_invalid_pixels_and_provenance() -> None:
    with pytest.raises(Volumetric3DVisualizationError, match="uint8"):
        Volumetric3DRenderResult(
            image=np.zeros((2, 2, 3), dtype=np.float64),
            scene_geometry_digest="scene",
            render_spec_digest="spec",
            backend_name="pyvista",
            backend_version="0.48.4",
            vtk_version="9.6.2",
            visible_layer_count=1,
        )
    with pytest.raises(Volumetric3DVisualizationError, match="provenance"):
        Volumetric3DRenderResult(
            image=np.zeros((2, 2, 3), dtype=np.uint8),
            scene_geometry_digest=" ",
            render_spec_digest="spec",
            backend_name="pyvista",
            backend_version="0.48.4",
            vtk_version="9.6.2",
            visible_layer_count=1,
        )


def test_public_renderer_type_checks_before_backend_import() -> None:
    with pytest.raises(TypeError, match="VolumetricScene"):
        render_volumetric_scene_3d(object())  # type: ignore[arg-type]


def test_png_export_boundary_is_checked_before_backend_import(tmp_path) -> None:
    with pytest.raises(Volumetric3DVisualizationError, match="PNG only"):
        export_volumetric_scene_3d(
            object(),  # type: ignore[arg-type]
            tmp_path / "scene.jpg",
        )


def test_missing_optional_backend_has_precise_installation_message() -> None:
    if importlib.util.find_spec("pyvista") is not None:
        pytest.skip("optional PyVista backend is installed in this test environment")
    from catalysis_workbench.visualization.volumetric_3d import _load_backend

    with pytest.raises(Volumetric3DBackendError, match="volumetric3d"):
        _load_backend()
