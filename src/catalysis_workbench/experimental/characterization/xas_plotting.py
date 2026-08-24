"""Passive publication rendering for already-prepared XAS/XANES traces."""

from __future__ import annotations

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from catalysis_workbench.core import Dataset, Series
from catalysis_workbench.visualization import FigureSpec, format_axis_label, get_preset, render_curves

from .xas import XASError, _semantic_token, validate_xas_series


def _series_tuple(data: Series | Dataset) -> tuple[Series, ...]:
    if isinstance(data, Series):
        return (data,)
    if isinstance(data, Dataset):
        if len(data) == 0:
            raise XASError("cannot plot an empty XAS Dataset")
        return tuple(data)
    raise TypeError("data must be a Series or Dataset")


def _x_label(series: Series, unit_format: str) -> str:
    relative = _semantic_token(series.x_axis.name) in {"energyrelativetoe0", "energye0"}
    base = "Energy - E0" if relative else "Energy"
    if unit_format == "parentheses":
        return f"{base} (eV)"
    if unit_format == "slash":
        return f"{base} / eV"
    if unit_format == "none":
        return base
    raise XASError("unsupported axis unit-label format")


def plot_xanes(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Render compatible raw or normalized XANES traces without reprocessing them."""
    series = _series_tuple(data)
    for item in series:
        validate_xas_series(item, allow_relative_energy=True)

    x_semantics = {_semantic_token(item.x_axis.name) for item in series}
    y_semantics = {_semantic_token(item.y_axis.name) for item in series}
    if len(x_semantics) != 1:
        raise XASError("XANES overlays require the same energy-reference semantic")
    if len(y_semantics) != 1:
        raise XASError("XANES overlays cannot mix raw and normalized absorption")

    resolved_spec = get_preset(preset) if spec is None else spec
    if not isinstance(resolved_spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")
    xlabel = resolved_spec.xlabel
    ylabel = resolved_spec.ylabel
    if xlabel is None:
        xlabel = _x_label(series[0], resolved_spec.style.axis_unit_format)
    if ylabel is None:
        ylabel = format_axis_label(
            series[0].y_axis,
            unit_format=resolved_spec.style.axis_unit_format,
        )
    return render_curves(data, resolved_spec.updated(xlabel=xlabel, ylabel=ylabel))


__all__ = ["plot_xanes"]
