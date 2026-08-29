"""Deterministic user-facing analysis document state."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from catalysis_workbench._canonical_json import (
    CanonicalJSONError,
    canonical_json_bytes,
    canonical_json_sha256,
)

from .data import (
    AnalysisDataError,
    DataSeriesSpec,
    _data_series_from_dict,
    _data_series_to_plain_dict,
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
    """Deterministic v1.1 document containing task, title, and mapped scientific inputs.

    ``schema_version=1`` remains accepted for Block-1 source compatibility and is
    normalized immediately to the current in-memory schema 2. Persisted schema-1
    documents are migrated explicitly by :func:`_document_from_dict` without writing
    the project file during open.
    """

    schema_version: int
    task_id: str
    title: str
    data_series: Sequence[DataSeriesSpec] = ()
    document_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version not in {1, 2}:
            raise AnalysisDocumentError("analysis schema_version must be the integer 1 or 2")
        try:
            task = get_analysis_task_descriptor(self.task_id)
        except ValueError as exc:
            raise AnalysisDocumentError(str(exc)) from exc
        object.__setattr__(self, "schema_version", 2)
        object.__setattr__(self, "task_id", task.task_id)
        object.__setattr__(self, "title", _title(self.title))

        if isinstance(self.data_series, (str, bytes)) or not isinstance(
            self.data_series, Sequence
        ):
            raise AnalysisDocumentError("analysis data_series must be an ordered sequence")
        data_series = tuple(self.data_series)
        if not all(isinstance(item, DataSeriesSpec) for item in data_series):
            raise TypeError("analysis data_series must contain DataSeriesSpec instances")
        data_ids = tuple(item.data_id for item in data_series)
        if len(data_ids) != len(set(data_ids)):
            raise AnalysisDocumentError("analysis data_series contains duplicate scientific inputs")
        object.__setattr__(self, "data_series", data_series)

        try:
            digest = canonical_json_sha256(_document_to_plain_dict(self))
        except CanonicalJSONError as exc:
            raise AnalysisDocumentError("analysis document cannot be canonicalized") from exc
        object.__setattr__(self, "document_sha256", digest)


_DOCUMENT_V1_FIELDS = frozenset({"schema_version", "task_id", "title"})
_DOCUMENT_V2_FIELDS = frozenset({"schema_version", "task_id", "title", "data_series"})


def _document_to_plain_dict(document: AnalysisDocument) -> dict[str, Any]:
    if not isinstance(document, AnalysisDocument):
        raise TypeError("document must be an AnalysisDocument")
    return {
        "schema_version": 2,
        "task_id": document.task_id,
        "title": document.title,
        "data_series": [_data_series_to_plain_dict(item) for item in document.data_series],
    }


def _validate_fields(value: dict[str, Any], required: frozenset[str]) -> None:
    fields = set(value)
    missing = sorted(required - fields)
    unknown = sorted(fields - required)
    if missing or unknown:
        raise AnalysisDocumentError(
            f"invalid analysis document fields; missing={missing!r}, unknown={unknown!r}"
        )


def _document_from_dict(value: object) -> AnalysisDocument:
    """Parse persisted schema 1/2 and return the normalized in-memory schema 2."""

    if not isinstance(value, dict):
        raise AnalysisDocumentError("serialized analysis document must be an object")
    if not all(type(key) is str for key in value):
        raise AnalysisDocumentError("analysis document field names must be strings")
    schema_version = value.get("schema_version")
    if type(schema_version) is not int or schema_version not in {1, 2}:
        raise AnalysisDocumentError("analysis schema_version must be the integer 1 or 2")

    if schema_version == 1:
        _validate_fields(value, _DOCUMENT_V1_FIELDS)
        return AnalysisDocument(
            schema_version=2,
            task_id=value["task_id"],
            title=value["title"],
            data_series=(),
        )

    _validate_fields(value, _DOCUMENT_V2_FIELDS)
    raw_series = value["data_series"]
    if not isinstance(raw_series, list):
        raise AnalysisDocumentError("serialized analysis data_series must be an array")
    try:
        data_series = tuple(_data_series_from_dict(item) for item in raw_series)
    except AnalysisDataError as exc:
        raise AnalysisDocumentError(str(exc)) from exc
    return AnalysisDocument(
        schema_version=2,
        task_id=value["task_id"],
        title=value["title"],
        data_series=data_series,
    )


__all__ = ["AnalysisDocument", "AnalysisDocumentError"]
