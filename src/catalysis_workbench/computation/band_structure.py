"""Immutable band-structure state and explicit reciprocal-path processing."""

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

_ALLOWED_SPINS = frozenset({"total", "up", "down"})
_ALLOWED_REFERENCES = frozenset({"source-native", "fermi"})


class BandStructureError(ValueError):
    """Raised when retained band-structure state is scientifically inconsistent."""


def _nonblank(value: object, *, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise BandStructureError(f"{name} must not be blank")
    return text


def _optional_label(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value)
    return None if not text.strip() else text


def _finite_float(value: object | None, *, name: str) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a finite float or None") from exc
    if not np.isfinite(result):
        raise BandStructureError(f"{name} must be finite")
    return result


def _frozen_float_array(values: Any, *, name: str, ndim: int) -> NDArray[np.float64]:
    try:
        source = np.asarray(values)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must contain real numeric values") from exc
    if np.iscomplexobj(source):
        raise BandStructureError(f"{name} must contain real values")
    try:
        array = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must contain real numeric values") from exc
    if array.ndim != ndim or array.size == 0:
        raise BandStructureError(
            f"{name} must be a non-empty {ndim}-dimensional array"
        )
    if not np.isfinite(array).all():
        raise BandStructureError(f"{name} must contain only finite values")
    contiguous = np.ascontiguousarray(array, dtype=np.float64)
    frozen = np.frombuffer(contiguous.tobytes(order="C"), dtype=np.float64).reshape(
        contiguous.shape
    )
    frozen.setflags(write=False)
    return frozen


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


def _update_digest_string(digest: Any, value: str | None) -> None:
    if value is None:
        digest.update(b"\xff")
        return
    encoded = value.encode("utf-8")
    digest.update(len(encoded).to_bytes(8, "little", signed=False))
    digest.update(encoded)


@dataclass(frozen=True, slots=True)
class BandPathSegment:
    """One explicit inclusive source-index segment of a reciprocal-space path."""

    key: str
    start_index: int
    end_index: int
    start_label: str | None = None
    end_label: str | None = None

    def __post_init__(self) -> None:
        key = _nonblank(self.key, name="key")
        for value, name in (
            (self.start_index, "start_index"),
            (self.end_index, "end_index"),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise BandStructureError(f"{name} must be a non-negative integer")
        if self.end_index <= self.start_index:
            raise BandStructureError("end_index must be greater than start_index")
        object.__setattr__(self, "key", key)
        object.__setattr__(self, "start_label", _optional_label(self.start_label))
        object.__setattr__(self, "end_label", _optional_label(self.end_label))


@dataclass(frozen=True, slots=True, eq=False)
class BandEnergyChannel:
    """Exact band-energy matrix for one physical spin channel."""

    spin: str
    energies_ev: Any
    band_indices: Sequence[int]
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        spin = _nonblank(self.spin, name="spin").lower()
        if spin not in _ALLOWED_SPINS:
            raise BandStructureError(
                "spin must be one of: " + ", ".join(sorted(_ALLOWED_SPINS))
            )
        energies = _frozen_float_array(
            self.energies_ev,
            name="energies_ev",
            ndim=2,
        )
        indices = tuple(self.band_indices)
        if len(indices) != energies.shape[0]:
            raise BandStructureError(
                "band_indices length must match the number of retained bands"
            )
        if any(
            isinstance(index, bool) or not isinstance(index, int) or index < 0
            for index in indices
        ):
            raise BandStructureError(
                "band_indices must contain non-negative integer source indices"
            )
        if len(set(indices)) != len(indices):
            raise BandStructureError("band_indices must not contain duplicates")

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.BandEnergyChannel.v1\0")
        _update_digest_string(digest, spin)
        for index in indices:
            digest.update(index.to_bytes(8, "little", signed=False))
        digest.update(energies.tobytes(order="C"))

        object.__setattr__(self, "spin", spin)
        object.__setattr__(self, "energies_ev", energies)
        object.__setattr__(self, "band_indices", indices)
        object.__setattr__(self, "digest", digest.hexdigest())

    def equals(self, other: object) -> bool:
        return (
            isinstance(other, BandEnergyChannel)
            and self.spin == other.spin
            and self.band_indices == other.band_indices
            and np.array_equal(self.energies_ev, other.energies_ev)
            and self.digest == other.digest
        )

    def __eq__(self, other: object) -> bool:
        return self.equals(other)


@dataclass(frozen=True, slots=True, eq=False)
class BandStructureState:
    """Backend-neutral immutable ordinary band-structure state."""

    structure: AtomicStructure
    kpoints_fractional: Any
    reciprocal_lattice_cartesian: Any
    reciprocal_unit: str
    reciprocal_cartesian_includes_2pi: bool
    channels: Sequence[BandEnergyChannel]
    path_segments: Sequence[BandPathSegment]
    source_digest: str
    source_fermi_ev: float | None = None
    reference_kind: str = "source-native"
    applied_shift_ev: float = 0.0
    reciprocal_coordinate_convention: str = "fractional"
    metadata: Mapping[str, Any] = field(default_factory=dict)
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.structure, AtomicStructure):
            raise TypeError("structure must be an AtomicStructure")
        if self.structure.lattice_angstrom is None or self.structure.pbc != (
            True,
            True,
            True,
        ):
            raise BandStructureError(
                "band structure requires a fully periodic AtomicStructure"
            )
        kpoints = _frozen_float_array(
            self.kpoints_fractional,
            name="kpoints_fractional",
            ndim=2,
        )
        if kpoints.shape[1] != 3:
            raise BandStructureError("kpoints_fractional must have shape (n, 3)")
        reciprocal = _frozen_float_array(
            self.reciprocal_lattice_cartesian,
            name="reciprocal_lattice_cartesian",
            ndim=2,
        )
        if reciprocal.shape != (3, 3):
            raise BandStructureError(
                "reciprocal_lattice_cartesian must have shape (3, 3)"
            )
        determinant = float(np.linalg.det(reciprocal))
        if not np.isfinite(determinant) or abs(determinant) <= 1e-15:
            raise BandStructureError(
                "reciprocal_lattice_cartesian must be nonsingular"
            )
        reciprocal_unit = _nonblank(self.reciprocal_unit, name="reciprocal_unit")
        convention = _nonblank(
            self.reciprocal_coordinate_convention,
            name="reciprocal_coordinate_convention",
        ).lower()
        if convention != "fractional":
            raise BandStructureError(
                "v0.7 Block-3 state requires fractional reciprocal coordinates"
            )
        if not isinstance(self.reciprocal_cartesian_includes_2pi, bool):
            raise TypeError("reciprocal_cartesian_includes_2pi must be bool")

        channels = tuple(self.channels)
        if not channels or any(
            not isinstance(channel, BandEnergyChannel) for channel in channels
        ):
            raise BandStructureError(
                "channels must contain at least one BandEnergyChannel"
            )
        spin_set = {channel.spin for channel in channels}
        if spin_set not in ({"total"}, {"up", "down"}):
            raise BandStructureError(
                "physical band channels must be exactly total or the complete up/down pair"
            )
        if len(spin_set) != len(channels):
            raise BandStructureError("physical spin channels must not be duplicated")
        first_indices = channels[0].band_indices
        for channel in channels:
            if channel.energies_ev.shape[1] != kpoints.shape[0]:
                raise BandStructureError(
                    "every band-energy channel must match the retained k-point count"
                )
            if channel.band_indices != first_indices:
                raise BandStructureError(
                    "all physical spin channels must retain identical band index/order"
                )

        segments = tuple(self.path_segments)
        if any(not isinstance(segment, BandPathSegment) for segment in segments):
            raise TypeError("path_segments must contain BandPathSegment objects")
        keys: set[str] = set()
        previous: BandPathSegment | None = None
        for segment in segments:
            if segment.key in keys:
                raise BandStructureError("path segment keys must be unique")
            keys.add(segment.key)
            if segment.end_index >= kpoints.shape[0]:
                raise BandStructureError(
                    "path segment bounds exceed the retained k-point grid"
                )
            if previous is not None and segment.start_index < previous.end_index:
                raise BandStructureError(
                    "path segments must be ordered and non-overlapping except a shared endpoint"
                )
            previous = segment

        source_digest = _nonblank(self.source_digest, name="source_digest")
        fermi = _finite_float(self.source_fermi_ev, name="source_fermi_ev")
        reference = _nonblank(self.reference_kind, name="reference_kind").lower()
        if reference not in _ALLOWED_REFERENCES:
            raise BandStructureError(
                "reference_kind must be one of: "
                + ", ".join(sorted(_ALLOWED_REFERENCES))
            )
        shift = _finite_float(self.applied_shift_ev, name="applied_shift_ev")
        assert shift is not None
        if reference == "source-native" and shift != 0.0:
            raise BandStructureError(
                "source-native band state requires applied_shift_ev == 0"
            )
        if reference == "fermi":
            if fermi is None:
                raise BandStructureError(
                    "Fermi-referenced band state requires source_fermi_ev"
                )
            if not np.isclose(shift, -fermi, rtol=0.0, atol=1e-12):
                raise BandStructureError(
                    "Fermi-referenced band state requires applied_shift_ev == -source_fermi_ev"
                )

        frozen_metadata = _freeze_metadata(self.metadata)
        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.BandStructureState.v1\0")
        _update_digest_string(digest, self.structure.digest)
        digest.update(kpoints.tobytes(order="C"))
        digest.update(reciprocal.tobytes(order="C"))
        _update_digest_string(digest, reciprocal_unit)
        _update_digest_string(digest, convention)
        digest.update(b"\x01" if self.reciprocal_cartesian_includes_2pi else b"\x00")
        for channel in channels:
            _update_digest_string(digest, channel.digest)
        for segment in segments:
            _update_digest_string(digest, segment.key)
            digest.update(segment.start_index.to_bytes(8, "little", signed=False))
            digest.update(segment.end_index.to_bytes(8, "little", signed=False))
            _update_digest_string(digest, segment.start_label)
            _update_digest_string(digest, segment.end_label)
        _update_digest_string(digest, source_digest)
        _update_digest_string(digest, None if fermi is None else repr(fermi))
        _update_digest_string(digest, reference)
        _update_digest_string(digest, repr(shift))

        object.__setattr__(self, "kpoints_fractional", kpoints)
        object.__setattr__(self, "reciprocal_lattice_cartesian", reciprocal)
        object.__setattr__(self, "reciprocal_unit", reciprocal_unit)
        object.__setattr__(self, "reciprocal_coordinate_convention", convention)
        object.__setattr__(self, "channels", channels)
        object.__setattr__(self, "path_segments", segments)
        object.__setattr__(self, "source_digest", source_digest)
        object.__setattr__(self, "source_fermi_ev", fermi)
        object.__setattr__(self, "reference_kind", reference)
        object.__setattr__(self, "applied_shift_ev", shift)
        object.__setattr__(self, "metadata", frozen_metadata)
        object.__setattr__(self, "digest", digest.hexdigest())

    def channel(self, spin: str) -> BandEnergyChannel:
        token = _nonblank(spin, name="spin").lower()
        for channel in self.channels:
            if channel.spin == token:
                return channel
        raise BandStructureError(f"band state does not contain physical spin {token!r}")

    def equals(self, other: object) -> bool:
        return (
            isinstance(other, BandStructureState)
            and self.structure == other.structure
            and np.array_equal(self.kpoints_fractional, other.kpoints_fractional)
            and np.array_equal(
                self.reciprocal_lattice_cartesian,
                other.reciprocal_lattice_cartesian,
            )
            and self.reciprocal_unit == other.reciprocal_unit
            and self.reciprocal_coordinate_convention
            == other.reciprocal_coordinate_convention
            and self.reciprocal_cartesian_includes_2pi
            == other.reciprocal_cartesian_includes_2pi
            and self.channels == other.channels
            and self.path_segments == other.path_segments
            and self.source_digest == other.source_digest
            and self.source_fermi_ev == other.source_fermi_ev
            and self.reference_kind == other.reference_kind
            and self.applied_shift_ev == other.applied_shift_ev
            and self.digest == other.digest
        )

    def __eq__(self, other: object) -> bool:
        return self.equals(other)


@dataclass(frozen=True, slots=True, eq=False)
class BandPathDistanceSegment:
    """Cumulative plotting coordinates for one explicit path segment."""

    key: str
    source_indices: Sequence[int]
    distances: Any
    start_label: str | None
    end_label: str | None
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        key = _nonblank(self.key, name="key")
        indices = tuple(self.source_indices)
        if len(indices) < 2 or any(
            isinstance(index, bool) or not isinstance(index, int) or index < 0
            for index in indices
        ):
            raise BandStructureError(
                "source_indices must contain at least two non-negative integers"
            )
        distances = _frozen_float_array(self.distances, name="distances", ndim=1)
        if distances.size != len(indices):
            raise BandStructureError(
                "distances length must match source_indices length"
            )
        if np.any(np.diff(distances) < 0.0):
            raise BandStructureError("band path distances must be non-decreasing")

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.BandPathDistanceSegment.v1\0")
        _update_digest_string(digest, key)
        for index in indices:
            digest.update(index.to_bytes(8, "little", signed=False))
        digest.update(distances.tobytes(order="C"))
        _update_digest_string(digest, _optional_label(self.start_label))
        _update_digest_string(digest, _optional_label(self.end_label))

        object.__setattr__(self, "key", key)
        object.__setattr__(self, "source_indices", indices)
        object.__setattr__(self, "distances", distances)
        object.__setattr__(self, "start_label", _optional_label(self.start_label))
        object.__setattr__(self, "end_label", _optional_label(self.end_label))
        object.__setattr__(self, "digest", digest.hexdigest())

    def equals(self, other: object) -> bool:
        return (
            isinstance(other, BandPathDistanceSegment)
            and self.key == other.key
            and self.source_indices == other.source_indices
            and np.array_equal(self.distances, other.distances)
            and self.start_label == other.start_label
            and self.end_label == other.end_label
            and self.digest == other.digest
        )

    def __eq__(self, other: object) -> bool:
        return self.equals(other)


@dataclass(frozen=True, slots=True, eq=False)
class BandPathCoordinates:
    """Derived path-distance state retaining reciprocal-space convention."""

    segments: Sequence[BandPathDistanceSegment]
    reciprocal_unit: str
    reciprocal_cartesian_includes_2pi: bool
    source_band_digest: str
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        segments = tuple(self.segments)
        if not segments or any(
            not isinstance(segment, BandPathDistanceSegment) for segment in segments
        ):
            raise BandStructureError(
                "segments must contain at least one BandPathDistanceSegment"
            )
        unit = _nonblank(self.reciprocal_unit, name="reciprocal_unit")
        if not isinstance(self.reciprocal_cartesian_includes_2pi, bool):
            raise TypeError("reciprocal_cartesian_includes_2pi must be bool")
        source_digest = _nonblank(
            self.source_band_digest,
            name="source_band_digest",
        )

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.BandPathCoordinates.v1\0")
        for segment in segments:
            _update_digest_string(digest, segment.digest)
        _update_digest_string(digest, unit)
        digest.update(b"\x01" if self.reciprocal_cartesian_includes_2pi else b"\x00")
        _update_digest_string(digest, source_digest)

        object.__setattr__(self, "segments", segments)
        object.__setattr__(self, "reciprocal_unit", unit)
        object.__setattr__(self, "source_band_digest", source_digest)
        object.__setattr__(self, "digest", digest.hexdigest())

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, BandPathCoordinates)
            and self.segments == other.segments
            and self.reciprocal_unit == other.reciprocal_unit
            and self.reciprocal_cartesian_includes_2pi
            == other.reciprocal_cartesian_includes_2pi
            and self.source_band_digest == other.source_band_digest
            and self.digest == other.digest
        )


