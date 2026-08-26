from __future__ import annotations

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.characterization import XRDProcessingConfig, process_xrd
from catalysis_workbench.experimental.operando.stack import FrameCoordinate
from catalysis_workbench.experimental.operando.xrd import (
    OperandoXRDError,
    build_xrd_operando_stack,
    xrd_fit_component_center_trace,
    xrd_fit_component_fwhm_trace,
    xrd_observed_peak_position_trace,
    xrd_window_integral_trace,
)
from catalysis_workbench.processing import (
    FitParameterSpec,
    PeakComponentSpec,
    PeakFitSpec,
    fit_peaks,
)


def _pattern(
    key: str,
    y: np.ndarray | list[float],
    *,
    x: np.ndarray | list[float] | None = None,
    x_name: str = "two_theta",
    x_unit: str = "deg",
    y_name: str = "intensity",
    y_unit: str | None = "counts",
) -> Series:
    signal = np.arange(20.0, 25.0, 1.0) if x is None else np.asarray(x, dtype=float)
    return Series(
        signal,
        y,
        key=key,
        x_axis=Axis(x_name, unit=x_unit),
        y_axis=Axis(y_name, unit=y_unit),
    )


def _coordinate(values: list[float]) -> FrameCoordinate:
    return FrameCoordinate("time", Axis("time", unit="s"), values)


def _stack(frames: list[Series]):
    return build_xrd_operando_stack(
        frames,
        frame_coordinates=[_coordinate([float(i) for i in range(len(frames))])],
        primary_coordinate_key="time",
    )


def test_xrd_adapter_preserves_exact_arrays_and_canonicalizes_semantic_aliases() -> None:
    first = _pattern("a", [0.0, 1.0, 2.0, 1.0, 0.0], x_name="2θ", x_unit="degree", y_unit="count")
    second = _pattern("b", [0.0, 2.0, 4.0, 2.0, 0.0])
    stack = _stack([first, second])

    assert stack.signal_axis.name == "two_theta"
    assert stack.signal_axis.unit == "deg"
    assert stack.value_axis.name == "intensity"
    assert stack.value_axis.unit == "counts"
    assert np.array_equal(stack.signal, first.x)
    assert np.array_equal(stack.values[0], first.y)
    assert np.array_equal(stack.values[1], second.y)
    assert stack.reconstructed_source_digests() == stack.source_digests
    assert not stack.signal.flags.writeable
    assert not stack.values.flags.writeable
    record = stack.metadata["catalysis_workbench.operando_domain"]
    assert record["technique"] == "xrd"
    assert record["normalization_basis"]["normalization"] is None


def test_xrd_adapter_fails_closed_on_grid_direction_and_normalization_basis() -> None:
    raw = _pattern("raw", [0.0, 1.0, 2.0, 1.0, 0.0])
    mismatched_grid = _pattern(
        "grid",
        [0.0, 1.0, 2.0, 1.0, 0.0],
        x=[20.0, 21.0, 22.1, 23.0, 24.0],
    )
    with pytest.raises(OperandoXRDError, match="literally identical"):
        _stack([raw, mismatched_grid])

    decreasing = _pattern(
        "decreasing",
        [0.0, 1.0, 2.0, 1.0, 0.0],
        x=[24.0, 23.0, 22.0, 21.0, 20.0],
    )
    with pytest.raises(OperandoXRDError, match="strictly increasing"):
        _stack([decreasing])

    normalized_max = process_xrd(
        _pattern("n1", [1.0, 2.0, 4.0, 2.0, 1.0]),
        XRDProcessingConfig(normalization="max"),
    )
    normalized_max_abs = process_xrd(
        _pattern("n2", [1.0, 2.0, 4.0, 2.0, 1.0]),
        XRDProcessingConfig(normalization="max_abs"),
    )
    with pytest.raises(OperandoXRDError, match="normalization basis"):
        _stack([normalized_max, normalized_max_abs])
    with pytest.raises(OperandoXRDError, match="normalization basis"):
        _stack([raw, normalized_max])


def test_xrd_adapter_rejects_reserved_domain_metadata() -> None:
    with pytest.raises(OperandoXRDError, match="reserved"):
        build_xrd_operando_stack(
            [_pattern("a", [0.0, 1.0, 2.0, 1.0, 0.0])],
            frame_coordinates=[_coordinate([0.0])],
            primary_coordinate_key="time",
            metadata={"catalysis_workbench.operando_domain": {"technique": "spoof"}},
        )


def test_xrd_window_integral_uses_only_retained_measured_points() -> None:
    stack = _stack(
        [
            _pattern("a", [0.0, 1.0, 2.0, 1.0, 0.0]),
            _pattern("b", [0.0, 2.0, 4.0, 2.0, 0.0]),
        ]
    )
    digest = stack.digest
    trace = xrd_window_integral_trace(
        stack,
        two_theta_min_deg=21.0,
        two_theta_max_deg=23.0,
        coordinate_key="time",
    )

    np.testing.assert_allclose(trace.values, [3.0, 6.0])
    assert trace.parameters["boundary_rule"] == "inclusive_measured_points_only"
    assert trace.parameters["integration_rule"] == "numpy.trapezoid"
    assert trace.parameters["interpolation"] is False
    assert trace.value_axis.unit == "counts*deg"
    assert stack.digest == digest


