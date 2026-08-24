"""Smoke the reviewed composition public API from an installed wheel."""

from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from catalysis_workbench.experimental.characterization import (
    CompositionMeasurement,
    CompositionTable,
    convert_composition_unit,
    plot_composition,
    solution_concentration_to_bulk_mass_fraction,
    summarize_composition_replicates,
)
from catalysis_workbench.visualization import export_figure, get_preset


def main() -> None:
    solution = CompositionMeasurement(
        key="installed-solution",
        sample_key="sample-a",
        element="Pb",
        analyte="208Pb",
        value=10.0,
        unit="mg/L",
        basis="solution_concentration",
    )
    bulk = solution_concentration_to_bulk_mass_fraction(
        solution,
        sample_mass=50.0,
        sample_mass_unit="mg",
        final_digest_volume=25.0,
        final_digest_volume_unit="mL",
        dilution_factor=2.0,
        target_unit="wt%",
    )
    assert bulk.value == 1.0
    assert bulk.basis == "bulk_mass_fraction"
    assert convert_composition_unit(bulk, target_unit="mg/g").value == 10.0

    raw = CompositionTable(
        (
            CompositionMeasurement(
                key="a-pb-1",
                sample_key="a",
                sample_label="A",
                element="Pb",
                analyte="208Pb",
                replicate_key="1",
                value=0.9,
                unit="wt%",
                basis="bulk_mass_fraction",
            ),
            CompositionMeasurement(
                key="a-pb-2",
                sample_key="a",
                sample_label="A",
                element="Pb",
                analyte="208Pb",
                replicate_key="2",
                value=1.1,
                unit="wt%",
                basis="bulk_mass_fraction",
            ),
            CompositionMeasurement(
                key="b-pb-1",
                sample_key="b",
                sample_label="B",
                element="Pb",
                analyte="208Pb",
                replicate_key="1",
                value=1.4,
                unit="wt%",
                basis="bulk_mass_fraction",
            ),
            CompositionMeasurement(
                key="b-pb-2",
                sample_key="b",
                sample_label="B",
                element="Pb",
                analyte="208Pb",
                replicate_key="2",
                value=1.6,
                unit="wt%",
                basis="bulk_mass_fraction",
            ),
        )
    )
    summaries = summarize_composition_replicates(raw)
    np.testing.assert_allclose([item.mean for item in summaries], (1.0, 1.5))
    np.testing.assert_allclose(
        [item.standard_deviation for item in summaries],
        (np.sqrt(0.02), np.sqrt(0.02)),
    )

    spec = get_preset("publication").with_export(dpi=120)
    fig, ax = plot_composition(summaries, spec, error="sd")
    assert len(ax.patches) == 2
    with TemporaryDirectory() as directory:
        path = export_figure(fig, Path(directory) / "composition.png", spec=spec)
        assert path.is_file() and path.stat().st_size > 0


if __name__ == "__main__":
    main()
