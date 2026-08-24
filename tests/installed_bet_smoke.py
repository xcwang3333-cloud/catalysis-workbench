"""Installed-wheel smoke for the reviewed quantitative BET public surface."""

from __future__ import annotations

from tempfile import TemporaryDirectory
from pathlib import Path

import numpy as np

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.characterization import (
    SorptionCondition,
    SorptionWindow,
    fit_bet,
    plot_bet_fit,
    prepare_sorption_series,
    summarize_bet_fit,
)
from catalysis_workbench.visualization import FigureSpec, export_figure

pressure = np.array([0.01, 0.03, 0.05, 0.08, 0.12, 0.18])
c_constant = 100.0
n_monolayer = 1.0
loading = (
    n_monolayer
    * c_constant
    * pressure
    / ((1.0 - pressure) * (1.0 + (c_constant - 1.0) * pressure))
)
raw = Series(
    x=pressure,
    y=loading,
    key="installed-bet",
    label="Installed BET",
    x_axis=Axis("relative_pressure", unit="1"),
    y_axis=Axis("adsorbed_quantity", unit="mmol/g"),
)
prepared = prepare_sorption_series(
    raw,
    SorptionCondition("N2", 77.0, "adsorption"),
)
result = fit_bet(
    prepared,
    SorptionWindow(0.01, 0.18, "BET region"),
    cross_section_nm2=0.162,
)
assert abs(result.c_constant - 100.0) < 1.0e-8
assert abs(result.n_monolayer_source - 1.0) < 1.0e-10
assert result.evaluation.consistency.all_passed
assert result.surface_area_m2_g > 0.0
assert summarize_bet_fit(result).n_points == pressure.size

spec = FigureSpec()
figure, axes = plot_bet_fit(result, spec)
assert len(axes.lines) == 2
with TemporaryDirectory() as directory:
    output = Path(directory) / "bet.svg"
    export_figure(figure, output, spec=spec)
    assert output.exists() and output.stat().st_size > 0

print("installed quantitative BET smoke: ok")
