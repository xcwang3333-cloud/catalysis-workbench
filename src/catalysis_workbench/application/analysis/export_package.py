"""Figure Package models, staged writers, and workspace provenance helpers."""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from catalysis_workbench._canonical_json import (
    canonical_json_bytes,
    canonical_json_sha256,
)
from catalysis_workbench.workspace import open_workspace
from catalysis_workbench.workspace.assets import (
    CopyAssetRequest,
    import_copy_assets_batch,
    verify_copy_asset,
)
from catalysis_workbench.workspace.composition import (
    create_workspace_composition,
    figure_spec_sha256,
    open_workspace_composition,
    record_figure_export,
)
from catalysis_workbench.workspace.evidence import (
    EvidenceRecord,
    append_evidence,
    create_evidence_ledger,
    open_evidence_ledger,
    record_evidence,
)
from catalysis_workbench.workspace.manifest import WorkspaceError

from .document import AnalysisDocument
from .evaluator import AnalysisResult
from .figure import FigureDraft, FigureSourceView, render_figure_draft

_FIGURE_FORMAT_ORDER = ("svg", "pdf", "png")
_SOURCE_FORMAT_ORDER = ("xlsx", "txt")
_FIGURE_ASSET_TYPE = "analysis_exported_figure"
_SOURCE_ASSET_TYPE = "analysis_figure_source_data"
_MANIFEST_ASSET_TYPE = "analysis_figure_package_manifest"
_FIGURE_SPEC_ASSET_TYPE = "figure_spec"


class FigurePackageExportError(RuntimeError):
    """Raised when a Figure Package cannot be published exactly and safely."""


@dataclass(frozen=True, slots=True)
class FigurePackageOptions:
    """Explicit output-format selection for one publication package."""

    figure_formats: Sequence[str] = ("svg", "pdf", "png")
    source_data_formats: Sequence[str] = ("xlsx", "txt")

    def __post_init__(self) -> None:
        figures = _formats(
            self.figure_formats,
            allowed=_FIGURE_FORMAT_ORDER,
            label="figure_formats",
        )
        sources = _formats(
            self.source_data_formats,
            allowed=_SOURCE_FORMAT_ORDER,
            label="source_data_formats",
        )
        if not figures:
            raise FigurePackageExportError("select at least one figure format")
        if not sources:
            raise FigurePackageExportError("select at least one source-data format")
        object.__setattr__(self, "figure_formats", figures)
        object.__setattr__(self, "source_data_formats", sources)


@dataclass(frozen=True, slots=True)
class FigurePackageResult:
    """Exact result of one successful external publication and provenance commit."""

    package_path: Path
    package_sha256: str
    manifest_sha256: str
    workspace_manifest_sha256: str
    file_sha256: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "package_path", Path(self.package_path))
        object.__setattr__(self, "file_sha256", dict(self.file_sha256))


@dataclass(slots=True)
class _TrackedMetadata:
    path: Path
    original: bytes | None
    expected: bytes | None = None

    @classmethod
    def capture(cls, path: Path) -> _TrackedMetadata:
        if path.is_symlink():
            raise FigurePackageExportError(
                f"metadata path must not be a symlink: {path.name}"
            )
        if not path.exists():
            return cls(path=path, original=None)
        if not path.is_file():
            raise FigurePackageExportError(
                f"metadata path must be a regular file: {path.name}"
            )
        return cls(path=path, original=path.read_bytes())

    def note(self) -> None:
        if self.path.is_symlink() or not self.path.is_file():
            raise FigurePackageExportError(
                f"metadata path changed unexpectedly: {self.path.name}"
            )
        self.expected = self.path.read_bytes()

    def rollback(self) -> bool:
        if self.expected is None:
            return True
        if self.path.is_symlink():
            return False
        if self.path.exists():
            if not self.path.is_file() or self.path.read_bytes() != self.expected:
                return (
                    self.original is not None
                    and self.path.read_bytes() == self.original
                )
        elif self.expected is not None:
            return self.original is None
        if self.original is None:
            self.path.unlink(missing_ok=True)
            return True
        _replace_bytes_atomically(self.path, self.original)
        return True


