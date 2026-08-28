"""Unified Gate-A audit for the frozen v1.0 installed wheel."""

from __future__ import annotations

import os
import subprocess
import sys
from importlib import import_module
from importlib.metadata import metadata, version as distribution_version
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
REVIEWED_INSTALLED_SMOKES = (
    "installed_v07_release_smoke.py",
    "installed_v08_block1_smoke.py",
    "installed_v08_block2_smoke.py",
    "installed_v08_block3_smoke.py",
    "installed_v08_block4_smoke.py",
    "installed_v08_block5_smoke.py",
    "installed_v08_block6_smoke.py",
    "installed_v09_smoke.py",
    "installed_v09_block5_smoke.py",
    "installed_v09_block6_smoke.py",
    "installed_v10_block1_smoke.py",
    "installed_v10_block2_smoke.py",
    "installed_v10_block3_smoke.py",
    "installed_v10_block4_smoke.py",
    "installed_v10_block5_smoke.py",
    "installed_v10_block6_smoke.py",
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
    raise AssertionError(f"v1.0 release audit imported repository source tree: {package_file}")


def _assert_gate_version() -> None:
    expected = os.environ.get("CATALYSIS_WORKBENCH_EXPECTED_VERSION")
    assert expected, "CATALYSIS_WORKBENCH_EXPECTED_VERSION must be set by the release gate"
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
    assert not forbidden, f"numerical/application imports loaded presentation backends: {forbidden!r}"


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
    extras = set(project.get_all("Provides-Extra") or ())
    assert {"desktop", "dev", "structure", "volumetric3d"}.issubset(extras)

    classifiers = set(project.get_all("Classifier") or ())
    for classifier in (
        "Development Status :: 4 - Beta",
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

    keywords = {item.strip() for item in (project["Keywords"] or "").split(",")}
    assert {"catalysis", "reproducibility", "visualization"}.issubset(keywords)


def _assert_optional_backends_are_lazy() -> None:
    forbidden_prefixes = ("PySide6", "pymatgen", "pyvista", "vtk", "vtkmodules")
    loaded = [
        name
        for name in sys.modules
        if any(name == prefix or name.startswith(f"{prefix}.") for prefix in forbidden_prefixes)
    ]
    assert not loaded, f"base release audit loaded optional backends: {loaded!r}"


def _run_reviewed_installed_smokes() -> None:
    tests_dir = ROOT / "tests"
    env = os.environ.copy()
    for filename in REVIEWED_INSTALLED_SMOKES:
        path = tests_dir / filename
        assert path.is_file(), f"missing reviewed installed smoke: {path}"
        subprocess.run([sys.executable, str(path)], check=True, env=env)


def main() -> None:
    _assert_installed_import()
    _assert_gate_version()
    _assert_numerical_imports_are_presentation_lazy()
    _assert_public_exports()
    _assert_base_package_metadata()
    _assert_optional_backends_are_lazy()
    _run_reviewed_installed_smokes()
    print("installed v1.0 Gate-A release audit: ok")


if __name__ == "__main__":
    main()
