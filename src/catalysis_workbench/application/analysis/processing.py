"""Deterministic task-specific scientific processing state for v1.1 analyses."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from math import isfinite
from types import MappingProxyType
from typing import Any, Literal

from catalysis_workbench._canonical_json import canonical_json_bytes
from catalysis_workbench.experimental.echem.quantities import canonical_current_density_unit

from .tasks import get_analysis_task_descriptor

RHEMode = Literal["none", "direct", "she_ph"]


class AnalysisProcessingError(ValueError):
    """Raised when persisted scientific processing state is invalid."""


def _text(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise AnalysisProcessingError(
            f"{label} must be a non-empty string without surrounding whitespace"
        )
    canonical_json_bytes(value)
    return value


def _optional_finite(value: object | None, *, label: str) -> float | None:
    if value is None:
        return None
    if type(value) not in (int, float) or not isfinite(float(value)):
        raise AnalysisProcessingError(f"{label} must be null or a finite real number")
    return float(value)


def _required_finite(value: object, *, label: str) -> float:
    checked = _optional_finite(value, label=label)
    if checked is None:
        raise AnalysisProcessingError(f"{label} must be a finite real number")
    return checked


@dataclass(frozen=True, slots=True)
class AnalysisRange:
    """Scientific x-range applied to computed results, not a figure display range."""

    x_min: float | None = None
    x_max: float | None = None

    def __post_init__(self) -> None:
        lower = _optional_finite(self.x_min, label="analysis_range.x_min")
        upper = _optional_finite(self.x_max, label="analysis_range.x_max")
        if lower is not None and upper is not None and lower > upper:
            raise AnalysisProcessingError(
                "analysis_range.x_min must be less than or equal to x_max"
            )
        object.__setattr__(self, "x_min", lower)
        object.__setattr__(self, "x_max", upper)

    @property
    def enabled(self) -> bool:
        return self.x_min is not None or self.x_max is not None


@dataclass(frozen=True, slots=True)
class LSVProcessingSpec:
    """Serializable LSV/current-processing parameters before scientific cropping."""

    rhe_mode: RHEMode = "none"
    rhe_offset_v: float | None = None
    reference_potential_vs_she_v: float | None = None
    ph: float | None = None
    temperature_k: float = 298.15
    resistance_ohm: float | None = None
    ir_correction_fraction: float = 1.0
    electrode_area_cm2: float | None = None
    normalize_to_current_density: bool = False
    current_density_unit: str = "mA/cm^2"

    def __post_init__(self) -> None:
        if self.rhe_mode not in {"none", "direct", "she_ph"}:
            raise AnalysisProcessingError("rhe_mode must be 'none', 'direct', or 'she_ph'")
        offset = _optional_finite(self.rhe_offset_v, label="rhe_offset_v")
        reference = _optional_finite(
            self.reference_potential_vs_she_v,
            label="reference_potential_vs_she_v",
        )
        ph = _optional_finite(self.ph, label="ph")
        temperature = _required_finite(self.temperature_k, label="temperature_k")
        if temperature <= 0:
            raise AnalysisProcessingError("temperature_k must be greater than zero")
        if self.rhe_mode == "none" and any(
            value is not None for value in (offset, reference, ph)
        ):
            raise AnalysisProcessingError(
                "rhe_mode='none' cannot persist RHE-conversion parameters"
            )
        if self.rhe_mode == "direct":
            if offset is None:
                raise AnalysisProcessingError("direct RHE conversion requires rhe_offset_v")
            if reference is not None or ph is not None:
                raise AnalysisProcessingError(
                    "direct RHE conversion cannot also define SHE-reference or pH parameters"
                )
        if self.rhe_mode == "she_ph":
            if reference is None or ph is None:
                raise AnalysisProcessingError(
                    "SHE+pH RHE conversion requires reference_potential_vs_she_v and ph"
                )
            if offset is not None:
                raise AnalysisProcessingError(
                    "SHE+pH RHE conversion derives its offset and cannot persist rhe_offset_v"
                )

        resistance = _optional_finite(self.resistance_ohm, label="resistance_ohm")
        if resistance is not None and resistance < 0:
            raise AnalysisProcessingError("resistance_ohm must be non-negative")
        fraction = _required_finite(
            self.ir_correction_fraction,
            label="ir_correction_fraction",
        )
        if not 0 <= fraction <= 1:
            raise AnalysisProcessingError(
                "ir_correction_fraction must be between 0 and 1"
            )
        area = _optional_finite(self.electrode_area_cm2, label="electrode_area_cm2")
        if area is not None and area <= 0:
            raise AnalysisProcessingError("electrode_area_cm2 must be greater than zero")
        if type(self.normalize_to_current_density) is not bool:
            raise AnalysisProcessingError("normalize_to_current_density must be a boolean")
        if self.normalize_to_current_density and area is None:
            raise AnalysisProcessingError(
                "electrode_area_cm2 is required for current-density normalization"
            )
        try:
            unit = canonical_current_density_unit(self.current_density_unit)
        except (TypeError, ValueError) as exc:
            raise AnalysisProcessingError(
                "current_density_unit must be A/cm^2, mA/cm^2, or uA/cm^2"
            ) from exc

        object.__setattr__(self, "rhe_offset_v", offset)
        object.__setattr__(self, "reference_potential_vs_she_v", reference)
        object.__setattr__(self, "ph", ph)
        object.__setattr__(self, "temperature_k", temperature)
        object.__setattr__(self, "resistance_ohm", resistance)
        object.__setattr__(self, "ir_correction_fraction", fraction)
        object.__setattr__(self, "electrode_area_cm2", area)
        object.__setattr__(self, "current_density_unit", unit)


@dataclass(frozen=True, slots=True)
class PartialCurrentPair:
    """Explicit pairing between one total-current input and one FE input."""

    current_data_id: str
    fe_data_id: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "current_data_id",
            _text(self.current_data_id, label="current_data_id"),
        )
        object.__setattr__(self, "fe_data_id", _text(self.fe_data_id, label="fe_data_id"))
        if self.current_data_id == self.fe_data_id:
            raise AnalysisProcessingError("partial-current pair requires two distinct inputs")


@dataclass(frozen=True, slots=True)
class LSVAnalysisSpec:
    """Common LSV settings, full per-series overrides, and scientific range."""

    common: LSVProcessingSpec = field(default_factory=LSVProcessingSpec)
    overrides: Mapping[str, LSVProcessingSpec] = field(default_factory=dict)
    analysis_range: AnalysisRange = field(default_factory=AnalysisRange)

    def __post_init__(self) -> None:
        if not isinstance(self.common, LSVProcessingSpec):
            raise TypeError("common must be an LSVProcessingSpec")
        if not isinstance(self.analysis_range, AnalysisRange):
            raise TypeError("analysis_range must be an AnalysisRange")
        object.__setattr__(self, "overrides", _freeze_overrides(self.overrides))


@dataclass(frozen=True, slots=True)
class FEPartialCurrentAnalysisSpec:
    """Current processing, explicit FE/current pairs, and scientific range."""

    current_common: LSVProcessingSpec = field(default_factory=LSVProcessingSpec)
    current_overrides: Mapping[str, LSVProcessingSpec] = field(default_factory=dict)
    pairs: tuple[PartialCurrentPair, ...] = ()
    analysis_range: AnalysisRange = field(default_factory=AnalysisRange)

    def __post_init__(self) -> None:
        if not isinstance(self.current_common, LSVProcessingSpec):
            raise TypeError("current_common must be an LSVProcessingSpec")
        if not isinstance(self.analysis_range, AnalysisRange):
            raise TypeError("analysis_range must be an AnalysisRange")
        object.__setattr__(
            self,
            "current_overrides",
            _freeze_overrides(self.current_overrides),
        )
        pairs = tuple(self.pairs)
        if not all(isinstance(item, PartialCurrentPair) for item in pairs):
            raise TypeError("pairs must contain PartialCurrentPair instances")
        identities = tuple((item.current_data_id, item.fe_data_id) for item in pairs)
        if len(identities) != len(set(identities)):
            raise AnalysisProcessingError("partial-current pairs must be unique")
        object.__setattr__(self, "pairs", pairs)


@dataclass(frozen=True, slots=True)
class GenericXYAnalysisSpec:
    """Generic XY processing is intentionally limited to scientific cropping in Block 3."""

    analysis_range: AnalysisRange = field(default_factory=AnalysisRange)

    def __post_init__(self) -> None:
        if not isinstance(self.analysis_range, AnalysisRange):
            raise TypeError("analysis_range must be an AnalysisRange")


AnalysisSpec = LSVAnalysisSpec | FEPartialCurrentAnalysisSpec | GenericXYAnalysisSpec


@dataclass(frozen=True, slots=True)
class AnalysisDependencyImpact:
    """Processing references that will be rewritten or removed with one data input."""

    override_count: int = 0
    partial_current_pair_count: int = 0


def _freeze_overrides(value: Mapping[str, LSVProcessingSpec]) -> Mapping[str, LSVProcessingSpec]:
    if not isinstance(value, Mapping):
        raise TypeError("processing overrides must be a mapping")
    detached: dict[str, LSVProcessingSpec] = {}
    for key in sorted(value):
        checked_key = _text(key, label="processing override data_id")
        item = value[key]
        if not isinstance(item, LSVProcessingSpec):
            raise TypeError("processing override values must be LSVProcessingSpec instances")
        detached[checked_key] = item
    return MappingProxyType(detached)


def default_analysis_spec(task_id: str) -> AnalysisSpec:
    task = get_analysis_task_descriptor(task_id)
    if task.task_id == "lsv":
        return LSVAnalysisSpec()
    if task.task_id == "fe_partial_current":
        return FEPartialCurrentAnalysisSpec()
    if task.task_id == "generic_xy":
        return GenericXYAnalysisSpec()
    raise AnalysisProcessingError(f"unsupported analysis task_id: {task.task_id!r}")


def validate_analysis_spec(task_id: str, analysis: object) -> AnalysisSpec:
    task = get_analysis_task_descriptor(task_id)
    expected: type[object]
    if task.task_id == "lsv":
        expected = LSVAnalysisSpec
    elif task.task_id == "fe_partial_current":
        expected = FEPartialCurrentAnalysisSpec
    else:
        expected = GenericXYAnalysisSpec
    if not isinstance(analysis, expected):
        raise AnalysisProcessingError(
            f"analysis state for task {task.task_id!r} must be {expected.__name__}"
        )
    return analysis


def _range_to_dict(value: AnalysisRange) -> dict[str, Any]:
    return {"x_min": value.x_min, "x_max": value.x_max}


def _lsv_processing_to_dict(value: LSVProcessingSpec) -> dict[str, Any]:
    return {
        "rhe_mode": value.rhe_mode,
        "rhe_offset_v": value.rhe_offset_v,
        "reference_potential_vs_she_v": value.reference_potential_vs_she_v,
        "ph": value.ph,
        "temperature_k": value.temperature_k,
        "resistance_ohm": value.resistance_ohm,
        "ir_correction_fraction": value.ir_correction_fraction,
        "electrode_area_cm2": value.electrode_area_cm2,
        "normalize_to_current_density": value.normalize_to_current_density,
        "current_density_unit": value.current_density_unit,
    }


def analysis_spec_to_plain_dict(task_id: str, analysis: AnalysisSpec) -> dict[str, Any]:
    checked = validate_analysis_spec(task_id, analysis)
    if isinstance(checked, LSVAnalysisSpec):
        return {
            "common": _lsv_processing_to_dict(checked.common),
            "overrides": {
                key: _lsv_processing_to_dict(value)
                for key, value in checked.overrides.items()
            },
            "analysis_range": _range_to_dict(checked.analysis_range),
        }
    if isinstance(checked, FEPartialCurrentAnalysisSpec):
        return {
            "current_common": _lsv_processing_to_dict(checked.current_common),
            "current_overrides": {
                key: _lsv_processing_to_dict(value)
                for key, value in checked.current_overrides.items()
            },
            "pairs": [
                {
                    "current_data_id": pair.current_data_id,
                    "fe_data_id": pair.fe_data_id,
                }
                for pair in checked.pairs
            ],
            "analysis_range": _range_to_dict(checked.analysis_range),
        }
    return {"analysis_range": _range_to_dict(checked.analysis_range)}


def _exact_object(value: object, fields: frozenset[str], *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(type(key) is str for key in value):
        raise AnalysisProcessingError(f"serialized {label} must be an object")
    missing = sorted(fields - set(value))
    unknown = sorted(set(value) - fields)
    if missing or unknown:
        raise AnalysisProcessingError(
            f"invalid {label} fields; missing={missing!r}, unknown={unknown!r}"
        )
    return value


_RANGE_FIELDS = frozenset({"x_min", "x_max"})
_LSV_FIELDS = frozenset(
    {
        "rhe_mode",
        "rhe_offset_v",
        "reference_potential_vs_she_v",
        "ph",
        "temperature_k",
        "resistance_ohm",
        "ir_correction_fraction",
        "electrode_area_cm2",
        "normalize_to_current_density",
        "current_density_unit",
    }
)
_LSV_ANALYSIS_FIELDS = frozenset({"common", "overrides", "analysis_range"})
_FE_ANALYSIS_FIELDS = frozenset(
    {"current_common", "current_overrides", "pairs", "analysis_range"}
)
_PAIR_FIELDS = frozenset({"current_data_id", "fe_data_id"})
_GENERIC_FIELDS = frozenset({"analysis_range"})


def _range_from_dict(value: object) -> AnalysisRange:
    item = _exact_object(value, _RANGE_FIELDS, label="analysis range")
    return AnalysisRange(x_min=item["x_min"], x_max=item["x_max"])


def _lsv_processing_from_dict(value: object) -> LSVProcessingSpec:
    item = _exact_object(value, _LSV_FIELDS, label="LSV processing")
    return LSVProcessingSpec(**item)


def _overrides_from_dict(value: object) -> dict[str, LSVProcessingSpec]:
    if not isinstance(value, dict) or not all(type(key) is str for key in value):
        raise AnalysisProcessingError("serialized processing overrides must be an object")
    return {key: _lsv_processing_from_dict(item) for key, item in value.items()}


def analysis_spec_from_dict(task_id: str, value: object) -> AnalysisSpec:
    task = get_analysis_task_descriptor(task_id)
    if task.task_id == "lsv":
        item = _exact_object(value, _LSV_ANALYSIS_FIELDS, label="LSV analysis")
        return LSVAnalysisSpec(
            common=_lsv_processing_from_dict(item["common"]),
            overrides=_overrides_from_dict(item["overrides"]),
            analysis_range=_range_from_dict(item["analysis_range"]),
        )
    if task.task_id == "fe_partial_current":
        item = _exact_object(value, _FE_ANALYSIS_FIELDS, label="FE/partial-current analysis")
        raw_pairs = item["pairs"]
        if not isinstance(raw_pairs, list):
            raise AnalysisProcessingError("serialized partial-current pairs must be an array")
        pairs = []
        for raw in raw_pairs:
            pair = _exact_object(raw, _PAIR_FIELDS, label="partial-current pair")
            pairs.append(PartialCurrentPair(**pair))
        return FEPartialCurrentAnalysisSpec(
            current_common=_lsv_processing_from_dict(item["current_common"]),
            current_overrides=_overrides_from_dict(item["current_overrides"]),
            pairs=tuple(pairs),
            analysis_range=_range_from_dict(item["analysis_range"]),
        )
    item = _exact_object(value, _GENERIC_FIELDS, label="generic XY analysis")
    return GenericXYAnalysisSpec(analysis_range=_range_from_dict(item["analysis_range"]))


def dependency_impact(analysis: AnalysisSpec, data_id: str) -> AnalysisDependencyImpact:
    checked_id = _text(data_id, label="data_id")
    if isinstance(analysis, LSVAnalysisSpec):
        return AnalysisDependencyImpact(override_count=int(checked_id in analysis.overrides))
    if isinstance(analysis, FEPartialCurrentAnalysisSpec):
        return AnalysisDependencyImpact(
            override_count=int(checked_id in analysis.current_overrides),
            partial_current_pair_count=sum(
                checked_id in {pair.current_data_id, pair.fe_data_id}
                for pair in analysis.pairs
            ),
        )
    return AnalysisDependencyImpact()


def remap_analysis_data_id(analysis: AnalysisSpec, old_id: str, new_id: str) -> AnalysisSpec:
    old_key = _text(old_id, label="old_data_id")
    new_key = _text(new_id, label="new_data_id")
    if old_key == new_key:
        return analysis
    if isinstance(analysis, LSVAnalysisSpec):
        overrides = dict(analysis.overrides)
        if old_key in overrides:
            if new_key in overrides:
                raise AnalysisProcessingError(
                    "cannot remap processing override onto an existing override"
                )
            overrides[new_key] = overrides.pop(old_key)
        return LSVAnalysisSpec(
            common=analysis.common,
            overrides=overrides,
            analysis_range=analysis.analysis_range,
        )
    if isinstance(analysis, FEPartialCurrentAnalysisSpec):
        overrides = dict(analysis.current_overrides)
        if old_key in overrides:
            if new_key in overrides:
                raise AnalysisProcessingError(
                    "cannot remap current override onto an existing override"
                )
            overrides[new_key] = overrides.pop(old_key)
        pairs = tuple(
            PartialCurrentPair(
                current_data_id=(
                    new_key if pair.current_data_id == old_key else pair.current_data_id
                ),
                fe_data_id=(
                    new_key if pair.fe_data_id == old_key else pair.fe_data_id
                ),
            )
            for pair in analysis.pairs
        )
        return FEPartialCurrentAnalysisSpec(
            current_common=analysis.current_common,
            current_overrides=overrides,
            pairs=pairs,
            analysis_range=analysis.analysis_range,
        )
    return analysis


def remove_analysis_data_id(analysis: AnalysisSpec, data_id: str) -> AnalysisSpec:
    checked_id = _text(data_id, label="data_id")
    if isinstance(analysis, LSVAnalysisSpec):
        overrides = dict(analysis.overrides)
        overrides.pop(checked_id, None)
        return LSVAnalysisSpec(
            common=analysis.common,
            overrides=overrides,
            analysis_range=analysis.analysis_range,
        )
    if isinstance(analysis, FEPartialCurrentAnalysisSpec):
        overrides = dict(analysis.current_overrides)
        overrides.pop(checked_id, None)
        pairs = tuple(
            pair
            for pair in analysis.pairs
            if checked_id not in {pair.current_data_id, pair.fe_data_id}
        )
        return FEPartialCurrentAnalysisSpec(
            current_common=analysis.current_common,
            current_overrides=overrides,
            pairs=pairs,
            analysis_range=analysis.analysis_range,
        )
    return analysis


__all__ = [
    "AnalysisDependencyImpact",
    "AnalysisProcessingError",
    "AnalysisRange",
    "AnalysisSpec",
    "FEPartialCurrentAnalysisSpec",
    "GenericXYAnalysisSpec",
    "LSVAnalysisSpec",
    "LSVProcessingSpec",
    "PartialCurrentPair",
    "analysis_spec_from_dict",
    "analysis_spec_to_plain_dict",
    "default_analysis_spec",
    "dependency_impact",
    "remap_analysis_data_id",
    "remove_analysis_data_id",
    "validate_analysis_spec",
]
