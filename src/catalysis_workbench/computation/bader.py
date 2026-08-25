"""Immutable Bader result state and explicit reference-electron charge accounting."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from numpy.typing import NDArray


class BaderError(ValueError):
    """Raised when Bader result or charge-accounting state is invalid."""


def _required_text(value: object, *, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise BaderError(f"{name} must not be blank")
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
        raise BaderError(f"{name} must be finite")
    return number


def _optional_nonnegative_float(value: object | None, *, name: str) -> float | None:
    if value is None:
        return None
    number = _finite_float(value, name=name)
    if number < 0:
        raise BaderError(f"{name} must be non-negative")
    return number


def _frozen_position(values: object) -> NDArray[np.float64]:
    try:
        source = np.asarray(values)
    except (TypeError, ValueError) as exc:
        raise TypeError("cartesian_position_angstrom must contain real numeric values") from exc
    if np.iscomplexobj(source):
        raise BaderError("cartesian_position_angstrom must contain real values")
    try:
        array = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise TypeError("cartesian_position_angstrom must contain real numeric values") from exc
    if array.shape != (3,) or not np.isfinite(array).all():
        raise BaderError("cartesian_position_angstrom must contain exactly three finite values")
    contiguous = np.ascontiguousarray(array, dtype=np.float64)
    frozen = np.frombuffer(contiguous.tobytes(order="C"), dtype=np.float64)
    frozen.setflags(write=False)
    return frozen


def _positive_int(value: object, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{name} must be an integer")
    integer = int(value)
    if integer <= 0:
        raise BaderError(f"{name} must be greater than zero")
    return integer


def _optional_site_index(value: object | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise TypeError("site_index must be an integer when supplied")
    integer = int(value)
    if integer < 0:
        raise BaderError("site_index must be non-negative")
    return integer


def _digest_text(digest: object, value: str) -> None:
    encoded = value.encode("utf-8")
    digest.update(len(encoded).to_bytes(8, "little", signed=False))
    digest.update(encoded)


def _digest_float(digest: object, value: float) -> None:
    digest.update(np.float64(value).tobytes())


def _digest_optional_float(digest: object, value: float | None) -> None:
    if value is None:
        digest.update(b"none\0")
    else:
        digest.update(b"value\0")
        _digest_float(digest, value)


@dataclass(frozen=True, slots=True, eq=False)
class BaderSiteResult:
    """One raw atom row from an ACF-style Bader result."""

    source_atom_index: int
    cartesian_position_angstrom: object
    bader_electrons: float
    min_distance_angstrom: float
    atomic_volume_angstrom3: float
    site_index: int | None = None
    site_key: str | None = None
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        source_index = _positive_int(self.source_atom_index, name="source_atom_index")
        position = _frozen_position(self.cartesian_position_angstrom)
        electrons = _finite_float(self.bader_electrons, name="bader_electrons")
        min_distance = _finite_float(
            self.min_distance_angstrom,
            name="min_distance_angstrom",
        )
        volume = _finite_float(self.atomic_volume_angstrom3, name="atomic_volume_angstrom3")
        if electrons < 0:
            raise BaderError("bader_electrons must be non-negative")
        if min_distance < 0:
            raise BaderError("min_distance_angstrom must be non-negative")
        if volume <= 0:
            raise BaderError("atomic_volume_angstrom3 must be greater than zero")

        site_index = _optional_site_index(self.site_index)
        site_key = _optional_text(self.site_key, name="site_key")
        if (site_index is None) != (site_key is None):
            raise BaderError("site_index and site_key must be supplied together")
        if site_index is not None and source_index != site_index + 1:
            raise BaderError(
                "direct structure mapping requires source_atom_index == site_index + 1"
            )

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.BaderSiteResult.v1\0")
        digest.update(source_index.to_bytes(8, "little", signed=False))
        digest.update(position.tobytes(order="C"))
        for value in (electrons, min_distance, volume):
            _digest_float(digest, value)
        if site_index is None:
            digest.update(b"unmapped\0")
        else:
            digest.update(b"mapped\0")
            digest.update(site_index.to_bytes(8, "little", signed=False))
            _digest_text(digest, site_key or "")

        object.__setattr__(self, "source_atom_index", source_index)
        object.__setattr__(self, "cartesian_position_angstrom", position)
        object.__setattr__(self, "bader_electrons", electrons)
        object.__setattr__(self, "min_distance_angstrom", min_distance)
        object.__setattr__(self, "atomic_volume_angstrom3", volume)
        object.__setattr__(self, "site_index", site_index)
        object.__setattr__(self, "site_key", site_key)
        object.__setattr__(self, "digest", digest.hexdigest())

    def equals(self, other: object) -> bool:
        return (
            isinstance(other, BaderSiteResult)
            and self.source_atom_index == other.source_atom_index
            and np.array_equal(
                self.cartesian_position_angstrom,
                other.cartesian_position_angstrom,
            )
            and self.bader_electrons == other.bader_electrons
            and self.min_distance_angstrom == other.min_distance_angstrom
            and self.atomic_volume_angstrom3 == other.atomic_volume_angstrom3
            and self.site_index == other.site_index
            and self.site_key == other.site_key
            and self.digest == other.digest
        )

    def __eq__(self, other: object) -> bool:
        return self.equals(other)


@dataclass(frozen=True, slots=True, eq=False)
class BaderResult:
    """Immutable raw Bader atom table with optional direct structure mapping."""

    sites: Sequence[BaderSiteResult]
    vacuum_charge_electrons: float | None = None
    vacuum_volume_angstrom3: float | None = None
    number_of_electrons: float | None = None
    structure_digest: str | None = None
    position_tolerance_angstrom: float | None = None
    source_format: str = "ACF.dat"
    source_path: str | None = None
    source_id: str | None = None
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        sites = tuple(self.sites)
        if not sites or not all(isinstance(site, BaderSiteResult) for site in sites):
            raise BaderError("sites must contain at least one BaderSiteResult")
        expected_indices = tuple(range(1, len(sites) + 1))
        if tuple(site.source_atom_index for site in sites) != expected_indices:
            raise BaderError("source atom indices must be the ordered standard sequence 1..N")

        mapped = tuple(site.site_index is not None for site in sites)
        if len(set(mapped)) != 1:
            raise BaderError("Bader sites must be either all mapped or all unmapped")
        structure_digest = _optional_text(self.structure_digest, name="structure_digest")
        tolerance = None
        if self.position_tolerance_angstrom is not None:
            tolerance = _finite_float(
                self.position_tolerance_angstrom,
                name="position_tolerance_angstrom",
            )
            if tolerance <= 0:
                raise BaderError("position_tolerance_angstrom must be greater than zero")
        if mapped[0]:
            if structure_digest is None or tolerance is None:
                raise BaderError(
                    "mapped Bader results require structure_digest and position tolerance"
                )
            if tuple(site.site_index for site in sites) != tuple(range(len(sites))):
                raise BaderError("mapped site indices must be the ordered sequence 0..N-1")
            site_keys = tuple(site.site_key for site in sites)
            if len(set(site_keys)) != len(site_keys):
                raise BaderError("mapped site keys must be unique")
        elif structure_digest is not None or tolerance is not None:
            raise BaderError(
                "unmapped Bader results cannot retain structure mapping provenance"
            )

        vacuum_charge = _optional_nonnegative_float(
            self.vacuum_charge_electrons,
            name="vacuum_charge_electrons",
        )
        vacuum_volume = _optional_nonnegative_float(
            self.vacuum_volume_angstrom3,
            name="vacuum_volume_angstrom3",
        )
        nelectrons = _optional_nonnegative_float(
            self.number_of_electrons,
            name="number_of_electrons",
        )
        source_format = _required_text(self.source_format, name="source_format")
        source_path = _optional_text(self.source_path, name="source_path")
        source_id = _optional_text(self.source_id, name="source_id")

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.BaderResult.v1\0")
        _digest_text(digest, source_format)
        for site in sites:
            _digest_text(digest, site.digest)
        for value in (vacuum_charge, vacuum_volume, nelectrons):
            _digest_optional_float(digest, value)
        if structure_digest is None:
            digest.update(b"unmapped\0")
        else:
            digest.update(b"mapped\0")
            _digest_text(digest, structure_digest)
            _digest_float(digest, tolerance or 0.0)

        object.__setattr__(self, "sites", sites)
        object.__setattr__(self, "vacuum_charge_electrons", vacuum_charge)
        object.__setattr__(self, "vacuum_volume_angstrom3", vacuum_volume)
        object.__setattr__(self, "number_of_electrons", nelectrons)
        object.__setattr__(self, "structure_digest", structure_digest)
        object.__setattr__(self, "position_tolerance_angstrom", tolerance)
        object.__setattr__(self, "source_format", source_format)
        object.__setattr__(self, "source_path", source_path)
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "digest", digest.hexdigest())

    @property
    def mapped(self) -> bool:
        return self.structure_digest is not None

    def equals(self, other: object) -> bool:
        return (
            isinstance(other, BaderResult)
            and self.sites == other.sites
            and self.vacuum_charge_electrons == other.vacuum_charge_electrons
            and self.vacuum_volume_angstrom3 == other.vacuum_volume_angstrom3
            and self.number_of_electrons == other.number_of_electrons
            and self.structure_digest == other.structure_digest
            and self.position_tolerance_angstrom == other.position_tolerance_angstrom
            and self.source_format == other.source_format
            and self.source_path == other.source_path
            and self.source_id == other.source_id
            and self.digest == other.digest
        )

    def __eq__(self, other: object) -> bool:
        return self.equals(other)


@dataclass(frozen=True, slots=True, eq=False)
class BaderChargeSiteResult:
    """One explicitly referenced Bader charge-accounting row."""

    source_atom_index: int
    cartesian_position_angstrom: object
    bader_electrons: float
    reference_electrons: float
    electron_transfer: float
    partial_charge: float
    source_site_digest: str
    site_index: int | None = None
    site_key: str | None = None
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        source_index = _positive_int(self.source_atom_index, name="source_atom_index")
        position = _frozen_position(self.cartesian_position_angstrom)
        bader = _finite_float(self.bader_electrons, name="bader_electrons")
        reference = _finite_float(self.reference_electrons, name="reference_electrons")
        transfer = _finite_float(self.electron_transfer, name="electron_transfer")
        partial = _finite_float(self.partial_charge, name="partial_charge")
        if bader < 0 or reference < 0:
            raise BaderError("Bader and reference electron populations must be non-negative")
        if not np.isclose(transfer, bader - reference, rtol=0.0, atol=1e-12):
            raise BaderError("electron_transfer must equal N_Bader - N_reference")
        if not np.isclose(partial, reference - bader, rtol=0.0, atol=1e-12):
            raise BaderError("partial_charge must equal N_reference - N_Bader")
        source_site_digest = _required_text(
            self.source_site_digest,
            name="source_site_digest",
        )
        site_index = _optional_site_index(self.site_index)
        site_key = _optional_text(self.site_key, name="site_key")
        if (site_index is None) != (site_key is None):
            raise BaderError("site_index and site_key must be supplied together")
        if site_index is not None and source_index != site_index + 1:
            raise BaderError(
                "direct structure mapping requires source_atom_index == site_index + 1"
            )

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.BaderChargeSiteResult.v1\0")
        digest.update(source_index.to_bytes(8, "little", signed=False))
        digest.update(position.tobytes(order="C"))
        for value in (bader, reference, transfer, partial):
            _digest_float(digest, value)
        _digest_text(digest, source_site_digest)
        if site_index is None:
            digest.update(b"unmapped\0")
        else:
            digest.update(b"mapped\0")
            digest.update(site_index.to_bytes(8, "little", signed=False))
            _digest_text(digest, site_key or "")

        object.__setattr__(self, "source_atom_index", source_index)
        object.__setattr__(self, "cartesian_position_angstrom", position)
        object.__setattr__(self, "bader_electrons", bader)
        object.__setattr__(self, "reference_electrons", reference)
        object.__setattr__(self, "electron_transfer", transfer)
        object.__setattr__(self, "partial_charge", partial)
        object.__setattr__(self, "source_site_digest", source_site_digest)
        object.__setattr__(self, "site_index", site_index)
        object.__setattr__(self, "site_key", site_key)
        object.__setattr__(self, "digest", digest.hexdigest())

    def equals(self, other: object) -> bool:
        return (
            isinstance(other, BaderChargeSiteResult)
            and self.source_atom_index == other.source_atom_index
            and np.array_equal(
                self.cartesian_position_angstrom,
                other.cartesian_position_angstrom,
            )
            and self.bader_electrons == other.bader_electrons
            and self.reference_electrons == other.reference_electrons
            and self.electron_transfer == other.electron_transfer
            and self.partial_charge == other.partial_charge
            and self.source_site_digest == other.source_site_digest
            and self.site_index == other.site_index
            and self.site_key == other.site_key
            and self.digest == other.digest
        )

    def __eq__(self, other: object) -> bool:
        return self.equals(other)


@dataclass(frozen=True, slots=True, eq=False)
class BaderChargeResult:
    """Immutable explicit charge-accounting result derived from one BaderResult."""

    source_bader_result_digest: str
    sites: Sequence[BaderChargeSiteResult]
    reference_id: str
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        source_digest = _required_text(
            self.source_bader_result_digest,
            name="source_bader_result_digest",
        )
        sites = tuple(self.sites)
        if not sites or not all(isinstance(site, BaderChargeSiteResult) for site in sites):
            raise BaderError("sites must contain at least one BaderChargeSiteResult")
        if tuple(site.source_atom_index for site in sites) != tuple(range(1, len(sites) + 1)):
            raise BaderError("charge-accounting source indices must be ordered 1..N")
        reference_id = _required_text(self.reference_id, name="reference_id")

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.BaderChargeResult.v1\0")
        _digest_text(digest, source_digest)
        _digest_text(digest, reference_id)
        for site in sites:
            _digest_text(digest, site.digest)

        object.__setattr__(self, "source_bader_result_digest", source_digest)
        object.__setattr__(self, "sites", sites)
        object.__setattr__(self, "reference_id", reference_id)
        object.__setattr__(self, "digest", digest.hexdigest())

    def equals(self, other: object) -> bool:
        return (
            isinstance(other, BaderChargeResult)
            and self.source_bader_result_digest == other.source_bader_result_digest
            and self.sites == other.sites
            and self.reference_id == other.reference_id
            and self.digest == other.digest
        )

    def __eq__(self, other: object) -> bool:
        return self.equals(other)


def account_bader_charges(
    result: BaderResult,
    reference_electrons: Sequence[float],
    *,
    reference_id: str,
) -> BaderChargeResult:
    """Derive explicit transfer/partial-charge signs from caller-supplied references."""
    if not isinstance(result, BaderResult):
        raise TypeError("result must be a BaderResult")
    try:
        references = tuple(reference_electrons)
    except TypeError as exc:
        raise TypeError("reference_electrons must be an ordered sequence") from exc
    if len(references) != len(result.sites):
        raise BaderError("reference_electrons length must match Bader site count")
    provenance = _required_text(reference_id, name="reference_id")

    charge_sites: list[BaderChargeSiteResult] = []
    for site, raw_reference in zip(result.sites, references, strict=True):
        reference = _finite_float(raw_reference, name="reference_electrons")
        if reference < 0:
            raise BaderError("reference_electrons must be non-negative")
        transfer = site.bader_electrons - reference
        partial = reference - site.bader_electrons
        charge_sites.append(
            BaderChargeSiteResult(
                source_atom_index=site.source_atom_index,
                cartesian_position_angstrom=site.cartesian_position_angstrom,
                bader_electrons=site.bader_electrons,
                reference_electrons=reference,
                electron_transfer=transfer,
                partial_charge=partial,
                source_site_digest=site.digest,
                site_index=site.site_index,
                site_key=site.site_key,
            )
        )
    return BaderChargeResult(
        source_bader_result_digest=result.digest,
        sites=charge_sites,
        reference_id=provenance,
    )


def bader_result_frame(result: BaderResult) -> pd.DataFrame:
    """Return a detached one-row-per-site table of raw retained Bader state."""
    if not isinstance(result, BaderResult):
        raise TypeError("result must be a BaderResult")
    rows = []
    for site in result.sites:
        x, y, z = (float(value) for value in site.cartesian_position_angstrom)
        rows.append(
            {
                "result_digest": result.digest,
                "source_atom_index": site.source_atom_index,
                "site_index": site.site_index,
                "site_key": site.site_key,
                "x_angstrom": x,
                "y_angstrom": y,
                "z_angstrom": z,
                "bader_electrons": site.bader_electrons,
                "min_distance_angstrom": site.min_distance_angstrom,
                "atomic_volume_angstrom3": site.atomic_volume_angstrom3,
                "vacuum_charge_electrons": result.vacuum_charge_electrons,
                "vacuum_volume_angstrom3": result.vacuum_volume_angstrom3,
                "number_of_electrons": result.number_of_electrons,
                "structure_digest": result.structure_digest,
                "position_tolerance_angstrom": result.position_tolerance_angstrom,
                "source_format": result.source_format,
                "source_path": result.source_path,
                "source_id": result.source_id,
                "site_digest": site.digest,
            }
        )
    return pd.DataFrame(rows)


def bader_charge_frame(result: BaderChargeResult) -> pd.DataFrame:
    """Return a detached table with explicit non-ambiguous derived charge fields."""
    if not isinstance(result, BaderChargeResult):
        raise TypeError("result must be a BaderChargeResult")
    rows = []
    for site in result.sites:
        x, y, z = (float(value) for value in site.cartesian_position_angstrom)
        rows.append(
            {
                "charge_result_digest": result.digest,
                "source_bader_result_digest": result.source_bader_result_digest,
                "reference_id": result.reference_id,
                "source_atom_index": site.source_atom_index,
                "site_index": site.site_index,
                "site_key": site.site_key,
                "x_angstrom": x,
                "y_angstrom": y,
                "z_angstrom": z,
                "bader_electrons": site.bader_electrons,
                "reference_electrons": site.reference_electrons,
                "electron_transfer": site.electron_transfer,
                "partial_charge": site.partial_charge,
                "source_site_digest": site.source_site_digest,
                "site_digest": site.digest,
            }
        )
    return pd.DataFrame(rows)


__all__ = [
    "BaderChargeResult",
    "BaderChargeSiteResult",
    "BaderError",
    "BaderResult",
    "BaderSiteResult",
    "account_bader_charges",
    "bader_charge_frame",
    "bader_result_frame",
]
