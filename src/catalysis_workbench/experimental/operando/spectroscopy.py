"""Operando Raman/FTIR adapters and explicit trajectories for v0.8 Block 4."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import log, sqrt
from typing import Any, Literal

import numpy as np

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.characterization import (
    FTIRBand,
    FTIRError,
    RamanBand,
    RamanError,
    measure_ftir_band,
    measure_raman_band,
    validate_ftir_series,
    validate_raman_series,
)
from catalysis_workbench.experimental.characterization.ftir import (
    _canonicalize_ftir_series,
)
from catalysis_workbench.experimental.characterization.raman import (
    _canonicalize_raman_series,
)
from catalysis_workbench.processing import PeakFitResult
from catalysis_workbench.processing.peak_fitting import _series_data_digest

from .operations import OperandoTrace, build_operando_trace, frame_cut
from .stack import (
    FrameCoordinate,
    OperandoStack,
    OperandoStackError,
    build_operando_stack,
    series_array_digest,
)

AreaMode = Literal["absolute", "net"]
Technique = Literal["raman", "ftir"]

_DOMAIN_METADATA_KEY = "catalysis_workbench.operando_domain"
_SUPPORTED_FWHM_MODELS = frozenset({"gaussian", "lorentzian", "voigt", "pseudo_voigt"})


class OperandoSpectroscopyError(OperandoStackError):
    """Raised when a Raman/FTIR operando request violates the frozen contract."""


def _domain_metadata(
    metadata: Mapping[str, Any] | None,
    *,
    technique: Technique,
    adapter: str,
    fit_source_sha256: Sequence[str],
) -> dict[str, Any]:
    output = {} if metadata is None else dict(metadata)
    if _DOMAIN_METADATA_KEY in output:
        raise OperandoSpectroscopyError(
            f"caller metadata must not override reserved {_DOMAIN_METADATA_KEY!r}"
        )
    output[_DOMAIN_METADATA_KEY] = {
        "technique": technique,
        "adapter": adapter,
        "fit_source_sha256": tuple(fit_source_sha256),
    }
    return output


def _canonical_domain_frames(
    frames: Sequence[Series],
    *,
    technique: Technique,
) -> tuple[tuple[Series, ...], tuple[str, ...], tuple[str, ...]]:
    retained = tuple(frames)
    if not retained or not all(isinstance(frame, Series) for frame in retained):
        raise OperandoSpectroscopyError("frames must contain at least one Series")

    canonical: list[Series] = []
    source_digests: list[str] = []
    fit_source_sha256: list[str] = []
    for index, frame in enumerate(retained):
        try:
            if technique == "raman":
                validate_raman_series(frame)
                normalized = _canonicalize_raman_series(frame)
            else:
                validate_ftir_series(frame)
                normalized = _canonicalize_ftir_series(frame)
            digest = series_array_digest(frame)
        except (RamanError, FTIRError, OperandoStackError, TypeError) as exc:
            raise OperandoSpectroscopyError(
                f"{technique} frame {index} is not valid retained domain state: {exc}"
            ) from exc

        if digest != series_array_digest(normalized):
            raise RuntimeError(
                "domain semantic canonicalization unexpectedly changed source arrays"
            )
        canonical.append(normalized)
        source_digests.append(digest)
        fit_source_sha256.append(_series_data_digest(normalized))

    return tuple(canonical), tuple(source_digests), tuple(fit_source_sha256)


def _build_domain_stack(
    frames: Sequence[Series],
    *,
    frame_coordinates: Sequence[FrameCoordinate],
    primary_coordinate_key: str,
    source_digests: Sequence[str],
    metadata: Mapping[str, Any],
) -> OperandoStack:
    try:
        return build_operando_stack(
            frames,
            frame_coordinates=frame_coordinates,
            primary_coordinate_key=primary_coordinate_key,
            expected_source_digests=source_digests,
            metadata=metadata,
        )
    except OperandoStackError as exc:
        raise OperandoSpectroscopyError(str(exc)) from exc


def build_raman_operando_stack(
    frames: Sequence[Series],
    *,
    frame_coordinates: Sequence[FrameCoordinate],
    primary_coordinate_key: str,
    metadata: Mapping[str, Any] | None = None,
) -> OperandoStack:
    """Build an exact-grid Raman stack without performing Raman processing."""
    canonical, source_digests, fit_source_sha256 = _canonical_domain_frames(
        frames,
        technique="raman",
    )
    return _build_domain_stack(
        canonical,
        frame_coordinates=frame_coordinates,
        primary_coordinate_key=primary_coordinate_key,
        source_digests=source_digests,
        metadata=_domain_metadata(
            metadata,
            technique="raman",
            adapter="build_raman_operando_stack",
            fit_source_sha256=fit_source_sha256,
        ),
    )


def build_ftir_operando_stack(
    frames: Sequence[Series],
    *,
    frame_coordinates: Sequence[FrameCoordinate],
    primary_coordinate_key: str,
    metadata: Mapping[str, Any] | None = None,
) -> OperandoStack:
    """Build an exact-grid FTIR stack without hidden conversion or processing."""
    canonical, source_digests, fit_source_sha256 = _canonical_domain_frames(
        frames,
        technique="ftir",
    )
    return _build_domain_stack(
        canonical,
        frame_coordinates=frame_coordinates,
        primary_coordinate_key=primary_coordinate_key,
        source_digests=source_digests,
        metadata=_domain_metadata(
            metadata,
            technique="ftir",
            adapter="build_ftir_operando_stack",
            fit_source_sha256=fit_source_sha256,
        ),
    )


def _domain_record(stack: OperandoStack, *, technique: Technique) -> Mapping[str, Any]:
    if not isinstance(stack, OperandoStack):
        raise TypeError("stack must be an OperandoStack")
    record = stack.metadata.get(_DOMAIN_METADATA_KEY)
    if not isinstance(record, Mapping) or record.get("technique") != technique:
        raise OperandoSpectroscopyError(
            f"stack must be produced by the reviewed {technique} operando adapter"
        )
    return record


def _area_unit(value_unit: str | None, signal_unit: str | None) -> str | None:
    value = None if value_unit is None else str(value_unit).strip()
    signal = None if signal_unit is None else str(signal_unit).strip()
    if value in {None, "", "1", "dimensionless"}:
        return signal
    if signal in {None, "", "1", "dimensionless"}:
        return value
    return f"{value}*{signal}"


def _band_trace(
    stack: OperandoStack,
    *,
    technique: Technique,
    band: RamanBand | FTIRBand,
    coordinate_key: str,
    metric: Literal["area", "peak_position"],
    area_mode: AreaMode,
) -> OperandoTrace:
    _domain_record(stack, technique=technique)
    if area_mode not in {"absolute", "net"}:
        raise OperandoSpectroscopyError("area_mode must be 'absolute' or 'net'")

    values: list[float] = []
    try:
        for index in range(stack.n_frames):
            spectrum = frame_cut(stack, index=index)
            measurement = (
                measure_raman_band(spectrum, band, area_mode=area_mode)
                if technique == "raman"
                else measure_ftir_band(spectrum, band, area_mode=area_mode)
            )
            value = measurement.area if metric == "area" else measurement.peak_position_cm1
            values.append(float(value))
    except (RamanError, FTIRError, TypeError) as exc:
        raise OperandoSpectroscopyError(
            f"{technique} {metric} trajectory failed in reviewed domain measurement: {exc}"
        ) from exc

    if technique == "raman":
        assert isinstance(band, RamanBand)
        band_parameters = {
            "band_min_cm1": band.x_min_cm1,
            "band_max_cm1": band.x_max_cm1,
            "band_label": band.label,
        }
    else:
        assert isinstance(band, FTIRBand)
        band_parameters = {
            "band_min_cm1": band.low_cm1,
            "band_max_cm1": band.high_cm1,
            "band_label": band.label,
        }

    if metric == "area":
        value_axis = Axis(
            f"{technique}_band_area",
            unit=_area_unit(stack.value_axis.unit, stack.signal_axis.unit),
            label="Band area",
            metadata={"technique": technique, "area_mode": area_mode},
        )
    else:
        value_axis = Axis(
            f"{technique}_peak_position",
            unit=stack.signal_axis.unit,
            label="Peak position",
            metadata={"technique": technique, "measurement": "observed_window_maximum"},
        )

    return build_operando_trace(
        stack,
        coordinate_key=coordinate_key,
        values=values,
        value_axis=value_axis,
        method=f"{technique}_band_{metric}",
        parameters={
            **band_parameters,
            "area_mode": area_mode,
            "domain_function": (
                "measure_raman_band" if technique == "raman" else "measure_ftir_band"
            ),
            "boundary_interpolation": "reviewed_domain_function_only",
        },
        metadata={"technique": technique, "measurement_kind": metric},
    )


def raman_band_area_trace(
    stack: OperandoStack,
    band: RamanBand,
    *,
    coordinate_key: str,
    area_mode: AreaMode = "net",
) -> OperandoTrace:
    """Return one explicit Raman direct-band area per retained frame."""
    if not isinstance(band, RamanBand):
        raise TypeError("band must be a RamanBand")
    return _band_trace(
        stack,
        technique="raman",
        band=band,
        coordinate_key=coordinate_key,
        metric="area",
        area_mode=area_mode,
    )


def raman_peak_position_trace(
    stack: OperandoStack,
    band: RamanBand,
    *,
    coordinate_key: str,
) -> OperandoTrace:
    """Return the observed Raman window maximum position per retained frame."""
    if not isinstance(band, RamanBand):
        raise TypeError("band must be a RamanBand")
    return _band_trace(
        stack,
        technique="raman",
        band=band,
        coordinate_key=coordinate_key,
        metric="peak_position",
        area_mode="net",
    )


def ftir_band_area_trace(
    stack: OperandoStack,
    band: FTIRBand,
    *,
    coordinate_key: str,
    area_mode: AreaMode = "net",
) -> OperandoTrace:
    """Return one explicit FTIR direct-band area per retained frame."""
    if not isinstance(band, FTIRBand):
        raise TypeError("band must be an FTIRBand")
    return _band_trace(
        stack,
        technique="ftir",
        band=band,
        coordinate_key=coordinate_key,
        metric="area",
        area_mode=area_mode,
    )


def ftir_peak_position_trace(
    stack: OperandoStack,
    band: FTIRBand,
    *,
    coordinate_key: str,
) -> OperandoTrace:
    """Return the observed FTIR window maximum position per retained frame."""
    if not isinstance(band, FTIRBand):
        raise TypeError("band must be an FTIRBand")
    return _band_trace(
        stack,
        technique="ftir",
        band=band,
        coordinate_key=coordinate_key,
        metric="peak_position",
        area_mode="net",
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
    raise OperandoSpectroscopyError(
        f"fit result does not contain component {component_key!r}"
    )


def _validated_fit_results(
    stack: OperandoStack,
    fit_results: Sequence[PeakFitResult],
    *,
    technique: Technique,
    component_key: str,
) -> tuple[tuple[PeakFitResult, ...], str, float, float, str]:
    record = _domain_record(stack, technique=technique)
    key = str(component_key).strip()
    if not key:
        raise OperandoSpectroscopyError("component_key must not be blank")
    retained = tuple(fit_results)
    if len(retained) != stack.n_frames or not all(
        isinstance(result, PeakFitResult) for result in retained
    ):
        raise OperandoSpectroscopyError(
            "fit_results must contain exactly one PeakFitResult per retained frame"
        )

    expected_fit_sha = tuple(record.get("fit_source_sha256", ()))
    if len(expected_fit_sha) != stack.n_frames:
        raise OperandoSpectroscopyError("stack is missing reconstructible fit-source provenance")

    model: str | None = None
    x_min: float | None = None
    x_max: float | None = None
    method: str | None = None
    for index, result in enumerate(retained):
        if not result.success:
            raise OperandoSpectroscopyError(
                f"fit result for frame {stack.frame_keys[index]!r} was not successful"
            )
        if result.source_key != stack.source_keys[index]:
            raise OperandoSpectroscopyError(
                "fit result source keys/order must exactly match retained stack source order"
            )
        if result.source_sha256 != expected_fit_sha[index]:
            raise OperandoSpectroscopyError(
                f"fit result for frame {stack.frame_keys[index]!r} does not match source arrays"
            )

        try:
            probe = _fit_probe(result)
            canonical_probe = (
                _canonicalize_raman_series(probe)
                if technique == "raman"
                else _canonicalize_ftir_series(probe)
            )
        except (RamanError, FTIRError, TypeError) as exc:
            raise OperandoSpectroscopyError(
                f"fit result axis state is not compatible with {technique}: {exc}"
            ) from exc
        if (
            canonical_probe.x_axis.name != stack.signal_axis.name
            or canonical_probe.x_axis.unit != stack.signal_axis.unit
            or canonical_probe.y_axis.name != stack.value_axis.name
            or canonical_probe.y_axis.unit != stack.value_axis.unit
        ):
            raise OperandoSpectroscopyError(
                "fit result axis/value basis is incompatible with the retained stack"
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
            raise OperandoSpectroscopyError(
                "fit component model, fit window, and fit method must be identical across frames"
            )

    assert model is not None and x_min is not None and x_max is not None and method is not None
    return retained, model, x_min, x_max, method


def _fitted_parameter(result: PeakFitResult, component_key: str, name: str) -> float:
    key = f"{component_key}.{name}"
    parameter = result.parameters.get(key)
    if parameter is None:
        raise OperandoSpectroscopyError(f"fit result is missing retained parameter {key!r}")
    value = float(parameter.value)
    if not np.isfinite(value):
        raise OperandoSpectroscopyError(f"fit parameter {key!r} must be finite")
    return value


def fit_component_center_trace(
    stack: OperandoStack,
    fit_results: Sequence[PeakFitResult],
    *,
    coordinate_key: str,
    component_key: str,
    technique: Technique,
) -> OperandoTrace:
    """Consume fitted component centers without performing an operando fit."""
    retained, model, x_min, x_max, fit_method = _validated_fit_results(
        stack,
        fit_results,
        technique=technique,
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
            f"{technique}_fit_center",
            unit=stack.signal_axis.unit,
            label="Fitted peak center",
            metadata={"technique": technique, "component_key": component_key},
        ),
        method=f"{technique}_fit_component_center",
        parameters={
            "component_key": component_key,
            "model": model,
            "fit_x_min": x_min,
            "fit_x_max": x_max,
            "fit_method": fit_method,
            "source_state": "PeakFitResult",
        },
        metadata={"technique": technique, "fit_derived": True},
    )


def _model_fwhm(result: PeakFitResult, component_key: str, model: str) -> float:
    if model not in _SUPPORTED_FWHM_MODELS:
        raise OperandoSpectroscopyError(
            f"model {model!r} has no supported reviewed FWHM consumer; "
            "Doniach FWHM is intentionally fail-closed"
        )
    sigma = _fitted_parameter(result, component_key, "sigma")
    if sigma < 0.0:
        raise OperandoSpectroscopyError("fit sigma must be non-negative for FWHM")
    if model == "gaussian":
        return 2.0 * sqrt(2.0 * log(2.0)) * sigma
    if model in {"lorentzian", "pseudo_voigt"}:
        return 2.0 * sigma
    gamma = _fitted_parameter(result, component_key, "gamma")
    if gamma < 0.0:
        raise OperandoSpectroscopyError("fit gamma must be non-negative for Voigt FWHM")
    return 1.0692 * gamma + sqrt(0.8664 * gamma * gamma + 5.545083 * sigma * sigma)


def fit_component_fwhm_trace(
    stack: OperandoStack,
    fit_results: Sequence[PeakFitResult],
    *,
    coordinate_key: str,
    component_key: str,
    technique: Technique,
) -> OperandoTrace:
    """Consume reviewed fit widths using the retained lmfit model convention."""
    retained, model, x_min, x_max, fit_method = _validated_fit_results(
        stack,
        fit_results,
        technique=technique,
        component_key=component_key,
    )
    if model not in _SUPPORTED_FWHM_MODELS:
        raise OperandoSpectroscopyError(
            f"model {model!r} has no supported reviewed FWHM consumer; "
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
            f"{technique}_fit_fwhm",
            unit=stack.signal_axis.unit,
            label="Fitted peak FWHM",
            metadata={"technique": technique, "component_key": component_key},
        ),
        method=f"{technique}_fit_component_fwhm",
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
        metadata={"technique": technique, "fit_derived": True},
    )
