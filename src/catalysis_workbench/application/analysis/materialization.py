"""Deterministic materialization of mapped analysis inputs into core Series objects."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.io.tabular import TabularReadError, read_tabular

from .data import DataSeriesSpec, source_spec_from_file


class AnalysisMaterializationError(ValueError):
    """Raised when exact raw bytes cannot satisfy a persisted analysis mapping."""


@dataclass(frozen=True, slots=True)
class MaterializedInput:
    """One path-independent scientific input plus its exact identity chain."""

    value: Series
    data_id: str
    source_sha256: str
    mapping_sha256: str
    input_sha256: str


def verify_source_bytes(spec: DataSeriesSpec, path: str | Path) -> Path:
    """Verify that ``path`` still contains the raw bytes described by ``spec``."""

    if not isinstance(spec, DataSeriesSpec):
        raise TypeError("spec must be a DataSeriesSpec")
    source = Path(path)
    observed = source_spec_from_file(source)
    if observed.content_sha256 != spec.source.content_sha256:
        raise AnalysisMaterializationError(
            f"source file changed since mapping; expected {spec.source.content_sha256}, "
            f"observed {observed.content_sha256}"
        )
    if observed.size_bytes != spec.source.size_bytes:
        raise AnalysisMaterializationError(
            f"source file size changed since mapping; expected {spec.source.size_bytes}, "
            f"observed {observed.size_bytes}"
        )
    return source


def _reader_kwargs(spec: DataSeriesSpec) -> dict[str, object]:
    mapping = spec.mapping
    kwargs: dict[str, object] = {
        "x": mapping.x_column,
        "y": mapping.y_column,
        "source_id": f"source-{spec.source.content_sha256}",
        "header": mapping.header,
        "skiprows": mapping.skip_rows,
    }
    if spec.source.source_format == "excel":
        kwargs["sheet_name"] = mapping.sheet
    else:
        kwargs["sep"] = mapping.delimiter
        kwargs["encoding"] = mapping.encoding
    return kwargs


def materialize_data_series(spec: DataSeriesSpec, path: str | Path) -> MaterializedInput:
    """Load one mapped input while excluding operational file paths from its Series metadata."""

    source = verify_source_bytes(spec, path)
    try:
        dataset = read_tabular(source, **_reader_kwargs(spec))
    except (TabularReadError, OSError, ValueError, TypeError) as exc:
        raise AnalysisMaterializationError(
            f"cannot materialize mapped input {spec.display_name!r}: {exc}"
        ) from exc
    if len(dataset.series) != 1:
        raise AnalysisMaterializationError(
            "one DataSeriesSpec must materialize exactly one scientific Series"
        )
    loaded = dataset.series[0]
    mapping = spec.mapping
    x_metadata: dict[str, object] = {"source_column": str(mapping.x_column)}
    if mapping.x_reference is not None:
        x_metadata["reference"] = mapping.x_reference
    y_metadata: dict[str, object] = {"source_column": str(mapping.y_column)}
    value = Series(
        x=loaded.x,
        y=loaded.y,
        label=spec.display_name,
        key=spec.data_id,
        x_axis=Axis(
            name=mapping.x_role,
            label=mapping.x_role,
            unit=mapping.x_unit,
            metadata=x_metadata,
        ),
        y_axis=Axis(
            name=mapping.y_role,
            label=mapping.y_role,
            unit=mapping.y_unit,
            metadata=y_metadata,
        ),
        metadata={
            "analysis_input": {
                "data_id": spec.data_id,
                "source_sha256": spec.source.content_sha256,
                "mapping_sha256": mapping.mapping_sha256,
                "input_sha256": spec.input_sha256,
                "original_name": spec.source.original_name,
            }
        },
    )
    return MaterializedInput(
        value=value,
        data_id=spec.data_id,
        source_sha256=spec.source.content_sha256,
        mapping_sha256=mapping.mapping_sha256,
        input_sha256=spec.input_sha256,
    )


__all__ = [
    "AnalysisMaterializationError",
    "MaterializedInput",
    "materialize_data_series",
    "verify_source_bytes",
]
