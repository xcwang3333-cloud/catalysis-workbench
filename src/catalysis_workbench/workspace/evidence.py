"""Persistent deterministic associations for reviewed workspace evidence."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from string import hexdigits

from catalysis_workbench._canonical_json import (
    CanonicalJSONError,
    canonical_json_bytes,
    canonical_json_sha256,
    loads_strict_json,
)
from catalysis_workbench.workflow.batch import BatchRunRecord
from catalysis_workbench.workflow.execution import WorkflowRun
from catalysis_workbench.workflow.qa import QAReport
from catalysis_workbench.workflow.recipe import WorkflowRecipe

from .manifest import WorkspaceError, _identifier
from .persistence import _replace_manifest_atomically, _root_path, open_workspace

__all__ = [
    "EvidenceLedger",
    "EvidenceRecord",
    "append_evidence",
    "create_evidence_ledger",
    "open_evidence_ledger",
    "record_evidence",
    "save_evidence_ledger",
]

_EVIDENCE_FILENAME = "workspace-evidence.json"
_EVIDENCE_KINDS = frozenset(
    {"artifact", "batch_run", "qa_report", "recipe", "workflow_run"}
)


def _sha256(value: object, *, label: str) -> str:
    if type(value) is not str or len(value) != 64:
        raise WorkspaceError(f"{label} must be a 64-character lowercase SHA-256")
    if value != value.lower() or any(character not in hexdigits.lower() for character in value):
        raise WorkspaceError(f"{label} must be a 64-character lowercase SHA-256")
    return value


def _kind(value: object) -> str:
    if type(value) is not str or value not in _EVIDENCE_KINDS:
        allowed = ", ".join(sorted(_EVIDENCE_KINDS))
        raise WorkspaceError(f"evidence kind must be one of: {allowed}")
    return value


def _identifiers(value: object, *, label: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise WorkspaceError(f"{label} must be an ordered sequence")
    checked = tuple(_identifier(item, label=f"{label} item") for item in value)
    if len(set(checked)) != len(checked):
        raise WorkspaceError(f"{label} values must be unique")
    return checked


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    """One deterministic association to already-produced reviewed evidence."""

    record_id: str
    kind: str
    evidence_sha256: str
    asset_ids: Sequence[str] = ()
    related_record_ids: Sequence[str] = ()
    record_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        record_id = _identifier(self.record_id, label="record_id")
        kind = _kind(self.kind)
        evidence_sha256 = _sha256(self.evidence_sha256, label="evidence_sha256")
        asset_ids = _identifiers(self.asset_ids, label="asset_ids")
        related_record_ids = _identifiers(
            self.related_record_ids,
            label="related_record_ids",
        )
        if record_id in related_record_ids:
            raise WorkspaceError("evidence record cannot relate to itself")

        digest = canonical_json_sha256(
            {
                "evidence_record_schema_version": 1,
                "record_id": record_id,
                "kind": kind,
                "evidence_sha256": evidence_sha256,
                "asset_ids": list(asset_ids),
                "related_record_ids": list(related_record_ids),
            }
        )
        object.__setattr__(self, "record_id", record_id)
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "evidence_sha256", evidence_sha256)
        object.__setattr__(self, "asset_ids", asset_ids)
        object.__setattr__(self, "related_record_ids", related_record_ids)
        object.__setattr__(self, "record_sha256", digest)


@dataclass(frozen=True, slots=True)
class EvidenceLedger:
    """Ordered immutable persistent evidence-association ledger."""

    schema_version: int
    records: Sequence[EvidenceRecord]
    ledger_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise WorkspaceError("evidence ledger schema_version must be the integer 1")
        if isinstance(self.records, (str, bytes)) or not isinstance(self.records, Sequence):
            raise WorkspaceError("evidence ledger records must be an ordered sequence")

        records = tuple(self.records)
        if any(not isinstance(record, EvidenceRecord) for record in records):
            raise TypeError("evidence ledger records must contain EvidenceRecord values")
        record_ids = tuple(record.record_id for record in records)
        if len(set(record_ids)) != len(record_ids):
            raise WorkspaceError("evidence record_id values must be unique")

        known = set(record_ids)
        for record in records:
            missing = sorted(set(record.related_record_ids) - known)
            if missing:
                raise WorkspaceError(
                    f"evidence record {record.record_id!r} references unknown records: {missing!r}"
                )

        digest = canonical_json_sha256(
            {
                "evidence_ledger_identity_schema_version": 1,
                "records": [
                    {"record_id": record.record_id, "record_sha256": record.record_sha256}
                    for record in records
                ],
            }
        )
        object.__setattr__(self, "records", records)
        object.__setattr__(self, "ledger_sha256", digest)


def record_evidence(
    record_id: str,
    evidence: WorkflowRecipe | WorkflowRun | BatchRunRecord | QAReport,
    *,
    asset_ids: Sequence[str] = (),
    related_record_ids: Sequence[str] = (),
) -> EvidenceRecord:
    """Reference the authoritative digest already exposed by a reviewed evidence object."""

    if isinstance(evidence, WorkflowRecipe):
        kind = "recipe"
        digest = evidence.recipe_sha256
    elif isinstance(evidence, WorkflowRun):
        kind = "workflow_run"
        digest = evidence.record_sha256
    elif isinstance(evidence, BatchRunRecord):
        kind = "batch_run"
        digest = evidence.record_sha256
    elif isinstance(evidence, QAReport):
        kind = "qa_report"
        digest = evidence.report_sha256
    else:
        raise TypeError(
            "evidence must be WorkflowRecipe, WorkflowRun, BatchRunRecord, or QAReport"
        )

    return EvidenceRecord(
        record_id=record_id,
        kind=kind,
        evidence_sha256=digest,
        asset_ids=asset_ids,
        related_record_ids=related_record_ids,
    )


_RECORD_REQUIRED_FIELDS = frozenset(
    {"record_id", "kind", "evidence_sha256", "asset_ids", "related_record_ids"}
)
_LEDGER_REQUIRED_FIELDS = frozenset({"schema_version", "records"})


def _required_fields(
    value: Mapping[object, object],
    *,
    required: frozenset[str],
    label: str,
) -> None:
    if not all(type(key) is str for key in value):
        raise WorkspaceError(f"{label} field names must be strings")
    fields = set(value)
    missing = sorted(required - fields)
    unknown = sorted(fields - required)
    if missing or unknown:
        raise WorkspaceError(
            f"invalid {label} fields; missing={missing!r}, unknown={unknown!r}"
        )


def _record_to_plain_dict(record: EvidenceRecord) -> dict[str, object]:
    return {
        "record_id": record.record_id,
        "kind": record.kind,
        "evidence_sha256": record.evidence_sha256,
        "asset_ids": list(record.asset_ids),
        "related_record_ids": list(record.related_record_ids),
    }


def _ledger_to_plain_dict(ledger: EvidenceLedger) -> dict[str, object]:
    return {
        "schema_version": ledger.schema_version,
        "records": [_record_to_plain_dict(record) for record in ledger.records],
    }


def _ledger_from_dict(value: object) -> EvidenceLedger:
    if not isinstance(value, Mapping):
        raise WorkspaceError("serialized evidence ledger must be an object")
    _required_fields(value, required=_LEDGER_REQUIRED_FIELDS, label="evidence ledger")
    records = value["records"]
    if not isinstance(records, list):
        raise WorkspaceError("serialized evidence records must be a list")

    parsed: list[EvidenceRecord] = []
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise WorkspaceError(f"serialized evidence record {index} must be an object")
        _required_fields(
            record,
            required=_RECORD_REQUIRED_FIELDS,
            label=f"evidence record {index}",
        )
        parsed.append(
            EvidenceRecord(
                record_id=record["record_id"],
                kind=record["kind"],
                evidence_sha256=record["evidence_sha256"],
                asset_ids=record["asset_ids"],
                related_record_ids=record["related_record_ids"],
            )
        )
    return EvidenceLedger(schema_version=value["schema_version"], records=parsed)


def _payload(ledger: EvidenceLedger) -> bytes:
    if not isinstance(ledger, EvidenceLedger):
        raise TypeError("ledger must be an EvidenceLedger")
    try:
        return canonical_json_bytes(_ledger_to_plain_dict(ledger)) + b"\n"
    except CanonicalJSONError as exc:
        raise WorkspaceError("evidence ledger cannot be serialized") from exc


def _evidence_path(root: Path) -> Path:
    return root / _EVIDENCE_FILENAME


def _validate_workspace_associations(ledger: EvidenceLedger, root: Path) -> None:
    manifest = open_workspace(root)
    known_assets = {asset.asset_id for asset in manifest.assets}
    for record in ledger.records:
        missing = sorted(set(record.asset_ids) - known_assets)
        if missing:
            raise WorkspaceError(
                f"evidence record {record.record_id!r} references unknown assets: {missing!r}"
            )


def create_evidence_ledger(root: str | Path) -> EvidenceLedger:
    """Create an empty evidence ledger beside an existing workspace manifest."""

    root_path = _root_path(root, must_exist=True)
    manifest = open_workspace(root_path)
    if any(
        asset.policy == "copy" and asset.path == _EVIDENCE_FILENAME
        for asset in manifest.assets
    ):
        raise WorkspaceError("workspace evidence metadata path is already cataloged as an asset")

    ledger = EvidenceLedger(schema_version=1, records=())
    path = _evidence_path(root_path)
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    with path.open("xb") as stream:
        stream.write(_payload(ledger))
    return ledger


def save_evidence_ledger(
    ledger: EvidenceLedger,
    root: str | Path,
    *,
    overwrite: bool = False,
) -> None:
    """Persist a fully validated evidence ledger at an explicit workspace root."""

    if type(overwrite) is not bool:
        raise TypeError("overwrite must be a bool")
    payload = _payload(ledger)
    root_path = _root_path(root, must_exist=True)
    _validate_workspace_associations(ledger, root_path)
    path = _evidence_path(root_path)
    if path.is_symlink():
        raise WorkspaceError("workspace evidence ledger must not be a symbolic link")
    if overwrite:
        _replace_manifest_atomically(path, payload)
        return
    with path.open("xb") as stream:
        stream.write(payload)


def open_evidence_ledger(root: str | Path) -> EvidenceLedger:
    """Strictly load deterministic evidence associations without executing them."""

    root_path = _root_path(root, must_exist=True)
    open_workspace(root_path)
    path = _evidence_path(root_path)
    if path.is_symlink():
        raise WorkspaceError("workspace evidence ledger must not be a symbolic link")
    if not path.exists():
        raise FileNotFoundError(path)
    if not path.is_file():
        raise WorkspaceError("workspace evidence ledger path must be a regular file")
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise WorkspaceError("workspace evidence ledger is not valid UTF-8") from exc
    try:
        value = loads_strict_json(text)
    except CanonicalJSONError as exc:
        raise WorkspaceError("cannot load workspace evidence ledger") from exc
    ledger = _ledger_from_dict(value)
    _validate_workspace_associations(ledger, root_path)
    return ledger


def append_evidence(root: str | Path, record: EvidenceRecord) -> EvidenceLedger:
    """Append one prevalidated association in literal caller order."""

    if not isinstance(record, EvidenceRecord):
        raise TypeError("record must be an EvidenceRecord")
    root_path = _root_path(root, must_exist=True)
    ledger = open_evidence_ledger(root_path)
    if any(existing.record_id == record.record_id for existing in ledger.records):
        raise WorkspaceError(f"evidence record_id collision: {record.record_id!r}")

    known_assets = {asset.asset_id for asset in open_workspace(root_path).assets}
    missing_assets = sorted(set(record.asset_ids) - known_assets)
    if missing_assets:
        raise WorkspaceError(
            f"evidence record {record.record_id!r} references unknown assets: {missing_assets!r}"
        )

    known_records = {existing.record_id for existing in ledger.records}
    missing_records = sorted(set(record.related_record_ids) - known_records)
    if missing_records:
        raise WorkspaceError(
            f"evidence record {record.record_id!r} references unavailable records: "
            f"{missing_records!r}"
        )

    updated = EvidenceLedger(
        schema_version=ledger.schema_version,
        records=(*ledger.records, record),
    )
    save_evidence_ledger(updated, root_path, overwrite=True)
    return updated
