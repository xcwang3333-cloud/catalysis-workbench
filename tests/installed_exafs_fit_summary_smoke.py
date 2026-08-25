"""Installed-wheel smoke for neutral v0.5 EXAFS fit-summary integration."""

from __future__ import annotations

import sys

from catalysis_workbench.experimental.characterization import (
    EXAFSFitDiagnostic,
    EXAFSFitSummary,
    EXAFSFitValue,
    EXAFSPathSummary,
    exafs_fit_diagnostics_frame,
    exafs_fit_summary_frame,
)

summary = EXAFSFitSummary(
    producer="installed-producer",
    source_id="installed-fit",
    paths=(
        EXAFSPathSummary(
            key="path-1",
            coordination_number=EXAFSFitValue(4.0, 0.3, status="fitted"),
            r_angstrom=EXAFSFitValue(2.01, 0.02, status="fitted"),
            sigma2_angstrom2=EXAFSFitValue(-0.001, status="fitted"),
        ),
    ),
    diagnostics=(EXAFSFitDiagnostic("R-factor", 0.01),),
)
paths = exafs_fit_summary_frame(summary)
diagnostics = exafs_fit_diagnostics_frame(summary)
assert paths.loc[0, "path_key"] == "path-1"
assert paths.loc[0, "sigma2_angstrom2"] == -0.001
assert diagnostics.loc[0, "diagnostic_label"] == "R-factor"
assert "matplotlib.pyplot" not in sys.modules
