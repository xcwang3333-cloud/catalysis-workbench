"""Formal-review regressions for CV/Cdl/ECSA provenance and API validation."""

from __future__ import annotations

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.echem import (
    CdlError,
    CVSweepPair,
    ecsa_from_cdl,
    fit_cdl,
)


def _axis() -> Axis:
    return Axis("potential", unit="V", metadata={"reference": "RHE"})


def _pair(rate_mv_s: float, *, key: str) -> CVSweepPair:
    delta = 0.02 * rate_mv_s * 1e-3 + 1e-4
    delta_ma = delta * 1e3
    anodic = Series(
        x=(0.4, 0.5, 0.6),
        y=(delta_ma,) * 3,
        key=f"{key}-anodic",
        x_axis=_axis(),
        y_axis=Axis("current", unit="mA"),
    )
    cathodic = Series(
        x=(0.6, 0.5, 0.4),
        y=(-delta_ma,) * 3,
        key=f"{key}-cathodic",
        x_axis=_axis(),
        y_axis=Axis("current", unit="mA"),
    )
    return CVSweepPair(key, anodic, cathodic, rate_mv_s, "mV/s")


def _fit():
    return fit_cdl(
        (
            _pair(10.0, key="10"),
            _pair(20.0, key="20"),
            _pair(50.0, key="50"),
        ),
        potential_value=0.5,
    )


def test_cv_pair_requires_stable_source_series_keys():
    pair = _pair(10.0, key="10")
    missing_key = Series(
        x=pair.anodic.x,
        y=pair.anodic.y,
        x_axis=pair.anodic.x_axis,
        y_axis=pair.anodic.y_axis,
    )
    with pytest.raises(CdlError, match="Series.key"):
        CVSweepPair(
            "bad",
            missing_key,
            pair.cathodic,
            10.0,
            "mV/s",
        )


def test_ecsa_retains_complete_source_fit_and_original_specific_capacitance_unit():
    fit = _fit()
    result = ecsa_from_cdl(
        fit,
        specific_capacitance_value=40.0,
        specific_capacitance_unit="µF/cm²",
        specific_capacitance_basis="matched literature material/electrolyte",
    )
    assert result.source_fit is fit
    assert result.source_fit.pair_keys == ("10", "20", "50")
    assert result.specific_capacitance_unit == "µF/cm²"
    assert result.specific_capacitance_canonical_unit == "F/cm^2"
    assert result.specific_capacitance_f_cm2 == pytest.approx(40e-6)
    assert result.cdl_value == pytest.approx(fit.slope)
    assert result.cdl_unit == "F"
    assert result.ecsa_unit == "cm^2"


def test_public_fit_result_mode_validation_does_not_leak_numpy_truth_errors():
    fit = _fit()
    with pytest.raises(CdlError, match="difference_mode"):
        type(fit)(
            scan_rate_v_s=fit.scan_rate_v_s,
            anodic_current=fit.anodic_current,
            cathodic_current=fit.cathodic_current,
            delta_half=fit.delta_half,
            current_basis=fit.current_basis,
            target_potential_v=fit.target_potential_v,
            reference=fit.reference,
            sampling_method=fit.sampling_method,
            difference_mode=np.array(["signed"]),  # type: ignore[arg-type]
            slope=fit.slope,
            intercept=fit.intercept,
            r_squared=fit.r_squared,
            pair_provenance=fit.pair_provenance,
        )
