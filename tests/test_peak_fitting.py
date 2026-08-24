"""Scientific/API regression tests for the shared constrained peak-fitting foundation."""

from __future__ import annotations

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.processing import (
    FitParameterSpec,
    PeakComponentSpec,
    PeakFitSpec,
    PeakFittingError,
    fit_peaks,
)


def _gaussian(x: np.ndarray, *, amplitude: float, center: float, sigma: float) -> np.ndarray:
    return amplitude / (sigma * np.sqrt(2.0 * np.pi)) * np.exp(
        -((x - center) ** 2) / (2.0 * sigma**2)
    )


def _series(x: np.ndarray, y: np.ndarray, *, key: str = "synthetic") -> Series:
    return Series(
        x=x,
        y=y,
        key=key,
        label="Synthetic spectrum",
        x_axis=Axis("x", unit="a.u."),
        y_axis=Axis("intensity", unit="counts"),
    )


def _gaussian_component(
    key: str,
    *,
    amplitude: FitParameterSpec,
    center: FitParameterSpec,
    sigma: FitParameterSpec,
) -> PeakComponentSpec:
    return PeakComponentSpec(
        key=key,
        model="gaussian",
        parameters={
            "amplitude": amplitude,
            "center": center,
            "sigma": sigma,
        },
    )


def test_gaussian_fit_recovers_hand_verifiable_parameters() -> None:
    x = np.linspace(-5.0, 5.0, 401)
    y = _gaussian(x, amplitude=12.0, center=0.75, sigma=0.8)
    source = _series(x, y)
    component = _gaussian_component(
        "peak_a",
        amplitude=FitParameterSpec(10.0, lower=0.0),
        center=FitParameterSpec(0.5, lower=-2.0, upper=2.0),
        sigma=FitParameterSpec(1.0, lower=0.1, upper=2.0),
    )

    result = fit_peaks(source, PeakFitSpec(-4.0, 4.0, (component,)))

    assert result.success
    assert result.source_key == "synthetic"
    assert result.x_axis_name == "x"
    assert result.x_unit == "a.u."
    assert result.n_points == 321
    assert result.parameters["peak_a.amplitude"].value == pytest.approx(12.0, rel=1e-6)
    assert result.parameters["peak_a.center"].value == pytest.approx(0.75, abs=1e-7)
    assert result.parameters["peak_a.sigma"].value == pytest.approx(0.8, rel=1e-6)
    assert np.max(np.abs(result.residual)) < 1e-8
    assert np.allclose(result.observed_y, result.best_fit_y, atol=1e-8)
    assert tuple(result.component_curves) == ("peak_a",)
    assert not result.x.flags.writeable
    assert not result.best_fit_y.flags.writeable
    with pytest.raises(ValueError):
        result.x[0] = 99.0


def test_cross_component_tie_uses_public_stable_key_syntax() -> None:
    x = np.linspace(-6.0, 6.0, 601)
    y = _gaussian(x, amplitude=8.0, center=-1.0, sigma=0.6) + _gaussian(
        x, amplitude=4.0, center=1.5, sigma=0.6
    )
    source = _series(x, y)
    first = _gaussian_component(
        "left",
        amplitude=FitParameterSpec(7.0, lower=0.0),
        center=FitParameterSpec(-0.8, lower=-2.0, upper=0.0),
        sigma=FitParameterSpec(0.7, lower=0.2, upper=1.2),
    )
    second = _gaussian_component(
        "right",
        amplitude=FitParameterSpec(3.5, lower=0.0),
        center=FitParameterSpec(1.7, vary=False, expr="{left.center} + 2.5"),
        sigma=FitParameterSpec(0.7, vary=False, expr="{left.sigma}"),
    )

    result = fit_peaks(source, PeakFitSpec(-5.0, 5.0, (first, second)))

    assert result.success
    assert result.parameters["left.center"].value == pytest.approx(-1.0, abs=1e-6)
    assert result.parameters["right.center"].value == pytest.approx(1.5, abs=1e-6)
    assert result.parameters["right.sigma"].value == pytest.approx(
        result.parameters["left.sigma"].value, rel=1e-10
    )
    assert result.parameters["right.center"].expr == "{left.center} + 2.5"
    assert result.parameters["right.center"].vary is False


def test_fixed_and_bounded_parameter_state_is_preserved() -> None:
    x = np.linspace(-4.0, 4.0, 401)
    y = _gaussian(x, amplitude=6.0, center=0.2, sigma=0.5)
    component = _gaussian_component(
        "fixed",
        amplitude=FitParameterSpec(5.0, lower=0.0, upper=10.0),
        center=FitParameterSpec(0.2, vary=False, lower=-1.0, upper=1.0),
        sigma=FitParameterSpec(0.7, lower=0.4, upper=0.8),
    )

    result = fit_peaks(_series(x, y), PeakFitSpec(-3.0, 3.0, (component,)))

    center = result.parameters["fixed.center"]
    sigma = result.parameters["fixed.sigma"]
    assert center.value == pytest.approx(0.2)
    assert center.vary is False
    assert center.lower == pytest.approx(-1.0)
    assert center.upper == pytest.approx(1.0)
    assert 0.4 <= sigma.value <= 0.8


