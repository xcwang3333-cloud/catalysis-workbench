"""Neutral immutable integration of externally computed EXAFS fit summaries."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from math import isfinite
from types import MappingProxyType
from typing import Any, Literal

import numpy as np
import pandas as pd

EXAFSFitStatus = Literal["reported", "fitted", "fixed", "derived", "unavailable"]


class EXAFSFitSummaryError(ValueError):
    """Raised when externally reported EXAFS fit-summary state is invalid."""


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


def _finite_optional(value: float | None, *, name: str) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a real numeric value or None") from exc
    if not isfinite(result):
        raise EXAFSFitSummaryError(f"{name} must be finite when supplied")
    return result


@dataclass(frozen=True, slots=True)
class EXAFSFitValue:
    """One externally reported scalar with optional uncertainty and status."""

    value: float | None
    uncertainty: float | None = None
    status: EXAFSFitStatus = "reported"

    def __post_init__(self) -> None:
        status = str(self.status).strip().casefold()
        allowed = {"reported", "fitted", "fixed", "derived", "unavailable"}
        if status not in allowed:
            raise EXAFSFitSummaryError(
                "status must be reported, fitted, fixed, derived, or unavailable"
            )
        value = _finite_optional(self.value, name="value")
        uncertainty = _finite_optional(self.uncertainty, name="uncertainty")
        if status == "unavailable":
            if value is not None or uncertainty is not None:
                raise EXAFSFitSummaryError(
                    "unavailable EXAFS fit values must not carry value/uncertainty"
                )
        else:
            if value is None:
                raise EXAFSFitSummaryError(
                    "available EXAFS fit values require an explicit numeric value"
                )
            if uncertainty is not None and uncertainty < 0.0:
                raise EXAFSFitSummaryError("reported uncertainty must be non-negative")
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "uncertainty", uncertainty)
        object.__setattr__(self, "status", status)

    @classmethod
    def unavailable(cls) -> EXAFSFitValue:
        """Return an explicit unavailable value state."""
        return cls(None, status="unavailable")


_UNAVAILABLE = EXAFSFitValue.unavailable()


def _fit_value_or_unavailable(value: EXAFSFitValue | None, *, name: str) -> EXAFSFitValue:
    if value is None:
        return _UNAVAILABLE
    if not isinstance(value, EXAFSFitValue):
        raise TypeError(f"{name} must be an EXAFSFitValue or None")
    return value


@dataclass(frozen=True, slots=True)
class EXAFSPathSummary:
    """Neutral summary of one externally reported EXAFS path/shell."""

    key: str
    label: str = ""
    coordination_number: EXAFSFitValue | None = None
    r_angstrom: EXAFSFitValue | None = None
    sigma2_angstrom2: EXAFSFitValue | None = None
    delta_e0_ev: EXAFSFitValue | None = None
    amplitude: EXAFSFitValue | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        key = str(self.key).strip()
        if not key:
            raise EXAFSFitSummaryError("EXAFS path key must not be empty")
        object.__setattr__(self, "key", key)
        object.__setattr__(self, "label", str(self.label).strip())
        for name in (
            "coordination_number",
            "r_angstrom",
            "sigma2_angstrom2",
            "delta_e0_ev",
            "amplitude",
        ):
            object.__setattr__(
                self,
                name,
                _fit_value_or_unavailable(getattr(self, name), name=name),
            )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))

    def metadata_dict(self) -> dict[str, Any]:
        """Return an independent mutable metadata copy."""
        return {key: _thaw_value(value) for key, value in self.metadata.items()}


@dataclass(frozen=True, slots=True)
class EXAFSFitDiagnostic:
    """One producer-defined fit diagnostic retained without reinterpretation."""

    label: str
    value: float
    unit: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        label = str(self.label).strip()
        if not label:
            raise EXAFSFitSummaryError("EXAFS fit diagnostic label must not be empty")
        value = _finite_optional(self.value, name="diagnostic value")
        unit = None if self.unit is None else str(self.unit).strip() or None
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "value", float(value))
        object.__setattr__(self, "unit", unit)
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))

    def metadata_dict(self) -> dict[str, Any]:
        """Return an independent mutable metadata copy."""
        return {key: _thaw_value(value) for key, value in self.metadata.items()}


@dataclass(frozen=True, slots=True)
class EXAFSFitSummary:
    """Immutable producer-scoped EXAFS fit summary with ordered paths/diagnostics."""

    producer: str
    source_id: str
    paths: tuple[EXAFSPathSummary, ...]
    diagnostics: tuple[EXAFSFitDiagnostic, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        producer = str(self.producer).strip()
        source_id = str(self.source_id).strip()
        if not producer:
            raise EXAFSFitSummaryError("producer must not be empty")
        if not source_id:
            raise EXAFSFitSummaryError("source_id must not be empty")
        paths = tuple(self.paths)
        diagnostics = tuple(self.diagnostics)
        if not paths:
            raise EXAFSFitSummaryError("EXAFS fit summary requires at least one path")
        if not all(isinstance(path, EXAFSPathSummary) for path in paths):
            raise TypeError("paths must contain only EXAFSPathSummary instances")
        if not all(isinstance(item, EXAFSFitDiagnostic) for item in diagnostics):
            raise TypeError("diagnostics must contain only EXAFSFitDiagnostic instances")
        path_keys = [path.key for path in paths]
        if len(path_keys) != len(set(path_keys)):
            raise EXAFSFitSummaryError("EXAFS path keys must be unique within a summary")
        labels = [item.label for item in diagnostics]
        if len(labels) != len(set(labels)):
            raise EXAFSFitSummaryError(
                "EXAFS diagnostic labels must be unique within a summary"
            )
        object.__setattr__(self, "producer", producer)
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "paths", paths)
        object.__setattr__(self, "diagnostics", diagnostics)
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))

    def metadata_dict(self) -> dict[str, Any]:
        """Return an independent mutable metadata copy."""
        return {key: _thaw_value(value) for key, value in self.metadata.items()}


def _value_columns(prefix: str, value: EXAFSFitValue) -> dict[str, Any]:
    return {
        prefix: value.value,
        f"{prefix}_uncertainty": value.uncertainty,
        f"{prefix}_status": value.status,
    }


def exafs_fit_summary_frame(summary: EXAFSFitSummary) -> pd.DataFrame:
    """Return a detached one-row-per-path reporting table with explicit unit columns."""
    if not isinstance(summary, EXAFSFitSummary):
        raise TypeError("summary must be an EXAFSFitSummary")
    rows: list[dict[str, Any]] = []
    for path in summary.paths:
        row: dict[str, Any] = {
            "producer": summary.producer,
            "source_id": summary.source_id,
            "path_key": path.key,
            "path_label": path.label,
        }
        row.update(_value_columns("coordination_number", path.coordination_number))
        row.update(_value_columns("r_angstrom", path.r_angstrom))
        row.update(_value_columns("sigma2_angstrom2", path.sigma2_angstrom2))
        row.update(_value_columns("delta_e0_ev", path.delta_e0_ev))
        row.update(_value_columns("amplitude", path.amplitude))
        rows.append(row)
    return pd.DataFrame.from_records(rows)


def exafs_fit_diagnostics_frame(summary: EXAFSFitSummary) -> pd.DataFrame:
    """Return a detached diagnostic table retaining producer labels and units verbatim."""
    if not isinstance(summary, EXAFSFitSummary):
        raise TypeError("summary must be an EXAFSFitSummary")
    rows = [
        {
            "producer": summary.producer,
            "source_id": summary.source_id,
            "diagnostic_label": item.label,
            "value": item.value,
            "unit": item.unit,
        }
        for item in summary.diagnostics
    ]
    return pd.DataFrame.from_records(
        rows,
        columns=["producer", "source_id", "diagnostic_label", "value", "unit"],
    )


__all__ = [
    "EXAFSFitDiagnostic",
    "EXAFSFitStatus",
    "EXAFSFitSummary",
    "EXAFSFitSummaryError",
    "EXAFSFitValue",
    "EXAFSPathSummary",
    "exafs_fit_diagnostics_frame",
    "exafs_fit_summary_frame",
]
