"""Unified Gate-A audit for the frozen v0.4 installed wheel.

CI runs this program with the Python interpreter from a fresh virtual environment that
contains the built wheel and its declared dependencies. The audit verifies packaging and
public-API invariants, then reuses the already reviewed installed-wheel smoke programs as
independent subprocesses so Gate A does not duplicate or weaken their scientific checks.
"""

from __future__ import annotations

import os
import subprocess
import sys
from importlib import import_module
from importlib.metadata import version as distribution_version
from pathlib import Path

import catalysis_workbench

ROOT = Path(__file__).resolve().parents[1]
SOURCE_TREE = (ROOT / "src").resolve()
PUBLIC_MODULES = (
    "catalysis_workbench.core",
    "catalysis_workbench.io",
    "catalysis_workbench.processing",
    "catalysis_workbench.experimental.echem",
    "catalysis_workbench.experimental.characterization",
    "catalysis_workbench.experimental.product",
    "catalysis_workbench.visualization",
)
REVIEWED_INSTALLED_SMOKES = (
    "installed_v03_release_smoke.py",
    "installed_peak_fitting_smoke.py",
    "installed_xps_smoke.py",
    "installed_xps_fitting_smoke.py",
    "installed_xps_plotting_smoke.py",
    "installed_eis_smoke.py",
    "installed_bet_smoke.py",
    "installed_product_calibration_smoke.py",
)


def _assert_installed_import() -> None:
    package_file = Path(catalysis_workbench.__file__).resolve()
    try:
        package_file.relative_to(SOURCE_TREE)
    except ValueError:
        return
    raise AssertionError(f"release audit imported repository source tree: {package_file}")


def _assert_gate_version() -> None:
    runtime = catalysis_workbench.__version__
    installed = distribution_version("catalysis-workbench")
    assert runtime == installed, (runtime, installed)
    expected = os.environ.get("CATALYSIS_WORKBENCH_EXPECTED_VERSION")
    assert expected, "CATALYSIS_WORKBENCH_EXPECTED_VERSION must be set by the release gate"
    assert runtime == expected, (runtime, expected)


def _assert_public_exports() -> None:
    for module_name in PUBLIC_MODULES:
        module = import_module(module_name)
        exports = tuple(getattr(module, "__all__", ()))
        assert exports, f"documented public module has empty __all__: {module_name}"
        assert len(exports) == len(set(exports)), f"duplicate __all__ names: {module_name}"
        for name in exports:
            assert isinstance(name, str) and name, f"invalid __all__ entry: {module_name}"
            getattr(module, name)


def _assert_numerical_imports_are_matplotlib_lazy() -> None:
    import_module("catalysis_workbench.processing")
    import_module("catalysis_workbench.experimental.echem")
    import_module("catalysis_workbench.experimental.characterization")
    import_module("catalysis_workbench.experimental.product")
    loaded = [
        name
        for name in sys.modules
        if name == "matplotlib" or name.startswith("matplotlib.")
    ]
    assert not loaded, f"numerical public imports loaded Matplotlib: {loaded!r}"


def _run_reviewed_installed_smokes() -> None:
    tests_dir = ROOT / "tests"
    for filename in REVIEWED_INSTALLED_SMOKES:
        path = tests_dir / filename
        assert path.is_file(), f"missing reviewed installed smoke: {path}"
        subprocess.run([sys.executable, str(path)], check=True, env=os.environ.copy())


def main() -> None:
    _assert_installed_import()
    _assert_gate_version()
    _assert_numerical_imports_are_matplotlib_lazy()
    _assert_public_exports()
    _run_reviewed_installed_smokes()
    print("installed v0.4 Gate-A release audit: ok")


if __name__ == "__main__":
    main()
