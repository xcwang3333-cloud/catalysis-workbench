from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from catalysis_workbench.workspace import create_workspace, open_workspace
from catalysis_workbench.workspace.assets import (
    CopyAssetRequest,
    import_copy_assets_batch,
    verify_copy_asset,
)
from catalysis_workbench.workspace.manifest import WorkspaceError


def _file(tmp_path: Path, name: str, payload: bytes) -> Path:
    path = tmp_path / name
    path.write_bytes(payload)
    return path


def test_batch_copy_publishes_literal_order_in_one_manifest(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    before = create_workspace(root)
    first = _file(tmp_path, "first.dat", b"first")
    second = _file(tmp_path, "second.dat", b"second")

    after = import_copy_assets_batch(
        root,
        (
            CopyAssetRequest(first, "raw-first", "analysis_raw_tabular", "data/raw/first.dat"),
            CopyAssetRequest(second, "raw-second", "analysis_raw_tabular", "data/raw/second.dat"),
        ),
        expected_manifest_sha256=before.manifest_sha256,
    )

    assert tuple(asset.asset_id for asset in after.assets) == ("raw-first", "raw-second")
    assert (root / "data/raw/first.dat").read_bytes() == b"first"
    assert (root / "data/raw/second.dat").read_bytes() == b"second"
    assert open_workspace(root) == after


def test_batch_copy_stale_expected_manifest_fails_before_file_mutation(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    before = create_workspace(root)
    first = _file(tmp_path, "first.dat", b"first")
    import_copy_assets_batch(
        root,
        (CopyAssetRequest(first, "first", "raw", "data/first.dat"),),
        expected_manifest_sha256=before.manifest_sha256,
    )
    second = _file(tmp_path, "second.dat", b"second")

    with pytest.raises(WorkspaceError, match="changed outside"):
        import_copy_assets_batch(
            root,
            (CopyAssetRequest(second, "second", "raw", "data/second.dat"),),
            expected_manifest_sha256=before.manifest_sha256,
        )

    assert not (root / "data/second.dat").exists()


def test_expected_digest_rejects_source_mutation_during_copy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from catalysis_workbench.workspace import assets

    root = tmp_path / "workspace"
    before = create_workspace(root)
    source = _file(tmp_path, "source.dat", b"before")
    expected = hashlib.sha256(b"before").hexdigest()
    original = assets._copy_selected_file

    def mutate_then_copy(source_path: Path, destination: Path, workspace_root: Path):
        source_path.write_bytes(b"after")
        return original(source_path, destination, workspace_root)

    monkeypatch.setattr(assets, "_copy_selected_file", mutate_then_copy)

    with pytest.raises(WorkspaceError, match="changed while it was being copied"):
        import_copy_assets_batch(
            root,
            (
                CopyAssetRequest(
                    source,
                    "raw",
                    "analysis_raw_tabular",
                    "data/raw.dat",
                    expected_content_sha256=expected,
                ),
            ),
            expected_manifest_sha256=before.manifest_sha256,
        )

    assert open_workspace(root) == before
    assert not (root / "data").exists()


def test_verify_copy_asset_detects_external_raw_mutation(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    before = create_workspace(root)
    source = _file(tmp_path, "source.dat", b"source")
    import_copy_assets_batch(
        root,
        (CopyAssetRequest(source, "raw", "analysis_raw_tabular", "data/raw.dat"),),
        expected_manifest_sha256=before.manifest_sha256,
    )
    asset, path = verify_copy_asset(root, "raw", expected_type="analysis_raw_tabular")
    assert asset.content_sha256 is not None
    path.write_bytes(b"tampered")

    with pytest.raises(WorkspaceError, match="digest does not match"):
        verify_copy_asset(root, "raw", expected_type="analysis_raw_tabular")


def test_batch_copy_failure_rolls_back_all_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from catalysis_workbench.workspace import assets

    root = tmp_path / "workspace"
    before = create_workspace(root)
    first = _file(tmp_path, "first.dat", b"first")
    second = _file(tmp_path, "second.dat", b"second")
    original = assets._copy_selected_file
    calls = 0

    def fail_second(source: Path, destination: Path, workspace_root: Path):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected copy failure")
        return original(source, destination, workspace_root)

    monkeypatch.setattr(assets, "_copy_selected_file", fail_second)

    with pytest.raises(OSError, match="injected copy failure"):
        import_copy_assets_batch(
            root,
            (
                CopyAssetRequest(first, "first", "raw", "data/first.dat"),
                CopyAssetRequest(second, "second", "raw", "data/second.dat"),
            ),
            expected_manifest_sha256=before.manifest_sha256,
        )

    assert open_workspace(root) == before
    assert not (root / "data").exists()