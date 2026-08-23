"""Reusable provenance records for electrochemistry analyses and fits."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from math import isfinite
from numbers import Real
from typing import Any, TypeVar

import numpy as np

from catalysis_workbench.core import Series

from .quantities import EchemQuantityError

ProvenanceScalar = str | int | float | bool | None
_T = TypeVar("_T")


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


def _required_text(value: Any, *, name: str) -> str:
    if not isinstance(value, str):
        raise EchemQuantityError(f"{name} must be a string")
    text = value.strip()
    if not text:
        raise EchemQuantityError(f"{name} must not be empty")
    return text


def _optional_unit(value: str | None, *, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise EchemQuantityError(f"{name} must be a string or None")
    return value.strip() or None


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

    def __post_init__(self) -> None:
        if not isinstance(self.key, str) or not isinstance(self.label, str):
            raise EchemQuantityError("source key and label must be strings")
        sha256 = _required_text(self.sha256, name="source sha256").lower()
        if len(sha256) != 64 or any(
            character not in "0123456789abcdef" for character in sha256
        ):
            raise EchemQuantityError(
                "source sha256 must contain exactly 64 hexadecimal characters"
            )

        object.__setattr__(self, "key", self.key.strip())
        object.__setattr__(self, "label", self.label.strip())
        object.__setattr__(self, "sha256", sha256)
        object.__setattr__(self, "x_name", _required_text(self.x_name, name="source x_name"))
        object.__setattr__(self, "x_unit", _optional_unit(self.x_unit, name="source x_unit"))
        object.__setattr__(self, "y_name", _required_text(self.y_name, name="source y_name"))
        object.__setattr__(self, "y_unit", _optional_unit(self.y_unit, name="source y_unit"))


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
        if isinstance(self.lower, (bool, np.bool_)) or not isinstance(self.lower, Real):
            raise EchemQuantityError("fit-window bounds must be real numeric values")
        if isinstance(self.upper, (bool, np.bool_)) or not isinstance(self.upper, Real):
            raise EchemQuantityError("fit-window bounds must be real numeric values")
        lower = float(self.lower)
        upper = float(self.upper)
        if not isfinite(lower) or not isfinite(upper):
            raise EchemQuantityError("fit-window bounds must be finite")
        if lower >= upper:
            raise EchemQuantityError(
                "fit-window lower bound must be smaller than upper bound"
            )
        unit = _required_text(self.unit, name="fit-window unit")

        if isinstance(self.n_points, (bool, np.bool_)) or not isinstance(self.n_points, Real):
            raise EchemQuantityError("fit-window n_points must be an integer >= 2")
        n_points_float = float(self.n_points)
        if not isfinite(n_points_float) or not n_points_float.is_integer():
            raise EchemQuantityError("fit-window n_points must be an integer >= 2")
        n_points = int(n_points_float)
        if n_points < 2:
            raise EchemQuantityError("fit-window n_points must be an integer >= 2")

        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)
        object.__setattr__(self, "unit", unit)
        object.__setattr__(self, "n_points", n_points)


def _freeze_scalar(value: Any, *, name: str) -> ProvenanceScalar:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, np.bool_):
        return bool(value)
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


def _freeze_unit(value: Any, *, name: str) -> str:
    if not isinstance(value, str):
        raise EchemQuantityError(f"provenance {name} must be a non-empty unit string")
    unit = value.strip()
    if not unit:
        raise EchemQuantityError(f"provenance {name} must be a non-empty unit string")
    return unit


def _normalized_key(value: Any, *, name: str) -> str:
    if not isinstance(value, str):
        raise EchemQuantityError(f"provenance {name} keys must be strings")
    key = value.strip()
    if not key:
        raise EchemQuantityError(f"provenance {name} keys must not be empty")
    return key


def _freeze_mapping(
    mapping: Mapping[str, Any] | None,
    *,
    name: str,
    value_freezer: Callable[..., _T],
) -> tuple[tuple[str, _T], ...]:
    if mapping is None:
        return ()
    frozen: list[tuple[str, _T]] = []
    for key, value in mapping.items():
        normalized_key = _normalized_key(key, name=name)
        frozen.append(
            (
                normalized_key,
                value_freezer(value, name=f"{name}.{normalized_key}"),
            )
        )
    frozen.sort(key=lambda item: item[0])
    if len({key for key, _ in frozen}) != len(frozen):
        raise EchemQuantityError(
            f"provenance {name} keys must be unique after normalization"
        )
    return tuple(frozen)


def _freeze_pairs(
    pairs: tuple[tuple[str, Any], ...],
    *,
    name: str,
    value_freezer: Callable[..., _T],
) -> tuple[tuple[str, _T], ...]:
    if not isinstance(pairs, tuple):
        raise EchemQuantityError(
            f"provenance {name} must be a tuple of (key, value) pairs"
        )
    frozen: list[tuple[str, _T]] = []
    for item in pairs:
        if not isinstance(item, tuple) or len(item) != 2:
            raise EchemQuantityError(
                f"provenance {name} must be a tuple of (key, value) pairs"
            )
        key, value = item
        normalized_key = _normalized_key(key, name=name)
        frozen.append(
            (
                normalized_key,
                value_freezer(value, name=f"{name}.{normalized_key}"),
            )
        )
    frozen.sort(key=lambda item: item[0])
    if len({key for key, _ in frozen}) != len(frozen):
        raise EchemQuantityError(
            f"provenance {name} keys must be unique after normalization"
        )
    return tuple(frozen)


@dataclass(frozen=True, slots=True)
class AnalysisProvenance:
    """Deterministic provenance payload shared by electrochemical result dataclasses."""

    source: SourceDataRef
    input_basis: str
    fit_window: FitWindow | None = None
    units: tuple[tuple[str, str], ...] = ()
    parameters: tuple[tuple[str, ProvenanceScalar], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.source, SourceDataRef):
            raise TypeError("source must be a SourceDataRef")
        if self.fit_window is not None and not isinstance(self.fit_window, FitWindow):
            raise TypeError("fit_window must be a FitWindow or None")
        basis = _required_text(self.input_basis, name="input_basis")
        units = _freeze_pairs(self.units, name="units", value_freezer=_freeze_unit)
        parameters = _freeze_pairs(
            self.parameters,
            name="parameters",
            value_freezer=_freeze_scalar,
        )
        object.__setattr__(self, "input_basis", basis)
        object.__setattr__(self, "units", units)
        object.__setattr__(self, "parameters", parameters)


def make_analysis_provenance(
    series: Series,
    *,
    input_basis: str,
    fit_window: FitWindow | None = None,
    units: Mapping[str, str] | None = None,
    parameters: Mapping[str, ProvenanceScalar] | None = None,
) -> AnalysisProvenance:
    """Construct deterministic provenance for a fit or scalar/summary result."""
    if fit_window is not None and not isinstance(fit_window, FitWindow):
        raise TypeError("fit_window must be a FitWindow or None")
    return AnalysisProvenance(
        source=source_data_ref(series),
        input_basis=input_basis,
        fit_window=fit_window,
        units=_freeze_mapping(units, name="units", value_freezer=_freeze_unit),
        parameters=_freeze_mapping(
            parameters,
            name="parameters",
            value_freezer=_freeze_scalar,
        ),
    )
