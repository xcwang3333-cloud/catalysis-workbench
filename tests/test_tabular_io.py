import numpy as np
import pandas as pd
import pytest

from catalysis_workbench.io import (
    TabularReadError,
    read_csv,
    read_excel,
    read_tabular,
    read_txt,
)


def test_read_csv_builds_multi_catalyst_dataset_with_units_and_keys(tmp_path):
    path = tmp_path / "lsv.csv"
    path.write_text(
        "Potential [V],Pb1-N/C,Pb3-N/C\n"
        "-0.2,-1.0,-2.0\n"
        "-0.3,-2.0,-4.0\n"
        "-0.4,-3.0,-6.0\n",
        encoding="utf-8",
    )

    dataset = read_csv(
        path,
        x="Potential [V]",
        y=["Pb1-N/C", "Pb3-N/C"],
        units={"Pb1-N/C": "mA cm^-2", "Pb3-N/C": "mA cm^-2"},
        axis_labels={"Pb1-N/C": "Current density", "Pb3-N/C": "Current density"},
        axis_names={"Pb1-N/C": "current_density", "Pb3-N/C": "current_density"},
        source_id="lsv.csv",
    )

    assert dataset.name == "lsv"
    assert dataset.labels == ("Pb1-N/C", "Pb3-N/C")
    assert dataset.keys == (
        "lsv.csv::table::c0->c1",
        "lsv.csv::table::c0->c2",
    )
    np.testing.assert_allclose(dataset[0].x, [-0.2, -0.3, -0.4])
    np.testing.assert_allclose(dataset[1].y, [-2.0, -4.0, -6.0])
    assert dataset[0].x_axis.label == "Potential"
    assert dataset[0].x_axis.unit == "V"
    assert dataset[0].y_axis.name == "current_density"
    assert dataset[0].y_axis.label == "Current density"
    assert dataset[0].y_axis.unit == "mA cm^-2"
    assert dataset[0].metadata["source"]["y_column_index"] == 1


def test_read_csv_accepts_column_positions_without_header(tmp_path):
    path = tmp_path / "numeric.csv"
    path.write_text("0,1,2\n1,3,4\n2,5,6\n", encoding="utf-8")

    dataset = read_csv(
        path,
        header=None,
        x=0,
        y=[1, 2],
        labels={1: "Catalyst A", 2: "Catalyst B"},
    )

    assert dataset.labels == ("Catalyst A", "Catalyst B")
    np.testing.assert_allclose(dataset[0].x, [0, 1, 2])
    np.testing.assert_allclose(dataset[1].y, [2, 4, 6])


def test_default_source_identity_distinguishes_same_named_files(tmp_path):
    first_path = tmp_path / "run1" / "data.csv"
    second_path = tmp_path / "run2" / "data.csv"
    first_path.parent.mkdir()
    second_path.parent.mkdir()
    first_path.write_text("x,y\n0,1\n1,2\n", encoding="utf-8")
    second_path.write_text("x,y\n0,3\n1,4\n", encoding="utf-8")

    first = read_csv(first_path, x="x", y="y")
    second = read_csv(second_path, x="x", y="y")
    combined = first.extend(second)

    assert first[0].key != second[0].key
    assert len(combined) == 2
    assert first[0].metadata["source"]["file_name"] == "data.csv"
    assert second[0].metadata["source"]["file_name"] == "data.csv"
    assert first[0].metadata["source"]["source_path"] != second[0].metadata["source"][
        "source_path"
    ]


def test_read_csv_preserves_explicit_missing_values(tmp_path):
    path = tmp_path / "missing.csv"
    path.write_text("x,y\n0,1\n1,\n2,3\n", encoding="utf-8")

    dataset = read_csv(path, x="x", y="y")

    assert dataset[0].has_missing
    assert np.isnan(dataset[0].y[1])


