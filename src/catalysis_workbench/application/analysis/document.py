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
from .processing import (
    AnalysisProcessingError,
    AnalysisSpec,
    FEPartialCurrentAnalysisSpec,
    LSVAnalysisSpec,
    analysis_spec_from_dict,
    analysis_spec_to_plain_dict,
    default_analysis_spec,
    validate_analysis_spec,
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


def _validate_analysis_references(
    analysis: AnalysisSpec,
    data_ids: tuple[str, ...],
) -> None:
    available = set(data_ids)
    if isinstance(analysis, LSVAnalysisSpec):
        unknown = sorted(set(analysis.overrides) - available)
        if unknown:
            raise AnalysisDocumentError(
                f"LSV processing overrides reference unknown data_id values: {unknown!r}"
            )
        return
    if isinstance(analysis, FEPartialCurrentAnalysisSpec):
        unknown_overrides = sorted(set(analysis.current_overrides) - available)
        if unknown_overrides:
            raise AnalysisDocumentError(
                "current-processing overrides reference unknown data_id values: "
                f"{unknown_overrides!r}"
            )
        referenced = {
            data_id
            for pair in analysis.pairs
            for data_id in (pair.current_data_id, pair.fe_data_id)
        }
        unknown_pairs = sorted(referenced - available)
        if unknown_pairs:
            raise AnalysisDocumentError(
                f"partial-current pairs reference unknown data_id values: {unknown_pairs!r}"
            )


@dataclass(frozen=True, slots=True)
class AnalysisDocument:
    """Deterministic v1.1 document containing mapped inputs and scientific settings.

    Persisted schema versions 1 and 2 remain readable. They are normalized in memory
    to schema 3 without writing the project during open. Schema 3 adds task-specific
    scientific processing state; computed arrays remain runtime-only.
    """

    schema_version: int
    task_id: str
    title: str
    data_series: Sequence[DataSeriesSpec] = ()
    analysis: AnalysisSpec | None = None
    document_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version not in {1, 2, 3}:
            raise AnalysisDocumentError(
                "analysis schema_version must be the integer 1, 2, or 3"
            )
        try:
            task = get_analysis_task_descriptor(self.task_id)
        except ValueError as exc:
            raise AnalysisDocumentError(str(exc)) from exc
        object.__setattr__(self, "schema_version", 3)
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

        analysis = self.analysis
        if analysis is None:
            analysis = default_analysis_spec(task.task_id)
        try:
            analysis = validate_analysis_spec(task.task_id, analysis)
        except (AnalysisProcessingError, TypeError, ValueError) as exc:
            raise AnalysisDocumentError(str(exc)) from exc
        _validate_analysis_references(analysis, data_ids)
        object.__setattr__(self, "analysis", analysis)

        try:
            digest = canonical_json_sha256(_document_to_plain_dict(self))
        except CanonicalJSONError as exc:
            raise AnalysisDocumentError("analysis document cannot be canonicalized") from exc
        object.__setattr__(self, "document_sha256", digest)


_DOCUMENT_V1_FIELDS = frozenset({"schema_version", "task_id", "title"})
_DOCUMENT_V2_FIELDS = frozenset({"schema_version", "task_id", "title", "data_series"})
_DOCUMENT_V3_FIELDS = frozenset(
    {"schema_version", "task_id", "title", "data_series", "analysis"}
)


def _document_to_plain_dict(document: AnalysisDocument) -> dict[str, Any]:
    if not isinstance(document, AnalysisDocument):
        raise TypeError("document must be an AnalysisDocument")
    assert document.analysis is not None
    return {
        "schema_version": 3,
        "task_id": document.task_id,
        "title": document.title,
        "data_series": [_data_series_to_plain_dict(item) for item in document.data_series],
        "analysis": analysis_spec_to_plain_dict(document.task_id, document.analysis),
    }


def _validate_fields(value: dict[str, Any], required: frozenset[str]) -> None:
    fields = set(value)
    missing = sorted(required - fields)
    unknown = sorted(fields - required)
    if missing or unknown:
        raise AnalysisDocumentError(
            f"invalid analysis document fields; missing={missing!r}, unknown={unknown!r}"
        )


def _data_series_from_value(raw_series: object) -> tuple[DataSeriesSpec, ...]:
    if not isinstance(raw_series, list):
        raise AnalysisDocumentError("serialized analysis data_series must be an array")
    try:
        return tuple(_data_series_from_dict(item) for item in raw_series)
    except AnalysisDataError as exc:
        raise AnalysisDocumentError(str(exc)) from exc


def _document_from_dict(value: object) -> AnalysisDocument:
    """Parse persisted schema 1/2/3 and return normalized in-memory schema 3."""

    if not isinstance(value, dict):
        raise AnalysisDocumentError("serialized analysis document must be an object")
    if not all(type(key) is str for key in value):
        raise AnalysisDocumentError("analysis document field names must be strings")
    schema_version = value.get("schema_version")
    if type(schema_version) is not int or schema_version not in {1, 2, 3}:
        raise AnalysisDocumentError(
            "analysis schema_version must be the integer 1, 2, or 3"
        )

    if schema_version == 1:
        _validate_fields(value, _DOCUMENT_V1_FIELDS)
        return AnalysisDocument(
            schema_version=3,
            task_id=value["task_id"],
            title=value["title"],
            data_series=(),
        )

    if schema_version == 2:
        _validate_fields(value, _DOCUMENT_V2_FIELDS)
        return AnalysisDocument(
            schema_version=3,
            task_id=value["task_id"],
            title=value["title"],
            data_series=_data_series_from_value(value["data_series"]),
        )

    _validate_fields(value, _DOCUMENT_V3_FIELDS)
    try:
        analysis = analysis_spec_from_dict(value["task_id"], value["analysis"])
    except (AnalysisProcessingError, TypeError, ValueError) as exc:
        raise AnalysisDocumentError(str(exc)) from exc
    return AnalysisDocument(
        schema_version=3,
        task_id=value["task_id"],
        title=value["title"],
        data_series=_data_series_from_value(value["data_series"]),
        analysis=analysis,
    )


__all__ = ["AnalysisDocument", "AnalysisDocumentError"]
