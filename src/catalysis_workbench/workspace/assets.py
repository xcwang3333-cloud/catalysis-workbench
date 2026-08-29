"""Explicit file import, batch copy, and exact asset verification for local workspaces."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Sequence
from dataclasses import dataclass
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

__all__ = [
    "CopyAssetRequest",
    "import_asset",
    "import_copy_assets_batch",
    "verify_copy_asset",
]


@dataclass(frozen=True, slots=True)
class CopyAssetRequest:
    """One explicit workspace-owned copy requested as part of an atomic manifest batch."""

    source: str | Path
    asset_id: str
    asset_type: str
    destination: str


def _selected_source(source: str | Path) -> Path:
    path = Path(source)
    if path.is_symlink():
        raise WorkspaceError("asset source must not be a symbolic link")
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


def _remove_created_directories(created_directories: tuple[Path, ...]) -> None:
    for directory in reversed(created_directories):
        try:
            directory.rmdir()
        except OSError:
            break


def _copy_selected_file(
    source: Path,
    destination: Path,
    root: Path,
) -> tuple[str, tuple[Path, ...]]:
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
        return digest.hexdigest(), tuple(created_directories)
    except BaseException:
        if created_file:
            destination.unlink(missing_ok=True)
        _remove_created_directories(tuple(created_directories))
        raise


def _rollback_copy(
    destination: Path,
    created_directories: tuple[Path, ...],
) -> None:
    destination.unlink(missing_ok=True)
    _remove_created_directories(created_directories)


def _asset_by_id(manifest: WorkspaceManifest, asset_id: str) -> WorkspaceAsset:
    checked = _identifier(asset_id, label="asset_id")
    for asset in manifest.assets:
        if asset.asset_id == checked:
            return asset
    raise WorkspaceError(f"unknown workspace asset_id: {checked!r}")


def verify_copy_asset(
    root: str | Path,
    asset_id: str,
    *,
    expected_type: str | None = None,
) -> tuple[WorkspaceAsset, Path]:
    """Return one workspace-owned asset only after its current bytes match the catalog."""

    root_path = _root_path(root, must_exist=True)
    manifest = open_workspace(root_path)
    asset = _asset_by_id(manifest, asset_id)
    if asset.policy != "copy":
        raise WorkspaceError(f"asset {asset.asset_id!r} must be workspace-owned")
    if expected_type is not None and asset.asset_type != expected_type:
        raise WorkspaceError(
            f"asset {asset.asset_id!r} must have asset_type {expected_type!r}"
        )
    if asset.content_sha256 is None:
        raise WorkspaceError(f"asset {asset.asset_id!r} requires content_sha256")
    path = _owned_path(root_path, asset.path)
    if path.is_symlink():
        raise WorkspaceError(f"asset {asset.asset_id!r} must not be a symbolic link")
    if not path.exists():
        raise FileNotFoundError(path)
    if not path.is_file():
        raise WorkspaceError(f"asset {asset.asset_id!r} path must be a regular file")
    observed = _sha256_file(path)
    if observed != asset.content_sha256:
        raise WorkspaceError(
            f"asset {asset.asset_id!r} content digest does not match workspace catalog"
        )
    return asset, path


def import_copy_assets_batch(
    root: str | Path,
    requests: Sequence[CopyAssetRequest],
    *,
    expected_manifest_sha256: str | None = None,
) -> WorkspaceManifest:
    """Copy several files and publish exactly one manifest revision, or roll back.

    All destinations and catalog collisions are preflighted before bytes are copied.
    The manifest observed before copying is checked again immediately before commit so
    an external catalog mutation causes a fail-closed rollback.
    """

    if isinstance(requests, (str, bytes)) or not isinstance(requests, Sequence):
        raise TypeError("requests must be an ordered sequence of CopyAssetRequest values")
    items = tuple(requests)
    if not all(isinstance(item, CopyAssetRequest) for item in items):
        raise TypeError("requests must contain CopyAssetRequest values")

    root_path = _root_path(root, must_exist=True)
    manifest = open_workspace(root_path)
    if (
        expected_manifest_sha256 is not None
        and manifest.manifest_sha256 != expected_manifest_sha256
    ):
        raise WorkspaceError("workspace changed outside the batch import; reopen explicitly")
    if not items:
        return manifest

    checked: list[tuple[Path, str, str, str, Path]] = []
    requested_ids: set[str] = set()
    requested_locations: set[str] = set()
    for item in items:
        asset_id = _identifier(item.asset_id, label="asset_id")
        asset_type = _identifier(item.asset_type, label="asset_type")
        destination = _workspace_owned_path(item.destination)
        if asset_id in requested_ids:
            raise WorkspaceError(f"workspace asset_id collision: {asset_id!r}")
        if destination in requested_locations:
            raise WorkspaceError(f"workspace asset location collision: {destination!r}")
        requested_ids.add(asset_id)
        requested_locations.add(destination)
        _preflight_asset_key(manifest, asset_id)
        _preflight_location(manifest, policy="copy", path=destination)
        source = _selected_source(item.source)
        destination_path = _owned_path(root_path, destination)
        if destination_path.exists() or destination_path.is_symlink():
            raise WorkspaceError(
                f"workspace copy destination already exists: {destination!r}"
            )
        checked.append((source, asset_id, asset_type, destination, destination_path))

    copied: list[tuple[Path, tuple[Path, ...]]] = []
    new_assets: list[WorkspaceAsset] = []
    try:
        for source, asset_id, asset_type, destination, destination_path in checked:
            digest, created_directories = _copy_selected_file(
                source, destination_path, root_path
            )
            copied.append((destination_path, created_directories))
            new_assets.append(
                WorkspaceAsset(
                    asset_id=asset_id,
                    asset_type=asset_type,
                    path=destination,
                    policy="copy",
                    content_sha256=digest,
                )
            )

        observed = open_workspace(root_path)
        if observed.manifest_sha256 != manifest.manifest_sha256:
            raise WorkspaceError("workspace changed while batch assets were being copied")
        updated = WorkspaceManifest(
            schema_version=manifest.schema_version,
            assets=(*manifest.assets, *new_assets),
        )
        save_workspace(
            updated,
            root_path,
            overwrite=True,
            expected_manifest_sha256=manifest.manifest_sha256,
        )
    except BaseException:
        for destination_path, created_directories in reversed(copied):
            _rollback_copy(destination_path, created_directories)
        raise

    reopened = open_workspace(root_path)
    if reopened != updated:
        raise WorkspaceError("workspace changed concurrently after batch import commit")
    return reopened


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
        save_workspace(
            updated,
            root_path,
            overwrite=True,
            expected_manifest_sha256=manifest.manifest_sha256,
        )
        return updated

    if type(destination) is not str or not destination:
        raise WorkspaceError("copy asset import requires an explicit destination")
    return import_copy_assets_batch(
        root_path,
        (
            CopyAssetRequest(
                source=source_path,
                asset_id=checked_asset_id,
                asset_type=checked_asset_type,
                destination=destination,
            ),
        ),
        expected_manifest_sha256=manifest.manifest_sha256,
    )
