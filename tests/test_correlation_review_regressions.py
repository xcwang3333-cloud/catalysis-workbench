from __future__ import annotations

from catalysis_workbench.computation import (
    ICOHPBondSummary,
    ICOHPResult,
    icohp_length_correlation,
)


def test_reversed_explicit_spin_set_has_same_scientific_state() -> None:
    source = ICOHPResult(
        bonds=(
            ICOHPBondSummary(
                bond_key="bond:1",
                source_label="1",
                bond_length_angstrom=2.1,
                number_of_bonds=2,
                icohp_by_spin={"up": -1.2, "down": -0.8},
            ),
        )
    )
    forward = icohp_length_correlation(
        source,
        spins=("up", "down"),
        provenance_id="explicit-spin-set-v1",
    )
    reversed_order = icohp_length_correlation(
        source,
        spins=("down", "up"),
        provenance_id="explicit-spin-set-v1",
    )

    assert forward.digest == reversed_order.digest
    assert forward.points[0].digest == reversed_order.points[0].digest
    assert forward.points[0].y_source_digest == reversed_order.points[0].y_source_digest
    assert forward.points[0].y_source_key == reversed_order.points[0].y_source_key
    assert forward.points[0].metadata["contributing_spins"] == "up,down"
