from __future__ import annotations

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.characterization import (
    RamanBand,
    RamanError,
    measure_raman_band,
    plot_raman,
)


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


def test_raman_band_boundary_interpolation_does_not_cross_missing_data():
    source = Series(
        x=(1000.0, 1200.0, 1400.0, 1600.0),
        y=(1.0, np.nan, 3.0, 4.0),
        label="gap",
        key="gap",
        x_axis=Axis("raman_shift", unit="cm^-1", label="Raman shift"),
        y_axis=Axis("intensity", unit="counts", label="Intensity"),
    )

    with pytest.raises(RamanError, match="boundary interpolation crosses missing"):
        measure_raman_band(source, RamanBand(1300.0, 1500.0, "gap"))
