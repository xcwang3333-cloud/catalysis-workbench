"""Model-width and FTIR-fit regressions for v0.8 Block-4 spectroscopy."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.operando import (
    FrameCoordinate,
    build_ftir_operando_stack,
    build_raman_operando_stack,
    fit_component_center_trace,
    fit_component_fwhm_trace,
)
from catalysis_workbench.processing import (
    FitParameterSpec,
    FittedParameter,
    PeakComponentSpec,
    PeakFitSpec,
    fit_peaks,
)


def _gaussian(x: np.ndarray, center: float, sigma: float) -> np.ndarray:
    return 500.0 / (sigma * np.sqrt(2.0 * np.pi)) * np.exp(
        -((x - center) ** 2) / (2.0 * sigma**2)
    )


def _coordinate() -> tuple[FrameCoordinate, ...]:
    return (FrameCoordinate("time", Axis("time", unit="s"), [0.0]),)


def _raman_source() -> Series:
    x = np.linspace(900.0, 1300.0, 201)
    return Series(
        x,
        _gaussian(x, 1100.0, 25.0),
        key="r-fit",
        x_axis=Axis("raman_shift", unit="cm^-1"),
        y_axis=Axis(
            "intensity",
            unit="counts",
            metadata={"processing_basis": "raw"},
        ),
    )


def _gaussian_result(source: Series):
    component = PeakComponentSpec(
        key="band",
        model="gaussian",
        parameters={
            "amplitude": FitParameterSpec(450.0, lower=0.0),
            "center": FitParameterSpec(1100.0, lower=1000.0, upper=1200.0),
            "sigma": FitParameterSpec(24.0, lower=5.0, upper=60.0),
        },
    )
    return fit_peaks(source, PeakFitSpec(980.0, 1220.0, (component,)))


def _extra_parameter(name: str, value: float) -> FittedParameter:
    return FittedParameter(
        component_key="band",
        parameter_name=name,
        value=value,
        stderr=None,
        vary=False,
        lower=None,
        upper=None,
        expr=None,
    )


@pytest.mark.parametrize(
    ("model", "extra_specs", "extra_values", "expected"),
    [
        ("gaussian", {}, {}, 2.0 * np.sqrt(2.0 * np.log(2.0)) * 25.0),
        ("lorentzian", {}, {}, 50.0),
        (
            "pseudo_voigt",
            {"fraction": FitParameterSpec(0.4, vary=False)},
            {"fraction": 0.4},
            50.0,
        ),
        (
            "voigt",
            {"gamma": FitParameterSpec(12.0, vary=False, lower=0.0)},
            {"gamma": 12.0},
            1.0692 * 12.0 + np.sqrt(0.8664 * 12.0**2 + 5.545083 * 25.0**2),
        ),
    ],
)
def test_supported_model_fwhm_conventions_are_explicit(
    model: str,
    extra_specs: dict[str, FitParameterSpec],
    extra_values: dict[str, float],
    expected: float,
) -> None:
    source = _raman_source()
    stack = build_raman_operando_stack(
        (source,),
        frame_coordinates=_coordinate(),
        primary_coordinate_key="time",
    )
    base = _gaussian_result(source)
    sigma = _extra_parameter("sigma", 25.0)
    parameters = dict(base.parameters)
    parameters["band.sigma"] = sigma
    for name, value in extra_values.items():
        parameters[f"band.{name}"] = _extra_parameter(name, value)

    component_parameters = {
        "amplitude": FitParameterSpec(500.0, vary=False, lower=0.0),
        "center": FitParameterSpec(1100.0, vary=False),
        "sigma": FitParameterSpec(25.0, vary=False, lower=0.0),
        **extra_specs,
    }
    component = PeakComponentSpec(
        key="band",
        model=model,
        parameters=component_parameters,
    )
    result = replace(
        base,
        spec=PeakFitSpec(980.0, 1220.0, (component,)),
        parameters=parameters,
    )

    trace = fit_component_fwhm_trace(
        stack,
        (result,),
        coordinate_key="time",
        component_key="band",
        technique="raman",
    )
    assert trace.values[0] == pytest.approx(expected, rel=1e-12)
    assert trace.parameters_dict()["model"] == model
    assert trace.parameters_dict()["formula_convention"] == "lmfit_builtin_model"


def test_descending_ftir_fit_center_and_fwhm_are_consumed_without_reordering() -> None:
    x = np.linspace(1800.0, 1400.0, 201)
    source = Series(
        x,
        _gaussian(x, 1600.0, 22.0),
        key="ftir-fit",
        x_axis=Axis("wavenumber", unit="cm^-1"),
        y_axis=Axis("absorbance", metadata={"processing_basis": "raw"}),
    )
    stack = build_ftir_operando_stack(
        (source,),
        frame_coordinates=_coordinate(),
        primary_coordinate_key="time",
    )
    component = PeakComponentSpec(
        key="band",
        model="gaussian",
        parameters={
            "amplitude": FitParameterSpec(450.0, lower=0.0),
            "center": FitParameterSpec(1600.0, lower=1500.0, upper=1700.0),
            "sigma": FitParameterSpec(25.0, lower=5.0, upper=60.0),
        },
    )
    result = fit_peaks(source, PeakFitSpec(1480.0, 1720.0, (component,)))

    center = fit_component_center_trace(
        stack,
        (result,),
        coordinate_key="time",
        component_key="band",
        technique="ftir",
    )
    width = fit_component_fwhm_trace(
        stack,
        (result,),
        coordinate_key="time",
        component_key="band",
        technique="ftir",
    )

    assert stack.signal_direction == "decreasing"
    np.testing.assert_array_equal(stack.signal, source.x)
    assert center.values[0] == pytest.approx(1600.0, abs=1e-6)
    assert width.values[0] == pytest.approx(
        2.0 * np.sqrt(2.0 * np.log(2.0)) * 22.0,
        rel=1e-6,
    )
