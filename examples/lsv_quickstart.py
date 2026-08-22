"""Minimal LSV import -> process -> plot -> export example."""

from pathlib import Path

from catalysis_workbench.experimental.echem import LSVProcessingConfig, plot_lsv, process_lsv
from catalysis_workbench.io import read_csv
from catalysis_workbench.visualization import export_figure, get_preset

HERE = Path(__file__).resolve().parent


def main(output_dir: Path | None = None) -> None:
    output = HERE / "output" if output_dir is None else Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    dataset = read_csv(
        HERE / "data" / "lsv_example.csv",
        x="Potential [V]",
        y="Current [mA]",
        source_id="example-lsv",
    )
    processed = process_lsv(
        dataset[0],
        LSVProcessingConfig(
            rhe_offset_v=0.210,
            source_reference="Ag/AgCl",
            resistance_ohm=5.0,
            electrode_area_cm2=0.196,
            normalize_to_current_density=True,
        ),
    )

    spec = get_preset("publication").with_export(dpi=300)
    fig, _ = plot_lsv(processed, spec)
    for suffix in ("png", "svg", "pdf"):
        export_figure(fig, output / f"lsv_example.{suffix}", spec=spec)


if __name__ == "__main__":
    main()
