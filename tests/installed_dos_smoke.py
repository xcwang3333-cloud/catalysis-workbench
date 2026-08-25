from __future__ import annotations

import sys

import numpy as np

from catalysis_workbench.computation import (
    BandCenterError,
    BandCenterResult,
    DOSChannel,
    DOSProcessingError,
    DOSProjection,
    DOSTrace,
    ElectronicDOS,
    ElectronicEnergyAxis,
    aggregate_dos,
    calculate_band_center,
    crop_dos_trace,
    dos_channel_trace,
    dos_trace_frame,
    reference_dos_to_fermi,
    select_dos_channels,
)

assert "matplotlib.pyplot" not in sys.modules

from catalysis_workbench.visualization import (  # noqa: E402
    DOSVisualizationError,
    plot_dos,
)


def main() -> None:
    assert issubclass(DOSProcessingError, ValueError)
    assert issubclass(BandCenterError, ValueError)
    assert issubclass(DOSVisualizationError, ValueError)
    assert DOSTrace.__name__ == "DOSTrace"
    assert BandCenterResult.__name__ == "BandCenterResult"

    energy = ElectronicEnergyAxis(
        (-2.0, 0.0, 2.0, 4.0),
        source_fermi_ev=1.0,
    )
    dos = ElectronicDOS(
        energy=energy,
        channels=(
            DOSChannel(DOSProjection("total", "total"), "up", (1.0, 2.0, 3.0, 4.0)),
            DOSChannel(
                DOSProjection("total", "total"),
                "down",
                (0.5, 1.0, 1.5, 2.0),
            ),
        ),
    )
    selected = select_dos_channels(dos, projection_kind="total", spins=("up", "down"))
    total = aggregate_dos(dos, selected, key="physical-total")
    np.testing.assert_allclose(total.density, [1.5, 3.0, 4.5, 6.0])

    center = calculate_band_center(
        total,
        -2.0,
        4.0,
        denominator_tolerance=1e-12,
    )
    assert center.source_trace_digest == total.digest
    assert center.source_spins == ("up", "down")
    assert center.integration_method == "trapezoid"
    np.testing.assert_allclose(center.center_ev, 26.0 / 15.0, rtol=0.0, atol=1e-12)

    down = dos_channel_trace(dos, projection_key="total", spin="down")
    referenced = reference_dos_to_fermi(down)
    cropped = crop_dos_trace(referenced, -1.0, 2.0)
    np.testing.assert_allclose(cropped.energy.values_ev, [-1.0, 1.0])
    assert list(dos_trace_frame(cropped)["density"]) == [1.0, 1.5]

    before = np.array(referenced.density, copy=True)
    figure, ax = plot_dos(referenced, mirror_spin_down=True, show_fermi=True)
    np.testing.assert_allclose(ax.lines[0].get_ydata(), -before)
    assert float(ax.lines[1].get_xdata()[0]) == 0.0
    np.testing.assert_array_equal(referenced.density, before)
    figure.canvas.draw()
    print("installed v0.6 DOS/band-center processing/plotting smoke: ok")


if __name__ == "__main__":
    main()
