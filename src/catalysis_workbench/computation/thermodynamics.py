"""Explicit free-energy thermodynamics and Computational Hydrogen Electrode state."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass, field
from math import isfinite, log

import numpy as np
import pandas as pd

from .dft_energetics import DFTEnergyLedger

BOLTZMANN_EV_PER_K = 8.617333262145e-5
_ALLOWED_POTENTIAL_REFERENCES = frozenset({"SHE", "RHE"})
_ALLOWED_REACTION_SOURCE_TYPES = frozenset(
    {"thermodynamic_state", "che_proton_electron_pair"}
)
_ALLOWED_CONTRIBUTION_TYPES = frozenset(
    {
        "electronic_dft",
        "zpe",
        "thermal_enthalpy",
        "entropy",
        "additional_correction",
    }
)
_CHE_PAIR_BASIS = "per proton-electron pair"


class ThermodynamicsError(ValueError):
    """Raised when explicit thermodynamic or CHE state is inconsistent."""


def _finite_real(value: object, *, name: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise TypeError(f"{name} must be a finite real numeric value")
    try:
        source = np.asarray(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a finite real numeric value") from exc
    if np.iscomplexobj(source) or source.ndim != 0 or source.dtype.kind not in "biuf":
        raise TypeError(f"{name} must be a finite real numeric value")
    number = float(value)
    if not isfinite(number):
        raise ThermodynamicsError(f"{name} must be finite")
    return number


def _positive_real(value: object, *, name: str) -> float:
    number = _finite_real(value, name=name)
    if number <= 0.0:
        raise ThermodynamicsError(f"{name} must be greater than zero")
    return number


def _optional_real(value: object | None, *, name: str) -> float | None:
    if value is None:
        return None
    return _finite_real(value, name=name)


def _required_text(value: object, *, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ThermodynamicsError(f"{name} must not be blank")
    return text


def _optional_text(value: object | None, *, name: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, name=name)


def _boolean(value: object, *, name: str) -> bool:
    if not isinstance(value, (bool, np.bool_)):
        raise TypeError(f"{name} must be boolean")
    return bool(value)


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
        return
    digest.update(b"value\0")
    digest.update(np.float64(value).tobytes())


@dataclass(frozen=True, slots=True, eq=False)
class FreeEnergyCorrection:
    """One caller-supplied additive free-energy correction in eV."""

    key: str
    correction_type: str
    value_ev: float
    source_id: str
    label: str | None = None
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        key = _required_text(self.key, name="correction key")
        correction_type = _required_text(self.correction_type, name="correction_type")
        value = _finite_real(self.value_ev, name="correction value_ev")
        source_id = _required_text(self.source_id, name="correction source_id")
        label = _optional_text(self.label, name="correction label")

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.FreeEnergyCorrection.v1\0")
        for text in (key, correction_type, source_id):
            _digest_text(digest, text)
        _digest_float(digest, value)

        object.__setattr__(self, "key", key)
        object.__setattr__(self, "correction_type", correction_type)
        object.__setattr__(self, "value_ev", value)
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "digest", digest.hexdigest())

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, FreeEnergyCorrection)
            and self.digest == other.digest
            and self.label == other.label
        )


@dataclass(frozen=True, slots=True, eq=False)
class ThermodynamicEntry:
    """Explicit corrections attached to one exact v0.5 DFT-ledger entry key."""

    key: str
    dft_entry_key: str
    zpe_ev: float | None = None
    thermal_enthalpy_correction_ev: float | None = None
    entropy_ev_per_k: float | None = None
    temperature_k: float | None = None
    corrections: Sequence[FreeEnergyCorrection] = ()
    label: str | None = None
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        key = _required_text(self.key, name="thermodynamic key")
        dft_key = _required_text(self.dft_entry_key, name="dft_entry_key")
        zpe = _optional_real(self.zpe_ev, name="zpe_ev")
        thermal = _optional_real(
            self.thermal_enthalpy_correction_ev,
            name="thermal_enthalpy_correction_ev",
        )
        entropy = _optional_real(self.entropy_ev_per_k, name="entropy_ev_per_k")
        temperature = (
            None
            if self.temperature_k is None
            else _positive_real(self.temperature_k, name="temperature_k")
        )
        if (thermal is not None or entropy is not None) and temperature is None:
            raise ThermodynamicsError(
                "temperature_k is required when thermal enthalpy or entropy is supplied"
            )

        corrections = tuple(self.corrections)
        if not all(isinstance(item, FreeEnergyCorrection) for item in corrections):
            raise TypeError("corrections must contain only FreeEnergyCorrection instances")
        correction_keys = [item.key for item in corrections]
        if len(correction_keys) != len(set(correction_keys)):
            raise ThermodynamicsError("additional correction keys must be unique")
        canonical_corrections = tuple(sorted(corrections, key=lambda item: item.key))
        label = _optional_text(self.label, name="thermodynamic label")

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.ThermodynamicEntry.v1\0")
        for text in (key, dft_key):
            _digest_text(digest, text)
        for value in (zpe, thermal, entropy, temperature):
            _digest_float(digest, value)
        for correction in canonical_corrections:
            _digest_text(digest, correction.digest)

        object.__setattr__(self, "key", key)
        object.__setattr__(self, "dft_entry_key", dft_key)
        object.__setattr__(self, "zpe_ev", zpe)
        object.__setattr__(self, "thermal_enthalpy_correction_ev", thermal)
        object.__setattr__(self, "entropy_ev_per_k", entropy)
        object.__setattr__(self, "temperature_k", temperature)
        object.__setattr__(self, "corrections", canonical_corrections)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "digest", digest.hexdigest())

    def correction(self, key: str) -> FreeEnergyCorrection:
        """Return one explicitly supplied correction by stable key."""
        requested = _required_text(key, name="correction key")
        for correction in self.corrections:
            if correction.key == requested:
                return correction
        raise ThermodynamicsError(f"unknown additional correction key: {requested}")

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, ThermodynamicEntry)
            and self.digest == other.digest
            and self.label == other.label
        )


@dataclass(frozen=True, slots=True, eq=False)
class FreeEnergyRecipe:
    """Explicit allowlist of thermodynamic terms that enter one evaluation."""

    key: str
    include_zpe: bool = False
    include_thermal_enthalpy: bool = False
    include_entropy: bool = False
    correction_keys: Sequence[str] = ()
    label: str | None = None
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        key = _required_text(self.key, name="recipe key")
        include_zpe = _boolean(self.include_zpe, name="include_zpe")
        include_thermal = _boolean(
            self.include_thermal_enthalpy,
            name="include_thermal_enthalpy",
        )
        include_entropy = _boolean(self.include_entropy, name="include_entropy")
        correction_keys = tuple(
            _required_text(value, name="recipe correction key")
            for value in self.correction_keys
        )
        if len(correction_keys) != len(set(correction_keys)):
            raise ThermodynamicsError("recipe correction_keys must be unique")
        canonical_keys = tuple(sorted(correction_keys))
        label = _optional_text(self.label, name="recipe label")

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.FreeEnergyRecipe.v1\0")
        _digest_text(digest, key)
        digest.update(bytes((include_zpe, include_thermal, include_entropy)))
        for correction_key in canonical_keys:
            _digest_text(digest, correction_key)

        object.__setattr__(self, "key", key)
        object.__setattr__(self, "include_zpe", include_zpe)
        object.__setattr__(self, "include_thermal_enthalpy", include_thermal)
        object.__setattr__(self, "include_entropy", include_entropy)
        object.__setattr__(self, "correction_keys", canonical_keys)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "digest", digest.hexdigest())

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, FreeEnergyRecipe)
            and self.digest == other.digest
            and self.label == other.label
        )


@dataclass(frozen=True, slots=True, eq=False)
class FreeEnergyContribution:
    """One reconstructible contribution retained in an evaluated free energy."""

    key: str
    contribution_type: str
    value_ev: float
    source_key: str
    source_digest: str
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        key = _required_text(self.key, name="contribution key")
        contribution_type = _required_text(
            self.contribution_type,
            name="contribution_type",
        )
        if contribution_type not in _ALLOWED_CONTRIBUTION_TYPES:
            raise ThermodynamicsError(
                "unsupported contribution_type: " + contribution_type
            )
        value = _finite_real(self.value_ev, name="contribution value_ev")
        source_key = _required_text(self.source_key, name="contribution source_key")
        source_digest = _required_text(
            self.source_digest,
            name="contribution source_digest",
        )

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.FreeEnergyContribution.v1\0")
        for text in (key, contribution_type, source_key, source_digest):
            _digest_text(digest, text)
        _digest_float(digest, value)

        object.__setattr__(self, "key", key)
        object.__setattr__(self, "contribution_type", contribution_type)
        object.__setattr__(self, "value_ev", value)
        object.__setattr__(self, "source_key", source_key)
        object.__setattr__(self, "source_digest", source_digest)
        object.__setattr__(self, "digest", digest.hexdigest())

    def __eq__(self, other: object) -> bool:
        return isinstance(other, FreeEnergyContribution) and self.digest == other.digest


@dataclass(frozen=True, slots=True, eq=False)
class FreeEnergyEvaluation:
    """One explicit, reconstructible thermodynamic free-energy evaluation."""

    key: str
    thermodynamic_entry_digest: str
    recipe_digest: str
    ledger_digest: str
    dft_entry_key: str
    normalization_basis: str
    temperature_k: float | None
    contributions: Sequence[FreeEnergyContribution]
    free_energy_ev: float
    label: str | None = None
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        key = _required_text(self.key, name="evaluation key")
        entry_digest = _required_text(
            self.thermodynamic_entry_digest,
            name="thermodynamic_entry_digest",
        )
        recipe_digest = _required_text(self.recipe_digest, name="recipe_digest")
        ledger_digest = _required_text(self.ledger_digest, name="ledger_digest")
        dft_entry_key = _required_text(self.dft_entry_key, name="dft_entry_key")
        basis = _required_text(self.normalization_basis, name="normalization_basis")
        temperature = (
            None
            if self.temperature_k is None
            else _positive_real(self.temperature_k, name="temperature_k")
        )
        contributions = tuple(self.contributions)
        if not contributions or not all(
            isinstance(item, FreeEnergyContribution) for item in contributions
        ):
            raise ThermodynamicsError(
                "contributions must contain at least one FreeEnergyContribution"
            )
        keys = [item.key for item in contributions]
        if len(keys) != len(set(keys)):
            raise ThermodynamicsError("free-energy contribution keys must be unique")
        if sum(item.contribution_type == "electronic_dft" for item in contributions) != 1:
            raise ThermodynamicsError(
                "free-energy evaluation requires exactly one electronic_dft contribution"
            )
        if any(
            item.contribution_type in {"thermal_enthalpy", "entropy"}
            for item in contributions
        ) and temperature is None:
            raise ThermodynamicsError(
                "temperature_k is required for retained thermal/entropy contributions"
            )
        free_energy = _finite_real(self.free_energy_ev, name="free_energy_ev")
        expected = float(sum(item.value_ev for item in contributions))
        if not np.isclose(free_energy, expected, rtol=1e-12, atol=1e-12):
            raise ThermodynamicsError(
                "free_energy_ev contradicts retained contributions"
            )
        label = _optional_text(self.label, name="evaluation label")

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.FreeEnergyEvaluation.v1\0")
        for text in (key, entry_digest, recipe_digest, ledger_digest, dft_entry_key, basis):
            _digest_text(digest, text)
        _digest_float(digest, temperature)
        for contribution in contributions:
            _digest_text(digest, contribution.digest)
        _digest_float(digest, free_energy)

        object.__setattr__(self, "key", key)
        object.__setattr__(self, "thermodynamic_entry_digest", entry_digest)
        object.__setattr__(self, "recipe_digest", recipe_digest)
        object.__setattr__(self, "ledger_digest", ledger_digest)
        object.__setattr__(self, "dft_entry_key", dft_entry_key)
        object.__setattr__(self, "normalization_basis", basis)
        object.__setattr__(self, "temperature_k", temperature)
        object.__setattr__(self, "contributions", contributions)
        object.__setattr__(self, "free_energy_ev", free_energy)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "digest", digest.hexdigest())

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, FreeEnergyEvaluation)
            and self.digest == other.digest
            and self.label == other.label
        )


def evaluate_free_energy(
    ledger: DFTEnergyLedger,
    entry: ThermodynamicEntry,
    recipe: FreeEnergyRecipe,
) -> FreeEnergyEvaluation:
    """Evaluate only the explicitly selected free-energy terms."""
    if not isinstance(ledger, DFTEnergyLedger):
        raise TypeError("ledger must be a DFTEnergyLedger")
    if not isinstance(entry, ThermodynamicEntry):
        raise TypeError("entry must be a ThermodynamicEntry")
    if not isinstance(recipe, FreeEnergyRecipe):
        raise TypeError("recipe must be a FreeEnergyRecipe")

    try:
        dft_entry = ledger.entry(entry.dft_entry_key)
    except ValueError as exc:
        raise ThermodynamicsError(
            f"thermodynamic entry references unknown DFT entry: {entry.dft_entry_key}"
        ) from exc
    basis = dft_entry.normalization_basis
    if basis is None:
        raise ThermodynamicsError(
            "free-energy evaluation requires an explicit DFT normalization_basis"
        )

    contributions: list[FreeEnergyContribution] = [
        FreeEnergyContribution(
            key="electronic_dft",
            contribution_type="electronic_dft",
            value_ev=dft_entry.energy_ev,
            source_key=dft_entry.key,
            source_digest=ledger.digest,
        )
    ]

    if recipe.include_zpe:
        if entry.zpe_ev is None:
            raise ThermodynamicsError("recipe requests ZPE but zpe_ev was not supplied")
        contributions.append(
            FreeEnergyContribution(
                key="zpe",
                contribution_type="zpe",
                value_ev=entry.zpe_ev,
                source_key=entry.key,
                source_digest=entry.digest,
            )
        )
    if recipe.include_thermal_enthalpy:
        if entry.thermal_enthalpy_correction_ev is None:
            raise ThermodynamicsError(
                "recipe requests thermal enthalpy but the correction was not supplied"
            )
        contributions.append(
            FreeEnergyContribution(
                key="thermal_enthalpy",
                contribution_type="thermal_enthalpy",
                value_ev=entry.thermal_enthalpy_correction_ev,
                source_key=entry.key,
                source_digest=entry.digest,
            )
        )
    if recipe.include_entropy:
        if entry.entropy_ev_per_k is None:
            raise ThermodynamicsError(
                "recipe requests entropy but entropy_ev_per_k was not supplied"
            )
        if entry.temperature_k is None:
            raise ThermodynamicsError(
                "recipe requests entropy but temperature_k was not supplied"
            )
        contributions.append(
            FreeEnergyContribution(
                key="entropy_minus_t_s",
                contribution_type="entropy",
                value_ev=-entry.temperature_k * entry.entropy_ev_per_k,
                source_key=entry.key,
                source_digest=entry.digest,
            )
        )

    selected_corrections: list[FreeEnergyCorrection] = []
    for key in recipe.correction_keys:
        try:
            selected_corrections.append(entry.correction(key))
        except ThermodynamicsError as exc:
            raise ThermodynamicsError(
                f"recipe requests unavailable additional correction: {key}"
            ) from exc
    for correction in selected_corrections:
        contributions.append(
            FreeEnergyContribution(
                key=f"correction:{correction.key}",
                contribution_type="additional_correction",
                value_ev=correction.value_ev,
                source_key=correction.key,
                source_digest=correction.digest,
            )
        )

    value = float(sum(item.value_ev for item in contributions))
    return FreeEnergyEvaluation(
        key=entry.key,
        thermodynamic_entry_digest=entry.digest,
        recipe_digest=recipe.digest,
        ledger_digest=ledger.digest,
        dft_entry_key=dft_entry.key,
        normalization_basis=basis,
        temperature_k=entry.temperature_k,
        contributions=tuple(contributions),
        free_energy_ev=value,
        label=entry.label,
    )


@dataclass(frozen=True, slots=True, eq=False)
class CHEState:
    """Explicit temperature, pH, potential, and reference state for CHE arithmetic."""

    temperature_k: float
    ph: float
    potential_v: float
    potential_reference: str
    boltzmann_ev_per_k: float = BOLTZMANN_EV_PER_K
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        temperature = _positive_real(self.temperature_k, name="temperature_k")
        ph = _finite_real(self.ph, name="ph")
        potential = _finite_real(self.potential_v, name="potential_v")
        reference = _required_text(
            self.potential_reference,
            name="potential_reference",
        ).upper()
        if reference not in _ALLOWED_POTENTIAL_REFERENCES:
            raise ThermodynamicsError("potential_reference must be SHE or RHE")
        boltzmann = _positive_real(
            self.boltzmann_ev_per_k,
            name="boltzmann_ev_per_k",
        )

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.CHEState.v1\0")
        for value in (temperature, ph, potential, boltzmann):
            _digest_float(digest, value)
        _digest_text(digest, reference)

        object.__setattr__(self, "temperature_k", temperature)
        object.__setattr__(self, "ph", ph)
        object.__setattr__(self, "potential_v", potential)
        object.__setattr__(self, "potential_reference", reference)
        object.__setattr__(self, "boltzmann_ev_per_k", boltzmann)
        object.__setattr__(self, "digest", digest.hexdigest())

    def __eq__(self, other: object) -> bool:
        return isinstance(other, CHEState) and self.digest == other.digest


@dataclass(frozen=True, slots=True, eq=False)
class CHEProtonElectronResult:
    """Explicit one-pair CHE chemical potential evaluated through the SHE equation."""

    h2_evaluation_key: str
    h2_evaluation_digest: str
    h2_normalization_basis: str
    h2_temperature_k: float | None
    h2_free_energy_ev: float
    che_state_digest: str
    temperature_k: float
    ph: float
    input_potential_v: float
    input_potential_reference: str
    boltzmann_ev_per_k: float
    nernst_ph_shift_v: float
    potential_she_v: float
    half_h2_ev: float
    potential_contribution_ev: float
    ph_contribution_ev: float
    mu_ev: float
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        h2_key = _required_text(self.h2_evaluation_key, name="h2_evaluation_key")
        h2_digest = _required_text(
            self.h2_evaluation_digest,
            name="h2_evaluation_digest",
        )
        h2_basis = _required_text(
            self.h2_normalization_basis,
            name="h2_normalization_basis",
        )
        h2_temperature = (
            None
            if self.h2_temperature_k is None
            else _positive_real(self.h2_temperature_k, name="h2_temperature_k")
        )
        h2_energy = _finite_real(self.h2_free_energy_ev, name="h2_free_energy_ev")
        state_digest = _required_text(self.che_state_digest, name="che_state_digest")
        temperature = _positive_real(self.temperature_k, name="temperature_k")
        ph = _finite_real(self.ph, name="ph")
        input_potential = _finite_real(
            self.input_potential_v,
            name="input_potential_v",
        )
        reference = _required_text(
            self.input_potential_reference,
            name="input_potential_reference",
        ).upper()
        if reference not in _ALLOWED_POTENTIAL_REFERENCES:
            raise ThermodynamicsError("input_potential_reference must be SHE or RHE")
        boltzmann = _positive_real(
            self.boltzmann_ev_per_k,
            name="boltzmann_ev_per_k",
        )
        shift = _finite_real(self.nernst_ph_shift_v, name="nernst_ph_shift_v")
        potential_she = _finite_real(self.potential_she_v, name="potential_she_v")
        half_h2 = _finite_real(self.half_h2_ev, name="half_h2_ev")
        potential_contribution = _finite_real(
            self.potential_contribution_ev,
            name="potential_contribution_ev",
        )
        ph_contribution = _finite_real(
            self.ph_contribution_ev,
            name="ph_contribution_ev",
        )
        mu = _finite_real(self.mu_ev, name="mu_ev")

        expected_shift = boltzmann * temperature * log(10.0) * ph
        expected_she = (
            input_potential
            if reference == "SHE"
            else input_potential - expected_shift
        )
        expected_half_h2 = 0.5 * h2_energy
        expected_potential_contribution = -expected_she
        expected_ph_contribution = -expected_shift
        expected_mu = (
            expected_half_h2
            + expected_potential_contribution
            + expected_ph_contribution
        )
        checks = (
            (shift, expected_shift, "nernst_ph_shift_v"),
            (potential_she, expected_she, "potential_she_v"),
            (half_h2, expected_half_h2, "half_h2_ev"),
            (
                potential_contribution,
                expected_potential_contribution,
                "potential_contribution_ev",
            ),
            (ph_contribution, expected_ph_contribution, "ph_contribution_ev"),
            (mu, expected_mu, "mu_ev"),
        )
        for retained, expected, name in checks:
            if not np.isclose(retained, expected, rtol=1e-12, atol=1e-12):
                raise ThermodynamicsError(f"{name} contradicts retained CHE state")
        if h2_temperature is not None and not np.isclose(
            h2_temperature,
            temperature,
            rtol=1e-12,
            atol=1e-12,
        ):
            raise ThermodynamicsError(
                "temperature_k must match the temperature of the evaluated H2 free energy"
            )

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.CHEProtonElectronResult.v1\0")
        for text in (h2_key, h2_digest, h2_basis, state_digest, reference):
            _digest_text(digest, text)
        for value in (
            h2_temperature,
            h2_energy,
            temperature,
            ph,
            input_potential,
            boltzmann,
            shift,
            potential_she,
            half_h2,
            potential_contribution,
            ph_contribution,
            mu,
        ):
            _digest_float(digest, value)

        object.__setattr__(self, "h2_evaluation_key", h2_key)
        object.__setattr__(self, "h2_evaluation_digest", h2_digest)
        object.__setattr__(self, "h2_normalization_basis", h2_basis)
        object.__setattr__(self, "h2_temperature_k", h2_temperature)
        object.__setattr__(self, "h2_free_energy_ev", h2_energy)
        object.__setattr__(self, "che_state_digest", state_digest)
        object.__setattr__(self, "temperature_k", temperature)
        object.__setattr__(self, "ph", ph)
        object.__setattr__(self, "input_potential_v", input_potential)
        object.__setattr__(self, "input_potential_reference", reference)
        object.__setattr__(self, "boltzmann_ev_per_k", boltzmann)
        object.__setattr__(self, "nernst_ph_shift_v", shift)
        object.__setattr__(self, "potential_she_v", potential_she)
        object.__setattr__(self, "half_h2_ev", half_h2)
        object.__setattr__(self, "potential_contribution_ev", potential_contribution)
        object.__setattr__(self, "ph_contribution_ev", ph_contribution)
        object.__setattr__(self, "mu_ev", mu)
        object.__setattr__(self, "digest", digest.hexdigest())

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, CHEProtonElectronResult)
            and self.digest == other.digest
        )


def evaluate_che_proton_electron(
    h2_free_energy: FreeEnergyEvaluation,
    state: CHEState,
) -> CHEProtonElectronResult:
    """Evaluate one proton-electron pair through the retained SHE-form CHE equation."""
    if not isinstance(h2_free_energy, FreeEnergyEvaluation):
        raise TypeError("h2_free_energy must be a FreeEnergyEvaluation")
    if not isinstance(state, CHEState):
        raise TypeError("state must be a CHEState")
    if h2_free_energy.temperature_k is not None and not np.isclose(
        h2_free_energy.temperature_k,
        state.temperature_k,
        rtol=1e-12,
        atol=1e-12,
    ):
        raise ThermodynamicsError(
            "CHE temperature must match the evaluated H2 free-energy temperature"
        )

    shift = state.boltzmann_ev_per_k * state.temperature_k * log(10.0) * state.ph
    potential_she = (
        state.potential_v
        if state.potential_reference == "SHE"
        else state.potential_v - shift
    )
    half_h2 = 0.5 * h2_free_energy.free_energy_ev
    potential_contribution = -potential_she
    ph_contribution = -shift
    mu = half_h2 + potential_contribution + ph_contribution
    return CHEProtonElectronResult(
        h2_evaluation_key=h2_free_energy.key,
        h2_evaluation_digest=h2_free_energy.digest,
        h2_normalization_basis=h2_free_energy.normalization_basis,
        h2_temperature_k=h2_free_energy.temperature_k,
        h2_free_energy_ev=h2_free_energy.free_energy_ev,
        che_state_digest=state.digest,
        temperature_k=state.temperature_k,
        ph=state.ph,
        input_potential_v=state.potential_v,
        input_potential_reference=state.potential_reference,
        boltzmann_ev_per_k=state.boltzmann_ev_per_k,
        nernst_ph_shift_v=shift,
        potential_she_v=potential_she,
        half_h2_ev=half_h2,
        potential_contribution_ev=potential_contribution,
        ph_contribution_ev=ph_contribution,
        mu_ev=mu,
    )


@dataclass(frozen=True, slots=True, eq=False)
class ReactionFreeEnergyTerm:
    """One explicit products-positive/reactants-negative reaction term."""

    source_key: str
    source_type: str
    coefficient: float
    value_ev: float
    source_digest: str
    normalization_basis: str
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        source_key = _required_text(self.source_key, name="reaction source_key")
        source_type = _required_text(self.source_type, name="reaction source_type")
        if source_type not in _ALLOWED_REACTION_SOURCE_TYPES:
            raise ThermodynamicsError("unsupported reaction source_type: " + source_type)
        coefficient = _finite_real(self.coefficient, name="reaction coefficient")
        value = _finite_real(self.value_ev, name="reaction value_ev")
        source_digest = _required_text(
            self.source_digest,
            name="reaction source_digest",
        )
        basis = _required_text(self.normalization_basis, name="normalization_basis")
        if source_type == "che_proton_electron_pair" and basis != _CHE_PAIR_BASIS:
            raise ThermodynamicsError(
                f"CHE reaction terms must use normalization_basis={_CHE_PAIR_BASIS!r}"
            )

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.ReactionFreeEnergyTerm.v1\0")
        for text in (source_key, source_type, source_digest, basis):
            _digest_text(digest, text)
        _digest_float(digest, coefficient)
        _digest_float(digest, value)

        object.__setattr__(self, "source_key", source_key)
        object.__setattr__(self, "source_type", source_type)
        object.__setattr__(self, "coefficient", coefficient)
        object.__setattr__(self, "value_ev", value)
        object.__setattr__(self, "source_digest", source_digest)
        object.__setattr__(self, "normalization_basis", basis)
        object.__setattr__(self, "digest", digest.hexdigest())

    @property
    def contribution_ev(self) -> float:
        return self.coefficient * self.value_ev

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ReactionFreeEnergyTerm) and self.digest == other.digest


def thermodynamic_reaction_term(
    evaluation: FreeEnergyEvaluation,
    coefficient: float,
) -> ReactionFreeEnergyTerm:
    """Create an explicit reaction term from one evaluated thermodynamic state."""
    if not isinstance(evaluation, FreeEnergyEvaluation):
        raise TypeError("evaluation must be a FreeEnergyEvaluation")
    return ReactionFreeEnergyTerm(
        source_key=evaluation.key,
        source_type="thermodynamic_state",
        coefficient=coefficient,
        value_ev=evaluation.free_energy_ev,
        source_digest=evaluation.digest,
        normalization_basis=evaluation.normalization_basis,
    )


def che_reaction_term(
    che_result: CHEProtonElectronResult,
    coefficient: float,
    *,
    source_key: str = "H+ + e-",
) -> ReactionFreeEnergyTerm:
    """Create an explicit reaction term for one-pair CHE chemical potential."""
    if not isinstance(che_result, CHEProtonElectronResult):
        raise TypeError("che_result must be a CHEProtonElectronResult")
    return ReactionFreeEnergyTerm(
        source_key=source_key,
        source_type="che_proton_electron_pair",
        coefficient=coefficient,
        value_ev=che_result.mu_ev,
        source_digest=che_result.digest,
        normalization_basis=_CHE_PAIR_BASIS,
    )


@dataclass(frozen=True, slots=True, eq=False)
class ReactionFreeEnergyResult:
    """Reconstructible explicit reaction free energy from retained terms."""

    terms: Sequence[ReactionFreeEnergyTerm]
    delta_g_ev: float
    expression_label: str
    thermodynamic_normalization_basis: str | None
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        terms = tuple(self.terms)
        if not terms or not all(isinstance(item, ReactionFreeEnergyTerm) for item in terms):
            raise ThermodynamicsError(
                "terms must contain at least one ReactionFreeEnergyTerm"
            )
        identities = [(item.source_type, item.source_key) for item in terms]
        if len(identities) != len(set(identities)):
            raise ThermodynamicsError("reaction source identities must be unique")
        thermo_bases = {
            item.normalization_basis
            for item in terms
            if item.source_type == "thermodynamic_state"
        }
        if len(thermo_bases) > 1:
            raise ThermodynamicsError(
                "thermodynamic reaction terms require one matching normalization_basis"
            )
        expected_basis = next(iter(thermo_bases), None)
        retained_basis = _optional_text(
            self.thermodynamic_normalization_basis,
            name="thermodynamic_normalization_basis",
        )
        if retained_basis != expected_basis:
            raise ThermodynamicsError(
                "thermodynamic_normalization_basis contradicts retained reaction terms"
            )
        delta = _finite_real(self.delta_g_ev, name="delta_g_ev")
        expected = float(sum(item.contribution_ev for item in terms))
        if not np.isclose(delta, expected, rtol=1e-12, atol=1e-12):
            raise ThermodynamicsError("delta_g_ev contradicts retained reaction terms")
        expression_label = _required_text(self.expression_label, name="expression_label")

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.ReactionFreeEnergyResult.v1\0")
        for term in terms:
            _digest_text(digest, term.digest)
        _digest_float(digest, delta)
        _digest_text(digest, retained_basis)

        object.__setattr__(self, "terms", terms)
        object.__setattr__(self, "delta_g_ev", delta)
        object.__setattr__(self, "expression_label", expression_label)
        object.__setattr__(self, "thermodynamic_normalization_basis", retained_basis)
        object.__setattr__(self, "digest", digest.hexdigest())

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, ReactionFreeEnergyResult)
            and self.digest == other.digest
            and self.expression_label == other.expression_label
        )


def reaction_free_energy(
    terms: Sequence[ReactionFreeEnergyTerm],
    *,
    expression_label: str,
) -> ReactionFreeEnergyResult:
    """Evaluate explicit products-positive/reactants-negative free-energy arithmetic."""
    retained_terms = tuple(terms)
    if not retained_terms or not all(
        isinstance(item, ReactionFreeEnergyTerm) for item in retained_terms
    ):
        raise ThermodynamicsError(
            "terms must contain at least one ReactionFreeEnergyTerm"
        )
    thermo_bases = {
        item.normalization_basis
        for item in retained_terms
        if item.source_type == "thermodynamic_state"
    }
    if len(thermo_bases) > 1:
        raise ThermodynamicsError(
            "thermodynamic reaction terms require one matching normalization_basis"
        )
    basis = next(iter(thermo_bases), None)
    return ReactionFreeEnergyResult(
        terms=retained_terms,
        delta_g_ev=float(sum(item.contribution_ev for item in retained_terms)),
        expression_label=expression_label,
        thermodynamic_normalization_basis=basis,
    )


def thermodynamic_entry_frame(entry: ThermodynamicEntry) -> pd.DataFrame:
    """Return one detached row with explicit supplied/not-supplied component state."""
    if not isinstance(entry, ThermodynamicEntry):
        raise TypeError("entry must be a ThermodynamicEntry")
    return pd.DataFrame(
        [
            {
                "entry_digest": entry.digest,
                "thermodynamic_key": entry.key,
                "label": entry.label,
                "dft_entry_key": entry.dft_entry_key,
                "zpe_ev": entry.zpe_ev,
                "zpe_supplied": entry.zpe_ev is not None,
                "thermal_enthalpy_correction_ev": entry.thermal_enthalpy_correction_ev,
                "thermal_enthalpy_supplied": (
                    entry.thermal_enthalpy_correction_ev is not None
                ),
                "entropy_ev_per_k": entry.entropy_ev_per_k,
                "entropy_supplied": entry.entropy_ev_per_k is not None,
                "temperature_k": entry.temperature_k,
                "correction_keys": tuple(item.key for item in entry.corrections),
                "correction_types": tuple(
                    item.correction_type for item in entry.corrections
                ),
                "correction_values_ev": tuple(item.value_ev for item in entry.corrections),
                "correction_source_ids": tuple(item.source_id for item in entry.corrections),
            }
        ]
    )


def free_energy_contributions_frame(evaluation: FreeEnergyEvaluation) -> pd.DataFrame:
    """Return a detached one-row-per-contribution free-energy table."""
    if not isinstance(evaluation, FreeEnergyEvaluation):
        raise TypeError("evaluation must be a FreeEnergyEvaluation")
    return pd.DataFrame(
        [
            {
                "evaluation_digest": evaluation.digest,
                "evaluation_key": evaluation.key,
                "ledger_digest": evaluation.ledger_digest,
                "dft_entry_key": evaluation.dft_entry_key,
                "normalization_basis": evaluation.normalization_basis,
                "temperature_k": evaluation.temperature_k,
                "contribution_key": item.key,
                "contribution_type": item.contribution_type,
                "value_ev": item.value_ev,
                "source_key": item.source_key,
                "source_digest": item.source_digest,
                "free_energy_ev": evaluation.free_energy_ev,
            }
            for item in evaluation.contributions
        ]
    )


def che_result_frame(result: CHEProtonElectronResult) -> pd.DataFrame:
    """Return a detached one-row CHE state and contribution table."""
    if not isinstance(result, CHEProtonElectronResult):
        raise TypeError("result must be a CHEProtonElectronResult")
    return pd.DataFrame(
        [
            {
                "che_digest": result.digest,
                "h2_evaluation_key": result.h2_evaluation_key,
                "h2_evaluation_digest": result.h2_evaluation_digest,
                "h2_normalization_basis": result.h2_normalization_basis,
                "h2_temperature_k": result.h2_temperature_k,
                "h2_free_energy_ev": result.h2_free_energy_ev,
                "temperature_k": result.temperature_k,
                "ph": result.ph,
                "input_potential_v": result.input_potential_v,
                "input_potential_reference": result.input_potential_reference,
                "boltzmann_ev_per_k": result.boltzmann_ev_per_k,
                "nernst_ph_shift_v": result.nernst_ph_shift_v,
                "potential_she_v": result.potential_she_v,
                "half_h2_ev": result.half_h2_ev,
                "potential_contribution_ev": result.potential_contribution_ev,
                "ph_contribution_ev": result.ph_contribution_ev,
                "mu_ev": result.mu_ev,
            }
        ]
    )


def reaction_free_energy_frame(result: ReactionFreeEnergyResult) -> pd.DataFrame:
    """Return a detached one-row-per-term reaction free-energy table."""
    if not isinstance(result, ReactionFreeEnergyResult):
        raise TypeError("result must be a ReactionFreeEnergyResult")
    return pd.DataFrame(
        [
            {
                "reaction_digest": result.digest,
                "expression_label": result.expression_label,
                "thermodynamic_normalization_basis": (
                    result.thermodynamic_normalization_basis
                ),
                "source_key": item.source_key,
                "source_type": item.source_type,
                "source_digest": item.source_digest,
                "normalization_basis": item.normalization_basis,
                "coefficient": item.coefficient,
                "value_ev": item.value_ev,
                "contribution_ev": item.contribution_ev,
                "delta_g_ev": result.delta_g_ev,
            }
            for item in result.terms
        ]
    )


__all__ = [
    "BOLTZMANN_EV_PER_K",
    "CHEProtonElectronResult",
    "CHEState",
    "FreeEnergyContribution",
    "FreeEnergyCorrection",
    "FreeEnergyEvaluation",
    "FreeEnergyRecipe",
    "ReactionFreeEnergyResult",
    "ReactionFreeEnergyTerm",
    "ThermodynamicEntry",
    "ThermodynamicsError",
    "che_reaction_term",
    "che_result_frame",
    "evaluate_che_proton_electron",
    "evaluate_free_energy",
    "free_energy_contributions_frame",
    "reaction_free_energy",
    "reaction_free_energy_frame",
    "thermodynamic_entry_frame",
    "thermodynamic_reaction_term",
]
