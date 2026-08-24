"""Smoke the reviewed gas-sorption public API from an installed wheel."""

from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.experimental.characterization import (
    SorptionCondition,
    SorptionWindow,
    convert_relative_pressure,
    plot_sorption,
    prepare_sorption_series,
    summarize_sorption_window,
)
from catalysis_workbench.visualization import export_figure, get_preset


def main() -> None:
    adsorption = prepare_sorption_series(
        Series(
            x=(0.01, 0.10, 0.50, 0.90),
            y=(0.2, 1.0, 3.0, 5.0),
            key="installed-ads",
            x_axis=Axis("relative_pressure", unit="1"),
            y_axis=Axis("adsorbed_quantity", unit="mmol/g"),
        ),
        SorptionCondition("N2", 77.0, "adsorption"),
    )
    percent = convert_relative_pressure(adsorption, target_unit="percent")
    np.testing.assert_allclose(percent.x, (1.0, 10.0, 50.0, 90.0))
    assert percent.x_axis.unit == "%"

    summary = summarize_sorption_window(
        adsorption,
        SorptionWindow(0.05, 0.80),
    )
    assert summary.n_measured_points == 2
    assert summary.minimum_loading == 1.0
    assert summary.maximum_loading == 3.0

    desorption = prepare_sorption_series(
        Series(
            x=(0.90, 0.50, 0.10, 0.01),
            y=(5.2, 3.4, 1.2, 0.3),
            key="installed-des",
            x_axis=Axis("relative_pressure", unit="1"),
            y_axis=Axis("adsorbed_quantity", unit="mmol/g"),
        ),
        SorptionCondition("N2", 77.0, "desorption"),
    )
    spec = get_preset("publication").with_export(dpi=120)
    fig, ax = plot_sorption(Dataset(series=(adsorption, desorption)), spec)
    assert len(ax.lines) == 2
    assert ax.lines[0].get_linestyle() == "-"
    assert ax.lines[1].get_linestyle() == "--"
    with TemporaryDirectory() as directory:
        path = export_figure(fig, Path(directory) / "sorption.png", spec=spec)
        assert path.is_file() and path.stat().st_size > 0


if __name__ == "__main__":
    main()
