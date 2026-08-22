"""Minimal XRD import -> process -> plot -> export example."""

from pathlib import Path

from catalysis_workbench.experimental.characterization import (
    PeakAnnotation,
    XRDProcessingConfig,
    plot_xrd,
    process_xrd,
)
from catalysis_workbench.io import read_csv
from catalysis_workbench.visualization import export_figure, get_preset

HERE = Path(__file__).resolve().parent


def main(output_dir: Path | None = None) -> None:
    output = HERE / "output" if output_dir is None else Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    dataset = read_csv(
        HERE / "data" / "xrd_example.csv",
        x="2theta [deg]",
        y="Intensity [counts]",
        source_id="example-xrd",
    )
    processed = process_xrd(
        dataset[0],
        XRDProcessingConfig(x_min_deg=20, x_max_deg=80, normalization="max"),
    )

    spec = get_preset("publication").with_export(dpi=300)
    fig, _ = plot_xrd(
        processed,
        spec,
        peak_annotations=(PeakAnnotation(35.0, "peak"),),
    )
    for suffix in ("png", "svg", "pdf"):
        export_figure(fig, output / f"xrd_example.{suffix}", spec=spec)


if __name__ == "__main__":
    main()
