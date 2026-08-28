"""Fresh-wheel smoke for the v1.0 Block-2 explicit asset catalog."""

from __future__ import annotations

import hashlib
import sys
import tempfile
from importlib.metadata import version as distribution_version
from pathlib import Path

import catalysis_workbench
import catalysis_workbench.workspace.assets as assets
from catalysis_workbench.workspace import create_workspace, open_workspace

ROOT = Path(__file__).resolve().parents[1]
SOURCE_TREE = (ROOT / "src").resolve()


def _assert_installed_import() -> None:
    package_file = Path(catalysis_workbench.__file__).resolve()
    assets_file = Path(assets.__file__).resolve()
    for path in (package_file, assets_file):
        try:
            path.relative_to(SOURCE_TREE)
        except ValueError:
            continue
        raise AssertionError(f"Block-2 smoke imported repository source tree: {path}")


def main() -> None:
    _assert_installed_import()
    assert catalysis_workbench.__version__ == "1.0.0"
    assert distribution_version("catalysis-workbench") == "1.0.0"
    assert assets.__all__ == ["import_asset"]

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
        or name == "pymatgen"
        or name.startswith("pymatgen.")
    ]
    assert not forbidden, (
        f"asset catalog import loaded scientific/presentation backends: {forbidden!r}"
    )

    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        root = base / "workspace"
        first = base / "first.bin"
        second = base / "second.bin"
        first.write_bytes(b"first-source")
        second.write_bytes(b"second-source")
        create_workspace(root)

        referenced = assets.import_asset(
            root,
            second,
            asset_id="reference",
            asset_type="caller-selected-type",
            policy="reference",
        )
        reference = referenced.assets[0]
        assert reference.policy == "reference"
        assert reference.path == str(second.absolute())
        assert reference.content_sha256 == hashlib.sha256(second.read_bytes()).hexdigest()

        copied = assets.import_asset(
            root,
            first,
            asset_id="copy",
            asset_type="another-explicit-type",
            policy="copy",
            destination="data/copied.bin",
        )
        assert tuple(item.asset_id for item in copied.assets) == ("reference", "copy")
        copy = copied.assets[1]
        copied_path = root / "data" / "copied.bin"
        assert copy.policy == "copy"
        assert copy.path == "data/copied.bin"
        assert copied_path.read_bytes() == b"first-source"
        assert first.read_bytes() == b"first-source"
        assert copy.content_sha256 == hashlib.sha256(copied_path.read_bytes()).hexdigest()
        assert open_workspace(root) == copied

        try:
            assets.import_asset(
                root,
                first,
                asset_id="copy",
                asset_type="source-file",
                policy="reference",
            )
        except ValueError:
            pass
        else:
            raise AssertionError("asset-id collision was accepted")

    print("installed v1.0 Block-2 asset catalog smoke: ok")


if __name__ == "__main__":
    main()