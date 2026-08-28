"""Cross-platform installed-wheel smoke for Stable 1.0 release candidates."""

from __future__ import annotations

import argparse
import os
import sys
from importlib import import_module
from importlib.metadata import metadata, version as distribution_version
from pathlib import Path

import catalysis_workbench

ROOT = Path(__file__).resolve().parents[1]
SOURCE_TREE = (ROOT / "src").resolve()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("base", "desktop"), required=True)
    return parser.parse_args()


def _assert_installed_import() -> None:
    package_file = Path(catalysis_workbench.__file__).resolve()
    try:
        package_file.relative_to(SOURCE_TREE)
    except ValueError:
        return
    raise AssertionError(f"platform smoke imported repository source tree: {package_file}")


def main() -> None:
    args = _parse_args()
    expected = os.environ.get("CATALYSIS_WORKBENCH_EXPECTED_VERSION")
    assert expected, "CATALYSIS_WORKBENCH_EXPECTED_VERSION is required"

    _assert_installed_import()
    assert catalysis_workbench.__version__ == expected
    assert distribution_version("catalysis-workbench") == expected

    project = metadata("catalysis-workbench")
    assert project["Requires-Python"] == ">=3.11"
    assert "desktop" in set(project.get_all("Provides-Extra") or ())

    for module_name in (
        "catalysis_workbench.core",
        "catalysis_workbench.workflow",
        "catalysis_workbench.workspace",
        "catalysis_workbench.application",
    ):
        module = import_module(module_name)
        exports = tuple(getattr(module, "__all__", ()))
        assert exports, module_name
        assert len(exports) == len(set(exports)), module_name

    assert not any(name == "PySide6" or name.startswith("PySide6.") for name in sys.modules)
    desktop = import_module("catalysis_workbench.desktop")
    assert not any(name == "PySide6" or name.startswith("PySide6.") for name in sys.modules)

    if args.mode == "base":
        assert desktop.desktop_available() is False
    else:
        assert desktop.desktop_available() is True
        qtcore = import_module("PySide6.QtCore")
        assert qtcore.qVersion()
        qtwidgets = import_module("PySide6.QtWidgets")
        assert hasattr(qtwidgets, "QApplication")

    print(f"installed v1.0 platform smoke ({args.mode}): ok")


if __name__ == "__main__":
    main()
