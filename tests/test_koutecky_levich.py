import numpy as np
import pytest

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.echem.koutecky_levich import (
    KouteckyLevichError,
    fit_koutecky_levich,
    kl_electron_number,
)
from catalysis_workbench.experimental.echem.quantities import (
    FARADAY_CONSTANT_C_MOL,
    rotation_rate_to_rad_s,
)


def _kl_series(
    *,
    rotation=(400.0, 900.0, 1600.0, 2500.0),
    rotation_unit="rpm",
    slope=3.0,
    intercept=2.0,
    negative=False,
    current_density=True,
    key="sample",
):
    omega = rotation_rate_to_rad_s(rotation, rotation_unit, allow_nan=False)
    reciprocal = intercept + slope * omega ** -0.5
    current = 1.0 / reciprocal
    if negative:
        current = -current
    if current_density:
        y_axis = Axis(
            "current_density",
            unit="A/cm^2",
            metadata={"normalization": "geometric_area"},
        )
    else:
        y_axis = Axis("current", unit="A")
    return Series(
        x=rotation,
        y=current,
        key=key,
        label="sample",
        x_axis=Axis("rotation_rate", unit=rotation_unit),
        y_axis=y_axis,
    )


def test_kl_recovers_hand_constructed_linear_fit():
    series = _kl_series()
    result = fit_koutecky_levich(
        series,
        (400.0, 2500.0),
        fit_window_unit="rpm",
        current_mode="nonnegative",
    )
    assert result.slope == pytest.approx(3.0)
    assert result.intercept == pytest.approx(2.0)
    assert result.r_squared == pytest.approx(1.0)
    assert result.current_basis == "current_density"
    assert result.normalization == "geometric_area"
    assert result.fit_window.unit == "rad/s"
    assert result.n_points == 4


def test_kl_rpm_and_rad_s_inputs_are_canonically_equivalent():
    rpm = np.array([400.0, 900.0, 1600.0, 2500.0])
    omega = rotation_rate_to_rad_s(rpm, "rpm", allow_nan=False)
    rpm_series = _kl_series(rotation=tuple(rpm), rotation_unit="rpm")
    rad_series = _kl_series(
        rotation=tuple(omega),
        rotation_unit="rad/s",
        key="sample-rad",
    )
    fit_rpm = fit_koutecky_levich(
        rpm_series,
        (400.0, 2500.0),
        fit_window_unit="rpm",
        current_mode="nonnegative",
    )
    fit_rad = fit_koutecky_levich(
        rad_series,
        (float(omega[0]), float(omega[-1])),
        fit_window_unit="rad/s",
        current_mode="nonnegative",
    )
    np.testing.assert_allclose(fit_rpm.rotation_rad_s, fit_rad.rotation_rad_s)
    assert fit_rpm.slope == pytest.approx(fit_rad.slope)
    assert fit_rpm.intercept == pytest.approx(fit_rad.intercept)


def test_kl_signed_and_magnitude_modes_are_explicit():
    series = _kl_series(negative=True)
    signed = fit_koutecky_levich(
        series,
        (400.0, 2500.0),
        fit_window_unit="rpm",
        current_mode="signed",
    )
    magnitude = fit_koutecky_levich(
        series,
        (400.0, 2500.0),
        fit_window_unit="rpm",
        current_mode="magnitude",
    )
    assert signed.slope == pytest.approx(-3.0)
    assert signed.intercept == pytest.approx(-2.0)
    assert magnitude.slope == pytest.approx(3.0)
    assert magnitude.intercept == pytest.approx(2.0)
    with pytest.raises(KouteckyLevichError, match="magnitude or nonnegative"):
        kl_electron_number(
            signed,
            diffusion_coefficient_cm2_s=1.9e-5,
            kinematic_viscosity_cm2_s=0.01,
            concentration_mol_cm3=1.2e-6,
        )


def test_kl_apparent_electron_number_recovers_known_value():
    n_true = 4.0
    diffusion = 1.9e-5
    viscosity = 0.01
    concentration = 1.2e-6
    transport = (
        0.62
        * FARADAY_CONSTANT_C_MOL
        * diffusion ** (2.0 / 3.0)
        * viscosity ** (-1.0 / 6.0)
        * concentration
    )
    slope = 1.0 / (n_true * transport)
    series = _kl_series(slope=slope, intercept=10.0)
    fit = fit_koutecky_levich(
        series,
        (400.0, 2500.0),
        fit_window_unit="rpm",
        current_mode="nonnegative",
    )
    derived = kl_electron_number(
        fit,
        diffusion_coefficient_cm2_s=diffusion,
        kinematic_viscosity_cm2_s=viscosity,
        concentration_mol_cm3=concentration,
    )
    assert derived.electron_number == pytest.approx(n_true)
    assert derived.faraday_constant_c_mol == FARADAY_CONSTANT_C_MOL
    assert derived.electrode_area_cm2 is None


