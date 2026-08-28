"""Fresh-wheel smoke for the v1.0 Block-3 persistent evidence ledger."""

from __future__ import annotations

import sys
import tempfile
from importlib.metadata import version as distribution_version
from pathlib import Path

import catalysis_workbench
from catalysis_workbench.workspace import create_workspace
from catalysis_workbench.workspace.evidence import (
    EvidenceLedger,
    EvidenceRecord,
    append_evidence,
    create_evidence_ledger,
    open_evidence_ledger,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE_TREE = (ROOT / "src").resolve()


def _assert_installed_import() -> None:
    package_file = Path(catalysis_workbench.__file__).resolve()
    try:
        package_file.relative_to(SOURCE_TREE)
    except ValueError:
        return
    raise AssertionError(f"evidence smoke imported repository source tree: {package_file}")


def main() -> None:
    _assert_installed_import()
    assert catalysis_workbench.__version__ == "1.1.0.dev0"
    assert distribution_version("catalysis-workbench") == "1.1.0.dev0"

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
    assert not forbidden, f"evidence import loaded presentation backends: {forbidden!r}"

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "workspace"
        create_workspace(root)
        empty = create_evidence_ledger(root)
        assert isinstance(empty, EvidenceLedger)
        assert empty.records == ()

        record = EvidenceRecord(
            record_id="artifact",
            kind="artifact",
            evidence_sha256="0" * 64,
        )
        updated = append_evidence(root, record)
        assert updated.records == (record,)
        assert open_evidence_ledger(root) == updated
        assert updated.ledger_sha256 == open_evidence_ledger(root).ledger_sha256

    print("installed v1.0 Block-3 evidence ledger smoke: ok")


if __name__ == "__main__":
    main()
