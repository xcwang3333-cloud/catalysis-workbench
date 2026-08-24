from dataclasses import replace

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
from catalysis_workbench.experimental.echem.rrde import RRDEError, rrde_metrics
from catalysis_workbench.experimental.echem.rrde_plotting import plot_rrde_metric


def _kl_fit():
    rotation = np.array([400.0, 900.0, 1600.0, 2500.0])
    omega = rotation_rate_to_rad_s(rotation, "rpm", allow_nan=False)
    current = 1.0 / (2.0 + 3.0 * omega ** -0.5)
    source = Series(
        x=rotation,
        y=current,
        key="kl-review",
        x_axis=Axis("rotation_rate", unit="rpm"),
        y_axis=Axis(
            "current_density",
            unit="A/cm^2",
            metadata={"normalization": "geometric_area"},
        ),
    )
    return fit_koutecky_levich(
        source,
        (400.0, 2500.0),
        fit_window_unit="rpm",
        current_mode="nonnegative",
    )


def _rrde_result(*, prefix: str, mode: str):
    x_axis = Axis("potential", unit="V", metadata={"reference": "RHE"})
    disk = Series(
        x=[0.8, 0.7, 0.6],
        y=[1.0, 2.0, 3.0],
        key=f"{prefix}-disk",
        label=prefix,
        x_axis=x_axis,
        y_axis=Axis("current", unit="mA"),
    )
    ring = Series(
        x=[0.8, 0.7, 0.6],
        y=[0.1, 0.2, 0.3],
        key=f"{prefix}-ring",
        x_axis=x_axis,
        y_axis=Axis("current", unit="mA"),
    )
    return rrde_metrics(
        disk,
        ring,
        collection_efficiency=0.5,
        current_mode=mode,
    )


def test_rrde_overlay_rejects_mixed_current_modes():
    nonnegative = _rrde_result(prefix="nonnegative", mode="nonnegative")
    magnitude = _rrde_result(prefix="magnitude", mode="magnitude")
    with pytest.raises(RRDEError, match="current_mode"):
        plot_rrde_metric([nonnegative, magnitude])


def test_rrde_potential_condition_requires_supported_unit():
    x_axis = Axis("potential", unit="banana", metadata={"reference": "RHE"})
    disk = Series(
        x=[0.8, 0.7],
        y=[1.0, 2.0],
        key="bad-unit-disk",
        x_axis=x_axis,
        y_axis=Axis("current", unit="mA"),
    )
    ring = Series(
        x=[0.8, 0.7],
        y=[0.1, 0.2],
        key="bad-unit-ring",
        x_axis=x_axis,
        y_axis=Axis("current", unit="mA"),
    )
    with pytest.raises(RRDEError, match="supported potential unit"):
        rrde_metrics(
            disk,
            ring,
            collection_efficiency=0.5,
            current_mode="nonnegative",
        )


def test_kl_public_result_rejects_forged_source_rotation_unit():
    result = _kl_fit()
    forged_source = replace(result.provenance.source, x_unit="Hz")
    forged_provenance = replace(result.provenance, source=forged_source)
    with pytest.raises(KouteckyLevichError, match="source units"):
        replace(result, provenance=forged_provenance)


def test_kl_public_result_rejects_forged_canonical_unit_record():
    result = _kl_fit()
    units = dict(result.provenance.units)
    units["rotation"] = "rpm"
    forged_provenance = replace(
        result.provenance,
        units=tuple(units.items()),
    )
    with pytest.raises(KouteckyLevichError, match="provenance unit"):
        replace(result, provenance=forged_provenance)


def test_kl_public_result_rejects_forged_fit_window_input_unit():
    result = _kl_fit()
    units = dict(result.provenance.units)
    units["fit_window_input"] = "Hz"
    forged_provenance = replace(
        result.provenance,
        units=tuple(units.items()),
    )
    with pytest.raises(KouteckyLevichError, match="fit_window_input"):
        replace(result, provenance=forged_provenance)


def test_kl_derived_electron_number_retains_specific_fit_provenance():
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
    rotation = np.array([400.0, 900.0, 1600.0, 2500.0])
    omega = rotation_rate_to_rad_s(rotation, "rpm", allow_nan=False)
    current = 1.0 / (10.0 + slope * omega ** -0.5)
    source = Series(
        x=rotation,
        y=current,
        key="known-n-review",
        x_axis=Axis("rotation_rate", unit="rpm"),
        y_axis=Axis(
            "current_density",
            unit="A/cm^2",
            metadata={"normalization": "geometric_area"},
        ),
    )
    fit = fit_koutecky_levich(
        source,
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
    assert derived.fit_slope == pytest.approx(fit.slope)
    assert derived.fit_window == fit.fit_window
    assert derived.fit_current_mode == fit.current_mode
    assert derived.fit_source_sha256 == fit.provenance.source.sha256


def test_kl_derived_result_rejects_inconsistent_stored_n():
    fit = _kl_fit()
    derived = kl_electron_number(
        fit,
        diffusion_coefficient_cm2_s=1.9e-5,
        kinematic_viscosity_cm2_s=0.01,
        concentration_mol_cm3=1.2e-6,
    )
    with pytest.raises(KouteckyLevichError, match="contradicts"):
        replace(derived, electron_number=derived.electron_number * 1.1)
