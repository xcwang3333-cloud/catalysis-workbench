"""Thin publication adapter for stored Koutecky-Levich fit results."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.visualization import (
    FigureSpec,
    SeriesStyle,
    VisualizationError,
    get_preset,
    render_curves,
)

from .koutecky_levich import KouteckyLevichError, KouteckyLevichFitResult


def _result_tuple(
    results: KouteckyLevichFitResult | Sequence[KouteckyLevichFitResult],
) -> tuple[KouteckyLevichFitResult, ...]:
    if isinstance(results, KouteckyLevichFitResult):
        return (results,)
    if isinstance(results, (str, bytes)) or not isinstance(results, Sequence):
        raise TypeError(
            "results must be a KouteckyLevichFitResult or sequence of results"
        )
    normalized = tuple(results)
    if not normalized:
        raise KouteckyLevichError("cannot plot an empty K-L result sequence")
    if not all(isinstance(item, KouteckyLevichFitResult) for item in normalized):
        raise TypeError("results must contain only KouteckyLevichFitResult instances")
    keys = tuple(item.provenance.source.key for item in normalized)
    if any(not key for key in keys):
        raise KouteckyLevichError(
            "multi-result K-L plotting requires non-empty source Series.key values"
        )
    if len(keys) != len(set(keys)):
        raise KouteckyLevichError(
            "multi-result K-L plotting requires unique source Series.key values"
        )
    return normalized


def _validate_compatibility(results: tuple[KouteckyLevichFitResult, ...]) -> None:
    first = results[0]
    for result in results[1:]:
        if result.current_basis != first.current_basis:
            raise KouteckyLevichError(
                "K-L overlay requires matching total-current/current-density basis"
            )
        if result.normalization != first.normalization:
            raise KouteckyLevichError(
                "K-L overlay requires matching normalization metadata"
            )
        if result.current_mode != first.current_mode:
            raise KouteckyLevichError(
                "K-L overlay requires matching current_mode conventions"
            )


def _generated_keys(
    result: KouteckyLevichFitResult,
    *,
    index: int,
) -> tuple[str, str]:
    base = result.provenance.source.key or f"result-{index}"
    return f"{base}:kl:selected", f"{base}:kl:fit"


def _validate_source_style_keys(
    results: tuple[KouteckyLevichFitResult, ...],
    spec: FigureSpec,
) -> None:
    available = {
        item.provenance.source.key
        for item in results
        if item.provenance.source.key
    }
    unknown = set(spec.series_styles) - available
    if unknown:
        raise VisualizationError(
            "K-L series style keys must match source Series.key values; "
            f"unknown keys: {sorted(unknown)!r}"
        )


def _component_styles(
    source_style: SeriesStyle | None,
    *,
    default_color: str,
) -> tuple[SeriesStyle, SeriesStyle]:
    color = (
        source_style.color
        if source_style is not None and source_style.color is not None
        else default_color
    )
    visible = True if source_style is None else source_style.visible
    alpha = None if source_style is None else source_style.alpha
    base_zorder = (
        2.0
        if source_style is None or source_style.zorder is None
        else source_style.zorder
    )
    raw_style = SeriesStyle(
        color=color,
        line_style="None",
        marker=(
            "o"
            if source_style is None or source_style.marker is None
            else source_style.marker
        ),
        marker_size=None if source_style is None else source_style.marker_size,
        marker_edge_width=(
            None if source_style is None else source_style.marker_edge_width
        ),
        alpha=alpha,
        zorder=base_zorder + 0.1,
        label=None if source_style is None else source_style.label,
        visible=visible,
    )
    fit_style = SeriesStyle(
        color=color,
        line_width=None if source_style is None else source_style.line_width,
        line_style=(
            "-"
            if source_style is None or source_style.line_style is None
            else source_style.line_style
        ),
        marker="",
        alpha=alpha,
        zorder=base_zorder,
        visible=visible,
    )
    return raw_style, fit_style


def plot_koutecky_levich(
    results: KouteckyLevichFitResult | Sequence[KouteckyLevichFitResult],
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Render stored transformed K-L points and stored fitted lines."""
    normalized = _result_tuple(results)
    _validate_compatibility(normalized)
    resolved_spec = get_preset(preset) if spec is None else spec
    if not isinstance(resolved_spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")
    _validate_source_style_keys(normalized, resolved_spec)

    source_styles = dict(resolved_spec.series_styles)
    render_spec = resolved_spec
    for key in tuple(source_styles):
        render_spec = render_spec.without_series_style(key)

    first = normalized[0]
    x_axis = Axis(
        "inverse_sqrt_rotation_rate",
        unit="(rad/s)^-1/2",
        label="Inverse square-root rotation rate",
    )
    y_axis = Axis(
        "reciprocal_current",
        unit=first.reciprocal_current_unit,
        label="Reciprocal current",
        metadata={"normalization": first.normalization},
    )

    generated: list[Series] = []
    generated_keys: set[str] = set()
    for index, result in enumerate(normalized):
        raw_key, fit_key = _generated_keys(result, index=index)
        if raw_key in generated_keys or fit_key in generated_keys:
            raise KouteckyLevichError("generated K-L plotting keys are not unique")
        generated_keys.update((raw_key, fit_key))
        display_label = result.provenance.source.label or result.provenance.source.key
        raw = Series(
            x=result.reciprocal_sqrt_rotation,
            y=result.reciprocal_current,
            label=display_label,
            key=raw_key,
            x_axis=x_axis,
            y_axis=y_axis,
        )
        order = np.argsort(result.reciprocal_sqrt_rotation)
        fit = Series(
            x=np.asarray(result.reciprocal_sqrt_rotation)[order],
            y=np.asarray(result.fitted_reciprocal_current)[order],
            label="",
            key=fit_key,
            x_axis=x_axis,
            y_axis=y_axis,
        )
        generated.extend((raw, fit))

        source_key = result.provenance.source.key
        source_style = source_styles.get(source_key) if source_key else None
        default_color = render_spec.style.color_cycle[
            index % len(render_spec.style.color_cycle)
        ]
        raw_style, fit_style = _component_styles(
            source_style,
            default_color=default_color,
        )
        render_spec = render_spec.with_series_style(raw_key, style=raw_style)
        render_spec = render_spec.with_series_style(fit_key, style=fit_style)

    return render_curves(Dataset(generated), render_spec)


__all__ = ["plot_koutecky_levich"]
