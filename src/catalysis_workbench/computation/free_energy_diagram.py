"""Explicit retained state for passive free-energy diagrams."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass, field
from math import isfinite

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from .thermodynamics import CHEProtonElectronResult, FreeEnergyEvaluation


class FreeEnergyDiagramError(ValueError):
    """Raised when retained free-energy-diagram state is scientifically ambiguous."""


_ALLOWED_ENERGY_MODES = {"absolute", "reference_relative"}


def _required_text(value: object, *, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise FreeEnergyDiagramError(f"{name} must not be blank")
    return text


def _optional_text(value: object | None, *, name: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, name=name)


def _finite_real(value: object, *, name: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise TypeError(f"{name} must be a real numeric value")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a real numeric value") from exc
    if not isfinite(number):
        raise FreeEnergyDiagramError(f"{name} must be finite")
    return number


def _positive_real(value: object, *, name: str) -> float:
    number = _finite_real(value, name=name)
    if number <= 0:
        raise FreeEnergyDiagramError(f"{name} must be greater than zero")
    return number


def _frozen_1d(values: Sequence[float], *, name: str) -> NDArray[np.float64]:
    source = np.asarray(values)
    if source.ndim != 1 or np.iscomplexobj(source) or source.dtype.kind not in "biuf":
        raise TypeError(f"{name} must be a one-dimensional real numeric sequence")
    normalized = np.ascontiguousarray(source, dtype=np.float64)
    if normalized.size == 0 or not np.isfinite(normalized).all():
        raise FreeEnergyDiagramError(f"{name} must contain finite values")
    result = np.frombuffer(normalized.tobytes(), dtype=np.float64)
    result.setflags(write=False)
    return result


def _digest_text(digest: object, value: str | None) -> None:
    if value is None:
        digest.update(b"none\0")
        return
    encoded = value.encode("utf-8")
    digest.update(len(encoded).to_bytes(8, "little", signed=False))
    digest.update(encoded)


def _digest_float(digest: object, value: float) -> None:
    digest.update(np.float64(value).tobytes())


@dataclass(frozen=True, slots=True, eq=False)
class FreeEnergyDiagramState:
    """One explicit ordered pathway state with reviewed free energy and provenance."""

    key: str
    absolute_energy_ev: float
    source_key: str
    source_type: str
    source_digest: str
    normalization_basis: str
    label: str | None = None
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        key = _required_text(self.key, name="state key")
        energy = _finite_real(self.absolute_energy_ev, name="absolute_energy_ev")
        source_key = _required_text(self.source_key, name="source_key")
        source_type = _required_text(self.source_type, name="source_type")
        source_digest = _required_text(self.source_digest, name="source_digest")
        basis = _required_text(self.normalization_basis, name="normalization_basis")
        label = _optional_text(self.label, name="label")

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.FreeEnergyDiagramState.v1\0")
        for text in (key, source_key, source_type, source_digest, basis):
            _digest_text(digest, text)
        _digest_float(digest, energy)

        object.__setattr__(self, "key", key)
        object.__setattr__(self, "absolute_energy_ev", energy)
        object.__setattr__(self, "source_key", source_key)
        object.__setattr__(self, "source_type", source_type)
        object.__setattr__(self, "source_digest", source_digest)
        object.__setattr__(self, "normalization_basis", basis)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "digest", digest.hexdigest())

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, FreeEnergyDiagramState)
            and self.digest == other.digest
            and self.label == other.label
        )


def diagram_state_from_free_energy(
    evaluation: FreeEnergyEvaluation,
    *,
    key: str | None = None,
    label: str | None = None,
) -> FreeEnergyDiagramState:
    """Adapt one reviewed Block-7 free-energy evaluation without changing its value."""
    if not isinstance(evaluation, FreeEnergyEvaluation):
        raise TypeError("evaluation must be a FreeEnergyEvaluation")
    state_key = evaluation.key if key is None else key
    source_label = getattr(evaluation, "label", None) if label is None else label
    return FreeEnergyDiagramState(
        key=state_key,
        absolute_energy_ev=evaluation.free_energy_ev,
        source_key=evaluation.key,
        source_type="free_energy_evaluation",
        source_digest=evaluation.digest,
        normalization_basis=evaluation.normalization_basis,
        label=source_label,
    )


@dataclass(frozen=True, slots=True, eq=False)
class FreeEnergyDiagramContext:
    """Retained electrochemical context copied from one reviewed CHE result."""

    che_source_digest: str
    temperature_k: float
    ph: float
    input_potential_v: float
    input_potential_reference: str
    potential_she_v: float
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        source_digest = _required_text(self.che_source_digest, name="che_source_digest")
        temperature = _positive_real(self.temperature_k, name="temperature_k")
        ph = _finite_real(self.ph, name="ph")
        potential = _finite_real(self.input_potential_v, name="input_potential_v")
        reference = _required_text(
            self.input_potential_reference,
            name="input_potential_reference",
        ).upper()
        if reference not in {"SHE", "RHE"}:
            raise FreeEnergyDiagramError("input_potential_reference must be SHE or RHE")
        potential_she = _finite_real(self.potential_she_v, name="potential_she_v")

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.FreeEnergyDiagramContext.v1\0")
        for text in (source_digest, reference):
            _digest_text(digest, text)
        for value in (temperature, ph, potential, potential_she):
            _digest_float(digest, value)

        object.__setattr__(self, "che_source_digest", source_digest)
        object.__setattr__(self, "temperature_k", temperature)
        object.__setattr__(self, "ph", ph)
        object.__setattr__(self, "input_potential_v", potential)
        object.__setattr__(self, "input_potential_reference", reference)
        object.__setattr__(self, "potential_she_v", potential_she)
        object.__setattr__(self, "digest", digest.hexdigest())

    def __eq__(self, other: object) -> bool:
        return isinstance(other, FreeEnergyDiagramContext) and self.digest == other.digest


def diagram_context_from_che(
    result: CHEProtonElectronResult,
) -> FreeEnergyDiagramContext:
    """Copy retained CHE context without recalculating potential or pH corrections."""
    if not isinstance(result, CHEProtonElectronResult):
        raise TypeError("result must be a CHEProtonElectronResult")
    return FreeEnergyDiagramContext(
        che_source_digest=result.digest,
        temperature_k=result.temperature_k,
        ph=result.ph,
        input_potential_v=result.input_potential_v,
        input_potential_reference=result.input_potential_reference,
        potential_she_v=result.potential_she_v,
    )


@dataclass(frozen=True, slots=True, eq=False)
class FreeEnergyDiagramSeries:
    """One immutable ordered free-energy pathway prepared for passive rendering."""

    key: str
    states: Sequence[FreeEnergyDiagramState]
    energy_mode: str
    plotted_energy_ev: Sequence[float]
    normalization_basis: str
    comparison_basis: str
    reference_state_key: str | None = None
    context: FreeEnergyDiagramContext | None = None
    label: str | None = None
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        key = _required_text(self.key, name="series key")
        states = tuple(self.states)
        if not states or not all(isinstance(item, FreeEnergyDiagramState) for item in states):
            raise FreeEnergyDiagramError(
                "states must contain at least one FreeEnergyDiagramState"
            )
        state_keys = tuple(item.key for item in states)
        if len(state_keys) != len(set(state_keys)):
            raise FreeEnergyDiagramError("diagram state keys must be unique within a series")

        mode = _required_text(self.energy_mode, name="energy_mode")
        if mode not in _ALLOWED_ENERGY_MODES:
            raise FreeEnergyDiagramError(
                "energy_mode must be 'absolute' or 'reference_relative'"
            )
        basis = _required_text(self.normalization_basis, name="normalization_basis")
        if any(item.normalization_basis != basis for item in states):
            raise FreeEnergyDiagramError(
                "all diagram states require one matching normalization_basis"
            )
        comparison_basis = _required_text(self.comparison_basis, name="comparison_basis")
        reference_key = _optional_text(
            self.reference_state_key,
            name="reference_state_key",
        )
        if mode == "absolute":
            if reference_key is not None:
                raise FreeEnergyDiagramError(
                    "absolute energy_mode must not define reference_state_key"
                )
        else:
            if reference_key is None:
                raise FreeEnergyDiagramError(
                    "reference_relative energy_mode requires explicit reference_state_key"
                )
            if reference_key not in state_keys:
                raise FreeEnergyDiagramError(
                    "reference_state_key must identify one retained diagram state"
                )

        context = self.context
        if context is not None and not isinstance(context, FreeEnergyDiagramContext):
            raise TypeError("context must be a FreeEnergyDiagramContext or None")
        label = _optional_text(self.label, name="label")
        plotted = _frozen_1d(self.plotted_energy_ev, name="plotted_energy_ev")
        if plotted.size != len(states):
            raise FreeEnergyDiagramError(
                "plotted_energy_ev length must match retained diagram states"
            )
        absolute = np.asarray(
            [item.absolute_energy_ev for item in states],
            dtype=np.float64,
        )
        if mode == "absolute":
            expected = absolute
        else:
            reference_index = state_keys.index(reference_key)
            expected = absolute - absolute[reference_index]
        if not np.allclose(plotted, expected, rtol=1e-12, atol=1e-12):
            raise FreeEnergyDiagramError(
                "plotted_energy_ev contradicts retained absolute energies/reference"
            )

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.FreeEnergyDiagramSeries.v1\0")
        for text in (key, mode, basis, comparison_basis, reference_key):
            _digest_text(digest, text)
        for state in states:
            _digest_text(digest, state.digest)
        _digest_text(digest, None if context is None else context.digest)
        for value in plotted:
            _digest_float(digest, float(value))

        object.__setattr__(self, "key", key)
        object.__setattr__(self, "states", states)
        object.__setattr__(self, "energy_mode", mode)
        object.__setattr__(self, "plotted_energy_ev", plotted)
        object.__setattr__(self, "normalization_basis", basis)
        object.__setattr__(self, "comparison_basis", comparison_basis)
        object.__setattr__(self, "reference_state_key", reference_key)
        object.__setattr__(self, "context", context)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "digest", digest.hexdigest())

    @property
    def state_keys(self) -> tuple[str, ...]:
        return tuple(item.key for item in self.states)

    @property
    def state_labels(self) -> tuple[str, ...]:
        return tuple(item.label or item.key for item in self.states)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, FreeEnergyDiagramSeries)
            and self.digest == other.digest
            and self.label == other.label
            and self.state_labels == other.state_labels
        )


def build_free_energy_diagram_series(
    states: Sequence[FreeEnergyDiagramState],
    *,
    key: str,
    energy_mode: str,
    comparison_basis: str,
    reference_state_key: str | None = None,
    context: FreeEnergyDiagramContext | None = None,
    label: str | None = None,
) -> FreeEnergyDiagramSeries:
    """Build explicit absolute or caller-referenced diagram state."""
    retained = tuple(states)
    if not retained or not all(isinstance(item, FreeEnergyDiagramState) for item in retained):
        raise FreeEnergyDiagramError(
            "states must contain at least one FreeEnergyDiagramState"
        )
    mode = _required_text(energy_mode, name="energy_mode")
    if mode not in _ALLOWED_ENERGY_MODES:
        raise FreeEnergyDiagramError(
            "energy_mode must be 'absolute' or 'reference_relative'"
        )
    if mode == "reference_relative" and reference_state_key is None:
        raise FreeEnergyDiagramError(
            "reference_relative energy_mode requires explicit reference_state_key"
        )
    if mode == "absolute" and reference_state_key is not None:
        raise FreeEnergyDiagramError(
            "absolute energy_mode must not define reference_state_key"
        )
    basis = retained[0].normalization_basis
    if any(item.normalization_basis != basis for item in retained):
        raise FreeEnergyDiagramError(
            "all diagram states require one matching normalization_basis"
        )
    absolute = np.asarray(
        [item.absolute_energy_ev for item in retained],
        dtype=np.float64,
    )
    if mode == "absolute":
        plotted = absolute
    else:
        state_keys = tuple(item.key for item in retained)
        requested = _required_text(reference_state_key, name="reference_state_key")
        if requested not in state_keys:
            raise FreeEnergyDiagramError(
                "reference_state_key must identify one retained diagram state"
            )
        plotted = absolute - absolute[state_keys.index(requested)]
    return FreeEnergyDiagramSeries(
        key=key,
        states=retained,
        energy_mode=mode,
        plotted_energy_ev=plotted,
        normalization_basis=basis,
        comparison_basis=comparison_basis,
        reference_state_key=reference_state_key,
        context=context,
        label=label,
    )


def validate_free_energy_diagram_series_compatibility(
    series: Sequence[FreeEnergyDiagramSeries],
) -> tuple[FreeEnergyDiagramSeries, ...]:
    """Fail closed unless several diagram series have explicit compatible semantics."""
    retained = tuple(series)
    if not retained or not all(isinstance(item, FreeEnergyDiagramSeries) for item in retained):
        raise FreeEnergyDiagramError(
            "series must contain at least one FreeEnergyDiagramSeries"
        )
    keys = tuple(item.key for item in retained)
    if len(keys) != len(set(keys)):
        raise FreeEnergyDiagramError("diagram series keys must be unique")
    reference = retained[0]
    reference_context_digest = (
        None if reference.context is None else reference.context.digest
    )
    for item in retained[1:]:
        if item.state_keys != reference.state_keys:
            raise FreeEnergyDiagramError(
                "diagram comparison requires identical ordered pathway-state keys"
            )
        if item.energy_mode != reference.energy_mode:
            raise FreeEnergyDiagramError(
                "diagram comparison requires matching energy_mode"
            )
        if item.normalization_basis != reference.normalization_basis:
            raise FreeEnergyDiagramError(
                "diagram comparison requires matching normalization_basis"
            )
        if item.comparison_basis != reference.comparison_basis:
            raise FreeEnergyDiagramError(
                "diagram comparison requires matching comparison_basis"
            )
        if item.reference_state_key != reference.reference_state_key:
            raise FreeEnergyDiagramError(
                "diagram comparison requires matching explicit reference_state_key"
            )
        item_context_digest = None if item.context is None else item.context.digest
        if item_context_digest != reference_context_digest:
            raise FreeEnergyDiagramError(
                "diagram comparison requires identical retained electrochemical context"
            )
    return retained


def free_energy_diagram_frame(series: FreeEnergyDiagramSeries) -> pd.DataFrame:
    """Return a detached one-row-per-state free-energy diagram table."""
    if not isinstance(series, FreeEnergyDiagramSeries):
        raise TypeError("series must be a FreeEnergyDiagramSeries")
    context = series.context
    return pd.DataFrame(
        [
            {
                "series_digest": series.digest,
                "series_key": series.key,
                "series_label": series.label,
                "state_index": index,
                "state_key": state.key,
                "state_label": state.label,
                "absolute_energy_ev": state.absolute_energy_ev,
                "plotted_energy_ev": float(series.plotted_energy_ev[index]),
                "energy_mode": series.energy_mode,
                "reference_state_key": series.reference_state_key,
                "source_key": state.source_key,
                "source_type": state.source_type,
                "source_digest": state.source_digest,
                "normalization_basis": series.normalization_basis,
                "comparison_basis": series.comparison_basis,
                "che_context_digest": None if context is None else context.che_source_digest,
                "temperature_k": None if context is None else context.temperature_k,
                "ph": None if context is None else context.ph,
                "input_potential_v": None if context is None else context.input_potential_v,
                "input_potential_reference": (
                    None if context is None else context.input_potential_reference
                ),
                "potential_she_v": None if context is None else context.potential_she_v,
            }
            for index, state in enumerate(series.states)
        ]
    )


__all__ = [
    "FreeEnergyDiagramContext",
    "FreeEnergyDiagramError",
    "FreeEnergyDiagramSeries",
    "FreeEnergyDiagramState",
    "build_free_energy_diagram_series",
    "diagram_context_from_che",
    "diagram_state_from_free_energy",
    "free_energy_diagram_frame",
    "validate_free_energy_diagram_series_compatibility",
]