def test_xrd_window_integral_requires_two_measured_points() -> None:
    stack = _stack([_pattern("a", [0.0, 1.0, 2.0, 1.0, 0.0])])
    with pytest.raises(OperandoXRDError, match="fewer than 2 measured points"):
        xrd_window_integral_trace(
            stack,
            two_theta_min_deg=21.9,
            two_theta_max_deg=22.1,
            coordinate_key="time",
        )


def test_xrd_observed_peak_position_uses_unique_retained_maximum() -> None:
    stack = _stack(
        [
            _pattern("a", [0.0, 1.0, 4.0, 2.0, 0.0]),
            _pattern("b", [0.0, 1.0, 2.0, 5.0, 0.0]),
        ]
    )
    trace = xrd_observed_peak_position_trace(
        stack,
        two_theta_min_deg=21.0,
        two_theta_max_deg=23.0,
        coordinate_key="time",
    )

    np.testing.assert_array_equal(trace.values, [22.0, 23.0])
    assert trace.parameters["tie_rule"] == "fail_closed"
    assert trace.parameters["interpolation"] is False


def test_xrd_observed_peak_position_fails_on_equal_maxima() -> None:
    stack = _stack([_pattern("tie", [0.0, 4.0, 4.0, 1.0, 0.0])])
    with pytest.raises(OperandoXRDError, match="ambiguous equal-maximum"):
        xrd_observed_peak_position_trace(
            stack,
            two_theta_min_deg=21.0,
            two_theta_max_deg=23.0,
            coordinate_key="time",
        )


def _gaussian(
    x: np.ndarray,
    *,
    amplitude: float,
    center: float,
    sigma: float,
) -> np.ndarray:
    return amplitude / (sigma * np.sqrt(2.0 * np.pi)) * np.exp(
        -((x - center) ** 2) / (2.0 * sigma**2)
    )


def _gaussian_spec() -> PeakFitSpec:
    component = PeakComponentSpec(
        key="peak",
        model="gaussian",
        parameters={
            "amplitude": FitParameterSpec(10.0, lower=0.0),
            "center": FitParameterSpec(25.0, lower=22.0, upper=28.0),
            "sigma": FitParameterSpec(0.8, lower=0.1, upper=2.0),
        },
    )
    return PeakFitSpec(22.0, 28.0, (component,))


def test_xrd_fit_center_and_fwhm_consume_compatible_peak_results() -> None:
    x = np.linspace(20.0, 30.0, 201)
    first = _pattern(
        "a",
        _gaussian(x, amplitude=12.0, center=24.0, sigma=0.5),
        x=x,
    )
    second = _pattern(
        "b",
        _gaussian(x, amplitude=16.0, center=26.0, sigma=0.7),
        x=x,
    )
    stack = build_xrd_operando_stack(
        [first, second],
        frame_coordinates=[_coordinate([0.0, 1.0])],
        primary_coordinate_key="time",
    )
    fits = [fit_peaks(first, _gaussian_spec()), fit_peaks(second, _gaussian_spec())]

    center = xrd_fit_component_center_trace(
        stack,
        fits,
        coordinate_key="time",
        component_key="peak",
    )
    width = xrd_fit_component_fwhm_trace(
        stack,
        fits,
        coordinate_key="time",
        component_key="peak",
    )

    np.testing.assert_allclose(center.values, [24.0, 26.0], atol=1e-6)
    np.testing.assert_allclose(
        width.values,
        2.0 * np.sqrt(2.0 * np.log(2.0)) * np.array([0.5, 0.7]),
        rtol=1e-5,
    )
    assert center.parameters["source_state"] == "PeakFitResult"
    assert width.parameters["formula_convention"] == "lmfit_builtin_model"


def test_xrd_fit_consumers_fail_closed_on_source_order_mismatch() -> None:
    x = np.linspace(20.0, 30.0, 201)
    first = _pattern("a", _gaussian(x, amplitude=12.0, center=24.0, sigma=0.5), x=x)
    second = _pattern("b", _gaussian(x, amplitude=12.0, center=26.0, sigma=0.5), x=x)
    stack = build_xrd_operando_stack(
        [first, second],
        frame_coordinates=[_coordinate([0.0, 1.0])],
        primary_coordinate_key="time",
    )
    fits = [fit_peaks(first, _gaussian_spec()), fit_peaks(second, _gaussian_spec())]

    with pytest.raises(OperandoXRDError, match="source keys/order"):
        xrd_fit_component_center_trace(
            stack,
            fits[::-1],
            coordinate_key="time",
            component_key="peak",
        )
