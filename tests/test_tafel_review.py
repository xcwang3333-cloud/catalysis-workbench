from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.echem import (
    TafelError,
    fit_tafel,
    plot_tafel,
)
from catalysis_workbench.visualization import FigureSpec, VisualizationError


def _series(
    *,
    key: str = "a",
    label: str = "A",
    slope_v_dec: float = -0.060,
    intercept_v: float = 0.200,
) -> Series:
    current = -np.array([1e-4, 2e-4, 5e-4, 1e-3, 2e-3])
    potential = intercept_v + slope_v_dec * np.log10(np.abs(current))
    return Series(
        x=potential,
        y=current,
        key=key,
        label=label,
        x_axis=Axis(
            "potential",
            unit="V",
            metadata={"reference": "RHE"},
        ),
        y_axis=Axis(
            "current_density",
            unit="A/cm^2",
            metadata={"normalization": "geometric_area"},
        ),
    )


def _fit(
    *,
    key: str = "a",
    label: str = "A",
    slope_v_dec: float = -0.060,
    intercept_v: float = 0.200,
):
    source = _series(
        key=key,
        label=label,
        slope_v_dec=slope_v_dec,
        intercept_v=intercept_v,
    )
    lower = float(np.min(source.x)) - 1e-9
    upper = float(np.max(source.x)) + 1e-9
    return fit_tafel(
        source,
        (lower, upper),
        fit_window_unit="V",
        branch="cathodic",
        current_sign="negative",
    )


def test_tafel_result_avoids_numpy_generated_dataclass_equality():
    first = _fit()
    second = _fit()

    assert first == first
    assert (first == second) is False
    assert isinstance(hash(first), int)


def test_tafel_result_constructor_rejects_non_numeric_scalars_and_bad_choices():
    result = _fit()

    with pytest.raises(TafelError, match="finite real numeric"):
        replace(result, slope_v_dec=True)
    with pytest.raises(TafelError, match="finite real numeric"):
        replace(result, intercept_v="0.2")
    with pytest.raises(TafelError, match="branch"):
        replace(result, branch=["cathodic"])  # type: ignore[arg-type]
    with pytest.raises(TafelError, match="current_sign"):
        replace(result, current_sign={"negative"})  # type: ignore[arg-type]


def test_tafel_result_constructor_rejects_contradictory_provenance_and_fit_data():
    result = _fit()

    with pytest.raises(TafelError, match="provenance branch contradicts"):
        replace(result, branch="anodic")

    bad_source = replace(result.provenance.source, y_name="current")
    bad_source_provenance = replace(result.provenance, source=bad_source)
    with pytest.raises(TafelError, match="source y axis"):
        replace(result, provenance=bad_source_provenance)

    bad_window = replace(result.fit_window, unit="mV")
    bad_window_provenance = replace(result.provenance, fit_window=bad_window)
    with pytest.raises(TafelError, match="canonical unit"):
        replace(result, provenance=bad_window_provenance)

    with pytest.raises(TafelError, match="fitted-potential data contradict"):
        replace(
            result,
            fitted_potential_v=np.asarray(result.fitted_potential_v) + 0.01,
        )


def test_fit_tafel_non_string_branch_and_sign_fail_as_tafel_errors():
    source = _series()
    lower = float(np.min(source.x)) - 1e-9
    upper = float(np.max(source.x)) + 1e-9

    with pytest.raises(TafelError, match="branch"):
        fit_tafel(
            source,
            (lower, upper),
            fit_window_unit="V",
            branch=[],  # type: ignore[arg-type]
            current_sign="negative",
        )
    with pytest.raises(TafelError, match="current_sign"):
        fit_tafel(
            source,
            (lower, upper),
            fit_window_unit="V",
            branch="cathodic",
            current_sign=[],  # type: ignore[arg-type]
        )


def test_plot_tafel_maps_source_key_style_to_raw_points_and_fit_line():
    first = _fit(key="a", label="A")
    second = _fit(
        key="b",
        label="B",
        slope_v_dec=-0.080,
        intercept_v=0.100,
    )
    spec = FigureSpec().with_series_style(
        "a",
        color="#123456",
        marker="s",
        line_style="--",
        line_width=2.5,
        label="Styled A",
    )

    _, ax = plot_tafel((first, second), spec)

    assert len(ax.lines) == 4
    raw_a, fit_a = ax.lines[:2]
    assert raw_a.get_color() == "#123456"
    assert raw_a.get_marker() == "s"
    assert raw_a.get_linestyle() == "None"
    assert fit_a.get_color() == "#123456"
    assert fit_a.get_marker() in {"", "None", "none", " "}
    assert fit_a.get_linestyle() == "--"
    assert fit_a.get_linewidth() == pytest.approx(2.5)
    assert ax.get_legend_handles_labels()[1][0] == "Styled A"


def test_plot_tafel_source_visibility_hides_both_components_of_one_result():
    first = _fit(key="a", label="A")
    second = _fit(
        key="b",
        label="B",
        slope_v_dec=-0.080,
        intercept_v=0.100,
    )
    spec = FigureSpec().with_series_style("a", visible=False)

    _, ax = plot_tafel((first, second), spec)

    assert len(ax.lines) == 2
    assert ax.get_legend_handles_labels()[1] == ["B"]


def test_plot_tafel_rejects_style_keys_that_are_not_source_series_keys():
    result = _fit(key="a")
    spec = FigureSpec().with_series_style("unknown", color="#123456")

    with pytest.raises(VisualizationError, match="source Series.key"):
        plot_tafel(result, spec)
