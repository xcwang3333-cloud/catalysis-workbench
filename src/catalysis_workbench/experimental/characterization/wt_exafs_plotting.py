"""Passive publication rendering for retained WT-EXAFS k-R maps."""

from __future__ import annotations

from math import isfinite

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from catalysis_workbench.visualization import FigureSpec, get_preset
from catalysis_workbench.visualization._rendering import (
    figure_axes_context,
    finalize_axes,
)

from .exafs import EXAFSError
from .wt_exafs import EXAFSWTComponent, EXAFSWTResult

_COMPONENT_LABELS = {
    "magnitude": "WT magnitude",
    "real": "WT real",
    "imaginary": "WT imaginary",
    "phase": "WT phase (rad)",
}


def _finite_optional(value: float | None, *, name: str) -> float | None:
    if value is None:
        return None
    result = float(value)
    if not isfinite(result):
        raise EXAFSError(f"{name} must be finite when supplied")
    return result


def plot_wt_exafs(
    result: EXAFSWTResult,
    spec: FigureSpec | None = None,
    *,
    component: EXAFSWTComponent = "magnitude",
    preset: str = "publication",
    cmap: str | None = None,
    vmin: float | None = None,
    vmax: float | None = None,
    show_colorbar: bool = False,
) -> tuple[Figure, Axes]:
    """Render one retained WT-EXAFS component without recomputing the transform."""
    if not isinstance(result, EXAFSWTResult):
        raise TypeError("result must be an EXAFSWTResult")
    if component not in {"magnitude", "real", "imaginary", "phase"}:
        raise EXAFSError("unsupported WT-EXAFS component")
    low = _finite_optional(vmin, name="vmin")
    high = _finite_optional(vmax, name="vmax")
    if low is not None and high is not None and not low < high:
        raise EXAFSError("vmin must be less than vmax")

    values = np.asarray(getattr(result, component), dtype=np.float64)
    before = np.array(values, copy=True)
    resolved_spec = get_preset(preset) if spec is None else spec
    if not isinstance(resolved_spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")

    with figure_axes_context(resolved_spec) as (figure, ax):
        mesh = ax.pcolormesh(
            result.k_grid,
            result.r_grid,
            values,
            shading="auto",
            cmap=cmap,
            vmin=low,
            vmax=high,
        )
        xlabel = resolved_spec.xlabel or "k (Å⁻¹)"
        ylabel = resolved_spec.ylabel or "R (Å)"
        finalize_axes(
            ax,
            resolved_spec,
            xlabel=xlabel,
            ylabel=ylabel,
            labeled_count=0,
        )
        if show_colorbar:
            colorbar = figure.colorbar(mesh, ax=ax)
            colorbar.set_label(
                _COMPONENT_LABELS[component],
                fontsize=resolved_spec.style.axis_label_size,
            )
            colorbar.ax.tick_params(
                labelsize=resolved_spec.style.tick_label_size,
                width=resolved_spec.style.tick_width,
            )
        if not np.array_equal(values, before):
            raise RuntimeError("WT-EXAFS plotting mutated retained transform state")
        return figure, ax


__all__ = ["plot_wt_exafs"]
