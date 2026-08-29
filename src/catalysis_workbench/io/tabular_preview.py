"""Bounded GUI-neutral previews for supported tabular analysis inputs."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .tabular import _header_parts


class TabularPreviewError(ValueError):
    """Raised when a tabular file cannot be previewed deterministically."""


@dataclass(frozen=True, slots=True)
class TabularColumnPreview:
    """One visible source column with its stable zero-based coordinate."""

    index: int
    name: str
    inferred_unit: str | None = None


@dataclass(frozen=True, slots=True)
class TabularPreview:
    """A bounded snapshot used to configure an explicit persisted mapping."""

    file_name: str
    file_suffix: str
    available_sheets: tuple[str, ...]
    selected_sheet: str | None
    resolved_delimiter: str | None
    header: int | None
    skip_rows: int
    encoding: str | None
    columns: tuple[TabularColumnPreview, ...]
    rows: tuple[tuple[str | None, ...], ...]
    truncated: bool


_SUPPORTED = frozenset({".csv", ".txt", ".tsv", ".dat", ".xlsx", ".xlsm"})


def _source(path: str | Path) -> Path:
    source = Path(path)
    if source.is_symlink():
        raise TabularPreviewError("tabular preview source must not be a symbolic link")
    if not source.exists():
        raise FileNotFoundError(source)
    if not source.is_file():
        raise TabularPreviewError("tabular preview source must be a regular file")
    if source.suffix.lower() not in _SUPPORTED:
        raise TabularPreviewError(
            f"unsupported tabular extension {source.suffix.lower()!r}; supported: "
            ".csv, .txt, .tsv, .dat, .xlsx, .xlsm"
        )
    return source


def _check_options(
    *, max_rows: int, header: int | None, skip_rows: int, encoding: str | None
) -> None:
    if type(max_rows) is not int or max_rows < 1 or max_rows > 1000:
        raise TabularPreviewError("max_rows must be an integer from 1 through 1000")
    if header is not None and (type(header) is not int or header < 0):
        raise TabularPreviewError("header must be None or a non-negative integer")
    if type(skip_rows) is not int or skip_rows < 0:
        raise TabularPreviewError("skip_rows must be a non-negative integer")
    if encoding is not None and (type(encoding) is not str or not encoding.strip()):
        raise TabularPreviewError("encoding must be a non-empty string or None")


def _sniff_delimiter(source: Path, *, encoding: str | None, skip_rows: int) -> str:
    codec = encoding or "utf-8"
    try:
        with source.open("r", encoding=codec, newline="") as stream:
            for _ in range(skip_rows):
                if stream.readline() == "":
                    break
            sample = stream.read(64 * 1024)
    except UnicodeError as exc:
        raise TabularPreviewError(f"cannot decode {source.name!r} using {codec!r}") from exc
    if not sample.strip():
        raise TabularPreviewError("cannot determine a delimiter from an empty text sample")
    try:
        return csv.Sniffer().sniff(sample, delimiters=",\t;| ").delimiter
    except csv.Error as exc:
        raise TabularPreviewError(
            "could not determine the text delimiter; choose one explicitly"
        ) from exc


def _resolved_delimiter(
    source: Path,
    *,
    delimiter: str | None,
    encoding: str | None,
    skip_rows: int,
) -> str:
    if delimiter is not None:
        if type(delimiter) is not str or not delimiter:
            raise TabularPreviewError("delimiter must be a non-empty string or None")
        return delimiter
    suffix = source.suffix.lower()
    if suffix == ".csv":
        return ","
    if suffix == ".tsv":
        return "\t"
    return _sniff_delimiter(source, encoding=encoding, skip_rows=skip_rows)


def _cell(value: Any) -> str | None:
    try:
        if bool(pd.isna(value)):
            return None
    except (TypeError, ValueError):
        pass
    return str(value)


def _preview_from_frame(
    frame: pd.DataFrame,
    *,
    source: Path,
    sheets: tuple[str, ...],
    selected_sheet: str | None,
    resolved_delimiter: str | None,
    header: int | None,
    skip_rows: int,
    encoding: str | None,
    max_rows: int,
) -> TabularPreview:
    visible = frame.iloc[:max_rows, :]
    columns: list[TabularColumnPreview] = []
    for index, column in enumerate(visible.columns):
        label, unit = _header_parts(column)
        columns.append(
            TabularColumnPreview(index=index, name=label, inferred_unit=unit)
        )
    rows = tuple(
        tuple(_cell(value) for value in row)
        for row in visible.itertuples(index=False, name=None)
    )
    return TabularPreview(
        file_name=source.name,
        file_suffix=source.suffix.lower(),
        available_sheets=sheets,
        selected_sheet=selected_sheet,
        resolved_delimiter=resolved_delimiter,
        header=header,
        skip_rows=skip_rows,
        encoding=encoding,
        columns=tuple(columns),
        rows=rows,
        truncated=len(frame.index) > max_rows,
    )


def inspect_tabular(
    path: str | Path,
    *,
    sheet: str | None = None,
    delimiter: str | None = None,
    header: int | None = 0,
    skip_rows: int = 0,
    encoding: str | None = "utf-8",
    max_rows: int = 100,
) -> TabularPreview:
    """Inspect at most ``max_rows`` rows plus one sentinel row.

    Text delimiter detection is only a configuration aid: the resolved delimiter is
    returned so callers can persist it explicitly in ``TabularMappingSpec``.
    """

    _check_options(
        max_rows=max_rows,
        header=header,
        skip_rows=skip_rows,
        encoding=encoding,
    )
    source = _source(path)
    suffix = source.suffix.lower()

    if suffix in {".xlsx", ".xlsm"}:
        if delimiter is not None:
            raise TabularPreviewError("Excel preview does not accept a delimiter")
        try:
            with pd.ExcelFile(source) as workbook:
                sheets = tuple(workbook.sheet_names)
                if not sheets:
                    raise TabularPreviewError("Excel workbook contains no sheets")
                selected = sheets[0] if sheet is None else sheet
                if selected not in sheets:
                    raise TabularPreviewError(
                        f"Excel sheet {selected!r} was not found. Available sheets: "
                        + ", ".join(sheets)
                    )
                frame = pd.read_excel(
                    workbook,
                    sheet_name=selected,
                    header=header,
                    skiprows=skip_rows,
                    nrows=max_rows + 1,
                )
        except TabularPreviewError:
            raise
        except Exception as exc:
            raise TabularPreviewError(f"cannot preview Excel file {source.name!r}") from exc
        return _preview_from_frame(
            frame,
            source=source,
            sheets=sheets,
            selected_sheet=selected,
            resolved_delimiter=None,
            header=header,
            skip_rows=skip_rows,
            encoding=None,
            max_rows=max_rows,
        )

    if sheet is not None:
        raise TabularPreviewError("delimited-text preview does not accept a sheet")
    resolved = _resolved_delimiter(
        source,
        delimiter=delimiter,
        encoding=encoding,
        skip_rows=skip_rows,
    )
    try:
        frame = pd.read_csv(
            source,
            sep=resolved,
            header=header,
            skiprows=skip_rows,
            encoding=encoding,
            nrows=max_rows + 1,
        )
    except Exception as exc:
        raise TabularPreviewError(f"cannot preview tabular file {source.name!r}") from exc
    return _preview_from_frame(
        frame,
        source=source,
        sheets=(),
        selected_sheet=None,
        resolved_delimiter=resolved,
        header=header,
        skip_rows=skip_rows,
        encoding=encoding,
        max_rows=max_rows,
    )


__all__ = [
    "TabularColumnPreview",
    "TabularPreview",
    "TabularPreviewError",
    "inspect_tabular",
]
