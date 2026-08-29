"""Fail-closed publication transaction for v1.1 Figure Packages."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from catalysis_workbench.workspace import open_workspace
from catalysis_workbench.workspace.manifest import WorkspaceAsset, WorkspaceError

from .document import AnalysisDocument
from .evaluator import AnalysisResult
from .export_package import (
    FigurePackageExportError,
    FigurePackageOptions,
    FigurePackageResult,
    _commit_workspace_provenance,
    _replace_bytes_atomically,
    _sha256_file,
    _validate_stage,
    _write_package_stage,
)
from .figure import FigureDraft, figure_draft_is_stale, figure_source_view
from .persistence import AnalysisProjectError, open_analysis_project

_METADATA_NAMES = (
    "workspace.json",
    "workspace-evidence.json",
    "workspace-composition.json",
)


@dataclass(slots=True)
class _PublicationRollback:
    """Exact pre-export workspace state retained until external publication succeeds."""

    root: Path
    original_metadata: dict[str, bytes | None]
    original_asset_ids: frozenset[str]
    expected_metadata: dict[str, bytes | None] = field(default_factory=dict)
    added_assets: tuple[WorkspaceAsset, ...] = ()

    @classmethod
    def capture(cls, root: Path) -> _PublicationRollback:
        manifest = open_workspace(root)
        original: dict[str, bytes | None] = {}
        for name in _METADATA_NAMES:
            path = root / name
            if path.is_symlink():
                raise FigurePackageExportError(
                    f"workspace metadata must not be a symbolic link: {name}"
                )
            if not path.exists():
                original[name] = None
                continue
            if not path.is_file():
                raise FigurePackageExportError(
                    f"workspace metadata must be a regular file: {name}"
                )
            original[name] = path.read_bytes()
        return cls(
            root=root,
            original_metadata=original,
            original_asset_ids=frozenset(asset.asset_id for asset in manifest.assets),
        )

    def note_committed(self) -> None:
        manifest = open_workspace(self.root)
        self.added_assets = tuple(
            asset
            for asset in manifest.assets
            if asset.asset_id not in self.original_asset_ids
        )
        expected: dict[str, bytes | None] = {}
        for name in _METADATA_NAMES:
            path = self.root / name
            if path.is_symlink():
                raise FigurePackageExportError(
                    f"workspace metadata changed to a symbolic link: {name}"
                )
            if not path.exists():
                expected[name] = None
            elif not path.is_file():
                raise FigurePackageExportError(
                    f"workspace metadata changed to a non-file path: {name}"
                )
            else:
                expected[name] = path.read_bytes()
        self.expected_metadata = expected

    def _preflight_rollback(self) -> tuple[tuple[Path, str], ...]:
        if not self.expected_metadata:
            return ()
        for name, expected in self.expected_metadata.items():
            path = self.root / name
            if path.is_symlink():
                raise FigurePackageExportError(
                    "workspace changed during export rollback; reopen and inspect provenance"
                )
            if expected is None:
                if path.exists():
                    raise FigurePackageExportError(
                        "workspace changed during export rollback; reopen and inspect provenance"
                    )
                continue
            if not path.is_file() or path.read_bytes() != expected:
                raise FigurePackageExportError(
                    "workspace changed during export rollback; reopen and inspect provenance"
                )

        removable: list[tuple[Path, str]] = []
        for asset in self.added_assets:
            if asset.policy != "copy" or asset.content_sha256 is None:
                raise FigurePackageExportError(
                    "export provenance created a non-verifiable workspace asset"
                )
            path = self.root / asset.path
            if path.is_symlink() or not path.is_file():
                raise FigurePackageExportError(
                    "workspace export asset changed during rollback; reopen and inspect provenance"
                )
            if _sha256_file(path) != asset.content_sha256:
                raise FigurePackageExportError(
                    "workspace export asset changed during rollback; reopen and inspect provenance"
                )
            removable.append((path, asset.content_sha256))
        return tuple(removable)

    def rollback(self) -> None:
        removable = self._preflight_rollback()
        for name, original in self.original_metadata.items():
            path = self.root / name
            if original is None:
                path.unlink(missing_ok=True)
            else:
                _replace_bytes_atomically(path, original)

        for path, digest in reversed(removable):
            if path.is_file() and not path.is_symlink() and _sha256_file(path) == digest:
                path.unlink()
                parent = path.parent
                while parent != self.root:
                    try:
                        parent.rmdir()
                    except OSError:
                        break
                    parent = parent.parent


def _manifest_file_identities(
    target: Path,
    manifest_sha256: str,
) -> dict[str, str] | None:
    """Return exact expected file identities only for a trusted package manifest."""

    manifest_path = target / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        return None
    try:
        if _sha256_file(manifest_path) != manifest_sha256:
            return None
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("files"), list):
        return None

    identities: dict[str, str] = {"manifest.json": manifest_sha256}
    for entry in payload["files"]:
        if not isinstance(entry, dict):
            return None
        relative = entry.get("path")
        digest = entry.get("sha256")
        if type(relative) is not str or type(digest) is not str:
            return None
        logical = PurePosixPath(relative)
        if (
            not relative
            or logical.is_absolute()
            or ".." in logical.parts
            or relative == "manifest.json"
            or relative in identities
        ):
            return None
        identities[relative] = digest
    return identities


def _expected_package_directories(identities: dict[str, str]) -> set[str]:
    directories: set[str] = set()
    for relative in identities:
        logical = PurePosixPath(relative)
        for parent in logical.parents:
            if parent == PurePosixPath("."):
                break
            directories.add(parent.as_posix())
    return directories


def _remove_exact_published_target(target: Path, manifest_sha256: str) -> bool:
    """Remove only a byte-exact package tree produced by this operation."""

    if target.is_symlink() or not target.is_dir():
        return not target.exists()
    identities = _manifest_file_identities(target, manifest_sha256)
    if identities is None:
        return False
    expected_directories = _expected_package_directories(identities)
    try:
        observed_files: set[str] = set()
        observed_directories: set[str] = set()
        for path in target.rglob("*"):
            if path.is_symlink():
                return False
            relative = path.relative_to(target).as_posix()
            if path.is_dir():
                observed_directories.add(relative)
                continue
            if not path.is_file():
                return False
            observed_files.add(relative)
        if observed_files != set(identities):
            return False
        if observed_directories != expected_directories:
            return False
        for relative, digest in identities.items():
            path = target / Path(*PurePosixPath(relative).parts)
            if not path.is_file() or _sha256_file(path) != digest:
                return False
        shutil.rmtree(target)
    except OSError:
        return False
    return not target.exists()


def _publish_stage(stage: Path, target: Path) -> None:
    """Publish the complete staged directory as the transaction's final mutation."""

    os.replace(stage, target)


