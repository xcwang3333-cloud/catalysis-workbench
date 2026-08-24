"""Smoke the XPS preparation API from an installed wheel."""

from __future__ import annotations

import sys

import numpy as np

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.characterization import (
    linear_xps_background,
    prepare_xps_region,
    shift_xps_binding_energy,
    shirley_xps_background,
    validate_xps_series,
)

assert not any(name == "matplotlib" or name.startswith("matplotlib.") for name in sys.modules)

x = np.linspace(0.0, 10.0, 101)
peak = 5.0 * np.exp(-((x - 5.0) ** 2) / (2.0 * 0.8**2))
y = 2.0 + peak
y[0] = 2.0
y[-1] = 2.0
source = Series(
    x=x[::-1],
    y=y[::-1],
    key="installed-xps",
    label="Installed XPS smoke",
    x_axis=Axis("binding_energy", unit="eV", label="Binding energy"),
    y_axis=Axis("intensity", unit="counts", label="Intensity"),
)

validate_xps_series(source)
corrected = shift_xps_binding_energy(
    source,
    0.25,
    reference="caller-supplied reference",
)
np.testing.assert_allclose(corrected.x, source.x + 0.25)
np.testing.assert_array_equal(corrected.y, source.y)

region = prepare_xps_region(corrected, 1.0, 9.5, minimum_points=3)
assert region.x[0] > region.x[-1]
assert np.all(region.x >= 1.0)
assert np.all(region.x <= 9.5)

linear = linear_xps_background(source)
assert linear.source_direction == "descending"
assert linear.background_y[0] == source.y[0]
assert linear.background_y[-1] == source.y[-1]

shirley = shirley_xps_background(source)
assert shirley.converged
assert shirley.iterations == 1
np.testing.assert_allclose(shirley.background_y, 2.0, atol=1e-12)
assert not shirley.background_y.flags.writeable

assert not any(name == "matplotlib" or name.startswith("matplotlib.") for name in sys.modules)
