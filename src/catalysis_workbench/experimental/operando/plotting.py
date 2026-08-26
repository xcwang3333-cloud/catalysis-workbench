"""Passive publication visualization for v0.8 Block 3 operando state."""

from __future__ import annotations

from collections.abc import Mapping
from math import isfinite

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from catalysis_workbench.core import Dataset, Series
from catalysis_workbench.visualization import (
    FigureSpec,
    VisualizationError,
    format_axis_label,
    get_preset,
    render_curves,
)
from catalysis_workbench.visualization._rendering import (
    figure_axes_context,
    finalize_axes,
)

from .operations import OperandoTrace
from .stack import FrameCoordinate, OperandoStack


class OperandoVisualizationError(VisualizationError):
    """Raised when passive operando rendering cannot satisfy its contract."""


def _resolved_spec(spec: FigureSpec | None, *, preset: str) -> FigureSpec:
    resolved = get_preset(preset) if spec is None else spec
    if not isinstance(resolved, FigureSpec):
        raise TypeError("spec must be a FigureSpec")
    return resolved


def _finite_scalar(value: object, *, name: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise TypeError(f"{name} must be a finite real scalar")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise TypeError(f"{name} must be a finite real scalar") from exc
    if not isfinite(number):
        raise OperandoVisualizationError(f"{name} must be finite")
    return number


def _explicit_bool(value: object, *, name: str) -> bool:
    if not isinstance(value, (bool, np.bool_)):
        raise TypeError(f"{name} must be a boolean")
    return bool(value)


def _coordinate_by_key(stack: OperandoStack, key: str) -> FrameCoordinate:
    text = str(key).strip()
    if not text:
        raise OperandoVisualizationError("coordinate_key must not be blank")
    for coordinate in stack.frame_coordinates:
        if coordinate.key == text:
            return coordinate
    raise OperandoVisualizationError(f"unknown frame coordinate {text!r}")


def _edge_coordinates(centers: np.ndarray) -> np.ndarray:
    if centers.ndim != 1 or centers.size < 2:
        raise OperandoVisualizationError(
            "coordinate display geometry requires at least two retained centers"
        )
    edges = np.empty(centers.size + 1, dtype=np.float64)
    edges[1:-1] = (centers[:-1] + centers[1:]) / 2.0
    edges[0] = centers[0] - (centers[1] - centers[0]) / 2.0
    edges[-1] = centers[-1] + (centers[-1] - centers[-2]) / 2.0
    return edges


def _frame_geometry(
    coordinate: FrameCoordinate,
    *,
    mode: str,
) -> tuple[np.ndarray, np.ndarray]:
    token = str(mode).strip().lower()
    if token == "ordinal":
        centers = np.arange(coordinate.values.size, dtype=np.float64)
        edges = np.arange(coordinate.values.size + 1, dtype=np.float64) - 0.5
        return centers, edges
    if token != "coordinate":
        raise OperandoVisualizationError(
            "frame_geometry must be 'ordinal' or 'coordinate'"
        )

    centers = np.asarray(coordinate.values, dtype=np.float64)
    if centers.size < 2:
        raise OperandoVisualizationError(
            "coordinate frame geometry requires at least two retained frames"
        )
    differences = np.diff(centers)
    if not (np.all(differences > 0.0) or np.all(differences < 0.0)):
        raise OperandoVisualizationError(
            "coordinate frame geometry requires unique strictly monotonic retained "
            "coordinate values; sorting or deduplication is not performed"
        )
    return centers, _edge_coordinates(centers)


def _value_limits(value_limits: object) -> tuple[float, float]:
    if not isinstance(value_limits, (tuple, list)) or len(value_limits) != 2:
        raise OperandoVisualizationError(
            "value_limits must contain exactly two explicit finite values"
        )
    lower = _finite_scalar(value_limits[0], name="value_limits[0]")
    upper = _finite_scalar(value_limits[1], name="value_limits[1]")
    if lower >= upper:
        raise OperandoVisualizationError(
            "value_limits[0] must be less than value_limits[1]"
        )
    return lower, upper


def _nonblank(value: object, *, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise OperandoVisualizationError(f"{name} must not be blank")
    return text


def _assert_stack_unchanged(
    stack: OperandoStack,
    *,
    digest: str,
    signal: np.ndarray,
    values: np.ndarray,
    coordinates: tuple[np.ndarray, ...],
) -> None:
    if stack.digest != digest:
        raise RuntimeError("operando plotting mutated retained stack provenance")
    if not np.array_equal(stack.signal, signal):
        raise RuntimeError("operando plotting mutated retained signal coordinates")
    if not np.array_equal(stack.values, values):
        raise RuntimeError("operando plotting mutated retained scientific values")
    for coordinate, before in zip(stack.frame_coordinates, coordinates, strict=True):
        if not np.array_equal(coordinate.values, before):
            raise RuntimeError("operando plotting mutated retained frame coordinates")


def _stack_snapshot(
    stack: OperandoStack,
) -> tuple[str, np.ndarray, np.ndarray, tuple[np.ndarray, ...]]:
    return (
        stack.digest,
        np.array(stack.signal, copy=True),
        np.array(stack.values, copy=True),
        tuple(np.array(item.values, copy=True) for item in stack.frame_coordinates),
    )


def _validate_waterfall_styles(stack: OperandoStack, spec: FigureSpec) -> None:
    unknown = set(spec.series_styles) - set(stack.frame_keys)
    if unknown:
        raise OperandoVisualizationError(
            f"series style keys are not retained frame keys: {sorted(unknown)!r}"
        )
    hidden = [key for key, style in spec.series_styles.items() if not style.visible]
    if hidden:
        raise OperandoVisualizationError(
            "waterfall rendering does not permit trace omission; "
            f"visible=False was supplied for {hidden!r}"
        )


def plot_operando_waterfall(
    stack: OperandoStack,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
    offset_step: float,
    reverse_signal: bool = False,
) -> tuple[Figure, Axes]:
    """Render exact retained frames with one finite presentation-only offset step."""
    if not isinstance(stack, OperandoStack):
        raise TypeError("stack must be an OperandoStack")
    resolved_spec = _resolved_spec(spec, preset=preset)
    offset = _finite_scalar(offset_step, name="offset_step")
    reverse = _explicit_bool(reverse_signal, name="reverse_signal")
    _validate_waterfall_styles(stack, resolved_spec)
    snapshot = _stack_snapshot(stack)

    display = Dataset(
        tuple(
            Series(
                stack.signal,
                stack.values[index] + float(index) * offset,
                key=frame_key,
                label=frame_key,
                x_axis=stack.signal_axis,
                y_axis=stack.value_axis,
                metadata={
                    "catalysis_workbench.operando_display": {
                        "source_stack_digest": stack.digest,
                        "frame_index": index,
                        "offset_step": offset,
                        "display_offset": float(index) * offset,
                    }
                },
            )
            for index, frame_key in enumerate(stack.frame_keys)
        )
    )
    figure, ax = render_curves(display, resolved_spec)
    if reverse:
        ax.invert_xaxis()

    _assert_stack_unchanged(
        stack,
        digest=snapshot[0],
        signal=snapshot[1],
        values=snapshot[2],
        coordinates=snapshot[3],
    )
    return figure, ax


def plot_operando_heatmap(
    stack: OperandoStack,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
    coordinate_key: str,
    frame_geometry: str,
    value_limits: tuple[float, float] | list[float],
    colormap: str,
    reverse_signal: bool = False,
    reverse_condition: bool = False,
    rasterized: bool = False,
    show_colorbar: bool = True,
) -> tuple[Figure, Axes]:
    """Render the exact retained matrix with explicit presentation geometry."""
    if not isinstance(stack, OperandoStack):
        raise TypeError("stack must be an OperandoStack")
    resolved_spec = _resolved_spec(spec, preset=preset)
    if resolved_spec.xscale != "linear" or resolved_spec.yscale != "linear":
        raise OperandoVisualizationError(
            "operando heatmaps require linear x and y display scales"
        )
    coordinate = _coordinate_by_key(stack, coordinate_key)
    mode = str(frame_geometry).strip().lower()
    frame_centers, frame_edges = _frame_geometry(coordinate, mode=mode)
    signal_edges = _edge_coordinates(np.asarray(stack.signal, dtype=np.float64))
    lower, upper = _value_limits(value_limits)
    cmap = _nonblank(colormap, name="colormap")
    reverse_x = _explicit_bool(reverse_signal, name="reverse_signal")
    reverse_y = _explicit_bool(reverse_condition, name="reverse_condition")
    raster = _explicit_bool(rasterized, name="rasterized")
    colorbar_requested = _explicit_bool(show_colorbar, name="show_colorbar")
    snapshot = _stack_snapshot(stack)

    with figure_axes_context(resolved_spec) as (figure, ax):
        mesh = ax.pcolormesh(
            signal_edges,
            frame_edges,
            stack.values,
            shading="flat",
            cmap=cmap,
            vmin=lower,
            vmax=upper,
            rasterized=raster,
        )
        if mode == "ordinal":
            ax.set_yticks(frame_centers)
            ax.set_yticklabels([f"{float(value):g}" for value in coordinate.values])
            coordinate_label = format_axis_label(
                coordinate.axis,
                unit_format=resolved_spec.style.axis_unit_format,
            )
            default_ylabel = f"{coordinate_label} [ordinal frame geometry]"
        else:
            default_ylabel = format_axis_label(
                coordinate.axis,
                unit_format=resolved_spec.style.axis_unit_format,
            )
        finalize_axes(
            ax,
            resolved_spec,
            xlabel=(
                format_axis_label(
                    stack.signal_axis,
                    unit_format=resolved_spec.style.axis_unit_format,
                )
                if resolved_spec.xlabel is None
                else resolved_spec.xlabel
            ),
            ylabel=(
                default_ylabel
                if resolved_spec.ylabel is None
                else resolved_spec.ylabel
            ),
            labeled_count=0,
        )
        if reverse_x:
            ax.invert_xaxis()
        if reverse_y:
            ax.invert_yaxis()
        if colorbar_requested:
            colorbar = figure.colorbar(mesh, ax=ax)
            colorbar.set_label(
                format_axis_label(
                    stack.value_axis,
                    unit_format=resolved_spec.style.axis_unit_format,
                )
            )

    _assert_stack_unchanged(
        stack,
        digest=snapshot[0],
        signal=snapshot[1],
        values=snapshot[2],
        coordinates=snapshot[3],
    )
    return figure, ax


def _valid_digest(value: object) -> bool:
    text = str(value).strip().lower()
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text)


def _require_frame_cut(series: Series) -> None:
    if not isinstance(series, Series):
        raise TypeError("cut must be a Series")
    provenance = series.metadata.get("catalysis_workbench.operando_cut")
    required = {"source_stack_digest", "frame_key", "frame_index", "source_digest"}
    if not isinstance(provenance, Mapping) or not required.issubset(provenance):
        raise OperandoVisualizationError(
            "cut must be an exact Series returned by operando frame_cut"
        )
    if str(provenance["frame_key"]).strip() != series.key:
        raise OperandoVisualizationError("frame-cut provenance contradicts the Series key")
    if not _valid_digest(provenance["source_stack_digest"]) or not _valid_digest(
        provenance["source_digest"]
    ):
        raise OperandoVisualizationError("frame-cut provenance contains an invalid digest")
    frame_index = provenance["frame_index"]
    if isinstance(frame_index, (bool, np.bool_)) or not isinstance(
        frame_index, (int, np.integer)
    ):
        raise OperandoVisualizationError("frame-cut provenance contains an invalid frame index")
    if int(frame_index) < 0:
        raise OperandoVisualizationError("frame-cut provenance contains an invalid frame index")


def plot_operando_frame_cut(
    cut: Series,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
    reverse_signal: bool = False,
) -> tuple[Figure, Axes]:
    """Plot one exact retained frame cut without scientific recalculation."""
    _require_frame_cut(cut)
    resolved_spec = _resolved_spec(spec, preset=preset)
    reverse = _explicit_bool(reverse_signal, name="reverse_signal")
    before_x = np.array(cut.x, copy=True)
    before_y = np.array(cut.y, copy=True)
    figure, ax = render_curves(cut, resolved_spec)
    if reverse:
        ax.invert_xaxis()
    if not np.array_equal(cut.x, before_x) or not np.array_equal(cut.y, before_y):
        raise RuntimeError("frame-cut plotting mutated retained Series values")
    return figure, ax


def plot_operando_trace(
    trace: OperandoTrace,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
    reverse_condition: bool = False,
) -> tuple[Figure, Axes]:
    """Plot one immutable derived trace in exact retained frame order."""
    if not isinstance(trace, OperandoTrace):
        raise TypeError("trace must be an OperandoTrace")
    resolved_spec = _resolved_spec(spec, preset=preset)
    reverse = _explicit_bool(reverse_condition, name="reverse_condition")
    before_digest = trace.digest
    before_coordinate = np.array(trace.coordinate.values, copy=True)
    before_values = np.array(trace.values, copy=True)
    display = Series(
        trace.coordinate.values,
        trace.values,
        key="operando-trace",
        label=trace.method,
        x_axis=trace.coordinate.axis,
        y_axis=trace.value_axis,
        metadata={
            "catalysis_workbench.operando_trace": {
                "trace_digest": trace.digest,
                "method": trace.method,
            }
        },
    )
    figure, ax = render_curves(display, resolved_spec)
    if reverse:
        ax.invert_xaxis()
    if (
        trace.digest != before_digest
        or not np.array_equal(trace.coordinate.values, before_coordinate)
        or not np.array_equal(trace.values, before_values)
    ):
        raise RuntimeError("trace plotting mutated retained OperandoTrace state")
    return figure, ax


__all__ = [
    "OperandoVisualizationError",
    "plot_operando_frame_cut",
    "plot_operando_heatmap",
    "plot_operando_trace",
    "plot_operando_waterfall",
]
