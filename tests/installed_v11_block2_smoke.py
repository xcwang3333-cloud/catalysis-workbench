"""Fresh-wheel smoke for v1.1 data intake and deterministic raw-source persistence."""

from __future__ import annotations

import tempfile
from pathlib import Path

from catalysis_workbench.application import (
    AnalysisSession,
    DataSeriesSpec,
    TabularMappingSpec,
    source_spec_from_file,
)


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        source = root / "Pb3.csv"
        source.write_text("Potential,Current\n0,1\n1,2\n", encoding="utf-8")
        spec = DataSeriesSpec(
            source=source_spec_from_file(source),
            mapping=TabularMappingSpec(
                delimiter=",",
                x_column=0,
                y_column=1,
                x_role="potential",
                y_role="current",
                x_unit="V",
                y_unit="mA",
                x_reference="RHE",
            ),
            display_name="Pb₃-N/C",
        )
        session = AnalysisSession()
        session.new_analysis("lsv")
        session.add_data_series(spec, source)
        project = root / "project"
        session.save_project_as(project)
        source.unlink()
        materialized = session.materialize_data(spec.data_id)
        assert tuple(materialized.value.y) == (1.0, 2.0)
        assert materialized.input_sha256 == spec.input_sha256

    print("installed v1.1 Block-2 data intake smoke: ok")


if __name__ == "__main__":
    main()