def test_explicit_background_is_cropped_used_and_preserved_exactly() -> None:
    x = np.linspace(0.0, 10.0, 501)
    background = 2.0 + 0.1 * x
    peak = _gaussian(x, amplitude=15.0, center=5.0, sigma=0.7)
    source = _series(x, background + peak)
    component = _gaussian_component(
        "signal",
        amplitude=FitParameterSpec(12.0, lower=0.0),
        center=FitParameterSpec(4.8, lower=4.0, upper=6.0),
        sigma=FitParameterSpec(0.9, lower=0.2, upper=2.0),
    )

    result = fit_peaks(
        source,
        PeakFitSpec(2.0, 8.0, (component,), background=background),
    )

    mask = (x >= 2.0) & (x <= 8.0)
    assert np.array_equal(result.background, background[mask])
    assert np.max(np.abs(result.residual)) < 1e-8
    assert result.parameters["signal.center"].value == pytest.approx(5.0, abs=1e-7)


def test_ascending_and_descending_storage_give_same_physical_fit() -> None:
    x = np.linspace(-5.0, 5.0, 401)
    y = _gaussian(x, amplitude=9.0, center=-0.35, sigma=0.65)
    component = _gaussian_component(
        "peak",
        amplitude=FitParameterSpec(8.0, lower=0.0),
        center=FitParameterSpec(-0.2, lower=-1.0, upper=1.0),
        sigma=FitParameterSpec(0.8, lower=0.2, upper=1.5),
    )
    spec = PeakFitSpec(-3.5, 3.5, (component,))

    ascending = fit_peaks(_series(x, y, key="ascending"), spec)
    descending = fit_peaks(_series(x[::-1], y[::-1], key="descending"), spec)

    for name in ("amplitude", "center", "sigma"):
        assert descending.parameters[f"peak.{name}"].value == pytest.approx(
            ascending.parameters[f"peak.{name}"].value, rel=1e-7, abs=1e-8
        )
    assert descending.x[0] > descending.x[-1]
    assert ascending.x[0] < ascending.x[-1]


def test_fit_window_uses_only_measured_points_without_interpolation() -> None:
    x = np.array([-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0])
    y = _gaussian(x, amplitude=5.0, center=0.0, sigma=0.8)
    component = _gaussian_component(
        "peak",
        amplitude=FitParameterSpec(4.5, vary=False),
        center=FitParameterSpec(0.0, vary=False),
        sigma=FitParameterSpec(0.8, vary=False),
    )

    result = fit_peaks(_series(x, y), PeakFitSpec(-1.2, 2.2, (component,)))

    assert np.array_equal(result.x, np.array([-1.0, 0.0, 1.0, 2.0]))
    assert result.n_points == 4


def test_component_identity_and_parameter_contract_are_explicit() -> None:
    valid = _gaussian_component(
        "peak_a",
        amplitude=FitParameterSpec(1.0),
        center=FitParameterSpec(0.0),
        sigma=FitParameterSpec(1.0),
    )
    with pytest.raises(PeakFittingError, match="component keys must be unique"):
        PeakFitSpec(-1.0, 1.0, (valid, valid))
    with pytest.raises(PeakFittingError, match="component key"):
        PeakComponentSpec(key="bad-key", model="gaussian", parameters=valid.parameters)
    with pytest.raises(PeakFittingError, match="parameters must be exactly"):
        PeakComponentSpec(
            key="missing",
            model="gaussian",
            parameters={
                "amplitude": FitParameterSpec(1.0),
                "center": FitParameterSpec(0.0),
            },
        )


def test_parameter_bounds_and_expression_state_fail_explicitly() -> None:
    with pytest.raises(PeakFittingError, match="lower bound"):
        FitParameterSpec(1.0, lower=2.0, upper=3.0)
    with pytest.raises(PeakFittingError, match="lower bound must be <="):
        FitParameterSpec(1.0, lower=2.0, upper=0.0)
    with pytest.raises(PeakFittingError, match="requires vary=False"):
        FitParameterSpec(1.0, expr="{other.center}")
    with pytest.raises(PeakFittingError, match="finite"):
        FitParameterSpec(float("nan"))


def test_model_domains_reject_values_that_backend_would_otherwise_clip() -> None:
    x = np.linspace(-2.0, 2.0, 101)
    y = _gaussian(x, amplitude=1.0, center=0.0, sigma=0.5)
    source = _series(x, y)

    bad_sigma = _gaussian_component(
        "bad_sigma",
        amplitude=FitParameterSpec(1.0),
        center=FitParameterSpec(0.0),
        sigma=FitParameterSpec(-1.0),
    )
    with pytest.raises(PeakFittingError, match="sigma"):
        fit_peaks(source, PeakFitSpec(-1.5, 1.5, (bad_sigma,)))

    bad_fraction = PeakComponentSpec(
        key="bad_fraction",
        model="pseudo_voigt",
        parameters={
            "amplitude": FitParameterSpec(1.0),
            "center": FitParameterSpec(0.0),
            "sigma": FitParameterSpec(1.0),
            "fraction": FitParameterSpec(1.2),
        },
    )
    with pytest.raises(PeakFittingError, match="fraction"):
        fit_peaks(source, PeakFitSpec(-1.5, 1.5, (bad_fraction,)))


