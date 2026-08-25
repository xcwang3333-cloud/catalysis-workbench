"""Renderer-neutral volumetric layer and scene state for v0.7."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from math import isfinite
from types import MappingProxyType
from typing import Any

import numpy as np

from ..computation.scalar_field import ScalarField, ScalarFieldSlice
from ..computation.structure_scene import StructureCameraSpec, StructureScene


class VolumetricSceneError(ValueError):
    """Raised when renderer-neutral volumetric scene state is invalid."""


def _nonblank(
    value: object,
    *,
    name: str,
    optional: bool = False,
) -> str | None:
    if value is None and optional:
        return None
    text = str(value).strip()
    if not text:
        raise VolumetricSceneError(f"{name} must not be blank")
    return text


def _opacity(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError("opacity must be a finite float") from exc
    if not isfinite(number) or not 0.0 <= number <= 1.0:
        raise VolumetricSceneError(
            "opacity must be finite and between 0 and 1"
        )
    return number


def _finite(value: object, *, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a finite float") from exc
    if not isfinite(number):
        raise VolumetricSceneError(f"{name} must be finite")
    return number


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _freeze_value(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, np.ndarray):
        array = np.array(value, copy=True)
        array.setflags(write=False)
        return array
    return deepcopy(value)


def _freeze_metadata(metadata: Mapping[str, Any] | None) -> Mapping[str, Any]:
    source = {} if metadata is None else dict(metadata)
    return MappingProxyType(
        {str(key): _freeze_value(value) for key, value in source.items()}
    )


def _digest_text(digest: Any, value: str | None) -> None:
    if value is None:
        digest.update(b"\xff")
        return
    encoded = value.encode("utf-8")
    digest.update(len(encoded).to_bytes(8, "little", signed=False))
    digest.update(encoded)


@dataclass(frozen=True, slots=True, eq=False)
class IsosurfaceLayerSpec:
    """One explicit scalar-field threshold with presentation-only style."""

    scalar_field: ScalarField
    threshold: float
    color: str = "#D95F02"
    opacity: float = 0.55
    visible: bool = True
    label: str | None = None
    geometry_digest: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.scalar_field, ScalarField):
            raise TypeError("scalar_field must be a ScalarField")
        threshold = _finite(self.threshold, name="threshold")
        color = str(_nonblank(self.color, name="color"))
        opacity = _opacity(self.opacity)
        label = _nonblank(self.label, name="label", optional=True)

        digest = hashlib.sha256()
        digest.update(
            b"CatalysisWorkbench.IsosurfaceLayerSpec.geometry.v1\0"
        )
        _digest_text(digest, self.scalar_field.digest)
        digest.update(np.float64(threshold).tobytes())

        object.__setattr__(self, "threshold", threshold)
        object.__setattr__(self, "color", color)
        object.__setattr__(self, "opacity", opacity)
        object.__setattr__(self, "visible", bool(self.visible))
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "geometry_digest", digest.hexdigest())

    @property
    def value_unit(self) -> str:
        return self.scalar_field.value_unit

    @property
    def source_field_digest(self) -> str:
        return self.scalar_field.digest

    @property
    def structure_digest(self) -> str:
        return self.scalar_field.structure.digest

    @property
    def grid_shape(self) -> tuple[int, int, int]:
        return self.scalar_field.grid_shape

    @property
    def registration_id(self) -> str | None:
        return self.scalar_field.registration_id

    @property
    def lattice_angstrom(self) -> np.ndarray:
        lattice = self.scalar_field.structure.lattice_angstrom
        assert lattice is not None
        return lattice

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, IsosurfaceLayerSpec)
            and self.scalar_field == other.scalar_field
            and self.threshold == other.threshold
            and self.color == other.color
            and self.opacity == other.opacity
            and self.visible == other.visible
            and self.label == other.label
        )


@dataclass(frozen=True, slots=True, eq=False)
class SliceLayerSpec:
    """One exact retained scalar-field slice with presentation-only style."""

    scalar_slice: ScalarFieldSlice
    colormap: str = "viridis"
    opacity: float = 1.0
    visible: bool = True
    value_min: float | None = None
    value_max: float | None = None
    label: str | None = None
    geometry_digest: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.scalar_slice, ScalarFieldSlice):
            raise TypeError("scalar_slice must be a ScalarFieldSlice")
        colormap = str(_nonblank(self.colormap, name="colormap"))
        opacity = _opacity(self.opacity)
        value_min = (
            None
            if self.value_min is None
            else _finite(self.value_min, name="value_min")
        )
        value_max = (
            None
            if self.value_max is None
            else _finite(self.value_max, name="value_max")
        )
        if (
            value_min is not None
            and value_max is not None
            and value_min >= value_max
        ):
            raise VolumetricSceneError(
                "value_min must be less than value_max"
            )
        label = _nonblank(self.label, name="label", optional=True)

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.SliceLayerSpec.geometry.v1\0")
        _digest_text(digest, self.scalar_slice.digest)

        object.__setattr__(self, "colormap", colormap)
        object.__setattr__(self, "opacity", opacity)
        object.__setattr__(self, "visible", bool(self.visible))
        object.__setattr__(self, "value_min", value_min)
        object.__setattr__(self, "value_max", value_max)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "geometry_digest", digest.hexdigest())

    @property
    def value_unit(self) -> str:
        return self.scalar_slice.value_unit

    @property
    def source_field_digest(self) -> str:
        return self.scalar_slice.source_field_digest

    @property
    def structure_digest(self) -> str:
        return self.scalar_slice.structure_digest

    @property
    def grid_shape(self) -> tuple[int, int, int]:
        return self.scalar_slice.grid_shape

    @property
    def registration_id(self) -> str | None:
        return self.scalar_slice.registration_id

    @property
    def lattice_angstrom(self) -> np.ndarray:
        return self.scalar_slice.lattice_angstrom

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, SliceLayerSpec)
            and self.scalar_slice == other.scalar_slice
            and self.colormap == other.colormap
            and self.opacity == other.opacity
            and self.visible == other.visible
            and self.value_min == other.value_min
            and self.value_max == other.value_max
            and self.label == other.label
        )


VolumetricLayerSpec = IsosurfaceLayerSpec | SliceLayerSpec


def _layer_geometry(
    layer: VolumetricLayerSpec,
) -> tuple[str, str, tuple[int, int, int], str | None, np.ndarray]:
    if not isinstance(layer, (IsosurfaceLayerSpec, SliceLayerSpec)):
        raise TypeError(
            "layers must contain only IsosurfaceLayerSpec or SliceLayerSpec"
        )
    return (
        layer.source_field_digest,
        layer.structure_digest,
        layer.grid_shape,
        layer.registration_id,
        np.asarray(layer.lattice_angstrom, dtype=np.float64),
    )


@dataclass(frozen=True, slots=True, eq=False)
class VolumetricScene:
    """Ordered renderer-neutral volumetric layers in one exact physical frame."""

    layers: Sequence[VolumetricLayerSpec]
    structure_scene: StructureScene | None = None
    camera: StructureCameraSpec = StructureCameraSpec()
    background: str = "#FFFFFF"
    metadata: Mapping[str, Any] = field(default_factory=dict)
    geometry_digest: str = field(init=False)

    def __post_init__(self) -> None:
        layers = tuple(self.layers)
        if not layers:
            raise VolumetricSceneError(
                "scene requires at least one volumetric layer"
            )
        (
            first_source,
            first_structure,
            first_shape,
            first_registration,
            first_lattice,
        ) = _layer_geometry(layers[0])
        source_digests = {first_source}

        for layer in layers[1:]:
            source, structure, shape, registration, lattice = _layer_geometry(
                layer
            )
            source_digests.add(source)
            if structure != first_structure:
                raise VolumetricSceneError(
                    "all layers require the same retained structure_digest"
                )
            if shape != first_shape:
                raise VolumetricSceneError(
                    "all layers require the same retained grid_shape"
                )
            if registration != first_registration:
                raise VolumetricSceneError(
                    "all layers require identical registration_id semantics"
                )
            if not np.array_equal(lattice, first_lattice):
                raise VolumetricSceneError(
                    "all layers require the same exact retained lattice; "
                    "no alignment or transformation is performed"
                )

        if len(source_digests) > 1 and first_registration is None:
            raise VolumetricSceneError(
                "multiple source fields require an explicit shared registration_id"
            )

        if self.structure_scene is not None:
            if not isinstance(self.structure_scene, StructureScene):
                raise TypeError(
                    "structure_scene must be a StructureScene or None"
                )
            if self.structure_scene.structure_digest != first_structure:
                raise VolumetricSceneError(
                    "structure_scene.structure_digest must match volumetric layers"
                )
        if not isinstance(self.camera, StructureCameraSpec):
            raise TypeError("camera must be a StructureCameraSpec")

        background = str(_nonblank(self.background, name="background"))
        metadata = _freeze_metadata(self.metadata)
        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.VolumetricScene.geometry.v1\0")
        _digest_text(digest, first_structure)
        _digest_text(digest, first_registration)
        for value in first_shape:
            digest.update(int(value).to_bytes(8, "little", signed=False))
        digest.update(first_lattice.tobytes(order="C"))
        for layer in layers:
            _digest_text(digest, layer.geometry_digest)

        object.__setattr__(self, "layers", layers)
        object.__setattr__(self, "background", background)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "geometry_digest", digest.hexdigest())

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, VolumetricScene)
            and self.layers == other.layers
            and self.structure_scene == other.structure_scene
            and self.camera == other.camera
            and self.background == other.background
        )


__all__ = [
    "IsosurfaceLayerSpec",
    "SliceLayerSpec",
    "VolumetricLayerSpec",
    "VolumetricScene",
    "VolumetricSceneError",
]
