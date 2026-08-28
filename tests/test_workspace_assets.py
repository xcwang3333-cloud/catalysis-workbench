from __future__ import annotations

import hashlib
import os
import subprocess
import sys
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
from catalysis_workbench.workspace.assets import import_asset
from catalysis_workbench.workspace.manifest import WorkspaceError


def _source(tmp_path: Path, name: str = "source.bin", payload: bytes = b"source-bytes") -> Path:
    path = tmp_path / name
    path.write_bytes(payload)
    return path


def test_reference_import_records_explicit_external_path_and_digest(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    source = _source(tmp_path)
    create_workspace(root)

    manifest = import_asset(
        root,
        source,
        asset_id="source-ref",
        asset_type="source-file",
        policy="reference",
    )

    asset = manifest.assets[0]
    assert asset.asset_id == "source-ref"
    assert asset.asset_type == "source-file"
    assert asset.policy == "reference"
    assert asset.path == str(source.absolute())
    assert asset.content_sha256 == hashlib.sha256(source.read_bytes()).hexdigest()
    assert source.read_bytes() == b"source-bytes"
    assert open_workspace(root) == manifest


def test_copy_import_retains_exact_bytes_and_source(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    source = _source(tmp_path, payload=b"\x00binary\xffpayload")
    create_workspace(root)

    manifest = import_asset(
        root,
        source,
        asset_id="source-copy",
        asset_type="explicit-user-type",
        policy="copy",
        destination="data/copied.dat",
    )

    asset = manifest.assets[0]
    copied = root / "data" / "copied.dat"
    assert asset.policy == "copy"
    assert asset.path == "data/copied.dat"
    assert asset.asset_type == "explicit-user-type"
    assert copied.read_bytes() == source.read_bytes()
    assert asset.content_sha256 == hashlib.sha256(copied.read_bytes()).hexdigest()
    assert source.read_bytes() == b"\x00binary\xffpayload"
    assert open_workspace(root) == manifest


def test_import_order_is_literal_call_order(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    first = _source(tmp_path, "first.txt", b"first")
    second = _source(tmp_path, "second.txt", b"second")
    create_workspace(root)

    import_asset(
        root,
        second,
        asset_id="second",
        asset_type="source-file",
        policy="reference",
    )
    manifest = import_asset(
        root,
        first,
        asset_id="first",
        asset_type="source-file",
        policy="copy",
        destination="assets/first.txt",
    )

    assert tuple(asset.asset_id for asset in manifest.assets) == ("second", "first")


@pytest.mark.parametrize("policy", ["", "COPY", "move", "Reference"])
def test_import_policy_is_explicit_and_closed(policy: str, tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    source = _source(tmp_path)
    create_workspace(root)

    with pytest.raises(WorkspaceError, match="policy"):
        import_asset(
            root,
            source,
            asset_id="source",
            asset_type="source-file",
            policy=policy,
        )


def test_reference_rejects_destination_before_manifest_mutation(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    source = _source(tmp_path)
    original = create_workspace(root)

    with pytest.raises(WorkspaceError, match="does not accept"):
        import_asset(
            root,
            source,
            asset_id="source",
            asset_type="source-file",
            policy="reference",
            destination="data/source.bin",
        )

    assert open_workspace(root) == original


@pytest.mark.parametrize("destination", [None, ""])
def test_copy_requires_explicit_destination(
    destination: str | None,
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspace"
    source = _source(tmp_path)
    original = create_workspace(root)

    with pytest.raises(WorkspaceError, match="explicit destination"):
        import_asset(
            root,
            source,
            asset_id="source",
            asset_type="source-file",
            policy="copy",
            destination=destination,
        )

    assert open_workspace(root) == original


@pytest.mark.parametrize(
    "destination",
    [
        "../escape.bin",
        "/absolute.bin",
        "C:/absolute.bin",
        "data/../escape.bin",
        "data//source.bin",
        "data\\source.bin",
        "workspace.json",
    ],
)
def test_copy_destination_reuses_block_one_confinement(
    destination: str,
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspace"
    source = _source(tmp_path)
    create_workspace(root)

    with pytest.raises(WorkspaceError):
        import_asset(
            root,
            source,
            asset_id="source",
            asset_type="source-file",
            policy="copy",
            destination=destination,
        )

    assert tuple(root.iterdir()) == (root / "workspace.json",)


def test_asset_id_collision_fails_before_copy_mutation(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    first = _source(tmp_path, "first.txt", b"first")
    second = _source(tmp_path, "second.txt", b"second")
    create_workspace(root)
    import_asset(
        root,
        first,
        asset_id="same",
        asset_type="source-file",
        policy="reference",
    )

    with pytest.raises(WorkspaceError, match="asset_id collision"):
        import_asset(
            root,
            second,
            asset_id="same",
            asset_type="source-file",
            policy="copy",
            destination="data/second.txt",
        )

    assert not (root / "data").exists()
    assert len(open_workspace(root).assets) == 1


def test_copy_destination_collision_fails_before_source_read_or_mutation(
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspace"
    source = _source(tmp_path)
    create_workspace(root)
    destination = root / "data"
    destination.mkdir()
    existing = destination / "source.bin"
    existing.write_bytes(b"existing")

    with pytest.raises(WorkspaceError, match="already exists"):
        import_asset(
            root,
            source,
            asset_id="copy",
            asset_type="source-file",
            policy="copy",
            destination="data/source.bin",
        )

    assert existing.read_bytes() == b"existing"
    assert open_workspace(root).assets == ()


def test_catalog_location_collision_fails_before_copy_mutation(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    (root / "data").mkdir()
    (root / "data" / "tracked.bin").write_bytes(b"tracked")
    tracked = WorkspaceManifest(
        schema_version=1,
        assets=(
            WorkspaceAsset(
                asset_id="tracked",
                asset_type="source-file",
                path="data/tracked.bin",
            ),
        ),
    )
    save_workspace(tracked, root, overwrite=True)

    replacement = _source(tmp_path, "replacement.bin", b"replacement")
    with pytest.raises(WorkspaceError, match="location collision"):
        import_asset(
            root,
            replacement,
            asset_id="replacement",
            asset_type="source-file",
            policy="copy",
            destination="data/tracked.bin",
        )

    assert (root / "data" / "tracked.bin").read_bytes() == b"tracked"
    assert open_workspace(root) == tracked


def test_reference_location_collision_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    source = _source(tmp_path)
    create_workspace(root)
    import_asset(
        root,
        source,
        asset_id="first",
        asset_type="source-file",
        policy="reference",
    )

    with pytest.raises(WorkspaceError, match="location collision"):
        import_asset(
            root,
            source,
            asset_id="second",
            asset_type="different-explicit-type",
            policy="reference",
        )


def test_missing_source_fails_without_catalog_mutation(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    original = create_workspace(root)

    with pytest.raises(FileNotFoundError):
        import_asset(
            root,
            tmp_path / "missing.bin",
            asset_id="missing",
            asset_type="source-file",
            policy="reference",
        )

    assert open_workspace(root) == original


def test_directory_source_is_not_recursively_scanned(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    source_directory = tmp_path / "source-directory"
    source_directory.mkdir()
    (source_directory / "nested.txt").write_text("nested", encoding="utf-8")
    original = create_workspace(root)

    with pytest.raises(WorkspaceError, match="existing file"):
        import_asset(
            root,
            source_directory,
            asset_id="directory",
            asset_type="source-file",
            policy="copy",
            destination="data/nested.txt",
        )

    assert open_workspace(root) == original
    assert not (root / "data").exists()


def test_copy_rejects_workspace_symlink_destination_traversal(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    outside = tmp_path / "outside"
    outside.mkdir()
    source = _source(tmp_path)
    create_workspace(root)
    link = root / "linked"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symbolic links unavailable: {exc}")

    with pytest.raises(WorkspaceError, match="symbolic link"):
        import_asset(
            root,
            source,
            asset_id="source",
            asset_type="source-file",
            policy="copy",
            destination="linked/source.bin",
        )

    assert not (outside / "source.bin").exists()


def test_reference_manifest_is_not_treated_as_workspace_owned_path(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    source = _source(tmp_path)
    create_workspace(root)

    manifest = import_asset(
        root,
        source,
        asset_id="external",
        asset_type="source-file",
        policy="reference",
    )

    restored = open_workspace(root)
    assert restored == manifest
    assert restored.assets[0].path.startswith(str(tmp_path))


def test_reference_asset_requires_content_digest() -> None:
    with pytest.raises(WorkspaceError, match="require content_sha256"):
        WorkspaceAsset(
            asset_id="external",
            asset_type="source-file",
            path="/tmp/external.bin",
            policy="reference",
        )


@pytest.mark.parametrize(
    "digest",
    [
        "",
        "0" * 63,
        "0" * 65,
        "G" * 64,
        "A" * 64,
    ],
)
def test_content_digest_is_strict_lowercase_sha256(digest: str) -> None:
    with pytest.raises(WorkspaceError, match="content_sha256"):
        WorkspaceAsset(
            asset_id="copy",
            asset_type="source-file",
            path="data/source.bin",
            content_sha256=digest,
        )


def test_legacy_block_one_asset_serialization_and_digest_remain_stable() -> None:
    asset = WorkspaceAsset(
        asset_id="legacy",
        asset_type="source-file",
        path="data/legacy.txt",
    )
    manifest = WorkspaceManifest(schema_version=1, assets=(asset,))
    legacy = {
        "schema_version": 1,
        "assets": [
            {
                "asset_id": "legacy",
                "asset_type": "source-file",
                "path": "data/legacy.txt",
            }
        ],
    }
    expected = hashlib.sha256(canonical_json_bytes(legacy)).hexdigest()
    assert manifest.manifest_sha256 == expected


def test_copy_digest_is_part_of_manifest_identity() -> None:
    first = WorkspaceManifest(
        schema_version=1,
        assets=(
            WorkspaceAsset(
                asset_id="copy",
                asset_type="source-file",
                path="data/source.bin",
                content_sha256="0" * 64,
            ),
        ),
    )
    second = WorkspaceManifest(
        schema_version=1,
        assets=(
            WorkspaceAsset(
                asset_id="copy",
                asset_type="source-file",
                path="data/source.bin",
                content_sha256="1" * 64,
            ),
        ),
    )
    assert first.manifest_sha256 != second.manifest_sha256


def test_reference_and_copy_locations_are_distinct_domains(tmp_path: Path) -> None:
    absolute = str((tmp_path / "same.txt").absolute())
    reference = WorkspaceAsset(
        asset_id="reference",
        asset_type="source-file",
        path=absolute,
        policy="reference",
        content_sha256="0" * 64,
    )
    copied = WorkspaceAsset(
        asset_id="copy",
        asset_type="source-file",
        path="same.txt",
        policy="copy",
        content_sha256="0" * 64,
    )
    manifest = WorkspaceManifest(schema_version=1, assets=(reference, copied))
    assert len(manifest.assets) == 2


def test_asset_module_import_has_no_scientific_or_presentation_side_effects() -> None:
    code = """
import sys
import catalysis_workbench.workspace.assets as assets
assert assets.__all__ == ["import_asset"]
for forbidden in ("matplotlib", "pyvista", "vtk", "pymatgen"):
    assert not any(name == forbidden or name.startswith(forbidden + ".") for name in sys.modules)
"""
    subprocess.run([sys.executable, "-c", code], check=True, env=os.environ.copy())
