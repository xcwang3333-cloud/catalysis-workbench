"""Scientific-contract regressions for CV sampling, Cdl fitting, and ECSA."""

from __future__ import annotations

import subprocess
import sys

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.echem import (
    CdlError,
    CVSweepPair,
    ecsa_from_cdl,
    fit_cdl,
    fit_cdl_groups,
    sample_cv_current,
    series_data_sha256,
)


def _potential_axis(reference: str = "RHE") -> Axis:
    return Axis(
        "potential",
        unit="V",
        label="Potential",
        metadata={"reference": reference},
    )


def _pair(
    scan_rate_mv_s: float,
    *,
    key: str | None = None,
    cdl: float = 0.02,
    intercept: float = 1e-4,
    basis: str = "current",
    reference: str = "RHE",
    negative_delta: bool = False,
) -> CVSweepPair:
    scan_rate_v_s = scan_rate_mv_s * 1e-3
    delta = cdl * scan_rate_v_s + intercept
    if negative_delta:
        delta = -delta
    if basis == "current":
        y_unit = "mA"
        y_name = "current"
        y_metadata = {}
        scale = 1e3
    else:
        y_unit = "mA/cm^2"
        y_name = "current_density"
        y_metadata = {"normalization": "geometric_area"}
        scale = 1e3

    anodic = Series(
        x=(0.4, 0.5, 0.6),
        y=(delta * scale,) * 3,
        key=f"{key or scan_rate_mv_s}-a",
        label="anodic",
        x_axis=_potential_axis(reference),
        y_axis=Axis(y_name, unit=y_unit, metadata=y_metadata),
    )
    cathodic = Series(
        x=(0.6, 0.5, 0.4),
        y=(-delta * scale,) * 3,
        key=f"{key or scan_rate_mv_s}-c",
        label="cathodic",
        x_axis=_potential_axis(reference),
        y_axis=Axis(y_name, unit=y_unit, metadata=y_metadata),
    )
    return CVSweepPair(
        key=key or f"scan-{scan_rate_mv_s:g}",
        anodic=anodic,
        cathodic=cathodic,
        scan_rate_value=scan_rate_mv_s,
        scan_rate_unit="mV/s",
    )


def _pairs(**kwargs) -> tuple[CVSweepPair, ...]:
    return tuple(_pair(rate, **kwargs) for rate in (10.0, 20.0, 50.0, 100.0))


def test_synthetic_total_current_cdl_recovers_known_free_intercept_fit():
    result = fit_cdl(
        _pairs(cdl=0.02, intercept=1e-4),
        potential_value=0.5,
        sampling_method="exact",
    )
    assert result.current_basis == "current"
    assert result.cdl_unit == "F"
    assert result.current_unit == "A"
    assert result.scan_rate_v_s.tolist() == pytest.approx([0.01, 0.02, 0.05, 0.1])
    assert result.slope == pytest.approx(0.02)
    assert result.intercept == pytest.approx(1e-4)
    assert result.r_squared == pytest.approx(1.0)
    assert result.n_points == 4


def test_synthetic_geometric_current_density_cdl_has_areal_units():
    result = fit_cdl(
        _pairs(cdl=0.1, intercept=2e-4, basis="density"),
        potential_value=0.5,
    )
    assert result.current_basis == "geometric_current_density"
    assert result.cdl_unit == "F/cm^2"
    assert result.current_unit == "A/cm^2"
    assert result.slope == pytest.approx(0.1)
    assert result.intercept == pytest.approx(2e-4)


def test_half_current_difference_is_hand_verified_and_sign_is_explicit():
    pair = _pair(20.0, cdl=0.02, intercept=1e-4)
    signed = fit_cdl(
        (pair, _pair(50.0), _pair(100.0)),
        potential_value=0.5,
        difference_mode="signed",
    )
    expected_first = 0.02 * 0.02 + 1e-4
    assert signed.delta_half[0] == pytest.approx(expected_first)

    negative_pairs = _pairs(negative_delta=True)
    with pytest.raises(CdlError, match="slope must be positive"):
        fit_cdl(
            negative_pairs,
            potential_value=0.5,
            difference_mode="signed",
        )
    magnitude = fit_cdl(
        negative_pairs,
        potential_value=0.5,
        difference_mode="magnitude",
    )
    assert magnitude.slope == pytest.approx(0.02)
    assert (magnitude.delta_half > 0).all()


