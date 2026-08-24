"""Series and Dataset adapters for partial current density analysis."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from catalysis_workbench.core import Axis, Dataset, Series

from .partial_current import (
    PartialCurrentDensityError,
    SignMode,
    partial_current_density,
)


def partial_current_density_series(
    current_density: Series,
    fe: Sequence[float] | np.ndarray,
    *,
    fe_unit: str = "fraction",
    sign_mode: SignMode = "signed",
) -> Series:
    """Convert one total-current series into one product partial-current series.

    The x-axis and condition metadata are preserved. FE values must already be
    aligned with the Series condition axis; this function never interpolates.
    """
    if not isinstance(current_density, Series):
        raise PartialCurrentDensityError("current_density must be a Series")

    result = partial_current_density(
        current_density.y,
        fe,
        fe_unit=fe_unit,  # type: ignore[arg-type]
        sign_mode=sign_mode,
    )
    if result.values.size != current_density.x.size:
        raise PartialCurrentDensityError("FE length must match Series length")

    metadata = current_density.metadata_dict()
    metadata.update(
        analysis="partial_current_density",
        fe_unit="fraction",
        sign_mode=sign_mode,
    )

    return Series(
        x=current_density.x,
        y=result.values,
        label=f"{current_density.label} partial current".strip(),
        key=current_density.key,
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
    fe_unit: str = "fraction",
    sign_mode: SignMode = "signed",
) -> Dataset:
    """Convert multi-product FE series into a partial-current Dataset."""
    if not isinstance(fe_dataset, Dataset):
        raise PartialCurrentDensityError("fe_dataset must be a Dataset")

    results = []
    for item in fe_dataset:
        results.append(
            partial_current_density_series(
                current_density,
                item.y,
                fe_unit=fe_unit,
                sign_mode=sign_mode,
            ).with_data(label=item.label, key=item.key)
        )

    return Dataset(
        series=tuple(results),
        name="partial current density",
        metadata={"source": "partial_current_density"},
    )


__all__ = [
    "partial_current_density_dataset",
    "partial_current_density_series",
]
