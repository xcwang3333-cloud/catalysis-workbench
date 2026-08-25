"""Explicit periodic-image geometry, coordination, and structure comparison."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import acos, degrees, isfinite, sqrt
from typing import Sequence

import numpy as np
from numpy.typing import NDArray

from .structure import AtomicStructure


class GeometryError(ValueError):
    """Raised when an explicit geometry request is invalid."""


def _integer(value: int, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{name} must be an integer")
    return int(value)


def _nonnegative_int(value: int, *, name: str) -> int:
    result = _integer(value, name=name)
    if result < 0:
        raise GeometryError(f"{name} must be non-negative")
    return result


def _frozen_vector(values: Sequence[float], *, name: str) -> NDArray[np.float64]:
    array = np.asarray(values)
    if np.iscomplexobj(array):
        raise GeometryError(f"{name} must contain real values")
    result = np.asarray(values, dtype=np.float64)
    if result.shape != (3,) or not np.isfinite(result).all():
        raise GeometryError(f"{name} must be a finite real 3-vector")
    frozen = np.frombuffer(np.ascontiguousarray(result).tobytes(), dtype=np.float64)
    frozen.setflags(write=False)
    return frozen


def _frozen_matrix(
    values: Sequence[Sequence[float]],
    *,
    name: str,
) -> NDArray[np.float64]:
    array = np.asarray(values)
    if np.iscomplexobj(array):
        raise GeometryError(f"{name} must contain real values")
    result = np.asarray(values, dtype=np.float64)
    if result.ndim != 2 or result.shape[1:] != (3,) or not np.isfinite(result).all():
        raise GeometryError(f"{name} must be a finite real N x 3 matrix")
    frozen = np.frombuffer(np.ascontiguousarray(result).tobytes(), dtype=np.float64).reshape(
        result.shape
    )
    frozen.setflags(write=False)
    return frozen


def _frozen_1d(values: Sequence[float], *, name: str) -> NDArray[np.float64]:
    array = np.asarray(values)
    if np.iscomplexobj(array):
        raise GeometryError(f"{name} must contain real values")
    result = np.asarray(values, dtype=np.float64)
    if result.ndim != 1 or not np.isfinite(result).all():
        raise GeometryError(f"{name} must be a finite real one-dimensional array")
    frozen = np.frombuffer(np.ascontiguousarray(result).tobytes(), dtype=np.float64)
    frozen.setflags(write=False)
    return frozen


@dataclass(frozen=True, slots=True, order=True)
class PeriodicImage:
    """Exact integer lattice-image offset along retained a/b/c row vectors."""

    a: int = 0
    b: int = 0
    c: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "a", _integer(self.a, name="a"))
        object.__setattr__(self, "b", _integer(self.b, name="b"))
        object.__setattr__(self, "c", _integer(self.c, name="c"))

    def as_tuple(self) -> tuple[int, int, int]:
        """Return the exact lattice-translation indices."""
        return self.a, self.b, self.c


_ZERO_IMAGE = PeriodicImage()


@dataclass(frozen=True, slots=True)
class SiteImage:
    """One stable site key at one exact periodic image."""

    site_key: str
    image: PeriodicImage = _ZERO_IMAGE

    def __post_init__(self) -> None:
        key = str(self.site_key).strip()
        if not key:
            raise GeometryError("site_key must not be blank")
        if not isinstance(self.image, PeriodicImage):
            raise TypeError("image must be a PeriodicImage")
        object.__setattr__(self, "site_key", key)


@dataclass(frozen=True, slots=True, eq=False)
class SiteDistanceResult:
    """One exact caller-selected site/image displacement and distance."""

    first: SiteImage
    second: SiteImage
    displacement_angstrom: Sequence[float]
    distance_angstrom: float

    def __post_init__(self) -> None:
        if not isinstance(self.first, SiteImage) or not isinstance(self.second, SiteImage):
            raise TypeError("first and second must be SiteImage instances")
        vector = _frozen_vector(self.displacement_angstrom, name="displacement_angstrom")
        distance = float(self.distance_angstrom)
        if not isfinite(distance) or distance < 0.0:
            raise GeometryError("distance_angstrom must be finite and non-negative")
        expected = float(np.linalg.norm(vector))
        if not np.isclose(distance, expected, rtol=1e-12, atol=1e-12):
            raise GeometryError("distance_angstrom contradicts displacement_angstrom")
        object.__setattr__(self, "displacement_angstrom", vector)
        object.__setattr__(self, "distance_angstrom", distance)


@dataclass(frozen=True, slots=True)
class SiteAngleResult:
    """One exact caller-selected first-vertex-third angle in degrees."""

    first: SiteImage
    vertex: SiteImage
    third: SiteImage
    angle_degrees: float

    def __post_init__(self) -> None:
        if not all(isinstance(item, SiteImage) for item in (self.first, self.vertex, self.third)):
            raise TypeError("first, vertex, and third must be SiteImage instances")
        angle = float(self.angle_degrees)
        if not isfinite(angle) or not 0.0 <= angle <= 180.0:
            raise GeometryError("angle_degrees must be finite and between 0 and 180")
        object.__setattr__(self, "angle_degrees", angle)


@dataclass(frozen=True, slots=True)
class CoordinationNeighbor:
    """One geometric neighbor retained by stable key and exact periodic image."""

    site_key: str
    image: PeriodicImage
    distance_angstrom: float

    def __post_init__(self) -> None:
        key = str(self.site_key).strip()
        if not key:
            raise GeometryError("neighbor site_key must not be blank")
        if not isinstance(self.image, PeriodicImage):
            raise TypeError("neighbor image must be a PeriodicImage")
        distance = float(self.distance_angstrom)
        if not isfinite(distance) or distance <= 0.0:
            raise GeometryError("neighbor distance_angstrom must be finite and positive")
        object.__setattr__(self, "site_key", key)
        object.__setattr__(self, "distance_angstrom", distance)


@dataclass(frozen=True, slots=True)
class CoordinationResult:
    """Deterministic coordination-by-cutoff result, not a chemical bond assignment."""

    center_key: str
    cutoff_angstrom: float
    image_range: tuple[int, int, int]
    neighbors: tuple[CoordinationNeighbor, ...]

    def __post_init__(self) -> None:
        key = str(self.center_key).strip()
        if not key:
            raise GeometryError("center_key must not be blank")
        cutoff = float(self.cutoff_angstrom)
        if not isfinite(cutoff) or cutoff <= 0.0:
            raise GeometryError("cutoff_angstrom must be finite and positive")
        if len(self.image_range) != 3:
            raise GeometryError("image_range must contain three values")
        image_range = tuple(
            _nonnegative_int(value, name=f"image_range[{index}]")
            for index, value in enumerate(self.image_range)
        )
        neighbors = tuple(self.neighbors)
        if not all(isinstance(item, CoordinationNeighbor) for item in neighbors):
            raise TypeError("neighbors must contain CoordinationNeighbor instances")
        identities = [(item.site_key, item.image.as_tuple()) for item in neighbors]
        if len(identities) != len(set(identities)):
            raise GeometryError("neighbor site/image identities must be unique")
        if any(item.site_key == key and item.image == _ZERO_IMAGE for item in neighbors):
            raise GeometryError("the exact center site/image cannot be its own neighbor")
        if any(item.distance_angstrom > cutoff + 1e-12 for item in neighbors):
            raise GeometryError("neighbor distance exceeds retained cutoff")
        expected_order = tuple(
            sorted(
                neighbors,
                key=lambda item: (
                    item.distance_angstrom,
                    item.site_key,
                    item.image.as_tuple(),
                ),
            )
        )
        if neighbors != expected_order:
            raise GeometryError(
                "neighbors must be ordered by distance, stable site key, and periodic image"
            )
        object.__setattr__(self, "center_key", key)
        object.__setattr__(self, "cutoff_angstrom", cutoff)
        object.__setattr__(self, "image_range", image_range)
        object.__setattr__(self, "neighbors", neighbors)

    @property
    def coordination_number(self) -> int:
        """Return the number of retained cutoff neighbors."""
        return len(self.neighbors)


@dataclass(frozen=True, slots=True)
class SiteMapping:
    """Explicit reference/candidate site mapping with explicit periodic images."""

    reference_key: str
    candidate_key: str
    reference_image: PeriodicImage = _ZERO_IMAGE
    candidate_image: PeriodicImage = _ZERO_IMAGE

    def __post_init__(self) -> None:
        reference_key = str(self.reference_key).strip()
        candidate_key = str(self.candidate_key).strip()
        if not reference_key or not candidate_key:
            raise GeometryError("mapping site keys must not be blank")
        if not isinstance(self.reference_image, PeriodicImage) or not isinstance(
            self.candidate_image, PeriodicImage
        ):
            raise TypeError("mapping images must be PeriodicImage instances")
        object.__setattr__(self, "reference_key", reference_key)
        object.__setattr__(self, "candidate_key", candidate_key)


@dataclass(frozen=True, slots=True, eq=False)
class StructureComparisonResult:
    """Mapped Cartesian displacement comparison with no hidden alignment."""

    reference_digest: str
    candidate_digest: str
    mappings: tuple[SiteMapping, ...]
    displacement_vectors_angstrom: Sequence[Sequence[float]]
    distances_angstrom: Sequence[float]
    rmsd_angstrom: float
    max_displacement_angstrom: float

    def __post_init__(self) -> None:
        reference_digest = str(self.reference_digest).strip()
        candidate_digest = str(self.candidate_digest).strip()
        if not reference_digest or not candidate_digest:
            raise GeometryError("structure digests must not be blank")
        mappings = tuple(self.mappings)
        if not mappings:
            raise GeometryError("mappings must contain at least one SiteMapping")
        if not all(isinstance(item, SiteMapping) for item in mappings):
            raise TypeError("mappings must contain only SiteMapping instances")
        reference_keys = [mapping.reference_key for mapping in mappings]
        candidate_keys = [mapping.candidate_key for mapping in mappings]
        if len(reference_keys) != len(set(reference_keys)):
            raise GeometryError("reference site keys must be unique in a comparison")
        if len(candidate_keys) != len(set(candidate_keys)):
            raise GeometryError("candidate site keys must be unique in a comparison")

        vectors = _frozen_matrix(
            self.displacement_vectors_angstrom,
            name="displacement_vectors_angstrom",
        )
        distances = _frozen_1d(self.distances_angstrom, name="distances_angstrom")
        if vectors.shape[0] != len(mappings) or distances.size != len(mappings):
            raise GeometryError("comparison arrays must match mapping count")
        expected_distances = np.linalg.norm(vectors, axis=1)
        if not np.allclose(distances, expected_distances, rtol=1e-12, atol=1e-12):
            raise GeometryError("distances_angstrom contradict displacement vectors")
        rmsd = float(self.rmsd_angstrom)
        maximum = float(self.max_displacement_angstrom)
        expected_rmsd = float(sqrt(float(np.mean(np.square(distances)))))
        expected_max = float(np.max(distances))
        if not isfinite(rmsd) or not np.isclose(rmsd, expected_rmsd, rtol=1e-12, atol=1e-12):
            raise GeometryError("rmsd_angstrom contradicts retained distances")
        if not isfinite(maximum) or not np.isclose(
            maximum,
            expected_max,
            rtol=1e-12,
            atol=1e-12,
        ):
            raise GeometryError("max_displacement_angstrom contradicts retained distances")
        object.__setattr__(self, "reference_digest", reference_digest)
        object.__setattr__(self, "candidate_digest", candidate_digest)
        object.__setattr__(self, "mappings", mappings)
        object.__setattr__(self, "displacement_vectors_angstrom", vectors)
        object.__setattr__(self, "distances_angstrom", distances)
        object.__setattr__(self, "rmsd_angstrom", rmsd)
        object.__setattr__(self, "max_displacement_angstrom", maximum)


def _site_index(structure: AtomicStructure, site_key: str) -> int:
    if not isinstance(structure, AtomicStructure):
        raise TypeError("structure must be an AtomicStructure")
    key = str(site_key).strip()
    try:
        return structure.site_keys.index(key)
    except ValueError as exc:
        raise GeometryError(f"unknown site key: {key}") from exc


def _validate_image(structure: AtomicStructure, image: PeriodicImage) -> None:
    if not isinstance(image, PeriodicImage):
        raise TypeError("image must be a PeriodicImage")
    offsets = image.as_tuple()
    for axis, (offset, enabled) in enumerate(zip(offsets, structure.pbc, strict=True)):
        if offset != 0 and not enabled:
            raise GeometryError(
                f"periodic image offset on nonperiodic axis {axis} is not allowed"
            )
    if any(offsets) and structure.lattice_angstrom is None:
        raise GeometryError("nonzero periodic images require an explicit lattice")


def _site_position(structure: AtomicStructure, site: SiteImage) -> NDArray[np.float64]:
    if not isinstance(site, SiteImage):
        raise TypeError("site must be a SiteImage")
    index = _site_index(structure, site.site_key)
    _validate_image(structure, site.image)
    position = np.asarray(structure.cartesian_coordinates[index], dtype=np.float64)
    if site.image != _ZERO_IMAGE:
        assert structure.lattice_angstrom is not None
        translation = np.asarray(site.image.as_tuple(), dtype=np.float64) @ np.asarray(
            structure.lattice_angstrom,
            dtype=np.float64,
        )
        position = position + translation
    return position


def site_distance(
    structure: AtomicStructure,
    first: SiteImage,
    second: SiteImage,
) -> SiteDistanceResult:
    """Return exact requested site/image distance without minimum-image replacement."""
    first_position = _site_position(structure, first)
    second_position = _site_position(structure, second)
    displacement = second_position - first_position
    return SiteDistanceResult(first, second, displacement, float(np.linalg.norm(displacement)))


def site_angle(
    structure: AtomicStructure,
    first: SiteImage,
    vertex: SiteImage,
    third: SiteImage,
) -> SiteAngleResult:
    """Return exact first-vertex-third angle for caller-selected periodic images."""
    first_vector = _site_position(structure, first) - _site_position(structure, vertex)
    third_vector = _site_position(structure, third) - _site_position(structure, vertex)
    first_norm = float(np.linalg.norm(first_vector))
    third_norm = float(np.linalg.norm(third_vector))
    if first_norm == 0.0 or third_norm == 0.0:
        raise GeometryError("site_angle requires nonzero vectors from the vertex")
    cosine = float(np.dot(first_vector, third_vector) / (first_norm * third_norm))
    cosine = min(1.0, max(-1.0, cosine))
    return SiteAngleResult(first, vertex, third, degrees(acos(cosine)))


def _validated_image_range(
    structure: AtomicStructure,
    image_range: Sequence[int],
) -> tuple[int, int, int]:
    if len(image_range) != 3:
        raise GeometryError("image_range must contain exactly three integer extents")
    ranges = tuple(
        _nonnegative_int(value, name=f"image_range[{index}]")
        for index, value in enumerate(image_range)
    )
    for axis, (extent, enabled) in enumerate(zip(ranges, structure.pbc, strict=True)):
        if extent and not enabled:
            raise GeometryError(f"image_range on nonperiodic axis {axis} must be zero")
    return ranges


def coordination_by_cutoff(
    structure: AtomicStructure,
    center_key: str,
    cutoff_angstrom: float,
    *,
    image_range: Sequence[int],
) -> CoordinationResult:
    """Enumerate cutoff neighbors only within caller-declared periodic image bounds."""
    if not isinstance(structure, AtomicStructure):
        raise TypeError("structure must be an AtomicStructure")
    center_index = _site_index(structure, center_key)
    cutoff = float(cutoff_angstrom)
    if not isfinite(cutoff) or cutoff <= 0.0:
        raise GeometryError("cutoff_angstrom must be finite and positive")
    ranges = _validated_image_range(structure, image_range)
    center = np.asarray(structure.cartesian_coordinates[center_index], dtype=np.float64)
    lattice = (
        None
        if structure.lattice_angstrom is None
        else np.asarray(structure.lattice_angstrom, dtype=np.float64)
    )
    records: list[CoordinationNeighbor] = []
    image_axes = [range(-extent, extent + 1) for extent in ranges]
    for site_index, site_key in enumerate(structure.site_keys):
        base = np.asarray(structure.cartesian_coordinates[site_index], dtype=np.float64)
        for image_tuple in product(*image_axes):
            if site_index == center_index and image_tuple == (0, 0, 0):
                continue
            position = base
            if image_tuple != (0, 0, 0):
                assert lattice is not None
                position = base + np.asarray(image_tuple, dtype=np.float64) @ lattice
            distance = float(np.linalg.norm(position - center))
            if 0.0 < distance <= cutoff + 1e-12:
                records.append(
                    CoordinationNeighbor(
                        site_key=site_key,
                        image=PeriodicImage(*image_tuple),
                        distance_angstrom=distance,
                    )
                )
    records.sort(
        key=lambda item: (
            item.distance_angstrom,
            item.site_key,
            item.image.as_tuple(),
        )
    )
    return CoordinationResult(
        center_key=str(center_key).strip(),
        cutoff_angstrom=cutoff,
        image_range=ranges,
        neighbors=tuple(records),
    )


def compare_structures(
    reference: AtomicStructure,
    candidate: AtomicStructure,
    mappings: Sequence[SiteMapping],
) -> StructureComparisonResult:
    """Compare exact caller-mapped positions without auto-mapping or alignment."""
    if not isinstance(reference, AtomicStructure) or not isinstance(candidate, AtomicStructure):
        raise TypeError("reference and candidate must be AtomicStructure instances")
    retained_mappings = tuple(mappings)
    if not retained_mappings:
        raise GeometryError("mappings must contain at least one SiteMapping")
    if not all(isinstance(mapping, SiteMapping) for mapping in retained_mappings):
        raise TypeError("mappings must contain only SiteMapping instances")
    reference_keys = [mapping.reference_key for mapping in retained_mappings]
    candidate_keys = [mapping.candidate_key for mapping in retained_mappings]
    if len(reference_keys) != len(set(reference_keys)):
        raise GeometryError("reference site keys must be unique in a comparison")
    if len(candidate_keys) != len(set(candidate_keys)):
        raise GeometryError("candidate site keys must be unique in a comparison")

    vectors: list[NDArray[np.float64]] = []
    for mapping in retained_mappings:
        reference_position = _site_position(
            reference,
            SiteImage(mapping.reference_key, mapping.reference_image),
        )
        candidate_position = _site_position(
            candidate,
            SiteImage(mapping.candidate_key, mapping.candidate_image),
        )
        vectors.append(candidate_position - reference_position)
    matrix = np.asarray(vectors, dtype=np.float64)
    distances = np.linalg.norm(matrix, axis=1)
    rmsd = float(sqrt(float(np.mean(np.square(distances)))))
    maximum = float(np.max(distances))
    return StructureComparisonResult(
        reference_digest=reference.digest,
        candidate_digest=candidate.digest,
        mappings=retained_mappings,
        displacement_vectors_angstrom=matrix,
        distances_angstrom=distances,
        rmsd_angstrom=rmsd,
        max_displacement_angstrom=maximum,
    )


__all__ = [
    "CoordinationNeighbor",
    "CoordinationResult",
    "GeometryError",
    "PeriodicImage",
    "SiteAngleResult",
    "SiteDistanceResult",
    "SiteImage",
    "SiteMapping",
    "StructureComparisonResult",
    "compare_structures",
    "coordination_by_cutoff",
    "site_angle",
    "site_distance",
]
