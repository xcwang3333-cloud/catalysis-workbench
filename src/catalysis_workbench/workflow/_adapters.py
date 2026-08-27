"""Private adapters from reviewed workflow contracts to scientific processing APIs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

from catalysis_workbench.core import Series
from catalysis_workbench.processing import crop, normalize, offset

from .registry import get_operation_descriptor


def validate_parameters(
    operation_id: str,
    parameters: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate one reviewed serialized parameter set and expand explicit defaults."""
    descriptor = get_operation_descriptor(operation_id)
    provided = dict(parameters)
    allowed = set(descriptor.parameter_names)
    unknown = sorted(set(provided) - allowed)
    missing = sorted(set(descriptor.required_parameters) - provided.keys())
    if missing or unknown:
        raise ValueError(
            f"invalid parameters for {operation_id!r}; missing={missing!r}, unknown={unknown!r}"
        )

    effective = dict(descriptor.parameter_defaults)
    effective.update(provided)

    if operation_id == "catalysis.processing.crop.v1":
        _validate_crop_parameters(effective)
    elif operation_id == "catalysis.processing.offset.v1":
        _validate_offset_parameters(effective)
    elif operation_id == "catalysis.processing.normalize.v1":
        _validate_normalize_parameters(effective)
    else:
        raise KeyError(f"no reviewed adapter for operation_id: {operation_id!r}")
    return effective


def execute_operation(
    operation_id: str,
    inputs: Mapping[str, object],
    parameters: Mapping[str, Any],
) -> dict[str, Series]:
    """Execute one already-preflighted reviewed operation."""
    series = inputs.get("series")
    if not isinstance(series, Series):
        raise TypeError(f"{operation_id!r} requires input port 'series' to be a Series")

    if operation_id == "catalysis.processing.crop.v1":
        result = crop(series, **dict(parameters))
    elif operation_id == "catalysis.processing.offset.v1":
        result = offset(series, parameters["value"])
    elif operation_id == "catalysis.processing.normalize.v1":
        result = normalize(series, **dict(parameters))
    else:
        raise KeyError(f"no reviewed adapter for operation_id: {operation_id!r}")

    if not isinstance(result, Series):
        raise TypeError(f"{operation_id!r} returned a non-Series result")
    return {"series": result}


def _numeric_scalar(value: object, *, label: str) -> None:
    try:
        array = np.asarray(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite JSON numeric scalar") from exc
    if array.ndim != 0 or array.dtype.kind not in "biuf":
        raise ValueError(f"{label} must be a finite JSON numeric scalar")
    scalar = array.item()
    if not np.isfinite(scalar):
        raise ValueError(f"{label} must be a finite JSON numeric scalar")


def _real_number_or_none(value: object, *, label: str) -> None:
    if value is None:
        return
    if type(value) not in (int, float):
        raise ValueError(f"{label} must be null or a real JSON number")
    _numeric_scalar(value, label=label)


def _validate_crop_parameters(parameters: Mapping[str, Any]) -> None:
    _real_number_or_none(parameters["x_min"], label="crop x_min")
    _real_number_or_none(parameters["x_max"], label="crop x_max")
    if parameters["x_min"] is None and parameters["x_max"] is None:
        raise ValueError("crop requires x_min, x_max, or both")
    if (
        parameters["x_min"] is not None
        and parameters["x_max"] is not None
        and parameters["x_min"] > parameters["x_max"]
    ):
        raise ValueError("crop x_min must be less than or equal to x_max")
    if type(parameters["inclusive"]) is not bool:
        raise ValueError("crop inclusive must be a JSON boolean")


def _validate_offset_parameters(parameters: Mapping[str, Any]) -> None:
    value = parameters["value"]
    if type(value) not in (int, float):
        raise ValueError("offset value must be a real JSON number")
    _numeric_scalar(value, label="offset value")


def _validate_normalize_parameters(parameters: Mapping[str, Any]) -> None:
    if parameters["method"] not in {"max", "max_abs", "minmax", "area"}:
        raise ValueError("normalize method is not supported by the v1 workflow contract")
    target = parameters["target"]
    if type(target) not in (int, float):
        raise ValueError("normalize target must be a real JSON number")
    _numeric_scalar(target, label="normalize target")
    if parameters["area_mode"] not in {"absolute", "net"}:
        raise ValueError("normalize area_mode is not supported by the v1 workflow contract")
