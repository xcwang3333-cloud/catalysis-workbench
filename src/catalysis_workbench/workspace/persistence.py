"""File-backed persistence for immutable workspace manifests."""

from __future__ import annotations

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
        _owned_path(root, asset.path)


def _payload(manifest: WorkspaceManifest) -> bytes:
    if not isinstance(manifest, WorkspaceManifest):
        raise TypeError("manifest must be a WorkspaceManifest")
    try:
        return canonical_json_bytes(_manifest_to_plain_dict(manifest)) + b"\n"
    except CanonicalJSONError as exc:
        raise WorkspaceError("workspace manifest cannot be serialized") from exc


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
) -> None:
    """Persist a validated workspace manifest at the explicit workspace root."""

    if type(overwrite) is not bool:
        raise TypeError("overwrite must be a bool")
    payload = _payload(manifest)
    root_path = _root_path(root, must_exist=True)
    _validate_owned_paths(manifest, root_path)

    manifest_path = root_path / _MANIFEST_FILENAME
    if manifest_path.is_symlink():
        raise WorkspaceError("workspace manifest file must not be a symbolic link")
    mode = "wb" if overwrite else "xb"
    with manifest_path.open(mode) as stream:
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
