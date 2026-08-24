"""Series and Dataset adapters for product partial current density."""

from __future__ import annotations

import numpy as np

from catalysis_workbench.core import Axis, Dataset, Series

from .partial_current import (
    PartialCurrentDensityError,
    SignMode,
    partial_current_density,
)
from .provenance import SourceDataRef, source_data_ref
from .quantities import EchemQuantityError, current_density_to_a_cm2

_COMPATIBILITY_METADATA_KEYS = ("reference", "normalization")


def _semantic_metadata_value(axis: Axis, key: str) -> object:
    value = axis.metadata.get(key)
    if isinstance(value, str):
        return value.strip().casefold()
    return value


def _validate_condition_compatibility(current: Series, fe: Series) -> None:
    if np.iscomplexobj(current.x) or np.iscomplexobj(fe.x):
        raise PartialCurrentDensityError("condition axes must contain real values")
    if not np.isfinite(current.x).all() or not np.isfinite(fe.x).all():
        raise PartialCurrentDensityError("condition axes must contain only finite values")
    if current.x_axis.name.casefold() != fe.x_axis.name.casefold():
        raise PartialCurrentDensityError("current and FE condition-axis names differ")
    if current.x_axis.unit != fe.x_axis.unit:
        raise PartialCurrentDensityError("current and FE condition-axis units differ")
    if not np.array_equal(current.x, fe.x):
        raise PartialCurrentDensityError(
            "current and FE condition values must match exactly; no interpolation is performed"
        )
    for key in _COMPATIBILITY_METADATA_KEYS:
        current_value = _semantic_metadata_value(current.x_axis, key)
        fe_value = _semantic_metadata_value(fe.x_axis, key)
        if current_value != fe_value:
            raise PartialCurrentDensityError(
                f"current and FE condition-axis {key!r} metadata differ"
            )


def _source_ref_dict(source: SourceDataRef) -> dict[str, object]:
    return {
        "key": source.key,
        "label": source.label,
        "sha256": source.sha256,
        "x_name": source.x_name,
        "x_unit": source.x_unit,
        "y_name": source.y_name,
        "y_unit": source.y_unit,
    }


def _validate_total_current_density(series: Series) -> None:
    if series.y_axis.name.casefold() != "current_density":
        raise PartialCurrentDensityError(
            "total-current Series requires y_axis.name='current_density'"
        )
    try:
        current_density_to_a_cm2(
            series.y,
            series.y_axis.unit,
            allow_nan=False,
        )
    except EchemQuantityError as exc:
        raise PartialCurrentDensityError(str(exc)) from exc


def _validate_fe_series(series: Series) -> str:
    if series.y_axis.name.casefold() != "faradaic_efficiency":
        raise PartialCurrentDensityError(
            "FE Series requires y_axis.name='faradaic_efficiency'"
        )
    if series.y_axis.unit not in {"fraction", "%"}:
        raise PartialCurrentDensityError(
            "FE Series requires y-axis unit 'fraction' or '%'"
        )
    return series.y_axis.unit


def partial_current_density_series(
    current_density: Series,
    fe: Series,
    *,
    sign_mode: SignMode = "signed",
) -> Series:
    """Calculate one condition-resolved product partial-current Series.

    Both input Series must already share the same condition grid. No interpolation,
    sign inversion, FE clipping, or renormalization is performed.
    """
    if not isinstance(current_density, Series) or not isinstance(fe, Series):
        raise TypeError("current_density and fe must both be Series instances")
    _validate_total_current_density(current_density)
    fe_unit = _validate_fe_series(fe)
    _validate_condition_compatibility(current_density, fe)

    result = partial_current_density(
        current_density.y,
        fe.y,
        fe_unit=fe_unit,
        sign_mode=sign_mode,
    )
    current_source = source_data_ref(current_density)
    fe_source = source_data_ref(fe)
    metadata = {
        "analysis": "partial_current_density",
        "equation": "j_product = FE_fraction * j_total",
        "sign_mode": result.sign_mode,
        "fe_input_unit": fe_unit,
        "current_density_unit": current_density.y_axis.unit,
        "current_source": _source_ref_dict(current_source),
        "fe_source": _source_ref_dict(fe_source),
        "fe_exceeds_unity": result.fe_exceeds_unity,
    }

    return Series(
        x=current_density.x,
        y=result.values,
        label=fe.label,
        key=fe.key,
        x_axis=current_density.x_axis,
        y_axis=Axis(
            "partial_current_density",
            unit=current_density.y_axis.unit,
            label="Partial current density",
            metadata=current_density.y_axis.metadata_dict(),
        ),
        metadata=metadata,
    )


def partial_current_density_dataset(
    current_density: Series,
    fe_dataset: Dataset,
    *,
    sign_mode: SignMode = "signed",
) -> Dataset:
    """Calculate ordered multi-product partial currents from one total-current Series."""
    if not isinstance(current_density, Series):
        raise TypeError("current_density must be a Series")
    if not isinstance(fe_dataset, Dataset):
        raise TypeError("fe_dataset must be a Dataset")
    if len(fe_dataset) == 0:
        raise PartialCurrentDensityError(
            "cannot calculate partial currents for an empty FE Dataset"
        )
    keys = tuple(item.key for item in fe_dataset)
    if any(not key for key in keys):
        raise PartialCurrentDensityError(
            "multi-product partial current requires non-empty FE Series.key values"
        )

    results = tuple(
        partial_current_density_series(
            current_density,
            item,
            sign_mode=sign_mode,
        )
        for item in fe_dataset
    )
    current_source = source_data_ref(current_density)
    return Dataset(
        series=results,
        name=fe_dataset.name or "partial current density",
        metadata={
            "analysis": "partial_current_density",
            "sign_mode": sign_mode,
            "product_keys": keys,
            "current_source": _source_ref_dict(current_source),
        },
    )


__all__ = [
    "partial_current_density_dataset",
    "partial_current_density_series",
]
