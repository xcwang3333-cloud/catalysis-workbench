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
from catalysis_workbench.workspace import WorkspaceAsset, create_workspace, open_workspace
from catalysis_workbench.workspace.manifest import WorkspaceError


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


def test_project_json_is_reserved_workspace_metadata() -> None:
    with pytest.raises(WorkspaceError, match="reserved workspace metadata"):
        WorkspaceAsset(
            asset_id="project-control-state",
            asset_type="metadata",
            path="project.json",
        )


def test_external_project_mutation_is_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "project"
    snapshot = create_analysis_project(_document(), root)
    project_path = root / "project.json"
    text = project_path.read_text(encoding="utf-8")
    project_path.write_text(
        text.replace("Pb nuclearity CO₂RR", "External edit"),
        encoding="utf-8",
    )

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
        '{"assets":[{"asset_id":"x","asset_type":"data","path":"data/x"}],'
        '"schema_version":1}\n',
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


@pytest.mark.parametrize(
    ("payload", "message"),
    (
        ("not-json\n", "cannot load project.json"),
        (
            '{"document":{"schema_version":1,"task_id":"lsv","title":"LSV"},'
            '"schema_version":2}\n',
            "project schema_version",
        ),
        (
            '{"document":{"schema_version":1,"task_id":"unknown","title":"LSV"},'
            '"schema_version":1}\n',
            "unknown analysis task_id",
        ),
    ),
)
def test_malformed_unknown_schema_or_unknown_task_fails_closed(
    tmp_path: Path,
    payload: str,
    message: str,
) -> None:
    root = tmp_path / "project"
    create_workspace(root)
    (root / "project.json").write_text(payload, encoding="utf-8")

    with pytest.raises(AnalysisProjectError, match=message):
        open_analysis_project(root)


def test_failed_first_save_rolls_back_only_its_exact_new_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from catalysis_workbench.application.analysis import persistence

    root = tmp_path / "project"

    def fail_after_write(_root: str | Path):
        raise AnalysisProjectError("injected verification failure")

    monkeypatch.setattr(persistence, "open_analysis_project", fail_after_write)

    with pytest.raises(AnalysisProjectError, match="injected verification failure"):
        persistence.create_analysis_project(_document(), root)

    assert not root.exists()


def test_failed_first_save_preserves_external_workspace_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from catalysis_workbench.application.analysis import persistence

    root = tmp_path / "project"
    external_payload = b'{"assets":[],"schema_version":1}\nexternal-change\n'

    def mutate_then_fail(observed_root: str | Path):
        (Path(observed_root) / "workspace.json").write_bytes(external_payload)
        raise AnalysisProjectError("injected concurrent mutation")

    monkeypatch.setattr(persistence, "open_analysis_project", mutate_then_fail)

    with pytest.raises(AnalysisProjectError, match="injected concurrent mutation"):
        persistence.create_analysis_project(_document(), root)

    assert root.is_dir()
    assert (root / "workspace.json").read_bytes() == external_payload
    assert not (root / "project.json").exists()


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
