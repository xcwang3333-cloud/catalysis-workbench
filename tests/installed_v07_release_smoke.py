"""Unified Gate-A audit for the frozen v0.7 installed wheel.

CI runs this program with the Python interpreter from a fresh base-wheel virtual
environment. The audit verifies packaging, version, public-API and lazy optional-backend
invariants, then reuses the reviewed v0.6 release audit plus all reviewed v0.7 base
installed-wheel smoke programs as independent subprocesses.

The optional ``structure`` and heavy ``volumetric3d`` backends remain audited in separate
fresh environments/jobs because neither belongs to the base wheel.
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
    "catalysis_workbench.computation",
    "catalysis_workbench.visualization",
)
NUMERICAL_MODULES = (
    "catalysis_workbench.processing",
    "catalysis_workbench.experimental.echem",
    "catalysis_workbench.experimental.characterization",
    "catalysis_workbench.experimental.product",
    "catalysis_workbench.computation",
)
REQUIRED_V07_COMPUTATION_EXPORTS = (
    "ScalarField",
    "ScalarFieldSlice",
    "BandStructureState",
    "BandProjectionState",
    "PlanarPotentialProfile",
    "WorkFunctionResult",
    "NEBImageState",
    "NEBPath",
    "NEBBarrierResult",
)
REQUIRED_V07_VISUALIZATION_EXPORTS = (
    "IsosurfaceLayerSpec",
    "SliceLayerSpec",
    "VolumetricScene",
    "plot_scalar_field_slice",
    "plot_band_structure",
    "plot_fat_band",
    "plot_planar_potential",
    "plot_neb_path",
    "Volumetric3DRenderSpec",
    "Volumetric3DRenderResult",
    "render_volumetric_scene_3d",
    "export_volumetric_scene_3d",
)
REVIEWED_INSTALLED_SMOKES = (
    "installed_v06_release_smoke.py",
    "installed_v07_block1_smoke.py",
    "installed_v07_block2_smoke.py",
    "installed_v07_block3_smoke.py",
    "installed_v07_block4_smoke.py",
    "installed_v07_block5_smoke.py",
    "installed_v07_block6_smoke.py",
    "installed_v07_block7_base_smoke.py",
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


def _assert_numerical_imports_are_matplotlib_lazy() -> None:
    for module_name in NUMERICAL_MODULES:
        import_module(module_name)
    loaded = [
        name
        for name in sys.modules
        if name == "matplotlib" or name.startswith("matplotlib.")
    ]
    assert not loaded, f"numerical public imports loaded Matplotlib: {loaded!r}"


def _assert_public_exports() -> None:
    for module_name in PUBLIC_MODULES:
        module = import_module(module_name)
        exports = tuple(getattr(module, "__all__", ()))
        assert exports, f"documented public module has empty __all__: {module_name}"
        assert len(exports) == len(set(exports)), f"duplicate __all__ names: {module_name}"
        for name in exports:
            assert isinstance(name, str) and name, f"invalid __all__ entry: {module_name}"
            getattr(module, name)

    computation = import_module("catalysis_workbench.computation")
    computation_exports = set(computation.__all__)
    missing_computation = [
        name for name in REQUIRED_V07_COMPUTATION_EXPORTS if name not in computation_exports
    ]
    assert not missing_computation, (
        f"missing reviewed v0.7 computation exports: {missing_computation!r}"
    )
    for name in REQUIRED_V07_COMPUTATION_EXPORTS:
        getattr(computation, name)

    visualization = import_module("catalysis_workbench.visualization")
    visualization_exports = set(visualization.__all__)
    missing_visualization = [
        name
        for name in REQUIRED_V07_VISUALIZATION_EXPORTS
        if name not in visualization_exports
    ]
    assert not missing_visualization, (
        f"missing reviewed v0.7 visualization exports: {missing_visualization!r}"
    )
    for name in REQUIRED_V07_VISUALIZATION_EXPORTS:
        getattr(visualization, name)


def _assert_heavy_3d_backend_is_lazy() -> None:
    loaded = [
        name
        for name in sys.modules
        if name == "pyvista"
        or name.startswith("pyvista.")
        or name == "vtk"
        or name.startswith("vtk.")
        or name.startswith("vtkmodules.")
    ]
    assert not loaded, f"base public imports loaded optional PyVista/VTK backend: {loaded!r}"


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
    _assert_heavy_3d_backend_is_lazy()
    _run_reviewed_installed_smokes()
    print("installed v0.7 Gate-A release audit: ok")


if __name__ == "__main__":
    main()
