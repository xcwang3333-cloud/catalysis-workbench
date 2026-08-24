"""Publication plotting for validated EIS data and already-computed EIS fits."""

from __future__ import annotations

from math import isfinite
from typing import Literal, TypeAlias

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from catalysis_workbench.core import Series
from catalysis_workbench.visualization import FigureSpec, get_preset
from catalysis_workbench.visualization._rendering import figure_context, finalize_axes

from .eis import EISError, EISFitResult, validate_eis_series
from .provenance import series_data_sha256

EISImaginaryDisplay: TypeAlias = Literal["negative", "raw"]

_NYQUIST_KEYS = frozenset({"eis_observed", "eis_best_fit"})
_BODE_KEYS = frozenset(
    {
        "eis_magnitude_observed",
        "eis_magnitude_best_fit",
        "eis_phase_observed",
        "eis_phase_best_fit",
    }
)


def _fraction(value: float, *, name: str, allow_zero: bool = False) -> float:
    number = float(value)
    lower_ok = number >= 0.0 if allow_zero else number > 0.0
    if not isfinite(number) or not lower_ok or number >= 1.0:
        interval = "[0, 1)" if allow_zero else "(0, 1)"
        raise EISError(f"{name} must be finite and in {interval}")
    return number


def _unit_label(base: str, unit: str, spec: FigureSpec) -> str:
    unit_format = spec.style.axis_unit_format
    if unit_format == "parentheses":
        return f"{base} ({unit})"
    if unit_format == "slash":
        return f"{base} / {unit}"
    if unit_format == "none":
        return base
    raise EISError("unsupported axis unit-label format")


