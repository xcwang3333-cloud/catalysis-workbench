"""Publication rendering adapter for gas-sorption isotherm branches."""

from __future__ import annotations

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from catalysis_workbench.core import Dataset, Series
from catalysis_workbench.visualization import FigureSpec, get_preset, render_curves

from .sorption import (
    SorptionBranchSelection,
    SorptionError,
    _canonicalize_sorption_series,
    select_sorption_branch,
    validate_sorption_overlay,
)


def _canonicalize_data(data: Series | Dataset) -> Series | Dataset:
    if isinstance(data, Series):
        return _canonicalize_sorption_series(data)
    if isinstance(data, Dataset):
        if len(data) == 0:
            raise SorptionError("cannot plot an empty sorption Dataset")
        return Dataset(
            series=tuple(_canonicalize_sorption_series(item) for item in data),
            name=data.name,
            metadata=data.metadata_dict(),
        )
    raise TypeError("data must be a Series or Dataset")


def _apply_branch_style_defaults(
    data: Series | Dataset,
    spec: FigureSpec,
) -> FigureSpec:
    """Add deterministic branch line styles without overriding explicit key styles."""
    series = (data,) if isinstance(data, Series) else tuple(data)
    resolved = spec
    for item in series:
        branch = str(item.metadata["sorption_branch"])
        default_style = "-" if branch == "adsorption" else "--"
        explicit = resolved.series_styles.get(item.key)
        if explicit is None or explicit.line_style is None:
            resolved = resolved.with_series_style(item.key, line_style=default_style)
    return resolved


def plot_sorption(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    branch: SorptionBranchSelection = "all",
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Render declared sorption branches through the shared publication renderer.

    Branch selection filters only caller-declared metadata. Pressure direction is never
    used to classify adsorption versus desorption, and plotting performs no fitting,
    interpolation, normalization, or unit conversion.
    """
    selected = select_sorption_branch(data, branch=branch)
    validate_sorption_overlay(selected)
    canonical = _canonicalize_data(selected)

    resolved_spec = get_preset(preset) if spec is None else spec
    if not isinstance(resolved_spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")
    resolved_spec = _apply_branch_style_defaults(canonical, resolved_spec)
    return render_curves(canonical, resolved_spec)
