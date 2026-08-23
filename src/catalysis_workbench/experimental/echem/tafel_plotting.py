"""Thin publication adapter for explicit Tafel fit results."""

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

from .tafel import TafelError, TafelFitResult


def _result_tuple(
    results: TafelFitResult | Sequence[TafelFitResult],
) -> tuple[TafelFitResult, ...]:
    if isinstance(results, TafelFitResult):
        return (results,)
    if isinstance(results, (str, bytes)) or not isinstance(results, Sequence):
        raise TypeError("results must be a TafelFitResult or a sequence of results")
    normalized = tuple(results)
    if not normalized:
        raise TafelError("cannot plot an empty Tafel result sequence")
    if not all(isinstance(item, TafelFitResult) for item in normalized):
        raise TypeError("results must contain only TafelFitResult instances")
    if len(normalized) > 1:
        keys = tuple(item.provenance.source.key for item in normalized)
        if any(not key for key in keys):
            raise TafelError(
                "multi-result Tafel plotting requires non-empty source Series.key values"
            )
        if len(keys) != len(set(keys)):
            raise TafelError(
                "multi-result Tafel plotting requires unique source Series.key values"
            )
    return normalized


def _potential_label(reference: str, *, unit_format: str) -> str:
    if unit_format == "none":
        return f"Potential vs {reference}"
    if unit_format == "parentheses":
        return f"Potential (V vs {reference})"
    if unit_format == "slash":
        return f"Potential / V vs {reference}"
    raise TafelError("unsupported axis unit-label format")


def _generated_keys(
    result: TafelFitResult,
    *,
    index: int,
) -> tuple[str, str]:
    base = result.provenance.source.key or f"result-{index}"
    return f"{base}:tafel:selected", f"{base}:tafel:fit"


def _validate_source_style_keys(
    results: Sequence[TafelFitResult],
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
            "Tafel series style keys must match source Series.key values; "
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


def plot_tafel(
    results: TafelFitResult | Sequence[TafelFitResult],
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Render selected Tafel points and fitted lines through the shared renderer.

    The adapter performs no fitting, refitting, sign conversion, window selection, or
    mechanism interpretation. ``FigureSpec.series_styles`` remain addressed by each
    result's original source ``Series.key``; the adapter deterministically maps one
    source style onto marker-only selected points and a line-only fitted component.
    """
    normalized = _result_tuple(results)
    resolved_spec = get_preset(preset) if spec is None else spec
    if not isinstance(resolved_spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")
    _validate_source_style_keys(normalized, resolved_spec)

    source_styles = dict(resolved_spec.series_styles)
    render_spec = resolved_spec
    for key in tuple(source_styles):
        render_spec = render_spec.without_series_style(key)

    generated: list[Series] = []
    generated_keys: set[str] = set()
    for index, result in enumerate(normalized):
        raw_key, fit_key = _generated_keys(result, index=index)
        if raw_key in generated_keys or fit_key in generated_keys:
            raise TafelError("generated Tafel plotting keys are not unique")
        generated_keys.update((raw_key, fit_key))

        x_axis = Axis(
            "log_current_density",
            label="log10(|j| / A cm^-2)",
            metadata={"normalization": result.current_basis},
        )
        y_axis = Axis(
            "potential",
            unit="V",
            label="Potential",
            metadata={"reference": result.potential_reference},
        )
        display_label = result.provenance.source.label or result.provenance.source.key
        raw = Series(
            x=result.log_current_density_a_cm2,
            y=result.potential_v,
            label=display_label,
            key=raw_key,
            x_axis=x_axis,
            y_axis=y_axis,
        )
        order = np.argsort(result.log_current_density_a_cm2)
        fit = Series(
            x=np.asarray(result.log_current_density_a_cm2)[order],
            y=np.asarray(result.fitted_potential_v)[order],
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

    if render_spec.xlabel is None:
        render_spec = render_spec.updated(xlabel="log10(|j| / A cm^-2)")
    if render_spec.ylabel is None:
        render_spec = render_spec.updated(
            ylabel=_potential_label(
                normalized[0].potential_reference,
                unit_format=render_spec.style.axis_unit_format,
            )
        )

    return render_curves(Dataset(generated), render_spec)
