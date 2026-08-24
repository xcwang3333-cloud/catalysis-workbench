from __future__ import annotations

import numpy as np

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.characterization import convert_temperature, derive_dtg


def test_temperature_conversion_updates_dtg_denominator_without_rescaling_values():
    tga = Series(
        x=(100.0, 200.0, 300.0, 400.0),
        y=(10.0, 9.0, 8.0, 7.0),
        key="sample",
        x_axis=Axis("temperature", unit="°C"),
        y_axis=Axis("mass", unit="mg"),
    )
    dtg_c = derive_dtg(tga, sign_mode="mass_loss_positive")
    dtg_k = convert_temperature(dtg_c, target_unit="K")

    np.testing.assert_allclose(dtg_k.x, np.asarray(dtg_c.x) + 273.15)
    np.testing.assert_allclose(dtg_k.y, dtg_c.y)
    assert dtg_k.x_axis.unit == "K"
    assert dtg_k.y_axis.unit == "mg/K"
    assert dtg_k.y_axis.metadata["dtg_sign_mode"] == "mass_loss_positive"
    assert dtg_k.y_axis.metadata["temperature_denominator_conversion"] == "°C->K"
