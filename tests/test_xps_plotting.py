"""Publication-rendering and diagnostic regressions for constrained XPS fits."""

from __future__ import annotations

import json
import subprocess
import sys

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.characterization import (
    XPSDoubletSpec,
    XPSError,
    fit_xps_peaks,
    linear_xps_background,
    plot_xps_fit,
    summarize_xps_fit,
)
from catalysis_workbench.processing import FitParameterSpec, PeakComponentSpec
from catalysis_workbench.visualization import AnnotationSpec, FigureSpec, SeriesStyle


def _gaussian(
    x: np.ndarray,
    *,
    amplitude: float,
    center: float,
    sigma: float,
) -> np.ndarray:
    return amplitude / (sigma * np.sqrt(2.0 * np.pi)) * np.exp(
        -((x - center) ** 2) / (2.0 * sigma**2)
    )


def _source(*, descending: bool = False, key: str = "xps-plot") -> Series:
    x = np.linspace(280.0, 290.0, 301)
    y = (
        2.0
        + _gaussian(x, amplitude=8.0, center=284.7, sigma=0.65)
        + _gaussian(x, amplitude=4.0, center=287.6, sigma=0.65)
    )
    y[0] = 2.0
    y[-1] = 2.0
    if descending:
        x = x[::-1]
        y = y[::-1]
    return Series(
        x=x,
        y=y,
        key=key,
        label="Synthetic XPS",
        x_axis=Axis("binding_energy", unit="eV", label="Binding energy"),
        y_axis=Axis("intensity", unit="counts", label="Intensity"),
    )


def _primary(*, key: str = "doublet_main", label: str = "Main state") -> PeakComponentSpec:
    return PeakComponentSpec(
        key=key,
        model="gaussian",
        label=label,
        parameters={
            "amplitude": FitParameterSpec(7.0, lower=0.0),
            "center": FitParameterSpec(284.6, lower=283.0, upper=286.0),
            "sigma": FitParameterSpec(0.7, lower=0.2, upper=1.5),
        },
    )


def _fit(*, descending: bool = False, reserved_key: str | None = None):
    source = _source(descending=descending)
    background = linear_xps_background(source)
    primary = _primary(key=reserved_key or "doublet_main")
    doublet = XPSDoubletSpec(
        primary=primary,
        secondary_key="doublet_partner",
        separation_ev=2.9,
        amplitude_ratio=0.5,
        parameter_ratios={"sigma": 1.0},
        secondary_label="Partner state",
    )
    return fit_xps_peaks(
        source,
        x_min_ev=280.0,
        x_max_ev=290.0,
        doublets=(doublet,),
        background=background,
    )


def _line_by_label(ax, label: str):
    matches = [line for line in ax.get_lines() if line.get_label() == label]
    assert len(matches) == 1
    return matches[0]


def test_plot_uses_exact_retained_fit_arrays() -> None:
    result = _fit()
    figure, axes = plot_xps_fit(result)
    assert len(axes) == 1
    ax = axes[0]

    observed = _line_by_label(ax, "Synthetic XPS")
    background = _line_by_label(ax, "Background")
    main = _line_by_label(ax, "Main state")
    partner = _line_by_label(ax, "Partner state")
    best = _line_by_label(ax, "Best fit")

    np.testing.assert_array_equal(observed.get_xdata(), result.fit.x)
    np.testing.assert_array_equal(observed.get_ydata(), result.fit.observed_y)
    np.testing.assert_array_equal(background.get_ydata(), result.fit.background)
    np.testing.assert_array_equal(
        main.get_ydata(), result.fit.component_curves["doublet_main"]
    )
    np.testing.assert_array_equal(
        partner.get_ydata(), result.fit.component_curves["doublet_partner"]
    )
    np.testing.assert_array_equal(best.get_ydata(), result.fit.best_fit_y)
    assert figure.get_size_inches()[0] == pytest.approx(3.5)


