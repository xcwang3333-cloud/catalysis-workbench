"""Minimal TGA -> DTG -> window measurement -> plot -> export example."""

from pathlib import Path

import numpy as np

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.characterization import (
    ThermalAnnotation,
    ThermalWindow,
    derive_dtg,
    measure_thermal_window,
    normalize_tga_mass,
    plot_thermal,
)
from catalysis_workbench.visualization import export_figure, get_preset

HERE = Path(__file__).resolve().parent


def main(output_dir: Path | None = None) -> None:
    output = HERE / "output" if output_dir is None else Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    temperature = np.array([100.0, 200.0, 300.0, 400.0, 500.0])
    mass_mg = np.array([10.0, 9.8, 8.8, 7.8, 7.6])
    raw = Series(
        x=temperature,
        y=mass_mg,
        label="Synthetic TGA",
        key="thermal-example",
        x_axis=Axis("temperature", unit="°C", label="Temperature"),
        y_axis=Axis("mass", unit="mg", label="Mass"),
    )

    normalized = normalize_tga_mass(raw, output="percent", reference="first_point")
    dtg = derive_dtg(normalized, sign_mode="mass_loss_positive")
    window = measure_thermal_window(
        dtg,
        ThermalWindow(150.0, 450.0, "main mass-loss region"),
        technique="dtg",
        extremum_mode="maximum",
        area_mode="net",
    )
    print(
        "DTG maximum = "
        f"{window.extremum_temperature:.1f} {window.temperature_unit}; "
        f"window area = {window.area:.3f} {window.signal_unit}·{window.temperature_unit}"
    )

    spec = get_preset("publication").with_export(dpi=300)
    fig, _ = plot_thermal(
        dtg,
        spec,
        technique="dtg",
        annotations=(
            ThermalAnnotation(window.extremum_temperature, "DTG max", rotation=0.0),
        ),
    )
    for suffix in ("png", "svg", "pdf"):
        export_figure(fig, output / f"thermal_dtg_example.{suffix}", spec=spec)


if __name__ == "__main__":
    main()
