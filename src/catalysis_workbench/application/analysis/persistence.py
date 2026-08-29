"""Strict file-backed persistence for v1.1 analysis projects."""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from catalysis_workbench._canonical_json import (
    CanonicalJSONError,
    canonical_json_bytes,
    loads_strict_json,
)
from catalysis_workbench.workspace import create_workspace, open_workspace
from catalysis_workbench.workspace.assets import (
    CopyAssetRequest,
    import_copy_assets_batch,
    verify_copy_asset,
)
from catalysis_workbench.workspace.manifest import WorkspaceError

from .data import DataSeriesSpec
from .document import (
    AnalysisDocument,
    AnalysisDocumentError,
    _document_from_dict,
    _document_to_plain_dict,
)
from .materialization import verify_source_bytes

_PROJECT_FILENAME = "project.json"
_PROJECT_FIELDS = frozenset({"schema_version", "document"})
_EMPTY_WORKSPACE_PAYLOAD = canonical_json_bytes({"schema_version": 1, "assets": []}) + b"\n"
_RAW_ASSET_TYPE = "analysis_raw_tabular"


class AnalysisProjectError(ValueError):
    """Raised when a v1.1 analysis project is invalid or changes concurrently."""


class LegacyWorkspaceError(AnalysisProjectError):
    """Raised when a v1.0 workspace has no v1.1 analysis project document."""


@dataclass(frozen=True, slots=True)
class AnalysisProjectSnapshot:
    """One exact project/document/workspace identity observed on disk."""

    root: Path
    document: AnalysisDocument
    workspace_manifest_sha256: str
    project_file_sha256: str


def _project_to_plain_dict(document: AnalysisDocument) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "document": _document_to_plain_dict(document),
    }


def _project_payload(document: AnalysisDocument) -> bytes:
    try:
        return canonical_json_bytes(_project_to_plain_dict(document)) + b"\n"
    except CanonicalJSONError as exc:
        raise AnalysisProjectError("analysis project cannot be serialized") from exc


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _project_path(root: Path) -> Path:
    project_path = root / _PROJECT_FILENAME
    if project_path.is_symlink():
        raise AnalysisProjectError("project.json must not be a symbolic link")
    return project_path


def _decode_project_payload(payload: bytes) -> AnalysisDocument:
    try:
        text = payload.decode("utf-8")
    except UnicodeError as exc:
        raise AnalysisProjectError("project.json is not valid UTF-8") from exc
    try:
        value = loads_strict_json(text)
    except CanonicalJSONError as exc:
        raise AnalysisProjectError("cannot load project.json") from exc
    if not isinstance(value, dict):
        raise AnalysisProjectError("serialized analysis project must be an object")
    if not all(type(key) is str for key in value):
        raise AnalysisProjectError("analysis project field names must be strings")
    fields = set(value)
    missing = sorted(_PROJECT_FIELDS - fields)
    unknown = sorted(fields - _PROJECT_FIELDS)
    if missing or unknown:
        raise AnalysisProjectError(
            f"invalid analysis project fields; missing={missing!r}, unknown={unknown!r}"
        )
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise AnalysisProjectError("analysis project schema_version must be the integer 1")
    try:
        return _document_from_dict(value["document"])
    except AnalysisDocumentError as exc:
        raise AnalysisProjectError(str(exc)) from exc


def _read_project_document(root: Path) -> tuple[AnalysisDocument, str]:
    project_path = _project_path(root)
    if not project_path.exists():
        raise LegacyWorkspaceError(
            "this directory is a legacy CatalysisWorkbench workspace and does not "
            "contain a v1.1 project document"
        )
    if not project_path.is_file():
        raise AnalysisProjectError("project.json must be a regular file")
    payload = project_path.read_bytes()
    return _decode_project_payload(payload), _sha256_bytes(payload)


def _snapshot_once(root: Path) -> AnalysisProjectSnapshot:
    manifest = open_workspace(root)
    document, project_file_sha256 = _read_project_document(root)
    return AnalysisProjectSnapshot(
        root=root.resolve(),
        document=document,
        workspace_manifest_sha256=manifest.manifest_sha256,
        project_file_sha256=project_file_sha256,
    )


def _raw_sources(document: AnalysisDocument) -> tuple[DataSeriesSpec, ...]:
    representatives: dict[str, DataSeriesSpec] = {}
    for item in document.data_series:
        existing = representatives.get(item.source.content_sha256)
        if existing is None:
            representatives[item.source.content_sha256] = item
            continue
        if existing.source != item.source:
            raise AnalysisProjectError(
                "one raw content digest is associated with inconsistent source metadata"
            )
    return tuple(representatives.values())