def test_scan_rates_are_sorted_deterministically_after_unit_conversion():
    pairs = (
        _pair(100.0, key="100"),
        _pair(10.0, key="10"),
        _pair(50.0, key="50"),
        _pair(20.0, key="20"),
    )
    result = fit_cdl(pairs, potential_value=0.5)
    assert result.scan_rate_v_s.tolist() == pytest.approx([0.01, 0.02, 0.05, 0.1])
    assert result.pair_keys == ("10", "20", "50", "100")


def test_linear_sampling_is_bracketed_and_never_extrapolates():
    sweep = Series(
        x=(0.4, 0.6),
        y=(1.0, 3.0),
        x_axis=_potential_axis(),
        y_axis=Axis("current", unit="mA"),
    )
    assert sample_cv_current(sweep, 0.5, sampling_method="linear") == pytest.approx(0.002)
    with pytest.raises(CdlError, match="not present"):
        sample_cv_current(sweep, 0.5, sampling_method="exact")
    with pytest.raises(CdlError, match="no extrapolation"):
        sample_cv_current(sweep, 0.7, sampling_method="linear")


def test_pair_rejects_mismatched_grid_reference_basis_and_missing_values():
    good = _pair(20.0)
    mismatched_grid = Series(
        x=(0.6, 0.45, 0.4),
        y=good.cathodic.y,
        x_axis=good.cathodic.x_axis,
        y_axis=good.cathodic.y_axis,
    )
    with pytest.raises(CdlError, match="potential grids must match"):
        CVSweepPair(
            "bad-grid",
            good.anodic,
            mismatched_grid,
            20.0,
            "mV/s",
        )

    wrong_reference = Series(
        x=good.cathodic.x,
        y=good.cathodic.y,
        x_axis=_potential_axis("Ag/AgCl"),
        y_axis=good.cathodic.y_axis,
    )
    with pytest.raises(CdlError, match="references must match"):
        CVSweepPair(
            "bad-ref",
            good.anodic,
            wrong_reference,
            20.0,
            "mV/s",
        )

    density = _pair(20.0, basis="density")
    with pytest.raises(CdlError, match="same current basis"):
        CVSweepPair(
            "bad-basis",
            good.anodic,
            density.cathodic,
            20.0,
            "mV/s",
        )

    nan_anodic = Series(
        x=good.anodic.x,
        y=(np.nan, 1.0, 1.0),
        x_axis=good.anodic.x_axis,
        y_axis=good.anodic.y_axis,
    )
    with pytest.raises(CdlError, match="missing values"):
        CVSweepPair(
            "bad-nan",
            nan_anodic,
            good.cathodic,
            20.0,
            "mV/s",
        )


def test_non_geometric_current_density_is_rejected_to_prevent_circular_ecsa():
    good = _pair(20.0, basis="density")
    bad_anodic = Series(
        x=good.anodic.x,
        y=good.anodic.y,
        x_axis=good.anodic.x_axis,
        y_axis=Axis(
            "current_density",
            unit="mA/cm^2",
            metadata={"normalization": "ecsa"},
        ),
    )
    with pytest.raises(CdlError, match="geometric-area normalization"):
        CVSweepPair(
            "bad-normalization",
            bad_anodic,
            good.cathodic,
            20.0,
            "mV/s",
        )


def test_duplicate_scan_rates_and_insufficient_pairs_fail_explicitly():
    with pytest.raises(CdlError, match="at least three"):
        fit_cdl((_pair(10.0), _pair(20.0)), potential_value=0.5)
    with pytest.raises(CdlError, match="distinct"):
        fit_cdl(
            (
                _pair(10.0, key="a"),
                _pair(10.0, key="b"),
                _pair(20.0, key="c"),
            ),
            potential_value=0.5,
        )