def test_default_descending_display_is_axes_only_and_source_modes_work() -> None:
    ascending = _fit(descending=False)
    source_x_before = ascending.fit.x.copy()
    best_before = ascending.fit.best_fit_y.copy()

    _, (default_ax,) = plot_xps_fit(ascending)
    assert default_ax.get_xlim()[0] > default_ax.get_xlim()[1]
    np.testing.assert_array_equal(ascending.fit.x, source_x_before)
    np.testing.assert_array_equal(ascending.fit.best_fit_y, best_before)

    _, (ascending_ax,) = plot_xps_fit(ascending, binding_energy_display="ascending")
    assert ascending_ax.get_xlim()[0] < ascending_ax.get_xlim()[1]

    _, (source_ax,) = plot_xps_fit(ascending, binding_energy_display="source")
    assert source_ax.get_xlim()[0] < source_ax.get_xlim()[1]

    descending = _fit(descending=True)
    _, (source_desc_ax,) = plot_xps_fit(descending, binding_energy_display="source")
    assert source_desc_ax.get_xlim()[0] > source_desc_ax.get_xlim()[1]

    with pytest.raises(XPSError, match="binding_energy_display"):
        plot_xps_fit(ascending, binding_energy_display="sideways")


def test_series_style_overrides_target_stable_visual_keys() -> None:
    result = _fit()
    spec = (
        FigureSpec(show_legend=True)
        .with_series_style(
            "xps_observed",
            SeriesStyle(label="Measured", marker="s", marker_size=5.5),
        )
        .with_series_style(
            "doublet_main",
            SeriesStyle(label="Primary", line_style=":"),
        )
        .with_series_style(
            "xps_background",
            SeriesStyle(visible=False),
        )
    )
    _, (ax,) = plot_xps_fit(result, spec)

    measured = _line_by_label(ax, "Measured")
    primary = _line_by_label(ax, "Primary")
    assert measured.get_marker() == "s"
    assert measured.get_markersize() == pytest.approx(5.5)
    assert primary.get_linestyle() == ":"
    assert all(line.get_label() != "Background" for line in ax.get_lines())

    bad_spec = FigureSpec().with_series_style("not_present", SeriesStyle())
    with pytest.raises(XPSError, match="not available"):
        plot_xps_fit(result, bad_spec)


def test_show_hide_background_and_components_is_render_only() -> None:
    result = _fit()
    component_before = {
        key: values.copy() for key, values in result.fit.component_curves.items()
    }
    _, (ax,) = plot_xps_fit(
        result,
        show_background=False,
        show_components=False,
    )
    labels = {line.get_label() for line in ax.get_lines()}
    assert labels == {"Synthetic XPS", "Best fit"}
    for key, values in component_before.items():
        np.testing.assert_array_equal(result.fit.component_curves[key], values)


def test_reserved_component_key_collision_fails_before_rendering() -> None:
    result = _fit(reserved_key="xps_best_fit")
    with pytest.raises(XPSError, match="reserved plotting-layer keys"):
        plot_xps_fit(result)


def test_residual_panel_uses_exact_physical_residual_and_geometry() -> None:
    result = _fit()
    figure, axes = plot_xps_fit(
        result,
        show_residual=True,
        residual_height_fraction=0.2,
        residual_gap_fraction=0.04,
    )
    assert len(axes) == 2
    main_ax, residual_ax = axes
    residual_line = _line_by_label(residual_ax, "Residual")
    np.testing.assert_array_equal(residual_line.get_xdata(), result.fit.x)
    np.testing.assert_array_equal(residual_line.get_ydata(), result.fit.residual)
    zero_lines = [line for line in residual_ax.get_lines() if line.get_label() == "_nolegend_"]
    assert len(zero_lines) == 1
    np.testing.assert_array_equal(zero_lines[0].get_ydata(), np.array([0.0, 0.0]))
    assert main_ax.get_xlim() == pytest.approx(residual_ax.get_xlim())
    assert main_ax.get_position().y0 > residual_ax.get_position().y1
    assert figure.axes == [main_ax, residual_ax]

    with pytest.raises(XPSError, match="must be < 1"):
        plot_xps_fit(
            result,
            show_residual=True,
            residual_height_fraction=0.8,
            residual_gap_fraction=0.3,
        )
    with pytest.raises(XPSError, match="residual_height_fraction"):
        plot_xps_fit(result, show_residual=True, residual_height_fraction=0.0)


