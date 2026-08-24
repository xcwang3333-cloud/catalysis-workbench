"""Scientific processing and quantitative helpers for thermal-analysis curves."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from typing import Any, Literal

import numpy as np

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.processing import ProcessingError, crop, offset

ThermalTechnique = Literal["tga", "dtg", "tpr", "tpd"]
TemperatureUnit = Literal["°C", "K"]
TGANormalization = Literal["fraction", "percent"]
DTGSignMode = Literal["signed", "mass_loss_positive"]
ThermalAreaMode = Literal["net", "absolute"]
ThermalExtremumMode = Literal["maximum", "minimum"]
ThermalDirection = Literal["ascending", "descending"]

_TEMPERATURE_NAMES = {"temperature", "temp"}
_TGA_MASS_NAMES = {"mass", "weight"}
_TGA_FRACTION_NAMES = {"massfraction", "weightfraction"}
_TGA_PERCENT_NAMES = {"masspercent", "weightpercent", "weightpercentage"}
_SIGNAL_NAMES = {"signal", "detectorsignal", "response"}
_NORMALIZED_SIGNAL_NAMES = {"normalizedsignal", "normalizedresponse"}
_DTG_NAMES = {"dtg", "massderivative", "masslossrate"}
_MASS_UNITS = {
    "g": "g",
    "gram": "g",
    "grams": "g",
    "mg": "mg",
    "milligram": "mg",
    "milligrams": "mg",
    "ug": "µg",
    "microgram": "µg",
    "micrograms": "µg",
}
_FRACTION_UNITS = {"1", "fraction", "dimensionless"}
_PERCENT_UNITS = {"%", "percent", "percentage"}


class ThermalError(ValueError):
    """Raised when thermal-analysis data or an operation is scientifically invalid."""


def _finite_float(value: Any, *, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a real numeric value") from exc
    if not isfinite(result):
        raise ThermalError(f"{name} must be finite")
    return result


def _semantic_token(value: str) -> str:
    token = str(value).strip().casefold()
    return "".join(character for character in token if character.isalnum())


def _compact_unit(unit: str) -> str:
    return (
        "".join(str(unit).strip().casefold().split())
        .replace("μ", "u")
        .replace("µ", "u")
        .replace("−", "-")
    )


def _temperature_unit(unit: str | None) -> TemperatureUnit:
    if unit is None or not str(unit).strip():
        raise ThermalError("temperature requires an explicit degree-Celsius or kelvin unit")
    token = _compact_unit(str(unit)).replace("℃", "°c")
    if token in {"°c", "c", "degc", "celsius", "degreecelsius", "degreescelsius"}:
        return "°C"
    if token in {"k", "kelvin", "kelvins"}:
        return "K"
    raise ThermalError(
        f"unsupported temperature unit {unit!r}; use °C/degC/celsius or K/kelvin"
    )


def _mass_unit(unit: str | None) -> str:
    if unit is None or not str(unit).strip():
        raise ThermalError("raw TGA mass requires an explicit mass unit")
    token = _compact_unit(str(unit))
    canonical = _MASS_UNITS.get(token)
    if canonical is None:
        raise ThermalError(f"unsupported TGA mass unit {unit!r}; use g, mg, or µg")
    return canonical


def _tga_y_semantic(series: Series) -> Literal["mass", "mass_fraction", "mass_percent"]:
    token = _semantic_token(series.y_axis.name)
    if token in _TGA_MASS_NAMES:
        return "mass"
    if token in _TGA_FRACTION_NAMES:
        return "mass_fraction"
    if token in _TGA_PERCENT_NAMES:
        return "mass_percent"
    raise ThermalError(
        "TGA requires y_axis.name='mass', 'mass_fraction', or 'mass_percent' "
        "(weight aliases are accepted)"
    )


def _tga_y_unit(series: Series, semantic: str) -> str:
    unit = series.y_axis.unit
    if semantic == "mass":
        return _mass_unit(unit)
    if unit is None or not str(unit).strip():
        raise ThermalError(f"{semantic} requires an explicit unit")
    token = _compact_unit(str(unit))
    if semantic == "mass_fraction" and token in _FRACTION_UNITS:
        return "1"
    if semantic == "mass_percent" and token in _PERCENT_UNITS:
        return "%"
    raise ThermalError(
        f"{semantic} has incompatible unit {unit!r}; use '1' for fraction or '%' for percent"
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


def _monotonic_direction(x: np.ndarray) -> ThermalDirection:
    delta = np.diff(x)
    if np.all(delta > 0):
        return "ascending"
    if np.all(delta < 0):
        return "descending"
    raise ThermalError("temperature values must be strictly monotonic without duplicates")


def _validate_temperature_axis(series: Series, *, minimum_points: int = 2) -> TemperatureUnit:
    if not isinstance(series, Series):
        raise TypeError("series must be a Series")
    if _semantic_token(series.x_axis.name) not in _TEMPERATURE_NAMES:
        raise ThermalError("thermal analysis requires x_axis.name='temperature' or 'temp'")
    unit = _temperature_unit(series.x_axis.unit)
    x = np.asarray(series.x)
    if np.iscomplexobj(x):
        raise ThermalError("temperature values must be real")
    x = x.astype(np.float64, copy=False)
    if x.size < minimum_points:
        raise ThermalError(f"thermal curves require at least {minimum_points} temperature points")
    if np.isnan(x).any() or np.isinf(x).any():
        raise ThermalError("temperature values must be finite")
    if unit == "K" and np.any(x < 0.0):
        raise ThermalError("kelvin temperature values must be non-negative")
    _monotonic_direction(x)
    return unit


def _validate_real_y(series: Series, *, operation: str, require_finite: bool = False) -> np.ndarray:
    y = np.asarray(series.y)
    if np.iscomplexobj(y):
        raise ThermalError(f"{operation} requires real y values")
    y = y.astype(np.float64, copy=False)
    if np.isinf(y).any():
        raise ThermalError(f"{operation} y values must not contain +/-inf")
    if require_finite and np.isnan(y).any():
        raise ThermalError(f"{operation} does not silently discard missing y values")
    return y


def _with_processing_record(
    series: Series,
    *,
    operation: str,
    parameters: Mapping[str, Any],
    x: np.ndarray | None = None,
    y: np.ndarray | None = None,
    x_axis: Axis | None = None,
    y_axis: Axis | None = None,
) -> Series:
    metadata = series.metadata_dict()
    history = list(metadata.get("processing_history", []))
    history.append({"operation": operation, "parameters": dict(parameters)})
    metadata["processing_history"] = history
    return Series(
        x=series.x if x is None else x,
        y=series.y if y is None else y,
        label=series.label,
        key=series.key,
        x_axis=series.x_axis if x_axis is None else x_axis,
        y_axis=series.y_axis if y_axis is None else y_axis,
        metadata=metadata,
    )


def validate_tga_series(series: Series) -> None:
    """Validate one TGA mass curve without normalizing or reordering it."""
    _validate_temperature_axis(series)
    semantic = _tga_y_semantic(series)
    _tga_y_unit(series, semantic)
    _validate_real_y(series, operation="TGA validation")


def _canonicalize_tga_series(series: Series) -> Series:
    validate_tga_series(series)
    semantic = _tga_y_semantic(series)
    y_unit = _tga_y_unit(series, semantic)
    temperature_unit = _temperature_unit(series.x_axis.unit)
    y_label = {
        "mass": "Mass",
        "mass_fraction": "Mass fraction",
        "mass_percent": "Mass",
    }[semantic]
    return Series(
        x=series.x,
        y=series.y,
        label=series.label,
        key=series.key,
        x_axis=Axis(
            "temperature",
            unit=temperature_unit,
            label=series.x_axis.label or "Temperature",
            metadata=series.x_axis.metadata_dict(),
        ),
        y_axis=Axis(
            semantic,
            unit=y_unit,
            label=series.y_axis.label or y_label,
            metadata=series.y_axis.metadata_dict(),
        ),
        metadata=series.metadata_dict(),
    )


def convert_temperature(series: Series, *, target_unit: Literal["degC", "°C", "K", "kelvin"]) -> Series:
    """Explicitly convert a thermal curve temperature axis between Celsius and kelvin."""
    source_unit = _validate_temperature_axis(series)
    if target_unit in {"degC", "°C"}:
        target: TemperatureUnit = "°C"
    elif target_unit in {"K", "kelvin"}:
        target = "K"
    else:
        raise ThermalError("target_unit must be 'degC'/'°C' or 'K'/'kelvin'")

    x = np.asarray(series.x, dtype=np.float64)
    if source_unit == target:
        converted = np.array(x, copy=True)
    elif source_unit == "K":
        converted = x - 273.15
    else:
        converted = x + 273.15
        if np.any(converted < 0.0):
            raise ThermalError("Celsius-to-kelvin conversion would produce temperature below 0 K")

    source_sha256 = _series_data_digest(series)
    x_metadata = series.x_axis.metadata_dict()
    x_metadata.update(
        {
            "temperature_conversion": f"{source_unit}->{target}",
            "source_sha256": source_sha256,
        }
    )
    return _with_processing_record(
        series,
        operation="convert_temperature",
        parameters={
            "source_unit": source_unit,
            "target_unit": target,
            "source_sha256": source_sha256,
        },
        x=converted,
        x_axis=Axis(
            "temperature",
            unit=target,
            label=series.x_axis.label or "Temperature",
            metadata=x_metadata,
        ),
    )


def normalize_tga_mass(
    series: Series,
    *,
    output: TGANormalization = "percent",
    reference: Literal["first_point"] | float = "first_point",
) -> Series:
    """Explicitly normalize raw TGA mass to fraction or percent."""
    source = _canonicalize_tga_series(series)
    semantic = _tga_y_semantic(source)
    if semantic != "mass":
        raise ThermalError("normalize_tga_mass requires raw mass data; input is already normalized")
    if output not in {"fraction", "percent"}:
        raise ThermalError("output must be 'fraction' or 'percent'")
    y = _validate_real_y(source, operation="TGA normalization", require_finite=True)

    if isinstance(reference, str):
        if reference != "first_point":
            raise ThermalError("reference string must be 'first_point'")
        reference_value = float(y[0])
        reference_basis = "first_point"
    else:
        if isinstance(reference, bool):
            raise TypeError("reference mass must be a real numeric value")
        reference_value = _finite_float(reference, name="reference")
        reference_basis = "explicit"
    if reference_value <= 0.0:
        raise ThermalError("TGA normalization reference mass must be greater than zero")

    normalized = y / reference_value
    if output == "percent":
        normalized = normalized * 100.0
        y_name, y_unit, y_label = "mass_percent", "%", "Mass"
    else:
        y_name, y_unit, y_label = "mass_fraction", "1", "Mass fraction"

    source_sha256 = _series_data_digest(source)
    y_metadata = source.y_axis.metadata_dict()
    normalization_signature = (
        f"thermal:tga:{output}:reference={reference_basis}:value={reference_value!r}:"
        f"unit={source.y_axis.unit}"
    )
    y_metadata.update(
        {
            "normalization": normalization_signature,
            "normalization_method": "tga_reference_mass",
            "normalization_output": output,
            "normalization_reference_basis": reference_basis,
            "normalization_reference_value": reference_value,
            "normalization_reference_unit": source.y_axis.unit,
            "source_sha256": source_sha256,
        }
    )
    return _with_processing_record(
        source,
        operation="normalize_tga_mass",
        parameters={
            "output": output,
            "reference_basis": reference_basis,
            "reference_value": reference_value,
            "reference_unit": source.y_axis.unit,
            "source_sha256": source_sha256,
        },
        y=normalized,
        y_axis=Axis(y_name, unit=y_unit, label=y_label, metadata=y_metadata),
    )


def _dtg_unit(base_unit: str, temperature_unit: TemperatureUnit) -> str:
    return f"{base_unit}/{temperature_unit}"


def derive_dtg(series: Series, *, sign_mode: DTGSignMode = "signed") -> Series:
    """Derive DTG explicitly as ``dy/dT`` or positive mass-loss rate ``-dy/dT``."""
    source = _canonicalize_tga_series(series)
    _validate_temperature_axis(source, minimum_points=3)
    if sign_mode not in {"signed", "mass_loss_positive"}:
        raise ThermalError("sign_mode must be 'signed' or 'mass_loss_positive'")
    x = np.asarray(source.x, dtype=np.float64)
    y = _validate_real_y(source, operation="DTG derivation", require_finite=True)
    derivative = np.gradient(y, x, edge_order=1)
    if sign_mode == "mass_loss_positive":
        derivative = -derivative

    source_semantic = _tga_y_semantic(source)
    source_unit = _tga_y_unit(source, source_semantic)
    temperature_unit = _temperature_unit(source.x_axis.unit)
    source_sha256 = _series_data_digest(source)
    y_metadata = source.y_axis.metadata_dict()
    y_metadata.update(
        {
            "thermal_technique": "dtg",
            "dtg_sign_mode": sign_mode,
            "derivative_backend": "numpy.gradient",
            "derivative_edge_order": 1,
            "source_mass_semantic": source_semantic,
            "source_sha256": source_sha256,
        }
    )
    y_name = "mass_derivative" if sign_mode == "signed" else "mass_loss_rate"
    y_label = "dMass/dT" if sign_mode == "signed" else "Mass-loss rate"
    return _with_processing_record(
        source,
        operation="derive_dtg",
        parameters={
            "backend": "numpy.gradient",
            "edge_order": 1,
            "sign_mode": sign_mode,
            "source_direction": _monotonic_direction(x),
            "source_sha256": source_sha256,
        },
        y=derivative,
        y_axis=Axis(
            y_name,
            unit=_dtg_unit(source_unit, temperature_unit),
            label=y_label,
            metadata=y_metadata,
        ),
    )


def validate_dtg_series(series: Series) -> None:
    """Validate a DTG curve with an explicit sign convention."""
    temperature_unit = _validate_temperature_axis(series)
    if _semantic_token(series.y_axis.name) not in _DTG_NAMES:
        raise ThermalError("DTG requires y_axis.name='mass_derivative' or 'mass_loss_rate'")
    sign_mode = series.y_axis.metadata.get("dtg_sign_mode")
    if sign_mode not in {"signed", "mass_loss_positive"}:
        raise ThermalError("DTG requires explicit y_axis.metadata['dtg_sign_mode']")
    source_semantic = str(series.y_axis.metadata.get("source_mass_semantic", "")).strip()
    if source_semantic not in {"mass", "mass_fraction", "mass_percent"}:
        raise ThermalError("DTG requires explicit source_mass_semantic metadata")
    base_unit = {
        "mass": _mass_unit(str(series.y_axis.unit).split("/", 1)[0]),
        "mass_fraction": "1",
        "mass_percent": "%",
    }[source_semantic]
    expected = _dtg_unit(base_unit, temperature_unit)
    unit = str(series.y_axis.unit or "").replace("degC", "°C")
    if unit != expected:
        raise ThermalError(f"DTG unit {series.y_axis.unit!r} is incompatible; expected {expected!r}")
    _validate_real_y(series, operation="DTG validation")


def _canonicalize_dtg_series(series: Series) -> Series:
    validate_dtg_series(series)
    sign_mode = str(series.y_axis.metadata["dtg_sign_mode"])
    source_semantic = str(series.y_axis.metadata["source_mass_semantic"])
    temperature_unit = _temperature_unit(series.x_axis.unit)
    base_unit = {
        "mass": _mass_unit(str(series.y_axis.unit).split("/", 1)[0]),
        "mass_fraction": "1",
        "mass_percent": "%",
    }[source_semantic]
    y_name = "mass_derivative" if sign_mode == "signed" else "mass_loss_rate"
    y_label = "dMass/dT" if sign_mode == "signed" else "Mass-loss rate"
    return Series(
        x=series.x,
        y=series.y,
        label=series.label,
        key=series.key,
        x_axis=Axis(
            "temperature",
            unit=temperature_unit,
            label=series.x_axis.label or "Temperature",
            metadata=series.x_axis.metadata_dict(),
        ),
        y_axis=Axis(
            y_name,
            unit=_dtg_unit(base_unit, temperature_unit),
            label=series.y_axis.label or y_label,
            metadata=series.y_axis.metadata_dict(),
        ),
        metadata=series.metadata_dict(),
    )


def validate_temperature_programmed_series(
    series: Series,
    *,
    technique: Literal["tpr", "tpd"],
) -> None:
    """Validate an explicit TPR/TPD detector-signal curve."""
    if technique not in {"tpr", "tpd"}:
        raise ThermalError("technique must be 'tpr' or 'tpd'")
    _validate_temperature_axis(series)
    token = _semantic_token(series.y_axis.name)
    if token not in _SIGNAL_NAMES | _NORMALIZED_SIGNAL_NAMES:
        raise ThermalError(
            "TPR/TPD requires y_axis.name='detector_signal', 'signal', 'response', "
            "or 'normalized_signal'"
        )
    if series.y_axis.unit is None or not str(series.y_axis.unit).strip():
        raise ThermalError("TPR/TPD detector signal requires an explicit unit string")
    declared = series.y_axis.metadata.get("thermal_technique")
    if declared is not None and str(declared).strip().casefold() != technique:
        raise ThermalError(
            f"declared thermal_technique {declared!r} conflicts with requested {technique!r}"
        )
    _validate_real_y(series, operation=technique.upper())


def _canonicalize_programmed_series(series: Series, technique: Literal["tpr", "tpd"]) -> Series:
    validate_temperature_programmed_series(series, technique=technique)
    temperature_unit = _temperature_unit(series.x_axis.unit)
    normalized = _semantic_token(series.y_axis.name) in _NORMALIZED_SIGNAL_NAMES
    y_name = "normalized_signal" if normalized else "detector_signal"
    y_metadata = series.y_axis.metadata_dict()
    y_metadata["thermal_technique"] = technique
    return Series(
        x=series.x,
        y=series.y,
        label=series.label,
        key=series.key,
        x_axis=Axis(
            "temperature",
            unit=temperature_unit,
            label=series.x_axis.label or "Temperature",
            metadata=series.x_axis.metadata_dict(),
        ),
        y_axis=Axis(
            y_name,
            unit=series.y_axis.unit,
            label=series.y_axis.label or "Signal",
            metadata=y_metadata,
        ),
        metadata=series.metadata_dict(),
    )


def _canonicalize_thermal_series(series: Series, technique: ThermalTechnique) -> Series:
    if technique == "tga":
        return _canonicalize_tga_series(series)
    if technique == "dtg":
        return _canonicalize_dtg_series(series)
    if technique in {"tpr", "tpd"}:
        return _canonicalize_programmed_series(series, technique)
    raise ThermalError("technique must be 'tga', 'dtg', 'tpr', or 'tpd'")


@dataclass(frozen=True, slots=True)
class ThermalProcessingConfig:
    """Explicit processing recipe for one thermal-analysis curve."""

    temperature_min: float | None = None
    temperature_max: float | None = None
    tga_normalization: TGANormalization | None = None
    tga_reference: Literal["first_point"] | float = "first_point"
    vertical_offset: float = 0.0

    def __post_init__(self) -> None:
        minimum = (
            None if self.temperature_min is None else _finite_float(self.temperature_min, name="temperature_min")
        )
        maximum = (
            None if self.temperature_max is None else _finite_float(self.temperature_max, name="temperature_max")
        )
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ThermalError("temperature_min must be <= temperature_max")
        if self.tga_normalization not in {None, "fraction", "percent"}:
            raise ThermalError("tga_normalization must be None, 'fraction', or 'percent'")
        if isinstance(self.tga_reference, str):
            if self.tga_reference != "first_point":
                raise ThermalError("tga_reference string must be 'first_point'")
        elif isinstance(self.tga_reference, bool):
            raise TypeError("tga_reference must be 'first_point' or a real mass value")
        else:
            reference = _finite_float(self.tga_reference, name="tga_reference")
            if reference <= 0.0:
                raise ThermalError("explicit tga_reference must be greater than zero")
            object.__setattr__(self, "tga_reference", reference)
        vertical_offset = _finite_float(self.vertical_offset, name="vertical_offset")
        object.__setattr__(self, "temperature_min", minimum)
        object.__setattr__(self, "temperature_max", maximum)
        object.__setattr__(self, "vertical_offset", vertical_offset)


def process_thermal(
    series: Series,
    *,
    technique: ThermalTechnique,
    config: ThermalProcessingConfig | None = None,
) -> Series:
    """Apply only explicitly requested thermal processing operations."""
    resolved = ThermalProcessingConfig() if config is None else config
    if not isinstance(resolved, ThermalProcessingConfig):
        raise TypeError("config must be a ThermalProcessingConfig")

    result = _canonicalize_thermal_series(series, technique)
    if resolved.tga_normalization is not None:
        if technique != "tga":
            raise ThermalError("tga_normalization is only valid for technique='tga'")
        result = normalize_tga_mass(
            result,
            output=resolved.tga_normalization,
            reference=resolved.tga_reference,
        )
    if resolved.temperature_min is not None or resolved.temperature_max is not None:
        try:
            result = crop(
                result,
                x_min=resolved.temperature_min,
                x_max=resolved.temperature_max,
            )
        except ProcessingError as exc:
            raise ThermalError(str(exc)) from exc
    if resolved.vertical_offset != 0.0:
        try:
            result = offset(result, resolved.vertical_offset)
        except ProcessingError as exc:
            raise ThermalError(str(exc)) from exc
    return result


def _require_keyed_dataset(dataset: Dataset, *, operation: str) -> None:
    if not isinstance(dataset, Dataset):
        raise TypeError("dataset must be a Dataset")
    if any(not key for key in dataset.keys):
        raise ThermalError(f"{operation} requires non-empty Series.key values")


def process_thermal_dataset(
    dataset: Dataset,
    *,
    technique: ThermalTechnique,
    config: ThermalProcessingConfig | None = None,
    overrides: Mapping[str, ThermalProcessingConfig] | None = None,
) -> Dataset:
    """Process a homogeneous thermal Dataset using stable-key overrides."""
    _require_keyed_dataset(dataset, operation="process_thermal_dataset")
    default = ThermalProcessingConfig() if config is None else config
    if not isinstance(default, ThermalProcessingConfig):
        raise TypeError("config must be a ThermalProcessingConfig")
    override_map = {} if overrides is None else dict(overrides)
    unknown = set(override_map) - set(dataset.keys)
    if unknown:
        raise ThermalError(f"override keys not present in Dataset: {sorted(unknown)!r}")
    if not all(isinstance(value, ThermalProcessingConfig) for value in override_map.values()):
        raise TypeError("overrides values must be ThermalProcessingConfig instances")
    processed = tuple(
        process_thermal(
            item,
            technique=technique,
            config=override_map.get(item.key, default),
        )
        for item in dataset
    )
    return Dataset(series=processed, name=dataset.name, metadata=dataset.metadata_dict())


def _overlay_signature(series: Series, technique: ThermalTechnique) -> tuple[Any, ...]:
    canonical = _canonicalize_thermal_series(series, technique)
    return (
        technique,
        canonical.x_axis.unit,
        canonical.y_axis.name,
        canonical.y_axis.unit,
        canonical.y_axis.metadata.get("normalization"),
        canonical.y_axis.metadata.get("dtg_sign_mode"),
        canonical.y_axis.metadata.get("source_mass_semantic"),
    )


def validate_thermal_overlay(data: Series | Dataset, *, technique: ThermalTechnique) -> None:
    """Reject thermal overlays with incompatible technique/unit/normalization/sign state."""
    if isinstance(data, Series):
        _canonicalize_thermal_series(data, technique)
        return
    if not isinstance(data, Dataset):
        raise TypeError("data must be a Series or Dataset")
    if len(data) == 0:
        raise ThermalError("cannot use an empty thermal Dataset")
    signatures = [_overlay_signature(item, technique) for item in data]
    first = signatures[0]
    for index, signature in enumerate(signatures[1:], start=1):
        if signature != first:
            raise ThermalError(
                "thermal overlay requires matching technique/x unit/y semantic/unit/"
                "normalization/DTG sign state; "
                f"Series index {index} has {signature!r}, expected {first!r}"
            )


def stack_thermal_dataset(
    dataset: Dataset,
    *,
    technique: ThermalTechnique,
    step: float,
    start: float = 0.0,
) -> Dataset:
    """Apply explicit vertical offsets to a compatible thermal Dataset."""
    _require_keyed_dataset(dataset, operation="stack_thermal_dataset")
    validate_thermal_overlay(dataset, technique=technique)
    step_value = _finite_float(step, name="step")
    start_value = _finite_float(start, name="start")
    stacked = tuple(
        offset(
            _canonicalize_thermal_series(item, technique),
            start_value + index * step_value,
        )
        for index, item in enumerate(dataset)
    )
    metadata = dataset.metadata_dict()
    history = list(metadata.get("thermal_stack_history", []))
    history.append(
        {
            "technique": technique,
            "step": step_value,
            "start": start_value,
            "keys": dataset.keys,
        }
    )
    metadata["thermal_stack_history"] = history
    return Dataset(series=stacked, name=dataset.name, metadata=metadata)


@dataclass(frozen=True, slots=True)
class ThermalWindow:
    """Explicit temperature interval for one direct thermal measurement."""

    low: float
    high: float
    label: str = ""

    def __post_init__(self) -> None:
        low = _finite_float(self.low, name="low")
        high = _finite_float(self.high, name="high")
        if low >= high:
            raise ThermalError("ThermalWindow requires low < high")
        object.__setattr__(self, "low", low)
        object.__setattr__(self, "high", high)
        object.__setattr__(self, "label", str(self.label).strip())


@dataclass(frozen=True, slots=True)
class ThermalWindowMeasurement:
    """Traceable direct-window extremum and area measurement."""

    technique: ThermalTechnique
    window: ThermalWindow
    extremum_mode: ThermalExtremumMode
    extremum_temperature: float
    extremum_value: float
    area: float
    area_mode: ThermalAreaMode
    n_measured_points: int
    integration_n_points: int
    boundary_mode: str
    source_direction: ThermalDirection
    source_key: str
    source_label: str
    source_sha256: str
    window_sha256: str
    temperature_unit: str
    signal_unit: str | None


def _ascending_xy(series: Series) -> tuple[np.ndarray, np.ndarray, ThermalDirection]:
    x = np.asarray(series.x, dtype=np.float64)
    y = np.asarray(series.y, dtype=np.float64)
    direction = _monotonic_direction(x)
    if direction == "descending":
        return x[::-1], y[::-1], direction
    return x, y, direction


def _boundary_value(x: np.ndarray, y: np.ndarray, position: float) -> float:
    exact = np.flatnonzero(x == position)
    if exact.size:
        value = float(y[int(exact[0])])
        if not isfinite(value):
            raise ThermalError("thermal window boundary falls on missing y data")
        return value
    right = int(np.searchsorted(x, position, side="right"))
    left = right - 1
    if left < 0 or right >= x.size:
        raise ThermalError("thermal window boundary is outside the measured range")
    left_y, right_y = float(y[left]), float(y[right])
    if not isfinite(left_y) or not isfinite(right_y):
        raise ThermalError(
            "linear boundary interpolation requires finite bracketing y values"
        )
    fraction = (position - float(x[left])) / (float(x[right]) - float(x[left]))
    return left_y + fraction * (right_y - left_y)


def measure_thermal_window(
    series: Series,
    window: ThermalWindow,
    *,
    technique: ThermalTechnique,
    extremum_mode: ThermalExtremumMode = "maximum",
    area_mode: ThermalAreaMode = "net",
) -> ThermalWindowMeasurement:
    """Measure one explicit thermal window with linear boundary interpolation only."""
    source = _canonicalize_thermal_series(series, technique)
    if not isinstance(window, ThermalWindow):
        raise TypeError("window must be a ThermalWindow")
    if extremum_mode not in {"maximum", "minimum"}:
        raise ThermalError("extremum_mode must be 'maximum' or 'minimum'")
    if area_mode not in {"net", "absolute"}:
        raise ThermalError("area_mode must be 'net' or 'absolute'")

    x, y, source_direction = _ascending_xy(source)
    if window.low < x[0] or window.high > x[-1]:
        raise ThermalError("thermal window must be fully contained in the measured range")
    interior_mask = (x > window.low) & (x < window.high)
    interior_y = y[interior_mask]
    if np.isnan(interior_y).any():
        raise ThermalError("thermal window contains missing y values")

    low_y = _boundary_value(x, y, window.low)
    high_y = _boundary_value(x, y, window.high)
    integration_x = np.concatenate(
        (np.array([window.low]), x[interior_mask], np.array([window.high]))
    )
    integration_y = np.concatenate(
        (np.array([low_y]), interior_y, np.array([high_y]))
    )
    if not np.isfinite(integration_y).all():
        raise ThermalError("thermal integration values must be finite")

    if area_mode == "absolute":
        area = float(np.trapezoid(np.abs(integration_y), x=integration_x))
    else:
        area = float(np.trapezoid(integration_y, x=integration_x))

    index = (
        int(np.argmax(integration_y))
        if extremum_mode == "maximum"
        else int(np.argmin(integration_y))
    )
    window_digest = hashlib.sha256()
    window_digest.update(_array_digest(integration_x).encode("ascii"))
    window_digest.update(_array_digest(integration_y).encode("ascii"))
    measured_mask = (x >= window.low) & (x <= window.high)

    return ThermalWindowMeasurement(
        technique=technique,
        window=window,
        extremum_mode=extremum_mode,
        extremum_temperature=float(integration_x[index]),
        extremum_value=float(integration_y[index]),
        area=area,
        area_mode=area_mode,
        n_measured_points=int(np.count_nonzero(measured_mask)),
        integration_n_points=int(integration_x.size),
        boundary_mode="linear",
        source_direction=source_direction,
        source_key=source.key,
        source_label=source.label,
        source_sha256=_series_data_digest(source),
        window_sha256=window_digest.hexdigest(),
        temperature_unit=str(source.x_axis.unit),
        signal_unit=source.y_axis.unit,
    )


@dataclass(frozen=True, slots=True)
class ThermalAnnotation:
    """One publication annotation at an explicit temperature."""

    temperature: float
    text: str
    series_key: str | None = None
    text_offset_points: float = 6.0
    rotation: float = 90.0
    font_size: float | None = None
    color: str | None = None

    def __post_init__(self) -> None:
        temperature = _finite_float(self.temperature, name="temperature")
        text = str(self.text).strip()
        if not text:
            raise ThermalError("ThermalAnnotation.text must not be empty")
        key = None if self.series_key is None else str(self.series_key).strip()
        text_offset = _finite_float(self.text_offset_points, name="text_offset_points")
        rotation = _finite_float(self.rotation, name="rotation")
        font_size = None if self.font_size is None else _finite_float(self.font_size, name="font_size")
        if font_size is not None and font_size <= 0.0:
            raise ThermalError("font_size must be greater than zero")
        object.__setattr__(self, "temperature", temperature)
        object.__setattr__(self, "text", text)
        object.__setattr__(self, "series_key", key or None)
        object.__setattr__(self, "text_offset_points", text_offset)
        object.__setattr__(self, "rotation", rotation)
        object.__setattr__(self, "font_size", font_size)
