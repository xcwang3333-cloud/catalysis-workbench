"""Fail-closed regressions for quantitative BET preprocessing provenance."""

from __future__ import annotations

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.characterization import (
    BETError,
    SorptionCondition,
    SorptionProcessingConfig,
    SorptionWindow,
    evaluate_bet_region,
    prepare_sorption_series,
    process_sorption,
)
from catalysis_workbench.processing import normalize


def _prepared() -> Series:
    pressure = np.array([0.01, 0.03, 0.05, 0.08, 0.12, 0.18])
    c_constant = 100.0
    n_monolayer = 1.0
    loading = (
        n_monolayer
        * c_constant
        * pressure
        / ((1.0 - pressure) * (1.0 + (c_constant - 1.0) * pressure))
    )
    raw = Series(
        x=pressure,
        y=loading,
        key="bet-preprocessing",
        x_axis=Axis("relative_pressure", unit="1"),
        y_axis=Axis("adsorbed_quantity", unit="mmol/g"),
    )
    return prepare_sorption_series(
        raw,
        SorptionCondition("N2", 77.0, "adsorption"),
    )


def test_bet_rejects_display_offset_recorded_in_processing_history() -> None:
    shifted = process_sorption(
        _prepared(),
        config=SorptionProcessingConfig(vertical_offset=0.25),
    )
    with pytest.raises(BETError, match="unsupported processing: offset"):
        evaluate_bet_region(shifted, SorptionWindow(0.01, 0.18))


def test_bet_rejects_normalized_loading_even_when_units_remain_sorption_compatible() -> None:
    normalized = normalize(_prepared(), method="max")
    with pytest.raises(BETError, match="unsupported processing: normalize"):
        evaluate_bet_region(normalized, SorptionWindow(0.01, 0.18))


def test_bet_rejects_unknown_processing_instead_of_defaulting_to_trust() -> None:
    source = _prepared()
    metadata = source.metadata_dict()
    history = list(metadata["processing_history"])
    history.append({"operation": "custom.quantitative_transform", "parameters": {}})
    metadata["processing_history"] = history
    altered_provenance = Series(
        x=source.x,
        y=source.y,
        key=source.key,
        label=source.label,
        x_axis=source.x_axis,
        y_axis=source.y_axis,
        metadata=metadata,
    )
    with pytest.raises(BETError, match="custom.quantitative_transform"):
        evaluate_bet_region(altered_provenance, SorptionWindow(0.01, 0.18))


def test_explicit_measured_point_crop_remains_compatible_with_bet() -> None:
    cropped = process_sorption(
        _prepared(),
        config=SorptionProcessingConfig(
            relative_pressure_min=0.03,
            relative_pressure_max=0.18,
        ),
    )
    evaluation = evaluate_bet_region(cropped, SorptionWindow(0.03, 0.18))
    assert evaluation.consistency.all_passed
    np.testing.assert_array_equal(
        evaluation.pressure_fraction,
        np.array([0.03, 0.05, 0.08, 0.12, 0.18]),
    )
