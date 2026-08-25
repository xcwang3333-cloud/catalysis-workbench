"""Immutable electronic-structure and volumetric state owned by CatalysisWorkbench."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .structure import AtomicStructure

_ALLOWED_ENERGY_REFERENCES = frozenset({"source-native", "fermi", "vacuum", "custom"})
_ALLOWED_SPINS = frozenset({"total", "up", "down"})
_ALLOWED_PROJECTION_KINDS = frozenset({"total", "site-orbital"})


class ElectronicStructureError(ValueError):
    """Raised when electronic-structure state is scientifically inconsistent."""


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


def _frozen_float_array(values: Any, *, name: str, ndim: int) -> NDArray[np.float64]:
    try:
        source = np.asarray(values)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must contain real numeric values") from exc
    if np.iscomplexobj(source):
        raise ElectronicStructureError(f"{name} must contain real values")
    try:
        array = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must contain real numeric values") from exc
    if array.ndim != ndim or array.size == 0:
        raise ElectronicStructureError(
            f"{name} must be a non-empty {ndim}-dimensional array"
        )
    if not np.isfinite(array).all():
        raise ElectronicStructureError(f"{name} must contain only finite values")
    contiguous = np.ascontiguousarray(array, dtype=np.float64)
    frozen = np.frombuffer(contiguous.tobytes(order="C"), dtype=np.float64).reshape(
        contiguous.shape
    )
    frozen.setflags(write=False)
    return frozen


def _finite_float(value: float | None, *, name: str) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a finite float or None") from exc
    if not np.isfinite(result):
        raise ElectronicStructureError(f"{name} must be finite")
    return result


def _nonblank(value: str, *, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ElectronicStructureError(f"{name} must not be blank")
    return text


def _update_digest_string(digest: Any, value: str | None) -> None:
    if value is None:
        digest.update(b"\xff")
        return
    encoded = value.encode("utf-8")
    digest.update(len(encoded).to_bytes(8, "little", signed=False))
    digest.update(encoded)


@dataclass(frozen=True, slots=True, eq=False)
class ElectronicEnergyAxis:
    """Strict source energy axis with explicit reference and Fermi semantics."""

    values_ev: Any
    reference_kind: str = "source-native"
    source_fermi_ev: float | None = None
    applied_shift_ev: float = 0.0
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        values = _frozen_float_array(self.values_ev, name="values_ev", ndim=1)
        if values.size < 2:
            raise ElectronicStructureError("values_ev must contain at least two points")
        if not np.all(np.diff(values) > 0):
            raise ElectronicStructureError(
                "values_ev must be strictly increasing without duplicates"
            )
        reference = _nonblank(self.reference_kind, name="reference_kind").lower()
        if reference not in _ALLOWED_ENERGY_REFERENCES:
            raise ElectronicStructureError(
                "reference_kind must be one of: "
                + ", ".join(sorted(_ALLOWED_ENERGY_REFERENCES))
            )
        fermi = _finite_float(self.source_fermi_ev, name="source_fermi_ev")
        shift = _finite_float(self.applied_shift_ev, name="applied_shift_ev")
        assert shift is not None

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.ElectronicEnergyAxis.v1\0")
        digest.update(values.tobytes(order="C"))
        _update_digest_string(digest, reference)
        _update_digest_string(digest, None if fermi is None else repr(fermi))
        _update_digest_string(digest, repr(shift))

        object.__setattr__(self, "values_ev", values)
        object.__setattr__(self, "reference_kind", reference)
        object.__setattr__(self, "source_fermi_ev", fermi)
        object.__setattr__(self, "applied_shift_ev", shift)
        object.__setattr__(self, "digest", digest.hexdigest())

    def equals(self, other: object) -> bool:
        return (
            isinstance(other, ElectronicEnergyAxis)
            and np.array_equal(self.values_ev, other.values_ev)
            and self.reference_kind == other.reference_kind
            and self.source_fermi_ev == other.source_fermi_ev
            and self.applied_shift_ev == other.applied_shift_ev
            and self.digest == other.digest
        )

    def __eq__(self, other: object) -> bool:
        return self.equals(other)


@dataclass(frozen=True, slots=True)
class DOSProjection:
    """Stable identity for one total or site/orbital DOS projection."""

    key: str
    kind: str
    site_index: int | None = None
    site_key: str | None = None
    element: str | None = None
    orbital: str | None = None

    def __post_init__(self) -> None:
        key = _nonblank(self.key, name="key")
        kind = _nonblank(self.kind, name="kind").lower()
        if kind not in _ALLOWED_PROJECTION_KINDS:
            raise ElectronicStructureError(
                "projection kind must be one of: "
                + ", ".join(sorted(_ALLOWED_PROJECTION_KINDS))
            )

        if kind == "total":
            if any(
                value is not None
                for value in (self.site_index, self.site_key, self.element, self.orbital)
            ):
                raise ElectronicStructureError(
                    "total projection must not carry site/orbital identity"
                )
        else:
            if (
                isinstance(self.site_index, bool)
                or not isinstance(self.site_index, int)
                or self.site_index < 0
            ):
                raise ElectronicStructureError(
                    "site-orbital projection requires a non-negative site_index"
                )
            site_key = _nonblank(
                "" if self.site_key is None else self.site_key,
                name="site_key",
            )
            element = _nonblank(
                "" if self.element is None else self.element,
                name="element",
            )
            orbital = _nonblank(
                "" if self.orbital is None else self.orbital,
                name="orbital",
            )
            object.__setattr__(self, "site_key", site_key)
            object.__setattr__(self, "element", element)
            object.__setattr__(self, "orbital", orbital)

        object.__setattr__(self, "key", key)
        object.__setattr__(self, "kind", kind)


@dataclass(frozen=True, slots=True, eq=False)
class DOSChannel:
    """One physical DOS channel on an authoritative shared energy grid."""

    projection: DOSProjection
    spin: str
    density: Any
    density_unit: str = "states/eV"
    normalization_basis: str = "cell"
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.projection, DOSProjection):
            raise TypeError("projection must be a DOSProjection")
        spin = _nonblank(self.spin, name="spin").lower()
        if spin not in _ALLOWED_SPINS:
            raise ElectronicStructureError(
                "spin must be one of: " + ", ".join(sorted(_ALLOWED_SPINS))
            )
        density = _frozen_float_array(self.density, name="density", ndim=1)
        if np.any(density < 0):
            raise ElectronicStructureError(
                "scientific DOS density must be non-negative; spin mirroring is display-only"
            )
        density_unit = _nonblank(self.density_unit, name="density_unit")
        normalization = _nonblank(
            self.normalization_basis,
            name="normalization_basis",
        )

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.DOSChannel.v1\0")
        _update_digest_string(digest, self.projection.key)
        _update_digest_string(digest, self.projection.kind)
        _update_digest_string(
            digest,
            None if self.projection.site_index is None else str(self.projection.site_index),
        )
        _update_digest_string(digest, self.projection.site_key)
        _update_digest_string(digest, self.projection.element)
        _update_digest_string(digest, self.projection.orbital)
        _update_digest_string(digest, spin)
        _update_digest_string(digest, density_unit)
        _update_digest_string(digest, normalization)
        digest.update(density.tobytes(order="C"))

        object.__setattr__(self, "spin", spin)
        object.__setattr__(self, "density", density)
        object.__setattr__(self, "density_unit", density_unit)
        object.__setattr__(self, "normalization_basis", normalization)
        object.__setattr__(self, "digest", digest.hexdigest())

    def equals(self, other: object) -> bool:
        return (
            isinstance(other, DOSChannel)
            and self.projection == other.projection
            and self.spin == other.spin
            and np.array_equal(self.density, other.density)
            and self.density_unit == other.density_unit
            and self.normalization_basis == other.normalization_basis
            and self.digest == other.digest
        )

    def __eq__(self, other: object) -> bool:
        return self.equals(other)


@dataclass(frozen=True, slots=True, eq=False)
class ElectronicDOS:
    """Immutable source DOS/PDOS state with explicit references and projections."""

    energy: ElectronicEnergyAxis
    channels: Sequence[DOSChannel]
    structure: AtomicStructure | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.energy, ElectronicEnergyAxis):
            raise TypeError("energy must be an ElectronicEnergyAxis")
        channels = tuple(self.channels)
        if not channels or any(not isinstance(channel, DOSChannel) for channel in channels):
            raise ElectronicStructureError(
                "channels must contain at least one DOSChannel"
            )
        expected = self.energy.values_ev.size
        identities: set[tuple[str, str]] = set()
        for channel in channels:
            if channel.density.size != expected:
                raise ElectronicStructureError(
                    "every DOS channel must match the electronic energy grid length"
                )
            identity = (channel.projection.key, channel.spin)
            if identity in identities:
                raise ElectronicStructureError(
                    "projection/spin channel identities must be unique"
                )
            identities.add(identity)
            projection = channel.projection
            if projection.kind == "site-orbital":
                if self.structure is None:
                    raise ElectronicStructureError(
                        "site/orbital projections require an attached AtomicStructure"
                    )
                assert projection.site_index is not None
                if projection.site_index >= self.structure.site_count:
                    raise ElectronicStructureError(
                        "projection site_index is outside the attached structure"
                    )
                if self.structure.site_keys[projection.site_index] != projection.site_key:
                    raise ElectronicStructureError(
                        "projection site_key does not match attached structure"
                    )
                if self.structure.elements[projection.site_index] != projection.element:
                    raise ElectronicStructureError(
                        "projection element does not match attached structure"
                    )

        metadata = _freeze_metadata(self.metadata)
        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.ElectronicDOS.v1\0")
        _update_digest_string(digest, self.energy.digest)
        _update_digest_string(
            digest,
            None if self.structure is None else self.structure.digest,
        )
        for channel in channels:
            _update_digest_string(digest, channel.digest)

        object.__setattr__(self, "channels", channels)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "digest", digest.hexdigest())

    def metadata_dict(self) -> dict[str, Any]:
        """Return an independent mutable copy of source/provenance metadata."""
        return {key: _thaw_value(value) for key, value in self.metadata.items()}

    def equals(self, other: object) -> bool:
        return (
            isinstance(other, ElectronicDOS)
            and self.energy == other.energy
            and self.channels == other.channels
            and (
                (self.structure is None and other.structure is None)
                or (
                    self.structure is not None
                    and other.structure is not None
                    and self.structure == other.structure
                )
            )
            and self.digest == other.digest
        )

    def __eq__(self, other: object) -> bool:
        return self.equals(other)


@dataclass(frozen=True, slots=True, eq=False)
class VolumetricGrid:
    """Immutable co-registered volumetric components on one periodic cell/grid."""

    structure: AtomicStructure
    components: Mapping[str, Any]
    density_unit: str = "1/angstrom^3"
    metadata: Mapping[str, Any] = field(default_factory=dict)
    grid_shape: tuple[int, int, int] = field(init=False)
    cell_volume_angstrom3: float = field(init=False)
    voxel_volume_angstrom3: float = field(init=False)
    component_integrals: Mapping[str, float] = field(init=False)
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.structure, AtomicStructure):
            raise TypeError("structure must be an AtomicStructure")
        if self.structure.lattice_angstrom is None or not all(self.structure.pbc):
            raise ElectronicStructureError(
                "volumetric grids require a fully periodic structure with an explicit lattice"
            )
        density_unit = _nonblank(self.density_unit, name="density_unit")
        if density_unit != "1/angstrom^3":
            raise ElectronicStructureError(
                "v0.6 volumetric density_unit must be exactly '1/angstrom^3'"
            )

        source_components = dict(self.components)
        if not source_components:
            raise ElectronicStructureError("components must contain at least one grid")
        frozen_components: dict[str, NDArray[np.float64]] = {}
        shape: tuple[int, int, int] | None = None
        for raw_key, values in source_components.items():
            key = _nonblank(str(raw_key), name="component key")
            if key in frozen_components:
                raise ElectronicStructureError("component keys must be unique")
            array = _frozen_float_array(
                values,
                name=f"component[{key}]",
                ndim=3,
            )
            if shape is None:
                shape = tuple(int(value) for value in array.shape)
            elif array.shape != shape:
                raise ElectronicStructureError(
                    "all volumetric components must have identical grid shapes"
                )
            frozen_components[key] = array
        assert shape is not None

        volume = float(abs(np.linalg.det(self.structure.lattice_angstrom)))
        if not np.isfinite(volume) or volume <= 0:
            raise ElectronicStructureError("structure lattice must have positive finite volume")
        voxel = volume / int(np.prod(shape))
        integrals = {
            key: float(np.sum(array, dtype=np.float64) * voxel)
            for key, array in frozen_components.items()
        }
        metadata = _freeze_metadata(self.metadata)

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.VolumetricGrid.v1\0")
        _update_digest_string(digest, self.structure.digest)
        _update_digest_string(digest, density_unit)
        for value in shape:
            digest.update(value.to_bytes(8, "little", signed=False))
        for key, array in frozen_components.items():
            _update_digest_string(digest, key)
            digest.update(array.tobytes(order="C"))

        object.__setattr__(self, "components", MappingProxyType(frozen_components))
        object.__setattr__(self, "density_unit", density_unit)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "grid_shape", shape)
        object.__setattr__(self, "cell_volume_angstrom3", volume)
        object.__setattr__(self, "voxel_volume_angstrom3", voxel)
        object.__setattr__(
            self,
            "component_integrals",
            MappingProxyType(integrals),
        )
        object.__setattr__(self, "digest", digest.hexdigest())

    def metadata_dict(self) -> dict[str, Any]:
        """Return an independent mutable copy of source/provenance metadata."""
        return {key: _thaw_value(value) for key, value in self.metadata.items()}

    def equals(self, other: object) -> bool:
        return (
            isinstance(other, VolumetricGrid)
            and self.structure == other.structure
            and self.density_unit == other.density_unit
            and self.grid_shape == other.grid_shape
            and tuple(self.components) == tuple(other.components)
            and all(
                np.array_equal(self.components[key], other.components[key])
                for key in self.components
            )
            and self.digest == other.digest
        )

    def __eq__(self, other: object) -> bool:
        return self.equals(other)


__all__ = [
    "DOSChannel",
    "DOSProjection",
    "ElectronicDOS",
    "ElectronicEnergyAxis",
    "ElectronicStructureError",
    "VolumetricGrid",
]
