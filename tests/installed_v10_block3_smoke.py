"""Fresh-wheel smoke for the v1.0 Block-3 persistent evidence ledger."""

from __future__ import annotations

import sys
import tempfile
from importlib.metadata import version as distribution_version
from pathlib import Path

import catalysis_workbench
from catalysis_workbench.workspace import create_workspace
from catalysis_workbench.workspace.assets import import_asset
from catalysis_workbench.workspace.evidence import (
    EvidenceAssociation,
    EvidenceLedger,
    EvidenceRef,
    append_evidence,
    artifact_evidence,
    load_evidence_ledger,
    recipe_evidence,
)
from catalysis_workbench.workflow.recipe import RecipeStep, WorkflowRecipe

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
    assert catalysis_workbench.__version__ == "1.0.0.dev0"
    assert distribution_version("catalysis-workbench") == "1.0.0.dev0"

    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        root = base / "workspace"
        source = base / "source.bin"
        source.write_bytes(b"explicit-source")
        create_workspace(root)
        manifest = import_asset(
            root,
            source,
            asset_id="source",
            asset_type="source-file",
            policy="copy",
            destination="data/source.bin",
        )
        asset = manifest.assets[0]

        recipe = WorkflowRecipe(
            schema_version=1,
            inputs=("input",),
            steps=(
                RecipeStep(
                    step_id="step",
                    operation_id="reviewed.operation",
                    inputs={"series": "input"},
                    outputs={"series": "processed"},
                    parameters={},
                ),
            ),
            outputs={"result": "processed"},
        )

        ledger = append_evidence(
            root,
            association_id="source-evidence",
            asset_ids=("source",),
            evidence=(artifact_evidence(asset), recipe_evidence(recipe)),
        )
        assert isinstance(ledger, EvidenceLedger)
        assert ledger.records == (
            EvidenceAssociation(
                association_id="source-evidence",
                asset_ids=("source",),
                evidence=(
                    EvidenceRef(kind="artifact", sha256=asset.content_sha256),
                    EvidenceRef(kind="recipe", sha256=recipe.recipe_sha256),
                ),
            ),
        )
        restored = load_evidence_ledger(root)
        assert restored == ledger
        assert restored.ledger_sha256 == ledger.ledger_sha256

    forbidden = [
        name
        for name in sys.modules
        if name == "pyvista"
        or name.startswith("pyvista.")
        or name == "vtk"
        or name.startswith("vtk.")
        or name.startswith("vtkmodules.")
    ]
    assert not forbidden, f"evidence smoke loaded presentation backends: {forbidden!r}"
    print("installed v1.0 Block-3 evidence ledger smoke: ok")


if __name__ == "__main__":
    main()
