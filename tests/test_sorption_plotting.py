"""Publication-plotting regressions for gas-sorption isotherms."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pytest

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.experimental.characterization import (
    SorptionCondition,
    SorptionError,
    plot_sorption,
    prepare_sorption_series,
)
from catalysis_workbench.visualization import FigureSpec, SeriesStyle


def _branch(key: str, branch: str, *, label: str | None = None) -> Series:
    x = (0.01, 0.10, 0.50, 0.90)
    y = (0.2, 1.0, 3.0, 5.0) if branch == "adsorption" else (0.3, 1.2, 3.4, 5.2)
    raw = Series(
        x=x,
        y=y,
        key=key,
        label=label or key,
        x_axis=Axis("relative_pressure", unit="1"),
        y_axis=Axis("adsorbed_quantity", unit="mmol/g"),
    )
    return prepare_sorption_series(
        raw,
        SorptionCondition("N2", 77.0, branch),
    )


def test_plot_sorption_applies_branch_line_style_defaults_without_data_changes() -> None:
    ads = _branch("sample-ads", "adsorption")
    des = _branch("sample-des", "desorption")
    fig, ax = plot_sorption(Dataset(series=(ads, des)))
    try:
        assert len(ax.lines) == 2
        assert ax.lines[0].get_linestyle() == "-"
        assert ax.lines[1].get_linestyle() == "--"
        assert tuple(ax.lines[0].get_xdata()) == tuple(ads.x)
        assert tuple(ax.lines[1].get_xdata()) == tuple(des.x)
    finally:
        plt.close(fig)


def test_explicit_stable_key_line_style_overrides_branch_default() -> None:
    des = _branch("sample-des", "desorption")
    spec = FigureSpec(
        series_styles={"sample-des": SeriesStyle(line_style=":", marker="s")}
    )
    fig, ax = plot_sorption(des, spec)
    try:
        assert ax.lines[0].get_linestyle() == ":"
        assert ax.lines[0].get_marker() == "s"
    finally:
        plt.close(fig)


def test_branch_selection_filters_declared_branches_only() -> None:
    ads = _branch("sample-ads", "adsorption")
    des = _branch("sample-des", "desorption")
    fig, ax = plot_sorption(Dataset(series=(ads, des)), branch="desorption")
    try:
        assert len(ax.lines) == 1
        assert ax.lines[0].get_label() == des.label
    finally:
        plt.close(fig)


def test_plot_preserves_explicit_labels_limits_and_scales() -> None:
    ads = _branch("sample-ads", "adsorption")
    spec = FigureSpec(
        xlabel="P/P0 custom",
        ylabel="Uptake custom",
        xlim=(0.0, 1.0),
        ylim=(0.0, 6.0),
        xscale="linear",
    )
    fig, ax = plot_sorption(ads, spec)
    try:
        assert ax.get_xlabel() == "P/P0 custom"
        assert ax.get_ylabel() == "Uptake custom"
        assert ax.get_xlim() == pytest.approx((0.0, 1.0))
        assert ax.get_ylim() == pytest.approx((0.0, 6.0))
    finally:
        plt.close(fig)


def test_plot_rejects_incompatible_overlay_before_rendering() -> None:
    n2 = _branch("n2", "adsorption")
    raw_ar = Series(
        x=(0.01, 0.10, 0.50, 0.90),
        y=(0.2, 1.0, 3.0, 5.0),
        key="ar",
        x_axis=Axis("relative_pressure", unit="1"),
        y_axis=Axis("adsorbed_quantity", unit="mmol/g"),
    )
    ar = prepare_sorption_series(raw_ar, SorptionCondition("Ar", 77.0, "adsorption"))
    with pytest.raises(SorptionError, match="overlay"):
        plot_sorption(Dataset(series=(n2, ar)))