def _formats(
    values: Sequence[str],
    *,
    allowed: Sequence[str],
    label: str,
) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise TypeError(f"{label} must be an ordered sequence")
    normalized = tuple(
        str(item).strip().lower().lstrip(".") for item in values
    )
    if len(set(normalized)) != len(normalized):
        raise FigurePackageExportError(f"{label} values must be unique")
    unknown = sorted(set(normalized) - set(allowed))
    if unknown:
        raise FigurePackageExportError(f"unsupported {label}: {unknown!r}")
    return tuple(item for item in allowed if item in normalized)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _replace_bytes_atomically(path: Path, payload: bytes) -> None:
    descriptor: int | None = None
    temporary: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(
            prefix=f".{path.name}-",
            suffix=".tmp",
            dir=path.parent,
        )
        temporary = Path(name)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = None
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _visible_source(
    source: FigureSourceView,
    draft: FigureDraft,
) -> tuple[tuple[str, str, Any], ...]:
    by_id = dict(zip(source.trace_ids, source.series, strict=True))
    visible: list[tuple[str, str, Any]] = []
    for trace_id in draft.trace_order:
        style = draft.figure_spec.series_styles.get(trace_id)
        if style is not None and not style.visible:
            continue
        item = by_id[trace_id]
        label = (
            style.label
            if style is not None and style.label is not None
            else item.label or item.key or trace_id
        )
        visible.append((trace_id, label, item))
    if not visible:
        raise FigurePackageExportError(
            "at least one figure trace must remain visible"
        )
    return tuple(visible)


def _plain_metadata(value: object) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _trace_index_entry(
    index: int,
    trace_id: str,
    label: str,
    identity: str,
    series: Any,
) -> dict[str, object]:
    return {
        "index": index,
        "trace_id": trace_id,
        "label": label,
        "scientific_identity": identity,
        "point_count": int(series.n_points),
        "x_name": series.x_axis.name,
        "x_label": series.x_axis.label,
        "x_unit": series.x_axis.unit,
        "x_reference": _plain_metadata(
            series.x_axis.metadata.get("reference")
        ),
        "x_normalization": _plain_metadata(
            series.x_axis.metadata.get("normalization")
        ),
        "y_name": series.y_axis.name,
        "y_label": series.y_axis.label,
        "y_unit": series.y_axis.unit,
        "y_reference": _plain_metadata(
            series.y_axis.metadata.get("reference")
        ),
        "y_normalization": _plain_metadata(
            series.y_axis.metadata.get("normalization")
        ),
    }


def _number_text(value: float) -> str:
    number = float(value)
    if math.isnan(number):
        return "nan"
    return format(number, ".17g")


