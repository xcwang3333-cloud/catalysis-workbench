"""Minimal FTIR baseline -> band measurement -> plot -> export example."""

from pathlib import Path

import numpy as np

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.characterization import (
    FTIRBand,
    FTIRPeakAnnotation,
    fit_ftir_baseline,
    measure_ftir_band,
    plot_ftir,
    subtract_ftir_baseline,
)
from catalysis_workbench.visualization import export_figure, get_preset

HERE = Path(__file__).resolve().parent


def main(output_dir: Path | None = None) -> None:
    output = HERE / "output" if output_dir is None else Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    wavenumber = np.array([2000.0, 1800.0, 1600.0, 1400.0, 1200.0, 1000.0])
    linear_baseline = 0.001 * wavenumber + 0.2
    absorbance = linear_baseline + np.array([0.0, 0.0, 2.0, 1.0, 0.0, 0.0])
    raw = Series(
        x=wavenumber,
        y=absorbance,
        label="Synthetic ATR-FTIR",
        key="ftir-example",
        x_axis=Axis("wavenumber", unit="cm^-1", label="Wavenumber"),
        y_axis=Axis("absorbance", label="Absorbance"),
    )

    baseline = fit_ftir_baseline(
        raw,
        ((1000.0, 1200.0), (1800.0, 2000.0)),
        degree=1,
    )
    corrected = subtract_ftir_baseline(raw, baseline)
    band = measure_ftir_band(corrected, FTIRBand(1200.0, 1800.0, "demo band"))
    print(f"Integrated absorbance = {band.area:.1f} absorbance·cm^-1")

    spec = get_preset("publication").with_export(dpi=300)
    fig, _ = plot_ftir(
        corrected,
        spec,
        peak_annotations=(FTIRPeakAnnotation(1600.0, "demo band"),),
        wavenumber_direction="descending",
    )
    for suffix in ("png", "svg", "pdf"):
        export_figure(fig, output / f"ftir_example.{suffix}", spec=spec)


if __name__ == "__main__":
    main()