def _resolved_spec(spec: FigureSpec | None, *, preset: str, bode: bool = False) -> FigureSpec:
    if spec is None:
        resolved = get_preset(preset)
        return resolved.updated(xscale="log") if bode else resolved
    if not isinstance(spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")
    return spec


def _validate_style_keys(spec: FigureSpec, available: frozenset[str], *, name: str) -> None:
    unknown = set(spec.series_styles) - set(available)
    if unknown:
        raise EISError(f"{name} series style keys are not available: {sorted(unknown)!r}")


def _line_kwargs(
    *,
    key: str,
    label: str,
    index: int,
    spec: FigureSpec,
    default_line_style: str | None = None,
    default_marker: str | None = None,
) -> tuple[dict[str, object], bool]:
    style = spec.style
    override = spec.series_styles.get(key)
    visible = True if override is None else override.visible
    color = (
        override.color
        if override is not None and override.color is not None
        else style.color_cycle[index % len(style.color_cycle)]
    )
    resolved_label = label
    if override is not None and override.label is not None:
        resolved_label = override.label
    kwargs: dict[str, object] = {
        "color": color,
        "linewidth": (
            override.line_width
            if override is not None and override.line_width is not None
            else style.line_width
        ),
        "linestyle": (
            override.line_style
            if override is not None and override.line_style is not None
            else (style.line_style if default_line_style is None else default_line_style)
        ),
        "marker": (
            override.marker
            if override is not None and override.marker is not None
            else (style.marker if default_marker is None else default_marker)
        ),
        "markersize": (
            override.marker_size
            if override is not None and override.marker_size is not None
            else style.marker_size
        ),
        "markeredgewidth": (
            override.marker_edge_width
            if override is not None and override.marker_edge_width is not None
            else style.marker_edge_width
        ),
        "label": resolved_label if resolved_label else "_nolegend_",
    }
    if override is not None and override.alpha is not None:
        kwargs["alpha"] = override.alpha
    if override is not None and override.zorder is not None:
        kwargs["zorder"] = override.zorder
    return kwargs, visible


def _validate_fit_alignment(series: Series, fit: EISFitResult | None) -> EISFitResult | None:
    if fit is None:
        return None
    if not isinstance(fit, EISFitResult):
        raise TypeError("fit must be an EISFitResult or None")
    if fit.source_key != series.key:
        raise EISError("EIS fit source key does not match plotted Series")
    if fit.source_sha256 != series_data_sha256(series):
        raise EISError("EIS fit source digest does not match plotted Series")
    if not np.array_equal(fit.frequency_hz, np.asarray(series.x, dtype=np.float64)):
        raise EISError("EIS fit frequency grid/order does not match plotted Series")
    if not np.array_equal(
        fit.observed_impedance,
        np.asarray(series.y, dtype=np.complex128),
    ):
        raise EISError("EIS fit observed impedance does not match plotted Series")
    return fit


def _imaginary_values(values: np.ndarray, display: EISImaginaryDisplay) -> np.ndarray:
    if display == "negative":
        return -values.imag
    if display == "raw":
        return values.imag
    raise EISError("imaginary_display must be 'negative' or 'raw'")


def plot_eis_nyquist(
    series: Series,
    spec: FigureSpec | None = None,
    *,
    fit: EISFitResult | None = None,
    imaginary_display: EISImaginaryDisplay = "negative",
    equal_aspect: bool = False,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Render literal EIS data as a passive Nyquist view."""
    validate_eis_series(series)
    aligned_fit = _validate_fit_alignment(series, fit)
    resolved_spec = _resolved_spec(spec, preset=preset)
    _validate_style_keys(resolved_spec, _NYQUIST_KEYS, name="Nyquist")

    observed = np.asarray(series.y, dtype=np.complex128)
    observed_x = observed.real
    observed_y = _imaginary_values(observed, imaginary_display)

    xlabel = resolved_spec.xlabel
    if xlabel is None:
        xlabel = _unit_label("Z′", "Ω", resolved_spec)
    ylabel = resolved_spec.ylabel
    if ylabel is None:
        base = "−Z″" if imaginary_display == "negative" else "Z″"
        ylabel = _unit_label(base, "Ω", resolved_spec)

    with figure_context(resolved_spec) as figure:
        ax = figure.add_axes(resolved_spec.layout.axes_bounds_fraction())
        labeled_count = 0
        observed_kwargs, observed_visible = _line_kwargs(
            key="eis_observed",
            label=series.label or "Observed",
            index=0,
            spec=resolved_spec,
            default_line_style="none",
            default_marker="o",
        )
        if observed_visible:
            ax.plot(observed_x, observed_y, **observed_kwargs)
            if observed_kwargs["label"] != "_nolegend_":
                labeled_count += 1

        if aligned_fit is not None:
            best = aligned_fit.best_fit_impedance
            fit_kwargs, fit_visible = _line_kwargs(
                key="eis_best_fit",
                label="Best fit",
                index=1,
                spec=resolved_spec,
            )
            if fit_visible:
                ax.plot(best.real, _imaginary_values(best, imaginary_display), **fit_kwargs)
                if fit_kwargs["label"] != "_nolegend_":
                    labeled_count += 1

        if labeled_count == 0:
            raise EISError("all Nyquist layers are hidden by SeriesStyle overrides")
        finalize_axes(
            ax,
            resolved_spec,
            xlabel=xlabel,
            ylabel=ylabel,
            labeled_count=labeled_count,
        )
        if bool(equal_aspect):
            ax.set_aspect("equal", adjustable="box")
        return figure, ax


def _bode_panel_bounds(
    spec: FigureSpec,
    *,
    phase_height_fraction: float,
    panel_gap_fraction: float,
) -> tuple[tuple[float, float, float, float], tuple[float, float, float, float]]:
    phase_fraction = _fraction(
        phase_height_fraction,
        name="phase_height_fraction",
    )
    gap_fraction = _fraction(
        panel_gap_fraction,
        name="panel_gap_fraction",
        allow_zero=True,
    )
    magnitude_fraction = 1.0 - phase_fraction - gap_fraction
    if magnitude_fraction <= 0:
        raise EISError("phase_height_fraction + panel_gap_fraction must be < 1")
    left, bottom, width, height = spec.layout.axes_bounds_fraction()
    phase = (left, bottom, width, height * phase_fraction)
    magnitude = (
        left,
        bottom + height * (phase_fraction + gap_fraction),
        width,
        height * magnitude_fraction,
    )
    return magnitude, phase


def _plot_bode_layer(
    *,
    ax_magnitude: Axes,
    ax_phase: Axes,
    frequency: np.ndarray,
    impedance: np.ndarray,
    spec: FigureSpec,
    magnitude_key: str,
    phase_key: str,
    label: str,
    index: int,
    observed: bool,
) -> int:
    line_style = "none" if observed else None
    marker = "o" if observed else None
    magnitude_kwargs, magnitude_visible = _line_kwargs(
        key=magnitude_key,
        label=label,
        index=index,
        spec=spec,
        default_line_style=line_style,
        default_marker=marker,
    )
    phase_kwargs, phase_visible = _line_kwargs(
        key=phase_key,
        label="_nolegend_",
        index=index,
        spec=spec,
        default_line_style=line_style,
        default_marker=marker,
    )
    if magnitude_visible:
        ax_magnitude.plot(frequency, np.abs(impedance), **magnitude_kwargs)
    if phase_visible:
        ax_phase.plot(frequency, np.angle(impedance, deg=True), **phase_kwargs)
    return int(magnitude_visible and magnitude_kwargs["label"] != "_nolegend_")


def plot_eis_bode(
    series: Series,
    spec: FigureSpec | None = None,
    *,
    fit: EISFitResult | None = None,
    phase_height_fraction: float = 0.38,
    panel_gap_fraction: float = 0.07,
    preset: str = "publication",
) -> tuple[Figure, tuple[Axes, Axes]]:
    """Render magnitude and principal phase directly from literal complex impedance."""
    validate_eis_series(series)
    aligned_fit = _validate_fit_alignment(series, fit)
    resolved_spec = _resolved_spec(spec, preset=preset, bode=True)
    _validate_style_keys(resolved_spec, _BODE_KEYS, name="Bode")
    magnitude_bounds, phase_bounds = _bode_panel_bounds(
        resolved_spec,
        phase_height_fraction=phase_height_fraction,
        panel_gap_fraction=panel_gap_fraction,
    )

    frequency = np.asarray(series.x, dtype=np.float64)
    observed = np.asarray(series.y, dtype=np.complex128)
    xlabel = resolved_spec.xlabel
    if xlabel is None:
        xlabel = _unit_label("Frequency", "Hz", resolved_spec)
    magnitude_ylabel = resolved_spec.ylabel
    if magnitude_ylabel is None:
        magnitude_ylabel = _unit_label("|Z|", "Ω", resolved_spec)

    with figure_context(resolved_spec) as figure:
        ax_magnitude = figure.add_axes(magnitude_bounds)
        ax_phase = figure.add_axes(phase_bounds)
        labeled_count = _plot_bode_layer(
            ax_magnitude=ax_magnitude,
            ax_phase=ax_phase,
            frequency=frequency,
            impedance=observed,
            spec=resolved_spec,
            magnitude_key="eis_magnitude_observed",
            phase_key="eis_phase_observed",
            label=series.label or "Observed",
            index=0,
            observed=True,
        )
        if aligned_fit is not None:
            labeled_count += _plot_bode_layer(
                ax_magnitude=ax_magnitude,
                ax_phase=ax_phase,
                frequency=aligned_fit.frequency_hz,
                impedance=aligned_fit.best_fit_impedance,
                spec=resolved_spec,
                magnitude_key="eis_magnitude_best_fit",
                phase_key="eis_phase_best_fit",
                label="Best fit",
                index=1,
                observed=False,
            )
        if not ax_magnitude.lines and not ax_phase.lines:
            raise EISError("all Bode layers are hidden by SeriesStyle overrides")

        finalize_axes(
            ax_magnitude,
            resolved_spec,
            xlabel="",
            ylabel=magnitude_ylabel,
            labeled_count=labeled_count,
        )
        phase_spec = resolved_spec.updated(
            title=None,
            ylabel=None,
            ylim=None,
            yscale="linear",
            show_legend=False,
            annotations=(),
        )
        finalize_axes(
            ax_phase,
            phase_spec,
            xlabel=xlabel,
            ylabel="Phase (°)",
            labeled_count=0,
        )
        ax_magnitude.tick_params(labelbottom=False)
        return figure, (ax_magnitude, ax_phase)


__all__ = ["EISImaginaryDisplay", "plot_eis_bode", "plot_eis_nyquist"]
