"""Formal-review regressions for TOF/TOFapp API and provenance validation."""

from __future__ import annotations

import pytest

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.echem import (
    TurnoverFrequencyError,
    TurnoverFrequencyResult,
    partial_current_density_series,
    turnover_frequency_from_partial_current_series,
)


def _potential_axis() -> Axis:
    return Axis("potential", unit="V", metadata={"reference": "RHE"})


def _partial_current() -> Series:
    current = Series(
        x=(-0.7,),
        y=(-10.0,),
        key="total",
        x_axis=_potential_axis(),
        y_axis=Axis(
            "current_density",
            unit="mA/cm^2",
            metadata={
                "normalization": "geometric_area",
                "electrode_area_cm2": 0.2,
            },
        ),
    )
    fe = Series(
        x=current.x,
        y=(50.0,),
        key="CO",
        label="CO",
        x_axis=current.x_axis,
        y_axis=Axis("faradaic_efficiency", unit="%"),
    )
    return partial_current_density_series(current, fe)


def test_result_constructor_rejects_unhashable_source_kind_with_domain_error():
    with pytest.raises(TurnoverFrequencyError, match="source_kind"):
        TurnoverFrequencyResult(
            source_kind=["molar_rate"],  # type: ignore[arg-type]
            product_rate_mol_s=[1e-6],
            inventory_basis="active_sites",
            inventory_value=1.0,
            inventory_unit="umol",
            inventory_mol=1e-6,
        )


def test_partial_current_requires_valid_upstream_sign_mode():
    source = _partial_current()
    metadata = source.metadata_dict()
    metadata.pop("sign_mode")
    incomplete = Series(
        x=source.x,
        y=source.y,
        key=source.key,
        label=source.label,
        x_axis=source.x_axis,
        y_axis=source.y_axis,
        metadata=metadata,
    )
    with pytest.raises(TurnoverFrequencyError, match="sign_mode"):
        turnover_frequency_from_partial_current_series(
            incomplete,
            electron_number=2,
            inventory_basis="active_sites",
            inventory_value=1.0,
            inventory_unit="umol",
            current_mode="magnitude",
            geometric_area_value=0.2,
            geometric_area_unit="cm^2",
        )


def test_partial_current_rejects_malformed_source_reference():
    source = _partial_current()
    metadata = source.metadata_dict()
    metadata["current_source"] = {"sha256": "not-a-digest"}
    malformed = Series(
        x=source.x,
        y=source.y,
        key=source.key,
        label=source.label,
        x_axis=source.x_axis,
        y_axis=source.y_axis,
        metadata=metadata,
    )
    with pytest.raises(TurnoverFrequencyError, match="current_source"):
        turnover_frequency_from_partial_current_series(
            malformed,
            electron_number=2,
            inventory_basis="active_sites",
            inventory_value=1.0,
            inventory_unit="umol",
            current_mode="magnitude",
            geometric_area_value=0.2,
            geometric_area_unit="cm^2",
        )
