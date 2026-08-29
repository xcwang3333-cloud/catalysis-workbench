from __future__ import annotations

import pytest

from catalysis_workbench.application import (
    AnalysisProcessingError,
    AnalysisRange,
    FEPartialCurrentAnalysisSpec,
    GenericXYAnalysisSpec,
    LSVAnalysisSpec,
    LSVProcessingSpec,
    PartialCurrentPair,
    default_analysis_spec,
)
from catalysis_workbench.application.analysis.processing import (
    analysis_spec_from_dict,
    analysis_spec_to_plain_dict,
)


def test_task_defaults_are_closed_and_task_specific() -> None:
    assert isinstance(default_analysis_spec("lsv"), LSVAnalysisSpec)
    assert isinstance(
        default_analysis_spec("fe_partial_current"), FEPartialCurrentAnalysisSpec
    )
    assert isinstance(default_analysis_spec("generic_xy"), GenericXYAnalysisSpec)


def test_analysis_range_and_lsv_processing_fail_closed() -> None:
    with pytest.raises(AnalysisProcessingError, match="less than or equal"):
        AnalysisRange(x_min=1.0, x_max=0.0)
    with pytest.raises(AnalysisProcessingError, match="requires rhe_offset_v"):
        LSVProcessingSpec(rhe_mode="direct")
    with pytest.raises(AnalysisProcessingError, match="electrode_area_cm2 is required"):
        LSVProcessingSpec(normalize_to_current_density=True)
    with pytest.raises(AnalysisProcessingError, match="between 0 and 1"):
        LSVProcessingSpec(ir_correction_fraction=1.1)


def test_processing_state_round_trips_with_explicit_pairs_and_overrides() -> None:
    common = LSVProcessingSpec(
        rhe_mode="she_ph",
        reference_potential_vs_she_v=0.197,
        ph=7.0,
        temperature_k=298.15,
        resistance_ohm=12.0,
        ir_correction_fraction=0.85,
        electrode_area_cm2=0.5,
        normalize_to_current_density=True,
        current_density_unit="mA/cm^2",
    )
    override = LSVProcessingSpec(
        rhe_mode="direct",
        rhe_offset_v=0.21,
        electrode_area_cm2=1.0,
        normalize_to_current_density=True,
    )
    lsv = LSVAnalysisSpec(
        common=common,
        overrides={"series-a": override},
        analysis_range=AnalysisRange(x_min=-0.8, x_max=-0.2),
    )
    assert analysis_spec_from_dict(
        "lsv", analysis_spec_to_plain_dict("lsv", lsv)
    ) == lsv

    fe = FEPartialCurrentAnalysisSpec(
        current_common=common,
        current_overrides={"series-current": override},
        pairs=(PartialCurrentPair("series-current", "series-fe"),),
        analysis_range=AnalysisRange(x_min=-0.8, x_max=-0.2),
    )
    assert analysis_spec_from_dict(
        "fe_partial_current",
        analysis_spec_to_plain_dict("fe_partial_current", fe),
    ) == fe


def test_partial_current_pairs_are_explicit_and_unique() -> None:
    pair = PartialCurrentPair("series-current", "series-fe")
    with pytest.raises(AnalysisProcessingError, match="distinct"):
        PartialCurrentPair("same", "same")
    with pytest.raises(AnalysisProcessingError, match="unique"):
        FEPartialCurrentAnalysisSpec(pairs=(pair, pair))
