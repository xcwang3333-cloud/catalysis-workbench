"""Deterministic persistent associations between workspace assets and reviewed evidence."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from catalysis_workbench._canonical_json import (
    CanonicalJSONError,
    canonical_json_bytes,
    canonical_json_sha256,
    loads_strict_json,
)

from .manifest import WorkspaceAsset, WorkspaceError, WorkspaceManifest
from .persistence import _root_path, open_workspace

__all__ = [
    "EvidenceAssociation",
    "EvidenceLedger",
    "EvidenceRef",
    "WorkspaceEvidenceError",
    "append_evidence",
    "artifact_evidence",
    "batch_run_evidence",
    "load_evidence_ledger",
    "qa_report_evidence",
    "recipe_evidence",
    "save_evidence_ledger",
    "workflow_run_evidence",
]


class WorkspaceEvidenceError(WorkspaceError):
    """Raised when workspace evidence state or persistence is invalid."""


_EVIDENCE_FILENAME = "evidence.json"
_EVIDENCE_KINDS = frozenset(
    {"recipe", "workflow-run", "batch-run", "qa-report", "artifact"}
)


def _stable_string(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value.strip() != value:
        raise WorkspaceEvidenceError(
            f"{label} must be a non-empty string without surrounding whitespace"
        )
    try:
        canonical_json_bytes(value)
    except CanonicalJSONError as exc:
        raise WorkspaceEvidenceError(f"{label} must be valid UTF-8") from exc
    return value


def _sha256(value: object, *, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or value.lower() != value
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise WorkspaceEvidenceError(f"{label} must be a lowercase SHA-256 hex digest")
    return value


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    """One explicit reference to identity already produced by a reviewed API."""

    kind: str
    sha256: str

    def __post_init__(self) -> None:
        kind = _stable_string(self.kind, label="evidence kind")
        if kind not in _EVIDENCE_KINDS:
            raise WorkspaceEvidenceError(f"unsupported evidence kind: {kind!r}")
        object.__setattr__(self, "kind", kind)
        object.__setattr__(
            self,
            "sha256",
            _sha256(self.sha256, label=f"{kind} evidence sha256"),
        )


@dataclass(frozen=True, slots=True)
class EvidenceAssociation:
    """Ordered deterministic association between workspace assets and evidence."""

    association_id: str
    asset_ids: Sequence[str]
    evidence: Sequence[EvidenceRef]
    association_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        association_id = _stable_string(self.association_id, label="association_id")
        if isinstance(self.asset_ids, (str, bytes)) or not isinstance(
            self.asset_ids, Sequence
        ):
            raise WorkspaceEvidenceError("asset_ids must be an ordered sequence")
        asset_ids = tuple(
            _stable_string(value, label="asset_id") for value in self.asset_ids
        )
        if not asset_ids:
            raise WorkspaceEvidenceError("an evidence association requires at least one asset_id")
        if len(asset_ids) != len(set(asset_ids)):
            raise WorkspaceEvidenceError("evidence association asset_ids must be unique")

        if isinstance(self.evidence, (str, bytes)) or not isinstance(
            self.evidence, Sequence
        ):
            raise WorkspaceEvidenceError("evidence must be an ordered sequence")
        evidence = tuple(self.evidence)
        if not evidence:
            raise WorkspaceEvidenceError(
                "an evidence association requires at least one evidence reference"
            )
        if any(not isinstance(item, EvidenceRef) for item in evidence):
            raise TypeError("evidence must contain only EvidenceRef values")
        keys = tuple((item.kind, item.sha256) for item in evidence)
        if len(keys) != len(set(keys)):
            raise WorkspaceEvidenceError(
                "evidence references must be unique within one association"
            )

        digest = canonical_json_sha256(
            {
                "association_schema_version": 1,
                "association_id": association_id,
                "asset_ids": list(asset_ids),
                "evidence": [
                    {"kind": item.kind, "sha256": item.sha256} for item in evidence
                ],
            }
        )
        object.__setattr__(self, "association_id", association_id)
        object.__setattr__(self, "asset_ids", asset_ids)
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(self, "association_sha256", digest)


@dataclass(frozen=True, slots=True)
class EvidenceLedger:
    """Ordered immutable file-backed evidence-association ledger."""

    schema_version: int
    records: Sequence[EvidenceAssociation]
    ledger_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise WorkspaceEvidenceError("evidence ledger schema_version must be integer 1")
        if isinstance(self.records, (str, bytes)) or not isinstance(
            self.records, Sequence
        ):
            raise WorkspaceEvidenceError("evidence ledger records must be an ordered sequence")
        records = tuple(self.records)
        if any(not isinstance(item, EvidenceAssociation) for item in records):
            raise TypeError("records must contain only EvidenceAssociation values")
        record_ids = tuple(item.association_id for item in records)
        if len(record_ids) != len(set(record_ids)):
            raise WorkspaceEvidenceError("evidence association_id values must be unique")
        digest = canonical_json_sha256(
            {
                "evidence_ledger_identity_schema_version": 1,
                "records": [
                    {"association_sha256": item.association_sha256} for item in records
                ],
            }
        )
        object.__setattr__(self, "records", records)
        object.__setattr__(self, "ledger_sha256", digest)


def recipe_evidence(recipe: object) -> EvidenceRef:
    """Reference the deterministic identity of one reviewed WorkflowRecipe."""

    from catalysis_workbench.workflow.recipe import WorkflowRecipe

    if not isinstance(recipe, WorkflowRecipe):
        raise TypeError("recipe must be a WorkflowRecipe")
    return EvidenceRef(kind="recipe", sha256=recipe.recipe_sha256)


def workflow_run_evidence(run: object) -> EvidenceRef:
    """Reference one reviewed WorkflowRun record identity without re-execution."""

    from catalysis_workbench.workflow.execution import WorkflowRun

    if not isinstance(run, WorkflowRun):
        raise TypeError("run must be a WorkflowRun")
    return EvidenceRef(kind="workflow-run", sha256=run.record_sha256)


def batch_run_evidence(record: object) -> EvidenceRef:
    """Reference one reviewed BatchRunRecord identity without re-execution."""

    from catalysis_workbench.workflow.batch import BatchRunRecord

    if not isinstance(record, BatchRunRecord):
        raise TypeError("record must be a BatchRunRecord")
    return EvidenceRef(kind="batch-run", sha256=record.record_sha256)


def qa_report_evidence(report: object) -> EvidenceRef:
    """Reference one reviewed QAReport identity without running QA."""

    from catalysis_workbench.workflow.qa import QAReport

    if not isinstance(report, QAReport):
        raise TypeError("report must be a QAReport")
    return EvidenceRef(kind="qa-report", sha256=report.report_sha256)


def artifact_evidence(asset: WorkspaceAsset) -> EvidenceRef:
    """Reference exact retained bytes for an explicitly selected workspace asset."""

    if not isinstance(asset, WorkspaceAsset):
        raise TypeError("asset must be a WorkspaceAsset")
    if asset.content_sha256 is None:
        raise WorkspaceEvidenceError(
            "artifact evidence requires a workspace asset with content_sha256"
        )
    return EvidenceRef(kind="artifact", sha256=asset.content_sha256)


_LEDGER_FIELDS = frozenset({"schema_version", "records"})
_ASSOCIATION_FIELDS = frozenset({"association_id", "asset_ids", "evidence"})
_REF_FIELDS = frozenset({"kind", "sha256"})


def _required_fields(
    value: Mapping[object, object], *, required: frozenset[str], label: str
) -> None:
    if not all(type(key) is str for key in value):
        raise WorkspaceEvidenceError(f"{label} field names must be strings")
    fields = set(value)
    missing = sorted(required - fields)
    unknown = sorted(fields - required)
    if missing or unknown:
        raise WorkspaceEvidenceError(
            f"invalid {label} fields; missing={missing!r}, unknown={unknown!r}"
        )


def _association_to_dict(record: EvidenceAssociation) -> dict[str, Any]:
    return {
        "association_id": record.association_id,
        "asset_ids": list(record.asset_ids),
        "evidence": [
            {"kind": item.kind, "sha256": item.sha256} for item in record.evidence
        ],
    }


def _ledger_to_dict(ledger: EvidenceLedger) -> dict[str, Any]:
    return {
        "schema_version": ledger.schema_version,
        "records": [_association_to_dict(record) for record in ledger.records],
    }


def _ledger_from_dict(value: object) -> EvidenceLedger:
    if not isinstance(value, Mapping):
        raise WorkspaceEvidenceError("serialized evidence ledger must be an object")
    _required_fields(value, required=_LEDGER_FIELDS, label="evidence ledger")
    records = value["records"]
    if not isinstance(records, list):
        raise WorkspaceEvidenceError("serialized evidence records must be a list")

    parsed: list[EvidenceAssociation] = []
    for record_index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise WorkspaceEvidenceError(
                f"serialized evidence association {record_index} must be an object"
            )
        _required_fields(
            record,
            required=_ASSOCIATION_FIELDS,
            label=f"evidence association {record_index}",
        )
        asset_ids = record["asset_ids"]
        refs = record["evidence"]
        if not isinstance(asset_ids, list):
            raise WorkspaceEvidenceError(
                f"serialized evidence association {record_index} asset_ids must be a list"
            )
        if not isinstance(refs, list):
            raise WorkspaceEvidenceError(
                f"serialized evidence association {record_index} evidence must be a list"
            )
        parsed_refs: list[EvidenceRef] = []
        for ref_index, ref in enumerate(refs):
            if not isinstance(ref, Mapping):
                raise WorkspaceEvidenceError(
                    "serialized evidence reference must be an object"
                )
            _required_fields(
                ref,
                required=_REF_FIELDS,
                label=(
                    f"evidence association {record_index} "
                    f"reference {ref_index}"
                ),
            )
            parsed_refs.append(EvidenceRef(kind=ref["kind"], sha256=ref["sha256"]))
        parsed.append(
            EvidenceAssociation(
                association_id=record["association_id"],
                asset_ids=asset_ids,
                evidence=parsed_refs,
            )
        )
    return EvidenceLedger(schema_version=value["schema_version"], records=parsed)


def _metadata_path_collision(manifest: WorkspaceManifest) -> None:
    for asset in manifest.assets:
        if asset.policy == "copy" and asset.path.casefold() == _EVIDENCE_FILENAME.casefold():
            raise WorkspaceEvidenceError(
                f"{_EVIDENCE_FILENAME!r} conflicts with an existing workspace-owned asset"
            )


def _validate_asset_ids(
    ledger: EvidenceLedger,
    manifest: WorkspaceManifest,
) -> None:
    known = {asset.asset_id for asset in manifest.assets}
    for record in ledger.records:
        unknown = [asset_id for asset_id in record.asset_ids if asset_id not in known]
        if unknown:
            raise WorkspaceEvidenceError(
                f"evidence association {record.association_id!r} references "
                f"unknown workspace assets: {unknown!r}"
            )


def _payload(ledger: EvidenceLedger) -> bytes:
    if not isinstance(ledger, EvidenceLedger):
        raise TypeError("ledger must be an EvidenceLedger")
    try:
        return canonical_json_bytes(_ledger_to_dict(ledger)) + b"\n"
    except CanonicalJSONError as exc:
        raise WorkspaceEvidenceError("evidence ledger cannot be serialized") from exc


def _replace_atomically(path: Path, payload: bytes) -> None:
    temporary_path: Path | None = None
    descriptor: int | None = None
    try:
        descriptor, name = tempfile.mkstemp(
            prefix=".evidence-",
            suffix=".tmp",
            dir=path.parent,
        )
        temporary_path = Path(name)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = None
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def save_evidence_ledger(
    ledger: EvidenceLedger,
    root: str | Path,
    *,
    overwrite: bool = False,
) -> None:
    """Persist a validated evidence ledger at the explicit workspace root."""

    if type(overwrite) is not bool:
        raise TypeError("overwrite must be a bool")
    payload = _payload(ledger)
    root_path = _root_path(root, must_exist=True)
    manifest = open_workspace(root_path)
    _metadata_path_collision(manifest)
    _validate_asset_ids(ledger, manifest)

    path = root_path / _EVIDENCE_FILENAME
    if path.is_symlink():
        raise WorkspaceEvidenceError("workspace evidence file must not be a symbolic link")
    if path.exists() and not path.is_file():
        raise WorkspaceEvidenceError("workspace evidence path must be a regular file")
    if overwrite:
        _replace_atomically(path, payload)
        return
    with path.open("xb") as stream:
        stream.write(payload)


def load_evidence_ledger(root: str | Path) -> EvidenceLedger:
    """Strictly load and validate the persistent evidence ledger."""

    root_path = _root_path(root, must_exist=True)
    manifest = open_workspace(root_path)
    _metadata_path_collision(manifest)
    path = root_path / _EVIDENCE_FILENAME
    if path.is_symlink():
        raise WorkspaceEvidenceError("workspace evidence file must not be a symbolic link")
    if not path.exists():
        raise FileNotFoundError(path)
    if not path.is_file():
        raise WorkspaceEvidenceError("workspace evidence path must be a regular file")
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise WorkspaceEvidenceError("workspace evidence file is not valid UTF-8") from exc
    try:
        value = loads_strict_json(text)
    except CanonicalJSONError as exc:
        raise WorkspaceEvidenceError("cannot load workspace evidence ledger") from exc
    ledger = _ledger_from_dict(value)
    _validate_asset_ids(ledger, manifest)
    return ledger


def append_evidence(
    root: str | Path,
    *,
    association_id: str,
    asset_ids: Sequence[str],
    evidence: Sequence[EvidenceRef],
) -> EvidenceLedger:
    """Append one explicit association without running or discovering evidence."""

    record = EvidenceAssociation(
        association_id=association_id,
        asset_ids=asset_ids,
        evidence=evidence,
    )
    root_path = _root_path(root, must_exist=True)
    manifest = open_workspace(root_path)
    _metadata_path_collision(manifest)

    path = root_path / _EVIDENCE_FILENAME
    if path.is_symlink():
        raise WorkspaceEvidenceError("workspace evidence file must not be a symbolic link")
    if path.exists():
        ledger = load_evidence_ledger(root_path)
    else:
        ledger = EvidenceLedger(schema_version=1, records=())

    if any(item.association_id == record.association_id for item in ledger.records):
        raise WorkspaceEvidenceError(
            f"evidence association_id collision: {record.association_id!r}"
        )
    updated = EvidenceLedger(
        schema_version=ledger.schema_version,
        records=(*ledger.records, record),
    )
    _validate_asset_ids(updated, manifest)
    save_evidence_ledger(updated, root_path, overwrite=path.exists())
    return updated
