"""Explicit file import and catalog operations for local workspaces."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from .manifest import (
    WorkspaceAsset,
    WorkspaceError,
    WorkspaceManifest,
    _external_reference_path,
    _identifier,
    _workspace_owned_path,
)
from .persistence import _owned_path, _root_path, open_workspace, save_workspace

__all__ = ["import_asset"]


def _selected_source(source: str | Path) -> Path:
    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(path)
    if not path.is_file():
        raise WorkspaceError("asset source must be an existing file")
    return path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _preflight_asset_key(manifest: WorkspaceManifest, asset_id: str) -> None:
    if any(asset.asset_id == asset_id for asset in manifest.assets):
        raise WorkspaceError(f"workspace asset_id collision: {asset_id!r}")


def _preflight_location(
    manifest: WorkspaceManifest,
    *,
    policy: str,
    path: str,
) -> None:
    if any(asset.policy == policy and asset.path == path for asset in manifest.assets):
        raise WorkspaceError(f"workspace asset location collision: {path!r}")


def _absolute_external_path(source: Path) -> str:
    return _external_reference_path(str(source.absolute()))


def _missing_parent_directories(root: Path, destination: Path) -> tuple[Path, ...]:
    missing: list[Path] = []
    current = destination.parent
    while current != root and not current.exists():
        missing.append(current)
        current = current.parent
    if current != root:
        if current.is_symlink():
            raise WorkspaceError("workspace-owned destination traverses a symbolic link")
        if not current.is_dir():
            raise WorkspaceError("workspace-owned destination parent is not a directory")
    return tuple(reversed(missing))


def _copy_selected_file(source: Path, destination: Path, root: Path) -> str:
    if destination.exists() or destination.is_symlink():
        raise WorkspaceError(f"workspace copy destination already exists: {destination!s}")

    created_directories: list[Path] = []
    created_file = False
    digest = hashlib.sha256()
    try:
        for directory in _missing_parent_directories(root, destination):
            directory.mkdir()
            created_directories.append(directory)

        with source.open("rb") as source_stream, destination.open("xb") as destination_stream:
            created_file = True
            while True:
                chunk = source_stream.read(1024 * 1024)
                if not chunk:
                    break
                destination_stream.write(chunk)
                digest.update(chunk)
            destination_stream.flush()
            os.fsync(destination_stream.fileno())
        return digest.hexdigest()
    except BaseException:
        if created_file:
            destination.unlink(missing_ok=True)
        for directory in reversed(created_directories):
            try:
                directory.rmdir()
            except OSError:
                break
        raise


def import_asset(
    root: str | Path,
    source: str | Path,
    *,
    asset_id: str,
    asset_type: str,
    policy: str,
    destination: str | None = None,
) -> WorkspaceManifest:
    """Import one explicitly selected file into the persistent workspace catalog."""

    checked_asset_id = _identifier(asset_id, label="asset_id")
    checked_asset_type = _identifier(asset_type, label="asset_type")
    if type(policy) is not str or policy not in {"reference", "copy"}:
        raise WorkspaceError("asset import policy must be 'reference' or 'copy'")

    root_path = _root_path(root, must_exist=True)
    manifest = open_workspace(root_path)
    _preflight_asset_key(manifest, checked_asset_id)
    source_path = _selected_source(source)

    if policy == "reference":
        if destination is not None:
            raise WorkspaceError("reference asset import does not accept a destination")
        reference_path = _absolute_external_path(source_path)
        _preflight_location(manifest, policy="reference", path=reference_path)
        digest = _sha256_file(source_path)
        asset = WorkspaceAsset(
            asset_id=checked_asset_id,
            asset_type=checked_asset_type,
            path=reference_path,
            policy="reference",
            content_sha256=digest,
        )
        updated = WorkspaceManifest(
            schema_version=manifest.schema_version,
            assets=(*manifest.assets, asset),
        )
        save_workspace(updated, root_path, overwrite=True)
        return updated

    if type(destination) is not str or not destination:
        raise WorkspaceError("copy asset import requires an explicit destination")
    serialized_destination = _workspace_owned_path(destination)
    _preflight_location(manifest, policy="copy", path=serialized_destination)
    destination_path = _owned_path(root_path, serialized_destination)
    if destination_path.exists() or destination_path.is_symlink():
        raise WorkspaceError(
            f"workspace copy destination already exists: {serialized_destination!r}"
        )

    digest = _copy_selected_file(source_path, destination_path, root_path)
    asset = WorkspaceAsset(
        asset_id=checked_asset_id,
        asset_type=checked_asset_type,
        path=serialized_destination,
        policy="copy",
        content_sha256=digest,
    )
    updated = WorkspaceManifest(
        schema_version=manifest.schema_version,
        assets=(*manifest.assets, asset),
    )
    try:
        save_workspace(updated, root_path, overwrite=True)
    except BaseException:
        destination_path.unlink(missing_ok=True)
        parent = destination_path.parent
        while parent != root_path:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent
        raise
    return updated
