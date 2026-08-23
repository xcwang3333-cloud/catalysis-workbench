"""Thin publication adapter for explicit Tafel fit results."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.visualization import FigureSpec, get_preset, render_curves

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


def _apply_default_series_style(
    spec: FigureSpec,
    *,
    key: str,
    color: str,
    raw_points: bool,
) -> FigureSpec:
    existing = spec.series_styles.get(key)
    changes: dict[str, object] = {}
    if existing is None or existing.color is None:
        changes["color"] = color
    if raw_points:
        if existing is None or existing.line_style is None:
            changes["line_style"] = "None"
        if existing is None or existing.marker is None:
            changes["marker"] = "o"
    else:
        if existing is None or existing.line_style is None:
            changes["line_style"] = "-"
        if existing is None or existing.marker is None:
            changes["marker"] = ""
    return spec.with_series_style(key, **changes) if changes else spec


def plot_tafel(
    results: TafelFitResult | Sequence[TafelFitResult],
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Render selected Tafel points and fitted lines through the shared renderer.

    The adapter performs no fitting, refitting, sign conversion, window selection, or
    mechanism interpretation. Raw selected points and fitted lines are converted from
    immutable :class:`TafelFitResult` objects into temporary core ``Series`` objects and
    delegated to ``render_curves``.
    """
    normalized = _result_tuple(results)
    resolved_spec = get_preset(preset) if spec is None else spec
    if not isinstance(resolved_spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")

    generated: list[Series] = []
    render_spec = resolved_spec
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

        color = render_spec.style.color_cycle[index % len(render_spec.style.color_cycle)]
        render_spec = _apply_default_series_style(
            render_spec,
            key=raw_key,
            color=color,
            raw_points=True,
        )
        render_spec = _apply_default_series_style(
            render_spec,
            key=fit_key,
            color=color,
            raw_points=False,
        )

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
