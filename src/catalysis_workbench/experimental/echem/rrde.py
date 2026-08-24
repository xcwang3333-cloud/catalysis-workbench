"""Explicit rotating ring-disk electrode metrics for aligned current Series."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from numbers import Real
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray

from catalysis_workbench.core import Axis, Series

from .provenance import SourceDataRef, source_data_ref
from .quantities import EchemQuantityError, current_to_a, potential_to_v

RRDECurrentMode = Literal["nonnegative", "magnitude"]
RRDEMetric = Literal["electron_number", "peroxide_percent"]
_COMPATIBILITY_METADATA_KEYS = ("reference", "normalization")


class RRDEError(ValueError):
    """Raised when RRDE inputs violate the explicit scientific contract."""


def _immutable_float_array(values: ArrayLike, *, name: str) -> NDArray[np.float64]:
    try:
        source = np.asarray(values)
    except (TypeError, ValueError) as exc:
        raise RRDEError(f"{name} must contain real numeric values") from exc
    if source.ndim != 1:
        raise RRDEError(f"{name} must be one-dimensional")
    if source.size == 0:
        raise RRDEError(f"{name} must contain at least one value")
    if np.iscomplexobj(source) or source.dtype.kind not in "iuf":
        raise RRDEError(f"{name} must contain real numeric values")
    normalized = np.ascontiguousarray(source, dtype=np.float64)
    if not np.isfinite(normalized).all():
        raise RRDEError(f"{name} must contain only finite values")
    buffer = normalized.tobytes(order="C")
    result = np.frombuffer(buffer, dtype=np.float64, count=normalized.size)
    result.setflags(write=False)
    return result


def _finite_scalar(value: object, *, name: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise RRDEError(f"{name} must be a finite real numeric value")
    numeric = float(value)
    if not isfinite(numeric):
        raise RRDEError(f"{name} must be a finite real numeric value")
    return numeric


def _collection_efficiency(value: object) -> float:
    numeric = _finite_scalar(value, name="collection_efficiency")
    if numeric <= 0.0 or numeric > 1.0:
        raise RRDEError("collection_efficiency must satisfy 0 < N <= 1")
    return numeric


def _current_mode(value: object) -> RRDECurrentMode:
    if isinstance(value, str):
        if value == "nonnegative":
            return "nonnegative"
        if value == "magnitude":
            return "magnitude"
    raise RRDEError("current_mode must be 'nonnegative' or 'magnitude'")


def _metric(value: object) -> RRDEMetric:
    if isinstance(value, str):
        if value == "electron_number":
            return "electron_number"
        if value == "peroxide_percent":
            return "peroxide_percent"
    raise RRDEError("metric must be 'electron_number' or 'peroxide_percent'")


def _required_text(value: object, *, name: str) -> str:
    if not isinstance(value, str):
        raise RRDEError(f"{name} must be a string")
    text = value.strip()
    if not text:
        raise RRDEError(f"{name} must not be empty")
    return text


def _semantic_metadata(axis: Axis, key: str) -> object:
    value = axis.metadata.get(key)
    if isinstance(value, str):
        text = " ".join(value.split())
        return text.casefold() if text else None
    return value


def _validate_potential_condition_unit(unit: str | None) -> None:
    try:
        potential_to_v([0.0], unit, allow_nan=False)
    except EchemQuantityError as exc:
        raise RRDEError(
            "potential-aligned RRDE data require a supported potential unit"
        ) from exc


def _validate_condition_axis(disk: Series, ring: Series) -> None:
    if disk.x_axis.name != ring.x_axis.name or disk.x_axis.unit != ring.x_axis.unit:
        raise RRDEError(
            "disk and ring condition axes must have exactly matching names and units"
        )
    for key in _COMPATIBILITY_METADATA_KEYS:
        if _semantic_metadata(disk.x_axis, key) != _semantic_metadata(ring.x_axis, key):
            raise RRDEError(
                f"disk and ring condition axes must have matching {key!r} metadata"
            )
    if disk.x_axis.name.casefold() == "potential":
        _require_potential_reference(disk)
        _require_potential_reference(ring)
        _validate_potential_condition_unit(disk.x_axis.unit)


def _require_potential_reference(series: Series) -> str:
    value = series.x_axis.metadata.get("reference")
    if value is None:
        raise RRDEError("potential-aligned RRDE data require explicit reference metadata")
    return _required_text(value, name="RRDE potential reference metadata")


def _condition_values(disk: Series, ring: Series) -> NDArray[np.float64]:
    disk_x = _immutable_float_array(disk.x, name="disk condition values")
    ring_x = _immutable_float_array(ring.x, name="ring condition values")
    if disk_x.shape != ring_x.shape or not np.array_equal(disk_x, ring_x):
        raise RRDEError(
            "disk and ring condition values must be exactly aligned; "
            "interpolation is not performed"
        )
    return disk_x


def _current_values_a(series: Series, *, role: str) -> NDArray[np.float64]:
    if series.y_axis.name.casefold() != "current":
        raise RRDEError(f"RRDE {role} y_axis.name must be 'current'")
    if series.y_axis.metadata.get("normalization") is not None:
        raise RRDEError(f"RRDE {role} must be total current, not normalized current")
    try:
        values = current_to_a(series.y, series.y_axis.unit, allow_nan=False)
    except EchemQuantityError as exc:
        raise RRDEError(str(exc)) from exc
    return _immutable_float_array(values, name=f"{role} current in A")


def _selected_currents(
    disk_a: NDArray[np.float64],
    ring_a: NDArray[np.float64],
    *,
    mode: RRDECurrentMode,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    if mode == "nonnegative":
        if (disk_a < 0.0).any() or (ring_a < 0.0).any():
            raise RRDEError(
                "current_mode='nonnegative' requires disk and ring currents >= 0"
            )
        return disk_a, ring_a
    return (
        _immutable_float_array(np.abs(disk_a), name="disk current magnitude"),
        _immutable_float_array(np.abs(ring_a), name="ring current magnitude"),
    )


@dataclass(frozen=True, slots=True, eq=False)
class RRDEResult:
    """Immutable ORR-style RRDE result for one explicitly aligned disk/ring pair."""

    collection_efficiency: float
    current_mode: RRDECurrentMode
    condition_name: str
    condition_unit: str | None
    condition_label: str | None
    condition_reference: str | None
    condition_normalization: str | None
    condition_values: ArrayLike
    disk_current_a: ArrayLike
    ring_current_a: ArrayLike
    disk_source: SourceDataRef
    ring_source: SourceDataRef

    def __post_init__(self) -> None:
        efficiency = _collection_efficiency(self.collection_efficiency)
        mode = _current_mode(self.current_mode)
        condition_name = _required_text(self.condition_name, name="condition_name")
        condition_unit = self.condition_unit
        if condition_unit is not None:
            condition_unit = _required_text(condition_unit, name="condition_unit")
        condition_label = self.condition_label
        if condition_label is not None:
            condition_label = _required_text(condition_label, name="condition_label")
        reference = self.condition_reference
        if reference is not None:
            reference = _required_text(reference, name="condition_reference")
        normalization = self.condition_normalization
        if normalization is not None:
            normalization = _required_text(
                normalization,
                name="condition_normalization",
            )
        if condition_name.casefold() == "potential":
            if reference is None:
                raise RRDEError("potential RRDE result requires condition_reference")
            _validate_potential_condition_unit(condition_unit)

        condition = _immutable_float_array(
            self.condition_values,
            name="RRDE condition values",
        )
        disk = _immutable_float_array(self.disk_current_a, name="RRDE disk current")
        ring = _immutable_float_array(self.ring_current_a, name="RRDE ring current")
        if condition.shape != disk.shape or condition.shape != ring.shape:
            raise RRDEError("RRDE result arrays must have exactly matching shapes")

        if not isinstance(self.disk_source, SourceDataRef):
            raise TypeError("disk_source must be a SourceDataRef")
        if not isinstance(self.ring_source, SourceDataRef):
            raise TypeError("ring_source must be a SourceDataRef")
        if not self.disk_source.key or not self.ring_source.key:
            raise RRDEError("RRDE sources require non-empty stable Series.key values")
        if self.disk_source.key == self.ring_source.key:
            raise RRDEError("RRDE disk and ring source keys must be distinct")
        for role, source in (("disk", self.disk_source), ("ring", self.ring_source)):
            if source.y_name.casefold() != "current":
                raise RRDEError(f"RRDE {role} source y semantic must be current")
            try:
                current_to_a([0.0], source.y_unit, allow_nan=False)
            except EchemQuantityError as exc:
                raise RRDEError(
                    f"RRDE {role} source must declare a supported current unit"
                ) from exc
            if source.x_name != condition_name or source.x_unit != condition_unit:
                raise RRDEError(
                    f"RRDE {role} source condition axis contradicts result axis"
                )

        disk_selected, ring_selected = _selected_currents(disk, ring, mode=mode)
        denominator = disk_selected + ring_selected / efficiency
        if (denominator == 0.0).any():
            raise RRDEError("RRDE denominator must be non-zero at every condition")

        object.__setattr__(self, "collection_efficiency", efficiency)
        object.__setattr__(self, "current_mode", mode)
        object.__setattr__(self, "condition_name", condition_name)
        object.__setattr__(self, "condition_unit", condition_unit)
        object.__setattr__(self, "condition_label", condition_label)
        object.__setattr__(self, "condition_reference", reference)
        object.__setattr__(self, "condition_normalization", normalization)
        object.__setattr__(self, "condition_values", condition)
        object.__setattr__(self, "disk_current_a", disk)
        object.__setattr__(self, "ring_current_a", ring)

    @property
    def electron_number(self) -> NDArray[np.float64]:
        """Return ORR-style apparent electron number without clipping."""
        disk, ring = _selected_currents(
            self.disk_current_a,
            self.ring_current_a,
            mode=self.current_mode,
        )
        denominator = disk + ring / self.collection_efficiency
        return _immutable_float_array(
            4.0 * disk / denominator,
            name="RRDE electron number",
        )

    @property
    def peroxide_percent(self) -> NDArray[np.float64]:
        """Return ORR-style peroxide yield in percent without clipping."""
        disk, ring = _selected_currents(
            self.disk_current_a,
            self.ring_current_a,
            mode=self.current_mode,
        )
        denominator = disk + ring / self.collection_efficiency
        return _immutable_float_array(
            200.0 * (ring / self.collection_efficiency) / denominator,
            name="RRDE peroxide percent",
        )


def rrde_metrics(
    disk: Series,
    ring: Series,
    *,
    collection_efficiency: float,
    current_mode: RRDECurrentMode,
) -> RRDEResult:
    """Calculate explicit ORR-style RRDE metrics from aligned total-current Series."""
    if not isinstance(disk, Series) or not isinstance(ring, Series):
        raise TypeError("disk and ring must be Series instances")
    if not disk.key or not ring.key:
        raise RRDEError("RRDE disk and ring Series require non-empty stable keys")
    if disk.key == ring.key:
        raise RRDEError("RRDE disk and ring Series keys must be distinct")

    mode = _current_mode(current_mode)
    efficiency = _collection_efficiency(collection_efficiency)
    _validate_condition_axis(disk, ring)
    condition = _condition_values(disk, ring)
    disk_a = _current_values_a(disk, role="disk")
    ring_a = _current_values_a(ring, role="ring")
    if condition.shape != disk_a.shape or condition.shape != ring_a.shape:
        raise RRDEError("RRDE condition and current arrays must have matching shapes")
    _selected_currents(disk_a, ring_a, mode=mode)

    reference = disk.x_axis.metadata.get("reference")
    normalization = disk.x_axis.metadata.get("normalization")
    return RRDEResult(
        collection_efficiency=efficiency,
        current_mode=mode,
        condition_name=disk.x_axis.name,
        condition_unit=disk.x_axis.unit,
        condition_label=disk.x_axis.label,
        condition_reference=(str(reference).strip() if reference is not None else None),
        condition_normalization=(
            str(normalization).strip() if normalization is not None else None
        ),
        condition_values=condition,
        disk_current_a=disk_a,
        ring_current_a=ring_a,
        disk_source=source_data_ref(disk),
        ring_source=source_data_ref(ring),
    )


def rrde_result_series(result: RRDEResult, metric: RRDEMetric) -> Series:
    """Convert one already-calculated RRDE metric into a publication-ready Series."""
    if not isinstance(result, RRDEResult):
        raise TypeError("result must be an RRDEResult")
    selected = _metric(metric)
    axis_metadata: dict[str, object] = {}
    if result.condition_reference is not None:
        axis_metadata["reference"] = result.condition_reference
    if result.condition_normalization is not None:
        axis_metadata["normalization"] = result.condition_normalization
    x_axis = Axis(
        result.condition_name,
        unit=result.condition_unit,
        label=result.condition_label,
        metadata=axis_metadata,
    )
    y_metadata = {
        "analysis": "rrde",
        "collection_efficiency": result.collection_efficiency,
        "current_mode": result.current_mode,
        "disk_source_key": result.disk_source.key,
        "ring_source_key": result.ring_source.key,
    }
    if selected == "electron_number":
        values = result.electron_number
        y_axis = Axis(
            "electron_number",
            label="Electron transfer number",
            metadata=y_metadata,
        )
    else:
        values = result.peroxide_percent
        y_axis = Axis(
            "peroxide_yield",
            unit="%",
            label="Peroxide yield",
            metadata=y_metadata,
        )
    return Series(
        x=result.condition_values,
        y=values,
        label=result.disk_source.label or result.disk_source.key,
        key=f"{result.disk_source.key}:{result.ring_source.key}:rrde:{selected}",
        x_axis=x_axis,
        y_axis=y_axis,
        metadata={
            "disk_source_sha256": result.disk_source.sha256,
            "ring_source_sha256": result.ring_source.sha256,
        },
    )


__all__ = [
    "RRDECurrentMode",
    "RRDEError",
    "RRDEMetric",
    "RRDEResult",
    "rrde_metrics",
    "rrde_result_series",
]
