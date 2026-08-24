"""Closure QA for product partial current density.

Closure is diagnostic only. It never rescales, renormalizes, clips, or corrects
experimental current densities.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from numbers import Real
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray

from catalysis_workbench.core import Dataset, Series

from .partial_current import PartialCurrentDensityError
from .partial_current_series import _validate_condition_compatibility
from .provenance import SourceDataRef, source_data_ref
from .quantities import EchemQuantityError, current_density_to_a_cm2

ClosureComparisonMode = Literal["signed", "magnitude"]


class PartialCurrentClosureError(ValueError):
    """Raised when closure inputs violate the scientific contract."""


def _immutable_float_array(
    values: ArrayLike,
    *,
    name: str,
    allow_inf: bool = False,
) -> NDArray[np.float64]:
    try:
        source = np.asarray(values)
    except (TypeError, ValueError) as exc:
        raise PartialCurrentClosureError(f"{name} must contain real numeric values") from exc
    if source.size == 0 or np.iscomplexobj(source) or source.dtype.kind not in "iuf":
        raise PartialCurrentClosureError(f"{name} must contain real numeric values")
    normalized = np.ascontiguousarray(source, dtype=np.float64)
    if np.isnan(normalized).any() or (not allow_inf and np.isinf(normalized).any()):
        qualifier = "NaN" if allow_inf else "non-finite values"
        raise PartialCurrentClosureError(f"{name} must not contain {qualifier}")
    buffer = normalized.tobytes(order="C")
    result = np.frombuffer(buffer, dtype=np.float64, count=normalized.size)
    result = result.reshape(normalized.shape)
    result.setflags(write=False)
    return result


def _immutable_bool_array(values: ArrayLike, *, name: str) -> NDArray[np.bool_]:
    source = np.asarray(values)
    if source.size == 0 or source.dtype.kind != "b":
        raise PartialCurrentClosureError(f"{name} must contain boolean values")
    normalized = np.ascontiguousarray(source, dtype=np.bool_)
    buffer = normalized.tobytes(order="C")
    result = np.frombuffer(buffer, dtype=np.bool_, count=normalized.size)
    result = result.reshape(normalized.shape)
    result.setflags(write=False)
    return result


def _normalize_mode(mode: object) -> ClosureComparisonMode:
    if mode == "signed":
        return "signed"
    if mode == "magnitude":
        return "magnitude"
    raise PartialCurrentClosureError("comparison_mode must be 'signed' or 'magnitude'")


def _normalize_tolerance(value: object) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise PartialCurrentClosureError("tolerance_fraction must be a non-negative number")
    numeric = float(value)
    if not isfinite(numeric) or numeric < 0.0:
        raise PartialCurrentClosureError("tolerance_fraction must be a non-negative number")
    return numeric


def _semantic_metadata_value(series: Series, key: str) -> object:
    value = series.y_axis.metadata.get(key)
    if isinstance(value, str):
        return value.strip().casefold()
    return value


def _validate_current_density_normalization(total: Series, partial: Series) -> None:
    total_normalization = _semantic_metadata_value(total, "normalization")
    partial_normalization = _semantic_metadata_value(partial, "normalization")
    if total_normalization != partial_normalization:
        raise PartialCurrentClosureError(
            "partial and total current-density normalization metadata differ"
        )


def _validate_current_source_provenance(total_source: SourceDataRef, partial: Series) -> None:
    current_source = partial.metadata.get("current_source")
    if current_source is None:
        return
    if not isinstance(current_source, Mapping):
        raise PartialCurrentClosureError(
            "partial-current current_source provenance must be a mapping"
        )
    source_sha = current_source.get("sha256")
    if not isinstance(source_sha, str) or source_sha.casefold() != total_source.sha256:
        raise PartialCurrentClosureError(
            "partial-current current_source provenance does not match total current density"
        )


@dataclass(frozen=True, slots=True, eq=False)
class PartialCurrentClosureResult:
    """Immutable report comparing summed product current with measured total current."""

    total_current_density: ArrayLike
    summed_partial_current_density: ArrayLike
    residual: ArrayLike
    absolute_error: ArrayLike
    relative_error: ArrayLike
    tolerance_fraction: float
    passed: ArrayLike
    comparison_mode: ClosureComparisonMode = "signed"
    total_source: SourceDataRef | None = None
    partial_sources: tuple[SourceDataRef, ...] = ()

    def __post_init__(self) -> None:
        total = _immutable_float_array(self.total_current_density, name="total current density")
        summed = _immutable_float_array(
            self.summed_partial_current_density,
            name="summed partial current density",
        )
        residual = _immutable_float_array(self.residual, name="closure residual")
        absolute = _immutable_float_array(self.absolute_error, name="closure absolute error")
        relative = _immutable_float_array(
            self.relative_error,
            name="closure relative error",
            allow_inf=True,
        )
        passed = _immutable_bool_array(self.passed, name="closure pass mask")
        shapes = {
            total.shape,
            summed.shape,
            residual.shape,
            absolute.shape,
            relative.shape,
            passed.shape,
        }
        if len(shapes) != 1:
            raise PartialCurrentClosureError("closure result arrays must have matching shapes")
        mode = _normalize_mode(self.comparison_mode)
        tolerance = _normalize_tolerance(self.tolerance_fraction)
        expected_residual = summed - total
        if not np.allclose(residual, expected_residual, rtol=0.0, atol=0.0):
            raise PartialCurrentClosureError(
                "closure residual is inconsistent with summed and total current"
            )
        if not np.allclose(absolute, np.abs(residual), rtol=0.0, atol=0.0):
            raise PartialCurrentClosureError(
                "closure absolute_error is inconsistent with residual"
            )
        denominator = np.abs(total)
        expected_relative = np.empty_like(absolute, dtype=np.float64)
        nonzero = denominator > 0.0
        np.divide(absolute, denominator, out=expected_relative, where=nonzero)
        expected_relative[~nonzero] = np.where(
            absolute[~nonzero] == 0.0,
            0.0,
            np.inf,
        )
        if not np.allclose(relative, expected_relative, rtol=0.0, atol=0.0):
            raise PartialCurrentClosureError(
                "closure relative_error is inconsistent with absolute error and total current"
            )
        expected_passed = relative <= tolerance
        if not np.array_equal(passed, expected_passed):
            raise PartialCurrentClosureError(
                "closure pass mask is inconsistent with tolerance"
            )
        sources = tuple(self.partial_sources)
        if not all(isinstance(source, SourceDataRef) for source in sources):
            raise TypeError("partial_sources must contain only SourceDataRef instances")
        if self.total_source is not None and not isinstance(self.total_source, SourceDataRef):
            raise TypeError("total_source must be a SourceDataRef or None")
        object.__setattr__(self, "total_current_density", total)
        object.__setattr__(self, "summed_partial_current_density", summed)
        object.__setattr__(self, "residual", residual)
        object.__setattr__(self, "absolute_error", absolute)
        object.__setattr__(self, "relative_error", relative)
        object.__setattr__(self, "passed", passed)
        object.__setattr__(self, "comparison_mode", mode)
        object.__setattr__(self, "tolerance_fraction", tolerance)
        object.__setattr__(self, "partial_sources", sources)

    @property
    def all_passed(self) -> bool:
        return bool(np.all(self.passed))

    @property
    def max_relative_error(self) -> float:
        return float(np.max(self.relative_error))


def partial_current_closure(
    total_current_density: ArrayLike | float,
    partial_current_densities: ArrayLike,
    *,
    tolerance_fraction: float = 0.05,
    comparison_mode: ClosureComparisonMode = "signed",
    total_source: SourceDataRef | None = None,
    partial_sources: tuple[SourceDataRef, ...] = (),
) -> PartialCurrentClosureResult:
    """Evaluate partial-current closure without modifying any input values.

    The first axis of ``partial_current_densities`` is the product axis. In signed
    mode the signed product currents are summed. In magnitude mode absolute product
    currents are summed and compared with ``abs(j_total)``. Zero total current gives
    relative error 0 only when the absolute closure error is also zero; otherwise it
    gives infinity and therefore fails any finite tolerance.
    """
    tolerance = _normalize_tolerance(tolerance_fraction)
    mode = _normalize_mode(comparison_mode)
    total_raw = _immutable_float_array(total_current_density, name="total current density")
    partial_raw = _immutable_float_array(
        partial_current_densities,
        name="partial current densities",
    )
    if partial_raw.ndim < 1:
        raise PartialCurrentClosureError("partial current densities require a product axis")
    if partial_raw.ndim == 1:
        partial_raw = partial_raw.reshape((1, *partial_raw.shape))
    if partial_raw.shape[1:] != total_raw.shape:
        raise PartialCurrentClosureError(
            "partial-current condition shape must match total current density"
        )

    if mode == "signed":
        compared_total = total_raw
        compared_partial = partial_raw
    else:
        compared_total = np.abs(total_raw)
        compared_partial = np.abs(partial_raw)
    summed = np.sum(compared_partial, axis=0)
    residual = summed - compared_total
    absolute = np.abs(residual)
    denominator = np.abs(compared_total)
    relative = np.empty_like(absolute, dtype=np.float64)
    nonzero = denominator > 0.0
    np.divide(absolute, denominator, out=relative, where=nonzero)
    relative[~nonzero] = np.where(absolute[~nonzero] == 0.0, 0.0, np.inf)
    passed = relative <= tolerance

    return PartialCurrentClosureResult(
        total_current_density=compared_total,
        summed_partial_current_density=summed,
        residual=residual,
        absolute_error=absolute,
        relative_error=relative,
        tolerance_fraction=tolerance,
        passed=passed,
        comparison_mode=mode,
        total_source=total_source,
        partial_sources=partial_sources,
    )


def partial_current_closure_dataset(
    total_current_density: Series,
    partial_currents: Dataset,
    *,
    tolerance_fraction: float = 0.05,
    comparison_mode: ClosureComparisonMode = "signed",
) -> PartialCurrentClosureResult:
    """Evaluate closure for condition-aligned partial-current Series with provenance."""
    if not isinstance(total_current_density, Series):
        raise TypeError("total_current_density must be a Series")
    if not isinstance(partial_currents, Dataset):
        raise TypeError("partial_currents must be a Dataset")
    if len(partial_currents) == 0:
        raise PartialCurrentClosureError("partial_currents Dataset must not be empty")
    if total_current_density.y_axis.name.casefold() != "current_density":
        raise PartialCurrentClosureError(
            "total-current Series requires y_axis.name='current_density'"
        )
    try:
        current_density_to_a_cm2(
            total_current_density.y,
            total_current_density.y_axis.unit,
            allow_nan=False,
        )
    except EchemQuantityError as exc:
        raise PartialCurrentClosureError(str(exc)) from exc

    total_source = source_data_ref(total_current_density)
    partial_values = []
    partial_sources = []
    for item in partial_currents:
        if item.y_axis.name.casefold() != "partial_current_density":
            raise PartialCurrentClosureError(
                "closure Dataset requires y_axis.name='partial_current_density'"
            )
        if item.y_axis.unit != total_current_density.y_axis.unit:
            raise PartialCurrentClosureError(
                "partial and total current-density units must match exactly for closure"
            )
        _validate_current_density_normalization(total_current_density, item)
        _validate_current_source_provenance(total_source, item)
        try:
            _validate_condition_compatibility(total_current_density, item)
        except PartialCurrentDensityError as exc:
            raise PartialCurrentClosureError(str(exc)) from exc
        partial_values.append(item.y)
        partial_sources.append(source_data_ref(item))

    return partial_current_closure(
        total_current_density.y,
        np.stack(partial_values, axis=0),
        tolerance_fraction=tolerance_fraction,
        comparison_mode=comparison_mode,
        total_source=total_source,
        partial_sources=tuple(partial_sources),
    )


__all__ = [
    "ClosureComparisonMode",
    "PartialCurrentClosureError",
    "PartialCurrentClosureResult",
    "partial_current_closure",
    "partial_current_closure_dataset",
]
