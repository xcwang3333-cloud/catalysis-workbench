"""Renderer-neutral immutable scene state for static atomistic visualization."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from math import isfinite
from types import MappingProxyType
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from .geometry import SiteImage
from .structure import AtomicStructure

Projection = Literal["orthographic", "perspective"]


class StructureSceneError(ValueError):
    """Raised when renderer-neutral structure scene state is invalid."""


def _positive(value: float, *, name: str) -> float:
    number = float(value)
    if not isfinite(number) or number <= 0.0:
        raise StructureSceneError(f"{name} must be finite and positive")
    return number


def _alpha(value: float) -> float:
    number = float(value)
    if not isfinite(number) or not 0.0 <= number <= 1.0:
        raise StructureSceneError("alpha must be finite and between 0 and 1")
    return number


def _color(value: str, *, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise StructureSceneError(f"{name} must not be blank")
    return text


def _frozen_vector(values: Sequence[float], *, name: str) -> NDArray[np.float64]:
    source = np.asarray(values)
    if np.iscomplexobj(source):
        raise StructureSceneError(f"{name} must contain real values")
    array = np.asarray(values, dtype=np.float64)
    if array.shape != (3,) or not np.isfinite(array).all():
        raise StructureSceneError(f"{name} must be a finite real 3-vector")
    frozen = np.frombuffer(np.ascontiguousarray(array).tobytes(), dtype=np.float64)
    frozen.setflags(write=False)
    return frozen


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _freeze_value(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, np.ndarray):
        frozen = np.array(value, copy=True)
        frozen.setflags(write=False)
        return frozen
    return deepcopy(value)


def _freeze_metadata(metadata: Mapping[str, Any] | None) -> Mapping[str, Any]:
    source = {} if metadata is None else dict(metadata)
    return MappingProxyType(
        {str(key): _freeze_value(value) for key, value in source.items()}
    )


# Presentation-only defaults. They are never used for bonding/coordination analysis.
_ELEMENT_COLORS: Mapping[str, str] = MappingProxyType(
    {
        "H": "#F2F2F2",
        "C": "#4A4A4A",
        "N": "#3050F8",
        "O": "#FF3030",
        "F": "#90E050",
        "P": "#FF8000",
        "S": "#FFD123",
        "Cl": "#1FF01F",
        "Fe": "#E06633",
        "Co": "#F090A0",
        "Ni": "#50D050",
        "Cu": "#C88033",
        "Zn": "#7D80B0",
        "Al": "#BFA6A6",
        "Pb": "#575961",
        "Pt": "#D0D0E0",
    }
)
_ELEMENT_RADII: Mapping[str, float] = MappingProxyType(
    {
        "H": 0.25,
        "C": 0.40,
        "N": 0.38,
        "O": 0.36,
        "F": 0.34,
        "P": 0.48,
        "S": 0.47,
        "Cl": 0.45,
        "Fe": 0.48,
        "Co": 0.47,
        "Ni": 0.46,
        "Cu": 0.46,
        "Zn": 0.47,
        "Al": 0.50,
        "Pb": 0.55,
        "Pt": 0.48,
    }
)
_FALLBACK_COLOR = "#9A9A9A"
_FALLBACK_RADIUS = 0.42


def default_element_color(element: str) -> str:
    """Return deterministic presentation-only element color."""
    return _ELEMENT_COLORS.get(str(element).strip(), _FALLBACK_COLOR)


def default_element_radius_angstrom(element: str) -> float:
    """Return deterministic presentation-only radius, never a bond criterion."""
    return float(_ELEMENT_RADII.get(str(element).strip(), _FALLBACK_RADIUS))


@dataclass(frozen=True, slots=True)
class StructureAtomStyle:
    color: str
    radius_angstrom: float
    alpha: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "color", _color(self.color, name="atom color"))
        object.__setattr__(
            self,
            "radius_angstrom",
            _positive(self.radius_angstrom, name="radius_angstrom"),
        )
        object.__setattr__(self, "alpha", _alpha(self.alpha))


@dataclass(frozen=True, slots=True)
class StructureBondStyle:
    color: str = "#707070"
    linewidth: float = 1.5
    alpha: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "color", _color(self.color, name="bond color"))
        object.__setattr__(
            self,
            "linewidth",
            _positive(self.linewidth, name="linewidth"),
        )
        object.__setattr__(self, "alpha", _alpha(self.alpha))


@dataclass(frozen=True, slots=True)
class StructureCellStyle:
    visible: bool = True
    color: str = "#555555"
    linewidth: float = 0.8
    alpha: float = 0.8

    def __post_init__(self) -> None:
        object.__setattr__(self, "visible", bool(self.visible))
        object.__setattr__(self, "color", _color(self.color, name="cell color"))
        object.__setattr__(
            self,
            "linewidth",
            _positive(self.linewidth, name="linewidth"),
        )
        object.__setattr__(self, "alpha", _alpha(self.alpha))


@dataclass(frozen=True, slots=True)
class StructureCameraSpec:
    projection: Projection = "orthographic"
    elevation_degrees: float = 20.0
    azimuth_degrees: float = -60.0
    roll_degrees: float = 0.0

    def __post_init__(self) -> None:
        projection = str(self.projection).strip().casefold()
        if projection not in {"orthographic", "perspective"}:
            raise StructureSceneError("projection must be orthographic or perspective")
        values = (
            float(self.elevation_degrees),
            float(self.azimuth_degrees),
            float(self.roll_degrees),
        )
        if not all(isfinite(value) for value in values):
            raise StructureSceneError("camera angles must be finite")
        object.__setattr__(self, "projection", projection)
        object.__setattr__(self, "elevation_degrees", values[0])
        object.__setattr__(self, "azimuth_degrees", values[1])
        object.__setattr__(self, "roll_degrees", values[2])


@dataclass(frozen=True, slots=True)
class StructureAtomVisual:
    site: SiteImage
    element: str
    position_angstrom: Sequence[float]
    style: StructureAtomStyle
    label: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.site, SiteImage):
            raise TypeError("site must be a SiteImage")
        element = str(self.element).strip()
        if not element:
            raise StructureSceneError("element must not be blank")
        if not isinstance(self.style, StructureAtomStyle):
            raise TypeError("style must be a StructureAtomStyle")
        label = None if self.label is None else str(self.label).strip() or None
        object.__setattr__(self, "element", element)
        object.__setattr__(
            self,
            "position_angstrom",
            _frozen_vector(self.position_angstrom, name="position_angstrom"),
        )
        object.__setattr__(self, "label", label)


@dataclass(frozen=True, slots=True)
class StructureBondVisual:
    first: SiteImage
    second: SiteImage
    first_position_angstrom: Sequence[float]
    second_position_angstrom: Sequence[float]
    style: StructureBondStyle = StructureBondStyle()

    def __post_init__(self) -> None:
        if not isinstance(self.first, SiteImage) or not isinstance(self.second, SiteImage):
            raise TypeError("bond endpoints must be SiteImage instances")
        if self.first == self.second:
            raise StructureSceneError("bond endpoints must be distinct site/image identities")
        if not isinstance(self.style, StructureBondStyle):
            raise TypeError("style must be a StructureBondStyle")
        first = _frozen_vector(
            self.first_position_angstrom,
            name="first_position_angstrom",
        )
        second = _frozen_vector(
            self.second_position_angstrom,
            name="second_position_angstrom",
        )
        if np.allclose(first, second, rtol=0.0, atol=1e-15):
            raise StructureSceneError("bond endpoints must not occupy the same position")
        object.__setattr__(self, "first_position_angstrom", first)
        object.__setattr__(self, "second_position_angstrom", second)


@dataclass(frozen=True, slots=True)
class StructureScene:
    """Immutable renderer-neutral scene with already-resolved visual geometry."""

    structure_digest: str
    atoms: tuple[StructureAtomVisual, ...]
    bonds: tuple[StructureBondVisual, ...] = ()
    cell_edges_angstrom: tuple[tuple[Sequence[float], Sequence[float]], ...] = ()
    cell_style: StructureCellStyle = StructureCellStyle()
    camera: StructureCameraSpec = StructureCameraSpec()
    background: str = "#FFFFFF"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        digest = str(self.structure_digest).strip()
        if not digest:
            raise StructureSceneError("structure_digest must not be blank")
        atoms = tuple(self.atoms)
        bonds = tuple(self.bonds)
        if not atoms:
            raise StructureSceneError("scene requires at least one atom")
        if not all(isinstance(atom, StructureAtomVisual) for atom in atoms):
            raise TypeError("atoms must contain StructureAtomVisual instances")
        if not all(isinstance(bond, StructureBondVisual) for bond in bonds):
            raise TypeError("bonds must contain StructureBondVisual instances")
        identities = [atom.site for atom in atoms]
        if len(identities) != len(set(identities)):
            raise StructureSceneError("scene atom SiteImage identities must be unique")
        atom_set = set(identities)
        if any(bond.first not in atom_set or bond.second not in atom_set for bond in bonds):
            raise StructureSceneError("every bond endpoint must exist in scene atoms")
        edges = tuple(
            (
                _frozen_vector(first, name="cell edge start"),
                _frozen_vector(second, name="cell edge end"),
            )
            for first, second in self.cell_edges_angstrom
        )
        if edges and len(edges) != 12:
            raise StructureSceneError(
                "periodic cell geometry must contain exactly 12 edges"
            )
        if not isinstance(self.cell_style, StructureCellStyle):
            raise TypeError("cell_style must be a StructureCellStyle")
        if not isinstance(self.camera, StructureCameraSpec):
            raise TypeError("camera must be a StructureCameraSpec")
        object.__setattr__(self, "structure_digest", digest)
        object.__setattr__(self, "atoms", atoms)
        object.__setattr__(self, "bonds", bonds)
        object.__setattr__(self, "cell_edges_angstrom", edges)
        object.__setattr__(
            self,
            "background",
            _color(self.background, name="background"),
        )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class StructureBondSpec:
    """Caller-supplied explicit visual bond; no chemical inference is performed."""

    first: SiteImage
    second: SiteImage
    style: StructureBondStyle = StructureBondStyle()

    def __post_init__(self) -> None:
        if not isinstance(self.first, SiteImage) or not isinstance(self.second, SiteImage):
            raise TypeError("bond endpoints must be SiteImage instances")
        if not isinstance(self.style, StructureBondStyle):
            raise TypeError("style must be a StructureBondStyle")


def _site_index(structure: AtomicStructure, key: str) -> int:
    try:
        return structure.site_keys.index(key)
    except ValueError as exc:
        raise StructureSceneError(f"unknown site key: {key}") from exc


def _position(structure: AtomicStructure, site: SiteImage) -> NDArray[np.float64]:
    index = _site_index(structure, site.site_key)
    offsets = site.image.as_tuple()
    for axis, (offset, enabled) in enumerate(
        zip(offsets, structure.pbc, strict=True)
    ):
        if offset and not enabled:
            raise StructureSceneError(
                f"periodic image offset on nonperiodic axis {axis} is not allowed"
            )
    position = np.asarray(structure.cartesian_coordinates[index], dtype=np.float64)
    if any(offsets):
        if structure.lattice_angstrom is None:
            raise StructureSceneError("nonzero periodic images require a lattice")
        position = position + np.asarray(offsets, dtype=np.float64) @ np.asarray(
            structure.lattice_angstrom,
            dtype=np.float64,
        )
    return position


def _cell_edges(
    structure: AtomicStructure,
) -> tuple[tuple[NDArray[np.float64], NDArray[np.float64]], ...]:
    if structure.lattice_angstrom is None:
        return ()
    lattice = np.asarray(structure.lattice_angstrom, dtype=np.float64)
    corners = {
        bits: np.asarray(bits, dtype=np.float64) @ lattice
        for bits in product_bits()
    }
    edges: list[tuple[NDArray[np.float64], NDArray[np.float64]]] = []
    for bits, first in corners.items():
        for axis in range(3):
            if bits[axis] == 0:
                neighbor = list(bits)
                neighbor[axis] = 1
                edges.append((first, corners[tuple(neighbor)]))
    return tuple(edges)


def product_bits() -> tuple[tuple[int, int, int], ...]:
    """Return deterministic unit-cell corner bit tuples."""
    return tuple(
        (a, b, c)
        for a in (0, 1)
        for b in (0, 1)
        for c in (0, 1)
    )


def build_structure_scene(
    structure: AtomicStructure,
    *,
    atom_images: Sequence[SiteImage] | None = None,
    bonds: Sequence[StructureBondSpec] = (),
    element_styles: Mapping[str, StructureAtomStyle] | None = None,
    site_styles: Mapping[str, StructureAtomStyle] | None = None,
    labels: Mapping[str, str] | None = None,
    cell_style: StructureCellStyle | None = None,
    camera: StructureCameraSpec | None = None,
    background: str = "#FFFFFF",
    metadata: Mapping[str, Any] | None = None,
) -> StructureScene:
    """Resolve explicit visual instructions into an immutable renderer-neutral scene."""
    if not isinstance(structure, AtomicStructure):
        raise TypeError("structure must be an AtomicStructure")
    if atom_images is None:
        atom_images = tuple(SiteImage(key) for key in structure.site_keys)
    retained_images = tuple(atom_images)
    if not retained_images:
        raise StructureSceneError("atom_images must contain at least one SiteImage")
    if not all(isinstance(site, SiteImage) for site in retained_images):
        raise TypeError("atom_images must contain only SiteImage instances")
    if len(retained_images) != len(set(retained_images)):
        raise StructureSceneError(
            "atom_images must contain unique SiteImage identities"
        )

    resolved_element_styles = {} if element_styles is None else dict(element_styles)
    resolved_site_styles = {} if site_styles is None else dict(site_styles)
    resolved_labels = {} if labels is None else dict(labels)
    atoms: list[StructureAtomVisual] = []
    for site in retained_images:
        index = _site_index(structure, site.site_key)
        element = structure.elements[index]
        style = resolved_site_styles.get(site.site_key)
        if style is None:
            style = resolved_element_styles.get(element)
        if style is None:
            style = StructureAtomStyle(
                color=default_element_color(element),
                radius_angstrom=default_element_radius_angstrom(element),
            )
        if not isinstance(style, StructureAtomStyle):
            raise TypeError("atom style overrides must be StructureAtomStyle instances")
        atoms.append(
            StructureAtomVisual(
                site=site,
                element=element,
                position_angstrom=_position(structure, site),
                style=style,
                label=resolved_labels.get(site.site_key),
            )
        )

    atom_set = set(retained_images)
    resolved_bonds: list[StructureBondVisual] = []
    for bond in bonds:
        if not isinstance(bond, StructureBondSpec):
            raise TypeError("bonds must contain only StructureBondSpec instances")
        if bond.first not in atom_set or bond.second not in atom_set:
            raise StructureSceneError(
                "bond endpoints must be explicitly present in atom_images"
            )
        resolved_bonds.append(
            StructureBondVisual(
                first=bond.first,
                second=bond.second,
                first_position_angstrom=_position(structure, bond.first),
                second_position_angstrom=_position(structure, bond.second),
                style=bond.style,
            )
        )

    resolved_cell_style = StructureCellStyle() if cell_style is None else cell_style
    resolved_camera = StructureCameraSpec() if camera is None else camera
    if not isinstance(resolved_cell_style, StructureCellStyle):
        raise TypeError("cell_style must be a StructureCellStyle")
    if not isinstance(resolved_camera, StructureCameraSpec):
        raise TypeError("camera must be a StructureCameraSpec")
    return StructureScene(
        structure_digest=structure.digest,
        atoms=tuple(atoms),
        bonds=tuple(resolved_bonds),
        cell_edges_angstrom=_cell_edges(structure),
        cell_style=resolved_cell_style,
        camera=resolved_camera,
        background=background,
        metadata={} if metadata is None else metadata,
    )


__all__ = [
    "Projection",
    "StructureAtomStyle",
    "StructureAtomVisual",
    "StructureBondSpec",
    "StructureBondStyle",
    "StructureBondVisual",
    "StructureCameraSpec",
    "StructureCellStyle",
    "StructureScene",
    "StructureSceneError",
    "build_structure_scene",
    "default_element_color",
    "default_element_radius_angstrom",
]
