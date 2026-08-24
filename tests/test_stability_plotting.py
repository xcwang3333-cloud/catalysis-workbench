"""Publication-adapter regressions for electrochemical stability."""

from __future__ import annotations

import pytest

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.experimental.echem import (
    StabilityAnalysisConfig,
    StabilityError,
    StabilityWindowSpec,
    analyze_stability,
    analyze_stability_dataset,
    plot_stability,
    plot_stability_summary,
)
from catalysis_workbench.visualization import VisualizationError


def _series(
    key: str,
    values=(10.0, 9.5, 9.0, 8.5, 8.0),
    *,
    label: str | None = None,
    reference: str | None = None,
    normalization: str = "geometric_area",
    unit: str = "mA/cm^2",
) -> Series:
    metadata = {"normalization": normalization}
    if reference is not None:
        metadata["reference"] = reference
    return Series(
        x=(0, 1, 2, 3, 4),
        y=values,
        key=key,
        label=label or key,
        x_axis=Axis("time", unit="h"),
        y_axis=Axis("current_density", unit=unit, metadata=metadata),
    )


def _config(mode: str = "signed") -> StabilityAnalysisConfig:
    return StabilityAnalysisConfig(
        analysis_window=StabilityWindowSpec(0, 4, "h"),
        baseline_window=StabilityWindowSpec(0, 1, "h"),
        final_window=StabilityWindowSpec(3, 4, "h"),
        retention_mode=mode,  # type: ignore[arg-type]
    )


def test_plot_stability_reuses_shared_curve_renderer():
    data = Dataset([_series("a"), _series("b")])
    fig, ax = plot_stability(data)
    assert fig is ax.figure
    assert len(ax.lines) == 2
    assert "h" in ax.get_xlabel()
    assert "mA/cm" in ax.get_ylabel()


def test_plot_stability_inherits_normalization_compatibility_guard():
    data = Dataset(
        [
            _series("a", normalization="geometric_area"),
            _series("b", normalization="ecsa"),
        ]
    )
    with pytest.raises(VisualizationError, match="normalization"):
        plot_stability(data)


def test_plot_stability_inherits_reference_compatibility_guard_for_potential():
    def potential(key: str, reference: str) -> Series:
        return Series(
            x=(0, 1, 2),
            y=(0.5, 0.51, 0.52),
            key=key,
            x_axis=Axis("time", unit="h"),
            y_axis=Axis("potential", unit="V", metadata={"reference": reference}),
        )

    with pytest.raises(VisualizationError, match="reference"):
        plot_stability(Dataset([potential("rhe", "RHE"), potential("she", "SHE")]))


def test_summary_bars_use_stable_keys_and_display_labels():
    a = _series("cat-a", label="Catalyst A")
    b = _series("cat-b", label="Catalyst B")
    results = analyze_stability_dataset(
        Dataset([a, b]),
        {"cat-a": _config(), "cat-b": _config()},
    )
    fig, ax = plot_stability_summary(results, metric="retention_percent")
    assert fig is ax.figure
    labels = [tick.get_text() for tick in ax.get_xticklabels()]
    assert labels == ["Catalyst A", "Catalyst B"]
    assert "%" in ax.get_ylabel()
    assert len(ax.patches) == 2


def test_summary_absolute_change_preserves_source_unit():
    results = analyze_stability_dataset(
        Dataset([_series("a"), _series("b")]),
        {"a": _config(), "b": _config()},
    )
    _, ax = plot_stability_summary(results, metric="absolute_change")
    assert "mA/cm" in ax.get_ylabel()


def test_summary_drift_uses_y_per_second_unit():
    result = analyze_stability(_series("a"), _config())
    _, ax = plot_stability_summary([result], metric="drift_slope_per_s")
    assert "/s" in ax.get_ylabel()


def test_retention_summary_requires_matching_retention_modes():
    a = analyze_stability(_series("a"), _config("signed"))
    b = analyze_stability(_series("b"), _config("magnitude"))
    with pytest.raises(StabilityError, match="matching signed/magnitude"):
        plot_stability_summary([a, b], metric="retention_percent")


def test_summary_rejects_incompatible_y_semantics():
    current_density = analyze_stability(_series("a"), _config())
    potential_series = Series(
        x=(0, 1, 2, 3, 4),
        y=(0.5, 0.51, 0.52, 0.53, 0.54),
        key="p",
        x_axis=Axis("time", unit="h"),
        y_axis=Axis("potential", unit="V", metadata={"reference": "RHE"}),
    )
    potential = analyze_stability(potential_series, _config())
    with pytest.raises(StabilityError, match="matching y semantics"):
        plot_stability_summary([current_density, potential])


def test_summary_rejects_invalid_metric_without_recomputing_any_metric():
    result = analyze_stability(_series("a"), _config())
    with pytest.raises(StabilityError, match="metric must be"):
        plot_stability_summary([result], metric="made_up")  # type: ignore[arg-type]
