from __future__ import annotations

import json
import os
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from catalysis_workbench._canonical_json import canonical_json_bytes
from catalysis_workbench.workspace import (
    WorkspaceAsset,
    WorkspaceManifest,
    create_workspace,
    open_workspace,
    save_workspace,
)
from catalysis_workbench.workspace.manifest import WorkspaceError


def _asset(
    *,
    asset_id: str = "source",
    asset_type: str = "source-file",
    path: str = "data/source.txt",
) -> WorkspaceAsset:
    return WorkspaceAsset(asset_id=asset_id, asset_type=asset_type, path=path)


def _manifest(*assets: WorkspaceAsset) -> WorkspaceManifest:
    return WorkspaceManifest(schema_version=1, assets=assets)


def test_workspace_asset_and_manifest_are_frozen_and_ordered() -> None:
    first = _asset(asset_id="first", path="data/first.txt")
    second = _asset(asset_id="second", path="data/second.txt")
    source = [first, second]
    manifest = WorkspaceManifest(schema_version=1, assets=source)
    source.reverse()

    assert manifest.assets == (first, second)
    with pytest.raises(FrozenInstanceError):
        first.asset_id = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        manifest.assets = ()  # type: ignore[misc]


@pytest.mark.parametrize("value", ["", " asset", "asset "])
def test_asset_id_must_be_explicit(value: str) -> None:
    with pytest.raises(WorkspaceError):
        _asset(asset_id=value)


@pytest.mark.parametrize("value", ["", " type", "type "])
def test_asset_type_must_be_explicit(value: str) -> None:
    with pytest.raises(WorkspaceError):
        _asset(asset_type=value)


@pytest.mark.parametrize(
    "path",
    [
        "",
        ".",
        "data/.",
        "data/../escape.txt",
        "../escape.txt",
        "/absolute.txt",
        "C:/absolute.txt",
        "C:relative.txt",
        "data\\source.txt",
        "data//source.txt",
        "data/source.txt/",
        "workspace.json",
        "WORKSPACE.JSON",
        "data/\x00source.txt",
    ],
)
def test_workspace_owned_path_rejects_ambiguous_or_escaping_forms(path: str) -> None:
    with pytest.raises(WorkspaceError):
        _asset(path=path)


def test_workspace_owned_path_uses_portable_posix_form() -> None:
    asset = _asset(path="data/raw/source.txt")
    assert asset.path == "data/raw/source.txt"


@pytest.mark.parametrize("schema_version", [True, 0, -1, 2, "1"])
def test_workspace_schema_version_is_strict(schema_version: object) -> None:
    with pytest.raises(WorkspaceError):
        WorkspaceManifest(schema_version=schema_version, assets=())


def test_duplicate_asset_ids_are_rejected() -> None:
    with pytest.raises(WorkspaceError, match="asset_id"):
        _manifest(
            _asset(asset_id="same", path="data/a.txt"),
            _asset(asset_id="same", path="data/b.txt"),
        )


def test_duplicate_asset_paths_are_rejected() -> None:
    with pytest.raises(WorkspaceError, match="paths"):
        _manifest(
            _asset(asset_id="a", path="data/same.txt"),
            _asset(asset_id="b", path="data/same.txt"),
        )


def test_manifest_digest_is_sensitive_to_asset_order() -> None:
    first = _asset(asset_id="first", path="data/first.txt")
    second = _asset(asset_id="second", path="data/second.txt")
    left = _manifest(first, second)
    right = _manifest(second, first)
    assert left.manifest_sha256 != right.manifest_sha256


def test_manifest_digest_is_independent_of_workspace_root(tmp_path: Path) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    create_workspace(first_root)
    create_workspace(second_root)

    manifest = _manifest(_asset())
    (first_root / "data").mkdir()
    (second_root / "data").mkdir()
    (first_root / "data" / "source.txt").write_text("same", encoding="utf-8")
    (second_root / "data" / "source.txt").write_text("same", encoding="utf-8")
    save_workspace(manifest, first_root, overwrite=True)
    save_workspace(manifest, second_root, overwrite=True)

    assert open_workspace(first_root).manifest_sha256 == manifest.manifest_sha256
    assert open_workspace(second_root).manifest_sha256 == manifest.manifest_sha256


def test_create_workspace_writes_empty_canonical_manifest(tmp_path: Path) -> None:
    root = tmp_path / "project"
    manifest = create_workspace(root)

    assert manifest.assets == ()
    serialized = {"schema_version": 1, "assets": []}
    assert (root / "workspace.json").read_bytes() == canonical_json_bytes(serialized) + b"\n"
    assert open_workspace(root).manifest_sha256 == manifest.manifest_sha256


