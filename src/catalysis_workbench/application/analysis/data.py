"""Deterministic scientific-input descriptors for v1.1 analysis documents."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from catalysis_workbench._canonical_json import canonical_json_bytes, canonical_json_sha256

_SUPPORTED_SUFFIXES = frozenset({".csv", ".txt", ".tsv", ".dat", ".xlsx", ".xlsm"})
_DELIMITED_SUFFIXES = frozenset({".csv", ".txt", ".tsv", ".dat"})
_EXCEL_SUFFIXES = frozenset({".xlsx", ".xlsm"})
_LOADER_ID = "catalysis.io.tabular.v1"


class AnalysisDataError(ValueError):
    """Raised when deterministic analysis-data state is invalid."""


def _text(value: object, *, label: str) -> str:
    if type(value) is not str or not value:
        raise AnalysisDataError(f"{label} must be a non-empty string")
    if value != value.strip():
        raise AnalysisDataError(f"{label} must not have surrounding whitespace")
    canonical_json_bytes(value)
    return value


def _optional_text(value: object | None, *, label: str) -> str | None:
    if value is None:
        return None
    return _text(value, label=label)


def _sha256(value: object, *, label: str) -> str:
    checked = _text(value, label=label)
    if len(checked) != 64 or checked != checked.lower():
        raise AnalysisDataError(f"{label} must be a 64-character lowercase SHA-256")
    try:
        int(checked, 16)
    except ValueError as exc:
        raise AnalysisDataError(f"{label} must be a 64-character lowercase SHA-256") from exc
    return checked


def _column_ref(value: object, *, label: str) -> str | int:
    if type(value) is int:
        if value < 0:
            raise AnalysisDataError(f"{label} integer position must be >= 0")
        return value
    if type(value) is str:
        return _text(value, label=label)
    raise AnalysisDataError(f"{label} must be an exact header string or zero-based integer")


def _source_format_for_suffix(suffix: str) -> str:
    if suffix in _DELIMITED_SUFFIXES:
        return "delimited_text"
    if suffix in _EXCEL_SUFFIXES:
        return "excel"
    raise AnalysisDataError(
        f"unsupported tabular suffix {suffix!r}; supported: "
        ".csv, .txt, .tsv, .dat, .xlsx, .xlsm"
    )


@dataclass(frozen=True, slots=True)
class SourceSpec:
    """Path-independent identity and user-facing origin metadata for raw bytes."""

    original_name: str
    source_format: str
    file_suffix: str
    content_sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        name = _text(self.original_name, label="original_name")
        source_format = _text(self.source_format, label="source_format")
        suffix = _text(self.file_suffix, label="file_suffix").lower()
        if suffix not in _SUPPORTED_SUFFIXES:
            _source_format_for_suffix(suffix)
        expected_format = _source_format_for_suffix(suffix)
        if source_format != expected_format:
            raise AnalysisDataError(
                f"source_format {source_format!r} does not match suffix {suffix!r}"
            )
        digest = _sha256(self.content_sha256, label="content_sha256")
        if type(self.size_bytes) is not int or self.size_bytes < 0:
            raise AnalysisDataError("size_bytes must be a non-negative integer")
        object.__setattr__(self, "original_name", name)
        object.__setattr__(self, "source_format", source_format)
        object.__setattr__(self, "file_suffix", suffix)
        object.__setattr__(self, "content_sha256", digest)

    @property
    def workspace_asset_id(self) -> str:
        return f"raw-{self.content_sha256}"

    @property
    def workspace_destination(self) -> str:
        return f"data/raw/{self.content_sha256}{self.file_suffix}"


@dataclass(frozen=True, slots=True)
class TabularMappingSpec:
    """Explicit parser and scientific-axis mapping for one y(x) series."""

    loader_id: str = _LOADER_ID
    sheet: str | None = None
    delimiter: str | None = None
    header: int | None = 0
    skip_rows: int = 0
    encoding: str | None = "utf-8"
    x_column: str | int = 0
    y_column: str | int = 1
    x_role: str = "x"
    y_role: str = "y"
    x_unit: str | None = None
    y_unit: str | None = None
    x_reference: str | None = None
    mapping_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        loader_id = _text(self.loader_id, label="loader_id")
        if loader_id != _LOADER_ID:
            raise AnalysisDataError(f"unsupported loader_id: {loader_id!r}")
        sheet = _optional_text(self.sheet, label="sheet")
        delimiter = self.delimiter
        if delimiter is not None:
            if type(delimiter) is not str or not delimiter:
                raise AnalysisDataError("delimiter must be a non-empty string or None")
            canonical_json_bytes(delimiter)
        if self.header is not None and (type(self.header) is not int or self.header < 0):
            raise AnalysisDataError("header must be None or a non-negative integer")
        if type(self.skip_rows) is not int or self.skip_rows < 0:
            raise AnalysisDataError("skip_rows must be a non-negative integer")
        encoding = _optional_text(self.encoding, label="encoding")
        x_column = _column_ref(self.x_column, label="x_column")
        y_column = _column_ref(self.y_column, label="y_column")
        if x_column == y_column:
            raise AnalysisDataError("x_column and y_column must be different")
        x_role = _text(self.x_role, label="x_role")
        y_role = _text(self.y_role, label="y_role")
        x_unit = _optional_text(self.x_unit, label="x_unit")
        y_unit = _optional_text(self.y_unit, label="y_unit")
        x_reference = _optional_text(self.x_reference, label="x_reference")
        object.__setattr__(self, "loader_id", loader_id)
        object.__setattr__(self, "sheet", sheet)
        object.__setattr__(self, "delimiter", delimiter)
        object.__setattr__(self, "encoding", encoding)
        object.__setattr__(self, "x_column", x_column)
        object.__setattr__(self, "y_column", y_column)
        object.__setattr__(self, "x_role", x_role)
        object.__setattr__(self, "y_role", y_role)
        object.__setattr__(self, "x_unit", x_unit)
        object.__setattr__(self, "y_unit", y_unit)
        object.__setattr__(self, "x_reference", x_reference)
        mapping_sha256 = canonical_json_sha256(_mapping_to_plain_dict(self))
        object.__setattr__(self, "mapping_sha256", mapping_sha256)


@dataclass(frozen=True, slots=True)
class DataSeriesSpec:
    """One deterministic raw-source + mapping scientific input."""

    source: SourceSpec
    mapping: TabularMappingSpec
    display_name: str
    input_sha256: str = field(init=False)
    data_id: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.source, SourceSpec):
            raise TypeError("source must be a SourceSpec")
        if not isinstance(self.mapping, TabularMappingSpec):
            raise TypeError("mapping must be a TabularMappingSpec")
        display_name = _text(self.display_name, label="display_name")
        if self.source.source_format == "delimited_text" and self.mapping.delimiter is None:
            raise AnalysisDataError("delimited-text mappings must persist an explicit delimiter")
        if self.source.source_format == "excel":
            if self.mapping.delimiter is not None:
                raise AnalysisDataError("Excel mappings must not define a delimiter")
            if self.mapping.sheet is None:
                raise AnalysisDataError("Excel mappings must persist an explicit sheet name")
        digest = canonical_json_sha256(
            {
                "source_sha256": self.source.content_sha256,
                "mapping_sha256": self.mapping.mapping_sha256,
            }
        )
        object.__setattr__(self, "display_name", display_name)
        object.__setattr__(self, "input_sha256", digest)
        object.__setattr__(self, "data_id", f"series-{digest}")


def source_spec_from_file(path: str | Path) -> SourceSpec:
    """Create a path-independent source identity from exact file bytes."""

    import hashlib

    source = Path(path)
    if source.is_symlink():
        raise AnalysisDataError("analysis source must not be a symbolic link")
    if not source.exists():
        raise FileNotFoundError(source)
    if not source.is_file():
        raise AnalysisDataError("analysis source must be a regular file")
    suffix = source.suffix.lower()
    source_format = _source_format_for_suffix(suffix)
    digest = hashlib.sha256()
    size = 0
    with source.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)
    return SourceSpec(
        original_name=source.name,
        source_format=source_format,
        file_suffix=suffix,
        content_sha256=digest.hexdigest(),
        size_bytes=size,
    )


def _source_to_plain_dict(source: SourceSpec) -> dict[str, Any]:
    return {
        "original_name": source.original_name,
        "source_format": source.source_format,
        "file_suffix": source.file_suffix,
        "content_sha256": source.content_sha256,
        "size_bytes": source.size_bytes,
    }


def _mapping_to_plain_dict(mapping: TabularMappingSpec) -> dict[str, Any]:
    return {
        "loader_id": mapping.loader_id,
        "sheet": mapping.sheet,
        "delimiter": mapping.delimiter,
        "header": mapping.header,
        "skip_rows": mapping.skip_rows,
        "encoding": mapping.encoding,
        "x_column": mapping.x_column,
        "y_column": mapping.y_column,
        "x_role": mapping.x_role,
        "y_role": mapping.y_role,
        "x_unit": mapping.x_unit,
        "y_unit": mapping.y_unit,
        "x_reference": mapping.x_reference,
    }


def _data_series_to_plain_dict(series: DataSeriesSpec) -> dict[str, Any]:
    return {
        "source": _source_to_plain_dict(series.source),
        "mapping": _mapping_to_plain_dict(series.mapping),
        "display_name": series.display_name,
    }


def _require_exact_fields(value: object, required: frozenset[str], *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(type(key) is str for key in value):
        raise AnalysisDataError(f"serialized {label} must be an object with string keys")
    fields = set(value)
    missing = sorted(required - fields)
    unknown = sorted(fields - required)
    if missing or unknown:
        raise AnalysisDataError(
            f"invalid {label} fields; missing={missing!r}, unknown={unknown!r}"
        )
    return value


_SOURCE_FIELDS = frozenset(
    {"original_name", "source_format", "file_suffix", "content_sha256", "size_bytes"}
)
_MAPPING_FIELDS = frozenset(
    {
        "loader_id",
        "sheet",
        "delimiter",
        "header",
        "skip_rows",
        "encoding",
        "x_column",
        "y_column",
        "x_role",
        "y_role",
        "x_unit",
        "y_unit",
        "x_reference",
    }
)
_DATA_FIELDS = frozenset({"source", "mapping", "display_name"})


def _source_from_dict(value: object) -> SourceSpec:
    item = _require_exact_fields(value, _SOURCE_FIELDS, label="source spec")
    return SourceSpec(**item)


def _mapping_from_dict(value: object) -> TabularMappingSpec:
    item = _require_exact_fields(value, _MAPPING_FIELDS, label="tabular mapping")
    return TabularMappingSpec(**item)


def _data_series_from_dict(value: object) -> DataSeriesSpec:
    item = _require_exact_fields(value, _DATA_FIELDS, label="data series")
    return DataSeriesSpec(
        source=_source_from_dict(item["source"]),
        mapping=_mapping_from_dict(item["mapping"]),
        display_name=item["display_name"],
    )


__all__ = [
    "AnalysisDataError",
    "DataSeriesSpec",
    "SourceSpec",
    "TabularMappingSpec",
    "source_spec_from_file",
]
