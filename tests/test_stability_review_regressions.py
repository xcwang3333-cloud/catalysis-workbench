"""Formal-review regressions for Issue #27 stability analysis."""

from __future__ import annotations

from dataclasses import replace

import pytest

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.experimental.echem import (
    FitWindow,
    StabilityAnalysisConfig,
    StabilityError,
    StabilityWindowSpec,
    analyze_stability,
    plot_stability,
    plot_stability_summary,
    validate_stability_series,
)


def _config() -> StabilityAnalysisConfig:
    return StabilityAnalysisConfig(
        analysis_window=StabilityWindowSpec(0, 4, "h"),
        baseline_window=StabilityWindowSpec(0, 1, "h"),
        final_window=StabilityWindowSpec(3, 4, "h"),
    )


def _source(key: str, *, time_basis: str | None = "running_only") -> Series:
    x_metadata = {} if time_basis is None else {"time_basis": time_basis}
    return Series(
        x=(0, 1, 2, 3, 4),
        y=(10, 9.5, 9, 8.5, 8),
        key=key,
        label=key,
        x_axis=Axis("time", unit="h", metadata=x_metadata),
        y_axis=Axis(
            "current_density",
            unit="mA/cm^2",
            metadata={"normalization": "geometric_area"},
        ),
    )


def test_raw_stability_overlay_rejects_mixed_time_basis():
    data = Dataset(
        [
            _source("running", time_basis="running_only"),
            _source("wall", time_basis="wall_clock"),
        ]
    )
    with pytest.raises(StabilityError, match="time_basis"):
        plot_stability(data)


def test_stability_summary_rejects_mixed_time_basis_provenance():
    running = analyze_stability(
        _source("running", time_basis="running_only"),
        _config(),
    )
    wall = analyze_stability(
        _source("wall", time_basis="wall_clock"),
        _config(),
    )
    with pytest.raises(StabilityError, match="time_basis"):
        plot_stability_summary([running, wall])


def test_supported_electrochemical_y_units_are_enforced():
    bad_current = Series(
        x=(0, 1, 2),
        y=(1, 1, 1),
        key="bad-current",
        x_axis=Axis("time", unit="s"),
        y_axis=Axis("current", unit="bananas"),
    )
    with pytest.raises(StabilityError):
        validate_stability_series(bad_current)

    bad_potential = Series(
        x=(0, 1, 2),
        y=(0.5, 0.5, 0.5),
        key="bad-potential",
        x_axis=Axis("time", unit="s"),
        y_axis=Axis(
            "potential",
            unit="mA",
            metadata={"reference": "RHE"},
        ),
    )
    with pytest.raises(StabilityError):
        validate_stability_series(bad_potential)


def test_activity_unit_must_match_normalization_basis():
    source = Series(
        x=(0, 1, 2),
        y=(1, 1, 1),
        key="bad-activity",
        x_axis=Axis("time", unit="s"),
        y_axis=Axis(
            "activity",
            unit="A/g",
            metadata={"normalization": "ecsa"},
        ),
    )
    with pytest.raises(StabilityError, match="unsupported unit"):
        validate_stability_series(source)


def test_result_rejects_forged_provenance_fit_window():
    result = analyze_stability(_source("source"), _config())
    assert result.provenance.fit_window is not None
    forged_provenance = replace(
        result.provenance,
        fit_window=FitWindow(0, 7200, "s", result.analysis_window.n_points),
    )
    with pytest.raises(StabilityError, match="fit window"):
        replace(result, provenance=forged_provenance)


def test_time_basis_is_retained_in_analysis_provenance():
    result = analyze_stability(_source("source", time_basis="running_only"), _config())
    parameters = dict(result.provenance.parameters)
    assert parameters["time_basis"] == "running_only"
