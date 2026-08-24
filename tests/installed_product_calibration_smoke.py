"""Installed-wheel smoke for the reviewed product calibration public surface."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.product import (
    QuantificationFactor,
    fit_calibration,
    plot_calibration,
    quantify_response,
    summarize_quantification_replicates,
)
from catalysis_workbench.visualization import FigureSpec, export_figure

quantity = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
response = 100.0 + 50.0 * quantity
standards = Series(
    x=quantity,
    y=response,
    key="installed-product-calibration",
    label="Installed calibration",
    x_axis=Axis("calibration_quantity", unit="umol", label="Product amount"),
    y_axis=Axis("response", unit="area", label="Peak area"),
)
calibration = fit_calibration(standards)
assert abs(calibration.slope - 50.0) < 1.0e-10
assert abs(calibration.intercept - 100.0) < 1.0e-10
assert calibration.r_squared == 1.0

quantified = quantify_response(
    calibration,
    np.array([200.0, 250.0]),
    response_unit="area",
    factors=(QuantificationFactor("dilution", 2.0),),
)
np.testing.assert_allclose(quantified.raw_quantity, np.array([2.0, 3.0]))
np.testing.assert_allclose(quantified.quantity, np.array([4.0, 6.0]))
summary = summarize_quantification_replicates(quantified)
assert summary.n == 2
assert abs(summary.mean - 5.0) < 1.0e-12
assert summary.sample_std is not None
assert summary.quantity_unit == "umol"

spec = FigureSpec()
figure, axes = plot_calibration(calibration, spec)
assert len(axes.lines) == 2
with TemporaryDirectory() as directory:
    output = Path(directory) / "product-calibration.svg"
    export_figure(figure, output, spec=spec)
    assert output.exists() and output.stat().st_size > 0

print("installed product calibration smoke: ok")
