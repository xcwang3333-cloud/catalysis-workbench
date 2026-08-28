"""Deterministic user-facing analysis document state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from catalysis_workbench._canonical_json import (
    CanonicalJSONError,
    canonical_json_bytes,
    canonical_json_sha256,
)

from .tasks import get_analysis_task_descriptor


class AnalysisDocumentError(ValueError):
    """Raised when an analysis document cannot satisfy its strict schema."""


def _title(value: object) -> str:
    if type(value) is not str or not value:
        raise AnalysisDocumentError("analysis title must be a non-empty string")
    if value != value.strip():
        raise AnalysisDocumentError("analysis title must not have surrounding whitespace")
    try:
        canonical_json_bytes(value)
    except CanonicalJSONError as exc:
        raise AnalysisDocumentError("analysis title must be valid UTF-8") from exc
    return value


@dataclass(frozen=True, slots=True)
class AnalysisDocument:
    """Minimal deterministic document shared by every v1.1 analysis task."""

    schema_version: int
    task_id: str
    title: str
    document_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise AnalysisDocumentError("analysis schema_version must be the integer 1")
        try:
            task = get_analysis_task_descriptor(self.task_id)
        except ValueError as exc:
            raise AnalysisDocumentError(str(exc)) from exc
        object.__setattr__(self, "task_id", task.task_id)
        object.__setattr__(self, "title", _title(self.title))
        try:
            digest = canonical_json_sha256(_document_to_plain_dict(self))
        except CanonicalJSONError as exc:
            raise AnalysisDocumentError("analysis document cannot be canonicalized") from exc
        object.__setattr__(self, "document_sha256", digest)


_DOCUMENT_FIELDS = frozenset({"schema_version", "task_id", "title"})


def _document_to_plain_dict(document: AnalysisDocument) -> dict[str, Any]:
    if not isinstance(document, AnalysisDocument):
        raise TypeError("document must be an AnalysisDocument")
    return {
        "schema_version": document.schema_version,
        "task_id": document.task_id,
        "title": document.title,
    }


def _document_from_dict(value: object) -> AnalysisDocument:
    if not isinstance(value, dict):
        raise AnalysisDocumentError("serialized analysis document must be an object")
    if not all(type(key) is str for key in value):
        raise AnalysisDocumentError("analysis document field names must be strings")
    fields = set(value)
    missing = sorted(_DOCUMENT_FIELDS - fields)
    unknown = sorted(fields - _DOCUMENT_FIELDS)
    if missing or unknown:
        raise AnalysisDocumentError(
            f"invalid analysis document fields; missing={missing!r}, unknown={unknown!r}"
        )
    return AnalysisDocument(
        schema_version=value["schema_version"],
        task_id=value["task_id"],
        title=value["title"],
    )


__all__ = ["AnalysisDocument", "AnalysisDocumentError"]