def band_path_coordinates(state: BandStructureState) -> BandPathCoordinates:
    """Derive segment-separated cumulative path distance without `2*pi` repair."""
    if not isinstance(state, BandStructureState):
        raise TypeError("state must be a BandStructureState")
    if not state.path_segments:
        raise BandStructureError(
            "band path coordinates require explicit retained path segments"
        )

    offset = 0.0
    retained: list[BandPathDistanceSegment] = []
    reciprocal = np.asarray(state.reciprocal_lattice_cartesian, dtype=np.float64)
    for segment in state.path_segments:
        indices = tuple(range(segment.start_index, segment.end_index + 1))
        fractional = np.asarray(state.kpoints_fractional[list(indices)], dtype=np.float64)
        delta_fractional = np.diff(fractional, axis=0)
        delta_cartesian = delta_fractional @ reciprocal
        step = np.linalg.norm(delta_cartesian, axis=1)
        local = np.concatenate(([0.0], np.cumsum(step)))
        distances = local + offset
        retained.append(
            BandPathDistanceSegment(
                key=segment.key,
                source_indices=indices,
                distances=distances,
                start_label=segment.start_label,
                end_label=segment.end_label,
            )
        )
        offset = float(distances[-1])

    return BandPathCoordinates(
        segments=retained,
        reciprocal_unit=state.reciprocal_unit,
        reciprocal_cartesian_includes_2pi=state.reciprocal_cartesian_includes_2pi,
        source_band_digest=state.digest,
    )