def test_figure_spec_labels_limits_typography_and_annotations_are_respected() -> None:
    result = _fit()
    spec = (
        FigureSpec(
            xlabel="BE / eV",
            ylabel="Signal / counts",
            title="XPS fit",
            xlim=(282.0, 289.0),
            ylim=(0.0, 8.0),
            annotations=(AnnotationSpec("A", 0.1, 0.9),),
        )
        .with_style(axis_label_size=9.0, tick_label_size=6.0, line_width=1.7)
        .with_layout(figure_width_in=4.0, figure_height_in=3.0)
    )
    figure, (ax,) = plot_xps_fit(result, spec)
    assert ax.get_xlabel() == "BE / eV"
    assert ax.get_ylabel() == "Signal / counts"
    assert ax.get_title() == "XPS fit"
    assert ax.get_xlim() == pytest.approx((289.0, 282.0))
    assert ax.get_ylim() == pytest.approx((0.0, 8.0))
    assert ax.xaxis.label.get_fontsize() == pytest.approx(9.0)
    assert any(text.get_text() == "A" for text in ax.texts)
    assert figure.get_size_inches() == pytest.approx(np.array([4.0, 3.0]))


def test_diagnostics_mirror_existing_shared_fit_state() -> None:
    result = _fit()
    diagnostics = summarize_xps_fit(result)
    fit = result.fit

    assert diagnostics.success == fit.success
    assert diagnostics.message == fit.message
    assert diagnostics.method == fit.method
    assert diagnostics.backend == fit.backend
    assert diagnostics.background_method == result.background_method
    assert diagnostics.source_direction == result.source_direction
    assert diagnostics.component_keys == result.component_keys
    assert diagnostics.n_points == fit.n_points
    assert diagnostics.n_varying_parameters == fit.n_varying_parameters
    assert diagnostics.chi_square == pytest.approx(fit.chi_square)
    assert diagnostics.reduced_chi_square == pytest.approx(fit.reduced_chi_square)
    assert diagnostics.aic == pytest.approx(fit.aic)
    assert diagnostics.bic == pytest.approx(fit.bic)
    assert diagnostics.covariance_available is (fit.covariance is not None)
    assert diagnostics.fitted_parameter_count == len(fit.parameters)
    expected_with = tuple(
        key for key, parameter in fit.parameters.items() if parameter.stderr is not None
    )
    expected_without = tuple(
        key for key, parameter in fit.parameters.items() if parameter.stderr is None
    )
    assert diagnostics.parameters_with_stderr == expected_with
    assert diagnostics.parameters_without_stderr == expected_without

    with pytest.raises(TypeError, match="XPSPeakFitResult"):
        summarize_xps_fit(object())  # type: ignore[arg-type]


def test_public_numerical_import_keeps_matplotlib_lazy_until_plot_call() -> None:
    code = r"""
import json
import sys
import catalysis_workbench.experimental.characterization as characterization
payload = {
    "matplotlib": any(
        name == "matplotlib" or name.startswith("matplotlib.")
        for name in sys.modules
    ),
    "has_plot": "plot_xps_fit" in characterization.__all__,
    "has_diagnostics": "summarize_xps_fit" in characterization.__all__,
}
print(json.dumps(payload))
"""
    completed = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout.strip())
    assert payload == {
        "matplotlib": False,
        "has_plot": True,
        "has_diagnostics": True,
    }
