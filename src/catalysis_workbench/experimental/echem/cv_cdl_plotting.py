"""Thin publication adapters for validated CV sweeps and calculated Cdl fits."""

from __future__ import annotations

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.visualization import FigureSpec, render_curves

from .cv_cdl import CdlError, CdlFitResult
from .plotting import plot_lsv as _plot_potential_current_curves

_GEOMETRIC = {"geometric", "geometric_area", "geometric_area_cm2"}


def _series_tuple(data: Series | Dataset) -> tuple[Series, ...]:
    if isinstance(data, Series):
        return (data,)
    if isinstance(data, Dataset):
        if len(data) == 0:
            raise CdlError("cannot plot an empty CV Dataset")
        return tuple(data)
    raise TypeError("data must be a Series or Dataset")


def _validate_cv(data: Series | Dataset) -> None:
    for item in _series_tuple(data):
        if item.x_axis.name.casefold() != "potential":
            raise CdlError("CV plotting requires x_axis.name='potential'")
        reference = item.x_axis.metadata.get("reference")
        if not isinstance(reference, str) or not reference.strip():
            raise CdlError("CV plotting requires explicit potential reference metadata")
        name = item.y_axis.name.casefold()
        normalization = item.y_axis.metadata.get("normalization")
        if name == "current":
            if normalization is not None:
                raise CdlError(
                    "total-current CV plotting refuses already-normalized current"
                )
        elif name == "current_density":
            normalized = (
                normalization.strip().casefold().replace(" ", "_")
                if isinstance(normalization, str)
                else None
            )
            if normalized not in _GEOMETRIC:
                raise CdlError(
                    "current-density CV plotting requires geometric-area normalization"
                )
        else:
            raise CdlError("CV plotting requires current or current_density y semantics")


def plot_cv(
    data: Series | Dataset,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Render prepared CV sweeps with electrochemical unit/reference guards.

    The adapter performs no correction, normalization, interpolation, pairing, or
    Cdl calculation. It adds the CV-specific normalization/reference requirements,
    then reuses the established LSV potential-current rendering gate so unsupported
    electrochemical units cannot be plotted as if they were valid CV quantities and
    the potential reference remains visible in automatic axis labels.
    """
    _validate_cv(data)
    return _plot_potential_current_curves(data, spec, preset=preset)


def _cdl_plot_dataset(result: CdlFitResult) -> Dataset:
    if not isinstance(result, CdlFitResult):
        raise TypeError("result must be a CdlFitResult")
    normalization = (
        "total_current_cdl"
        if result.current_basis == "current"
        else "geometric_area_cdl"
    )
    x_axis = Axis("scan_rate", unit="V/s", label="Scan rate")
    y_axis = Axis(
        "half_current_difference",
        unit=result.current_unit,
        label="Half current difference",
        metadata={"normalization": normalization},
    )
    measured = Series(
        x=result.scan_rate_v_s,
        y=result.delta_half,
        key="cdl-measured",
        label="Measured",
        x_axis=x_axis,
        y_axis=y_axis,
        metadata={
            "analysis": "cdl_fit",
            "target_potential_v": result.target_potential_v,
            "reference": result.reference,
            "difference_mode": result.difference_mode,
        },
    )
    fitted = Series(
        x=result.scan_rate_v_s,
        y=result.fit_values,
        key="cdl-fit",
        label="Linear fit",
        x_axis=x_axis,
        y_axis=y_axis,
        metadata={
            "analysis": "cdl_fit",
            "slope": result.slope,
            "intercept": result.intercept,
            "r_squared": result.r_squared,
        },
    )
    return Dataset(
        series=(measured, fitted),
        name="Cdl fit",
        metadata={
            "analysis": "cdl_fit",
            "cdl_value": result.slope,
            "cdl_unit": result.cdl_unit,
            "reference": result.reference,
            "target_potential_v": result.target_potential_v,
        },
    )


def plot_cdl_fit(
    result: CdlFitResult,
    spec: FigureSpec | None = None,
    *,
    preset: str = "publication",
) -> tuple[Figure, Axes]:
    """Render measured half-current differences and the already calculated fit."""
    return render_curves(_cdl_plot_dataset(result), spec, preset=preset)


__all__ = ["plot_cdl_fit", "plot_cv"]