def test_nonfinite_missing_complex_and_nonmonotonic_input_fail() -> None:
    component = _gaussian_component(
        "peak",
        amplitude=FitParameterSpec(1.0, vary=False),
        center=FitParameterSpec(0.0, vary=False),
        sigma=FitParameterSpec(1.0, vary=False),
    )
    spec = PeakFitSpec(-2.0, 2.0, (component,))

    with pytest.raises(PeakFittingError, match="missing/non-finite y"):
        fit_peaks(_series(np.array([-1.0, 0.0, 1.0]), np.array([1.0, np.nan, 1.0])), spec)

    complex_source = Series(
        x=np.array([-1.0, 0.0, 1.0]),
        y=np.array([1.0 + 1.0j, 2.0 + 0.0j, 1.0 + 0.0j]),
        x_axis=Axis("x"),
        y_axis=Axis("y"),
    )
    with pytest.raises(PeakFittingError, match="real-valued"):
        fit_peaks(complex_source, spec)

    with pytest.raises(PeakFittingError, match="strictly monotonic"):
        fit_peaks(
            _series(
                np.array([-1.0, 0.0, 0.0, 1.0]),
                np.array([1.0, 2.0, 2.0, 1.0]),
            ),
            spec,
        )


def test_bad_unknown_and_circular_expression_references_fail() -> None:
    x = np.linspace(-3.0, 3.0, 101)
    y = _gaussian(x, amplitude=3.0, center=0.0, sigma=0.6)

    unknown = _gaussian_component(
        "a",
        amplitude=FitParameterSpec(3.0, lower=0.0),
        center=FitParameterSpec(0.0, vary=False, expr="{missing.center}"),
        sigma=FitParameterSpec(0.6, lower=0.1),
    )
    with pytest.raises(PeakFittingError, match="unknown parameters"):
        fit_peaks(_series(x, y), PeakFitSpec(-2.0, 2.0, (unknown,)))

    first = _gaussian_component(
        "a",
        amplitude=FitParameterSpec(2.0, lower=0.0),
        center=FitParameterSpec(0.0, vary=False, expr="{b.center}"),
        sigma=FitParameterSpec(0.6, lower=0.1),
    )
    second = _gaussian_component(
        "b",
        amplitude=FitParameterSpec(1.0, lower=0.0),
        center=FitParameterSpec(1.0, vary=False, expr="{a.center}"),
        sigma=FitParameterSpec(0.6, lower=0.1),
    )
    with pytest.raises(PeakFittingError, match="circular dependency"):
        fit_peaks(_series(x, y), PeakFitSpec(-2.0, 2.0, (first, second)))


def test_background_weights_and_point_count_are_validated_against_fit_grid() -> None:
    x = np.linspace(-2.0, 2.0, 101)
    y = _gaussian(x, amplitude=3.0, center=0.0, sigma=0.5)
    component = _gaussian_component(
        "peak",
        amplitude=FitParameterSpec(3.0, vary=False),
        center=FitParameterSpec(0.0, vary=False),
        sigma=FitParameterSpec(0.5, vary=False),
    )

    with pytest.raises(PeakFittingError, match="background must contain exactly"):
        fit_peaks(
            _series(x, y),
            PeakFitSpec(-1.0, 1.0, (component,), background=np.zeros(10)),
        )

    selected = int(np.count_nonzero((x >= -1.0) & (x <= 1.0)))
    with pytest.raises(PeakFittingError, match="weights must contain exactly"):
        fit_peaks(
            _series(x, y),
            PeakFitSpec(-1.0, 1.0, (component,), weights=np.ones(selected - 1)),
        )
    with pytest.raises(PeakFittingError, match="non-negative"):
        PeakFitSpec(-1.0, 1.0, (component,), weights=np.array([1.0, -1.0]))


def test_uncertainty_absence_is_none_and_result_is_deterministic() -> None:
    x = np.linspace(-2.0, 2.0, 101)
    y = _gaussian(x, amplitude=3.0, center=0.0, sigma=0.5)
    component = _gaussian_component(
        "fixed",
        amplitude=FitParameterSpec(3.0, vary=False),
        center=FitParameterSpec(0.0, vary=False),
        sigma=FitParameterSpec(0.5, vary=False),
    )
    spec = PeakFitSpec(-1.5, 1.5, (component,))

    first = fit_peaks(_series(x, y), spec)
    second = fit_peaks(_series(x, y), spec)

    assert first.source_sha256 == second.source_sha256
    assert np.array_equal(first.best_fit_y, second.best_fit_y)
    assert first.covariance is None
    assert first.covariance_parameter_order == ()
    assert all(parameter.stderr is None for parameter in first.parameters.values())
