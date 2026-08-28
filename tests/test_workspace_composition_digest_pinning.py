from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from catalysis_workbench.workflow import RecipeStep, WorkflowRecipe
from catalysis_workbench.workspace import (
    WorkspaceManifest,
    create_workspace,
    open_workspace,
    save_workspace,
)
from catalysis_workbench.workspace.assets import import_asset
from catalysis_workbench.workspace.composition import (
    bind_recipe_assets,
    create_workspace_composition,
    open_workspace_composition,
    record_figure_export,
    save_figure_spec_asset,
    save_recipe_asset,
)
from catalysis_workbench.workspace.evidence import (
    EvidenceLedger,
    EvidenceRecord,
    append_evidence,
    create_evidence_ledger,
    save_evidence_ledger,
)
from catalysis_workbench.workspace.manifest import WorkspaceError


def _recipe() -> WorkflowRecipe:
    return WorkflowRecipe(
        schema_version=1,
        inputs=("raw",),
        steps=(
            RecipeStep(
                step_id="identity",
                operation_id="example.identity",
                inputs={"value": "raw"},
                outputs={"value": "processed"},
                parameters={},
            ),
        ),
        outputs={"result": "processed"},
    )


def _copy_asset(
    root: Path,
    source_dir: Path,
    *,
    asset_id: str,
    destination: str,
    content: bytes,
    asset_type: str = "data",
) -> None:
    source = source_dir / f"{asset_id}.bin"
    source.write_bytes(content)
    import_asset(
        root,
        source,
        asset_id=asset_id,
        asset_type=asset_type,
        policy="copy",
        destination=destination,
    )


def test_recipe_composition_pins_asset_content_digest(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    save_recipe_asset(
        root,
        _recipe(),
        asset_id="recipe-main",
        destination="recipes/main.json",
    )
    _copy_asset(
        root,
        tmp_path,
        asset_id="raw-data",
        destination="data/raw.bin",
        content=b"raw-v1",
    )
    _copy_asset(
        root,
        tmp_path,
        asset_id="result-data",
        destination="data/result.bin",
        content=b"result-v1",
    )
    create_workspace_composition(root)

    composition = bind_recipe_assets(
        root,
        composition_id="analysis-main",
        recipe_asset_id="recipe-main",
        input_assets={"raw": "raw-data"},
        output_assets={"result": "result-data"},
    )
    frozen_digest = composition.recipes[0].input_asset_sha256["raw"]

    manifest = open_workspace(root)
    raw_asset = next(asset for asset in manifest.assets if asset.asset_id == "raw-data")
    assert frozen_digest == raw_asset.content_sha256

    replacement_bytes = b"raw-v2"
    (root / raw_asset.path).write_bytes(replacement_bytes)
    replacement_digest = hashlib.sha256(replacement_bytes).hexdigest()
    updated_assets = tuple(
        replace(asset, content_sha256=replacement_digest)
        if asset.asset_id == "raw-data"
        else asset
        for asset in manifest.assets
    )
    save_workspace(
        WorkspaceManifest(schema_version=manifest.schema_version, assets=updated_assets),
        root,
        overwrite=True,
    )

    with pytest.raises(WorkspaceError, match="input asset digest mismatch"):
        open_workspace_composition(root)


def test_figure_composition_pins_evidence_record_digest(tmp_path: Path) -> None:
    from catalysis_workbench.visualization import FigureSpec

    root = tmp_path / "workspace"
    create_workspace(root)
    save_figure_spec_asset(
        root,
        FigureSpec(title="Pinned evidence"),
        asset_id="figure-spec",
        destination="figures/spec.json",
    )
    _copy_asset(
        root,
        tmp_path,
        asset_id="figure-export",
        destination="exports/result.svg",
        content=b"<svg/>",
        asset_type="exported_figure",
    )
    create_evidence_ledger(root)
    original = EvidenceRecord(
        record_id="run-evidence",
        kind="artifact",
        evidence_sha256="a" * 64,
    )
    append_evidence(root, original)
    create_workspace_composition(root)

    composition = record_figure_export(
        root,
        composition_id="figure-main",
        figure_spec_asset_id="figure-spec",
        exported_figure_asset_id="figure-export",
        evidence_record_ids=("run-evidence",),
    )
    assert composition.figures[0].evidence_record_sha256 == {
        "run-evidence": original.record_sha256
    }

    replacement = EvidenceRecord(
        record_id="run-evidence",
        kind="artifact",
        evidence_sha256="b" * 64,
    )
    assert replacement.record_sha256 != original.record_sha256
    save_evidence_ledger(
        EvidenceLedger(schema_version=1, records=(replacement,)),
        root,
        overwrite=True,
    )

    with pytest.raises(WorkspaceError, match="evidence digest mismatch"):
        open_workspace_composition(root)
