"""Minimal Raman import -> process -> plot -> export example."""

from pathlib import Path

from catalysis_workbench.experimental.characterization import (
    RamanBand,
    RamanPeakAnnotation,
    RamanProcessingConfig,
    id_ig_ratio,
    plot_raman,
    process_raman,
)
from catalysis_workbench.io import read_csv
from catalysis_workbench.visualization import export_figure, get_preset

HERE = Path(__file__).resolve().parent


def main(output_dir: Path | None = None) -> None:
    output = HERE / "output" if output_dir is None else Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    dataset = read_csv(
        HERE / "data" / "raman_example.csv",
        x="Raman shift [cm^-1]",
        y="Intensity [counts]",
        source_id="example-raman",
    )
    processed = process_raman(
        dataset[0],
        RamanProcessingConfig(
            shift_min_cm1=1000,
            shift_max_cm1=1800,
            normalization="max",
        ),
    )

    ratio = id_ig_ratio(
        processed,
        RamanBand(1250, 1450, "D"),
        RamanBand(1550, 1650, "G"),
        metric="height",
    )
    print(f"I_D/I_G = {ratio.value:.3f}")

    spec = get_preset("publication").with_export(dpi=300)
    fig, _ = plot_raman(
        processed,
        spec,
        peak_annotations=(
            RamanPeakAnnotation(1400, "D"),
            RamanPeakAnnotation(1600, "G"),
        ),
    )
    for suffix in ("png", "svg", "pdf"):
        export_figure(fig, output / f"raman_example.{suffix}", spec=spec)


if __name__ == "__main__":
    main()
