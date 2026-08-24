"""Installed-wheel smoke for the v0.5 XAS/XANES public surface."""

from __future__ import annotations

import sys

import numpy as np

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.characterization import (
    XANESNormalizationSpec,
    XASWindow,
    normalize_xanes,
    shift_xas_energy,
    validate_xas_series,
    xanes_relative_energy,
)


source = Series(
    x=np.arange(0.0, 7.0),
    y=np.array([0.7, 0.8, 0.9, 3.0, 3.2, 3.4, 3.6]),
    key="installed-xas",
    x_axis=Axis("energy", unit="eV"),
    y_axis=Axis("mu", unit="a.u."),
)
validate_xas_series(source)
shifted = shift_xas_energy(source, 0.0, reference="installed smoke")
result = normalize_xanes(
    shifted,
    XANESNormalizationSpec(
        e0_ev=3.0,
        pre_edge=XASWindow(0.0, 2.0),
        post_edge=XASWindow(4.0, 6.0),
        pre_edge_order=1,
        post_edge_order=1,
    ),
)
assert np.isclose(result.edge_step, 2.0)
relative = xanes_relative_energy(result)
assert np.isclose(relative.x[3], 0.0)
assert result.normalized.y_axis.name == "normalized_mu"
assert "matplotlib.pyplot" not in sys.modules
