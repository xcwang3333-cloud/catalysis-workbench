"""Passive publication plotting for reviewed product calibration fits."""

from __future__ import annotations

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from catalysis_workbench.visualization import FigureSpec, get_preset
from catalysis_workbench.visualization._rendering import figure_context, finalize_axes

from .calibration import CalibrationFitResult, ProductCalibrationError

_CALIBRATION_KEYS = frozenset({"calibration_observed", "calibration_fit"})


def _resolved_spec(spec: FigureSpec | None, *, preset: str) -> FigureSpec:
    if spec is None:
        return get_preset(preset)
    if not isinstance(spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")
    return spec


def _validate_style_keys(spec: FigureSpec) -> None:
    unknown = set(spec.series_styles) - set(_CALIBRATION_KEYS)
    if unknown:
        raise ProductCalibrationError(
            f"calibration series style keys are not available: {sorted(unknown)!r}"
        )


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


def _axis_label(label: str | None, fallback: str, unit: str) -> str:
    name = fallback if label is None else label
    return f"{name} ({unit})"


def plot_calibration(
    result: CalibrationFitResult,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Render retained standards and retained linear fit without refitting."""
    if not isinstance(result, CalibrationFitResult):
        raise TypeError("result must be a CalibrationFitResult")
    resolved_spec = _resolved_spec(spec, preset=preset)
    _validate_style_keys(resolved_spec)

    xlabel = resolved_spec.xlabel
    if xlabel is None:
        xlabel = _axis_label(
            result.x_axis_label,
            "Calibration quantity",
            result.x_unit,
        )
    ylabel = resolved_spec.ylabel
    if ylabel is None:
        ylabel = _axis_label(
            result.y_axis_label,
            "Response",
            result.y_unit,
        )

    with figure_context(resolved_spec) as figure:
        ax = figure.add_axes(resolved_spec.layout.axes_bounds_fraction())
        labeled_count = 0

        observed_kwargs, observed_visible = _line_kwargs(
            key="calibration_observed",
            label="Standards",
            index=0,
            spec=resolved_spec,
            default_line_style="none",
            default_marker="o",
        )
        if observed_visible:
            ax.plot(result.quantity, result.response, **observed_kwargs)
            if observed_kwargs["label"] != "_nolegend_":
                labeled_count += 1

        fit_kwargs, fit_visible = _line_kwargs(
            key="calibration_fit",
            label="Linear fit",
            index=1,
            spec=resolved_spec,
        )
        if fit_visible:
            ax.plot(
                result.fit_line_quantity,
                result.fit_line_response,
                **fit_kwargs,
            )
            if fit_kwargs["label"] != "_nolegend_":
                labeled_count += 1

        if labeled_count == 0:
            raise ProductCalibrationError(
                "all calibration layers are hidden by SeriesStyle overrides"
            )
        finalize_axes(
            ax,
            resolved_spec,
            xlabel=xlabel,
            ylabel=ylabel,
            labeled_count=labeled_count,
        )
        return figure, ax


__all__ = ["plot_calibration"]
