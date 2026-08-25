"""Immutable PROCAR projection state and explicit aggregation."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .band_structure import BandStructureState

_ALLOWED_SPINS = frozenset({"total", "up", "down"})


class BandProjectionError(ValueError):
    """Raised when projected-band state is scientifically inconsistent."""


def _nonblank(value: object, *, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise BandProjectionError(f"{name} must not be blank")
    return text


def _frozen_nonnegative_array(values: Any, *, name: str, ndim: int) -> NDArray[np.float64]:
    try:
        source = np.asarray(values)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must contain real numeric values") from exc
    if np.iscomplexobj(source):
        raise BandProjectionError(f"{name} must contain real values")
    try:
        array = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must contain real numeric values") from exc
    if array.ndim != ndim or array.size == 0:
        raise BandProjectionError(f"{name} must be a non-empty {ndim}-dimensional array")
    if not np.isfinite(array).all():
        raise BandProjectionError(f"{name} must contain only finite values")
    if np.any(array < 0.0):
        raise BandProjectionError(f"{name} must contain only non-negative values")
    contiguous = np.ascontiguousarray(array, dtype=np.float64)
    frozen = np.frombuffer(contiguous.tobytes(order="C"), dtype=np.float64).reshape(
        contiguous.shape
    )
    frozen.setflags(write=False)
    return frozen


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_value(item) for key, item in value.items()})
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
    return MappingProxyType({str(key): _freeze_value(value) for key, value in source.items()})


def _update_digest_string(digest: Any, value: str | None) -> None:
    if value is None:
        digest.update(b"\xff")
        return
    encoded = value.encode("utf-8")
    digest.update(len(encoded).to_bytes(8, "little", signed=False))
    digest.update(encoded)


@dataclass(frozen=True, slots=True, eq=False)
class BandProjectionChannel:
    """Exact scalar PROCAR projection weights for one physical spin channel.

    The canonical axis order is ``(band, kpoint, site, orbital)``. Adapter-level
    transposition into this order is representational only and does not alter values.
    """

    spin: str
    weights: Any
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        spin = _nonblank(self.spin, name="spin").lower()
        if spin not in _ALLOWED_SPINS:
            raise BandProjectionError(
                "spin must be one of: " + ", ".join(sorted(_ALLOWED_SPINS))
            )
        weights = _frozen_nonnegative_array(self.weights, name="weights", ndim=4)

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.BandProjectionChannel.v1\0")
        _update_digest_string(digest, spin)
        for size in weights.shape:
            digest.update(int(size).to_bytes(8, "little", signed=False))
        digest.update(weights.tobytes(order="C"))

        object.__setattr__(self, "spin", spin)
        object.__setattr__(self, "weights", weights)
        object.__setattr__(self, "digest", digest.hexdigest())

    def equals(self, other: object) -> bool:
        return (
            isinstance(other, BandProjectionChannel)
            and self.spin == other.spin
            and np.array_equal(self.weights, other.weights)
            and self.digest == other.digest
        )

    def __eq__(self, other: object) -> bool:
        return self.equals(other)


@dataclass(frozen=True, slots=True, eq=False)
class BandProjectionState:
    """Projection state explicitly bound to one reviewed ordinary band source."""

    band_structure: BandStructureState
    orbitals: Sequence[str]
    channels: Sequence[BandProjectionChannel]
    source_digest: str
    projection_semantics: str = "vasp-procar-projection-weight"
    projection_unit: str = "dimensionless"
    metadata: Mapping[str, Any] = field(default_factory=dict)
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.band_structure, BandStructureState):
            raise TypeError("band_structure must be a BandStructureState")

        orbitals = tuple(_nonblank(item, name="orbital") for item in self.orbitals)
        if not orbitals:
            raise BandProjectionError("orbitals must contain at least one source orbital")
        if len(set(orbitals)) != len(orbitals):
            raise BandProjectionError("orbitals must not contain duplicate source labels")

        channels = tuple(self.channels)
        if not channels or any(
            not isinstance(channel, BandProjectionChannel) for channel in channels
        ):
            raise BandProjectionError(
                "channels must contain at least one BandProjectionChannel"
            )
        spin_set = {channel.spin for channel in channels}
        expected_spins = {channel.spin for channel in self.band_structure.channels}
        if spin_set != expected_spins:
            raise BandProjectionError(
                "projection physical spin set must exactly match the associated band state"
            )
        if len(channels) != len(spin_set):
            raise BandProjectionError("projection physical spin channels must not be duplicated")

        n_bands = self.band_structure.channels[0].energies_ev.shape[0]
        n_kpoints = self.band_structure.kpoints_fractional.shape[0]
        n_sites = self.band_structure.structure.site_count
        expected_shape = (n_bands, n_kpoints, n_sites, len(orbitals))
        for channel in channels:
            if channel.weights.shape != expected_shape:
                raise BandProjectionError(
                    "every projection channel must have shape "
                    f"{expected_shape}, got {channel.weights.shape}"
                )

        source_digest = _nonblank(self.source_digest, name="source_digest")
        semantics = _nonblank(self.projection_semantics, name="projection_semantics")
        unit = _nonblank(self.projection_unit, name="projection_unit")
        if unit != "dimensionless":
            raise BandProjectionError("Block-4 PROCAR projection_unit must be 'dimensionless'")
        frozen_metadata = _freeze_metadata(self.metadata)

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.BandProjectionState.v1\0")
        _update_digest_string(digest, self.band_structure.digest)
        _update_digest_string(digest, self.band_structure.source_digest)
        for orbital in orbitals:
            _update_digest_string(digest, orbital)
        for channel in channels:
            _update_digest_string(digest, channel.digest)
        _update_digest_string(digest, source_digest)
        _update_digest_string(digest, semantics)
        _update_digest_string(digest, unit)

        object.__setattr__(self, "orbitals", orbitals)
        object.__setattr__(self, "channels", channels)
        object.__setattr__(self, "source_digest", source_digest)
        object.__setattr__(self, "projection_semantics", semantics)
        object.__setattr__(self, "projection_unit", unit)
        object.__setattr__(self, "metadata", frozen_metadata)
        object.__setattr__(self, "digest", digest.hexdigest())

    @property
    def site_keys(self) -> tuple[str, ...]:
        """Exact site keys inherited from the associated structure."""
        return self.band_structure.structure.site_keys

    @property
    def elements(self) -> tuple[str, ...]:
        """Exact element identities inherited from the associated structure."""
        return self.band_structure.structure.elements

    def channel(self, spin: str) -> BandProjectionChannel:
        token = _nonblank(spin, name="spin").lower()
        for channel in self.channels:
            if channel.spin == token:
                return channel
        raise BandProjectionError(f"projection state does not contain physical spin {token!r}")

    def equals(self, other: object) -> bool:
        return (
            isinstance(other, BandProjectionState)
            and self.band_structure == other.band_structure
            and self.orbitals == other.orbitals
            and self.channels == other.channels
            and self.source_digest == other.source_digest
            and self.projection_semantics == other.projection_semantics
            and self.projection_unit == other.projection_unit
            and self.digest == other.digest
        )

    def __eq__(self, other: object) -> bool:
        return self.equals(other)


@dataclass(frozen=True, slots=True, eq=False)
class AggregatedBandProjection:
    """One explicit site/orbital sum for one physical spin channel."""

    band_structure: BandStructureState
    projection_state_digest: str
    projection_source_digest: str
    spin: str
    site_indices: Sequence[int]
    site_keys: Sequence[str]
    elements: Sequence[str]
    orbitals: Sequence[str]
    weights: Any
    aggregation: str = "sum"
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.band_structure, BandStructureState):
            raise TypeError("band_structure must be a BandStructureState")
        projection_state_digest = _nonblank(
            self.projection_state_digest, name="projection_state_digest"
        )
        projection_source_digest = _nonblank(
            self.projection_source_digest, name="projection_source_digest"
        )
        spin = _nonblank(self.spin, name="spin").lower()
        if spin not in {channel.spin for channel in self.band_structure.channels}:
            raise BandProjectionError(
                "aggregated projection spin must exist in the associated band state"
            )

        site_indices = tuple(self.site_indices)
        if not site_indices:
            raise BandProjectionError("site_indices must not be empty")
        if any(
            isinstance(index, bool) or not isinstance(index, int) or index < 0
            for index in site_indices
        ):
            raise BandProjectionError("site_indices must contain non-negative integers")
        if len(set(site_indices)) != len(site_indices):
            raise BandProjectionError("site_indices must not contain duplicates")
        if any(index >= self.band_structure.structure.site_count for index in site_indices):
            raise BandProjectionError("site_indices exceed the associated structure")

        site_keys = tuple(_nonblank(value, name="site_key") for value in self.site_keys)
        elements = tuple(_nonblank(value, name="element") for value in self.elements)
        orbitals = tuple(_nonblank(value, name="orbital") for value in self.orbitals)
        if len(site_keys) != len(site_indices) or len(elements) != len(site_indices):
            raise BandProjectionError(
                "site_keys and elements must match the explicit site_indices length"
            )
        if not orbitals or len(set(orbitals)) != len(orbitals):
            raise BandProjectionError("orbitals must be a non-empty unique explicit selection")

        weights = _frozen_nonnegative_array(self.weights, name="weights", ndim=2)
        expected_shape = (
            self.band_structure.channels[0].energies_ev.shape[0],
            self.band_structure.kpoints_fractional.shape[0],
        )
        if weights.shape != expected_shape:
            raise BandProjectionError(
                f"aggregated weights must have shape {expected_shape}, got {weights.shape}"
            )
        aggregation = _nonblank(self.aggregation, name="aggregation").lower()
        if aggregation != "sum":
            raise BandProjectionError("Block-4 aggregation must be explicit 'sum'")

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.AggregatedBandProjection.v1\0")
        _update_digest_string(digest, self.band_structure.digest)
        _update_digest_string(digest, projection_state_digest)
        _update_digest_string(digest, projection_source_digest)
        _update_digest_string(digest, spin)
        for index in site_indices:
            digest.update(index.to_bytes(8, "little", signed=False))
        for value in site_keys:
            _update_digest_string(digest, value)
        for value in elements:
            _update_digest_string(digest, value)
        for value in orbitals:
            _update_digest_string(digest, value)
        _update_digest_string(digest, aggregation)
        digest.update(weights.tobytes(order="C"))

        object.__setattr__(self, "projection_state_digest", projection_state_digest)
        object.__setattr__(self, "projection_source_digest", projection_source_digest)
        object.__setattr__(self, "spin", spin)
        object.__setattr__(self, "site_indices", site_indices)
        object.__setattr__(self, "site_keys", site_keys)
        object.__setattr__(self, "elements", elements)
        object.__setattr__(self, "orbitals", orbitals)
        object.__setattr__(self, "weights", weights)
        object.__setattr__(self, "aggregation", aggregation)
        object.__setattr__(self, "digest", digest.hexdigest())

    def equals(self, other: object) -> bool:
        return (
            isinstance(other, AggregatedBandProjection)
            and self.band_structure == other.band_structure
            and self.projection_state_digest == other.projection_state_digest
            and self.projection_source_digest == other.projection_source_digest
            and self.spin == other.spin
            and self.site_indices == other.site_indices
            and self.site_keys == other.site_keys
            and self.elements == other.elements
            and self.orbitals == other.orbitals
            and self.aggregation == other.aggregation
            and np.array_equal(self.weights, other.weights)
            and self.digest == other.digest
        )

    def __eq__(self, other: object) -> bool:
        return self.equals(other)


def aggregate_band_projection(
    state: BandProjectionState,
    *,
    spin: str,
    site_indices: Sequence[int],
    orbitals: Sequence[str],
) -> AggregatedBandProjection:
    """Sum only explicitly selected retained site/orbital projection weights."""
    if not isinstance(state, BandProjectionState):
        raise TypeError("state must be a BandProjectionState")
    channel = state.channel(spin)

    requested_sites = tuple(site_indices)
    if not requested_sites:
        raise BandProjectionError("site_indices must not be empty")
    if len(set(requested_sites)) != len(requested_sites):
        raise BandProjectionError("site_indices must not contain duplicates")
    if any(
        isinstance(index, bool)
        or not isinstance(index, int)
        or index < 0
        or index >= state.band_structure.structure.site_count
        for index in requested_sites
    ):
        raise BandProjectionError("site_indices contain an unknown source site")
    selected_site_set = set(requested_sites)
    canonical_sites = tuple(
        index
        for index in range(state.band_structure.structure.site_count)
        if index in selected_site_set
    )

    requested_orbitals = tuple(_nonblank(value, name="orbital") for value in orbitals)
    if not requested_orbitals:
        raise BandProjectionError("orbitals must not be empty")
    if len(set(requested_orbitals)) != len(requested_orbitals):
        raise BandProjectionError("orbitals must not contain duplicates")
    unknown = set(requested_orbitals) - set(state.orbitals)
    if unknown:
        raise BandProjectionError(
            "unknown source orbital label(s): " + ", ".join(sorted(unknown))
        )
    selected_orbital_set = set(requested_orbitals)
    canonical_orbitals = tuple(
        orbital for orbital in state.orbitals if orbital in selected_orbital_set
    )
    orbital_indices = tuple(state.orbitals.index(orbital) for orbital in canonical_orbitals)

    selected = channel.weights[:, :, canonical_sites, :]
    selected = selected[:, :, :, orbital_indices]
    aggregated = np.sum(selected, axis=(2, 3), dtype=np.float64)

    structure = state.band_structure.structure
    return AggregatedBandProjection(
        band_structure=state.band_structure,
        projection_state_digest=state.digest,
        projection_source_digest=state.source_digest,
        spin=channel.spin,
        site_indices=canonical_sites,
        site_keys=tuple(structure.site_keys[index] for index in canonical_sites),
        elements=tuple(structure.elements[index] for index in canonical_sites),
        orbitals=canonical_orbitals,
        weights=aggregated,
        aggregation="sum",
    )


__all__ = [
    "AggregatedBandProjection",
    "BandProjectionChannel",
    "BandProjectionError",
    "BandProjectionState",
    "aggregate_band_projection",
]
