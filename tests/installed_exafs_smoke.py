"""Installed-wheel smoke for the v0.5 EXAFS forward-FT public surface."""

from __future__ import annotations

import sys

import numpy as np

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.characterization import (
    EXAFSFTSpec,
    EXAFSKSpaceSpec,
    forward_ft_exafs,
    ft_exafs_component,
    prepare_exafs_kspace,
    validate_exafs_series,
)

k = np.arange(0.0, 8.0 + 0.025, 0.05)
source = Series(
    x=k,
    y=np.sin(2.0 * k) * np.exp(-0.1 * k),
    key="installed-exafs",
    x_axis=Axis("k", unit="Å^-1"),
    y_axis=Axis("chi", unit="1"),
)
validate_exafs_series(source)
prepared = prepare_exafs_kspace(
    source,
    EXAFSKSpaceSpec(kmin=2.0, kmax=6.0, kweight=2.0, dk=1.0),
)
result = forward_ft_exafs(
    prepared,
    EXAFSFTSpec(nfft=2048, rmax_angstrom=10.0),
)
magnitude = ft_exafs_component(result, "magnitude")
assert np.isclose(result.r_step, np.pi / (0.05 * 2048))
assert np.allclose(result.magnitude, np.abs(result.chi_r))
assert magnitude.y_axis.name == "chi_r_magnitude"
assert magnitude.x_axis.metadata["phase_corrected"] is False
assert "matplotlib.pyplot" not in sys.modules
