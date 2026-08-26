"""Installed-wheel smoke for v0.8 Block-4 Raman/FTIR operando consumers."""

from __future__ import annotations

import numpy as np

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.characterization import FTIRBand, RamanBand
from catalysis_workbench.experimental.operando import (
    FrameCoordinate,
    build_ftir_operando_stack,
    build_raman_operando_stack,
    fit_component_center_trace,
    fit_component_fwhm_trace,
    ftir_band_area_trace,
    plot_operando_heatmap,
    plot_operando_waterfall,
    raman_band_area_trace,
    raman_peak_position_trace,
)
from catalysis_workbench.processing import (
    FitParameterSpec,
    PeakComponentSpec,
    PeakFitSpec,
    fit_peaks,
)


def _gaussian(x: np.ndarray, center: float, sigma: float) -> np.ndarray:
    return 500.0 / (sigma * np.sqrt(2.0 * np.pi)) * np.exp(
        -((x - center) ** 2) / (2.0 * sigma**2)
    )


def main() -> None:
    coordinates = (
        FrameCoordinate("time", Axis("time", unit="s"), [0.0, 10.0, 20.0]),
        FrameCoordinate(
            "potential",
            Axis("potential", unit="V", metadata={"reference": "RHE"}),
            [-0.5, -0.7, -0.5],
        ),
    )
    x = np.linspace(900.0, 1300.0, 201)
    raman_frames = tuple(
        Series(
            x,
            _gaussian(x, center, sigma),
            key=f"r-{index}",
            x_axis=Axis("raman_shift", unit="cm^-1"),
            y_axis=Axis(
                "intensity",
                unit="counts",
                metadata={"processing_basis": "raw"},
            ),
        )
        for index, (center, sigma) in enumerate(
            ((1080.0, 20.0), (1100.0, 24.0), (1120.0, 28.0))
        )
    )
    raman = build_raman_operando_stack(
        raman_frames,
        frame_coordinates=coordinates,
        primary_coordinate_key="time",
    )
    before = raman.digest
    band = RamanBand(1020.0, 1180.0, label="explicit band")
    area = raman_band_area_trace(raman, band, coordinate_key="potential")
    position = raman_peak_position_trace(raman, band, coordinate_key="potential")
    assert area.n_frames == position.n_frames == 3
    np.testing.assert_array_equal(position.coordinate.values, [-0.5, -0.7, -0.5])

    component = PeakComponentSpec(
        key="band",
        model="gaussian",
        parameters={
            "amplitude": FitParameterSpec(450.0, lower=0.0),
            "center": FitParameterSpec(1100.0, lower=1000.0, upper=1200.0),
            "sigma": FitParameterSpec(25.0, lower=5.0, upper=60.0),
        },
    )
    spec = PeakFitSpec(980.0, 1220.0, (component,))
    fit_results = tuple(fit_peaks(frame, spec) for frame in raman_frames)
    centers = fit_component_center_trace(
        raman,
        fit_results,
        coordinate_key="time",
        component_key="band",
        technique="raman",
    )
    widths = fit_component_fwhm_trace(
        raman,
        fit_results,
        coordinate_key="time",
        component_key="band",
        technique="raman",
    )
    np.testing.assert_allclose(centers.values, [1080.0, 1100.0, 1120.0], atol=1e-5)
    assert np.all(widths.values > 0.0)

    waterfall, waterfall_ax = plot_operando_waterfall(raman, offset_step=1.0)
    assert waterfall.canvas is not None and len(waterfall_ax.lines) == 3
    heatmap, heatmap_ax = plot_operando_heatmap(
        raman,
        coordinate_key="potential",
        frame_geometry="ordinal",
        value_limits=(0.0, float(np.max(raman.values))),
        colormap="viridis",
        show_colorbar=False,
    )
    assert heatmap.canvas is not None and len(heatmap_ax.collections) == 1
    assert raman.digest == before

    wn = np.array([1800.0, 1700.0, 1600.0, 1500.0, 1400.0])
    ftir_frames = tuple(
        Series(
            wn,
            row,
            key=f"f-{index}",
            x_axis=Axis("wavenumber", unit="cm^-1"),
            y_axis=Axis("absorbance", metadata={"processing_basis": "raw"}),
        )
        for index, row in enumerate(
            (
                [0.0, 1.0, 5.0, 2.0, 0.0],
                [0.0, 2.0, 4.0, 6.0, 1.0],
                [0.0, 3.0, 7.0, 1.0, 0.0],
            )
        )
    )
    ftir = build_ftir_operando_stack(
        ftir_frames,
        frame_coordinates=coordinates,
        primary_coordinate_key="time",
    )
    ftir_area = ftir_band_area_trace(
        ftir,
        FTIRBand(1450.0, 1750.0),
        coordinate_key="time",
    )
    assert ftir.signal_direction == "decreasing"
    assert ftir_area.n_frames == 3

    print("installed v0.8 Block-4 Raman/FTIR operando smoke: ok")


if __name__ == "__main__":
    main()
