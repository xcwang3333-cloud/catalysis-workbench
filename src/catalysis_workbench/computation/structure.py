"""Immutable atomic-structure state owned by CatalysisWorkbench."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

import numpy as np
from numpy.typing import NDArray


class StructureError(ValueError):
    """Raised when atomic-structure state is internally inconsistent."""


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _freeze_value(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_value(item) for item in value)
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


def _thaw_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_value(item) for item in value]
    if isinstance(value, frozenset):
        return {_thaw_value(item) for item in value}
    if isinstance(value, np.ndarray):
        return np.array(value, copy=True)
    return deepcopy(value)


def _frozen_float_matrix(
    values: Any,
    *,
    name: str,
    columns: int,
    rows: int | None = None,
) -> NDArray[np.float64]:
    source = np.asarray(values)
    if np.iscomplexobj(source):
        raise StructureError(f"{name} must contain real values")
    try:
        array = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must contain real numeric values") from exc
    if array.ndim != 2 or array.shape[1] != columns:
        row_text = "N" if rows is None else str(rows)
        raise StructureError(f"{name} must have shape ({row_text}, {columns})")
    if rows is not None and array.shape[0] != rows:
        raise StructureError(f"{name} must have shape ({rows}, {columns})")
    if array.shape[0] == 0 or not np.isfinite(array).all():
        raise StructureError(f"{name} must contain finite values and at least one row")
    contiguous = np.ascontiguousarray(array, dtype=np.float64)
    frozen = np.frombuffer(contiguous.tobytes(order="C"), dtype=np.float64).reshape(
        contiguous.shape
    )
    frozen.setflags(write=False)
    return frozen


def _nonblank_strings(values: Sequence[str], *, name: str) -> tuple[str, ...]:
    result = tuple(str(value).strip() for value in values)
    if not result or any(not value for value in result):
        raise StructureError(f"{name} must contain nonblank strings")
    return result


def _site_labels(
    values: Sequence[str | None] | None,
    *,
    count: int,
) -> tuple[str | None, ...]:
    if values is None:
        return (None,) * count
    if len(values) != count:
        raise StructureError("site_labels length must match site count")
    result: list[str | None] = []
    for value in values:
        if value is None:
            result.append(None)
            continue
        text = str(value).strip()
        result.append(text or None)
    return tuple(result)


def _pbc_flags(values: Sequence[bool]) -> tuple[bool, bool, bool]:
    if len(values) != 3:
        raise StructureError("pbc must contain exactly three boolean flags")
    result: list[bool] = []
    for value in values:
        if not isinstance(value, (bool, np.bool_)):
            raise TypeError("pbc flags must be booleans")
        result.append(bool(value))
    return result[0], result[1], result[2]


def _update_digest_string(digest: hashlib._Hash, value: str | None) -> None:
    if value is None:
        digest.update(b"\xff")
        return
    encoded = value.encode("utf-8")
    digest.update(len(encoded).to_bytes(8, "little", signed=False))
    digest.update(encoded)


def _structure_digest(
    species: tuple[str, ...],
    elements: tuple[str, ...],
    coordinates: NDArray[np.float64],
    lattice: NDArray[np.float64] | None,
    pbc: tuple[bool, bool, bool],
    site_keys: tuple[str, ...],
    site_labels: tuple[str | None, ...],
) -> str:
    """Return a digest of retained scientific/identity state, excluding metadata."""
    digest = hashlib.sha256()
    digest.update(b"CatalysisWorkbench.AtomicStructure.v1\0")
    digest.update(len(species).to_bytes(8, "little", signed=False))
    for collection in (species, elements, site_keys):
        for value in collection:
            _update_digest_string(digest, value)
    for value in site_labels:
        _update_digest_string(digest, value)
    digest.update(bytes(int(flag) for flag in pbc))
    digest.update(np.ascontiguousarray(coordinates, dtype=np.float64).tobytes())
    if lattice is None:
        digest.update(b"no-lattice")
    else:
        digest.update(b"lattice")
        digest.update(np.ascontiguousarray(lattice, dtype=np.float64).tobytes())
    return digest.hexdigest()


@dataclass(frozen=True, slots=True, eq=False)
class AtomicStructure:
    """Ordered immutable atomic structure with explicit Cartesian/PBC semantics.

    `species` retains the full ordered species identity supplied by the caller or
    parser (for example, an oxidation-decorated species string). `elements` stores
    the corresponding canonical element symbols. Cartesian coordinates and lattice
    vectors are always in angstrom.
    """

    species: Sequence[str]
    elements: Sequence[str]
    cartesian_coordinates: Any
    lattice_angstrom: Any | None = None
    pbc: Sequence[bool] = (False, False, False)
    site_keys: Sequence[str] | None = None
    site_labels: Sequence[str | None] | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        species = _nonblank_strings(self.species, name="species")
        elements = _nonblank_strings(self.elements, name="elements")
        coordinates = _frozen_float_matrix(
            self.cartesian_coordinates,
            name="cartesian_coordinates",
            columns=3,
        )
        count = coordinates.shape[0]
        if len(species) != count or len(elements) != count:
            raise StructureError(
                "species/elements lengths must match Cartesian coordinate site count"
            )

        pbc = _pbc_flags(self.pbc)
        lattice: NDArray[np.float64] | None = None
        if self.lattice_angstrom is not None:
            lattice = _frozen_float_matrix(
                self.lattice_angstrom,
                name="lattice_angstrom",
                rows=3,
                columns=3,
            )
            if np.linalg.matrix_rank(lattice) != 3:
                raise StructureError("lattice_angstrom must be nonsingular")
        if any(pbc) and lattice is None:
            raise StructureError("periodic axes require an explicit lattice_angstrom")

        if self.site_keys is None:
            width = max(4, len(str(count - 1)))
            site_keys = tuple(f"site-{index:0{width}d}" for index in range(count))
        else:
            if len(self.site_keys) != count:
                raise StructureError("site_keys length must match site count")
            site_keys = _nonblank_strings(self.site_keys, name="site_keys")
        if len(set(site_keys)) != count:
            raise StructureError("site_keys must be unique")
        site_labels = _site_labels(self.site_labels, count=count)
        metadata = _freeze_metadata(self.metadata)
        digest = _structure_digest(
            species,
            elements,
            coordinates,
            lattice,
            pbc,
            site_keys,
            site_labels,
        )

        object.__setattr__(self, "species", species)
        object.__setattr__(self, "elements", elements)
        object.__setattr__(self, "cartesian_coordinates", coordinates)
        object.__setattr__(self, "lattice_angstrom", lattice)
        object.__setattr__(self, "pbc", pbc)
        object.__setattr__(self, "site_keys", site_keys)
        object.__setattr__(self, "site_labels", site_labels)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "digest", digest)

    @property
    def site_count(self) -> int:
        """Return the ordered number of sites."""
        return len(self.species)

    @property
    def is_periodic(self) -> bool:
        """Return whether at least one periodic boundary condition is active."""
        return any(self.pbc)

    def metadata_dict(self) -> dict[str, Any]:
        """Return an independent mutable copy of source/provenance metadata."""
        return {key: _thaw_value(value) for key, value in self.metadata.items()}

    def equals(self, other: object) -> bool:
        """Return exact scientific/identity equality; metadata is intentionally excluded."""
        return (
            isinstance(other, AtomicStructure)
            and self.species == other.species
            and self.elements == other.elements
            and np.array_equal(self.cartesian_coordinates, other.cartesian_coordinates)
            and (
                (self.lattice_angstrom is None and other.lattice_angstrom is None)
                or (
                    self.lattice_angstrom is not None
                    and other.lattice_angstrom is not None
                    and np.array_equal(self.lattice_angstrom, other.lattice_angstrom)
                )
            )
            and self.pbc == other.pbc
            and self.site_keys == other.site_keys
            and self.site_labels == other.site_labels
            and self.digest == other.digest
        )

    def __eq__(self, other: object) -> bool:
        return self.equals(other)


__all__ = ["AtomicStructure", "StructureError"]
