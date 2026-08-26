"""Operando XAS/XANES adapters and explicit descriptors for v0.8 Block 5."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal

import numpy as np

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.characterization import (
    XANESNormalizationResult,
    XASError,
    XASWindow,
    validate_xas_series,
)

from .operations import OperandoTrace, build_operando_trace
from .stack import (
    FrameCoordinate,
    OperandoStack,
    OperandoStackError,
    build_operando_stack,
    series_array_digest,
)

XASMode = Literal["raw", "normalized"]
EdgePositionMethod = Literal["adjacent_secant_maximum"]
WindowIntegralMethod = Literal["trapezoid_measured_points"]
WhiteLineMethod = Literal["observed_maximum"]

_DOMAIN_METADATA_KEY = "catalysis_workbench.operando_domain"
_RAW_VALUE_NAMES = frozenset({"mu", "absorption"})
_NORMALIZED_VALUE_NAMES = frozenset({"normalizedmu", "munormalized"})


class OperandoXASError(OperandoStackError):
    """Raised when XAS/XANES operando state violates the frozen Block-5 contract."""


def _semantic_token(value: str) -> str:
    token = str(value).strip().casefold()
    return "".join(character for character in token if character.isalnum())


def _energy_reference(series: Series) -> str | None:
    reference = series.metadata.get("energy_reference")
    if reference is None:
        return None
    text = str(reference).strip()
    if not text:
        raise OperandoXASError("energy_reference metadata must not be blank")
    return text


def _canonical_xas_series(series: Series, *, mode: XASMode) -> Series:
    if not isinstance(series, Series):
        raise TypeError("XAS frames must be Series objects")
    try:
        validate_xas_series(series)
    except (XASError, TypeError) as exc:
        raise OperandoXASError(f"invalid retained XAS frame: {exc}") from exc

    value_name = _semantic_token(series.y_axis.name)
    if mode == "raw" and value_name not in _RAW_VALUE_NAMES:
        raise OperandoXASError("raw XAS mode requires mu/absorption input")
    if mode == "normalized" and value_name not in _NORMALIZED_VALUE_NAMES:
        raise OperandoXASError("normalized XANES mode requires normalized_mu input")

    canonical = Series(
        x=series.x,
        y=series.y,
        label=series.label,
        key=series.key,
        x_axis=Axis(
            "energy",
            unit="eV",
            label=series.x_axis.label,
            metadata=series.x_axis.metadata_dict(),
        ),
        y_axis=Axis(
            "mu" if mode == "raw" else "normalized_mu",
            unit=series.y_axis.unit,
            label=series.y_axis.label,
            metadata=series.y_axis.metadata_dict(),
        ),
        metadata=series.metadata_dict(),
    )
    if series_array_digest(canonical) != series_array_digest(series):
        raise RuntimeError("XAS semantic canonicalization unexpectedly changed source arrays")
    return canonical


def _normalization_signature(result: XANESNormalizationResult) -> dict[str, Any]:
    return {
        "e0_ev": result.e0_ev,
        "pre_edge_ev": (result.pre_edge.start_ev, result.pre_edge.end_ev),
        "post_edge_ev": (result.post_edge.start_ev, result.post_edge.end_ev),
        "pre_edge_order": result.pre_edge_order,
        "post_edge_order": result.post_edge_order,
    }


def _domain_metadata(
    metadata: Mapping[str, Any] | None,
    *,
    mode: XASMode,
    adapter: str,
    energy_reference: str | None,
    normalization_signature: Mapping[str, Any] | None = None,
    normalization_source_digests: Sequence[str] = (),
) -> dict[str, Any]:
    output = {} if metadata is None else dict(metadata)
    if _DOMAIN_METADATA_KEY in output:
        raise OperandoXASError(
            f"caller metadata must not override reserved {_DOMAIN_METADATA_KEY!r}"
        )
    record: dict[str, Any] = {
        "technique": "xas",
        "mode": mode,
        "adapter": adapter,
        "energy_reference": energy_reference,
        "normalization_source_digests": tuple(normalization_source_digests),
    }
    if normalization_signature is not None:
        record["normalization_signature"] = dict(normalization_signature)
    output[_DOMAIN_METADATA_KEY] = record
    return output


def _require_common_energy_reference(frames: Sequence[Series]) -> str | None:
    references = tuple(_energy_reference(frame) for frame in frames)
    first = references[0]
    if any(reference != first for reference in references[1:]):
        raise OperandoXASError(
            "all XAS frames must use the same explicit energy_reference metadata state"
        )
    return first


def build_xas_operando_stack(
    frames: Sequence[Series],
    *,
    frame_coordinates: Sequence[FrameCoordinate],
    primary_coordinate_key: str,
    metadata: Mapping[str, Any] | None = None,
) -> OperandoStack:
    """Build an exact-grid raw-XAS stack without hidden energy processing."""
    retained = tuple(frames)
    if not retained:
        raise OperandoXASError("frames must contain at least one raw XAS Series")
    canonical = tuple(_canonical_xas_series(frame, mode="raw") for frame in retained)
    source_digests = tuple(series_array_digest(frame) for frame in canonical)
    reference = _require_common_energy_reference(canonical)
    try:
        return build_operando_stack(
            canonical,
            frame_coordinates=frame_coordinates,
            primary_coordinate_key=primary_coordinate_key,
            expected_source_digests=source_digests,
            metadata=_domain_metadata(
                metadata,
                mode="raw",
                adapter="build_xas_operando_stack",
                energy_reference=reference,
            ),
        )
    except OperandoStackError as exc:
        raise OperandoXASError(str(exc)) from exc


def build_xanes_operando_stack(
    results: Sequence[XANESNormalizationResult],
    *,
    frame_coordinates: Sequence[FrameCoordinate],
    primary_coordinate_key: str,
    metadata: Mapping[str, Any] | None = None,
) -> OperandoStack:
    """Build an exact-grid normalized-XANES stack from reviewed result state."""
    retained = tuple(results)
    if not retained or not all(
        isinstance(result, XANESNormalizationResult) for result in retained
    ):
        raise OperandoXASError(
            "results must contain at least one XANESNormalizationResult"
        )

    signatures = tuple(_normalization_signature(result) for result in retained)
    first_signature = signatures[0]
    if any(signature != first_signature for signature in signatures[1:]):
        raise OperandoXASError(
            "normalized XANES frames must use identical E0/pre-edge/post-edge "
            "normalization parameters"
        )

    canonical = tuple(
        _canonical_xas_series(result.normalized, mode="normalized")
        for result in retained
    )
    reference = _require_common_energy_reference(canonical)
    source_digests = tuple(series_array_digest(frame) for frame in canonical)
    normalization_source_digests = tuple(result.source_digest for result in retained)
    try:
        return build_operando_stack(
            canonical,
            frame_coordinates=frame_coordinates,
            primary_coordinate_key=primary_coordinate_key,
            expected_source_digests=source_digests,
            metadata=_domain_metadata(
                metadata,
                mode="normalized",
                adapter="build_xanes_operando_stack",
                energy_reference=reference,
                normalization_signature=first_signature,
                normalization_source_digests=normalization_source_digests,
            ),
        )
    except OperandoStackError as exc:
        raise OperandoXASError(str(exc)) from exc


def _domain_record(stack: OperandoStack) -> Mapping[str, Any]:
    if not isinstance(stack, OperandoStack):
        raise TypeError("stack must be an OperandoStack")
    record = stack.metadata.get(_DOMAIN_METADATA_KEY)
    if not isinstance(record, Mapping) or record.get("technique") != "xas":
        raise OperandoXASError("stack must be produced by a reviewed XAS/XANES operando adapter")
    if record.get("mode") not in {"raw", "normalized"}:
        raise OperandoXASError("XAS operando stack is missing a valid raw/normalized mode")
    return record


def _require_mode(stack: OperandoStack, mode: XASMode) -> Mapping[str, Any]:
    record = _domain_record(stack)
    if record.get("mode") != mode:
        raise OperandoXASError(f"descriptor requires {mode!r} XAS/XANES mode")
    return record


def _window_indices(
    stack: OperandoStack,
    window: XASWindow,
    *,
    min_points: int,
) -> np.ndarray:
    if not isinstance(window, XASWindow):
        raise TypeError("window must be an XASWindow")
    energy = np.asarray(stack.signal, dtype=np.float64)
    indices = np.flatnonzero(
        (energy >= window.start_ev) & (energy <= window.end_ev)
    )
    if indices.size < min_points:
        raise OperandoXASError(
            f"window [{window.start_ev}, {window.end_ev}] eV retains fewer than "
            f"{min_points} measured points"
        )
    return indices


def _window_parameters(
    stack: OperandoStack,
    window: XASWindow,
    indices: np.ndarray,
) -> dict[str, Any]:
    retained_energy = np.asarray(stack.signal, dtype=np.float64)[indices]
    return {
        "window_start_ev": window.start_ev,
        "window_end_ev": window.end_ev,
        "retained_min_ev": float(np.min(retained_energy)),
        "retained_max_ev": float(np.max(retained_energy)),
        "retained_first_index": int(indices[0]),
        "retained_last_index": int(indices[-1]),
        "retained_point_count": int(indices.size),
        "boundary_policy": "measured_points_only",
    }


def _integral_unit(value_unit: str | None, energy_unit: str | None) -> str | None:
    value = None if value_unit is None else str(value_unit).strip()
    energy = None if energy_unit is None else str(energy_unit).strip()
    if value in {None, "", "1", "dimensionless"}:
        return energy
    if energy in {None, "", "1", "dimensionless"}:
        return value
    return f"{value}*{energy}"


def xanes_white_line_intensity_trace(
    stack: OperandoStack,
    window: XASWindow,
    *,
    coordinate_key: str,
    method: WhiteLineMethod = "observed_maximum",
) -> OperandoTrace:
    """Return the observed normalized-XANES maximum intensity in an explicit window."""
    _require_mode(stack, "normalized")
    if method != "observed_maximum":
        raise OperandoXASError("white-line method must be 'observed_maximum'")
    indices = _window_indices(stack, window, min_points=1)
    values = np.max(np.asarray(stack.values)[:, indices], axis=1)
    return build_operando_trace(
        stack,
        coordinate_key=coordinate_key,
        values=values,
        value_axis=Axis(
            "xanes_white_line_intensity",
            unit=stack.value_axis.unit,
            label="White-line intensity",
            metadata={"measurement": "observed_window_maximum"},
        ),
        method="xanes_white_line_intensity",
        parameters={
            **_window_parameters(stack, window, indices),
            "method": method,
            "assignment_semantics": "measurement_label_only",
        },
        metadata={"technique": "xas", "mode": "normalized"},
    )


def xanes_edge_position_trace(
    stack: OperandoStack,
    window: XASWindow,
    *,
    coordinate_key: str,
    method: EdgePositionMethod = "adjacent_secant_maximum",
) -> OperandoTrace:
    """Estimate edge position by the maximum adjacent measured-point secant slope."""
    _require_mode(stack, "normalized")
    if method != "adjacent_secant_maximum":
        raise OperandoXASError(
            "edge-position method must be 'adjacent_secant_maximum'"
        )
    indices = _window_indices(stack, window, min_points=2)
    energy = np.asarray(stack.signal, dtype=np.float64)[indices]
    delta_energy = np.diff(energy)
    if np.any(delta_energy == 0.0):
        raise RuntimeError("retained XAS energy unexpectedly contains duplicates")

    positions: list[float] = []
    for frame_index in range(stack.n_frames):
        values = np.asarray(stack.values[frame_index], dtype=np.float64)[indices]
        slopes = np.diff(values) / delta_energy
        if not np.isfinite(slopes).all():
            raise OperandoXASError("edge-position secant calculation produced non-finite values")
        maximum = float(np.max(slopes))
        if maximum <= 0.0:
            raise OperandoXASError(
                f"frame {stack.frame_keys[frame_index]!r} has no positive secant "
                "slope in the caller window"
            )
        candidates = np.flatnonzero(slopes == maximum)
        if candidates.size != 1:
            raise OperandoXASError(
                f"frame {stack.frame_keys[frame_index]!r} has an ambiguous "
                "equal-maximum edge secant"
            )
        local_index = int(candidates[0])
        positions.append(float((energy[local_index] + energy[local_index + 1]) / 2.0))

    return build_operando_trace(
        stack,
        coordinate_key=coordinate_key,
        values=positions,
        value_axis=Axis(
            "xanes_edge_position",
            unit=stack.signal_axis.unit,
            label="Edge position",
            metadata={
                "measurement": "maximum_adjacent_secant",
                "position_rule": "segment_midpoint",
            },
        ),
        method="xanes_edge_position",
        parameters={
            **_window_parameters(stack, window, indices),
            "method": method,
            "derivative_rule": "adjacent_measured_point_secant",
            "position_rule": "segment_midpoint",
            "energy_alignment": "none",
        },
        metadata={"technique": "xas", "mode": "normalized"},
    )


def xas_window_integral_trace(
    stack: OperandoStack,
    window: XASWindow,
    *,
    coordinate_key: str,
    method: WindowIntegralMethod = "trapezoid_measured_points",
) -> OperandoTrace:
    """Integrate raw or normalized XAS over retained measured points in a caller window."""
    record = _domain_record(stack)
    if method != "trapezoid_measured_points":
        raise OperandoXASError(
            "window-integral method must be 'trapezoid_measured_points'"
        )
    indices = _window_indices(stack, window, min_points=2)
    energy = np.asarray(stack.signal, dtype=np.float64)[indices]
    ascending = energy if energy[0] < energy[-1] else energy[::-1]

    integrals: list[float] = []
    for frame_index in range(stack.n_frames):
        values = np.asarray(stack.values[frame_index], dtype=np.float64)[indices]
        ordered_values = values if energy[0] < energy[-1] else values[::-1]
        integral = float(np.trapezoid(ordered_values, ascending))
        if not np.isfinite(integral):
            raise OperandoXASError("window integral produced a non-finite value")
        integrals.append(integral)

    return build_operando_trace(
        stack,
        coordinate_key=coordinate_key,
        values=integrals,
        value_axis=Axis(
            "xas_window_integral",
            unit=_integral_unit(stack.value_axis.unit, stack.signal_axis.unit),
            label="XAS window integral",
            metadata={"mode": record["mode"], "integration": method},
        ),
        method="xas_window_integral",
        parameters={
            **_window_parameters(stack, window, indices),
            "method": method,
            "integration_direction": "increasing_physical_energy",
            "boundary_interpolation": "none",
        },
        metadata={"technique": "xas", "mode": record["mode"]},
    )


__all__ = [
    "OperandoXASError",
    "build_xanes_operando_stack",
    "build_xas_operando_stack",
    "xanes_edge_position_trace",
    "xanes_white_line_intensity_trace",
    "xas_window_integral_trace",
]
