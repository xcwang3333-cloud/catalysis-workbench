"""Explicit immutable DOS/PDOS processing on CatalysisWorkbench electronic state."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from .electronic_structure import DOSChannel, ElectronicDOS, ElectronicEnergyAxis

_ALLOWED_SPINS = frozenset({"total", "up", "down"})
_ALLOWED_PROJECTION_KINDS = frozenset({"total", "site-orbital"})


class DOSProcessingError(ValueError):
    """Raised when a requested DOS operation is scientifically incompatible."""


def _required_text(value: str, *, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise DOSProcessingError(f"{name} must not be blank")
    return text


def _frozen_float_array(values: object, *, name: str) -> NDArray[np.float64]:
    try:
        source = np.asarray(values)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must contain real numeric values") from exc
    if np.iscomplexobj(source):
        raise DOSProcessingError(f"{name} must contain real values")
    try:
        array = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must contain real numeric values") from exc
    if array.ndim != 1 or array.size < 2:
        raise DOSProcessingError(f"{name} must be a one-dimensional array with >=2 points")
    if not np.isfinite(array).all():
        raise DOSProcessingError(f"{name} must contain only finite values")
    contiguous = np.ascontiguousarray(array, dtype=np.float64)
    frozen = np.frombuffer(contiguous.tobytes(order="C"), dtype=np.float64)
    frozen.setflags(write=False)
    return frozen


def _digest_text(digest: object, value: str) -> None:
    encoded = value.encode("utf-8")
    digest.update(len(encoded).to_bytes(8, "little", signed=False))
    digest.update(encoded)


def _optional_text_filter(
    values: Sequence[str] | None,
    *,
    name: str,
    lower: bool = False,
) -> frozenset[str] | None:
    if values is None:
        return None
    retained = tuple(_required_text(value, name=name) for value in values)
    if not retained:
        raise DOSProcessingError(f"{name} must not be empty when supplied")
    if lower:
        retained = tuple(value.lower() for value in retained)
    return frozenset(retained)


def _optional_index_filter(values: Sequence[int] | None) -> frozenset[int] | None:
    if values is None:
        return None
    retained = tuple(values)
    if not retained:
        raise DOSProcessingError("site_indices must not be empty when supplied")
    for value in retained:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise DOSProcessingError("site_indices must contain non-negative integers")
    return frozenset(retained)


@dataclass(frozen=True, slots=True, eq=False)
class DOSTrace:
    """One immutable processed DOS trace with explicit source-channel provenance."""

    key: str
    energy: ElectronicEnergyAxis
    density: object
    source_dos_digest: str
    source_channel_digests: Sequence[str]
    source_projection_keys: Sequence[str]
    source_spins: Sequence[str]
    density_unit: str
    normalization_basis: str
    operations: Sequence[str]
    label: str = ""
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        key = _required_text(self.key, name="key")
        if not isinstance(self.energy, ElectronicEnergyAxis):
            raise TypeError("energy must be an ElectronicEnergyAxis")
        density = _frozen_float_array(self.density, name="density")
        if density.size != self.energy.values_ev.size:
            raise DOSProcessingError("density length must match the retained energy axis")
        if np.any(density < 0):
            raise DOSProcessingError(
                "scientific DOS density must remain non-negative; mirroring is display-only"
            )

        source_digest = _required_text(self.source_dos_digest, name="source_dos_digest")
        channel_digests = tuple(
            _required_text(value, name="source_channel_digest")
            for value in self.source_channel_digests
        )
        projection_keys = tuple(
            _required_text(value, name="source_projection_key")
            for value in self.source_projection_keys
        )
        spins = tuple(
            _required_text(value, name="source_spin").lower()
            for value in self.source_spins
        )
        operations = tuple(_required_text(value, name="operation") for value in self.operations)
        if not channel_digests or not operations:
            raise DOSProcessingError("source channels and operation history must not be empty")
        if not (len(channel_digests) == len(projection_keys) == len(spins)):
            raise DOSProcessingError("source channel/projection/spin provenance must align")
        if len(channel_digests) != len(set(channel_digests)):
            raise DOSProcessingError("source channel digests must be unique")
        if any(spin not in _ALLOWED_SPINS for spin in spins):
            raise DOSProcessingError("source spins must be total, up, or down")

        density_unit = _required_text(self.density_unit, name="density_unit")
        normalization = _required_text(
            self.normalization_basis,
            name="normalization_basis",
        )
        label = str(self.label).strip()

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.DOSTrace.v1\0")
        _digest_text(digest, self.energy.digest)
        _digest_text(digest, source_digest)
        _digest_text(digest, density_unit)
        _digest_text(digest, normalization)
        for values in (channel_digests, projection_keys, spins, operations):
            for value in values:
                _digest_text(digest, value)
            digest.update(b"\0")
        digest.update(density.tobytes(order="C"))

        object.__setattr__(self, "key", key)
        object.__setattr__(self, "density", density)
        object.__setattr__(self, "source_dos_digest", source_digest)
        object.__setattr__(self, "source_channel_digests", channel_digests)
        object.__setattr__(self, "source_projection_keys", projection_keys)
        object.__setattr__(self, "source_spins", spins)
        object.__setattr__(self, "density_unit", density_unit)
        object.__setattr__(self, "normalization_basis", normalization)
        object.__setattr__(self, "operations", operations)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "digest", digest.hexdigest())

    def equals(self, other: object) -> bool:
        return (
            isinstance(other, DOSTrace)
            and self.key == other.key
            and self.label == other.label
            and self.energy == other.energy
            and np.array_equal(self.density, other.density)
            and self.source_dos_digest == other.source_dos_digest
            and self.source_channel_digests == other.source_channel_digests
            and self.source_projection_keys == other.source_projection_keys
            and self.source_spins == other.source_spins
            and self.density_unit == other.density_unit
            and self.normalization_basis == other.normalization_basis
            and self.operations == other.operations
            and self.digest == other.digest
        )

    def __eq__(self, other: object) -> bool:
        return self.equals(other)


def select_dos_channels(
    dos: ElectronicDOS,
    *,
    projection_keys: Sequence[str] | None = None,
    projection_kind: str | None = None,
    site_indices: Sequence[int] | None = None,
    site_keys: Sequence[str] | None = None,
    elements: Sequence[str] | None = None,
    orbitals: Sequence[str] | None = None,
    spins: Sequence[str] | None = None,
) -> tuple[DOSChannel, ...]:
    """Select source channels by explicit retained semantic fields, preserving source order."""
    if not isinstance(dos, ElectronicDOS):
        raise TypeError("dos must be an ElectronicDOS")

    keys = _optional_text_filter(projection_keys, name="projection_key")
    sites = _optional_index_filter(site_indices)
    stable_sites = _optional_text_filter(site_keys, name="site_key")
    element_set = _optional_text_filter(elements, name="element")
    orbital_set = _optional_text_filter(orbitals, name="orbital")
    spin_set = _optional_text_filter(spins, name="spin", lower=True)
    if spin_set is not None and not spin_set.issubset(_ALLOWED_SPINS):
        raise DOSProcessingError("spins must contain only total, up, or down")

    kind = None
    if projection_kind is not None:
        kind = _required_text(projection_kind, name="projection_kind").lower()
        if kind not in _ALLOWED_PROJECTION_KINDS:
            raise DOSProcessingError("projection_kind must be total or site-orbital")

    selected: list[DOSChannel] = []
    for channel in dos.channels:
        projection = channel.projection
        if keys is not None and projection.key not in keys:
            continue
        if kind is not None and projection.kind != kind:
            continue
        if sites is not None and projection.site_index not in sites:
            continue
        if stable_sites is not None and projection.site_key not in stable_sites:
            continue
        if element_set is not None and projection.element not in element_set:
            continue
        if orbital_set is not None and projection.orbital not in orbital_set:
            continue
        if spin_set is not None and channel.spin not in spin_set:
            continue
        selected.append(channel)

    if not selected:
        raise DOSProcessingError("DOS selector matched no retained source channels")
    return tuple(selected)


def _trace_from_channels(
    dos: ElectronicDOS,
    channels: Sequence[DOSChannel],
    *,
    key: str,
    label: str,
    operation: str,
) -> DOSTrace:
    retained = tuple(channels)
    if not retained:
        raise DOSProcessingError("at least one source DOS channel is required")
    if not all(isinstance(channel, DOSChannel) for channel in retained):
        raise TypeError("channels must contain only DOSChannel instances")
    requested_digests = tuple(channel.digest for channel in retained)
    if len(set(requested_digests)) != len(retained):
        raise DOSProcessingError("the same source DOS channel cannot be included twice")

    available = {channel.digest for channel in dos.channels}
    if any(digest not in available for digest in requested_digests):
        raise DOSProcessingError("all selected channels must belong to the supplied ElectronicDOS")
    requested = frozenset(requested_digests)
    retained = tuple(channel for channel in dos.channels if channel.digest in requested)

    units = {channel.density_unit for channel in retained}
    normalizations = {channel.normalization_basis for channel in retained}
    if len(units) != 1 or len(normalizations) != 1:
        raise DOSProcessingError(
            "DOS aggregation requires matching density units and normalization bases"
        )
    density = np.sum(
        np.stack([channel.density for channel in retained], axis=0),
        axis=0,
        dtype=np.float64,
    )
    return DOSTrace(
        key=key,
        label=label,
        energy=dos.energy,
        density=density,
        source_dos_digest=dos.digest,
        source_channel_digests=tuple(channel.digest for channel in retained),
        source_projection_keys=tuple(channel.projection.key for channel in retained),
        source_spins=tuple(channel.spin for channel in retained),
        density_unit=retained[0].density_unit,
        normalization_basis=retained[0].normalization_basis,
        operations=(operation,),
    )


def dos_channel_trace(
    dos: ElectronicDOS,
    *,
    projection_key: str,
    spin: str,
    key: str | None = None,
    label: str | None = None,
) -> DOSTrace:
    """Construct a retained trace from one exact projection-key/spin channel."""
    projection = _required_text(projection_key, name="projection_key")
    physical_spin = _required_text(spin, name="spin").lower()
    channels = select_dos_channels(
        dos,
        projection_keys=(projection,),
        spins=(physical_spin,),
    )
    if len(channels) != 1:
        raise DOSProcessingError("exact projection-key/spin selection must identify one channel")
    trace_key = key or f"{projection}:{physical_spin}"
    trace_label = label if label is not None else trace_key
    return _trace_from_channels(
        dos,
        channels,
        key=trace_key,
        label=trace_label,
        operation="select-channel",
    )


def aggregate_dos(
    dos: ElectronicDOS,
    channels: Sequence[DOSChannel],
    *,
    key: str,
    label: str = "",
) -> DOSTrace:
    """Explicitly sum compatible retained DOS channels without hidden grouping."""
    if not isinstance(dos, ElectronicDOS):
        raise TypeError("dos must be an ElectronicDOS")
    return _trace_from_channels(
        dos,
        channels,
        key=key,
        label=label or key,
        operation="aggregate-sum",
    )


def reference_dos_to_fermi(trace: DOSTrace) -> DOSTrace:
    """Return an explicit ``E - E_F`` trace, shifting the retained axis exactly once."""
    if not isinstance(trace, DOSTrace):
        raise TypeError("trace must be a DOSTrace")
    energy = trace.energy
    if energy.source_fermi_ev is None:
        raise DOSProcessingError("Fermi referencing requires a retained source_fermi_ev")

    target_shift = -energy.source_fermi_ev
    if energy.reference_kind == "fermi":
        if not np.isclose(energy.applied_shift_ev, target_shift, rtol=0.0, atol=1e-12):
            raise DOSProcessingError("retained Fermi-referenced axis has inconsistent shift state")
        return trace
    if energy.reference_kind != "source-native":
        raise DOSProcessingError(
            "Fermi referencing currently requires source-native or already-Fermi state"
        )

    delta = target_shift - energy.applied_shift_ev
    referenced = ElectronicEnergyAxis(
        energy.values_ev + delta,
        reference_kind="fermi",
        source_fermi_ev=energy.source_fermi_ev,
        applied_shift_ev=target_shift,
    )
    return DOSTrace(
        key=trace.key,
        label=trace.label,
        energy=referenced,
        density=trace.density,
        source_dos_digest=trace.source_dos_digest,
        source_channel_digests=trace.source_channel_digests,
        source_projection_keys=trace.source_projection_keys,
        source_spins=trace.source_spins,
        density_unit=trace.density_unit,
        normalization_basis=trace.normalization_basis,
        operations=(*trace.operations, "reference:fermi"),
    )


def crop_dos_trace(trace: DOSTrace, energy_min_ev: float, energy_max_ev: float) -> DOSTrace:
    """Crop to retained points inside an inclusive energy window without interpolation."""
    if not isinstance(trace, DOSTrace):
        raise TypeError("trace must be a DOSTrace")
    try:
        low = float(energy_min_ev)
        high = float(energy_max_ev)
    except (TypeError, ValueError) as exc:
        raise TypeError("energy window limits must be finite floats") from exc
    if not np.isfinite(low) or not np.isfinite(high) or low >= high:
        raise DOSProcessingError("energy window requires finite energy_min_ev < energy_max_ev")

    mask = (trace.energy.values_ev >= low) & (trace.energy.values_ev <= high)
    if int(np.count_nonzero(mask)) < 2:
        raise DOSProcessingError("energy window must retain at least two source-grid points")
    cropped_energy = ElectronicEnergyAxis(
        trace.energy.values_ev[mask],
        reference_kind=trace.energy.reference_kind,
        source_fermi_ev=trace.energy.source_fermi_ev,
        applied_shift_ev=trace.energy.applied_shift_ev,
    )
    return DOSTrace(
        key=trace.key,
        label=trace.label,
        energy=cropped_energy,
        density=trace.density[mask],
        source_dos_digest=trace.source_dos_digest,
        source_channel_digests=trace.source_channel_digests,
        source_projection_keys=trace.source_projection_keys,
        source_spins=trace.source_spins,
        density_unit=trace.density_unit,
        normalization_basis=trace.normalization_basis,
        operations=(*trace.operations, f"crop:[{low!r},{high!r}]"),
    )


def dos_trace_frame(trace: DOSTrace) -> pd.DataFrame:
    """Return a detached point-wise reporting table for one retained DOS trace."""
    if not isinstance(trace, DOSTrace):
        raise TypeError("trace must be a DOSTrace")
    return pd.DataFrame.from_records(
        [
            {
                "trace_key": trace.key,
                "trace_label": trace.label,
                "trace_digest": trace.digest,
                "source_dos_digest": trace.source_dos_digest,
                "source_projection_keys": tuple(trace.source_projection_keys),
                "source_spins": tuple(trace.source_spins),
                "energy_reference": trace.energy.reference_kind,
                "source_fermi_ev": trace.energy.source_fermi_ev,
                "applied_shift_ev": trace.energy.applied_shift_ev,
                "energy_ev": energy,
                "density": density,
                "density_unit": trace.density_unit,
                "normalization_basis": trace.normalization_basis,
                "operations": tuple(trace.operations),
            }
            for energy, density in zip(
                trace.energy.values_ev,
                trace.density,
                strict=True,
            )
        ]
    )


__all__ = [
    "DOSProcessingError",
    "DOSTrace",
    "aggregate_dos",
    "crop_dos_trace",
    "dos_channel_trace",
    "dos_trace_frame",
    "reference_dos_to_fermi",
    "select_dos_channels",
]
