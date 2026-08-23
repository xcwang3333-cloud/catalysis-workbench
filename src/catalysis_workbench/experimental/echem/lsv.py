"""Scientific processing for LSV and polarization curves.

This module deliberately contains no plotting code. Publication rendering is owned by
``catalysis_workbench.visualization`` and connected through a thin LSV adapter.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from math import isfinite
from typing import Any, TypeVar

import numpy as np

from catalysis_workbench.core import Axis, Dataset, Series

from .quantities import (
    FARADAY_CONSTANT_C_MOL,
    GAS_CONSTANT_J_MOL_K,
    EchemQuantityError,
    canonical_current_density_unit,
    current_density_from_a_cm2,
    current_density_to_a_cm2,
    current_to_a,
    is_current_density_unit,
    is_current_unit,
    nonnegative_finite,
    normalize_reference_name,
    normalize_unit,
    positive_finite,
    potential_to_v,
    same_reference,
)

_GEOMETRIC_NORMALIZATION_NAMES = {
    "geometric",
    "geometric_area",
    "geometric_area_cm2",
}
_T = TypeVar("_T")


class LSVError(ValueError):
    """Raised when an LSV transformation is scientifically or numerically invalid."""


def _translate_quantity_error(function: Callable[..., _T], *args: Any, **kwargs: Any) -> _T:
    try:
        return function(*args, **kwargs)
    except EchemQuantityError as exc:
        raise LSVError(str(exc)) from exc


def _compact_unit(unit: str | None) -> str:
    try:
        return normalize_unit(unit)
    except EchemQuantityError as exc:
        raise LSVError("electrochemical axis unit is required") from exc


def _normalize_reference_name(reference: str) -> str:
    try:
        return normalize_reference_name(reference)
    except EchemQuantityError as exc:
        raise LSVError("source_reference must not be empty") from exc


def _same_reference(left: str, right: str) -> bool:
    try:
        return same_reference(left, right)
    except EchemQuantityError as exc:
        raise LSVError(str(exc)) from exc


def _history_has(series: Series, operation: str) -> bool:
    history = series.metadata.get("processing_history", ())
    return any(
        isinstance(record, Mapping) and record.get("operation") == operation
        for record in history
    )


def _positive_finite(value: float, *, name: str) -> float:
    return _translate_quantity_error(positive_finite, value, name=name)


def _nonnegative_finite(value: float, *, name: str) -> float:
    return _translate_quantity_error(nonnegative_finite, value, name=name)


def _axis_with(
    axis: Axis,
    *,
    name: str,
    unit: str,
    label: str,
    metadata_updates: Mapping[str, Any] | None = None,
) -> Axis:
    metadata = axis.metadata_dict()
    if metadata_updates:
        metadata.update(metadata_updates)
    return Axis(name=name, unit=unit, label=label, metadata=metadata)


def _transform(
    series: Series,
    *,
    x: np.ndarray | None = None,
    y: np.ndarray | None = None,
    x_axis: Axis | None = None,
    y_axis: Axis | None = None,
    operation: str,
    parameters: Mapping[str, Any],
) -> Series:
    metadata = series.metadata_dict()
    history = list(metadata.get("processing_history", []))
    history.append({"operation": operation, "parameters": dict(parameters)})
    metadata["processing_history"] = history
    return Series(
        x=series.x if x is None else x,
        y=series.y if y is None else y,
        label=series.label,
        x_axis=series.x_axis if x_axis is None else x_axis,
        y_axis=series.y_axis if y_axis is None else y_axis,
        metadata=metadata,
        key=series.key,
    )


def _potential_in_v(series: Series) -> np.ndarray:
    try:
        return potential_to_v(series.x, series.x_axis.unit, allow_nan=False)
    except EchemQuantityError as exc:
        message = str(exc)
        if "unit is required" in message:
            raise LSVError("electrochemical axis unit is required") from exc
        raise LSVError(message) from exc


def _current_in_a(series: Series) -> np.ndarray:
    if is_current_density_unit(series.y_axis.unit):
        raise LSVError(
            "current-density input requires electrode area to recover total current"
        )
    try:
        return current_to_a(series.y, series.y_axis.unit, allow_nan=True)
    except EchemQuantityError as exc:
        message = str(exc)
        if "unit is required" in message:
            raise LSVError("electrochemical axis unit is required") from exc
        raise LSVError(message) from exc


def _density_area_basis(series: Series, supplied_area_cm2: float) -> str:
    declared = series.y_axis.metadata.get("normalization")
    if declared is None:
        return "geometric_area_explicit_assumption"

    declared_name = str(declared).strip().lower().replace(" ", "_")
    if declared_name not in _GEOMETRIC_NORMALIZATION_NAMES:
        raise LSVError(
            "current-density iR reconstruction requires geometric-area "
            f"normalization; found {declared!r}"
        )

    stored_area = series.y_axis.metadata.get("electrode_area_cm2")
    if stored_area is None:
        return "geometric_area_declared"

    normalized_area = _positive_finite(stored_area, name="stored electrode_area_cm2")
    if not np.isclose(normalized_area, supplied_area_cm2, rtol=1e-12, atol=0.0):
        raise LSVError(
            "electrode_area_cm2 does not match the area used to create current density: "
            f"{supplied_area_cm2!r} vs {normalized_area!r}"
        )
    return "geometric_area_declared_matched"


def _current_from_series_in_a(
    series: Series,
    *,
    electrode_area_cm2: float | None,
    allow_nan: bool,
) -> tuple[np.ndarray, str, str | None]:
    unit = series.y_axis.unit
    if is_current_unit(unit):
        try:
            values = current_to_a(series.y, unit, allow_nan=allow_nan)
        except EchemQuantityError as exc:
            raise LSVError(str(exc)) from exc
        return values, "current", None
    if is_current_density_unit(unit):
        if electrode_area_cm2 is None:
            raise LSVError(
                "electrode_area_cm2 is required for iR correction of current-density data"
            )
        area = _positive_finite(electrode_area_cm2, name="electrode_area_cm2")
        area_basis = _density_area_basis(series, area)
        try:
            density_a_cm2 = current_density_to_a_cm2(
                series.y,
                unit,
                allow_nan=allow_nan,
            )
        except EchemQuantityError as exc:
            raise LSVError(str(exc)) from exc
        return density_a_cm2 * area, "current_density", area_basis
    if unit is None or not str(unit).strip():
        raise LSVError("electrochemical axis unit is required")
    raise LSVError(f"unsupported current/current-density unit {unit!r}")


def rhe_offset_from_she(
    reference_potential_vs_she_v: float,
    ph: float,
    *,
    temperature_k: float = 298.15,
) -> float:
    """Return the additive offset converting ``E vs reference`` to ``E vs RHE``."""
    reference = float(reference_potential_vs_she_v)
    ph_value = float(ph)
    temperature = _positive_finite(temperature_k, name="temperature_k")
    if not isfinite(reference) or not isfinite(ph_value):
        raise LSVError("reference_potential_vs_she_v and ph must be finite")
    nernst_slope = (
        2.303 * GAS_CONSTANT_J_MOL_K * temperature / FARADAY_CONSTANT_C_MOL
    )
    return reference + nernst_slope * ph_value


def convert_potential_to_rhe(
    series: Series,
    *,
    offset_v: float,
    source_reference: str | None = None,
) -> Series:
    """Convert the x-axis potential to RHE using an explicit additive offset in volts."""
    if _history_has(series, "echem.convert_potential_to_rhe"):
        raise LSVError("potential has already been converted to RHE")

    declared_reference = series.x_axis.metadata.get("reference")
    declared_name = None
    if declared_reference is not None:
        declared_name = _normalize_reference_name(str(declared_reference))
        if declared_name.casefold() == "rhe":
            raise LSVError("potential is already referenced to RHE")

    reference_name = None
    if source_reference is not None:
        reference_name = _normalize_reference_name(source_reference)
        if reference_name.casefold() == "rhe":
            raise LSVError("source_reference is already RHE; no RHE conversion is needed")
        if declared_name is not None and not _same_reference(declared_name, reference_name):
            raise LSVError(
                "source_reference contradicts x-axis reference metadata: "
                f"{reference_name!r} vs {declared_name!r}"
            )
    elif declared_name is not None:
        reference_name = declared_name

    offset = float(offset_v)
    if not isfinite(offset):
        raise LSVError("offset_v must be finite")
    converted = _potential_in_v(series) + offset
    axis_updates: dict[str, Any] = {"reference": "RHE"}
    if reference_name is not None:
        axis_updates["source_reference"] = reference_name
    x_axis = _axis_with(
        series.x_axis,
        name="potential",
        unit="V",
        label="Potential",
        metadata_updates=axis_updates,
    )
    parameters: dict[str, Any] = {"offset_v": offset, "target_reference": "RHE"}
    if reference_name is not None:
        parameters["source_reference"] = reference_name
    return _transform(
        series,
        x=converted,
        x_axis=x_axis,
        operation="echem.convert_potential_to_rhe",
        parameters=parameters,
    )


def correct_ir_drop(
    series: Series,
    *,
    resistance_ohm: float,
    correction_fraction: float = 1.0,
    electrode_area_cm2: float | None = None,
) -> Series:
    """Apply signed ohmic-drop correction ``E_corr = E - f * I * R``."""
    if series.x_axis.metadata.get("ir_corrected") is True or _history_has(
        series, "echem.correct_ir_drop"
    ):
        raise LSVError("potential has already been iR corrected")

    resistance = _nonnegative_finite(resistance_ohm, name="resistance_ohm")
    fraction = float(correction_fraction)
    if not isfinite(fraction) or not 0 <= fraction <= 1:
        raise LSVError("correction_fraction must be finite and between 0 and 1")

    potential_v = _potential_in_v(series)
    current_a, current_kind, area_basis = _current_from_series_in_a(
        series,
        electrode_area_cm2=electrode_area_cm2,
        allow_nan=False,
    )
    corrected = potential_v - fraction * current_a * resistance
    x_axis = _axis_with(
        series.x_axis,
        name="potential",
        unit="V",
        label="Potential",
        metadata_updates={"ir_corrected": True},
    )
    parameters: dict[str, Any] = {
        "resistance_ohm": resistance,
        "correction_fraction": fraction,
        "formula": "E_corrected = E - fraction * I * R",
        "current_kind": current_kind,
    }
    if current_kind == "current_density":
        parameters["electrode_area_cm2"] = float(electrode_area_cm2)
        parameters["density_area_basis"] = area_basis

    return _transform(
        series,
        x=corrected,
        x_axis=x_axis,
        operation="echem.correct_ir_drop",
        parameters=parameters,
    )


def to_current_density(
    series: Series,
    *,
    electrode_area_cm2: float,
    output_unit: str = "mA/cm^2",
) -> Series:
    """Normalize total current by geometric electrode area while preserving current sign."""
    area = _positive_finite(electrode_area_cm2, name="electrode_area_cm2")
    if is_current_density_unit(series.y_axis.unit):
        raise LSVError("Series y data are already current density; refusing double normalization")
    current_a = _current_in_a(series)

    try:
        canonical_unit = canonical_current_density_unit(output_unit)
        density = current_density_from_a_cm2(current_a / area, output_unit)
    except EchemQuantityError as exc:
        raise LSVError(str(exc)) from exc

    y_axis = _axis_with(
        series.y_axis,
        name="current_density",
        unit=canonical_unit,
        label="Current density",
        metadata_updates={
            "normalization": "geometric_area",
            "electrode_area_cm2": area,
        },
    )
    return _transform(
        series,
        y=density,
        y_axis=y_axis,
        operation="echem.to_current_density",
        parameters={"electrode_area_cm2": area, "output_unit": canonical_unit},
    )


@dataclass(frozen=True, slots=True)
class LSVProcessingConfig:
    """Explicit, serializable parameters for one LSV processing pipeline."""

    rhe_offset_v: float | None = None
    source_reference: str | None = None
    resistance_ohm: float | None = None
    ir_correction_fraction: float = 1.0
    electrode_area_cm2: float | None = None
    normalize_to_current_density: bool = False
    current_density_unit: str = "mA/cm^2"

    def __post_init__(self) -> None:
        if self.source_reference is not None:
            reference_name = _normalize_reference_name(self.source_reference)
            if self.rhe_offset_v is None:
                raise LSVError("source_reference requires rhe_offset_v")
            if reference_name.casefold() == "rhe":
                raise LSVError("source_reference must not be RHE when applying an RHE offset")
            object.__setattr__(self, "source_reference", reference_name)

        if self.rhe_offset_v is not None and not isfinite(float(self.rhe_offset_v)):
            raise LSVError("rhe_offset_v must be finite")
        if self.resistance_ohm is not None:
            _nonnegative_finite(self.resistance_ohm, name="resistance_ohm")
        fraction = float(self.ir_correction_fraction)
        if not isfinite(fraction) or not 0 <= fraction <= 1:
            raise LSVError("ir_correction_fraction must be between 0 and 1")
        if self.electrode_area_cm2 is not None:
            _positive_finite(self.electrode_area_cm2, name="electrode_area_cm2")
        if self.normalize_to_current_density and self.electrode_area_cm2 is None:
            raise LSVError(
                "electrode_area_cm2 is required when normalize_to_current_density=True"
            )
        try:
            canonical_current_density_unit(self.current_density_unit)
        except EchemQuantityError as exc:
            raise LSVError(
                "current_density_unit must be A/cm^2, mA/cm^2, or uA/cm^2"
            ) from exc


def process_lsv(series: Series, config: LSVProcessingConfig) -> Series:
    """Apply a deterministic LSV pipeline: RHE -> iR -> current-density normalization."""
    if not isinstance(config, LSVProcessingConfig):
        raise TypeError("config must be an LSVProcessingConfig")

    result = series
    if config.rhe_offset_v is not None:
        result = convert_potential_to_rhe(
            result,
            offset_v=config.rhe_offset_v,
            source_reference=config.source_reference,
        )
    if config.resistance_ohm is not None:
        result = correct_ir_drop(
            result,
            resistance_ohm=config.resistance_ohm,
            correction_fraction=config.ir_correction_fraction,
            electrode_area_cm2=config.electrode_area_cm2,
        )
    if config.normalize_to_current_density:
        result = to_current_density(
            result,
            electrode_area_cm2=float(config.electrode_area_cm2),
            output_unit=config.current_density_unit,
        )
    return result


def process_lsv_dataset(
    dataset: Dataset,
    config: LSVProcessingConfig,
    *,
    overrides: Mapping[str, LSVProcessingConfig] | None = None,
) -> Dataset:
    """Process a multi-catalyst Dataset with optional stable-key-specific configs."""
    if not isinstance(config, LSVProcessingConfig):
        raise TypeError("config must be an LSVProcessingConfig")
    per_series = {} if overrides is None else dict(overrides)
    if not all(isinstance(value, LSVProcessingConfig) for value in per_series.values()):
        raise TypeError("all overrides must be LSVProcessingConfig instances")

    available_keys = {item.key for item in dataset if item.key}
    unknown = set(per_series) - available_keys
    if unknown:
        raise LSVError(f"override keys not present in Dataset: {sorted(unknown)!r}")

    transformed = tuple(
        process_lsv(item, per_series.get(item.key, config)) for item in dataset
    )
    return Dataset(
        series=transformed,
        name=dataset.name,
        metadata=dataset.metadata_dict(),
    )
