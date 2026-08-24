"""Minimal explicit gas-sorption branch preparation -> plotting -> export example."""

from pathlib import Path

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.experimental.characterization import (
    SorptionCondition,
    SorptionWindow,
    plot_sorption,
    prepare_sorption_series,
    summarize_sorption_window,
)
from catalysis_workbench.visualization import export_figure, get_preset

HERE = Path(__file__).resolve().parent


def main(output_dir: Path | None = None) -> None:
    output = HERE / "output" if output_dir is None else Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    adsorption = prepare_sorption_series(
        Series(
            x=(0.01, 0.05, 0.10, 0.30, 0.60, 0.90, 0.99),
            y=(0.20, 0.45, 0.70, 1.40, 2.80, 4.80, 5.60),
            label="Sample A",
            key="sample-a-ads",
            x_axis=Axis("relative_pressure", unit="1"),
            y_axis=Axis("adsorbed_quantity", unit="mmol/g"),
        ),
        SorptionCondition("N2", 77.0, "adsorption"),
    )
    desorption = prepare_sorption_series(
        Series(
            x=(0.99, 0.90, 0.60, 0.30, 0.10, 0.05, 0.01),
            y=(5.65, 5.05, 3.20, 1.65, 0.76, 0.48, 0.21),
            label="Sample A",
            key="sample-a-des",
            x_axis=Axis("relative_pressure", unit="1"),
            y_axis=Axis("adsorbed_quantity", unit="mmol/g"),
        ),
        SorptionCondition("N2", 77.0, "desorption"),
    )

    summary = summarize_sorption_window(
        adsorption,
        SorptionWindow(0.10, 0.60, "middle-pressure measured points"),
    )
    print(
        f"Measured points in window: {summary.n_measured_points}; "
        f"loading range = {summary.minimum_loading:.2f}–{summary.maximum_loading:.2f} "
        f"{summary.loading_unit}"
    )

    dataset = Dataset(series=(adsorption, desorption), name="Synthetic N2 isotherm")
    spec = get_preset("publication").with_export(dpi=300)
    fig, _ = plot_sorption(dataset, spec, branch="all")
    for suffix in ("png", "svg", "pdf"):
        export_figure(fig, output / f"sorption_example.{suffix}", spec=spec)


if __name__ == "__main__":
    main()
