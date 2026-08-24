"""Minimal explicit ICP composition mass-balance -> replicate summary -> plot example."""

from pathlib import Path

from catalysis_workbench.experimental.characterization import (
    CompositionMeasurement,
    CompositionTable,
    plot_composition,
    solution_concentration_to_bulk_mass_fraction,
    summarize_composition_replicates,
)
from catalysis_workbench.visualization import export_figure, get_preset

HERE = Path(__file__).resolve().parent


def main(output_dir: Path | None = None) -> None:
    output = HERE / "output" if output_dir is None else Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    measured_solution = CompositionMeasurement(
        key="sample-a-pb-solution",
        sample_key="sample-a",
        sample_label="Sample A",
        element="Pb",
        analyte="208Pb",
        value=10.0,
        unit="mg/L",
        basis="solution_concentration",
    )
    bulk_pb = solution_concentration_to_bulk_mass_fraction(
        measured_solution,
        sample_mass=50.0,
        sample_mass_unit="mg",
        final_digest_volume=25.0,
        final_digest_volume_unit="mL",
        dilution_factor=2.0,
        target_unit="wt%",
    )
    print(f"Explicit mass-balance Pb loading = {bulk_pb.value:.3f} {bulk_pb.unit}")

    replicates = CompositionTable(
        (
            CompositionMeasurement(
                key="a-pb-1",
                sample_key="sample-a",
                sample_label="Sample A",
                element="Pb",
                analyte="208Pb",
                replicate_key="1",
                value=0.92,
                unit="wt%",
                basis="bulk_mass_fraction",
            ),
            CompositionMeasurement(
                key="a-pb-2",
                sample_key="sample-a",
                sample_label="Sample A",
                element="Pb",
                analyte="208Pb",
                replicate_key="2",
                value=0.96,
                unit="wt%",
                basis="bulk_mass_fraction",
            ),
            CompositionMeasurement(
                key="b-pb-1",
                sample_key="sample-b",
                sample_label="Sample B",
                element="Pb",
                analyte="208Pb",
                replicate_key="1",
                value=1.58,
                unit="wt%",
                basis="bulk_mass_fraction",
            ),
            CompositionMeasurement(
                key="b-pb-2",
                sample_key="sample-b",
                sample_label="Sample B",
                element="Pb",
                analyte="208Pb",
                replicate_key="2",
                value=1.64,
                unit="wt%",
                basis="bulk_mass_fraction",
            ),
        ),
        name="Synthetic ICP composition",
    )
    summaries = summarize_composition_replicates(replicates)
    for item in summaries:
        print(
            f"{item.sample_label}: {item.mean:.3f} {item.unit}; "
            f"SD={item.standard_deviation:.3f}; n={item.n}"
        )

    spec = get_preset("publication").with_export(dpi=300)
    fig, _ = plot_composition(summaries, spec, error="sd")
    for suffix in ("png", "svg", "pdf"):
        export_figure(fig, output / f"composition_example.{suffix}", spec=spec)


if __name__ == "__main__":
    main()
