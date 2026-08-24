"""Review regressions for composition API compatibility and lazy imports."""

from __future__ import annotations

import subprocess
import sys

import pytest

from catalysis_workbench.experimental.characterization import (
    CompositionError,
    CompositionSummary,
)


def test_characterization_numerical_import_keeps_matplotlib_lazy() -> None:
    code = """
import sys
import catalysis_workbench.experimental.characterization
assert not any(name == 'matplotlib' or name.startswith('matplotlib.') for name in sys.modules)
"""
    subprocess.run([sys.executable, "-c", code], check=True)


def test_summary_rejects_fractional_n_instead_of_truncating() -> None:
    with pytest.raises((CompositionError, TypeError, ValueError)):
        CompositionSummary(
            sample_key="a",
            element="Pb",
            basis="bulk_mass_fraction",
            unit="wt%",
            n=1.5,  # type: ignore[arg-type]
            mean=1.0,
            standard_deviation=None,
            rsd_percent=None,
            source_keys=("a",),
            source_sha256="0" * 64,
        )


def test_summary_rejects_nonhex_sha256() -> None:
    with pytest.raises(CompositionError, match="SHA-256"):
        CompositionSummary(
            sample_key="a",
            element="Pb",
            basis="bulk_mass_fraction",
            unit="wt%",
            n=1,
            mean=1.0,
            standard_deviation=None,
            rsd_percent=None,
            source_keys=("a",),
            source_sha256="z" * 64,
        )
