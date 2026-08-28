"""Installed-wheel smoke for v0.9 Block 5 preset bundles."""

from __future__ import annotations

import importlib.metadata
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import catalysis_workbench
import catalysis_workbench.visualization as visualization

EXPECTED_VERSION = "1.1.0.dev0"
EXPECTED_PUBLIC_API = {
    "FigurePresetBundle",
    "FigurePresetEntry",
    "install_preset_bundle",
    "load_preset_bundle",
    "save_preset_bundle",
}
SOURCE_TREE = Path(__file__).resolve().parents[1] / "src"


def main() -> None:
    assert importlib.metadata.version("catalysis-workbench") == EXPECTED_VERSION
    assert catalysis_workbench.__version__ == EXPECTED_VERSION
    visualization_path = Path(visualization.__file__).resolve()
    assert not visualization_path.is_relative_to(SOURCE_TREE)
    assert "site-packages" in {part.lower() for part in visualization_path.parts}
    assert EXPECTED_PUBLIC_API.issubset(set(visualization.__all__))
    assert all(hasattr(visualization, name) for name in EXPECTED_PUBLIC_API)

    first = visualization.FigurePresetEntry(
        name="block5-first",
        spec=visualization.FigureSpec(title="First"),
    )
    second = visualization.FigurePresetEntry(
        name="block5-second",
        spec=visualization.FigureSpec(title="Second"),
    )
    bundle = visualization.FigurePresetBundle(
        schema_version=1,
        entries=(first, second),
    )
    assert len(bundle.bundle_sha256) == 64

    with TemporaryDirectory() as directory:
        path = Path(directory) / "presets.json"
        visualization.save_preset_bundle(bundle, path)
        restored = visualization.load_preset_bundle(path)
        assert restored.bundle_sha256 == bundle.bundle_sha256
        assert tuple(entry.name for entry in restored.entries) == (
            "block5-first",
            "block5-second",
        )
        try:
            visualization.save_preset_bundle(bundle, path)
        except FileExistsError:
            pass
        else:
            raise AssertionError("save_preset_bundle silently overwrote an existing file")

    before = visualization.list_presets()
    conflict = visualization.FigurePresetBundle(
        schema_version=1,
        entries=(
            visualization.FigurePresetEntry(
                name="block5-partial",
                spec=visualization.FigureSpec(title="must-not-install"),
            ),
            visualization.FigurePresetEntry(
                name="publication",
                spec=visualization.FigureSpec(title="conflict"),
            ),
        ),
    )
    try:
        visualization.install_preset_bundle(conflict)
    except visualization.VisualizationError:
        pass
    else:
        raise AssertionError("conflicting preset bundle was installed")
    assert visualization.list_presets() == before
    try:
        visualization.get_preset("block5-partial")
    except visualization.VisualizationError:
        pass
    else:
        raise AssertionError("failed bundle installation partially mutated the registry")

    visualization.install_preset_bundle(bundle)
    assert visualization.list_presets() == (*before, "block5-first", "block5-second")
    assert visualization.get_preset("block5-first").title == "First"
    assert visualization.get_preset("block5-second").title == "Second"

    for optional_name in ("pymatgen", "pyvista", "vtk"):
        assert optional_name not in sys.modules

    print("installed v0.9 Block 5 smoke passed")


if __name__ == "__main__":
    main()
