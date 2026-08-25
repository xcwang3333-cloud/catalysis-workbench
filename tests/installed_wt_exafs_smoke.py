"""Installed-wheel smoke for the v0.5 WT-EXAFS public surface."""

from __future__ import annotations

import sys

import numpy as np

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.characterization import (
    EXAFSWTSpec,
    cauchy_wt_exafs,
)

k = np.arange(0.0, 15.0 + 0.025, 0.05)
target_r = 2.5
source = Series(
    x=k,
    y=np.cos(2.0 * target_r * k),
    key="installed-wt",
    x_axis=Axis("k", unit="Å^-1"),
    y_axis=Axis("chi", unit="1"),
)
result = cauchy_wt_exafs(
    source,
    EXAFSWTSpec(
        order=20,
        rmin_angstrom=1.0,
        rmax_angstrom=4.0,
        rstep_angstrom=0.1,
        nfft=512,
    ),
)
k_index = int(np.argmin(np.abs(result.k_grid - 7.5)))
ridge = float(result.r_grid[np.argmax(result.magnitude[:, k_index])])
assert np.isclose(ridge, target_r, atol=result.spec.rstep_angstrom)
assert np.allclose(result.magnitude, np.abs(result.transform))
assert result.spec.frequency_mapping == "omega_peak=2R"
assert "matplotlib.pyplot" not in sys.modules
