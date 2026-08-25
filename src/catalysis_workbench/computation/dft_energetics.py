"""Explicit immutable post-processing for caller-supplied DFT energies."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from hashlib import sha256
from math import isfinite
from types import MappingProxyType
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray


class DFTEnergeticsError(ValueError):
    """Raised when explicit DFT-energy state or arithmetic is invalid."""


def _finite_real(value: float, *, name: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise TypeError(f"{name} must be a real numeric value")
    source = np.asarray(value)
    if np.iscomplexobj(source) or source.ndim != 0 or source.dtype.kind not in "biuf":
        raise TypeError(f"{name} must be a real numeric value")
    number = float(value)
    if not isfinite(number):
        raise DFTEnergeticsError(f"{name} must be finite")
    return number


def _optional_text(value: str | None, *, name: str) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        raise DFTEnergeticsError(f"{name} must not be blank when supplied")
    return text


def _required_text(value: str, *, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise DFTEnergeticsError(f"{name} must not be blank")
    return text


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


def _frozen_1d(values: Sequence[float], *, name: str) -> NDArray[np.float64]:
    source = np.asarray(values)
    if source.ndim != 1 or np.iscomplexobj(source) or source.dtype.kind not in "biuf":
        raise TypeError(f"{name} must be a one-dimensional real numeric sequence")
    array = np.ascontiguousarray(source, dtype=np.float64)
    if not np.isfinite(array).all():
        raise DFTEnergeticsError(f"{name} must contain only finite values")
    frozen = np.frombuffer(array.tobytes(), dtype=np.float64)
    frozen.setflags(write=False)
    return frozen


@dataclass(frozen=True, slots=True)
class DFTEnergyEntry:
    """One caller-supplied scalar DFT energy in eV with explicit identity."""

    key: str
    energy_ev: float
    label: str | None = None
    normalization_basis: str | None = None
    source_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "key", _required_text(self.key, name="energy key"))
        object.__setattr__(self, "energy_ev", _finite_real(self.energy_ev, name="energy_ev"))
        object.__setattr__(self, "label", _optional_text(self.label, name="label"))
        object.__setattr__(
            self,
            "normalization_basis",
            _optional_text(self.normalization_basis, name="normalization_basis"),
        )
        object.__setattr__(
            self,
            "source_id",
            _optional_text(self.source_id, name="source_id"),
        )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))

    def metadata_dict(self) -> dict[str, Any]:
        """Return an independent mutable metadata copy."""
        return {key: _thaw_value(value) for key, value in self.metadata.items()}


@dataclass(frozen=True, slots=True)
class DFTEnergyLedger:
    """Ordered immutable ledger of explicitly keyed DFT energies."""

    entries: tuple[DFTEnergyEntry, ...]
    source_id: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        entries = tuple(self.entries)
        if not entries:
            raise DFTEnergeticsError("DFT energy ledger requires at least one entry")
        if not all(isinstance(entry, DFTEnergyEntry) for entry in entries):
            raise TypeError("entries must contain only DFTEnergyEntry instances")
        keys = [entry.key for entry in entries]
        if len(keys) != len(set(keys)):
            raise DFTEnergeticsError("DFT energy entry keys must be unique within a ledger")
        source_id = _required_text(self.source_id, name="ledger source_id")
        digest_state = [source_id]
        for entry in entries:
            digest_state.extend(
                (
                    entry.key,
                    entry.energy_ev.hex(),
                    entry.normalization_basis or "<none>",
                    entry.source_id or "<none>",
                )
            )
        digest = sha256("\x1f".join(digest_state).encode("utf-8")).hexdigest()
        object.__setattr__(self, "entries", entries)
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))
        object.__setattr__(self, "digest", digest)

    def entry(self, key: str) -> DFTEnergyEntry:
        """Return one entry by stable key or fail closed."""
        requested = _required_text(key, name="entry key")
        for entry in self.entries:
            if entry.key == requested:
                return entry
        raise DFTEnergeticsError(f"unknown DFT energy entry key: {requested}")

    def metadata_dict(self) -> dict[str, Any]:
        """Return an independent mutable metadata copy."""
        return {key: _thaw_value(value) for key, value in self.metadata.items()}


@dataclass(frozen=True, slots=True)
class EnergyTerm:
    """One explicit coefficient applied to one keyed ledger energy."""

    entry_key: str
    coefficient: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "entry_key",
            _required_text(self.entry_key, name="term entry_key"),
        )
        object.__setattr__(
            self,
            "coefficient",
            _finite_real(self.coefficient, name="term coefficient"),
        )


@dataclass(frozen=True, slots=True, eq=False)
class RelativeEnergyResult:
    """Explicit same-basis relative energies against one retained reference."""

    ledger_digest: str
    reference_key: str
    entry_keys: tuple[str, ...]
    entry_labels: tuple[str, ...]
    energies_ev: Sequence[float]
    delta_energy_ev: Sequence[float]
    normalization_basis: str

    def __post_init__(self) -> None:
        ledger_digest = _required_text(self.ledger_digest, name="ledger_digest")
        reference_key = _required_text(self.reference_key, name="reference_key")
        keys = tuple(_required_text(key, name="entry key") for key in self.entry_keys)
        labels = tuple(str(label) for label in self.entry_labels)
        if not keys:
            raise DFTEnergeticsError("relative-energy result requires at least one entry")
        if len(keys) != len(set(keys)):
            raise DFTEnergeticsError("relative-energy entry keys must be unique")
        if reference_key not in keys:
            raise DFTEnergeticsError("reference_key must be retained in relative-energy entries")
        if len(labels) != len(keys):
            raise DFTEnergeticsError("entry_labels must match entry_keys")
        energies = _frozen_1d(self.energies_ev, name="energies_ev")
        deltas = _frozen_1d(self.delta_energy_ev, name="delta_energy_ev")
        if energies.size != len(keys) or deltas.size != len(keys):
            raise DFTEnergeticsError("relative-energy arrays must match entry key count")
        reference_index = keys.index(reference_key)
        expected = energies - energies[reference_index]
        if not np.allclose(deltas, expected, rtol=1e-12, atol=1e-12):
            raise DFTEnergeticsError("delta_energy_ev contradicts retained energies/reference")
        basis = _required_text(self.normalization_basis, name="normalization_basis")
        object.__setattr__(self, "ledger_digest", ledger_digest)
        object.__setattr__(self, "reference_key", reference_key)
        object.__setattr__(self, "entry_keys", keys)
        object.__setattr__(self, "entry_labels", labels)
        object.__setattr__(self, "energies_ev", energies)
        object.__setattr__(self, "delta_energy_ev", deltas)
        object.__setattr__(self, "normalization_basis", basis)


@dataclass(frozen=True, slots=True, eq=False)
class EnergyCombinationResult:
    """Reconstructible explicit linear combination of retained ledger energies."""

    ledger_digest: str
    terms: tuple[EnergyTerm, ...]
    term_energies_ev: Sequence[float]
    contributions_ev: Sequence[float]
    value_ev: float
    expression_label: str
    result_basis: str

    def __post_init__(self) -> None:
        ledger_digest = _required_text(self.ledger_digest, name="ledger_digest")
        terms = tuple(self.terms)
        if not terms:
            raise DFTEnergeticsError("energy combination requires at least one term")
        if not all(isinstance(term, EnergyTerm) for term in terms):
            raise TypeError("terms must contain only EnergyTerm instances")
        term_keys = [term.entry_key for term in terms]
        if len(term_keys) != len(set(term_keys)):
            raise DFTEnergeticsError("energy combination entry keys must be unique")
        energies = _frozen_1d(self.term_energies_ev, name="term_energies_ev")
        contributions = _frozen_1d(self.contributions_ev, name="contributions_ev")
        if energies.size != len(terms) or contributions.size != len(terms):
            raise DFTEnergeticsError("combination arrays must match term count")
        coefficients = np.asarray([term.coefficient for term in terms], dtype=np.float64)
        expected_contributions = coefficients * energies
        if not np.allclose(
            contributions,
            expected_contributions,
            rtol=1e-12,
            atol=1e-12,
        ):
            raise DFTEnergeticsError("contributions_ev contradict terms and term energies")
        value = _finite_real(self.value_ev, name="value_ev")
        if not np.isclose(value, float(np.sum(contributions)), rtol=1e-12, atol=1e-12):
            raise DFTEnergeticsError("value_ev contradicts retained contributions")
        object.__setattr__(self, "ledger_digest", ledger_digest)
        object.__setattr__(self, "terms", terms)
        object.__setattr__(self, "term_energies_ev", energies)
        object.__setattr__(self, "contributions_ev", contributions)
        object.__setattr__(self, "value_ev", value)
        object.__setattr__(
            self,
            "expression_label",
            _required_text(self.expression_label, name="expression_label"),
        )
        object.__setattr__(
            self,
            "result_basis",
            _required_text(self.result_basis, name="result_basis"),
        )


def relative_energies(
    ledger: DFTEnergyLedger,
    reference_key: str,
    *,
    entry_keys: Sequence[str] | None = None,
) -> RelativeEnergyResult:
    """Compute same-basis relative energies against an explicit retained reference."""
    if not isinstance(ledger, DFTEnergyLedger):
        raise TypeError("ledger must be a DFTEnergyLedger")
    reference = ledger.entry(reference_key)
    if entry_keys is None:
        selected = ledger.entries
    else:
        retained_keys = tuple(_required_text(key, name="entry key") for key in entry_keys)
        if not retained_keys:
            raise DFTEnergeticsError("entry_keys must contain at least one key")
        if len(retained_keys) != len(set(retained_keys)):
            raise DFTEnergeticsError("entry_keys must be unique")
        if reference.key not in retained_keys:
            raise DFTEnergeticsError("entry_keys must explicitly include the reference key")
        selected = tuple(ledger.entry(key) for key in retained_keys)
    basis = reference.normalization_basis
    if basis is None:
        raise DFTEnergeticsError(
            "relative energies require an explicit reference normalization_basis"
        )
    if any(entry.normalization_basis != basis for entry in selected):
        raise DFTEnergeticsError(
            "relative energies require one explicit matching normalization_basis"
        )
    energies = np.asarray([entry.energy_ev for entry in selected], dtype=np.float64)
    reference_energy = reference.energy_ev
    labels = tuple(entry.label or entry.key for entry in selected)
    return RelativeEnergyResult(
        ledger_digest=ledger.digest,
        reference_key=reference.key,
        entry_keys=tuple(entry.key for entry in selected),
        entry_labels=labels,
        energies_ev=energies,
        delta_energy_ev=energies - reference_energy,
        normalization_basis=basis,
    )


def combine_energies(
    ledger: DFTEnergyLedger,
    terms: Sequence[EnergyTerm],
    *,
    expression_label: str,
    result_basis: str,
) -> EnergyCombinationResult:
    """Evaluate an explicit caller-defined linear combination of ledger energies."""
    if not isinstance(ledger, DFTEnergyLedger):
        raise TypeError("ledger must be a DFTEnergyLedger")
    retained_terms = tuple(terms)
    if not retained_terms:
        raise DFTEnergeticsError("terms must contain at least one EnergyTerm")
    if not all(isinstance(term, EnergyTerm) for term in retained_terms):
        raise TypeError("terms must contain only EnergyTerm instances")
    term_keys = [term.entry_key for term in retained_terms]
    if len(term_keys) != len(set(term_keys)):
        raise DFTEnergeticsError("terms must use unique entry keys")
    entries = tuple(ledger.entry(term.entry_key) for term in retained_terms)
    energies = np.asarray([entry.energy_ev for entry in entries], dtype=np.float64)
    coefficients = np.asarray(
        [term.coefficient for term in retained_terms],
        dtype=np.float64,
    )
    contributions = coefficients * energies
    return EnergyCombinationResult(
        ledger_digest=ledger.digest,
        terms=retained_terms,
        term_energies_ev=energies,
        contributions_ev=contributions,
        value_ev=float(np.sum(contributions)),
        expression_label=expression_label,
        result_basis=result_basis,
    )


def adsorption_energy(
    ledger: DFTEnergyLedger,
    *,
    combined_key: str,
    slab_key: str,
    adsorbate_key: str,
    adsorbate_stoichiometry: float = 1.0,
    result_basis: str = "adsorption_event",
    expression_label: str | None = None,
) -> EnergyCombinationResult:
    """Return ``E(combined)-E(slab)-n*E(adsorbate)`` with explicit retained terms."""
    keys = (
        _required_text(combined_key, name="combined_key"),
        _required_text(slab_key, name="slab_key"),
        _required_text(adsorbate_key, name="adsorbate_key"),
    )
    if len(set(keys)) != 3:
        raise DFTEnergeticsError("adsorption-energy keys must identify three distinct entries")
    stoichiometry = _finite_real(
        adsorbate_stoichiometry,
        name="adsorbate_stoichiometry",
    )
    if stoichiometry <= 0.0:
        raise DFTEnergeticsError("adsorbate_stoichiometry must be positive")
    label = expression_label or (
        f"E({keys[0]}) - E({keys[1]}) - {stoichiometry:g}*E({keys[2]})"
    )
    return combine_energies(
        ledger,
        (
            EnergyTerm(keys[0], 1.0),
            EnergyTerm(keys[1], -1.0),
            EnergyTerm(keys[2], -stoichiometry),
        ),
        expression_label=label,
        result_basis=result_basis,
    )


def dft_energy_entries_frame(ledger: DFTEnergyLedger) -> pd.DataFrame:
    """Return a detached reporting table for the retained energy ledger."""
    if not isinstance(ledger, DFTEnergyLedger):
        raise TypeError("ledger must be a DFTEnergyLedger")
    rows = [
        {
            "ledger_source_id": ledger.source_id,
            "ledger_digest": ledger.digest,
            "entry_key": entry.key,
            "entry_label": entry.label,
            "energy_ev": entry.energy_ev,
            "normalization_basis": entry.normalization_basis,
            "entry_source_id": entry.source_id,
        }
        for entry in ledger.entries
    ]
    frame = pd.DataFrame.from_records(rows)
    for column in ("entry_label", "normalization_basis", "entry_source_id"):
        frame[column] = pd.Series([row[column] for row in rows], dtype=object)
    return frame


def relative_energy_frame(result: RelativeEnergyResult) -> pd.DataFrame:
    """Return a detached one-row-per-state relative-energy table."""
    if not isinstance(result, RelativeEnergyResult):
        raise TypeError("result must be a RelativeEnergyResult")
    return pd.DataFrame.from_records(
        [
            {
                "ledger_digest": result.ledger_digest,
                "reference_key": result.reference_key,
                "entry_key": key,
                "entry_label": label,
                "energy_ev": energy,
                "delta_energy_ev": delta,
                "normalization_basis": result.normalization_basis,
            }
            for key, label, energy, delta in zip(
                result.entry_keys,
                result.entry_labels,
                result.energies_ev,
                result.delta_energy_ev,
                strict=True,
            )
        ]
    )


def energy_combination_frame(result: EnergyCombinationResult) -> pd.DataFrame:
    """Return a detached term-by-term audit table for one linear combination."""
    if not isinstance(result, EnergyCombinationResult):
        raise TypeError("result must be an EnergyCombinationResult")
    return pd.DataFrame.from_records(
        [
            {
                "ledger_digest": result.ledger_digest,
                "expression_label": result.expression_label,
                "result_basis": result.result_basis,
                "entry_key": term.entry_key,
                "coefficient": term.coefficient,
                "entry_energy_ev": energy,
                "contribution_ev": contribution,
                "result_value_ev": result.value_ev,
            }
            for term, energy, contribution in zip(
                result.terms,
                result.term_energies_ev,
                result.contributions_ev,
                strict=True,
            )
        ]
    )


__all__ = [
    "DFTEnergeticsError",
    "DFTEnergyEntry",
    "DFTEnergyLedger",
    "EnergyCombinationResult",
    "EnergyTerm",
    "RelativeEnergyResult",
    "adsorption_energy",
    "combine_energies",
    "dft_energy_entries_frame",
    "energy_combination_frame",
    "relative_energies",
    "relative_energy_frame",
]