def reference_band_structure_to_fermi(
    state: BandStructureState,
) -> BandStructureState:
    """Return an explicit `E - E_F` band state without hidden alignment."""
    if not isinstance(state, BandStructureState):
        raise TypeError("state must be a BandStructureState")
    if state.reference_kind == "fermi":
        return state
    if state.source_fermi_ev is None:
        raise BandStructureError(
            "Fermi referencing requires retained source_fermi_ev"
        )
    shift = -float(state.source_fermi_ev)
    channels = tuple(
        BandEnergyChannel(
            spin=channel.spin,
            energies_ev=np.asarray(channel.energies_ev) + shift,
            band_indices=channel.band_indices,
        )
        for channel in state.channels
    )
    metadata = dict(state.metadata)
    metadata["reference_source_state_digest"] = state.digest
    metadata["reference_transform"] = "E_source - E_F"
    return BandStructureState(
        structure=state.structure,
        kpoints_fractional=state.kpoints_fractional,
        reciprocal_lattice_cartesian=state.reciprocal_lattice_cartesian,
        reciprocal_unit=state.reciprocal_unit,
        reciprocal_cartesian_includes_2pi=state.reciprocal_cartesian_includes_2pi,
        channels=channels,
        path_segments=state.path_segments,
        source_digest=state.source_digest,
        source_fermi_ev=state.source_fermi_ev,
        reference_kind="fermi",
        applied_shift_ev=shift,
        reciprocal_coordinate_convention=state.reciprocal_coordinate_convention,
        metadata=metadata,
    )


__all__ = [
    "BandEnergyChannel",
    "BandPathCoordinates",
    "BandPathDistanceSegment",
    "BandPathSegment",
    "BandStructureError",
    "BandStructureState",
    "band_path_coordinates",
    "reference_band_structure_to_fermi",
]
