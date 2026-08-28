from __future__ import annotations

from pathlib import Path

import pytest

from catalysis_workbench.workspace import WorkspaceAsset, create_workspace, open_workspace
from catalysis_workbench.workspace.assets import import_asset
from catalysis_workbench.workspace.manifest import WorkspaceError


@pytest.mark.parametrize("path", ["workspace-evidence.json", "WORKSPACE-EVIDENCE.JSON"])
def test_evidence_metadata_path_is_reserved_for_workspace_assets(path: str) -> None:
    with pytest.raises(WorkspaceError, match="reserved workspace metadata"):
        WorkspaceAsset(
            asset_id="evidence-metadata",
            asset_type="source-file",
            path=path,
        )


def test_copy_import_to_evidence_metadata_path_rolls_back_before_catalog_mutation(
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspace"
    source = tmp_path / "source.bin"
    source.write_bytes(b"source")
    original = create_workspace(root)

    with pytest.raises(WorkspaceError, match="reserved workspace metadata"):
        import_asset(
            root,
            source,
            asset_id="metadata",
            asset_type="source-file",
            policy="copy",
            destination="workspace-evidence.json",
        )

    assert not (root / "workspace-evidence.json").exists()
    assert source.read_bytes() == b"source"
    assert open_workspace(root) == original
