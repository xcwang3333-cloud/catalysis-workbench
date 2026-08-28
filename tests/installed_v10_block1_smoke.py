"""Fresh-wheel smoke for the v1.0 Block-1 workspace foundation."""

from __future__ import annotations

import sys
import tempfile
from importlib.metadata import version as distribution_version
from pathlib import Path

import catalysis_workbench
from catalysis_workbench.workspace import (
    WorkspaceAsset,
    WorkspaceManifest,
    create_workspace,
    open_workspace,
    save_workspace,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE_TREE = (ROOT / "src").resolve()
EXPECTED_EXPORTS = [
    "WorkspaceAsset",
    "WorkspaceManifest",
    "create_workspace",
    "open_workspace",
    "save_workspace",
]


def _assert_installed_import() -> None:
    package_file = Path(catalysis_workbench.__file__).resolve()
    try:
        package_file.relative_to(SOURCE_TREE)
    except ValueError:
        return
    raise AssertionError(f"workspace smoke imported repository source tree: {package_file}")


def main() -> None:
    _assert_installed_import()
    assert catalysis_workbench.__version__ == "1.0.0"
    assert distribution_version("catalysis-workbench") == "1.0.0"

    import catalysis_workbench.workspace as workspace

    assert workspace.__all__ == EXPECTED_EXPORTS
    for name in EXPECTED_EXPORTS:
        getattr(workspace, name)

    forbidden = [
        name
        for name in sys.modules
        if name == "matplotlib"
        or name.startswith("matplotlib.")
        or name == "pyvista"
        or name.startswith("pyvista.")
        or name == "vtk"
        or name.startswith("vtk.")
        or name.startswith("vtkmodules.")
    ]
    assert not forbidden, f"workspace import loaded presentation backends: {forbidden!r}"

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "workspace"
        empty = create_workspace(root)
        assert empty.assets == ()

        data = root / "data"
        data.mkdir()
        (data / "source.txt").write_text("source", encoding="utf-8")
        manifest = WorkspaceManifest(
            schema_version=1,
            assets=(
                WorkspaceAsset(
                    asset_id="source",
                    asset_type="source-file",
                    path="data/source.txt",
                ),
            ),
        )
        save_workspace(manifest, root, overwrite=True)
        restored = open_workspace(root)
        assert restored == manifest
        assert restored.manifest_sha256 == manifest.manifest_sha256

    print("installed v1.0 Block-1 workspace smoke: ok")


if __name__ == "__main__":
    main()