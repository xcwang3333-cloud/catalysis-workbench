import matplotlib
import numpy as np
import pytest

matplotlib.use("Agg")

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.echem.koutecky_levich import (
    KouteckyLevichError,
    fit_koutecky_levich,
)
from catalysis_workbench.experimental.echem.koutecky_levich_plotting import (
    plot_koutecky_levich,
)
from catalysis_workbench.experimental.echem.quantities import rotation_rate_to_rad_s
from catalysis_workbench.experimental.echem.rrde import rrde_metrics
from catalysis_workbench.experimental.echem.rrde_plotting import plot_rrde_metric


def _rrde_result():
    x_axis = Axis("potential", unit="V", metadata={"reference": "RHE"})
    disk = Series(
        x=[0.8, 0.7, 0.6],
        y=[-1.0, -2.0, -3.0],
        key="disk",
        label="sample",
        x_axis=x_axis,
        y_axis=Axis("current", unit="mA"),
    )
    ring = Series(
        x=[0.8, 0.7, 0.6],
        y=[0.1, 0.2, 0.3],
        key="ring",
        x_axis=x_axis,
        y_axis=Axis("current", unit="mA"),
    )
    return rrde_metrics(
        disk,
        ring,
        collection_efficiency=0.5,
        current_mode="magnitude",
    )


def _kl_result(*, key="kl", current_mode="nonnegative", current_density=True):
    rotation = np.array([400.0, 900.0, 1600.0, 2500.0])
    omega = rotation_rate_to_rad_s(rotation, "rpm", allow_nan=False)
    reciprocal = 2.0 + 3.0 * omega ** -0.5
    current = 1.0 / reciprocal
    if current_density:
        y_axis = Axis(
            "current_density",
            unit="A/cm^2",
            metadata={"normalization": "geometric_area"},
        )
    else:
        y_axis = Axis("current", unit="A")
    series = Series(
        x=rotation,
        y=current,
        key=key,
        label=key,
        x_axis=Axis("rotation_rate", unit="rpm"),
        y_axis=y_axis,
    )
    return fit_koutecky_levich(
        series,
        (400.0, 2500.0),
        fit_window_unit="rpm",
        current_mode=current_mode,
    )


def test_plot_rrde_metric_uses_already_calculated_series():
    result = _rrde_result()
    figure, axes = plot_rrde_metric(result, metric="electron_number")
    assert len(axes.lines) == 1
    np.testing.assert_allclose(axes.lines[0].get_ydata(), result.electron_number)
    figure.clear()


def test_plot_koutecky_levich_renders_points_and_stored_fit():
    result = _kl_result()
    figure, axes = plot_koutecky_levich(result)
    assert len(axes.lines) == 2
    plotted = sorted(
        (np.asarray(line.get_xdata()), np.asarray(line.get_ydata()))
        for line in axes.lines
    )
    assert any(
        np.allclose(y, result.reciprocal_current)
        for _, y in plotted
    )
    assert any(
        np.allclose(np.sort(y), np.sort(result.fitted_reciprocal_current))
        for _, y in plotted
    )
    figure.clear()


def test_kl_overlay_rejects_incompatible_current_basis_and_mode():
    density = _kl_result(key="density")
    total = _kl_result(key="total", current_density=False)
    with pytest.raises(KouteckyLevichError, match="basis"):
        plot_koutecky_levich([density, total])

    signed_source = _kl_result(key="signed", current_mode="signed")
    with pytest.raises(KouteckyLevichError, match="current_mode"):
        plot_koutecky_levich([density, signed_source])
