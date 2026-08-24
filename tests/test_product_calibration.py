"""Scientific/API regressions for explicit product calibration and quantification."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.product import (
    CalibrationRange,
    ProductCalibrationError,
    QuantificationFactor,
    fit_calibration,
    plot_calibration,
    quantify_response,
    summarize_quantification_replicates,
)
from catalysis_workbench.visualization import FigureSpec


def _series(
    *,
    quantity: np.ndarray | None = None,
    response: np.ndarray | None = None,
    x_unit: str = "mM",
    y_unit: str = "area",
    metadata: dict[str, object] | None = None,
) -> Series:
    x = (
        np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        if quantity is None
        else np.asarray(quantity)
    )
    y = 2.0 + 3.0 * np.asarray(x, dtype=np.float64) if response is None else response
    return Series(
        x=x,
        y=y,
        key="calibration-source",
        label="Product calibration",
        x_axis=Axis(
            "calibration_quantity",
            unit=x_unit,
            label="Concentration",
        ),
        y_axis=Axis(
            "response",
            unit=y_unit,
            label="Integrated response",
        ),
        metadata={} if metadata is None else metadata,
    )


def test_exact_free_intercept_calibration_recovers_coefficients() -> None:
    result = fit_calibration(_series())
    assert result.slope == pytest.approx(3.0, rel=1e-12)
    assert result.intercept == pytest.approx(2.0, rel=1e-12)
    assert result.r_squared == pytest.approx(1.0, abs=1e-14)
    assert result.slope_stderr == pytest.approx(0.0, abs=1e-14)
    assert result.intercept_stderr == pytest.approx(0.0, abs=1e-14)
    assert result.n_points == 5
    assert result.n_varying_parameters == 2


def test_exact_zero_intercept_calibration_recovers_slope() -> None:
    quantity = np.array([0.0, 1.0, 2.0, 3.0])
    result = fit_calibration(
        _series(quantity=quantity, response=4.0 * quantity),
        intercept_policy="zero",
    )
    assert result.slope == pytest.approx(4.0, rel=1e-12)
    assert result.intercept == 0.0
    assert result.slope_stderr == pytest.approx(0.0, abs=1e-14)
    assert result.intercept_stderr is None
    assert result.n_varying_parameters == 1


def test_calibration_requires_three_observations_and_two_distinct_quantities() -> None:
    with pytest.raises(ProductCalibrationError, match="at least three"):
        fit_calibration(_series(quantity=np.array([0.0, 1.0])))
    with pytest.raises(ProductCalibrationError, match="two distinct"):
        fit_calibration(_series(quantity=np.array([1.0, 1.0, 1.0])))


def test_invalid_calibration_quantity_states_fail_explicitly() -> None:
    with pytest.raises(ProductCalibrationError, match="non-negative"):
        fit_calibration(_series(quantity=np.array([-1.0, 0.0, 1.0])))
    with pytest.raises(ProductCalibrationError, match="finite"):
        fit_calibration(_series(quantity=np.array([0.0, np.nan, 1.0])))
    complex_source = Series(
        x=np.array([0.0 + 0.0j, 1.0 + 0.0j, 2.0 + 0.0j]),
        y=np.array([2.0, 5.0, 8.0]),
        key="complex-calibration",
        x_axis=Axis("calibration_quantity", unit="mM"),
        y_axis=Axis("response", unit="area"),
    )
    with pytest.raises(ProductCalibrationError, match="real numeric"):
        fit_calibration(complex_source)


def test_axis_semantics_and_units_are_explicit() -> None:
    wrong_axis = Series(
        x=np.array([0.0, 1.0, 2.0]),
        y=np.array([2.0, 5.0, 8.0]),
        key="wrong-axis",
        x_axis=Axis("concentration", unit="mM"),
        y_axis=Axis("response", unit="area"),
    )
    with pytest.raises(ProductCalibrationError, match="calibration_quantity"):
        fit_calibration(wrong_axis)
    missing_unit = Series(
        x=np.array([0.0, 1.0, 2.0]),
        y=np.array([2.0, 5.0, 8.0]),
        key="missing-unit",
        x_axis=Axis("calibration_quantity"),
        y_axis=Axis("response", unit="area"),
    )
    with pytest.raises(ProductCalibrationError, match="unit"):
        fit_calibration(missing_unit)


def test_calibration_range_uses_measured_points_and_retains_source_order() -> None:
    quantity = np.array([0.0, 2.0, 1.0, 2.0, 3.0, 4.0])
    result = fit_calibration(
        _series(quantity=quantity),
        calibration_range=CalibrationRange(1.0, 3.0),
    )
    assert result.source_indices == (1, 2, 3, 4)
    np.testing.assert_array_equal(result.quantity, np.array([2.0, 1.0, 2.0, 3.0]))
    np.testing.assert_array_equal(result.fit_line_quantity, np.array([1.0, 3.0]))
    assert np.count_nonzero(result.quantity == 2.0) == 2


def test_calibration_range_requires_three_selected_measured_standards() -> None:
    with pytest.raises(ProductCalibrationError, match="at least three"):
        fit_calibration(
            _series(),
            calibration_range=CalibrationRange(0.0, 1.0),
        )


def test_calibration_rejects_preprocessed_standard_response_state() -> None:
    source = _series(
        metadata={"processing_history": [{"operation": "normalize", "method": "max"}]}
    )
    with pytest.raises(ProductCalibrationError, match="processing_history"):
        fit_calibration(source)


def test_centered_r_squared_and_uncertainty_remain_unavailable_when_undefined() -> None:
    result = fit_calibration(
        _series(response=np.full(5, 7.0)),
    )
    assert result.slope == pytest.approx(0.0, abs=1e-14)
    assert result.r_squared is None
    assert result.slope_stderr is None
    assert result.intercept_stderr is None


def test_calibration_result_arrays_are_immutable_and_source_is_not_mutated() -> None:
    source = _series()
    source_x = np.array(source.x, copy=True)
    source_y = np.array(source.y, copy=True)
    result = fit_calibration(source)
    for array in (
        result.source_quantity,
        result.source_response,
        result.quantity,
        result.response,
        result.best_fit_response,
        result.residual,
        result.fit_line_quantity,
        result.fit_line_response,
    ):
        assert not array.flags.writeable
        with pytest.raises(ValueError):
            array.reshape(-1)[0] = 0.0
    np.testing.assert_array_equal(source.x, source_x)
    np.testing.assert_array_equal(source.y, source_y)


def test_calibration_result_reconstruction_fails_closed() -> None:
    result = fit_calibration(_series())
    with pytest.raises(ProductCalibrationError, match="slope"):
        replace(result, slope=result.slope * 1.1)
    with pytest.raises(ProductCalibrationError, match="best-fit"):
        replace(result, best_fit_response=result.best_fit_response + 1.0)
    with pytest.raises(ProductCalibrationError, match="residual"):
        replace(result, residual=result.residual + 1.0)
    with pytest.raises(ProductCalibrationError, match="source_sha256"):
        replace(result, source_sha256="0" * 64)
    with pytest.raises(ProductCalibrationError, match="source_sha256"):
        replace(result, x_unit="umol")


def test_inverse_quantification_recovers_exact_quantity_and_scalar_shape() -> None:
    calibration = fit_calibration(_series())
    result = quantify_response(calibration, 8.0, response_unit="area")
    assert np.asarray(result.quantity).shape == ()
    assert result.quantity.item() == pytest.approx(2.0, rel=1e-12)
    assert result.raw_quantity.item() == pytest.approx(2.0, rel=1e-12)
    assert np.asarray(result.extrapolated).shape == ()
    assert not bool(result.extrapolated.item())
    assert result.quantity_unit == "mM"


def test_quantification_response_unit_must_match_exactly() -> None:
    calibration = fit_calibration(_series())
    with pytest.raises(ProductCalibrationError, match="exactly match"):
        quantify_response(calibration, 8.0, response_unit="a.u.")


def test_zero_slope_calibration_cannot_be_inverted() -> None:
    calibration = fit_calibration(_series(response=np.full(5, 7.0)))
    with pytest.raises(ProductCalibrationError, match="non-zero"):
        quantify_response(calibration, 7.0, response_unit="area")


def test_named_dimensionless_factors_apply_exactly_and_retain_order() -> None:
    calibration = fit_calibration(_series())
    factors = (
        QuantificationFactor("dilution", 2.0),
        QuantificationFactor("aliquot_scale", 3.0),
    )
    result = quantify_response(
        calibration,
        8.0,
        response_unit="area",
        factors=factors,
    )
    assert result.raw_quantity.item() == pytest.approx(2.0)
    assert result.quantity.item() == pytest.approx(12.0)
    assert result.factor_multiplier == pytest.approx(6.0)
    assert tuple(factor.key for factor in result.factors) == (
        "dilution",
        "aliquot_scale",
    )


@pytest.mark.parametrize("value", [0.0, -1.0, np.nan, np.inf])
def test_invalid_quantification_factor_values_fail(value: float) -> None:
    with pytest.raises(ProductCalibrationError):
        QuantificationFactor("factor", value)


def test_duplicate_quantification_factor_keys_fail() -> None:
    calibration = fit_calibration(_series())
    with pytest.raises(ProductCalibrationError, match="duplicate"):
        quantify_response(
            calibration,
            8.0,
            response_unit="area",
            factors=(
                QuantificationFactor("dilution", 2.0),
                QuantificationFactor("dilution", 3.0),
            ),
        )


def test_extrapolation_is_rejected_by_default_and_explicit_when_allowed() -> None:
    calibration = fit_calibration(_series())
    with pytest.raises(ProductCalibrationError, match="extrapolate"):
        quantify_response(calibration, 17.0, response_unit="area")
    result = quantify_response(
        calibration,
        17.0,
        response_unit="area",
        allow_extrapolation=True,
    )
    assert result.quantity.item() == pytest.approx(5.0)
    assert bool(result.extrapolated.item())


def test_negative_inverse_quantity_fails_without_clipping() -> None:
    calibration = fit_calibration(_series())
    with pytest.raises(ProductCalibrationError, match="negative quantity"):
        quantify_response(calibration, 1.0, response_unit="area")


def test_vector_quantification_preserves_input_shape() -> None:
    calibration = fit_calibration(_series())
    response = np.array([[2.0, 5.0], [8.0, 11.0]])
    result = quantify_response(calibration, response, response_unit="area")
    assert result.quantity.shape == (2, 2)
    np.testing.assert_allclose(result.quantity, np.array([[0.0, 1.0], [2.0, 3.0]]))
    assert result.extrapolated.shape == (2, 2)


def test_quantification_result_reconstruction_fails_closed() -> None:
    result = quantify_response(
        fit_calibration(_series()),
        np.array([5.0, 8.0]),
        response_unit="area",
    )
    with pytest.raises(ProductCalibrationError, match="raw_quantity"):
        replace(result, raw_quantity=result.raw_quantity + 1.0)
    with pytest.raises(ProductCalibrationError, match="quantity"):
        replace(result, quantity=result.quantity + 1.0)
    with pytest.raises(ProductCalibrationError, match="extrapolation"):
        replace(result, extrapolated=np.logical_not(result.extrapolated))


def test_replicate_summary_is_explicit_and_uses_sample_standard_deviation() -> None:
    calibration = fit_calibration(_series())
    quantified = quantify_response(
        calibration,
        np.array([5.0, 8.0, 11.0]),
        response_unit="area",
    )
    summary = summarize_quantification_replicates(quantified)
    assert summary.n == 3
    assert summary.mean == pytest.approx(2.0)
    assert summary.sample_std == pytest.approx(1.0)
    assert summary.rsd_percent == pytest.approx(50.0)
    assert summary.quantity_unit == "mM"


def test_single_replicate_summary_does_not_fabricate_uncertainty() -> None:
    quantified = quantify_response(
        fit_calibration(_series()),
        8.0,
        response_unit="area",
    )
    summary = summarize_quantification_replicates(quantified)
    assert summary.n == 1
    assert summary.mean == pytest.approx(2.0)
    assert summary.sample_std is None
    assert summary.rsd_percent is None


def test_calibration_plot_uses_retained_arrays_and_figure_spec() -> None:
    result = fit_calibration(_series())
    spec = (
        FigureSpec(xlim=(0.0, 5.0), ylim=(0.0, 20.0))
        .with_series_style("calibration_fit", line_width=2.5)
        .with_series_style("calibration_observed", marker_size=5.0)
    )
    _, ax = plot_calibration(result, spec)
    observed = next(line for line in ax.lines if line.get_label() == "Standards")
    fitted = next(line for line in ax.lines if line.get_label() == "Linear fit")
    np.testing.assert_array_equal(observed.get_xdata(), result.quantity)
    np.testing.assert_array_equal(observed.get_ydata(), result.response)
    np.testing.assert_array_equal(fitted.get_xdata(), result.fit_line_quantity)
    np.testing.assert_array_equal(fitted.get_ydata(), result.fit_line_response)
    assert fitted.get_linewidth() == pytest.approx(2.5)
    assert observed.get_markersize() == pytest.approx(5.0)
    assert ax.get_xlim() == pytest.approx((0.0, 5.0))
    assert ax.get_ylim() == pytest.approx((0.0, 20.0))


def test_importing_product_public_api_keeps_matplotlib_lazy() -> None:
    code = r"""
import json
import sys
import catalysis_workbench.experimental.product as product
loaded = any(name == "matplotlib" or name.startswith("matplotlib.") for name in sys.modules)
print(json.dumps({
    "matplotlib": loaded,
    "fit": "fit_calibration" in product.__all__,
    "plot": "plot_calibration" in product.__all__,
}))
"""
    completed = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout.strip())
    assert payload == {"matplotlib": False, "fit": True, "plot": True}
