"""Explicit first-moment band-center analysis for retained DOS traces."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np

from .dos import DOSTrace


class BandCenterError(ValueError):
    """Raised when a band-center calculation is scientifically invalid."""


def _required_text(value: str, *, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise BandCenterError(f"{name} must not be blank")
    return text


def _finite_float(value: object, *, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a finite float") from exc
    if not np.isfinite(number):
        raise BandCenterError(f"{name} must be finite")
    return number


def _window(value: Sequence[float], *, name: str) -> tuple[float, float]:
    retained = tuple(value)
    if len(retained) != 2:
        raise BandCenterError(f"{name} must contain exactly two values")
    low = _finite_float(retained[0], name=f"{name}[0]")
    high = _finite_float(retained[1], name=f"{name}[1]")
    if low >= high:
        raise BandCenterError(f"{name} must satisfy lower < upper")
    return low, high


def _digest_text(digest: object, value: str) -> None:
    encoded = value.encode("utf-8")
    digest.update(len(encoded).to_bytes(8, "little", signed=False))
    digest.update(encoded)


def _digest_float(digest: object, value: float) -> None:
    digest.update(np.float64(value).tobytes())


@dataclass(frozen=True, slots=True, eq=False)
class BandCenterResult:
    """Immutable first-moment result with explicit DOS and window provenance."""

    source_trace_key: str
    source_trace_digest: str
    source_dos_digest: str
    source_channel_digests: Sequence[str]
    source_projection_keys: Sequence[str]
    source_spins: Sequence[str]
    source_operations: Sequence[str]
    energy_reference_kind: str
    source_fermi_ev: float | None
    applied_shift_ev: float
    density_unit: str
    normalization_basis: str
    requested_window_ev: Sequence[float]
    integrated_window_ev: Sequence[float]
    point_count: int
    numerator: float
    denominator: float
    denominator_tolerance: float
    center_ev: float
    integration_method: str = field(init=False, default="trapezoid")
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        trace_key = _required_text(self.source_trace_key, name="source_trace_key")
        trace_digest = _required_text(self.source_trace_digest, name="source_trace_digest")
        dos_digest = _required_text(self.source_dos_digest, name="source_dos_digest")
        channel_digests = tuple(
            _required_text(value, name="source_channel_digest")
            for value in self.source_channel_digests
        )
        projection_keys = tuple(
            _required_text(value, name="source_projection_key")
            for value in self.source_projection_keys
        )
        spins = tuple(_required_text(value, name="source_spin") for value in self.source_spins)
        operations = tuple(
            _required_text(value, name="source_operation") for value in self.source_operations
        )
        if not channel_digests or not operations:
            raise BandCenterError("source channel and operation provenance must not be empty")
        if not (len(channel_digests) == len(projection_keys) == len(spins)):
            raise BandCenterError("source channel/projection/spin provenance must align")

        reference_kind = _required_text(
            self.energy_reference_kind,
            name="energy_reference_kind",
        )
        source_fermi = None
        if self.source_fermi_ev is not None:
            source_fermi = _finite_float(self.source_fermi_ev, name="source_fermi_ev")
        applied_shift = _finite_float(self.applied_shift_ev, name="applied_shift_ev")
        density_unit = _required_text(self.density_unit, name="density_unit")
        normalization = _required_text(self.normalization_basis, name="normalization_basis")
        requested_window = _window(self.requested_window_ev, name="requested_window_ev")
        integrated_window = _window(self.integrated_window_ev, name="integrated_window_ev")
        if integrated_window[0] < requested_window[0] or integrated_window[1] > requested_window[1]:
            raise BandCenterError("integrated window must lie inside the requested window")

        if isinstance(self.point_count, bool) or not isinstance(self.point_count, int):
            raise TypeError("point_count must be an integer")
        if self.point_count < 2:
            raise BandCenterError("point_count must be at least two")

        numerator = _finite_float(self.numerator, name="numerator")
        denominator = _finite_float(self.denominator, name="denominator")
        tolerance = _finite_float(self.denominator_tolerance, name="denominator_tolerance")
        if tolerance <= 0:
            raise BandCenterError("denominator_tolerance must be greater than zero")
        if denominator <= tolerance:
            raise BandCenterError("denominator must exceed denominator_tolerance")
        center = _finite_float(self.center_ev, name="center_ev")
        expected_center = numerator / denominator
        if not np.isclose(center, expected_center, rtol=1e-12, atol=1e-12):
            raise BandCenterError("center_ev must equal numerator / denominator")

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.BandCenterResult.v1\0")
        for value in (
            trace_key,
            trace_digest,
            dos_digest,
            reference_kind,
            density_unit,
            normalization,
            "trapezoid",
        ):
            _digest_text(digest, value)
        for values in (channel_digests, projection_keys, spins, operations):
            for value in values:
                _digest_text(digest, value)
            digest.update(b"\0")
        _digest_text(digest, "none" if source_fermi is None else "value")
        if source_fermi is not None:
            _digest_float(digest, source_fermi)
        for value in (
            applied_shift,
            *requested_window,
            *integrated_window,
            numerator,
            denominator,
            tolerance,
            center,
        ):
            _digest_float(digest, value)
        digest.update(self.point_count.to_bytes(8, "little", signed=False))

        object.__setattr__(self, "source_trace_key", trace_key)
        object.__setattr__(self, "source_trace_digest", trace_digest)
        object.__setattr__(self, "source_dos_digest", dos_digest)
        object.__setattr__(self, "source_channel_digests", channel_digests)
        object.__setattr__(self, "source_projection_keys", projection_keys)
        object.__setattr__(self, "source_spins", spins)
        object.__setattr__(self, "source_operations", operations)
        object.__setattr__(self, "energy_reference_kind", reference_kind)
        object.__setattr__(self, "source_fermi_ev", source_fermi)
        object.__setattr__(self, "applied_shift_ev", applied_shift)
        object.__setattr__(self, "density_unit", density_unit)
        object.__setattr__(self, "normalization_basis", normalization)
        object.__setattr__(self, "requested_window_ev", requested_window)
        object.__setattr__(self, "integrated_window_ev", integrated_window)
        object.__setattr__(self, "numerator", numerator)
        object.__setattr__(self, "denominator", denominator)
        object.__setattr__(self, "denominator_tolerance", tolerance)
        object.__setattr__(self, "center_ev", center)
        object.__setattr__(self, "digest", digest.hexdigest())

    def equals(self, other: object) -> bool:
        return (
            isinstance(other, BandCenterResult)
            and self.source_trace_key == other.source_trace_key
            and self.source_trace_digest == other.source_trace_digest
            and self.source_dos_digest == other.source_dos_digest
            and self.source_channel_digests == other.source_channel_digests
            and self.source_projection_keys == other.source_projection_keys
            and self.source_spins == other.source_spins
            and self.source_operations == other.source_operations
            and self.energy_reference_kind == other.energy_reference_kind
            and self.source_fermi_ev == other.source_fermi_ev
            and self.applied_shift_ev == other.applied_shift_ev
            and self.density_unit == other.density_unit
            and self.normalization_basis == other.normalization_basis
            and self.requested_window_ev == other.requested_window_ev
            and self.integrated_window_ev == other.integrated_window_ev
            and self.point_count == other.point_count
            and self.numerator == other.numerator
            and self.denominator == other.denominator
            and self.denominator_tolerance == other.denominator_tolerance
            and self.center_ev == other.center_ev
            and self.integration_method == other.integration_method
            and self.digest == other.digest
        )

    def __eq__(self, other: object) -> bool:
        return self.equals(other)


def calculate_band_center(
    trace: DOSTrace,
    energy_min_ev: float,
    energy_max_ev: float,
    *,
    denominator_tolerance: float,
) -> BandCenterResult:
    """Calculate an explicit trapezoidal first moment on retained source-grid points."""
    if not isinstance(trace, DOSTrace):
        raise TypeError("trace must be a DOSTrace")

    low = _finite_float(energy_min_ev, name="energy_min_ev")
    high = _finite_float(energy_max_ev, name="energy_max_ev")
    if low >= high:
        raise BandCenterError("integration window requires energy_min_ev < energy_max_ev")
    tolerance = _finite_float(denominator_tolerance, name="denominator_tolerance")
    if tolerance <= 0:
        raise BandCenterError("denominator_tolerance must be greater than zero")

    energies = trace.energy.values_ev
    if energies.ndim != 1 or energies.size < 2 or not np.all(np.diff(energies) > 0):
        raise BandCenterError("retained energy grid must be one-dimensional and strictly increasing")
    if low < float(energies[0]) or high > float(energies[-1]):
        raise BandCenterError("requested integration window must lie inside the retained energy axis")

    mask = (energies >= low) & (energies <= high)
    point_count = int(np.count_nonzero(mask))
    if point_count < 2:
        raise BandCenterError("integration window must retain at least two source-grid points")

    selected_energy = energies[mask]
    selected_density = trace.density[mask]
    denominator = float(np.trapezoid(selected_density, x=selected_energy))
    numerator = float(np.trapezoid(selected_density * selected_energy, x=selected_energy))
    if not np.isfinite(denominator) or not np.isfinite(numerator):
        raise BandCenterError("band-center integrals must be finite")
    if denominator <= tolerance:
        raise BandCenterError(
            "DOS first-moment denominator does not exceed the caller-supplied tolerance"
        )
    center = numerator / denominator
    if not np.isfinite(center):
        raise BandCenterError("band center must be finite")

    return BandCenterResult(
        source_trace_key=trace.key,
        source_trace_digest=trace.digest,
        source_dos_digest=trace.source_dos_digest,
        source_channel_digests=trace.source_channel_digests,
        source_projection_keys=trace.source_projection_keys,
        source_spins=trace.source_spins,
        source_operations=trace.operations,
        energy_reference_kind=trace.energy.reference_kind,
        source_fermi_ev=trace.energy.source_fermi_ev,
        applied_shift_ev=trace.energy.applied_shift_ev,
        density_unit=trace.density_unit,
        normalization_basis=trace.normalization_basis,
        requested_window_ev=(low, high),
        integrated_window_ev=(float(selected_energy[0]), float(selected_energy[-1])),
        point_count=point_count,
        numerator=numerator,
        denominator=denominator,
        denominator_tolerance=tolerance,
        center_ev=center,
    )


__all__ = ["BandCenterError", "BandCenterResult", "calculate_band_center"]
