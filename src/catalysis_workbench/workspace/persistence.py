"""File-backed persistence for immutable workspace manifests."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path, PurePosixPath

from catalysis_workbench._canonical_json import (
    CanonicalJSONError,
    canonical_json_bytes,
    loads_strict_json,
)

from .manifest import (
    _MANIFEST_FILENAME,
    WorkspaceError,
    WorkspaceManifest,
    _manifest_from_dict,
    _manifest_to_plain_dict,
)


def _root_path(root: str | Path, *, must_exist: bool) -> Path:
    path = Path(root)
    if path.is_symlink():
        raise WorkspaceError("workspace root must not be a symbolic link")
    if must_exist:
        if not path.exists():
            raise FileNotFoundError(path)
        if not path.is_dir():
            raise NotADirectoryError(path)
    return path


def _owned_path(root: Path, serialized_path: str) -> Path:
    root_resolved = root.resolve(strict=False)
    relative = PurePosixPath(serialized_path)
    candidate = root.joinpath(*relative.parts)

    current = root
    if current.is_symlink():
        raise WorkspaceError("workspace root must not be a symbolic link")
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise WorkspaceError(
                f"workspace-owned path traverses a symbolic link: {serialized_path!r}"
            )

    resolved = candidate.resolve(strict=False)
    if not resolved.is_relative_to(root_resolved):
        raise WorkspaceError(
            f"workspace-owned path escapes workspace root: {serialized_path!r}"
        )
    return candidate


def _validate_owned_paths(manifest: WorkspaceManifest, root: Path) -> None:
    for asset in manifest.assets:
        if asset.policy == "copy":
            _owned_path(root, asset.path)


def _payload(manifest: WorkspaceManifest) -> bytes:
    if not isinstance(manifest, WorkspaceManifest):
        raise TypeError("manifest must be a WorkspaceManifest")
    try:
        return canonical_json_bytes(_manifest_to_plain_dict(manifest)) + b"\n"
    except CanonicalJSONError as exc:
        raise WorkspaceError("workspace manifest cannot be serialized") from exc


def _replace_manifest_atomically(manifest_path: Path, payload: bytes) -> None:
    root = manifest_path.parent
    temporary_path: Path | None = None
    descriptor: int | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".workspace-",
            suffix=".tmp",
            dir=root,
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = None
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, manifest_path)
        temporary_path = None
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def create_workspace(root: str | Path) -> WorkspaceManifest:
    """Create an empty workspace directory and canonical manifest."""

    root_path = _root_path(root, must_exist=False)
    if root_path.exists() or root_path.is_symlink():
        raise FileExistsError(root_path)

    manifest = WorkspaceManifest(schema_version=1, assets=())
    payload = _payload(manifest)

    root_path.mkdir()
    manifest_path = root_path / _MANIFEST_FILENAME
    try:
        with manifest_path.open("xb") as stream:
            stream.write(payload)
    except BaseException:
        try:
            manifest_path.unlink(missing_ok=True)
            root_path.rmdir()
        except OSError:
            pass
        raise
    return manifest


def save_workspace(
    manifest: WorkspaceManifest,
    root: str | Path,
    *,
    overwrite: bool = False,
    expected_manifest_sha256: str | None = None,
) -> None:
    """Persist a validated manifest, optionally refusing stale overwrite callers."""

    if type(overwrite) is not bool:
        raise TypeError("overwrite must be a bool")
    if expected_manifest_sha256 is not None and (
        type(expected_manifest_sha256) is not str or len(expected_manifest_sha256) != 64
    ):
        raise WorkspaceError("expected_manifest_sha256 must be a 64-character SHA-256")
    payload = _payload(manifest)
    root_path = _root_path(root, must_exist=True)
    _validate_owned_paths(manifest, root_path)

    manifest_path = root_path / _MANIFEST_FILENAME
    if manifest_path.is_symlink():
        raise WorkspaceError("workspace manifest file must not be a symbolic link")
    if expected_manifest_sha256 is not None:
        observed = open_workspace(root_path)
        if observed.manifest_sha256 != expected_manifest_sha256:
            raise WorkspaceError("workspace changed outside the writer; reopen explicitly")
    if overwrite:
        _replace_manifest_atomically(manifest_path, payload)
        return
    with manifest_path.open("xb") as stream:
        stream.write(payload)


def open_workspace(root: str | Path) -> WorkspaceManifest:
    """Strictly load and validate a workspace manifest from an explicit root."""

    root_path = _root_path(root, must_exist=True)
    manifest_path = root_path / _MANIFEST_FILENAME
    if manifest_path.is_symlink():
        raise WorkspaceError("workspace manifest file must not be a symbolic link")
    if not manifest_path.exists():
        raise FileNotFoundError(manifest_path)
    if not manifest_path.is_file():
        raise WorkspaceError("workspace manifest path must be a regular file")

    try:
        text = manifest_path.read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise WorkspaceError("workspace manifest is not valid UTF-8") from exc
    try:
        value = loads_strict_json(text)
    except CanonicalJSONError as exc:
        raise WorkspaceError("cannot load workspace manifest") from exc

    manifest = _manifest_from_dict(value)
    _validate_owned_paths(manifest, root_path)
    return manifest