def test_create_workspace_refuses_existing_root(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    with pytest.raises(FileExistsError):
        create_workspace(root)


def test_save_refuses_overwrite_by_default(tmp_path: Path) -> None:
    root = tmp_path / "project"
    create_workspace(root)
    with pytest.raises(FileExistsError):
        save_workspace(_manifest(), root)


def test_save_allows_explicit_overwrite(tmp_path: Path) -> None:
    root = tmp_path / "project"
    create_workspace(root)
    (root / "data").mkdir()
    (root / "data" / "source.txt").write_text("payload", encoding="utf-8")

    manifest = _manifest(_asset())
    save_workspace(manifest, root, overwrite=True)
    assert open_workspace(root).manifest_sha256 == manifest.manifest_sha256


def test_save_requires_bool_overwrite(tmp_path: Path) -> None:
    root = tmp_path / "project"
    create_workspace(root)
    with pytest.raises(TypeError):
        save_workspace(_manifest(), root, overwrite=1)  # type: ignore[arg-type]


def test_open_rejects_unknown_serialized_fields(tmp_path: Path) -> None:
    root = tmp_path / "project"
    create_workspace(root)
    (root / "workspace.json").write_text(
        '{"assets":[],"extra":true,"schema_version":1}\n',
        encoding="utf-8",
    )
    with pytest.raises(WorkspaceError, match="unknown"):
        open_workspace(root)


def test_open_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    root = tmp_path / "project"
    create_workspace(root)
    (root / "workspace.json").write_text(
        '{"assets":[],"schema_version":1,"schema_version":1}\n',
        encoding="utf-8",
    )
    with pytest.raises(WorkspaceError, match="cannot load"):
        open_workspace(root)


def test_open_rejects_non_list_assets(tmp_path: Path) -> None:
    root = tmp_path / "project"
    create_workspace(root)
    (root / "workspace.json").write_text(
        '{"assets":{},"schema_version":1}\n',
        encoding="utf-8",
    )
    with pytest.raises(WorkspaceError, match="must be a list"):
        open_workspace(root)


def test_open_rejects_unknown_asset_fields(tmp_path: Path) -> None:
    root = tmp_path / "project"
    create_workspace(root)
    payload = {
        "schema_version": 1,
        "assets": [
            {
                "asset_id": "source",
                "asset_type": "source-file",
                "path": "data/source.txt",
                "external_path": "/forbidden",
            }
        ],
    }
    (root / "workspace.json").write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(WorkspaceError, match="unknown"):
        open_workspace(root)


def _symlink_or_skip(target: Path, link: Path, *, target_is_directory: bool = False) -> None:
    try:
        link.symlink_to(target, target_is_directory=target_is_directory)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symbolic links unavailable: {exc}")


def test_open_rejects_workspace_root_symlink(tmp_path: Path) -> None:
    real_root = tmp_path / "real"
    create_workspace(real_root)
    link_root = tmp_path / "linked"
    _symlink_or_skip(real_root, link_root, target_is_directory=True)
    with pytest.raises(WorkspaceError, match="root"):
        open_workspace(link_root)


def test_save_rejects_symlink_traversal(tmp_path: Path) -> None:
    root = tmp_path / "project"
    outside = tmp_path / "outside"
    create_workspace(root)
    outside.mkdir()
    _symlink_or_skip(outside, root / "linked", target_is_directory=True)

    manifest = _manifest(_asset(path="linked/source.txt"))
    with pytest.raises(WorkspaceError, match="symbolic link"):
        save_workspace(manifest, root, overwrite=True)


def test_open_rejects_symlink_traversal(tmp_path: Path) -> None:
    root = tmp_path / "project"
    outside = tmp_path / "outside"
    create_workspace(root)
    outside.mkdir()
    _symlink_or_skip(outside, root / "linked", target_is_directory=True)

    payload = {
        "schema_version": 1,
        "assets": [
            {
                "asset_id": "source",
                "asset_type": "source-file",
                "path": "linked/source.txt",
            }
        ],
    }
    (root / "workspace.json").write_bytes(canonical_json_bytes(payload) + b"\n")
    with pytest.raises(WorkspaceError, match="symbolic link"):
        open_workspace(root)


def test_workspace_public_import_has_no_gui_or_scientific_side_effects() -> None:
    import subprocess
    import sys

    code = """
import sys
import catalysis_workbench.workspace as workspace
assert workspace.__all__ == [
    "WorkspaceAsset",
    "WorkspaceManifest",
    "create_workspace",
    "open_workspace",
    "save_workspace",
]
for forbidden in ("matplotlib", "pyvista", "vtk"):
    assert not any(name == forbidden or name.startswith(forbidden + ".") for name in sys.modules)
"""
    subprocess.run([sys.executable, "-c", code], check=True, env=os.environ.copy())