def test_kl_total_current_electron_number_requires_area():
    area = 0.196
    n_true = 4.0
    diffusion = 1.9e-5
    viscosity = 0.01
    concentration = 1.2e-6
    transport = (
        0.62
        * FARADAY_CONSTANT_C_MOL
        * area
        * diffusion ** (2.0 / 3.0)
        * viscosity ** (-1.0 / 6.0)
        * concentration
    )
    slope = 1.0 / (n_true * transport)
    series = _kl_series(
        slope=slope,
        intercept=20.0,
        current_density=False,
    )
    fit = fit_koutecky_levich(
        series,
        (400.0, 2500.0),
        fit_window_unit="rpm",
        current_mode="nonnegative",
    )
    with pytest.raises(KouteckyLevichError, match="electrode_area_cm2"):
        kl_electron_number(
            fit,
            diffusion_coefficient_cm2_s=diffusion,
            kinematic_viscosity_cm2_s=viscosity,
            concentration_mol_cm3=concentration,
        )
    derived = kl_electron_number(
        fit,
        diffusion_coefficient_cm2_s=diffusion,
        kinematic_viscosity_cm2_s=viscosity,
        concentration_mol_cm3=concentration,
        electrode_area_cm2=area,
    )
    assert derived.electron_number == pytest.approx(n_true)


def test_kl_current_density_rejects_non_geometric_normalization():
    series = _kl_series()
    bad = Series(
        x=series.x,
        y=series.y,
        key=series.key,
        x_axis=series.x_axis,
        y_axis=Axis(
            "current_density",
            unit="A/cm^2",
            metadata={"normalization": "ecsa"},
        ),
    )
    with pytest.raises(KouteckyLevichError, match="geometric-area"):
        fit_koutecky_levich(
            bad,
            (400.0, 2500.0),
            fit_window_unit="rpm",
            current_mode="nonnegative",
        )


def test_kl_rejects_zero_current_and_nonpositive_selected_rotation():
    series = _kl_series()
    zero = Series(
        x=series.x,
        y=[series.y[0], 0.0, series.y[2], series.y[3]],
        key="zero",
        x_axis=series.x_axis,
        y_axis=series.y_axis,
    )
    with pytest.raises(KouteckyLevichError, match="non-zero"):
        fit_koutecky_levich(
            zero,
            (400.0, 2500.0),
            fit_window_unit="rpm",
            current_mode="nonnegative",
        )

    bad_rotation = Series(
        x=[0.0, 400.0, 900.0, 1600.0],
        y=[0.1, 0.2, 0.3, 0.4],
        key="rot",
        x_axis=Axis("rotation_rate", unit="rpm"),
        y_axis=series.y_axis,
    )
    with pytest.raises(KouteckyLevichError, match="greater than zero"):
        fit_koutecky_levich(
            bad_rotation,
            (0.0, 1600.0),
            fit_window_unit="rpm",
            current_mode="nonnegative",
        )


def test_kl_requires_three_points_supported_units_and_stable_key():
    series = _kl_series()
    with pytest.raises(KouteckyLevichError, match="at least three"):
        fit_koutecky_levich(
            series,
            (900.0, 1600.0),
            fit_window_unit="rpm",
            current_mode="nonnegative",
        )

    bad_unit = Series(
        x=series.x,
        y=series.y,
        key="bad-unit",
        x_axis=Axis("rotation_rate", unit="Hz"),
        y_axis=series.y_axis,
    )
    with pytest.raises(KouteckyLevichError, match="unsupported rotation rate unit"):
        fit_koutecky_levich(
            bad_unit,
            (400.0, 2500.0),
            fit_window_unit="rpm",
            current_mode="nonnegative",
        )

    missing_key = Series(
        x=series.x,
        y=series.y,
        x_axis=series.x_axis,
        y_axis=series.y_axis,
    )
    with pytest.raises(KouteckyLevichError, match="stable Series.key"):
        fit_koutecky_levich(
            missing_key,
            (400.0, 2500.0),
            fit_window_unit="rpm",
            current_mode="nonnegative",
        )
