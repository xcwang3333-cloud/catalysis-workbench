from __future__ import annotations

from pathlib import Path

import pytest

from catalysis_workbench.application import (
    AnalysisDocument,
    AnalysisProjectError,
    LegacyWorkspaceError,
    create_analysis_project,
    open_analysis_project,
    save_analysis_project,
)
from catalysis_workbench.workspace import create_workspace, open_workspace


def _document(title: str = "Pb nuclearity CO₂RR") -> AnalysisDocument:
    return AnalysisDocument(schema_version=1, task_id="lsv", title=title)


def test_first_save_creates_project_and_workspace_then_round_trips(tmp_path: Path) -> None:
    root = tmp_path / "project"
    created = create_analysis_project(_document(), root)

    assert (root / "workspace.json").is_file()
    assert (root / "project.json").is_file()
    reopened = open_analysis_project(root)
    assert reopened == created
    assert reopened.document.title == "Pb nuclearity CO₂RR"


def test_title_save_does_not_change_workspace_manifest_identity(tmp_path: Path) -> None:
    root = tmp_path / "project"
    before = create_analysis_project(_document(), root)
    workspace_before = open_workspace(root).manifest_sha256

    after = save_analysis_project(
        _document("Pb₃-N/C LSV"),
        root,
        expected_project_file_sha256=before.project_file_sha256,
        expected_workspace_manifest_sha256=before.workspace_manifest_sha256,
    )

    assert after.document.title == "Pb₃-N/C LSV"
    assert after.project_file_sha256 != before.project_file_sha256
    assert open_workspace(root).manifest_sha256 == workspace_before
    assert after.workspace_manifest_sha256 == workspace_before


def test_external_project_mutation_is_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "project"
    snapshot = create_analysis_project(_document(), root)
    project_path = root / "project.json"
    text = project_path.read_text(encoding="utf-8")
    project_path.write_text(text.replace("Pb nuclearity CO₂RR", "External edit"), encoding="utf-8")

    with pytest.raises(AnalysisProjectError, match="changed outside"):
        save_analysis_project(
            _document("Session edit"),
            root,
            expected_project_file_sha256=snapshot.project_file_sha256,
            expected_workspace_manifest_sha256=snapshot.workspace_manifest_sha256,
        )


def test_external_workspace_mutation_is_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "project"
    snapshot = create_analysis_project(_document(), root)
    workspace_path = root / "workspace.json"
    workspace_path.write_text(
        '{"assets":[{"asset_id":"x","asset_type":"data","path":"data/x"}],"schema_version":1}\n',
        encoding="utf-8",
    )

    with pytest.raises(AnalysisProjectError, match="workspace changed outside"):
        save_analysis_project(
            _document("Session edit"),
            root,
            expected_project_file_sha256=snapshot.project_file_sha256,
            expected_workspace_manifest_sha256=snapshot.workspace_manifest_sha256,
        )


def test_existing_target_and_legacy_workspace_are_rejected(tmp_path: Path) -> None:
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(FileExistsError):
        create_analysis_project(_document(), existing)

    legacy = tmp_path / "legacy"
    create_workspace(legacy)
    with pytest.raises(LegacyWorkspaceError, match="legacy CatalysisWorkbench workspace"):
        open_analysis_project(legacy)


def test_project_json_symlink_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    create_workspace(root)
    target = tmp_path / "outside.json"
    target.write_text("{}", encoding="utf-8")
    try:
        (root / "project.json").symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links are not available on this platform")

    with pytest.raises(AnalysisProjectError, match="symbolic link"):
        open_analysis_project(root)
