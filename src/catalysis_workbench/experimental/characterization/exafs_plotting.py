"""Passive publication rendering for retained FT-EXAFS components."""

from __future__ import annotations

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from catalysis_workbench.core import Dataset, Series
from catalysis_workbench.visualization import FigureSpec, get_preset, render_curves

from .exafs import EXAFSError, _compact_unit, _semantic_token

_R_NAMES = {"r"}
_COMPONENT_NAMES = {
    "chirmagnitude": "|χ(R)|",
    "chirreal": "Re χ(R)",
    "chirimaginary": "Im χ(R)",
    "chirphase": "Phase χ(R)",
}


def _series_tuple(data: Series | Dataset) -> tuple[Series, ...]:
    if isinstance(data, Series):
        return (data,)
    if isinstance(data, Dataset):
        if len(data) == 0:
            raise EXAFSError("cannot plot an empty FT-EXAFS Dataset")
        return tuple(data)
    raise TypeError("data must be a Series or Dataset")


def _validate_component_series(series: Series) -> None:
    if not isinstance(series, Series):
        raise TypeError("FT-EXAFS plotting requires Series objects")
    if np.iscomplexobj(series.x) or np.iscomplexobj(series.y):
        raise EXAFSError("FT-EXAFS plotting requires a retained real-valued component")
    if not np.isfinite(np.asarray(series.x, dtype=np.float64)).all():
        raise EXAFSError("FT-EXAFS R values must be finite")
    if not np.isfinite(np.asarray(series.y, dtype=np.float64)).all():
        raise EXAFSError("FT-EXAFS component values must be finite")
    if _semantic_token(series.x_axis.name) not in _R_NAMES:
        raise EXAFSError("FT-EXAFS x axis must identify R")
    if _compact_unit(series.x_axis.unit) not in {"angstrom", "a"}:
        raise EXAFSError("FT-EXAFS R requires an explicit angstrom unit")
    y_name = _semantic_token(series.y_axis.name)
    if y_name not in _COMPONENT_NAMES:
        raise EXAFSError("unsupported FT-EXAFS component semantic")
    if series.x_axis.metadata.get("phase_corrected") is True:
        raise EXAFSError("phase-corrected R data are outside the v0.5 FT-EXAFS plot contract")


def _x_label(unit_format: str) -> str:
    if unit_format == "parentheses":
        return "R (Å)"
    if unit_format == "slash":
        return "R / Å"
    if unit_format == "none":
        return "R"
    raise EXAFSError("unsupported axis unit-label format")


def _y_label(series: Series, unit_format: str) -> str:
    base = _COMPONENT_NAMES[_semantic_token(series.y_axis.name)]
    unit = series.y_axis.unit
    if not unit or unit_format == "none":
        return base
    display_unit = str(unit).replace("angstrom", "Å")
    if unit_format == "parentheses":
        return f"{base} ({display_unit})"
    if unit_format == "slash":
        return f"{base} / {display_unit}"
    raise EXAFSError("unsupported axis unit-label format")


def plot_ft_exafs(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Render retained real-valued FT-EXAFS state without recomputing the FT."""
    series = _series_tuple(data)
    for item in series:
        _validate_component_series(item)
    semantics = {_semantic_token(item.y_axis.name) for item in series}
    if len(semantics) != 1:
        raise EXAFSError("one FT-EXAFS axes cannot mix magnitude/real/imaginary/phase")

    resolved_spec = get_preset(preset) if spec is None else spec
    if not isinstance(resolved_spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")
    xlabel = resolved_spec.xlabel
    ylabel = resolved_spec.ylabel
    if xlabel is None:
        xlabel = _x_label(resolved_spec.style.axis_unit_format)
    if ylabel is None:
        ylabel = _y_label(series[0], resolved_spec.style.axis_unit_format)
    return render_curves(data, resolved_spec.updated(xlabel=xlabel, ylabel=ylabel))


__all__ = ["plot_ft_exafs"]
