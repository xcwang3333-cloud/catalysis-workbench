"""Explicit gas-sorption isotherm semantics and conservative processing helpers."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from typing import Any, Literal

import numpy as np

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.processing import ProcessingError, crop, offset

SorptionBranch = Literal["adsorption", "desorption"]
SorptionBranchSelection = Literal["adsorption", "desorption", "all"]
RelativePressureUnit = Literal["1", "%"]
SorptionLoadingFamily = Literal[
    "molar_per_mass",
    "gas_volume_stp_per_mass",
    "mass_per_mass",
]
SorptionDirection = Literal["ascending", "descending"]

_RELATIVE_PRESSURE_NAMES = {
    "relativepressure",
    "pp0",
    "p0p",
}
_LOADING_NAMES = {"adsorbedquantity", "loading", "uptake"}
_FRACTION_UNITS = {"1", "fraction", "dimensionless"}
_PERCENT_UNITS = {"%", "percent", "percentage"}


class SorptionError(ValueError):
    """Raised when gas-sorption data or an operation violates the scientific contract."""


def _finite_float(value: Any, *, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a real numeric value") from exc
    if not isfinite(number):
        raise SorptionError(f"{name} must be finite")
    return number


def _positive_float(value: Any, *, name: str) -> float:
    number = _finite_float(value, name=name)
    if number <= 0.0:
        raise SorptionError(f"{name} must be greater than zero")
    return number


def _semantic_token(value: str) -> str:
    token = str(value).strip().casefold()
    token = token.replace("₀", "0")
    return "".join(character for character in token if character.isalnum())


def _compact_unit(unit: str) -> str:
    return (
        "".join(str(unit).strip().casefold().split())
        .replace("−", "-")
        .replace("⁻", "-")
        .replace("¹", "1")
        .replace("³", "3")
        .replace("^", "")
        .replace("·", "")
    )


def _relative_pressure_unit(unit: str | None) -> RelativePressureUnit:
    if unit is None or not str(unit).strip():
        raise SorptionError("relative pressure requires an explicit fraction or percent unit")
    token = _compact_unit(str(unit))
    if token in _FRACTION_UNITS:
        return "1"
    if token in _PERCENT_UNITS:
        return "%"
    raise SorptionError(
        f"unsupported relative-pressure unit {unit!r}; use '1' or '%'"
    )


def _loading_signature(unit: str | None) -> tuple[SorptionLoadingFamily, str]:
    if unit is None or not str(unit).strip():
        raise SorptionError("adsorbed quantity requires an explicit unit")
    token = _compact_unit(str(unit))
    molar_mmol = {
        "mmol/g",
        "mmolg-1",
        "mmolg1",
    }
    molar_molkg = {
        "mol/kg",
        "molkg-1",
        "molkg1",
    }
    mass_mass = {
        "mg/g",
        "mgg-1",
        "mgg1",
    }
    volume_stp = {
        "cm3(stp)/g",
        "cm3stp/g",
        "cm3(stp)g-1",
        "cm3stpg-1",
        "cm3(stp)g1",
        "cm3stpg1",
    }
    if token in molar_mmol:
        return "molar_per_mass", "mmol/g"
    if token in molar_molkg:
        return "molar_per_mass", "mol/kg"
    if token in mass_mass:
        return "mass_per_mass", "mg/g"
    if token in volume_stp:
        return "gas_volume_stp_per_mass", "cm^3(STP)/g"
    raise SorptionError(
        f"unsupported adsorbed-quantity unit {unit!r}; use mmol/g, mol/kg, "
        "mg/g, or cm^3(STP)/g"
    )


def _array_digest(values: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(values)
    digest = hashlib.sha256()
    digest.update(str(contiguous.dtype).encode("ascii"))
    digest.update(str(contiguous.shape).encode("ascii"))
    digest.update(contiguous.tobytes(order="C"))
    return digest.hexdigest()


def _series_data_digest(series: Series) -> str:
    digest = hashlib.sha256()
    digest.update(_array_digest(np.asarray(series.x)).encode("ascii"))
    digest.update(_array_digest(np.asarray(series.y)).encode("ascii"))
    return digest.hexdigest()


def _monotonic_direction(values: np.ndarray) -> SorptionDirection:
    delta = np.diff(values)
    if np.all(delta > 0.0):
        return "ascending"
    if np.all(delta < 0.0):
        return "descending"
    raise SorptionError(
        "relative-pressure values must be strictly monotonic without duplicates"
    )


def _validate_numeric_axes(series: Series) -> tuple[RelativePressureUnit, str, str]:
    if not isinstance(series, Series):
        raise TypeError("series must be a Series")
    if _semantic_token(series.x_axis.name) not in _RELATIVE_PRESSURE_NAMES:
        raise SorptionError(
            "gas sorption requires x_axis.name='relative_pressure' or an unambiguous P/P0 alias"
        )
    pressure_unit = _relative_pressure_unit(series.x_axis.unit)
    if _semantic_token(series.y_axis.name) not in _LOADING_NAMES:
        raise SorptionError(
            "gas sorption requires y_axis.name='adsorbed_quantity', 'loading', or 'uptake'"
        )
    loading_family, loading_unit = _loading_signature(series.y_axis.unit)

    x = np.asarray(series.x)
    y = np.asarray(series.y)
    if np.iscomplexobj(x) or np.iscomplexobj(y):
        raise SorptionError("gas-sorption pressure and loading values must be real")
    x = x.astype(np.float64, copy=False)
    y = y.astype(np.float64, copy=False)
    if x.size < 2:
        raise SorptionError("a sorption branch requires at least two measured points")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise SorptionError("gas-sorption values must be finite; missing values are not dropped")
    if np.any(x < 0.0):
        raise SorptionError("relative pressure must be non-negative")
    _monotonic_direction(x)
    return pressure_unit, loading_family, loading_unit


@dataclass(frozen=True, slots=True)
class SorptionCondition:
    """Explicit experimental conditions for one adsorption/desorption branch."""

    adsorbate: str
    measurement_temperature_k: float
    branch: SorptionBranch
    standard_temperature_k: float | None = None
    standard_pressure_kpa: float | None = None

    def __post_init__(self) -> None:
        adsorbate = str(self.adsorbate).strip()
        if not adsorbate:
            raise SorptionError("adsorbate must not be empty")
        temperature = _positive_float(
            self.measurement_temperature_k,
            name="measurement_temperature_k",
        )
        if self.branch not in {"adsorption", "desorption"}:
            raise SorptionError("branch must be 'adsorption' or 'desorption'")

        standard_temperature = (
            None
            if self.standard_temperature_k is None
            else _positive_float(
                self.standard_temperature_k,
                name="standard_temperature_k",
            )
        )
        standard_pressure = (
            None
            if self.standard_pressure_kpa is None
            else _positive_float(
                self.standard_pressure_kpa,
                name="standard_pressure_kpa",
            )
        )
        if (standard_temperature is None) != (standard_pressure is None):
            raise SorptionError(
                "standard_temperature_k and standard_pressure_kpa must be supplied together"
            )

        object.__setattr__(self, "adsorbate", adsorbate)
        object.__setattr__(self, "measurement_temperature_k", temperature)
        object.__setattr__(self, "standard_temperature_k", standard_temperature)
        object.__setattr__(self, "standard_pressure_kpa", standard_pressure)


def prepare_sorption_series(series: Series, condition: SorptionCondition) -> Series:
    """Attach explicit sorption conditions and canonical axis semantics without fitting."""
    if not isinstance(condition, SorptionCondition):
        raise TypeError("condition must be a SorptionCondition")
    pressure_unit, loading_family, loading_unit = _validate_numeric_axes(series)
    if loading_family == "gas_volume_stp_per_mass":
        if condition.standard_temperature_k is None or condition.standard_pressure_kpa is None:
            raise SorptionError(
                "cm^3(STP)/g loading requires explicit standard_temperature_k and "
                "standard_pressure_kpa"
            )

    source_sha256 = _series_data_digest(series)
    x = np.asarray(series.x, dtype=np.float64)
    metadata = series.metadata_dict()
    metadata.update(
        {
            "sorption_adsorbate": condition.adsorbate,
            "sorption_temperature_k": condition.measurement_temperature_k,
            "sorption_branch": condition.branch,
            "sorption_pressure_representation": "relative",
            "sorption_loading_family": loading_family,
            "sorption_source_direction": _monotonic_direction(x),
            "sorption_source_sha256": source_sha256,
        }
    )
    if loading_family == "gas_volume_stp_per_mass":
        metadata.update(
            {
                "sorption_standard_temperature_k": condition.standard_temperature_k,
                "sorption_standard_pressure_kpa": condition.standard_pressure_kpa,
            }
        )
    else:
        metadata.pop("sorption_standard_temperature_k", None)
        metadata.pop("sorption_standard_pressure_kpa", None)

    history = list(metadata.get("processing_history", []))
    history.append(
        {
            "operation": "sorption.prepare",
            "parameters": {
                "adsorbate": condition.adsorbate,
                "measurement_temperature_k": condition.measurement_temperature_k,
                "branch": condition.branch,
                "relative_pressure_unit": pressure_unit,
                "loading_family": loading_family,
                "loading_unit": loading_unit,
                "standard_temperature_k": condition.standard_temperature_k,
                "standard_pressure_kpa": condition.standard_pressure_kpa,
                "source_sha256": source_sha256,
            },
        }
    )
    metadata["processing_history"] = history

    return Series(
        x=series.x,
        y=series.y,
        label=series.label,
        key=series.key,
        x_axis=Axis(
            "relative_pressure",
            unit=pressure_unit,
            label=series.x_axis.label or "Relative pressure, P/P0",
            metadata=series.x_axis.metadata_dict(),
        ),
        y_axis=Axis(
            "adsorbed_quantity",
            unit=loading_unit,
            label=series.y_axis.label or "Adsorbed quantity",
            metadata=series.y_axis.metadata_dict(),
        ),
        metadata=metadata,
    )


def _condition_from_series(series: Series) -> SorptionCondition:
    metadata = series.metadata
    try:
        adsorbate = str(metadata["sorption_adsorbate"])
        temperature = float(metadata["sorption_temperature_k"])
        branch = str(metadata["sorption_branch"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SorptionError(
            "prepared sorption Series requires explicit adsorbate, measurement temperature, "
            "and branch metadata"
        ) from exc
    if branch not in {"adsorption", "desorption"}:
        raise SorptionError("invalid sorption_branch metadata")
    standard_temperature = metadata.get("sorption_standard_temperature_k")
    standard_pressure = metadata.get("sorption_standard_pressure_kpa")
    return SorptionCondition(
        adsorbate=adsorbate,
        measurement_temperature_k=temperature,
        branch=branch,
        standard_temperature_k=standard_temperature,
        standard_pressure_kpa=standard_pressure,
    )


def validate_sorption_series(series: Series) -> None:
    """Validate a prepared sorption branch without changing its numerical data."""
    pressure_unit, loading_family, loading_unit = _validate_numeric_axes(series)
    condition = _condition_from_series(series)
    declared_family = str(series.metadata.get("sorption_loading_family", "")).strip()
    if declared_family != loading_family:
        raise SorptionError(
            f"sorption_loading_family {declared_family!r} conflicts with unit {loading_unit!r}"
        )
    if series.metadata.get("sorption_pressure_representation") != "relative":
        raise SorptionError("sorption pressure representation must be explicitly 'relative'")
    if loading_family == "gas_volume_stp_per_mass":
        if condition.standard_temperature_k is None or condition.standard_pressure_kpa is None:
            raise SorptionError(
                "cm^3(STP)/g loading requires explicit standard gas conditions"
            )
    _relative_pressure_unit(pressure_unit)


def _canonicalize_sorption_series(series: Series) -> Series:
    validate_sorption_series(series)
    pressure_unit, loading_family, loading_unit = _validate_numeric_axes(series)
    condition = _condition_from_series(series)
    metadata = series.metadata_dict()
    metadata["sorption_loading_family"] = loading_family
    return Series(
        x=series.x,
        y=series.y,
        label=series.label,
        key=series.key,
        x_axis=Axis(
            "relative_pressure",
            unit=pressure_unit,
            label=series.x_axis.label or "Relative pressure, P/P0",
            metadata=series.x_axis.metadata_dict(),
        ),
        y_axis=Axis(
            "adsorbed_quantity",
            unit=loading_unit,
            label=series.y_axis.label or "Adsorbed quantity",
            metadata=series.y_axis.metadata_dict(),
        ),
        metadata={
            **metadata,
            "sorption_adsorbate": condition.adsorbate,
            "sorption_temperature_k": condition.measurement_temperature_k,
            "sorption_branch": condition.branch,
        },
    )


def convert_relative_pressure(
    series: Series,
    *,
    target_unit: Literal["fraction", "1", "percent", "%"],
) -> Series:
    """Explicitly convert relative pressure between fraction and percent."""
    source = _canonicalize_sorption_series(series)
    source_unit = _relative_pressure_unit(source.x_axis.unit)
    target: RelativePressureUnit
    if target_unit in {"fraction", "1"}:
        target = "1"
    elif target_unit in {"percent", "%"}:
        target = "%"
    else:
        raise SorptionError("target_unit must be 'fraction'/'1' or 'percent'/'%'")

    x = np.asarray(source.x, dtype=np.float64)
    if source_unit == target:
        converted = np.array(x, copy=True)
    elif target == "%":
        converted = x * 100.0
    else:
        converted = x / 100.0

    source_sha256 = _series_data_digest(source)
    x_metadata = source.x_axis.metadata_dict()
    x_metadata.update(
        {
            "relative_pressure_conversion": f"{source_unit}->{target}",
            "source_sha256": source_sha256,
        }
    )
    metadata = source.metadata_dict()
    history = list(metadata.get("processing_history", []))
    history.append(
        {
            "operation": "sorption.convert_relative_pressure",
            "parameters": {
                "source_unit": source_unit,
                "target_unit": target,
                "source_sha256": source_sha256,
            },
        }
    )
    metadata["processing_history"] = history
    return Series(
        x=converted,
        y=source.y,
        label=source.label,
        key=source.key,
        x_axis=Axis(
            "relative_pressure",
            unit=target,
            label=source.x_axis.label,
            metadata=x_metadata,
        ),
        y_axis=source.y_axis,
        metadata=metadata,
    )


@dataclass(frozen=True, slots=True)
class SorptionProcessingConfig:
    """Explicit non-model sorption processing recipe."""

    relative_pressure_min: float | None = None
    relative_pressure_max: float | None = None
    vertical_offset: float = 0.0

    def __post_init__(self) -> None:
        minimum = (
            None
            if self.relative_pressure_min is None
            else _finite_float(
                self.relative_pressure_min,
                name="relative_pressure_min",
            )
        )
        maximum = (
            None
            if self.relative_pressure_max is None
            else _finite_float(
                self.relative_pressure_max,
                name="relative_pressure_max",
            )
        )
        if minimum is not None and minimum < 0.0:
            raise SorptionError("relative_pressure_min must be non-negative")
        if maximum is not None and maximum < 0.0:
            raise SorptionError("relative_pressure_max must be non-negative")
        if minimum is not None and maximum is not None and minimum > maximum:
            raise SorptionError("relative_pressure_min must be <= relative_pressure_max")
        vertical_offset = _finite_float(self.vertical_offset, name="vertical_offset")
        object.__setattr__(self, "relative_pressure_min", minimum)
        object.__setattr__(self, "relative_pressure_max", maximum)
        object.__setattr__(self, "vertical_offset", vertical_offset)


def process_sorption(
    series: Series,
    *,
    condition: SorptionCondition | None = None,
    config: SorptionProcessingConfig | None = None,
) -> Series:
    """Prepare/validate and apply only explicit crop/offset sorption processing."""
    source = (
        prepare_sorption_series(series, condition)
        if condition is not None
        else _canonicalize_sorption_series(series)
    )
    resolved = SorptionProcessingConfig() if config is None else config
    if not isinstance(resolved, SorptionProcessingConfig):
        raise TypeError("config must be a SorptionProcessingConfig")

    result = source
    if resolved.relative_pressure_min is not None or resolved.relative_pressure_max is not None:
        try:
            result = crop(
                result,
                x_min=resolved.relative_pressure_min,
                x_max=resolved.relative_pressure_max,
            )
        except ProcessingError as exc:
            raise SorptionError(str(exc)) from exc
        validate_sorption_series(result)
    if resolved.vertical_offset != 0.0:
        try:
            result = offset(result, resolved.vertical_offset)
        except ProcessingError as exc:
            raise SorptionError(str(exc)) from exc
    return result


def _require_keyed_dataset(dataset: Dataset, *, operation: str) -> None:
    if not isinstance(dataset, Dataset):
        raise TypeError("dataset must be a Dataset")
    if any(not key for key in dataset.keys):
        raise SorptionError(f"{operation} requires non-empty Series.key values")


def process_sorption_dataset(
    dataset: Dataset,
    *,
    conditions: Mapping[str, SorptionCondition] | None = None,
    config: SorptionProcessingConfig | None = None,
    overrides: Mapping[str, SorptionProcessingConfig] | None = None,
) -> Dataset:
    """Process a sorption Dataset with stable-key condition/config mappings."""
    _require_keyed_dataset(dataset, operation="process_sorption_dataset")
    condition_map = {} if conditions is None else dict(conditions)
    override_map = {} if overrides is None else dict(overrides)
    keys = set(dataset.keys)
    unknown_conditions = set(condition_map) - keys
    unknown_overrides = set(override_map) - keys
    if unknown_conditions:
        raise SorptionError(
            f"condition keys not present in Dataset: {sorted(unknown_conditions)!r}"
        )
    if unknown_overrides:
        raise SorptionError(
            f"override keys not present in Dataset: {sorted(unknown_overrides)!r}"
        )
    if not all(isinstance(value, SorptionCondition) for value in condition_map.values()):
        raise TypeError("conditions values must be SorptionCondition instances")
    if not all(
        isinstance(value, SorptionProcessingConfig) for value in override_map.values()
    ):
        raise TypeError("overrides values must be SorptionProcessingConfig instances")
    default = SorptionProcessingConfig() if config is None else config
    if not isinstance(default, SorptionProcessingConfig):
        raise TypeError("config must be a SorptionProcessingConfig")

    processed = tuple(
        process_sorption(
            item,
            condition=condition_map.get(item.key),
            config=override_map.get(item.key, default),
        )
        for item in dataset
    )
    return Dataset(
        series=processed,
        name=dataset.name,
        metadata=dataset.metadata_dict(),
    )


def _overlay_signature(series: Series) -> tuple[Any, ...]:
    source = _canonicalize_sorption_series(series)
    condition = _condition_from_series(source)
    loading_family, loading_unit = _loading_signature(source.y_axis.unit)
    standard = (
        condition.standard_temperature_k,
        condition.standard_pressure_kpa,
    ) if loading_family == "gas_volume_stp_per_mass" else (None, None)
    return (
        condition.adsorbate.casefold(),
        condition.measurement_temperature_k,
        source.x_axis.unit,
        source.y_axis.name,
        loading_family,
        loading_unit,
        standard,
    )


def validate_sorption_overlay(data: Series | Dataset) -> None:
    """Reject overlays with incompatible adsorbate/conditions/units/bases."""
    if isinstance(data, Series):
        _canonicalize_sorption_series(data)
        return
    if not isinstance(data, Dataset):
        raise TypeError("data must be a Series or Dataset")
    if len(data) == 0:
        raise SorptionError("cannot use an empty sorption Dataset")
    signatures = [_overlay_signature(item) for item in data]
    expected = signatures[0]
    for index, signature in enumerate(signatures[1:], start=1):
        if signature != expected:
            raise SorptionError(
                "sorption overlay requires matching adsorbate/measurement temperature/"
                "relative-pressure unit/loading basis-unit/standard gas condition; "
                f"Series index {index} has {signature!r}, expected {expected!r}"
            )


def select_sorption_branch(
    data: Series | Dataset,
    *,
    branch: SorptionBranchSelection = "all",
) -> Series | Dataset:
    """Filter only already-declared sorption branches; never infer branch from x direction."""
    if branch not in {"adsorption", "desorption", "all"}:
        raise SorptionError("branch must be 'adsorption', 'desorption', or 'all'")
    if isinstance(data, Series):
        source = _canonicalize_sorption_series(data)
        declared = str(source.metadata["sorption_branch"])
        if branch != "all" and declared != branch:
            raise SorptionError(
                f"requested branch {branch!r} is not present in the supplied Series"
            )
        return source
    if not isinstance(data, Dataset):
        raise TypeError("data must be a Series or Dataset")
    if len(data) == 0:
        raise SorptionError("cannot filter an empty sorption Dataset")
    canonical = tuple(_canonicalize_sorption_series(item) for item in data)
    if branch == "all":
        selected = canonical
    else:
        selected = tuple(
            item for item in canonical if item.metadata["sorption_branch"] == branch
        )
    if not selected:
        raise SorptionError(f"Dataset contains no declared {branch!r} branch")
    return Dataset(
        series=selected,
        name=data.name,
        metadata=data.metadata_dict(),
    )


@dataclass(frozen=True, slots=True)
class SorptionWindow:
    """Explicit relative-pressure interval for measured-point summaries."""

    low: float
    high: float
    label: str = ""

    def __post_init__(self) -> None:
        low = _finite_float(self.low, name="low")
        high = _finite_float(self.high, name="high")
        if low < 0.0 or high < 0.0:
            raise SorptionError("SorptionWindow bounds must be non-negative")
        if low >= high:
            raise SorptionError("SorptionWindow requires low < high")
        object.__setattr__(self, "low", low)
        object.__setattr__(self, "high", high)
        object.__setattr__(self, "label", str(self.label).strip())


@dataclass(frozen=True, slots=True)
class SorptionWindowSummary:
    """Measured-point-only loading summary for an explicit relative-pressure window."""

    window: SorptionWindow
    n_measured_points: int
    minimum_loading: float
    minimum_relative_pressure: float
    maximum_loading: float
    maximum_relative_pressure: float
    pressure_unit: str
    loading_unit: str
    branch: SorptionBranch
    source_direction: SorptionDirection
    source_key: str
    source_label: str
    source_sha256: str


def summarize_sorption_window(
    series: Series,
    window: SorptionWindow,
) -> SorptionWindowSummary:
    """Summarize only measured points inside a caller-supplied pressure window."""
    source = _canonicalize_sorption_series(series)
    if not isinstance(window, SorptionWindow):
        raise TypeError("window must be a SorptionWindow")
    x = np.asarray(source.x, dtype=np.float64)
    y = np.asarray(source.y, dtype=np.float64)
    lower = float(np.min(x))
    upper = float(np.max(x))
    if window.low < lower or window.high > upper:
        raise SorptionError("sorption window must be fully contained in measured range")
    mask = (x >= window.low) & (x <= window.high)
    indices = np.flatnonzero(mask)
    if indices.size == 0:
        raise SorptionError(
            "sorption window contains no measured points; interpolation is not performed"
        )
    selected_y = y[indices]
    min_local = int(np.argmin(selected_y))
    max_local = int(np.argmax(selected_y))
    min_index = int(indices[min_local])
    max_index = int(indices[max_local])
    return SorptionWindowSummary(
        window=window,
        n_measured_points=int(indices.size),
        minimum_loading=float(y[min_index]),
        minimum_relative_pressure=float(x[min_index]),
        maximum_loading=float(y[max_index]),
        maximum_relative_pressure=float(x[max_index]),
        pressure_unit=str(source.x_axis.unit),
        loading_unit=str(source.y_axis.unit),
        branch=str(source.metadata["sorption_branch"]),
        source_direction=_monotonic_direction(x),
        source_key=source.key,
        source_label=source.label,
        source_sha256=_series_data_digest(source),
    )