def test_total_current_cdl_to_ecsa_requires_explicit_cs_and_records_basis():
    cdl = fit_cdl(_pairs(cdl=0.02), potential_value=0.5)
    ecsa = ecsa_from_cdl(
        cdl,
        specific_capacitance_value=40.0,
        specific_capacitance_unit="uF/cm^2",
        specific_capacitance_basis="literature value for matching material/electrolyte",
    )
    assert ecsa.total_cdl_f == pytest.approx(0.02)
    assert ecsa.specific_capacitance_f_cm2 == pytest.approx(40e-6)
    assert ecsa.ecsa_cm2 == pytest.approx(500.0)
    assert ecsa.geometric_area_cm2 is None
    assert "matching material" in ecsa.specific_capacitance_basis


def test_areal_cdl_requires_geometric_area_before_reporting_ecsa_area():
    cdl = fit_cdl(
        _pairs(cdl=0.1, basis="density"),
        potential_value=0.5,
    )
    with pytest.raises(CdlError, match="geometric_area_value"):
        ecsa_from_cdl(
            cdl,
            specific_capacitance_value=40.0,
            specific_capacitance_unit="uF/cm^2",
            specific_capacitance_basis="explicit Cs",
        )
    ecsa = ecsa_from_cdl(
        cdl,
        specific_capacitance_value=40.0,
        specific_capacitance_unit="uF/cm^2",
        specific_capacitance_basis="explicit Cs",
        geometric_area_value=0.2,
        geometric_area_unit="cm^2",
    )
    assert ecsa.total_cdl_f == pytest.approx(0.02)
    assert ecsa.ecsa_cm2 == pytest.approx(500.0)
    assert ecsa.roughness_factor == pytest.approx(2500.0)


def test_invalid_specific_capacitance_and_irrelevant_area_fail_explicitly():
    cdl = fit_cdl(_pairs(), potential_value=0.5)
    with pytest.raises(CdlError, match="specific_capacitance_value"):
        ecsa_from_cdl(
            cdl,
            specific_capacitance_value=0.0,
            specific_capacitance_unit="uF/cm^2",
            specific_capacitance_basis="explicit Cs",
        )
    with pytest.raises(CdlError, match="specific_capacitance_unit"):
        ecsa_from_cdl(
            cdl,
            specific_capacitance_value=40.0,
            specific_capacitance_unit="F/g",
            specific_capacitance_basis="explicit Cs",
        )
    with pytest.raises(CdlError, match="must be omitted"):
        ecsa_from_cdl(
            cdl,
            specific_capacitance_value=40.0,
            specific_capacitance_unit="uF/cm^2",
            specific_capacitance_basis="explicit Cs",
            geometric_area_value=0.2,
            geometric_area_unit="cm^2",
        )


def test_pair_provenance_contains_deterministic_source_digests():
    pairs = _pairs()
    result = fit_cdl(pairs, potential_value=0.5)
    first_pair = sorted(pairs, key=lambda item: item.scan_rate_v_s)[0]
    first_provenance = result.pair_provenance[0]
    assert first_provenance.key == first_pair.key
    assert first_provenance.anodic_source.sha256 == series_data_sha256(first_pair.anodic)
    assert first_provenance.cathodic_source.sha256 == series_data_sha256(first_pair.cathodic)


def test_group_helper_uses_stable_mapping_keys_and_preserves_mapping_order():
    collection = fit_cdl_groups(
        {"cat-b": _pairs(), "cat-a": _pairs(cdl=0.03)},
        potential_value=0.5,
    )
    assert collection.keys == ("cat-b", "cat-a")
    assert collection["cat-b"].slope == pytest.approx(0.02)
    assert collection["cat-a"].slope == pytest.approx(0.03)


def test_numerical_echem_import_remains_matplotlib_lazy_with_cdl_api():
    code = (
        "import sys; "
        "import catalysis_workbench.experimental.echem as e; "
        "assert hasattr(e, 'fit_cdl'); "
        "assert hasattr(e, 'ecsa_from_cdl'); "
        "assert 'matplotlib' not in sys.modules"
    )
    subprocess.run([sys.executable, "-c", code], check=True)
