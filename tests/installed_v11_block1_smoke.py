"""Fresh-wheel smoke for v1.1 Block 1 analysis documents and project persistence."""

from __future__ import annotations

import sys
import tempfile
from importlib.metadata import version as distribution_version
from pathlib import Path

import catalysis_workbench
from catalysis_workbench.application import AnalysisSession, analysis_task_catalog
from catalysis_workbench.workspace import open_workspace

ROOT = Path(__file__).resolve().parents[1]
SOURCE_TREE = (ROOT / "src").resolve()
EXPECTED_VERSION = "1.1.0"


def _assert_installed_import() -> None:
    package_file = Path(catalysis_workbench.__file__).resolve()
    try:
        package_file.relative_to(SOURCE_TREE)
    except ValueError:
        return
    raise AssertionError(f"v1.1 smoke imported repository source tree: {package_file}")


def main() -> None:
    _assert_installed_import()
    assert catalysis_workbench.__version__ == EXPECTED_VERSION
    assert distribution_version("catalysis-workbench") == EXPECTED_VERSION
    assert "PySide6" not in sys.modules
    assert "matplotlib.pyplot" not in sys.modules
    assert tuple(task.task_id for task in analysis_task_catalog()) == (
        "lsv",
        "fe_partial_current",
        "generic_xy",
    )

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "project"
        session = AnalysisSession()
        untitled = session.new_analysis("lsv")
        assert untitled.is_unsaved and not untitled.is_dirty
        assert not root.exists()

        session.rename_analysis("Installed v1.1 LSV")
        saved = session.save_project_as(root)
        manifest_sha = open_workspace(root).manifest_sha256
        assert not saved.is_dirty
        assert saved.can_undo
        assert (root / "workspace.json").is_file()
        assert (root / "project.json").is_file()

        session.close_analysis()
        reopened = session.open_project(root)
        assert reopened.document is not None
        assert reopened.document.title == "Installed v1.1 LSV"
        assert open_workspace(root).manifest_sha256 == manifest_sha

    print("installed v1.1 Block-1 analysis project smoke: ok")


if __name__ == "__main__":
    main()
