"""Strict file-backed persistence for v1.1 analysis projects."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from catalysis_workbench._canonical_json import (
    CanonicalJSONError,
    canonical_json_bytes,
    canonical_json_sha256,
    loads_strict_json,
)
from catalysis_workbench.workspace import create_workspace, open_workspace

from .document import (
    AnalysisDocument,
    AnalysisDocumentError,
    _document_from_dict,
    _document_to_plain_dict,
)

_PROJECT_FILENAME = "project.json"
_PROJECT_FIELDS = frozenset({"schema_version", "document"})


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


def _project_sha256(document: AnalysisDocument) -> str:
    return canonical_json_sha256(_project_to_plain_dict(document))


def _project_payload(document: AnalysisDocument) -> bytes:
    try:
        return canonical_json_bytes(_project_to_plain_dict(document)) + b"\n"
    except CanonicalJSONError as exc:
        raise AnalysisProjectError("analysis project cannot be serialized") from exc


def _project_path(root: Path) -> Path:
    project_path = root / _PROJECT_FILENAME
    if project_path.is_symlink():
        raise AnalysisProjectError("project.json must not be a symbolic link")
    return project_path


def _read_project_document(root: Path) -> AnalysisDocument:
    project_path = _project_path(root)
    if not project_path.exists():
        raise LegacyWorkspaceError(
            "this directory is a legacy CatalysisWorkbench workspace and does not "
            "contain a v1.1 project document"
        )
    if not project_path.is_file():
        raise AnalysisProjectError("project.json must be a regular file")
    try:
        text = project_path.read_text(encoding="utf-8")
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


def _snapshot_once(root: Path) -> AnalysisProjectSnapshot:
    manifest = open_workspace(root)
    document = _read_project_document(root)
    return AnalysisProjectSnapshot(
        root=root.resolve(),
        document=document,
        workspace_manifest_sha256=manifest.manifest_sha256,
        project_file_sha256=_project_sha256(document),
    )


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
) -> AnalysisProjectSnapshot:
    """Replace project.json only when exact on-disk project/workspace identities match."""

    if not isinstance(document, AnalysisDocument):
        raise TypeError("document must be an AnalysisDocument")
    root_path = Path(root)
    before = _snapshot_once(root_path)
    if before.workspace_manifest_sha256 != expected_workspace_manifest_sha256:
        raise AnalysisProjectError("workspace changed outside the analysis session; reopen explicitly")
    if before.project_file_sha256 != expected_project_file_sha256:
        raise AnalysisProjectError("project.json changed outside the analysis session; reopen explicitly")

    project_path = _project_path(root_path)
    payload = _project_payload(document)
    _replace_project_atomically(project_path, payload)

    observed = _snapshot_once(root_path)
    expected_project_sha = _project_sha256(document)
    if observed.project_file_sha256 != expected_project_sha or observed.document != document:
        raise AnalysisProjectError("project.json changed concurrently while it was being saved")
    if observed.workspace_manifest_sha256 != expected_workspace_manifest_sha256:
        raise AnalysisProjectError("workspace changed concurrently while project.json was being saved")
    return observed


def _rollback_new_workspace(root: Path) -> None:
    """Remove only the exact untouched workspace created by this failed first save."""

    try:
        entries = tuple(root.iterdir())
    except (FileNotFoundError, NotADirectoryError):
        return
    if len(entries) != 1 or entries[0].name != "workspace.json" or entries[0].is_symlink():
        return
    entries[0].unlink(missing_ok=True)
    try:
        root.rmdir()
    except OSError:
        pass


def create_analysis_project(
    document: AnalysisDocument,
    root: str | Path,
) -> AnalysisProjectSnapshot:
    """Create a new workspace/project pair at a path that must not already exist."""

    if not isinstance(document, AnalysisDocument):
        raise TypeError("document must be an AnalysisDocument")
    root_path = Path(root)
    if root_path.exists() or root_path.is_symlink():
        raise FileExistsError(root_path)

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
        _rollback_new_workspace(root_path)
        raise


__all__ = [
    "AnalysisProjectError",
    "AnalysisProjectSnapshot",
    "LegacyWorkspaceError",
    "create_analysis_project",
    "open_analysis_project",
    "save_analysis_project",
]