def export_figure_package(
    document: AnalysisDocument,
    result: AnalysisResult,
    draft: FigureDraft,
    *,
    project_root: str | Path,
    expected_workspace_manifest_sha256: str,
    expected_project_file_sha256: str,
    destination: str | Path,
    options: FigurePackageOptions | None = None,
) -> FigurePackageResult:
    """Atomically publish one Figure Package together with workspace provenance."""

    if not isinstance(document, AnalysisDocument):
        raise TypeError("document must be an AnalysisDocument")
    if not isinstance(result, AnalysisResult):
        raise TypeError("result must be an AnalysisResult")
    if not isinstance(draft, FigureDraft):
        raise TypeError("draft must be a FigureDraft")
    resolved_options = FigurePackageOptions() if options is None else options
    if not isinstance(resolved_options, FigurePackageOptions):
        raise TypeError("options must be a FigurePackageOptions")

    root = Path(project_root)
    try:
        snapshot = open_analysis_project(root)
    except (AnalysisProjectError, OSError, WorkspaceError) as exc:
        raise FigurePackageExportError(str(exc)) from exc
    if snapshot.workspace_manifest_sha256 != expected_workspace_manifest_sha256:
        raise FigurePackageExportError(
            "workspace changed outside the analysis session; reopen explicitly"
        )
    if snapshot.project_file_sha256 != expected_project_file_sha256:
        raise FigurePackageExportError(
            "project.json changed outside the analysis session; reopen explicitly"
        )
    if snapshot.document != document:
        raise FigurePackageExportError("save the current analysis project before exporting")
    if result.document_sha256 != document.document_sha256:
        raise FigurePackageExportError("analysis result does not match the saved document")
    if figure_draft_is_stale(draft, document, result):
        raise FigurePackageExportError(
            "analysis results changed; refresh this figure before exporting"
        )

    target = Path(destination)
    if target.exists() or target.is_symlink():
        raise FigurePackageExportError(
            "Figure Package destination must not already exist"
        )
    parent = target.parent
    if not parent.exists():
        raise FileNotFoundError(parent)
    if not parent.is_dir():
        raise NotADirectoryError(parent)

    stage = Path(tempfile.mkdtemp(prefix=f".{target.name}-export-", dir=parent))
    rollback: _PublicationRollback | None = None
    manifest_sha256: str | None = None
    published = False
    try:
        source = figure_source_view(document, result, draft.view_id)
        manifest, package_sha256, manifest_sha256 = _write_package_stage(
            stage,
            document,
            result,
            draft,
            source,
            resolved_options,
        )
        file_identities = _validate_stage(stage, manifest)

        rollback = _PublicationRollback.capture(root)
        workspace_sha = _commit_workspace_provenance(
            root,
            stage,
            manifest,
            manifest_sha256,
            draft,
            result,
            expected_workspace_manifest_sha256=expected_workspace_manifest_sha256,
        )
        rollback.note_committed()

        # All workspace checks happen before the final external rename. After a
        # successful publication there is deliberately no operation left that can
        # invalidate an otherwise complete transaction.
        reopened = open_analysis_project(root)
        if reopened.workspace_manifest_sha256 != workspace_sha:
            raise FigurePackageExportError(
                "workspace changed before Figure Package publication"
            )
        if reopened.project_file_sha256 != expected_project_file_sha256:
            raise FigurePackageExportError(
                "project.json changed before Figure Package publication"
            )

        _publish_stage(stage, target)
        published = True
        return FigurePackageResult(
            package_path=target.resolve(),
            package_sha256=package_sha256,
            manifest_sha256=manifest_sha256,
            workspace_manifest_sha256=workspace_sha,
            file_sha256=file_identities,
        )
    except BaseException as exc:
        target_removed = True
        if manifest_sha256 is not None and target.exists():
            target_removed = _remove_exact_published_target(target, manifest_sha256)
        if rollback is not None:
            if not target_removed:
                raise FigurePackageExportError(
                    "Figure Package publication failed after the destination changed; "
                    "reopen and inspect the package and workspace provenance"
                ) from exc
            try:
                rollback.rollback()
            except FigurePackageExportError as rollback_exc:
                raise rollback_exc from exc
        raise
    finally:
        if not published and stage.exists() and stage.is_dir() and not stage.is_symlink():
            shutil.rmtree(stage, ignore_errors=True)


__all__ = ["export_figure_package"]