def _source_location(
    source_sha256: str,
    source_locations: Mapping[str, str | Path] | None,
) -> Path:
    if source_locations is None or source_sha256 not in source_locations:
        raise AnalysisProjectError(
            f"raw source {source_sha256} is not available; re-add the source file"
        )
    return Path(source_locations[source_sha256])


def _ensure_raw_assets(
    document: AnalysisDocument,
    root: Path,
    *,
    source_locations: Mapping[str, str | Path] | None,
    expected_manifest_sha256: str,
) -> str:
    manifest = open_workspace(root)
    if manifest.manifest_sha256 != expected_manifest_sha256:
        raise AnalysisProjectError("workspace changed outside the analysis session; reopen explicitly")
    by_id = {asset.asset_id: asset for asset in manifest.assets}
    requests: list[CopyAssetRequest] = []
    for representative in _raw_sources(document):
        source = representative.source
        asset_id = source.workspace_asset_id
        existing = by_id.get(asset_id)
        if existing is not None:
            if (
                existing.asset_type != _RAW_ASSET_TYPE
                or existing.policy != "copy"
                or existing.path != source.workspace_destination
                or existing.content_sha256 != source.content_sha256
            ):
                raise AnalysisProjectError(
                    f"workspace raw asset {asset_id!r} conflicts with analysis source identity"
                )
            try:
                verify_copy_asset(root, asset_id, expected_type=_RAW_ASSET_TYPE)
            except (WorkspaceError, OSError) as exc:
                raise AnalysisProjectError(str(exc)) from exc
            continue
        location = _source_location(source.content_sha256, source_locations)
        try:
            verify_source_bytes(representative, location)
        except (ValueError, OSError) as exc:
            raise AnalysisProjectError(str(exc)) from exc
        requests.append(
            CopyAssetRequest(
                source=location,
                asset_id=asset_id,
                asset_type=_RAW_ASSET_TYPE,
                destination=source.workspace_destination,
            )
        )
    if not requests:
        return manifest.manifest_sha256
    try:
        updated = import_copy_assets_batch(
            root,
            tuple(requests),
            expected_manifest_sha256=manifest.manifest_sha256,
        )
    except (WorkspaceError, OSError) as exc:
        raise AnalysisProjectError(str(exc)) from exc
    return updated.manifest_sha256


def open_analysis_project(root: str | Path) -> AnalysisProjectSnapshot:
    """Load a project only after two exact workspace/project observations agree."""

    root_path = Path(root)
    first = _snapshot_once(root_path)
    second = _snapshot_once(root_path)
    if (
        first.workspace_manifest_sha256 != second.workspace_manifest_sha256
        or first.project_file_sha256 != second.project_file_sha256
    ):
        raise AnalysisProjectError("analysis project changed while it was being opened; retry")
    return second


def _replace_project_atomically(project_path: Path, payload: bytes) -> None:
    descriptor: int | None = None
    temporary_path: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".project-",
            suffix=".tmp",
            dir=project_path.parent,
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = None
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, project_path)
        temporary_path = None
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def save_analysis_project(
    document: AnalysisDocument,
    root: str | Path,
    *,
    expected_project_file_sha256: str,
    expected_workspace_manifest_sha256: str,
    source_locations: Mapping[str, str | Path] | None = None,
) -> AnalysisProjectSnapshot:
    """Persist document and missing raw copies only from exact observed identities."""

    if not isinstance(document, AnalysisDocument):
        raise TypeError("document must be an AnalysisDocument")
    root_path = Path(root)
    before = _snapshot_once(root_path)
    if before.workspace_manifest_sha256 != expected_workspace_manifest_sha256:
        raise AnalysisProjectError(
            "workspace changed outside the analysis session; reopen explicitly"
        )
    if before.project_file_sha256 != expected_project_file_sha256:
        raise AnalysisProjectError(
            "project.json changed outside the analysis session; reopen explicitly"
        )

    workspace_sha = _ensure_raw_assets(
        document,
        root_path,
        source_locations=source_locations,
        expected_manifest_sha256=before.workspace_manifest_sha256,
    )
    _, observed_project_sha = _read_project_document(root_path)
    if observed_project_sha != expected_project_file_sha256:
        raise AnalysisProjectError(
            "project.json changed outside the analysis session while raw data were saved"
        )
    if open_workspace(root_path).manifest_sha256 != workspace_sha:
        raise AnalysisProjectError("workspace changed concurrently while raw data were saved")

    project_path = _project_path(root_path)
    payload = _project_payload(document)
    _replace_project_atomically(project_path, payload)

    observed = _snapshot_once(root_path)
    expected_project_sha = _sha256_bytes(payload)
    if observed.project_file_sha256 != expected_project_sha or observed.document != document:
        raise AnalysisProjectError("project.json changed concurrently while it was being saved")
    if observed.workspace_manifest_sha256 != workspace_sha:
        raise AnalysisProjectError(
            "workspace changed concurrently while project.json was being saved"
        )
    return observed


