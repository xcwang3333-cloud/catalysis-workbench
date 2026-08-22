"""Publication rendering adapter for LSV and polarization curves.

Scientific correction and normalization remain in :mod:`.lsv`.  This module is a
thin domain adapter over the shared visualization engine: it validates canonical
LSV axis semantics, adds electrochemical reference information to automatic axis
labels, and delegates all artists/layout/export styling to ``render_curves``.
"""

from __future__ import annotations

from collections.abc import Sequence

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.visualization import (
    FigureSpec,
    format_axis_label,
    get_preset,
    render_curves,
)

from .lsv import (
    LSVError,
    _CURRENT_DENSITY_TO_A_CM2,
    _CURRENT_TO_A,
    _POTENTIAL_TO_V,
    _compact_unit,
)


def _series_tuple(data: Series | Dataset) -> tuple[Series, ...]:
    if isinstance(data, Series):
        return (data,)
    if isinstance(data, Dataset):
        if len(data) == 0:
            raise LSVError("cannot plot an empty LSV Dataset")
        return tuple(data)
    raise TypeError("data must be a Series or Dataset")


def _validate_lsv_axes(series: Sequence[Series]) -> None:
    for item in series:
        if item.x_axis.name.casefold() != "potential":
            raise LSVError(
                "LSV plotting requires x_axis.name='potential'; "
                f"got {item.x_axis.name!r}"
            )
        potential_unit = _compact_unit(item.x_axis.unit)
        if potential_unit not in _POTENTIAL_TO_V:
            raise LSVError(
                "LSV plotting requires potential units V or mV; "
                f"got {item.x_axis.unit!r}"
            )

        y_name = item.y_axis.name.casefold()
        if y_name not in {"current", "current_density"}:
            raise LSVError(
                "LSV plotting requires y_axis.name='current' or 'current_density'; "
                f"got {item.y_axis.name!r}"
            )
        y_unit = _compact_unit(item.y_axis.unit)
        supported_units = (
            _CURRENT_TO_A if y_name == "current" else _CURRENT_DENSITY_TO_A_CM2
        )
        if y_unit not in supported_units:
            quantity = "current" if y_name == "current" else "current density"
            raise LSVError(
                f"LSV plotting requires a supported {quantity} unit; "
                f"got {item.y_axis.unit!r}"
            )


def _potential_axis_label(axis: Axis, *, unit_format: str) -> str:
    reference = axis.metadata.get("reference")
    if reference is None or not str(reference).strip():
        return format_axis_label(axis, unit_format=unit_format)

    base = axis.label or axis.name
    reference_name = str(reference).strip()
    if unit_format == "none":
        return f"{base} vs {reference_name}"
    if unit_format == "parentheses":
        return f"{base} ({axis.unit} vs {reference_name})"
    if unit_format == "slash":
        return f"{base} / {axis.unit} vs {reference_name}"
    # FigureSpec/PlotStyle already validates supported unit formats, but keep this
    # defensive branch so the helper remains correct if called independently later.
    raise LSVError("unsupported axis unit-label format")


def plot_lsv(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Render an LSV/polarization curve through the shared publication renderer.

    The adapter performs **no** numerical correction, normalization, smoothing, sign
    inversion, or resampling.  Process data explicitly with :func:`process_lsv` or
    :func:`process_lsv_dataset` before plotting when those operations are required.

    ``None`` axis labels inherit automatic electrochemical labels.  Explicit strings,
    including ``""``, are preserved exactly.  Potential reference metadata such as
    ``reference="RHE"`` is rendered as ``Potential (V vs RHE)`` by default and remains
    visible even when the global unit-display format is disabled.
    """
    series = _series_tuple(data)
    _validate_lsv_axes(series)

    resolved_spec = get_preset(preset) if spec is None else spec
    if not isinstance(resolved_spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")

    first = series[0]
    xlabel = resolved_spec.xlabel
    ylabel = resolved_spec.ylabel
    if xlabel is None:
        xlabel = _potential_axis_label(
            first.x_axis,
            unit_format=resolved_spec.style.axis_unit_format,
        )
    if ylabel is None:
        ylabel = format_axis_label(
            first.y_axis,
            unit_format=resolved_spec.style.axis_unit_format,
        )

    render_spec = resolved_spec.updated(xlabel=xlabel, ylabel=ylabel)
    return render_curves(data, render_spec)
