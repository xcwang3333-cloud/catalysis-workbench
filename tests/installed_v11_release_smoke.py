"""Unified Stable-1.1 audit for the reviewed v1.1 installed wheel."""

from __future__ import annotations

import io
import os
import subprocess
import sys
from contextlib import redirect_stdout
from importlib import import_module
from importlib.metadata import entry_points, metadata
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
    "catalysis_workbench.computation",
    "catalysis_workbench.visualization",
    "catalysis_workbench.workflow",
    "catalysis_workbench.workspace",
    "catalysis_workbench.application",
)
NUMERICAL_MODULES = (
    "catalysis_workbench.processing",
    "catalysis_workbench.experimental.echem",
    "catalysis_workbench.experimental.characterization",
    "catalysis_workbench.experimental.product",
    "catalysis_workbench.computation",
    "catalysis_workbench.workflow",
    "catalysis_workbench.workspace",
    "catalysis_workbench.application",
)
REVIEWED_V11_SMOKES = (
    "installed_v11_block1_smoke.py",
    "installed_v11_block2_smoke.py",
    "installed_v11_block3_smoke.py",
    "installed_v11_block4_smoke.py",
    "installed_v11_block5_smoke.py",
    "installed_v11_block6_smoke.py",
)
EXPECTED_PROJECT_URLS = {
    "Homepage": "https://github.com/xcwang3333-cloud/catalysis-workbench",
    "Repository": "https://github.com/xcwang3333-cloud/catalysis-workbench",
    "Issues": "https://github.com/xcwang3333-cloud/catalysis-workbench/issues",
    "Changelog": "https://github.com/xcwang3333-cloud/catalysis-workbench/blob/main/CHANGELOG.md",
}


def _assert_installed_import() -> None:
    package_file = Path(catalysis_workbench.__file__).resolve()
    try:
        package_file.relative_to(SOURCE_TREE)
    except ValueError:
        return
    raise AssertionError(f"v1.1 release audit imported repository source tree: {package_file}")


def _expected_version() -> str:
    expected = os.environ.get("CATALYSIS_WORKBENCH_EXPECTED_VERSION")
    assert expected, "CATALYSIS_WORKBENCH_EXPECTED_VERSION must be set by the release gate"
    return expected


def _assert_gate_version(expected: str) -> None:
    runtime = catalysis_workbench.__version__
    installed = distribution_version("catalysis-workbench")
    assert runtime == installed == expected, (runtime, installed, expected)


def _assert_numerical_imports_are_presentation_lazy() -> None:
    for module_name in NUMERICAL_MODULES:
        import_module(module_name)
    forbidden = [
        name
        for name in sys.modules
        if name == "matplotlib"
        or name.startswith("matplotlib.")
        or name == "PySide6"
        or name.startswith("PySide6.")
        or name == "pyvista"
        or name.startswith("pyvista.")
        or name == "vtk"
        or name.startswith("vtk.")
        or name.startswith("vtkmodules.")
    ]
    assert not forbidden, (
        f"numerical/application imports loaded presentation backends: {forbidden!r}"
    )


def _assert_public_exports() -> None:
    for module_name in PUBLIC_MODULES:
        module = import_module(module_name)
        exports = tuple(getattr(module, "__all__", ()))
        assert exports, f"documented public module has empty __all__: {module_name}"
        assert len(exports) == len(set(exports)), f"duplicate __all__ names: {module_name}"
        for name in exports:
            assert isinstance(name, str) and name, f"invalid __all__ entry: {module_name}"
            getattr(module, name)

    desktop = import_module("catalysis_workbench.desktop")
    assert tuple(desktop.__all__) == (
        "CatalysisWorkbenchMainWindow",
        "DesktopDependencyError",
        "desktop_available",
        "launch_desktop",
    )
    assert desktop.desktop_available() is False


def _assert_base_package_metadata() -> None:
    project = metadata("catalysis-workbench")
    assert project["Requires-Python"] == ">=3.11"
    assert project["License-Expression"] == "BSD-3-Clause"
    assert "LICENSE" in set(project.get_all("License-File") or ())
    extras = set(project.get_all("Provides-Extra") or ())
    assert {"desktop", "dev", "structure", "volumetric3d"}.issubset(extras)
    classifiers = set(project.get_all("Classifier") or ())
    for classifier in (
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Chemistry",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.14",
        "Operating System :: OS Independent",
    ):
        assert classifier in classifiers, classifier

    urls: dict[str, str] = {}
    for item in project.get_all("Project-URL") or ():
        label, separator, url = item.partition(", ")
        assert separator, item
        urls[label] = url
    assert urls == EXPECTED_PROJECT_URLS, urls

    scripts = {ep.name: ep.value for ep in entry_points(group="console_scripts")}
    assert scripts.get("catalysis-workbench") == "catalysis_workbench.desktop.cli:main"


def _assert_base_cli_version_is_qt_free(expected: str) -> None:
    cli = import_module("catalysis_workbench.desktop.cli")
    before = {name for name in sys.modules if name == "PySide6" or name.startswith("PySide6.")}
    assert not before
    stream = io.StringIO()
    with redirect_stdout(stream):
        code = cli.main(("--version",))
    assert code == 0
    assert stream.getvalue().strip() == f"CatalysisWorkbench {expected}"
    after = {name for name in sys.modules if name == "PySide6" or name.startswith("PySide6.")}
    assert not after


def _run_smoke(filename: str, env: dict[str, str]) -> None:
    path = ROOT / "tests" / filename
    assert path.is_file(), f"missing reviewed installed smoke: {path}"
    subprocess.run([sys.executable, str(path)], check=True, env=env)


def _run_reviewed_smokes() -> None:
    env = os.environ.copy()
    _run_smoke("installed_v10_release_smoke.py", env)
    for filename in REVIEWED_V11_SMOKES:
        _run_smoke(filename, env)


def main() -> None:
    _assert_installed_import()
    expected = _expected_version()
    _assert_gate_version(expected)
    _assert_numerical_imports_are_presentation_lazy()
    _assert_public_exports()
    _assert_base_package_metadata()
    _assert_base_cli_version_is_qt_free(expected)
    _run_reviewed_smokes()
    print("installed Stable v1.1 release audit: ok")


if __name__ == "__main__":
    main()