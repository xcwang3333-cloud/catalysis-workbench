"""Reusable provenance records for electrochemistry analyses and fits."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping

import numpy as np

from catalysis_workbench.core import Series

from .quantities import EchemQuantityError

ProvenanceScalar = str | int | float | bool | None


def _array_digest(values: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(values)
    digest = hashlib.sha256()
    digest.update(str(contiguous.dtype).encode("ascii"))
    digest.update(str(contiguous.shape).encode("ascii"))
    digest.update(contiguous.tobytes(order="C"))
    return digest.hexdigest()


def series_data_sha256(series: Series) -> str:
    """Return a deterministic SHA-256 over a Series' numerical x/y data."""
    if not isinstance(series, Series):
        raise TypeError("series must be a Series")
    digest = hashlib.sha256()
    digest.update(_array_digest(np.asarray(series.x)).encode("ascii"))
    digest.update(_array_digest(np.asarray(series.y)).encode("ascii"))
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class SourceDataRef:
    """Stable source-data identity carried by immutable analysis results."""

    key: str
    label: str
    sha256: str
    x_name: str
    x_unit: str | None
    y_name: str
    y_unit: str | None


def source_data_ref(series: Series) -> SourceDataRef:
    """Build a traceable source reference without copying source arrays into a result."""
    if not isinstance(series, Series):
        raise TypeError("series must be a Series")
    return SourceDataRef(
        key=series.key,
        label=series.label,
        sha256=series_data_sha256(series),
        x_name=series.x_axis.name,
        x_unit=series.x_axis.unit,
        y_name=series.y_axis.name,
        y_unit=series.y_axis.unit,
    )


@dataclass(frozen=True, slots=True)
class FitWindow:
    """Explicit physical fit interval and selected-point count."""

    lower: float
    upper: float
    unit: str
    n_points: int

    def __post_init__(self) -> None:
        lower = float(self.lower)
        upper = float(self.upper)
        if not isfinite(lower) or not isfinite(upper):
            raise EchemQuantityError("fit-window bounds must be finite")
        if lower >= upper:
            raise EchemQuantityError("fit-window lower bound must be smaller than upper bound")
        unit = str(self.unit).strip()
        if not unit:
            raise EchemQuantityError("fit-window unit must not be empty")
        if isinstance(self.n_points, bool):
            raise EchemQuantityError("fit-window n_points must be an integer >= 2")
        n_points = int(self.n_points)
        if n_points != self.n_points or n_points < 2:
            raise EchemQuantityError("fit-window n_points must be an integer >= 2")
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)
        object.__setattr__(self, "unit", unit)
        object.__setattr__(self, "n_points", n_points)


def _freeze_scalar(value: Any, *, name: str) -> ProvenanceScalar:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, (float, np.floating)):
        numeric = float(value)
        if not isfinite(numeric):
            raise EchemQuantityError(f"provenance {name} must be finite")
        return numeric
    if isinstance(value, np.integer):
        return int(value)
    raise EchemQuantityError(
        f"provenance {name} must be a scalar string/int/float/bool/None value"
    )


def _freeze_mapping(
    mapping: Mapping[str, Any] | None,
    *,
    name: str,
) -> tuple[tuple[str, ProvenanceScalar], ...]:
    if mapping is None:
        return ()
    frozen: list[tuple[str, ProvenanceScalar]] = []
    for key, value in mapping.items():
        normalized_key = str(key).strip()
        if not normalized_key:
            raise EchemQuantityError(f"provenance {name} keys must not be empty")
        frozen.append(
            (
                normalized_key,
                _freeze_scalar(value, name=f"{name}.{normalized_key}"),
            )
        )
    frozen.sort(key=lambda item: item[0])
    if len({key for key, _ in frozen}) != len(frozen):
        raise EchemQuantityError(f"provenance {name} keys must be unique after normalization")
    return tuple(frozen)


@dataclass(frozen=True, slots=True)
class AnalysisProvenance:
    """Deterministic provenance payload shared by electrochemical result dataclasses."""

    source: SourceDataRef
    input_basis: str
    fit_window: FitWindow | None = None
    units: tuple[tuple[str, ProvenanceScalar], ...] = ()
    parameters: tuple[tuple[str, ProvenanceScalar], ...] = ()

    def __post_init__(self) -> None:
        basis = str(self.input_basis).strip()
        if not basis:
            raise EchemQuantityError("input_basis must not be empty")
        object.__setattr__(self, "input_basis", basis)


def make_analysis_provenance(
    series: Series,
    *,
    input_basis: str,
    fit_window: FitWindow | None = None,
    units: Mapping[str, ProvenanceScalar] | None = None,
    parameters: Mapping[str, ProvenanceScalar] | None = None,
) -> AnalysisProvenance:
    """Construct deterministic provenance for a fit or scalar/summary result."""
    if fit_window is not None and not isinstance(fit_window, FitWindow):
        raise TypeError("fit_window must be a FitWindow or None")
    return AnalysisProvenance(
        source=source_data_ref(series),
        input_basis=input_basis,
        fit_window=fit_window,
        units=_freeze_mapping(units, name="units"),
        parameters=_freeze_mapping(parameters, name="parameters"),
    )
