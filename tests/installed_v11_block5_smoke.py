"""Fresh-wheel headless smoke for v1.1 Block-5 Figure Package export."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from catalysis_workbench.application import (
    AnalysisSession,
    DataSeriesSpec,
    FigurePackageOptions,
    TabularMappingSpec,
    export_session_figure_package,
    source_spec_from_file,
)


def _mapped(path: Path, *, name: str) -> DataSeriesSpec:
    return DataSeriesSpec(
        source=source_spec_from_file(path),
        mapping=TabularMappingSpec(
            delimiter=",",
            x_column=0,
            y_column=1,
            x_role="potential",
            y_role="signal",
            x_unit="V",
            y_unit="a.u.",
            x_reference="RHE",
        ),
        display_name=name,
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        first_path = base / "first.csv"
        second_path = base / "second.csv"
        first_path.write_text("x,y\n0,1\n1,2\n2,3\n", encoding="utf-8")
        second_path.write_text("x,y\n0,3\n1,2\n2,1\n", encoding="utf-8")
        first = _mapped(first_path, name="Pb1")
        second = _mapped(second_path, name="Pb2")

        session = AnalysisSession()
        session.new_analysis("generic_xy")
        session.add_data_series_batch(((first, first_path), (second, second_path)))
        session.create_figure("processed")
        draft = session.figure_draft("processed")
        session.replace_figure_spec(
            "processed",
            draft.figure_spec.updated(xlim=(0.5, 1.5)).with_series_style(
                second.data_id,
                visible=False,
            ),
        )
        project = base / "project"
        session.save_project_as(project)
        before = session.state
        assert before.document is not None
        before_document_sha = before.document.document_sha256

        package = base / "figure-package"
        result = export_session_figure_package(
            session,
            "processed",
            package,
            options=FigurePackageOptions(
                figure_formats=("svg",),
                source_data_formats=("txt",),
            ),
        )

        after = session.state
        assert after.document is before.document
        assert after.document.document_sha256 == before_document_sha
        assert after.revision == before.revision
        assert after.is_dirty is False
        assert after.workspace_manifest_sha256 == result.workspace_manifest_sha256
        assert after.workspace_manifest_sha256 != before.workspace_manifest_sha256
        assert (package / "figure.svg").is_file()
        assert (package / "manifest.json").is_file()
        assert (package / "source-data" / "trace-001.txt").is_file()
        assert not (package / "source-data" / "trace-002.txt").exists()

        manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["package_sha256"] == result.package_sha256
        assert manifest["trace_order"] == [first.data_id]
        assert str(base.resolve()) not in json.dumps(manifest, sort_keys=True)

        rows = [
            line
            for line in (package / "source-data" / "trace-001.txt")
            .read_text(encoding="utf-8")
            .splitlines()
            if not line.startswith("#")
        ]
        assert rows[0] == "x\ty\tx_missing\ty_missing"
        assert rows[1:] == [
            "0\t1\t0\t0",
            "1\t2\t0\t0",
            "2\t3\t0\t0",
        ]

        reopened = AnalysisSession()
        reopened.open_project(project)
        assert reopened.state.workspace_manifest_sha256 == result.workspace_manifest_sha256
        assert reopened.figure_is_stale("processed") is False

    print("installed v1.1 Block-5 smoke: ok")


if __name__ == "__main__":
    main()
