"""Smoke basic EIS fitting and publication plotting from an installed wheel."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.echem import (
    EISCapacitor,
    EISParallelCircuit,
    EISParameterSpec,
    EISResistor,
    EISSeriesCircuit,
    evaluate_eis_circuit,
    fit_eis,
    plot_eis_bode,
    plot_eis_nyquist,
    summarize_eis_fit,
)
from catalysis_workbench.visualization import FigureSpec, export_figure


def resistor(key: str, value: float, *, vary: bool = True) -> EISResistor:
    return EISResistor(key, EISParameterSpec(value, vary=vary, lower=0.0))


def capacitor(key: str, value: float, *, vary: bool = True) -> EISCapacitor:
    return EISCapacitor(key, EISParameterSpec(value, vary=vary, lower=0.0))


frequency = np.logspace(5, 0, 60)
true_circuit = EISSeriesCircuit(
    (
        resistor("rs", 4.0, vary=False),
        EISParallelCircuit(
            (
                resistor("rct", 22.0, vary=False),
                capacitor("cdl", 8.0e-4, vary=False),
            )
        ),
    )
)
impedance = evaluate_eis_circuit(true_circuit, frequency)
source = Series(
    x=frequency,
    y=impedance,
    key="installed-eis",
    label="Installed EIS",
    x_axis=Axis("frequency", unit="Hz"),
    y_axis=Axis("impedance", unit="ohm"),
)
fit_circuit = EISSeriesCircuit(
    (
        resistor("rs", 5.0),
        EISParallelCircuit((resistor("rct", 18.0), capacitor("cdl", 1.0e-3))),
    )
)
result = fit_eis(source, fit_circuit)
assert result.success
assert abs(result.parameters["rs.R"].value - 4.0) < 1e-3
assert abs(result.parameters["rct.R"].value - 22.0) < 1e-3
assert abs(result.parameters["cdl.C"].value - 8.0e-4) < 1e-6
np.testing.assert_allclose(result.best_fit_impedance, impedance, rtol=1e-4, atol=1e-6)
np.testing.assert_array_equal(
    result.residual_impedance,
    np.asarray(source.y) - result.best_fit_impedance,
)

diagnostics = summarize_eis_fit(result)
assert diagnostics.parameter_keys == ("rs.R", "rct.R", "cdl.C")
assert diagnostics.frequency_direction == "descending"

spec = FigureSpec().with_layout(figure_width_in=4.0, figure_height_in=3.0)
nyquist_figure, nyquist_ax = plot_eis_nyquist(source, spec, fit=result)
assert len(nyquist_ax.lines) == 2
bode_figure, bode_axes = plot_eis_bode(source, fit=result)
assert len(bode_axes) == 2
assert bode_axes[0].get_xscale() == "log"

with tempfile.TemporaryDirectory() as directory:
    output = Path(directory) / "eis-nyquist.svg"
    export_figure(nyquist_figure, output, spec=spec)
    assert output.exists() and output.stat().st_size > 0

assert bode_figure is not None
