"""Immutable COHP/ICOHP scientific state with explicit source semantics."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from .electronic_structure import ElectronicEnergyAxis

_ALLOWED_SPINS = frozenset({"total", "up", "down"})


class BondingError(ValueError):
    """Raised when COHP/ICOHP bonding state is scientifically inconsistent."""


def _required_text(value: object, *, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise BondingError(f"{name} must not be blank")
    return text


def _optional_text(value: object | None, *, name: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, name=name)


def _finite_float(value: object, *, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a finite float") from exc
    if not np.isfinite(number):
        raise BondingError(f"{name} must be finite")
    return number


def _optional_positive_float(value: object | None, *, name: str) -> float | None:
    if value is None:
        return None
    number = _finite_float(value, name=name)
    if number <= 0:
        raise BondingError(f"{name} must be greater than zero")
    return number


def _positive_int(value: object, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{name} must be an integer")
    integer = int(value)
    if integer <= 0:
        raise BondingError(f"{name} must be greater than zero")
    return integer


def _spin(value: object) -> str:
    text = _required_text(value, name="spin").lower()
    if text not in _ALLOWED_SPINS:
        raise BondingError("spin must be one of: total, up, down")
    return text


def _frozen_array(values: object, *, name: str) -> NDArray[np.float64]:
    try:
        source = np.asarray(values)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must contain real numeric values") from exc
    if np.iscomplexobj(source):
        raise BondingError(f"{name} must contain real values")
    try:
        array = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must contain real numeric values") from exc
    if array.ndim != 1 or array.size == 0 or not np.isfinite(array).all():
        raise BondingError(f"{name} must be a non-empty finite one-dimensional array")
    contiguous = np.ascontiguousarray(array, dtype=np.float64)
    frozen = np.frombuffer(contiguous.tobytes(order="C"), dtype=np.float64)
    frozen.setflags(write=False)
    return frozen


def _site_indices(values: Sequence[int] | None) -> tuple[int, ...]:
    if values is None:
        return ()
    result: list[int] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
            raise TypeError("source_site_indices must contain integers")
        integer = int(value)
        if integer < 0:
            raise BondingError("source_site_indices must be non-negative")
        result.append(integer)
    if result and len(result) != 2:
        raise BondingError("source_site_indices must contain exactly two sites when supplied")
    return tuple(result)


def _orbital_descriptors(values: Sequence[object] | None) -> tuple[str, ...]:
    if values is None:
        return ()
    result = tuple(_required_text(value, name="orbital descriptor") for value in values)
    return result


def _digest_text(digest: object, value: str | None) -> None:
    if value is None:
        digest.update(b"none\0")
        return
    encoded = value.encode("utf-8")
    digest.update(len(encoded).to_bytes(8, "little", signed=False))
    digest.update(encoded)


def _digest_float(digest: object, value: float | None) -> None:
    if value is None:
        digest.update(b"none\0")
    else:
        digest.update(b"value\0")
        digest.update(np.float64(value).tobytes())


@dataclass(frozen=True, slots=True, eq=False)
class COHPChannel:
    """One physical-spin COHP channel for a concrete LOBSTER bond/orbital identity."""

    key: str
    bond_key: str
    source_label: str
    spin: str
    cohp: object
    integrated_cohp: object
    bond_length_angstrom: float | None = None
    source_site_indices: Sequence[int] | None = None
    orbital_key: str | None = None
    orbital_label: str | None = None
    orbital_descriptors: Sequence[object] | None = None
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        key = _required_text(self.key, name="key")
        bond_key = _required_text(self.bond_key, name="bond_key")
        label = _required_text(self.source_label, name="source_label")
        spin = _spin(self.spin)
        cohp = _frozen_array(self.cohp, name="cohp")
        integrated = _frozen_array(self.integrated_cohp, name="integrated_cohp")
        if cohp.shape != integrated.shape:
            raise BondingError("cohp and integrated_cohp must have identical shapes")
        length = _optional_positive_float(
            self.bond_length_angstrom,
            name="bond_length_angstrom",
        )
        sites = _site_indices(self.source_site_indices)
        orbital_key = _optional_text(self.orbital_key, name="orbital_key")
        orbital_label = _optional_text(self.orbital_label, name="orbital_label")
        descriptors = _orbital_descriptors(self.orbital_descriptors)
        orbital_fields = (orbital_key is not None, orbital_label is not None, bool(descriptors))
        if any(orbital_fields) and not all(orbital_fields):
            raise BondingError(
                "orbital_key, orbital_label and orbital_descriptors must be supplied together"
            )

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.COHPChannel.v1\0")
        for value in (key, bond_key, label, spin, orbital_key, orbital_label):
            _digest_text(digest, value)
        _digest_float(digest, length)
        for index in sites:
            digest.update(index.to_bytes(8, "little", signed=False))
        for descriptor in descriptors:
            _digest_text(digest, descriptor)
        digest.update(cohp.tobytes(order="C"))
        digest.update(integrated.tobytes(order="C"))

        object.__setattr__(self, "key", key)
        object.__setattr__(self, "bond_key", bond_key)
        object.__setattr__(self, "source_label", label)
        object.__setattr__(self, "spin", spin)
        object.__setattr__(self, "cohp", cohp)
        object.__setattr__(self, "integrated_cohp", integrated)
        object.__setattr__(self, "bond_length_angstrom", length)
        object.__setattr__(self, "source_site_indices", sites)
        object.__setattr__(self, "orbital_key", orbital_key)
        object.__setattr__(self, "orbital_label", orbital_label)
        object.__setattr__(self, "orbital_descriptors", descriptors)
        object.__setattr__(self, "digest", digest.hexdigest())

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, COHPChannel)
            and self.digest == other.digest
            and np.array_equal(self.cohp, other.cohp)
            and np.array_equal(self.integrated_cohp, other.integrated_cohp)
        )


@dataclass(frozen=True, slots=True, eq=False)
class COHPResult:
    """Immutable concrete-bond COHP state on one already-Fermi-referenced energy grid."""

    energy: ElectronicEnergyAxis
    channels: Sequence[COHPChannel]
    producer_fermi_ev: float | None = None
    source_format: str = "COHPCAR.lobster"
    source_path: str | None = None
    source_id: str | None = None
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.energy, ElectronicEnergyAxis):
            raise TypeError("energy must be an ElectronicEnergyAxis")
        if self.energy.reference_kind != "fermi" or self.energy.source_fermi_ev != 0.0:
            raise BondingError(
                "LOBSTER COHP energy must be retained as already Fermi-referenced with zero at E_F"
            )
        channels = tuple(self.channels)
        if not channels or not all(isinstance(channel, COHPChannel) for channel in channels):
            raise BondingError("channels must contain at least one COHPChannel")
        keys = tuple(channel.key for channel in channels)
        if len(set(keys)) != len(keys):
            raise BondingError("COHP channel keys must be unique")
        for channel in channels:
            if channel.cohp.size != self.energy.values_ev.size:
                raise BondingError("COHP channel arrays must align exactly with the energy grid")
        producer_fermi = None
        if self.producer_fermi_ev is not None:
            producer_fermi = _finite_float(self.producer_fermi_ev, name="producer_fermi_ev")
        source_format = _required_text(self.source_format, name="source_format")
        source_path = _optional_text(self.source_path, name="source_path")
        source_id = _optional_text(self.source_id, name="source_id")

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.COHPResult.v1\0")
        _digest_text(digest, self.energy.digest)
        _digest_float(digest, producer_fermi)
        _digest_text(digest, source_format)
        for channel in channels:
            _digest_text(digest, channel.digest)

        object.__setattr__(self, "channels", channels)
        object.__setattr__(self, "producer_fermi_ev", producer_fermi)
        object.__setattr__(self, "source_format", source_format)
        object.__setattr__(self, "source_path", source_path)
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "digest", digest.hexdigest())

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, COHPResult)
            and self.energy == other.energy
            and self.channels == other.channels
            and self.producer_fermi_ev == other.producer_fermi_ev
            and self.source_format == other.source_format
            and self.source_path == other.source_path
            and self.source_id == other.source_id
            and self.digest == other.digest
        )


@dataclass(frozen=True, slots=True, eq=False)
class ICOHPBondSummary:
    """One source-sign ICOHP(E_F) bond summary with explicit spin values."""

    bond_key: str
    source_label: str
    bond_length_angstrom: float
    number_of_bonds: int
    icohp_by_spin: Mapping[str, float]
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        bond_key = _required_text(self.bond_key, name="bond_key")
        label = _required_text(self.source_label, name="source_label")
        length = _optional_positive_float(
            self.bond_length_angstrom,
            name="bond_length_angstrom",
        )
        assert length is not None
        number_of_bonds = _positive_int(self.number_of_bonds, name="number_of_bonds")
        try:
            source_items = tuple(dict(self.icohp_by_spin).items())
        except (TypeError, ValueError) as exc:
            raise TypeError("icohp_by_spin must be mapping-like") from exc
        if not source_items:
            raise BondingError("icohp_by_spin must not be empty")
        parsed: dict[str, float] = {}
        for raw_spin, raw_value in source_items:
            spin = _spin(raw_spin)
            if spin in parsed:
                raise BondingError("icohp_by_spin contains duplicate spin identities")
            parsed[spin] = _finite_float(raw_value, name=f"icohp_by_spin[{spin}]")
        if "total" in parsed and len(parsed) != 1:
            raise BondingError("physical total cannot coexist with up/down ICOHP values")
        if "total" not in parsed and set(parsed) != {"up", "down"}:
            raise BondingError("spin-polarized ICOHP state must contain both up and down")
        ordered_keys = ("total",) if "total" in parsed else ("up", "down")
        frozen_map = MappingProxyType({key: parsed[key] for key in ordered_keys})

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.ICOHPBondSummary.v1\0")
        for value in (bond_key, label):
            _digest_text(digest, value)
        _digest_float(digest, length)
        digest.update(number_of_bonds.to_bytes(8, "little", signed=False))
        for spin in ordered_keys:
            _digest_text(digest, spin)
            _digest_float(digest, parsed[spin])

        object.__setattr__(self, "bond_key", bond_key)
        object.__setattr__(self, "source_label", label)
        object.__setattr__(self, "bond_length_angstrom", length)
        object.__setattr__(self, "number_of_bonds", number_of_bonds)
        object.__setattr__(self, "icohp_by_spin", frozen_map)
        object.__setattr__(self, "digest", digest.hexdigest())

    @property
    def spins(self) -> tuple[str, ...]:
        return tuple(self.icohp_by_spin)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ICOHPBondSummary) and self.digest == other.digest


@dataclass(frozen=True, slots=True, eq=False)
class ICOHPResult:
    """Immutable list of source-sign ICOHP(E_F) bond summaries."""

    bonds: Sequence[ICOHPBondSummary]
    source_format: str = "ICOHPLIST.lobster"
    source_path: str | None = None
    source_id: str | None = None
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        bonds = tuple(self.bonds)
        if not bonds or not all(isinstance(bond, ICOHPBondSummary) for bond in bonds):
            raise BondingError("bonds must contain at least one ICOHPBondSummary")
        keys = tuple(bond.bond_key for bond in bonds)
        labels = tuple(bond.source_label for bond in bonds)
        if len(set(keys)) != len(keys) or len(set(labels)) != len(labels):
            raise BondingError("ICOHP bond keys and source labels must be unique")
        source_format = _required_text(self.source_format, name="source_format")
        source_path = _optional_text(self.source_path, name="source_path")
        source_id = _optional_text(self.source_id, name="source_id")

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.ICOHPResult.v1\0")
        _digest_text(digest, source_format)
        for bond in bonds:
            _digest_text(digest, bond.digest)

        object.__setattr__(self, "bonds", bonds)
        object.__setattr__(self, "source_format", source_format)
        object.__setattr__(self, "source_path", source_path)
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "digest", digest.hexdigest())

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, ICOHPResult)
            and self.bonds == other.bonds
            and self.source_format == other.source_format
            and self.source_path == other.source_path
            and self.source_id == other.source_id
            and self.digest == other.digest
        )


@dataclass(frozen=True, slots=True)
class ICOHPSpinSum:
    """Explicit source-sign sum of selected physical ICOHP(E_F) spin channels."""

    bond_key: str
    source_label: str
    contributing_spins: Sequence[str]
    value: float
    source_summary_digest: str
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        bond_key = _required_text(self.bond_key, name="bond_key")
        label = _required_text(self.source_label, name="source_label")
        spins = tuple(_spin(spin) for spin in self.contributing_spins)
        if not spins or len(set(spins)) != len(spins):
            raise BondingError("contributing_spins must be a non-empty unique sequence")
        value = _finite_float(self.value, name="value")
        source_digest = _required_text(
            self.source_summary_digest,
            name="source_summary_digest",
        )
        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.ICOHPSpinSum.v1\0")
        for text in (bond_key, label, source_digest):
            _digest_text(digest, text)
        for spin in spins:
            _digest_text(digest, spin)
        _digest_float(digest, value)
        object.__setattr__(self, "bond_key", bond_key)
        object.__setattr__(self, "source_label", label)
        object.__setattr__(self, "contributing_spins", spins)
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "source_summary_digest", source_digest)
        object.__setattr__(self, "digest", digest.hexdigest())


def select_cohp_channels(
    result: COHPResult,
    *,
    bond_keys: Sequence[str] | None = None,
    source_labels: Sequence[str] | None = None,
    spins: Sequence[str] | None = None,
    orbital_keys: Sequence[str] | None = None,
) -> tuple[COHPChannel, ...]:
    """Select exact retained COHP channels while preserving source order."""
    if not isinstance(result, COHPResult):
        raise TypeError("result must be a COHPResult")
    key_filter = None if bond_keys is None else frozenset(_required_text(v, name="bond_key") for v in bond_keys)
    label_filter = None if source_labels is None else frozenset(
        _required_text(v, name="source_label") for v in source_labels
    )
    spin_filter = None if spins is None else frozenset(_spin(v) for v in spins)
    orbital_filter = None if orbital_keys is None else frozenset(
        _required_text(v, name="orbital_key") for v in orbital_keys
    )
    selected = tuple(
        channel
        for channel in result.channels
        if (key_filter is None or channel.bond_key in key_filter)
        and (label_filter is None or channel.source_label in label_filter)
        and (spin_filter is None or channel.spin in spin_filter)
        and (orbital_filter is None or channel.orbital_key in orbital_filter)
    )
    if not selected:
        raise BondingError("COHP channel selection matched no retained channels")
    return selected


def select_icohp_bonds(
    result: ICOHPResult,
    *,
    bond_keys: Sequence[str] | None = None,
    source_labels: Sequence[str] | None = None,
) -> tuple[ICOHPBondSummary, ...]:
    """Select exact ICOHP summaries while preserving source order."""
    if not isinstance(result, ICOHPResult):
        raise TypeError("result must be an ICOHPResult")
    key_filter = None if bond_keys is None else frozenset(_required_text(v, name="bond_key") for v in bond_keys)
    label_filter = None if source_labels is None else frozenset(
        _required_text(v, name="source_label") for v in source_labels
    )
    selected = tuple(
        bond
        for bond in result.bonds
        if (key_filter is None or bond.bond_key in key_filter)
        and (label_filter is None or bond.source_label in label_filter)
    )
    if not selected:
        raise BondingError("ICOHP bond selection matched no retained summaries")
    return selected


def sum_icohp_spins(
    summary: ICOHPBondSummary,
    *,
    spins: Sequence[str],
) -> ICOHPSpinSum:
    """Explicitly sum caller-selected physical ICOHP(E_F) channels."""
    if not isinstance(summary, ICOHPBondSummary):
        raise TypeError("summary must be an ICOHPBondSummary")
    selected = tuple(_spin(spin) for spin in spins)
    if not selected or len(set(selected)) != len(selected):
        raise BondingError("spins must be a non-empty unique sequence")
    missing = [spin for spin in selected if spin not in summary.icohp_by_spin]
    if missing:
        raise BondingError("requested ICOHP spin is not retained: " + ", ".join(missing))
    value = float(sum(summary.icohp_by_spin[spin] for spin in selected))
    return ICOHPSpinSum(
        bond_key=summary.bond_key,
        source_label=summary.source_label,
        contributing_spins=selected,
        value=value,
        source_summary_digest=summary.digest,
    )


def cohp_channels_frame(result: COHPResult) -> pd.DataFrame:
    """Return a detached point-wise table of retained source-sign COHP channels."""
    rows: list[dict[str, object]] = []
    for channel in result.channels:
        for energy, cohp, integrated in zip(
            result.energy.values_ev,
            channel.cohp,
            channel.integrated_cohp,
            strict=True,
        ):
            rows.append(
                {
                    "result_digest": result.digest,
                    "channel_digest": channel.digest,
                    "channel_key": channel.key,
                    "bond_key": channel.bond_key,
                    "source_label": channel.source_label,
                    "spin": channel.spin,
                    "energy_ev": float(energy),
                    "energy_reference": result.energy.reference_kind,
                    "cohp": float(cohp),
                    "integrated_cohp": float(integrated),
                    "bond_length_angstrom": channel.bond_length_angstrom,
                    "source_site_indices": channel.source_site_indices,
                    "orbital_key": channel.orbital_key,
                    "orbital_label": channel.orbital_label,
                    "orbital_descriptors": channel.orbital_descriptors,
                }
            )
    return pd.DataFrame(rows)


def icohp_bonds_frame(result: ICOHPResult) -> pd.DataFrame:
    """Return a detached one-row-per-bond table with explicit spin columns."""
    rows: list[dict[str, object]] = []
    for bond in result.bonds:
        rows.append(
            {
                "result_digest": result.digest,
                "summary_digest": bond.digest,
                "bond_key": bond.bond_key,
                "source_label": bond.source_label,
                "bond_length_angstrom": bond.bond_length_angstrom,
                "number_of_bonds": bond.number_of_bonds,
                "icohp_total": bond.icohp_by_spin.get("total"),
                "icohp_up": bond.icohp_by_spin.get("up"),
                "icohp_down": bond.icohp_by_spin.get("down"),
            }
        )
    return pd.DataFrame(rows)
