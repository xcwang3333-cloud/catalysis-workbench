"""Scientific processing for LSV and polarization curves.

This module deliberately contains no plotting code. Publication rendering is owned by
``catalysis_workbench.visualization`` and will be connected through a thin LSV adapter
once the shared visualization layer is available.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from typing import Any

import numpy as np

from catalysis_workbench.core import Axis, Dataset, Series

_GAS_CONSTANT_J_MOL_K = 8.31446261815324
_FARADAY_CONSTANT_C_MOL = 96485.33212

_POTENTIAL_TO_V = {"v": 1.0, "mv": 1e-3}
_CURRENT_TO_A = {"a": 1.0, "ma": 1e-3, "ua": 1e-6}
_CURRENT_DENSITY_TO_A_CM2 = {
    "a/cm^2": 1.0,
    "a/cm2": 1.0,
    "acm^-2": 1.0,
    "acm-2": 1.0,
    "ma/cm^2": 1e-3,
    "ma/cm2": 1e-3,
    "macm^-2": 1e-3,
    "macm-2": 1e-3,
    "ua/cm^2": 1e-6,
    "ua/cm2": 1e-6,
    "uacm^-2": 1e-6,
    "uacm-2": 1e-6,
}
_CANONICAL_DENSITY_UNITS = {
    "a/cm^2": "A/cm^2",
    "ma/cm^2": "mA/cm^2",
    "ua/cm^2": "uA/cm^2",
}
_GEOMETRIC_NORMALIZATION_NAMES = {
    "geometric",
    "geometric_area",
    "geometric_area_cm2",
}


class LSVError(ValueError):
    """Raised when an LSV transformation is scientifically or numerically invalid."""


def _compact_unit(unit: str | None) -> str:
    if unit is None or not str(unit).strip():
        raise LSVError("electrochemical axis unit is required")
    compact = str(unit).strip().lower()
    compact = compact.replace("µ", "u").replace("μ", "u")
    compact = compact.replace("⁻²", "^-2")
    compact = compact.replace("−", "-").replace("⁻", "-").replace("²", "^2")
    compact = compact.replace("·", "").replace("*", "").replace(" ", "")
    return compact


def _normalize_reference_name(reference: str) -> str:
    name = " ".join(str(reference).split())
    if not name:
        raise LSVError("source_reference must not be empty")
    return name


def _same_reference(left: str, right: str) -> bool:
    return _normalize_reference_name(left).casefold() == _normalize_reference_name(right).casefold()


def _history_has(series: Series, operation: str) -> bool:
    history = series.metadata.get("processing_history", ())
    return any(
        isinstance(record, Mapping) and record.get("operation") == operation
        for record in history
    )


def _require_real(values: np.ndarray, *, quantity: str, allow_nan: bool = True) -> np.ndarray:
    array = np.asarray(values)
    if np.iscomplexobj(array):
        raise LSVError(f"{quantity} must be real-valued")
    real = array.astype(np.float64, copy=False)
    if np.isinf(real).any():
        raise LSVError(f"{quantity} must not contain +/-inf")
    if not allow_nan and np.isnan(real).any():
        raise LSVError(f"{quantity} must not contain missing values")
    return real


def _positive_finite(value: float, *, name: str) -> float:
    numeric = float(value)
    if not isfinite(numeric) or numeric <= 0:
        raise LSVError(f"{name} must be finite and greater than zero")
    return numeric


def _nonnegative_finite(value: float, *, name: str) -> float:
    numeric = float(value)
    if not isfinite(numeric) or numeric < 0:
        raise LSVError(f"{name} must be finite and non-negative")
    return numeric


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
    unit = _compact_unit(series.x_axis.unit)
    try:
        factor = _POTENTIAL_TO_V[unit]
    except KeyError as exc:
        raise LSVError(
            f"unsupported potential unit {series.x_axis.unit!r}; use V or mV"
        ) from exc
    potential = _require_real(series.x, quantity="potential", allow_nan=False)
    return potential * factor


def _current_in_a(series: Series) -> np.ndarray:
    unit = _compact_unit(series.y_axis.unit)
    try:
        factor = _CURRENT_TO_A[unit]
    except KeyError as exc:
        if unit in _CURRENT_DENSITY_TO_A_CM2:
            raise LSVError(
                "current-density input requires electrode area to recover total current"
            ) from exc
        raise LSVError(
            f"unsupported current unit {series.y_axis.unit!r}; use A, mA, or uA"
        ) from exc
    current = _require_real(series.y, quantity="current", allow_nan=True)
    return current * factor


def _current_from_series_in_a(
    series: Series,
    *,
    electrode_area_cm2: float | None,
    allow_nan: bool,
) -> tuple[np.ndarray, str, str | None]:
    unit = _compact_unit(series.y_axis.unit)
    values = _require_real(series.y, quantity="current", allow_nan=allow_nan)
    if unit in _CURRENT_TO_A:
        return values * _CURRENT_TO_A[unit], "current", None
    if unit in _CURRENT_DENSITY_TO_A_CM2:
        if electrode_area_cm2 is None:
            raise LSVError(
                "electrode_area_cm2 is required for iR correction of current-density data"
            )
        area = _positive_finite(electrode_area_cm2, name="electrode_area_cm2")
        declared = series.y_axis.metadata.get("normalization")
        if declared is not None:
            declared_name = str(declared).strip().lower().replace(" ", "_")
            if declared_name not in _GEOMETRIC_NORMALIZATION_NAMES:
                raise LSVError(
                    "current-density iR reconstruction requires geometric-area "
                    f"normalization; found {declared!r}"
                )
            area_basis = "geometric_area_declared"
        else:
            area_basis = "geometric_area_explicit_assumption"
        density_a_cm2 = values * _CURRENT_DENSITY_TO_A_CM2[unit]
        return density_a_cm2 * area, "current_density", area_basis
    raise LSVError(f"unsupported current/current-density unit {series.y_axis.unit!r}")


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
        2.303 * _GAS_CONSTANT_J_MOL_K * temperature / _FARADAY_CONSTANT_C_MOL
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
    input_unit = _compact_unit(series.y_axis.unit)
    if input_unit in _CURRENT_DENSITY_TO_A_CM2:
        raise LSVError("Series y data are already current density; refusing double normalization")
    current_a = _current_in_a(series)

    output_key = _compact_unit(output_unit)
    if output_key not in _CURRENT_DENSITY_TO_A_CM2:
        raise LSVError("output_unit must be A/cm^2, mA/cm^2, or uA/cm^2")
    factor = _CURRENT_DENSITY_TO_A_CM2[output_key]
    density = current_a / area / factor
    canonical_unit = _CANONICAL_DENSITY_UNITS.get(output_key)
    if canonical_unit is None:
        if output_key.startswith("ma"):
            canonical_unit = "mA/cm^2"
        elif output_key.startswith("ua"):
            canonical_unit = "uA/cm^2"
        else:
            canonical_unit = "A/cm^2"

    y_axis = _axis_with(
        series.y_axis,
        name="current_density",
        unit=canonical_unit,
        label="Current density",
        metadata_updates={"normalization": "geometric_area"},
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
        reference_name = None
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
        if _compact_unit(self.current_density_unit) not in _CURRENT_DENSITY_TO_A_CM2:
            raise LSVError("current_density_unit must be A/cm^2, mA/cm^2, or uA/cm^2")


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
