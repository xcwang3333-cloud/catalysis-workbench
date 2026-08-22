"""Tabular readers for common catalysis data exported as Excel, CSV, or TXT.

The reader layer deliberately performs only file parsing, column selection, basic
numeric validation, and metadata capture. It does not apply electrochemical,
spectroscopic, or plotting-specific transformations.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, TypeAlias

import pandas as pd

from catalysis_workbench.core import Axis, Dataset, Series

ColumnRef: TypeAlias = str | int
ColumnMap: TypeAlias = Mapping[ColumnRef, str]

_UNIT_PATTERN = re.compile(r"^\s*(.*?)\s*(?:/\s*)?\[([^\[\]]+)\]\s*$")


class TabularReadError(ValueError):
    """Raised when a tabular file cannot be converted into scientific series."""


def _header_parts(value: object) -> tuple[str, str | None]:
    """Return a conservative semantic label and optional unit from a header.

    Only a trailing square-bracket unit is inferred automatically, for example
    ``Potential [V]`` or ``Current density / [mA cm^-2]``. Parentheses are not
    interpreted because scientific column names often contain meaningful parentheses.
    """
    text = str(value).strip()
    match = _UNIT_PATTERN.match(text)
    if not match:
        return text, None
    label = match.group(1).strip()
    unit = match.group(2).strip()
    return label or text, unit or None


def _semantic_name(label: str, *, fallback: str) -> str:
    """Create a lightweight machine-facing axis name without claiming domain meaning."""
    name = re.sub(r"[^0-9A-Za-z]+", "_", label.strip()).strip("_").lower()
    return name or fallback


def _normalize_y_refs(y: ColumnRef | Sequence[ColumnRef]) -> tuple[ColumnRef, ...]:
    if isinstance(y, (str, int)):
        return (y,)
    refs = tuple(y)
    if not refs:
        raise TabularReadError("At least one y column must be selected")
    if not all(isinstance(ref, (str, int)) for ref in refs):
        raise TypeError("y column references must be strings or integer positions")
    return refs


def _resolve_column(frame: pd.DataFrame, ref: ColumnRef) -> tuple[int, object]:
    """Resolve a column by exact header or zero-based position."""
    if isinstance(ref, int):
        if ref < 0 or ref >= frame.shape[1]:
            raise TabularReadError(
                f"Column position {ref} is out of range for {frame.shape[1]} columns"
            )
        return ref, frame.columns[ref]

    matches = [index for index, column in enumerate(frame.columns) if str(column) == ref]
    if not matches:
        available = ", ".join(str(column) for column in frame.columns)
        raise TabularReadError(
            f"Column {ref!r} was not found. Available columns: {available}"
        )
    if len(matches) > 1:
        raise TabularReadError(
            f"Column name {ref!r} is ambiguous; select it by integer position instead"
        )
    index = matches[0]
    return index, frame.columns[index]


def _lookup(
    mapping: ColumnMap | None,
    ref: ColumnRef,
    column: object,
    index: int,
) -> str | None:
    if mapping is None:
        return None
    for candidate in (ref, column, index):
        if candidate in mapping:
            value = str(mapping[candidate]).strip()
            return value or None
    return None


def _numeric_values(frame: pd.DataFrame, index: int, *, role: str, column: object):
    source = frame.iloc[:, index]
    converted = pd.to_numeric(source, errors="coerce")
    invalid = source.notna() & converted.isna()
    if invalid.any():
        bad_index = invalid[invalid].index[:5]
        rows = [int(row) for row in bad_index]
        examples = [source.loc[row] for row in bad_index]
        raise TabularReadError(
            f"{role} column {column!r} contains non-numeric values "
            f"at rows {rows}: {examples}"
        )
    if converted.isna().all():
        raise TabularReadError(f"{role} column {column!r} contains no numeric values")
    return converted.to_numpy()


def _source_identity(path: Path, source_id: str | None) -> tuple[str, str]:
    """Return a collision-resistant source identity and normalized source path."""
    source_path = path.resolve().as_posix()
    if source_id is None:
        return source_path, source_path
    normalized = str(source_id).strip()
    if not normalized:
        raise TabularReadError("source_id must not be empty")
    return normalized, source_path


def _series_key(
    source_id: str,
    sheet: str | None,
    x_index: int,
    y_index: int,
) -> str:
    """Return a deterministic non-display key based on source coordinates."""
    sheet_token = "table" if sheet is None else sheet
    return f"{source_id}::{sheet_token}::c{x_index}->c{y_index}"


def _frame_to_series(
    frame: pd.DataFrame,
    *,
    path: Path,
    source_id: str,
    source_path: str,
    sheet: str | None,
    x: ColumnRef,
    y: ColumnRef | Sequence[ColumnRef],
    labels: ColumnMap | None,
    units: ColumnMap | None,
    axis_labels: ColumnMap | None,
    axis_names: ColumnMap | None,
) -> tuple[Series, ...]:
    if frame.empty:
        raise TabularReadError(f"No tabular data were found in {path.name!r}")

    x_index, x_column = _resolve_column(frame, x)
    x_values = _numeric_values(frame, x_index, role="x", column=x_column)
    x_header_label, x_inferred_unit = _header_parts(x_column)
    x_label = _lookup(axis_labels, x, x_column, x_index) or x_header_label
    x_unit = _lookup(units, x, x_column, x_index) or x_inferred_unit
    x_name = _lookup(axis_names, x, x_column, x_index) or _semantic_name(
        x_label, fallback=f"column_{x_index}"
    )

    y_refs = _normalize_y_refs(y)
    seen_y_indexes: set[int] = set()
    series_items: list[Series] = []
    for y_ref in y_refs:
        y_index, y_column = _resolve_column(frame, y_ref)
        if y_index == x_index:
            raise TabularReadError("x and y must refer to different columns")
        if y_index in seen_y_indexes:
            raise TabularReadError(
                f"y column {y_column!r} was selected more than once"
            )
        seen_y_indexes.add(y_index)

        y_values = _numeric_values(frame, y_index, role="y", column=y_column)
        y_header_label, y_inferred_unit = _header_parts(y_column)
        y_axis_label = _lookup(axis_labels, y_ref, y_column, y_index) or y_header_label
        y_unit = _lookup(units, y_ref, y_column, y_index) or y_inferred_unit
        y_name = _lookup(axis_names, y_ref, y_column, y_index) or _semantic_name(
            y_axis_label, fallback=f"column_{y_index}"
        )
        display_label = _lookup(labels, y_ref, y_column, y_index) or y_header_label

        source_metadata: dict[str, Any] = {
            "source_id": source_id,
            "source_path": source_path,
            "file_name": path.name,
            "file_suffix": path.suffix.lower(),
            "sheet": sheet,
            "x_column": str(x_column),
            "y_column": str(y_column),
            "x_column_index": x_index,
            "y_column_index": y_index,
        }
        series_items.append(
            Series(
                x=x_values,
                y=y_values,
                label=display_label,
                key=_series_key(source_id, sheet, x_index, y_index),
                x_axis=Axis(
                    name=x_name,
                    label=x_label,
                    unit=x_unit,
                    metadata={
                        "source_column": str(x_column),
                        "column_index": x_index,
                    },
                ),
                y_axis=Axis(
                    name=y_name,
                    label=y_axis_label,
                    unit=y_unit,
                    metadata={
                        "source_column": str(y_column),
                        "column_index": y_index,
                    },
                ),
                metadata={"source": source_metadata},
            )
        )
    return tuple(series_items)


def _dataset(
    series: Sequence[Series],
    *,
    path: Path,
    source_id: str,
    source_path: str,
    name: str | None,
    sheets: Sequence[str | None],
    metadata: Mapping[str, Any] | None,
) -> Dataset:
    dataset_metadata: dict[str, Any] = dict(metadata or {})
    dataset_metadata["source"] = {
        "source_id": source_id,
        "source_path": source_path,
        "file_name": path.name,
        "file_suffix": path.suffix.lower(),
        "sheets": tuple(sheets),
    }
    return Dataset(series=tuple(series), name=name or path.stem, metadata=dataset_metadata)


def _resolve_excel_sheets(
    available: Sequence[str],
    selection: str | int | Sequence[str | int] | None,
) -> tuple[str, ...]:
    if selection is None:
        selected = tuple(available)
    else:
        requested: tuple[str | int, ...]
        if isinstance(selection, (str, int)):
            requested = (selection,)
        else:
            requested = tuple(selection)
        selected_list: list[str] = []
        for item in requested:
            if isinstance(item, int):
                if item < 0 or item >= len(available):
                    raise TabularReadError(
                        f"Excel sheet position {item} is out of range "
                        f"for {len(available)} sheets"
                    )
                selected_list.append(available[item])
            elif item in available:
                selected_list.append(item)
            else:
                raise TabularReadError(
                    f"Excel sheet {item!r} was not found. "
                    f"Available sheets: {', '.join(available)}"
                )
        selected = tuple(selected_list)

    if not selected:
        raise TabularReadError("At least one Excel sheet must be selected")
    if len(selected) != len(set(selected)):
        raise TabularReadError("The same Excel sheet was selected more than once")
    return selected


def read_csv(
    path: str | Path,
    *,
    x: ColumnRef,
    y: ColumnRef | Sequence[ColumnRef],
    labels: ColumnMap | None = None,
    units: ColumnMap | None = None,
    axis_labels: ColumnMap | None = None,
    axis_names: ColumnMap | None = None,
    name: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    source_id: str | None = None,
    sep: str = ",",
    header: int | None = 0,
    skiprows: int | Sequence[int] | None = None,
    na_values: object | None = None,
    encoding: str | None = None,
    comment: str | None = None,
) -> Dataset:
    """Read one CSV file into a file-format-agnostic :class:`Dataset`."""
    source = Path(path)
    identity, source_path = _source_identity(source, source_id)
    frame = pd.read_csv(
        source,
        sep=sep,
        header=header,
        skiprows=skiprows,
        na_values=na_values,
        encoding=encoding,
        comment=comment,
    )
    series = _frame_to_series(
        frame,
        path=source,
        source_id=identity,
        source_path=source_path,
        sheet=None,
        x=x,
        y=y,
        labels=labels,
        units=units,
        axis_labels=axis_labels,
        axis_names=axis_names,
    )
    return _dataset(
        series,
        path=source,
        source_id=identity,
        source_path=source_path,
        name=name,
        sheets=(None,),
        metadata=metadata,
    )


def read_txt(
    path: str | Path,
    *,
    x: ColumnRef,
    y: ColumnRef | Sequence[ColumnRef],
    labels: ColumnMap | None = None,
    units: ColumnMap | None = None,
    axis_labels: ColumnMap | None = None,
    axis_names: ColumnMap | None = None,
    name: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    source_id: str | None = None,
    sep: str | None = None,
    header: int | None = 0,
    skiprows: int | Sequence[int] | None = None,
    na_values: object | None = None,
    encoding: str | None = None,
    comment: str | None = None,
) -> Dataset:
    """Read delimited text, using pandas delimiter sniffing when ``sep`` is omitted."""
    source = Path(path)
    identity, source_path = _source_identity(source, source_id)
    frame = pd.read_csv(
        source,
        sep=sep,
        engine="python" if sep is None else None,
        header=header,
        skiprows=skiprows,
        na_values=na_values,
        encoding=encoding,
        comment=comment,
    )
    series = _frame_to_series(
        frame,
        path=source,
        source_id=identity,
        source_path=source_path,
        sheet=None,
        x=x,
        y=y,
        labels=labels,
        units=units,
        axis_labels=axis_labels,
        axis_names=axis_names,
    )
    return _dataset(
        series,
        path=source,
        source_id=identity,
        source_path=source_path,
        name=name,
        sheets=(None,),
        metadata=metadata,
    )


def read_excel(
    path: str | Path,
    *,
    x: ColumnRef,
    y: ColumnRef | Sequence[ColumnRef],
    labels: ColumnMap | None = None,
    units: ColumnMap | None = None,
    axis_labels: ColumnMap | None = None,
    axis_names: ColumnMap | None = None,
    name: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    source_id: str | None = None,
    sheet_name: str | int | Sequence[str | int] | None = 0,
    header: int | None = 0,
    skiprows: int | Sequence[int] | None = None,
    na_values: object | None = None,
) -> Dataset:
    """Read one or several Excel sheets and combine selected curves in one Dataset."""
    source = Path(path)
    identity, source_path = _source_identity(source, source_id)
    with pd.ExcelFile(source) as workbook:
        sheets = _resolve_excel_sheets(workbook.sheet_names, sheet_name)
        all_series: list[Series] = []
        for sheet in sheets:
            frame = pd.read_excel(
                workbook,
                sheet_name=sheet,
                header=header,
                skiprows=skiprows,
                na_values=na_values,
            )
            all_series.extend(
                _frame_to_series(
                    frame,
                    path=source,
                    source_id=identity,
                    source_path=source_path,
                    sheet=sheet,
                    x=x,
                    y=y,
                    labels=labels,
                    units=units,
                    axis_labels=axis_labels,
                    axis_names=axis_names,
                )
            )

    return _dataset(
        all_series,
        path=source,
        source_id=identity,
        source_path=source_path,
        name=name,
        sheets=sheets,
        metadata=metadata,
    )


def read_tabular(path: str | Path, **kwargs: Any) -> Dataset:
    """Dispatch a supported tabular file to the corresponding reader by extension."""
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix == ".csv":
        return read_csv(source, **kwargs)
    if suffix in {".txt", ".tsv", ".dat"}:
        if suffix == ".tsv" and "sep" not in kwargs:
            kwargs["sep"] = "\t"
        return read_txt(source, **kwargs)
    if suffix in {".xlsx", ".xlsm"}:
        return read_excel(source, **kwargs)
    raise TabularReadError(
        f"Unsupported tabular extension {suffix!r}; supported: "
        ".csv, .txt, .tsv, .dat, .xlsx, .xlsm"
    )
