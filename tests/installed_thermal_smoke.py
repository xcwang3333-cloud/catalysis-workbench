"""Smoke the reviewed thermal-analysis public API from an installed wheel."""

from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.characterization import (
    ThermalWindow,
    convert_temperature,
    derive_dtg,
    measure_thermal_window,
    normalize_tga_mass,
    plot_thermal,
)
from catalysis_workbench.visualization import export_figure, get_preset


def _close(actual: float, expected: float, tolerance: float = 1e-10) -> None:
    scale = max(1.0, abs(expected))
    assert abs(actual - expected) <= tolerance * scale, (actual, expected)


def main() -> None:
    tga = Series(
        x=(100.0, 200.0, 300.0, 400.0),
        y=(10.0, 9.0, 8.0, 7.0),
        key="installed-tga",
        x_axis=Axis("temperature", unit="°C"),
        y_axis=Axis("mass", unit="mg"),
    )
    normalized = normalize_tga_mass(tga, output="percent", reference="first_point")
    np.testing.assert_allclose(normalized.y, (100.0, 90.0, 80.0, 70.0))

    dtg = derive_dtg(tga, sign_mode="mass_loss_positive")
    np.testing.assert_allclose(dtg.y, 0.01)
    assert dtg.y_axis.unit == "mg/°C"
    dtg_k = convert_temperature(dtg, target_unit="K")
    np.testing.assert_allclose(dtg_k.y, dtg.y)
    assert dtg_k.x_axis.unit == "K"
    assert dtg_k.y_axis.unit == "mg/K"

    tpr = Series(
        x=(100.0, 200.0, 300.0, 400.0, 500.0),
        y=(0.0, 1.0, 3.0, 1.0, 0.0),
        key="installed-tpr",
        x_axis=Axis("temperature", unit="°C"),
        y_axis=Axis("detector_signal", unit="a.u."),
    )
    measurement = measure_thermal_window(
        tpr,
        ThermalWindow(150.0, 450.0),
        technique="tpr",
        extremum_mode="maximum",
        area_mode="net",
    )
    _close(measurement.extremum_temperature, 300.0)
    _close(measurement.extremum_value, 3.0)
    _close(measurement.area, 475.0)

    spec = get_preset("publication").with_export(dpi=120)
    fig, _ = plot_thermal(tpr, spec, technique="tpr")
    with TemporaryDirectory() as directory:
        path = export_figure(fig, Path(directory) / "thermal.png", spec=spec)
        assert path.is_file() and path.stat().st_size > 0


if __name__ == "__main__":
    main()
