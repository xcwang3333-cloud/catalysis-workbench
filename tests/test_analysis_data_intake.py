from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
import pytest

from catalysis_workbench.application import (
    AnalysisMaterializationError,
    DataSeriesSpec,
    TabularMappingSpec,
    materialize_data_series,
    source_spec_from_file,
)
from catalysis_workbench.io import inspect_tabular


def _csv(tmp_path: Path, name: str = "Pb₃-LSV.csv") -> Path:
    path = tmp_path / name
    path.write_text(
        "Potential [V],Current density [mA cm^-2],FECO [%]\n"
        "-0.20,-1.0,20\n"
        "-0.30,-2.0,40\n"
        "-0.40,-3.0,60\n",
        encoding="utf-8",
    )
    return path


def _mapping(**changes: object) -> TabularMappingSpec:
    values: dict[str, object] = {
        "delimiter": ",",
        "x_column": 0,
        "y_column": 1,
        "x_role": "potential",
        "y_role": "current_density",
        "x_unit": "V",
        "y_unit": "mA cm^-2",
        "x_reference": "RHE",
    }
    values.update(changes)
    return TabularMappingSpec(**values)


def test_scientific_input_identity_is_path_independent_and_display_name_independent(
    tmp_path: Path,
) -> None:
    first_path = _csv(tmp_path)
    second_path = tmp_path / "renamed.csv"
    shutil.copyfile(first_path, second_path)

    first = DataSeriesSpec(
        source=source_spec_from_file(first_path),
        mapping=_mapping(),
        display_name="Pb₃-N/C",
    )
    moved = DataSeriesSpec(
        source=source_spec_from_file(second_path),
        mapping=_mapping(),
        display_name="renamed display",
    )

    assert first.source.content_sha256 == moved.source.content_sha256
    assert first.mapping.mapping_sha256 == moved.mapping.mapping_sha256
    assert first.input_sha256 == moved.input_sha256
    assert first.data_id == moved.data_id


def test_mapping_columns_units_and_reference_change_input_identity(tmp_path: Path) -> None:
    path = _csv(tmp_path)
    source = source_spec_from_file(path)
    baseline = DataSeriesSpec(source=source, mapping=_mapping(), display_name="baseline")
    changed_column = DataSeriesSpec(
        source=source,
        mapping=_mapping(y_column=2, y_role="faradaic_efficiency", y_unit="%"),
        display_name="column",
    )
    changed_unit = DataSeriesSpec(
        source=source,
        mapping=_mapping(y_unit="A cm^-2"),
        display_name="unit",
    )
    changed_reference = DataSeriesSpec(
        source=source,
        mapping=_mapping(x_reference="Ag/AgCl"),
        display_name="reference",
    )

    assert len(
        {
            baseline.input_sha256,
            changed_column.input_sha256,
            changed_unit.input_sha256,
            changed_reference.input_sha256,
        }
    ) == 4


def test_preview_is_bounded_and_freezes_auto_delimiter(tmp_path: Path) -> None:
    path = tmp_path / "preview.txt"
    path.write_text("Potential [V]\tCurrent [mA]\n0\t1\n1\t2\n2\t3\n", encoding="utf-8")

    preview = inspect_tabular(path, max_rows=2)

    assert preview.resolved_delimiter == "\t"
    assert preview.truncated is True
    assert len(preview.rows) == 2
    assert tuple(column.index for column in preview.columns) == (0, 1)
    assert tuple(column.name for column in preview.columns) == ("Potential", "Current")
    assert tuple(column.inferred_unit for column in preview.columns) == ("V", "mA")


def test_excel_preview_exposes_sheets_without_persisting_an_implicit_choice(
    tmp_path: Path,
) -> None:
    path = tmp_path / "book.xlsx"
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({"x": [1, 2], "y": [3, 4]}).to_excel(
            writer, sheet_name="LSV", index=False
        )
        pd.DataFrame({"x": [5], "y": [6]}).to_excel(
            writer, sheet_name="FE", index=False
        )

    preview = inspect_tabular(path, sheet="FE")

    assert preview.available_sheets == ("LSV", "FE")
    assert preview.selected_sheet == "FE"
    assert preview.resolved_delimiter is None
    assert preview.rows == (("5", "6"),)


def test_materialization_uses_explicit_semantics_and_contains_no_operational_path(
    tmp_path: Path,
) -> None:
    path = _csv(tmp_path)
    spec = DataSeriesSpec(
        source=source_spec_from_file(path),
        mapping=_mapping(),
        display_name="Pb₃-N/C",
    )

    materialized = materialize_data_series(spec, path)

    assert materialized.input_sha256 == spec.input_sha256
    assert materialized.value.label == "Pb₃-N/C"
    assert materialized.value.x_axis.name == "potential"
    assert materialized.value.x_axis.unit == "V"
    assert materialized.value.x_axis.metadata["reference"] == "RHE"
    assert materialized.value.y_axis.name == "current_density"
    assert materialized.value.y_axis.unit == "mA cm^-2"
    assert set(materialized.value.metadata) == {"analysis_input"}
    assert str(tmp_path) not in repr(materialized.value.metadata)


def test_materialization_refuses_changed_bytes_and_non_numeric_mapping(tmp_path: Path) -> None:
    path = _csv(tmp_path)
    source = source_spec_from_file(path)
    spec = DataSeriesSpec(source=source, mapping=_mapping(), display_name="Pb₃-N/C")
    path.write_text("Potential,Current\n0,bad\n", encoding="utf-8")

    with pytest.raises(AnalysisMaterializationError, match="changed since mapping"):
        materialize_data_series(spec, path)

    bad = tmp_path / "bad.csv"
    bad.write_text("Potential,Current\n0,bad\n1,worse\n", encoding="utf-8")
    bad_spec = DataSeriesSpec(
        source=source_spec_from_file(bad),
        mapping=_mapping(x_unit=None, y_unit=None, x_reference=None),
        display_name="bad",
    )
    with pytest.raises(AnalysisMaterializationError, match="non-numeric"):
        materialize_data_series(bad_spec, bad)