def _write_txt_source_data(
    root: Path,
    visible: Sequence[tuple[str, str, Any]],
    identities: Mapping[str, str],
) -> tuple[Path, ...]:
    directory = root / "source-data"
    directory.mkdir()
    written: list[Path] = []
    for index, (trace_id, label, series) in enumerate(visible, start=1):
        path = directory / f"trace-{index:03d}.txt"
        metadata = _trace_index_entry(
            index,
            trace_id,
            label,
            identities[trace_id],
            series,
        )
        metadata_text = json.dumps(
            metadata,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        lines = [
            "# metadata\t" + metadata_text,
            "x\ty\tx_missing\ty_missing",
        ]
        for x_value, y_value in zip(series.x, series.y, strict=True):
            x_missing = bool(math.isnan(float(x_value)))
            y_missing = bool(math.isnan(float(y_value)))
            lines.append(
                "\t".join(
                    (
                        _number_text(float(x_value)),
                        _number_text(float(y_value)),
                        "1" if x_missing else "0",
                        "1" if y_missing else "0",
                    )
                )
            )
        path.write_text(
            "\n".join(lines) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        written.append(path)
    return tuple(written)


def _write_xlsx_source_data(
    path: Path,
    visible: Sequence[tuple[str, str, Any]],
    identities: Mapping[str, str],
) -> None:
    from datetime import datetime

    from openpyxl import Workbook

    workbook = Workbook()
    workbook.properties.created = datetime(1980, 1, 1)
    workbook.properties.modified = datetime(1980, 1, 1)
    index_sheet = workbook.active
    index_sheet.title = "Index"
    headers = tuple(
        _trace_index_entry(
            1,
            "x",
            "x",
            "0" * 64,
            visible[0][2],
        ).keys()
    )
    index_sheet.append(headers)
    for index, (trace_id, label, series) in enumerate(visible, start=1):
        entry = _trace_index_entry(
            index,
            trace_id,
            label,
            identities[trace_id],
            series,
        )
        index_sheet.append(tuple(entry[key] for key in headers))
        sheet = workbook.create_sheet(f"Trace {index:03d}")
        sheet.append(("x", "y", "x_missing", "y_missing"))
        for x_value, y_value in zip(series.x, series.y, strict=True):
            x_number = float(x_value)
            y_number = float(y_value)
            x_missing = math.isnan(x_number)
            y_missing = math.isnan(y_number)
            sheet.append(
                (
                    None if x_missing else x_number,
                    None if y_missing else y_number,
                    x_missing,
                    y_missing,
                )
            )
    workbook.save(path)


def _file_entry(
    root: Path,
    path: Path,
    *,
    role: str,
    format_name: str,
) -> dict[str, object]:
    relative = path.relative_to(root).as_posix()
    return {
        "path": relative,
        "role": role,
        "format": format_name,
        "sha256": _sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _workflow_provenance(
    view_id: str,
    result: AnalysisResult,
) -> dict[str, str] | None:
    if view_id == "fe":
        return None
    run = result.workflow_run
    return {
        "recipe_sha256": run.recipe_sha256,
        "content_sha256": run.content_sha256,
        "record_sha256": run.record_sha256,
    }


def _semantic_manifest(
    document: AnalysisDocument,
    result: AnalysisResult,
    draft: FigureDraft,
    source: FigureSourceView,
    visible: Sequence[tuple[str, str, Any]],
    options: FigurePackageOptions,
) -> dict[str, object]:
    trace_ids = [trace_id for trace_id, _label, _series in visible]
    return {
        "identity_schema_version": 1,
        "task_id": document.task_id,
        "view_id": draft.view_id,
        "analysis_document_sha256": document.document_sha256,
        "figure_draft_sha256": draft.figure_sha256,
        "source_view_sha256": source.source_view_sha256,
        "trace_order": trace_ids,
        "trace_identities": {
            trace_id: source.trace_identities[trace_id]
            for trace_id in trace_ids
        },
        "figure_spec_sha256": figure_spec_sha256(draft.figure_spec),
        "figure_formats": list(options.figure_formats),
        "source_data_formats": list(options.source_data_formats),
        "workflow": _workflow_provenance(draft.view_id, result),
    }


def _write_package_stage(
    stage: Path,
    document: AnalysisDocument,
    result: AnalysisResult,
    draft: FigureDraft,
    source: FigureSourceView,
    options: FigurePackageOptions,
) -> tuple[dict[str, object], str, str]:
    visible = _visible_source(source, draft)
    from matplotlib import font_manager

    available_fonts = {
        entry.name for entry in font_manager.fontManager.ttflist
    }
    if draft.figure_spec.style.font_family not in available_fonts:
        raise FigurePackageExportError(
            f"font {draft.figure_spec.style.font_family!r} "
            "is unavailable on this system"
        )

    figure, _axes = render_figure_draft(document, result, draft)
    files: list[dict[str, object]] = []
    try:
        from catalysis_workbench.visualization.export import export_figure

        for format_name in options.figure_formats:
            path = stage / f"figure.{format_name}"
            export_figure(
                figure,
                path,
                spec=draft.figure_spec,
                format=format_name,
            )
            files.append(
                _file_entry(
                    stage,
                    path,
                    role="figure",
                    format_name=format_name,
                )
            )
    finally:
        from matplotlib import pyplot as plt

        plt.close(figure)

    if "xlsx" in options.source_data_formats:
        path = stage / "source-data.xlsx"
        _write_xlsx_source_data(path, visible, source.trace_identities)
        files.append(
            _file_entry(
                stage,
                path,
                role="source_data",
                format_name="xlsx",
            )
        )
    if "txt" in options.source_data_formats:
        for path in _write_txt_source_data(
            stage,
            visible,
            source.trace_identities,
        ):
            files.append(
                _file_entry(
                    stage,
                    path,
                    role="source_data",
                    format_name="txt",
                )
            )

    semantic = _semantic_manifest(
        document,
        result,
        draft,
        source,
        visible,
        options,
    )
    package_sha256 = canonical_json_sha256(semantic)
    manifest = {
        "schema_version": 1,
        **semantic,
        "package_sha256": package_sha256,
        "files": sorted(files, key=lambda item: str(item["path"])),
    }
    manifest_path = stage / "manifest.json"
    manifest_path.write_bytes(canonical_json_bytes(manifest) + b"\n")
    manifest_sha256 = _sha256_file(manifest_path)
    return manifest, package_sha256, manifest_sha256


def _validate_stage(
    stage: Path,
    manifest: Mapping[str, object],
) -> dict[str, str]:
    files = manifest.get("files")
    if not isinstance(files, list):
        raise FigurePackageExportError(
            "package manifest files must be a list"
        )
    identities: dict[str, str] = {}
    for entry in files:
        if not isinstance(entry, Mapping):
            raise FigurePackageExportError(
                "package manifest file entry must be an object"
            )
        relative = entry.get("path")
        expected = entry.get("sha256")
        if type(relative) is not str or type(expected) is not str:
            raise FigurePackageExportError(
                "package manifest file identity is invalid"
            )
        path = stage / relative
        if (
            path.is_symlink()
            or not path.is_file()
            or _sha256_file(path) != expected
        ):
            raise FigurePackageExportError(
                f"staged package file failed verification: {relative}"
            )
        identities[relative] = expected
    manifest_path = stage / "manifest.json"
    identities["manifest.json"] = _sha256_file(manifest_path)
    return identities


def _serialize_figure_spec(path: Path, draft: FigureDraft) -> str:
    payload = canonical_json_bytes(
        {
            "schema_version": 1,
            "spec": draft.figure_spec.to_dict(),
        }
    ) + b"\n"
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def _ensure_provenance_asset(
    root: Path,
    request: CopyAssetRequest,
    existing: Mapping[str, Any],
) -> CopyAssetRequest | None:
    asset = existing.get(request.asset_id)
    if asset is None:
        return request
    if (
        asset.asset_type != request.asset_type
        or asset.policy != "copy"
        or asset.path != request.destination
        or asset.content_sha256 != request.expected_content_sha256
    ):
        raise FigurePackageExportError(
            f"workspace provenance asset collision: {request.asset_id!r}"
        )
    try:
        verify_copy_asset(
            root,
            request.asset_id,
            expected_type=request.asset_type,
        )
    except (OSError, WorkspaceError) as exc:
        raise FigurePackageExportError(str(exc)) from exc
    return None


def _append_or_verify_evidence(root: Path, record: EvidenceRecord) -> None:
    ledger = open_evidence_ledger(root)
    existing = next(
        (
            item
            for item in ledger.records
            if item.record_id == record.record_id
        ),
        None,
    )
    if existing is None:
        append_evidence(root, record)
        return
    if existing != record:
        raise FigurePackageExportError(
            f"evidence record collision: {record.record_id!r}"
        )


def _composition_exists(
    root: Path,
    composition_id: str,
    *,
    figure_asset_id: str,
) -> bool:
    composition = open_workspace_composition(root)
    for item in composition.figures:
        if item.composition_id != composition_id:
            continue
        if item.exported_figure_asset_id != figure_asset_id:
            raise FigurePackageExportError(
                f"figure composition collision: {composition_id!r}"
            )
        return True
    return False


def _rollback_provenance(
    tracked: Sequence[_TrackedMetadata],
    new_assets: Sequence[tuple[Path, str]],
) -> None:
    safe = True
    for item in reversed(tuple(tracked)):
        try:
            safe = item.rollback() and safe
        except OSError:
            safe = False
    if safe:
        for path, digest in reversed(tuple(new_assets)):
            try:
                if (
                    path.is_file()
                    and not path.is_symlink()
                    and _sha256_file(path) == digest
                ):
                    path.unlink()
            except OSError:
                safe = False
    if not safe:
        raise FigurePackageExportError(
            "export failed and workspace changed during rollback; "
            "reopen and inspect provenance"
        )


def _commit_workspace_provenance(
    project_root: Path,
    stage: Path,
    manifest: Mapping[str, object],
    manifest_sha256: str,
    draft: FigureDraft,
    result: AnalysisResult,
    *,
    expected_workspace_manifest_sha256: str,
) -> str:
    workspace_tracker = _TrackedMetadata.capture(
        project_root / "workspace.json"
    )
    evidence_tracker = _TrackedMetadata.capture(
        project_root / "workspace-evidence.json"
    )
    composition_tracker = _TrackedMetadata.capture(
        project_root / "workspace-composition.json"
    )
    tracked = (
        workspace_tracker,
        evidence_tracker,
        composition_tracker,
    )
    new_assets: list[tuple[Path, str]] = []

    manifest_before = open_workspace(project_root)
    if (
        manifest_before.manifest_sha256
        != expected_workspace_manifest_sha256
    ):
        raise FigurePackageExportError(
            "workspace changed outside the analysis session; reopen explicitly"
        )

    prefix = manifest_sha256[:24]
    with tempfile.TemporaryDirectory(
        prefix="cw-figure-spec-"
    ) as directory:
        spec_path = Path(directory) / "figure-spec.json"
        spec_file_sha = _serialize_figure_spec(spec_path, draft)
        figure_spec_identity = figure_spec_sha256(draft.figure_spec)
        requests: list[CopyAssetRequest] = [
            CopyAssetRequest(
                source=spec_path,
                asset_id=f"figure-spec-{figure_spec_identity[:24]}",
                asset_type=_FIGURE_SPEC_ASSET_TYPE,
                destination=(
                    "artifacts/figure-specs/"
                    f"{figure_spec_identity}.json"
                ),
                expected_content_sha256=spec_file_sha,
            )
        ]
        files = manifest.get("files")
        assert isinstance(files, list)
        for entry in files:
            assert isinstance(entry, Mapping)
            relative = str(entry["path"])
            digest = str(entry["sha256"])
            role = str(entry["role"])
            asset_type = (
                _FIGURE_ASSET_TYPE
                if role == "figure"
                else _SOURCE_ASSET_TYPE
            )
            relative_identity = hashlib.sha256(
                relative.encode()
            ).hexdigest()[:12]
            requests.append(
                CopyAssetRequest(
                    source=stage / relative,
                    asset_id=(
                        f"export-{prefix}-{relative_identity}"
                    ),
                    asset_type=asset_type,
                    destination=(
                        f"artifacts/exports/{manifest_sha256}/{relative}"
                    ),
                    expected_content_sha256=digest,
                )
            )
        requests.append(
            CopyAssetRequest(
                source=stage / "manifest.json",
                asset_id=f"export-{prefix}-manifest",
                asset_type=_MANIFEST_ASSET_TYPE,
                destination=(
                    f"artifacts/exports/{manifest_sha256}/manifest.json"
                ),
                expected_content_sha256=manifest_sha256,
            )
        )

        existing = {
            asset.asset_id: asset for asset in manifest_before.assets
        }
        pending = tuple(
            request
            for request in requests
            if _ensure_provenance_asset(
                project_root,
                request,
                existing,
            )
            is not None
        )
        try:
            if pending:
                updated = import_copy_assets_batch(
                    project_root,
                    pending,
                    expected_manifest_sha256=(
                        manifest_before.manifest_sha256
                    ),
                )
                workspace_tracker.note()
                for request in pending:
                    new_assets.append(
                        (
                            project_root / request.destination,
                            str(request.expected_content_sha256),
                        )
                    )
            else:
                updated = manifest_before

            try:
                open_evidence_ledger(project_root)
            except FileNotFoundError:
                create_evidence_ledger(project_root)
                evidence_tracker.note()
            try:
                open_workspace_composition(project_root)
            except FileNotFoundError:
                create_workspace_composition(project_root)
                composition_tracker.note()

            workflow_record_id: str | None = None
            if draft.view_id != "fe":
                workflow_record_id = f"workflow-{prefix}"
                workflow_record = record_evidence(
                    workflow_record_id,
                    result.workflow_run,
                )
                _append_or_verify_evidence(
                    project_root,
                    workflow_record,
                )
                evidence_tracker.note()

            all_asset_ids = tuple(
                request.asset_id for request in requests
            )
            package_record_id = f"package-{prefix}"
            package_record = EvidenceRecord(
                record_id=package_record_id,
                kind="artifact",
                evidence_sha256=manifest_sha256,
                asset_ids=all_asset_ids,
                related_record_ids=(
                    ()
                    if workflow_record_id is None
                    else (workflow_record_id,)
                ),
            )
            _append_or_verify_evidence(
                project_root,
                package_record,
            )
            evidence_tracker.note()

            figure_spec_asset_id = requests[0].asset_id
            figure_requests = [
                request
                for request in requests
                if request.asset_type == _FIGURE_ASSET_TYPE
            ]
            evidence_ids = (
                (package_record_id,)
                if workflow_record_id is None
                else (workflow_record_id, package_record_id)
            )
            for request in figure_requests:
                format_name = Path(
                    request.destination
                ).suffix.lstrip(".")
                composition_id = f"figure-{prefix}-{format_name}"
                if not _composition_exists(
                    project_root,
                    composition_id,
                    figure_asset_id=request.asset_id,
                ):
                    record_figure_export(
                        project_root,
                        composition_id=composition_id,
                        figure_spec_asset_id=figure_spec_asset_id,
                        exported_figure_asset_id=request.asset_id,
                        evidence_record_ids=evidence_ids,
                    )
                    composition_tracker.note()

            observed = open_workspace(project_root)
            if observed.manifest_sha256 != updated.manifest_sha256:
                raise FigurePackageExportError(
                    "workspace changed during export provenance commit"
                )
            return observed.manifest_sha256
        except BaseException:
            _rollback_provenance(tracked, new_assets)
            raise


__all__ = [
    "FigurePackageExportError",
    "FigurePackageOptions",
    "FigurePackageResult",
]
