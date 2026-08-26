"""Operando XRD adapters and explicit trajectories for v0.8 Block 6."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import log, sqrt
from typing import Any

import numpy as np

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.characterization import XRDError, validate_xrd_series
from catalysis_workbench.experimental.characterization.xrd import _canonicalize_xrd_series
from catalysis_workbench.processing import PeakFitResult
from catalysis_workbench.processing.peak_fitting import _series_data_digest

from .operations import OperandoTrace, build_operando_trace
from .stack import (
    FrameCoordinate,
    OperandoStack,
    OperandoStackError,
    build_operando_stack,
    series_array_digest,
)

_DOMAIN_METADATA_KEY = "catalysis_workbench.operando_domain"
_SUPPORTED_FWHM_MODELS = frozenset(
    {"gaussian", "lorentzian", "voigt", "pseudo_voigt"}
)


class OperandoXRDError(OperandoStackError):
    """Raised when an operando XRD request violates the frozen v0.8 contract."""


def _normalization_basis(series: Series) -> dict[str, Any]:
    metadata = series.y_axis.metadata
    return {
        "value_semantic": series.y_axis.name,
        "value_unit": series.y_axis.unit,
        "normalization": metadata.get("normalization"),
        "normalization_method": metadata.get("normalization_method"),
        "normalization_target": metadata.get("normalization_target"),
        "normalization_area_mode": metadata.get("normalization_area_mode"),
    }


def _domain_metadata(
    metadata: Mapping[str, Any] | None,
    *,
    fit_source_sha256: Sequence[str],
    normalization_basis: Mapping[str, Any],
) -> dict[str, Any]:
    output = {} if metadata is None else dict(metadata)
    if _DOMAIN_METADATA_KEY in output:
        raise OperandoXRDError(
            f"caller metadata must not override reserved {_DOMAIN_METADATA_KEY!r}"
        )
    output[_DOMAIN_METADATA_KEY] = {
        "technique": "xrd",
        "adapter": "build_xrd_operando_stack",
        "fit_source_sha256": tuple(fit_source_sha256),
        "normalization_basis": dict(normalization_basis),
    }
    return output


def build_xrd_operando_stack(
    frames: Sequence[Series],
    *,
    frame_coordinates: Sequence[FrameCoordinate],
    primary_coordinate_key: str,
    metadata: Mapping[str, Any] | None = None,
) -> OperandoStack:
    """Build one exact-grid stack from already validated/prepared XRD frames."""
    retained = tuple(frames)
    if not retained or not all(isinstance(frame, Series) for frame in retained):
        raise OperandoXRDError("frames must contain at least one Series")

    canonical: list[Series] = []
    source_digests: list[str] = []
    fit_source_sha256: list[str] = []
    basis: dict[str, Any] | None = None
    for index, frame in enumerate(retained):
        try:
            validate_xrd_series(frame)
            normalized = _canonicalize_xrd_series(frame)
            source_digest = series_array_digest(frame)
        except (XRDError, OperandoStackError, TypeError) as exc:
            raise OperandoXRDError(
                f"XRD frame {index} is not valid retained domain state: {exc}"
            ) from exc

        if source_digest != series_array_digest(normalized):
            raise RuntimeError(
                "XRD semantic canonicalization unexpectedly changed source arrays"
            )
        current_basis = _normalization_basis(normalized)
        if basis is None:
            basis = current_basis
        elif current_basis != basis:
            raise OperandoXRDError(
                "all XRD frames require one compatible intensity/normalization basis"
            )

        canonical.append(normalized)
        source_digests.append(source_digest)
        fit_source_sha256.append(_series_data_digest(normalized))

    assert basis is not None
    try:
        return build_operando_stack(
            canonical,
            frame_coordinates=frame_coordinates,
            primary_coordinate_key=primary_coordinate_key,
            expected_source_digests=source_digests,
            metadata=_domain_metadata(
                metadata,
                fit_source_sha256=fit_source_sha256,
                normalization_basis=basis,
            ),
        )
    except OperandoStackError as exc:
        raise OperandoXRDError(str(exc)) from exc


def _domain_record(stack: OperandoStack) -> Mapping[str, Any]:
    if not isinstance(stack, OperandoStack):
        raise TypeError("stack must be an OperandoStack")
    record = stack.metadata.get(_DOMAIN_METADATA_KEY)
    if not isinstance(record, Mapping) or record.get("technique") != "xrd":
        raise OperandoXRDError(
            "stack must be produced by the reviewed XRD operando adapter"
        )
    return record


def _finite_window(
    two_theta_min_deg: float,
    two_theta_max_deg: float,
) -> tuple[float, float]:
    try:
        lower = float(two_theta_min_deg)
        upper = float(two_theta_max_deg)
    except (TypeError, ValueError) as exc:
        raise TypeError("XRD window bounds must be real numeric scalars") from exc
    if not np.isfinite(lower) or not np.isfinite(upper):
        raise OperandoXRDError("XRD window bounds must be finite")
    if not lower < upper:
        raise OperandoXRDError("XRD window requires two_theta_min_deg < two_theta_max_deg")
    return lower, upper


def _window_indices(
    stack: OperandoStack,
    *,
    two_theta_min_deg: float,
    two_theta_max_deg: float,
    min_points: int,
) -> tuple[np.ndarray, float, float]:
    _domain_record(stack)
    lower, upper = _finite_window(two_theta_min_deg, two_theta_max_deg)
    indices = np.flatnonzero((stack.signal >= lower) & (stack.signal <= upper))
    if indices.size < min_points:
        raise OperandoXRDError(
            f"XRD window [{lower}, {upper}] deg retains fewer than "
            f"{min_points} measured points"
        )
    return indices, lower, upper


def _integral_unit(value_unit: str | None, signal_unit: str | None) -> str | None:
    value = None if value_unit is None else str(value_unit).strip()
    signal = None if signal_unit is None else str(signal_unit).strip()
    if value in {None, "", "1", "dimensionless"}:
        return signal
    if signal in {None, "", "1", "dimensionless"}:
        return value
    return f"{value}*{signal}"


def xrd_window_integral_trace(
    stack: OperandoStack,
    *,
    two_theta_min_deg: float,
    two_theta_max_deg: float,
    coordinate_key: str,
) -> OperandoTrace:
    """Integrate only retained measured XRD points inside one explicit window."""
    indices, lower, upper = _window_indices(
        stack,
        two_theta_min_deg=two_theta_min_deg,
        two_theta_max_deg=two_theta_max_deg,
        min_points=2,
    )
    x = stack.signal[indices]
    values = tuple(
        float(np.trapezoid(stack.values[index, indices], x=x))
        for index in range(stack.n_frames)
    )
    return build_operando_trace(
        stack,
        coordinate_key=coordinate_key,
        values=values,
        value_axis=Axis(
            "xrd_window_integral",
            unit=_integral_unit(stack.value_axis.unit, stack.signal_axis.unit),
            label="XRD window intensity integral",
            metadata={"technique": "xrd", "integration": "trapezoid"},
        ),
        method="xrd_window_integral",
        parameters={
            "two_theta_min_deg": lower,
            "two_theta_max_deg": upper,
            "boundary_rule": "inclusive_measured_points_only",
            "integration_rule": "numpy.trapezoid",
            "interpolation": False,
        },
        metadata={"technique": "xrd", "measurement_kind": "window_integral"},
    )


def xrd_observed_peak_position_trace(
    stack: OperandoStack,
    *,
    two_theta_min_deg: float,
    two_theta_max_deg: float,
    coordinate_key: str,
) -> OperandoTrace:
    """Return the unique observed measured-point maximum position per frame."""
    indices, lower, upper = _window_indices(
        stack,
        two_theta_min_deg=two_theta_min_deg,
        two_theta_max_deg=two_theta_max_deg,
        min_points=1,
    )
    values: list[float] = []
    for frame_index in range(stack.n_frames):
        selected = stack.values[frame_index, indices]
        maximum = float(np.max(selected))
        candidates = np.flatnonzero(selected == maximum)
        if candidates.size != 1:
            raise OperandoXRDError(
                f"frame {stack.frame_keys[frame_index]!r} has an ambiguous equal-maximum "
                "XRD peak in the caller window"
            )
        values.append(float(stack.signal[indices[int(candidates[0])]]))

    return build_operando_trace(
        stack,
        coordinate_key=coordinate_key,
        values=values,
        value_axis=Axis(
            "xrd_observed_peak_position",
            unit=stack.signal_axis.unit,
            label="Observed XRD peak position",
            metadata={"technique": "xrd", "measurement": "observed_window_maximum"},
        ),
        method="xrd_observed_peak_position",
        parameters={
            "two_theta_min_deg": lower,
            "two_theta_max_deg": upper,
            "boundary_rule": "inclusive_measured_points_only",
            "tie_rule": "fail_closed",
            "interpolation": False,
        },
        metadata={"technique": "xrd", "measurement_kind": "peak_position"},
    )


def _fit_probe(result: PeakFitResult) -> Series:
    return Series(
        result.x,
        result.observed_y,
        key=result.source_key,
        x_axis=Axis(result.x_axis_name, unit=result.x_unit),
        y_axis=Axis(result.y_axis_name, unit=result.y_unit),
    )


def _component_model(result: PeakFitResult, component_key: str) -> str:
    for component in result.spec.components:
        if component.key == component_key:
            return str(component.model)
    raise OperandoXRDError(
        f"fit result does not contain component {component_key!r}"
    )


def _validated_fit_results(
    stack: OperandoStack,
    fit_results: Sequence[PeakFitResult],
    *,
    component_key: str,
) -> tuple[tuple[PeakFitResult, ...], str, float, float, str]:
    record = _domain_record(stack)
    key = str(component_key).strip()
    if not key:
        raise OperandoXRDError("component_key must not be blank")
    retained = tuple(fit_results)
    if len(retained) != stack.n_frames or not all(
        isinstance(result, PeakFitResult) for result in retained
    ):
        raise OperandoXRDError(
            "fit_results must contain exactly one PeakFitResult per retained XRD frame"
        )

    expected_fit_sha = tuple(record.get("fit_source_sha256", ()))
    if len(expected_fit_sha) != stack.n_frames:
        raise OperandoXRDError("XRD stack is missing reconstructible fit-source provenance")

    model: str | None = None
    x_min: float | None = None
    x_max: float | None = None
    method: str | None = None
    for index, result in enumerate(retained):
        if not result.success:
            raise OperandoXRDError(
                f"fit result for frame {stack.frame_keys[index]!r} was not successful"
            )
        if result.source_key != stack.source_keys[index]:
            raise OperandoXRDError(
                "fit result source keys/order must exactly match retained XRD source order"
            )
        if result.source_sha256 != expected_fit_sha[index]:
            raise OperandoXRDError(
                f"fit result for frame {stack.frame_keys[index]!r} does not match source arrays"
            )

        try:
            canonical_probe = _canonicalize_xrd_series(_fit_probe(result))
        except (XRDError, TypeError) as exc:
            raise OperandoXRDError(
                f"fit result axis state is not compatible with XRD: {exc}"
            ) from exc
        if (
            canonical_probe.x_axis.name != stack.signal_axis.name
            or canonical_probe.x_axis.unit != stack.signal_axis.unit
            or canonical_probe.y_axis.name != stack.value_axis.name
            or canonical_probe.y_axis.unit != stack.value_axis.unit
        ):
            raise OperandoXRDError(
                "fit result axis/value basis is incompatible with the retained XRD stack"
            )

        current_model = _component_model(result, key)
        current_x_min = float(result.spec.x_min)
        current_x_max = float(result.spec.x_max)
        current_method = str(result.spec.method)
        if model is None:
            model, x_min, x_max, method = (
                current_model,
                current_x_min,
                current_x_max,
                current_method,
            )
        elif (
            current_model != model
            or current_x_min != x_min
            or current_x_max != x_max
            or current_method != method
        ):
            raise OperandoXRDError(
                "fit component model, fit window, and fit method must be identical "
                "across XRD frames"
            )

    assert model is not None and x_min is not None and x_max is not None and method is not None
    return retained, model, x_min, x_max, method


def _fitted_parameter(result: PeakFitResult, component_key: str, name: str) -> float:
    key = f"{component_key}.{name}"
    parameter = result.parameters.get(key)
    if parameter is None:
        raise OperandoXRDError(f"fit result is missing retained parameter {key!r}")
    value = float(parameter.value)
    if not np.isfinite(value):
        raise OperandoXRDError(f"fit parameter {key!r} must be finite")
    return value


def xrd_fit_component_center_trace(
    stack: OperandoStack,
    fit_results: Sequence[PeakFitResult],
    *,
    coordinate_key: str,
    component_key: str,
) -> OperandoTrace:
    """Consume caller-supplied XRD fitted component centers without refitting."""
    retained, model, x_min, x_max, fit_method = _validated_fit_results(
        stack,
        fit_results,
        component_key=component_key,
    )
    values = tuple(
        _fitted_parameter(result, component_key, "center") for result in retained
    )
    return build_operando_trace(
        stack,
        coordinate_key=coordinate_key,
        values=values,
        value_axis=Axis(
            "xrd_fit_center",
            unit=stack.signal_axis.unit,
            label="Fitted XRD peak center",
            metadata={"technique": "xrd", "component_key": component_key},
        ),
        method="xrd_fit_component_center",
        parameters={
            "component_key": component_key,
            "model": model,
            "fit_x_min": x_min,
            "fit_x_max": x_max,
            "fit_method": fit_method,
            "source_state": "PeakFitResult",
        },
        metadata={"technique": "xrd", "fit_derived": True},
    )


def _model_fwhm(result: PeakFitResult, component_key: str, model: str) -> float:
    if model not in _SUPPORTED_FWHM_MODELS:
        raise OperandoXRDError(
            f"model {model!r} has no supported reviewed XRD FWHM consumer; "
            "Doniach FWHM is intentionally fail-closed"
        )
    sigma = _fitted_parameter(result, component_key, "sigma")
    if sigma < 0.0:
        raise OperandoXRDError("fit sigma must be non-negative for XRD FWHM")
    if model == "gaussian":
        return 2.0 * sqrt(2.0 * log(2.0)) * sigma
    if model in {"lorentzian", "pseudo_voigt"}:
        return 2.0 * sigma
    gamma = _fitted_parameter(result, component_key, "gamma")
    if gamma < 0.0:
        raise OperandoXRDError("fit gamma must be non-negative for Voigt XRD FWHM")
    return 1.0692 * gamma + sqrt(0.8664 * gamma * gamma + 5.545083 * sigma * sigma)


def xrd_fit_component_fwhm_trace(
    stack: OperandoStack,
    fit_results: Sequence[PeakFitResult],
    *,
    coordinate_key: str,
    component_key: str,
) -> OperandoTrace:
    """Consume caller-supplied fit widths using reviewed lmfit model conventions."""
    retained, model, x_min, x_max, fit_method = _validated_fit_results(
        stack,
        fit_results,
        component_key=component_key,
    )
    if model not in _SUPPORTED_FWHM_MODELS:
        raise OperandoXRDError(
            f"model {model!r} has no supported reviewed XRD FWHM consumer; "
            "Doniach FWHM is intentionally fail-closed"
        )
    values = tuple(_model_fwhm(result, component_key, model) for result in retained)
    formula = {
        "gaussian": "2*sqrt(2*ln(2))*sigma",
        "lorentzian": "2*sigma",
        "pseudo_voigt": "2*sigma",
        "voigt": "1.0692*gamma+sqrt(0.8664*gamma^2+5.545083*sigma^2)",
    }[model]
    return build_operando_trace(
        stack,
        coordinate_key=coordinate_key,
        values=values,
        value_axis=Axis(
            "xrd_fit_fwhm",
            unit=stack.signal_axis.unit,
            label="Fitted XRD peak FWHM",
            metadata={"technique": "xrd", "component_key": component_key},
        ),
        method="xrd_fit_component_fwhm",
        parameters={
            "component_key": component_key,
            "model": model,
            "formula": formula,
            "formula_convention": "lmfit_builtin_model",
            "fit_x_min": x_min,
            "fit_x_max": x_max,
            "fit_method": fit_method,
            "source_state": "PeakFitResult",
        },
        metadata={"technique": "xrd", "fit_derived": True},
    )


__all__ = [
    "OperandoXRDError",
    "build_xrd_operando_stack",
    "xrd_fit_component_center_trace",
    "xrd_fit_component_fwhm_trace",
    "xrd_observed_peak_position_trace",
    "xrd_window_integral_trace",
]
