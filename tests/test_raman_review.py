from __future__ import annotations

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.characterization import plot_raman


def test_plot_raman_normalized_semantic_controls_automatic_ylabel():
    source = Series(
        x=(1000.0, 1200.0, 1400.0, 1600.0),
        y=(0.1, 0.5, 0.3, 1.0),
        label="normalized",
        key="normalized",
        x_axis=Axis("raman_shift", unit="cm^-1", label="Raman shift"),
        y_axis=Axis(
            "normalized_intensity",
            unit="a.u.",
            label="Intensity",
        ),
    )

    _, ax = plot_raman(source)

    assert ax.get_ylabel() == "Normalized intensity (a.u.)"