def _rollback_new_workspace(root: Path, *, expected_workspace_payload: bytes) -> None:
    """Remove only the exact untouched workspace created by this failed first save."""

    try:
        entries = tuple(root.iterdir())
    except (FileNotFoundError, NotADirectoryError):
        return
    workspace_path = root / "workspace.json"
    if (
        len(entries) != 1
        or entries[0] != workspace_path
        or workspace_path.is_symlink()
        or not workspace_path.is_file()
    ):
        return
    try:
        if workspace_path.read_bytes() != expected_workspace_payload:
            return
    except OSError:
        return
    workspace_path.unlink(missing_ok=True)
    try:
        root.rmdir()
    except OSError:
        pass


def _create_empty_project_compat(
    document: AnalysisDocument,
    root_path: Path,
) -> AnalysisProjectSnapshot:
    """Preserve Block-1 rollback semantics for projects without mapped data."""

    create_workspace(root_path)
    project_path = root_path / _PROJECT_FILENAME
    payload = _project_payload(document)
    wrote_exact_project = False
    try:
        if project_path.is_symlink() or project_path.exists():
            raise AnalysisProjectError("project.json unexpectedly exists in the new workspace")
        with project_path.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        wrote_exact_project = True
        return open_analysis_project(root_path)
    except BaseException:
        if wrote_exact_project and project_path.exists() and not project_path.is_symlink():
            try:
                if project_path.is_file() and project_path.read_bytes() == payload:
                    project_path.unlink()
            except OSError:
                pass
        _rollback_new_workspace(
            root_path,
            expected_workspace_payload=_EMPTY_WORKSPACE_PAYLOAD,
        )
        raise


def _create_staged_project(
    document: AnalysisDocument,
    root_path: Path,
    *,
    source_locations: Mapping[str, str | Path] | None,
) -> AnalysisProjectSnapshot:
    parent = root_path.parent
    if not parent.exists():
        raise FileNotFoundError(parent)
    if not parent.is_dir():
        raise NotADirectoryError(parent)

    staging = Path(
        tempfile.mkdtemp(prefix=f".{root_path.name}-staging-", dir=parent)
    )
    try:
        workspace = create_workspace(staging / "workspace-root")
        # Move the freshly created workspace contents up one level so the staging
        # directory itself is the eventual project root without ever exposing the
        # final destination prematurely.
        workspace_dir = staging / "workspace-root"
        (workspace_dir / "workspace.json").replace(staging / "workspace.json")
        workspace_dir.rmdir()
        workspace = open_workspace(staging)
        workspace_sha = _ensure_raw_assets(
            document,
            staging,
            source_locations=source_locations,
            expected_manifest_sha256=workspace.manifest_sha256,
        )
        payload = _project_payload(document)
        project_path = staging / _PROJECT_FILENAME
        with project_path.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        staged_snapshot = open_analysis_project(staging)
        if staged_snapshot.workspace_manifest_sha256 != workspace_sha:
            raise AnalysisProjectError("staged workspace identity changed during first save")
        for representative in _raw_sources(document):
            verify_copy_asset(
                staging,
                representative.source.workspace_asset_id,
                expected_type=_RAW_ASSET_TYPE,
            )
        os.replace(staging, root_path)
        return open_analysis_project(root_path)
    except BaseException:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging, ignore_errors=True)
        raise


def create_analysis_project(
    document: AnalysisDocument,
    root: str | Path,
    *,
    source_locations: Mapping[str, str | Path] | None = None,
) -> AnalysisProjectSnapshot:
    """Create a new project; mapped data are staged and verified before publication."""

    if not isinstance(document, AnalysisDocument):
        raise TypeError("document must be an AnalysisDocument")
    root_path = Path(root)
    if root_path.exists() or root_path.is_symlink():
        raise FileExistsError(root_path)
    if not document.data_series:
        return _create_empty_project_compat(document, root_path)
    return _create_staged_project(
        document,
        root_path,
        source_locations=source_locations,
    )


__all__ = [
    "AnalysisProjectError",
    "AnalysisProjectSnapshot",
    "LegacyWorkspaceError",
    "create_analysis_project",
    "open_analysis_project",
    "save_analysis_project",
]
