from __future__ import annotations

from catalysis_workbench import computation


def main() -> None:
    assert issubclass(computation.CorrelationError, ValueError)
    point = computation.CorrelationPoint(
        key="pair:1",
        x_value=2.1,
        y_value=-1.5,
        x_source_key="geometry:pair:1",
        x_source_digest="geometry-digest",
        y_source_key="bonding:pair:1",
        y_source_digest="bonding-digest",
        mapping_key="manual-map:1",
        mapping_provenance="caller-reviewed identity",
        metadata={"kind": "installed-smoke"},
    )
    dataset = computation.build_correlation_dataset(
        (point,),
        x_definition="bond length",
        x_unit="angstrom",
        y_definition="bond descriptor",
        y_unit="eV",
        provenance_id="installed-manual-map",
    )
    frame = computation.correlation_points_frame(dataset)
    assert frame.loc[0, "x_value"] == 2.1
    assert frame.loc[0, "y_value"] == -1.5

    summary = computation.ICOHPBondSummary(
        bond_key="bond:1",
        source_label="1",
        bond_length_angstrom=2.0,
        number_of_bonds=2,
        icohp_by_spin={"up": -1.0, "down": -0.5},
    )
    source = computation.ICOHPResult(bonds=(summary,))
    correlated = computation.icohp_length_correlation(
        source,
        spins=("up", "down"),
        provenance_id="installed-explicit-spin-sum",
    )
    assert correlated.points[0].x_value == 2.0
    assert correlated.points[0].y_value == -1.5
    assert correlated.points[0].metadata["number_of_bonds"] == "2"
    print("installed v0.6 explicit geometry-bonding correlation smoke: ok")


if __name__ == "__main__":
    main()
