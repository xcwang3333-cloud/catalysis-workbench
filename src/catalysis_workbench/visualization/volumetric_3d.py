"""Optional headless PyVista backend for renderer-neutral volumetric scenes."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from math import cos, isfinite, radians, sin
from pathlib import Path
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from catalysis_workbench.computation import (
    ScalarField,
    ScalarFieldSlice,
    StructureCameraSpec,
    slice_cartesian_coordinate_grid,
)

from .volumetric import (
    IsosurfaceLayerSpec,
    SliceLayerSpec,
    VolumetricScene,
)

AntiAliasingMode = Literal["none", "fxaa", "ssaa", "msaa"]

_FIELD_SCALARS = "catalysis_workbench_scalar"
_SLICE_SCALARS = "catalysis_workbench_slice"


class Volumetric3DVisualizationError(ValueError):
    """Raised when explicit 3-D rendering state is invalid."""


class Volumetric3DBackendError(ImportError):
    """Raised when the optional PyVista/VTK backend is unavailable."""


def _positive_real(value: object, *, name: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise TypeError(f"{name} must be a real numeric value")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a real numeric value") from exc
    if not isfinite(number) or number <= 0.0:
        raise Volumetric3DVisualizationError(f"{name} must be finite and positive")
    return number


def _positive_int(value: object, *, name: str) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{name} must be an integer")
    number = int(value)
    if number <= 0:
        raise Volumetric3DVisualizationError(f"{name} must be positive")
    return number


def _window_size(value: object) -> tuple[int, int]:
    try:
        width, height = value  # type: ignore[misc]
    except (TypeError, ValueError) as exc:
        raise TypeError("window_size_px must contain exactly two integers") from exc
    return (
        _positive_int(width, name="window width"),
        _positive_int(height, name="window height"),
    )


def _fractional_clip_bounds(
    value: object | None,
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]] | None:
    if value is None:
        return None
    try:
        axes = tuple(value)  # type: ignore[arg-type]
    except TypeError as exc:
        raise TypeError("clip_fractional_bounds must contain three (min, max) pairs") from exc
    if len(axes) != 3:
        raise Volumetric3DVisualizationError(
            "clip_fractional_bounds must contain exactly three axis bounds"
        )
    retained: list[tuple[float, float]] = []
    for axis, raw in enumerate(axes):
        try:
            lower_raw, upper_raw = raw
        except (TypeError, ValueError) as exc:
            raise TypeError(f"clip axis {axis} must contain exactly two values") from exc
        try:
            lower = float(lower_raw)
            upper = float(upper_raw)
        except (TypeError, ValueError) as exc:
            raise TypeError(f"clip axis {axis} values must be real numeric values") from exc
        if not isfinite(lower) or not isfinite(upper):
            raise Volumetric3DVisualizationError(
                f"clip axis {axis} bounds must be finite"
            )
        if not 0.0 <= lower < upper <= 1.0:
            raise Volumetric3DVisualizationError(
                f"clip axis {axis} requires 0 <= min < max <= 1"
            )
        retained.append((lower, upper))
    return retained[0], retained[1], retained[2]


def _digest_float(digest: Any, value: float) -> None:
    digest.update(np.float64(value).tobytes())


@dataclass(frozen=True, slots=True)
class Volumetric3DRenderSpec:
    """Explicit presentation/export controls for the optional static 3-D backend."""

    window_size_px: tuple[int, int] = (900, 700)
    transparent_background: bool = False
    surface_lighting: bool = True
    slice_lighting: bool = False
    anti_aliasing: AntiAliasingMode = "ssaa"
    show_scalar_bars: bool = True
    sphere_theta_resolution: int = 24
    sphere_phi_resolution: int = 24
    bond_radius_per_linewidth_angstrom: float = 0.035
    camera_distance_factor: float = 2.8
    perspective_view_angle_degrees: float = 30.0
    orthographic_scale_factor: float = 0.65
    clip_fractional_bounds: (
        tuple[tuple[float, float], tuple[float, float], tuple[float, float]] | None
    ) = None
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        size = _window_size(self.window_size_px)
        mode = str(self.anti_aliasing).strip().casefold()
        if mode not in {"none", "fxaa", "ssaa", "msaa"}:
            raise Volumetric3DVisualizationError(
                "anti_aliasing must be one of 'none', 'fxaa', 'ssaa', or 'msaa'"
            )
        theta = _positive_int(self.sphere_theta_resolution, name="sphere_theta_resolution")
        phi = _positive_int(self.sphere_phi_resolution, name="sphere_phi_resolution")
        if theta < 8 or phi < 8:
            raise Volumetric3DVisualizationError(
                "sphere resolutions must each be at least 8"
            )
        bond_scale = _positive_real(
            self.bond_radius_per_linewidth_angstrom,
            name="bond_radius_per_linewidth_angstrom",
        )
        distance = _positive_real(self.camera_distance_factor, name="camera_distance_factor")
        view_angle = _positive_real(
            self.perspective_view_angle_degrees,
            name="perspective_view_angle_degrees",
        )
        if view_angle >= 179.0:
            raise Volumetric3DVisualizationError(
                "perspective_view_angle_degrees must be less than 179"
            )
        ortho = _positive_real(
            self.orthographic_scale_factor,
            name="orthographic_scale_factor",
        )
        clip_bounds = _fractional_clip_bounds(self.clip_fractional_bounds)

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.Volumetric3DRenderSpec.v1\0")
        for item in size:
            digest.update(item.to_bytes(8, "little", signed=False))
        digest.update(bytes((bool(self.transparent_background),)))
        digest.update(bytes((bool(self.surface_lighting),)))
        digest.update(bytes((bool(self.slice_lighting),)))
        digest.update(bytes((bool(self.show_scalar_bars),)))
        digest.update(mode.encode("ascii"))
        digest.update(theta.to_bytes(8, "little", signed=False))
        digest.update(phi.to_bytes(8, "little", signed=False))
        for number in (bond_scale, distance, view_angle, ortho):
            _digest_float(digest, number)
        if clip_bounds is None:
            digest.update(b"no-clip\0")
        else:
            for lower, upper in clip_bounds:
                _digest_float(digest, lower)
                _digest_float(digest, upper)

        object.__setattr__(self, "window_size_px", size)
        object.__setattr__(self, "transparent_background", bool(self.transparent_background))
        object.__setattr__(self, "surface_lighting", bool(self.surface_lighting))
        object.__setattr__(self, "slice_lighting", bool(self.slice_lighting))
        object.__setattr__(self, "anti_aliasing", mode)
        object.__setattr__(self, "show_scalar_bars", bool(self.show_scalar_bars))
        object.__setattr__(self, "sphere_theta_resolution", theta)
        object.__setattr__(self, "sphere_phi_resolution", phi)
        object.__setattr__(self, "bond_radius_per_linewidth_angstrom", bond_scale)
        object.__setattr__(self, "camera_distance_factor", distance)
        object.__setattr__(self, "perspective_view_angle_degrees", view_angle)
        object.__setattr__(self, "orthographic_scale_factor", ortho)
        object.__setattr__(self, "clip_fractional_bounds", clip_bounds)
        object.__setattr__(self, "digest", digest.hexdigest())


@dataclass(frozen=True, slots=True, eq=False)
class Volumetric3DRenderResult:
    """Backend-hidden immutable screenshot result from one retained scene/spec."""

    image: Any
    scene_geometry_digest: str
    render_spec_digest: str
    backend_name: str
    backend_version: str
    vtk_version: str
    visible_layer_count: int

    def __post_init__(self) -> None:
        source = np.asarray(self.image)
        if source.dtype != np.uint8 or source.ndim != 3 or source.shape[2] not in (3, 4):
            raise Volumetric3DVisualizationError(
                "image must be a uint8 array with shape (height, width, 3 or 4)"
            )
        if source.shape[0] <= 0 or source.shape[1] <= 0:
            raise Volumetric3DVisualizationError("image dimensions must be positive")
        frozen = np.frombuffer(
            np.ascontiguousarray(source).tobytes(order="C"),
            dtype=np.uint8,
        ).reshape(source.shape)
        frozen.setflags(write=False)
        scene_digest = str(self.scene_geometry_digest).strip()
        spec_digest = str(self.render_spec_digest).strip()
        backend_name = str(self.backend_name).strip()
        backend_version = str(self.backend_version).strip()
        vtk_version = str(self.vtk_version).strip()
        if not all((scene_digest, spec_digest, backend_name, backend_version, vtk_version)):
            raise Volumetric3DVisualizationError("render-result provenance must not be blank")
        visible = _positive_int(self.visible_layer_count, name="visible_layer_count")
        object.__setattr__(self, "image", frozen)
        object.__setattr__(self, "scene_geometry_digest", scene_digest)
        object.__setattr__(self, "render_spec_digest", spec_digest)
        object.__setattr__(self, "backend_name", backend_name)
        object.__setattr__(self, "backend_version", backend_version)
        object.__setattr__(self, "vtk_version", vtk_version)
        object.__setattr__(self, "visible_layer_count", visible)

    @property
    def width_px(self) -> int:
        return int(self.image.shape[1])

    @property
    def height_px(self) -> int:
        return int(self.image.shape[0])

    @property
    def channels(self) -> int:
        return int(self.image.shape[2])

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Volumetric3DRenderResult)
            and self.scene_geometry_digest == other.scene_geometry_digest
            and self.render_spec_digest == other.render_spec_digest
            and self.backend_name == other.backend_name
            and self.backend_version == other.backend_version
            and self.vtk_version == other.vtk_version
            and self.visible_layer_count == other.visible_layer_count
            and np.array_equal(self.image, other.image)
        )


def _load_backend() -> tuple[Any, Any]:
    try:
        import pyvista as pv
        import vtk
    except ImportError as exc:
        raise Volumetric3DBackendError(
            "advanced volumetric 3-D rendering requires the optional "
            "'volumetric3d' extra: pip install 'catalysis-workbench[volumetric3d]'"
        ) from exc
    return pv, vtk


def _field_cartesian_grid(scalar_field: ScalarField) -> NDArray[np.float64]:
    if not isinstance(scalar_field, ScalarField):
        raise TypeError("scalar_field must be a ScalarField")
    shape = scalar_field.grid_shape
    lattice = scalar_field.structure.lattice_angstrom
    assert lattice is not None
    indices = np.indices(shape, dtype=np.float64)
    fractional = np.empty((*shape, 3), dtype=np.float64)
    for axis in range(3):
        fractional[..., axis] = indices[axis] / shape[axis]
    return np.asarray(fractional @ lattice, dtype=np.float64)


def _structured_grid_from_scalar_field(scalar_field: ScalarField, pv: Any) -> Any:
    cartesian = _field_cartesian_grid(scalar_field)
    grid = pv.StructuredGrid()
    grid.points = np.column_stack(
        [cartesian[..., axis].ravel(order="F") for axis in range(3)]
    )
    grid.dimensions = scalar_field.grid_shape
    grid.point_data[_FIELD_SCALARS] = np.asarray(
        scalar_field.values,
        dtype=np.float64,
    ).ravel(order="F").copy()
    return grid


def _structured_grid_from_slice(scalar_slice: ScalarFieldSlice, pv: Any) -> Any:
    if not isinstance(scalar_slice, ScalarFieldSlice):
        raise TypeError("scalar_slice must be a ScalarFieldSlice")
    cartesian = slice_cartesian_coordinate_grid(scalar_slice)
    grid = pv.StructuredGrid()
    grid.points = np.column_stack(
        [cartesian[..., axis].ravel(order="F") for axis in range(3)]
    )
    grid.dimensions = (*scalar_slice.values.shape, 1)
    grid.point_data[_SLICE_SCALARS] = np.asarray(
        scalar_slice.values,
        dtype=np.float64,
    ).ravel(order="F").copy()
    return grid


def _apply_fractional_clip(
    dataset: Any,
    *,
    lattice_angstrom: NDArray[np.float64],
    bounds: tuple[tuple[float, float], tuple[float, float], tuple[float, float]] | None,
) -> Any:
    if bounds is None:
        return dataset
    lattice = np.asarray(lattice_angstrom, dtype=np.float64)
    inverse = np.linalg.inv(lattice)
    clipped = dataset
    for axis, (lower, upper) in enumerate(bounds):
        normal = np.asarray(inverse[:, axis], dtype=np.float64)
        normal /= np.linalg.norm(normal)
        lower_origin = np.asarray(lower * lattice[axis], dtype=np.float64)
        upper_origin = np.asarray(upper * lattice[axis], dtype=np.float64)
        clipped = clipped.clip(normal=normal, origin=lower_origin, invert=False)
        clipped = clipped.clip(normal=normal, origin=upper_origin, invert=True)
    return clipped


def _scalar_bar_title(layer: SliceLayerSpec) -> str:
    label = layer.label or layer.scalar_slice.field_kind
    return f"{label} ({layer.value_unit})"


def _render_isosurface_layer(
    plotter: Any,
    layer: IsosurfaceLayerSpec,
    spec: Volumetric3DRenderSpec,
    pv: Any,
) -> None:
    grid = _structured_grid_from_scalar_field(layer.scalar_field, pv)
    mesh = grid.contour(isosurfaces=[layer.threshold], scalars=_FIELD_SCALARS)
    if mesh.n_points == 0 or mesh.n_cells == 0:
        raise Volumetric3DVisualizationError(
            f"visible isosurface threshold {layer.threshold:g} does not intersect "
            f"field {layer.scalar_field.source_key!r}"
        )
    mesh = _apply_fractional_clip(
        mesh,
        lattice_angstrom=layer.lattice_angstrom,
        bounds=spec.clip_fractional_bounds,
    )
    if mesh.n_points == 0 or mesh.n_cells == 0:
        return
    plotter.add_mesh(
        mesh,
        color=layer.color,
        opacity=layer.opacity,
        lighting=spec.surface_lighting,
        smooth_shading=True,
        show_scalar_bar=False,
    )


def _render_slice_layer(
    plotter: Any,
    layer: SliceLayerSpec,
    spec: Volumetric3DRenderSpec,
    pv: Any,
) -> None:
    grid = _structured_grid_from_slice(layer.scalar_slice, pv)
    grid = _apply_fractional_clip(
        grid,
        lattice_angstrom=layer.lattice_angstrom,
        bounds=spec.clip_fractional_bounds,
    )
    if grid.n_points == 0 or grid.n_cells == 0:
        return
    values = np.asarray(layer.scalar_slice.values, dtype=np.float64)
    lower = float(np.min(values)) if layer.value_min is None else layer.value_min
    upper = float(np.max(values)) if layer.value_max is None else layer.value_max
    if lower == upper:
        delta = max(1.0, abs(lower)) * 1e-12
        lower -= delta
        upper += delta
    plotter.add_mesh(
        grid,
        scalars=_SLICE_SCALARS,
        cmap=layer.colormap,
        clim=(lower, upper),
        opacity=layer.opacity,
        lighting=spec.slice_lighting,
        show_scalar_bar=spec.show_scalar_bars,
        scalar_bar_args={"title": _scalar_bar_title(layer)},
    )


def _render_structure_overlay(
    plotter: Any,
    scene: VolumetricScene,
    spec: Volumetric3DRenderSpec,
    pv: Any,
) -> None:
    structure = scene.structure_scene
    if structure is None:
        return
    for atom in structure.atoms:
        sphere = pv.Sphere(
            radius=atom.style.radius_angstrom,
            center=tuple(float(value) for value in atom.position_angstrom),
            theta_resolution=spec.sphere_theta_resolution,
            phi_resolution=spec.sphere_phi_resolution,
        )
        plotter.add_mesh(
            sphere,
            color=atom.style.color,
            opacity=atom.style.alpha,
            lighting=spec.surface_lighting,
            smooth_shading=True,
            show_scalar_bar=False,
        )
    for bond in structure.bonds:
        line = pv.Line(
            tuple(float(value) for value in bond.first_position_angstrom),
            tuple(float(value) for value in bond.second_position_angstrom),
        )
        tube = line.tube(
            radius=(
                bond.style.linewidth * spec.bond_radius_per_linewidth_angstrom
            )
        )
        plotter.add_mesh(
            tube,
            color=bond.style.color,
            opacity=bond.style.alpha,
            lighting=spec.surface_lighting,
            smooth_shading=True,
            show_scalar_bar=False,
        )
    if structure.cell_style.visible:
        for first, second in structure.cell_edges_angstrom:
            line = pv.Line(
                tuple(float(value) for value in first),
                tuple(float(value) for value in second),
            )
            plotter.add_mesh(
                line,
                color=structure.cell_style.color,
                opacity=structure.cell_style.alpha,
                line_width=structure.cell_style.linewidth,
                render_lines_as_tubes=True,
                lighting=spec.surface_lighting,
                show_scalar_bar=False,
            )


def _normalize(vector: NDArray[np.float64]) -> NDArray[np.float64]:
    length = float(np.linalg.norm(vector))
    if not isfinite(length) or length <= 0.0:
        raise Volumetric3DVisualizationError("camera vector normalization failed")
    return np.asarray(vector / length, dtype=np.float64)


def _rotate_about_axis(
    vector: NDArray[np.float64],
    axis: NDArray[np.float64],
    angle_degrees: float,
) -> NDArray[np.float64]:
    theta = radians(angle_degrees)
    unit_axis = _normalize(axis)
    return np.asarray(
        vector * cos(theta)
        + np.cross(unit_axis, vector) * sin(theta)
        + unit_axis * np.dot(unit_axis, vector) * (1.0 - cos(theta)),
        dtype=np.float64,
    )


def _apply_camera(
    plotter: Any,
    camera_spec: StructureCameraSpec,
    render_spec: Volumetric3DRenderSpec,
) -> None:
    bounds = np.asarray(plotter.bounds, dtype=np.float64)
    if bounds.shape != (6,) or not np.isfinite(bounds).all():
        raise Volumetric3DVisualizationError("visible scene bounds are unavailable")
    minimum = np.asarray((bounds[0], bounds[2], bounds[4]), dtype=np.float64)
    maximum = np.asarray((bounds[1], bounds[3], bounds[5]), dtype=np.float64)
    center = (minimum + maximum) / 2.0
    span = maximum - minimum
    diagonal = float(np.linalg.norm(span))
    extent = diagonal if diagonal > 1e-12 else 1.0

    azimuth = radians(camera_spec.azimuth_degrees)
    elevation = radians(camera_spec.elevation_degrees)
    outward = _normalize(
        np.asarray(
            (
                cos(elevation) * cos(azimuth),
                cos(elevation) * sin(azimuth),
                sin(elevation),
            ),
            dtype=np.float64,
        )
    )
    position = center + outward * extent * render_spec.camera_distance_factor
    viewing_direction = _normalize(center - position)
    reference_up = np.asarray((0.0, 0.0, 1.0), dtype=np.float64)
    projected_up = reference_up - viewing_direction * np.dot(reference_up, viewing_direction)
    if np.linalg.norm(projected_up) <= 1e-8:
        reference_up = np.asarray((0.0, 1.0, 0.0), dtype=np.float64)
        projected_up = reference_up - viewing_direction * np.dot(
            reference_up,
            viewing_direction,
        )
    up = _normalize(projected_up)
    up = _normalize(
        _rotate_about_axis(up, viewing_direction, camera_spec.roll_degrees)
    )

    camera = plotter.camera
    camera.position = tuple(float(value) for value in position)
    camera.focal_point = tuple(float(value) for value in center)
    camera.up = tuple(float(value) for value in up)
    if camera_spec.projection == "orthographic":
        camera.enable_parallel_projection()
        camera.parallel_scale = (
            max(float(np.max(span)), 1.0)
            * render_spec.orthographic_scale_factor
        )
    else:
        camera.disable_parallel_projection()
        camera.view_angle = render_spec.perspective_view_angle_degrees
    camera.reset_clipping_range()


def _snapshot_scene(scene: VolumetricScene) -> tuple[tuple[str, bytes], ...]:
    snapshots: list[tuple[str, bytes]] = []
    for layer in scene.layers:
        if isinstance(layer, IsosurfaceLayerSpec):
            snapshots.append(
                (
                    layer.scalar_field.digest,
                    np.asarray(layer.scalar_field.values).tobytes(order="C"),
                )
            )
        else:
            snapshots.append(
                (
                    layer.scalar_slice.digest,
                    np.asarray(layer.scalar_slice.values).tobytes(order="C"),
                )
            )
    return tuple(snapshots)


def _verify_scene_unchanged(
    scene: VolumetricScene,
    before_digest: str,
    snapshots: tuple[tuple[str, bytes], ...],
) -> None:
    if scene.geometry_digest != before_digest:
        raise RuntimeError("3-D rendering mutated retained volumetric scene state")
    after = _snapshot_scene(scene)
    if after != snapshots:
        raise RuntimeError("3-D rendering mutated retained scalar-field arrays")


def _render(
    scene: VolumetricScene,
    spec: Volumetric3DRenderSpec,
    *,
    output_path: Path | None = None,
) -> Volumetric3DRenderResult:
    if not isinstance(scene, VolumetricScene):
        raise TypeError("scene must be a VolumetricScene")
    if not isinstance(spec, Volumetric3DRenderSpec):
        raise TypeError("spec must be a Volumetric3DRenderSpec")
    pv, vtk = _load_backend()
    before_digest = scene.geometry_digest
    snapshots = _snapshot_scene(scene)
    visible_layers = tuple(layer for layer in scene.layers if layer.visible)
    if not visible_layers:
        raise Volumetric3DVisualizationError("scene has no visible volumetric layers")

    plotter = pv.Plotter(off_screen=True, window_size=spec.window_size_px)
    rendered_layer_count = 0
    try:
        plotter.set_background(scene.background)
        if spec.anti_aliasing != "none":
            plotter.enable_anti_aliasing(spec.anti_aliasing)
        actor_count_before = len(plotter.actors)
        for layer in visible_layers:
            before = len(plotter.actors)
            if isinstance(layer, IsosurfaceLayerSpec):
                _render_isosurface_layer(plotter, layer, spec, pv)
            elif isinstance(layer, SliceLayerSpec):
                _render_slice_layer(plotter, layer, spec, pv)
            else:  # pragma: no cover - VolumetricScene already validates layer types.
                raise TypeError("unsupported volumetric layer type")
            if len(plotter.actors) > before:
                rendered_layer_count += 1
        if rendered_layer_count == 0:
            raise Volumetric3DVisualizationError(
                "explicit clipping removed all visible volumetric geometry"
            )
        _render_structure_overlay(plotter, scene, spec, pv)
        if len(plotter.actors) <= actor_count_before:
            raise Volumetric3DVisualizationError("no renderable scene actors were created")
        _apply_camera(plotter, scene.camera, spec)
        filename = None if output_path is None else str(output_path)
        image = plotter.screenshot(
            filename=filename,
            return_img=True,
            window_size=spec.window_size_px,
            transparent_background=spec.transparent_background,
        )
        if image is None:
            raise Volumetric3DVisualizationError("backend did not return a screenshot")
    finally:
        plotter.close()

    _verify_scene_unchanged(scene, before_digest, snapshots)
    return Volumetric3DRenderResult(
        image=np.asarray(image, dtype=np.uint8),
        scene_geometry_digest=scene.geometry_digest,
        render_spec_digest=spec.digest,
        backend_name="pyvista",
        backend_version=str(pv.__version__),
        vtk_version=str(vtk.vtkVersion.GetVTKVersion()),
        visible_layer_count=rendered_layer_count,
    )


def render_volumetric_scene_3d(
    scene: VolumetricScene,
    spec: Volumetric3DRenderSpec | None = None,
) -> Volumetric3DRenderResult:
    """Render one retained volumetric scene to an immutable off-screen image."""
    resolved = Volumetric3DRenderSpec() if spec is None else spec
    return _render(scene, resolved)


def export_volumetric_scene_3d(
    scene: VolumetricScene,
    path: str | Path,
    spec: Volumetric3DRenderSpec | None = None,
) -> Path:
    """Render and export one retained volumetric scene as a PNG screenshot."""
    resolved = Volumetric3DRenderSpec() if spec is None else spec
    if not isinstance(resolved, Volumetric3DRenderSpec):
        raise TypeError("spec must be a Volumetric3DRenderSpec")
    destination = Path(path)
    if destination.suffix.casefold() != ".png":
        raise Volumetric3DVisualizationError("3-D static export currently supports PNG only")
    destination.parent.mkdir(parents=True, exist_ok=True)
    _render(scene, resolved, output_path=destination)
    if not destination.is_file() or destination.stat().st_size <= 0:
        raise Volumetric3DVisualizationError("backend did not create the requested PNG")
    return destination


__all__ = [
    "AntiAliasingMode",
    "Volumetric3DBackendError",
    "Volumetric3DRenderResult",
    "Volumetric3DRenderSpec",
    "Volumetric3DVisualizationError",
    "export_volumetric_scene_3d",
    "render_volumetric_scene_3d",
]