def test_read_csv_rejects_non_numeric_selected_data(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("x,y\n0,1\n1,bad\n", encoding="utf-8")

    with pytest.raises(TabularReadError, match="non-numeric"):
        read_csv(path, x="x", y="y")


def test_reader_rejects_duplicate_y_column_selection(tmp_path):
    path = tmp_path / "duplicate_y.csv"
    path.write_text("x,y\n0,1\n1,2\n", encoding="utf-8")

    with pytest.raises(TabularReadError, match="selected more than once"):
        read_csv(path, x="x", y=["y", 1])


def test_reader_rejects_empty_source_id_override(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("x,y\n0,1\n1,2\n", encoding="utf-8")

    with pytest.raises(TabularReadError, match="source_id"):
        read_csv(path, x="x", y="y", source_id="   ")


def test_read_txt_can_sniff_tab_delimiter(tmp_path):
    path = tmp_path / "raman.txt"
    path.write_text(
        "Shift [cm^-1]\tSample A\tSample B\n"
        "100\t1.0\t2.0\n"
        "200\t1.5\t2.5\n",
        encoding="utf-8",
    )

    dataset = read_txt(path, x="Shift [cm^-1]", y=["Sample A", "Sample B"])

    assert len(dataset) == 2
    assert dataset[0].x_axis.label == "Shift"
    assert dataset[0].x_axis.unit == "cm^-1"
    np.testing.assert_allclose(dataset[1].y, [2.0, 2.5])


def test_read_tabular_dispatches_tsv(tmp_path):
    path = tmp_path / "xrd.tsv"
    path.write_text("2theta\tA\n20\t100\n30\t200\n", encoding="utf-8")

    dataset = read_tabular(path, x="2theta", y="A", source_id="xrd.tsv")

    assert dataset[0].key == "xrd.tsv::table::c0->c1"
    np.testing.assert_allclose(dataset[0].y, [100, 200])


def test_read_excel_all_sheets_uses_canonical_sheet_names_and_duplicate_labels(tmp_path):
    path = tmp_path / "replicates.xlsx"
    first = pd.DataFrame({"Potential [V]": [0.0, 0.1], "Signal [a.u.]": [1.0, 2.0]})
    second = pd.DataFrame({"Potential [V]": [0.0, 0.1], "Signal [a.u.]": [1.1, 2.1]})
    with pd.ExcelWriter(path) as writer:
        first.to_excel(writer, sheet_name="Replicate 1", index=False)
        second.to_excel(writer, sheet_name="Replicate 2", index=False)

    dataset = read_excel(
        path,
        sheet_name=None,
        x="Potential [V]",
        y="Signal [a.u.]",
        labels={"Signal [a.u.]": "Pb3-N/C"},
        source_id="replicates.xlsx",
    )

    assert dataset.labels == ("Pb3-N/C", "Pb3-N/C")
    assert dataset.keys == (
        "replicates.xlsx::Replicate 1::c0->c1",
        "replicates.xlsx::Replicate 2::c0->c1",
    )
    assert dataset.metadata["source"]["sheets"] == ("Replicate 1", "Replicate 2")
    assert dataset.by_key("replicates.xlsx::Replicate 2::c0->c1").label == "Pb3-N/C"


def test_read_excel_integer_sheet_selection_resolves_to_sheet_name(tmp_path):
    path = tmp_path / "two_sheets.xlsx"
    frame = pd.DataFrame({"x": [0, 1], "y": [2, 3]})
    with pd.ExcelWriter(path) as writer:
        frame.to_excel(writer, sheet_name="First", index=False)
        frame.to_excel(writer, sheet_name="Second", index=False)

    dataset = read_excel(
        path,
        sheet_name=1,
        x="x",
        y="y",
        source_id="two_sheets.xlsx",
    )

    assert dataset.keys == ("two_sheets.xlsx::Second::c0->c1",)
    assert dataset.metadata["source"]["sheets"] == ("Second",)


def test_read_excel_rejects_empty_sheet_selection(tmp_path):
    path = tmp_path / "data.xlsx"
    pd.DataFrame({"x": [0, 1], "y": [2, 3]}).to_excel(path, index=False)

    with pytest.raises(TabularReadError, match="At least one Excel sheet"):
        read_excel(path, sheet_name=[], x="x", y="y")


def test_reader_reports_missing_column(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("x,y\n0,1\n", encoding="utf-8")

    with pytest.raises(TabularReadError, match="was not found"):
        read_csv(path, x="potential", y="y")


def test_reader_rejects_same_x_and_y_column(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("x,y\n0,1\n1,2\n", encoding="utf-8")

    with pytest.raises(TabularReadError, match="different columns"):
        read_csv(path, x="x", y="x")


def test_reader_preserves_dataset_metadata(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("x,y\n0,1\n1,2\n", encoding="utf-8")

    dataset = read_csv(
        path,
        x="x",
        y="y",
        name="Comparison",
        metadata={"technique": "generic", "note": "raw export"},
        source_id="project/data.csv",
    )

    assert dataset.name == "Comparison"
    assert dataset.metadata["technique"] == "generic"
    assert dataset.metadata["note"] == "raw export"
    assert dataset.metadata["source"]["file_name"] == "data.csv"
    assert dataset.metadata["source"]["source_id"] == "project/data.csv"
    assert dataset.metadata["source"]["source_path"] == path.resolve().as_posix()


def test_read_tabular_rejects_unsupported_extension(tmp_path):
    path = tmp_path / "data.xyz"
    path.write_text("x y\n0 1\n", encoding="utf-8")

    with pytest.raises(TabularReadError, match="Unsupported"):
        read_tabular(path, x="x", y="y")
