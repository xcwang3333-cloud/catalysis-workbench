"""Scientific/API regressions for explicit quantitative BET analysis."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace

import numpy as np
import pytest
from scipy.constants import Avogadro, R

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.characterization import (
    BETConsistencyResult,
    BETError,
    SorptionCondition,
    SorptionWindow,
    convert_relative_pressure,
    evaluate_bet_region,
    fit_bet,
    plot_bet_fit,
    prepare_sorption_series,
    summarize_bet_fit,
)
from catalysis_workbench.visualization import FigureSpec

_PRESSURE = np.array([0.01, 0.03, 0.05, 0.08, 0.12, 0.18])


def _bet_loading(
    pressure: np.ndarray,
    *,
    n_monolayer: float = 1.0,
    c_constant: float = 100.0,
) -> np.ndarray:
    return (
        n_monolayer
        * c_constant
        * pressure
        / ((1.0 - pressure) * (1.0 + (c_constant - 1.0) * pressure))
    )


def _prepared(
    *,
    pressure: np.ndarray = _PRESSURE,
    n_monolayer: float = 1.0,
    c_constant: float = 100.0,
    loading_unit: str = "mmol/g",
    branch: str = "adsorption",
    descending: bool = False,
    standard_temperature_k: float | None = None,
    standard_pressure_kpa: float | None = None,
) -> Series:
    loading = _bet_loading(
        np.asarray(pressure, dtype=np.float64),
        n_monolayer=n_monolayer,
        c_constant=c_constant,
    )
    x = np.asarray(pressure, dtype=np.float64)
    if descending:
        x = x[::-1]
        loading = loading[::-1]
    raw = Series(
        x=x,
        y=loading,
        key="bet-source",
        label="Synthetic BET",
        x_axis=Axis("relative_pressure", unit="1"),
        y_axis=Axis("adsorbed_quantity", unit=loading_unit),
    )
    return prepare_sorption_series(
        raw,
        SorptionCondition(
            adsorbate="N2",
            measurement_temperature_k=77.0,
            branch=branch,
            standard_temperature_k=standard_temperature_k,
            standard_pressure_kpa=standard_pressure_kpa,
        ),
    )


def _window() -> SorptionWindow:
    return SorptionWindow(0.01, 0.18, "BET region")


def test_exact_synthetic_bet_recovers_linear_and_physical_parameters() -> None:
    result = fit_bet(_prepared(), _window(), cross_section_nm2=0.162)
    evaluation = result.evaluation
    assert evaluation.slope == pytest.approx(0.99, rel=1e-12)
    assert evaluation.intercept == pytest.approx(0.01, rel=1e-12)
    assert evaluation.r_squared == pytest.approx(1.0, abs=1e-14)
    assert result.c_constant == pytest.approx(100.0, rel=1e-11)
    assert result.n_monolayer_source == pytest.approx(1.0, rel=1e-11)
    assert result.p_monolayer == pytest.approx(1.0 / 11.0, rel=1e-11)
    assert evaluation.consistency.all_passed


def test_surface_area_uses_explicit_cross_section_and_molar_loading() -> None:
    result = fit_bet(_prepared(), _window(), cross_section_nm2=0.162)
    expected = 1.0e-3 * Avogadro * 0.162 * 1.0e-18
    assert result.n_monolayer_mol_g == pytest.approx(1.0e-3, rel=1e-11)
    assert result.surface_area_m2_g == pytest.approx(expected, rel=1e-11)


def test_mmol_per_g_and_mol_per_kg_have_explicit_equivalent_molar_conversion() -> None:
    mmol = fit_bet(_prepared(loading_unit="mmol/g"), _window(), cross_section_nm2=0.162)
    molkg = fit_bet(_prepared(loading_unit="mol/kg"), _window(), cross_section_nm2=0.162)
    assert mmol.n_monolayer_mol_g == pytest.approx(1.0e-3)
    assert molkg.n_monolayer_mol_g == pytest.approx(1.0e-3)
    assert molkg.surface_area_m2_g == pytest.approx(mmol.surface_area_m2_g)


def test_stp_volume_loading_uses_declared_standard_condition() -> None:
    temperature = 273.15
    pressure_kpa = 101.325
    n_monolayer_mol_g = 1.0e-3
    n_monolayer_cm3_g = n_monolayer_mol_g * R * temperature / pressure_kpa / 1.0e-3
    source = _prepared(
        n_monolayer=n_monolayer_cm3_g,
        loading_unit="cm^3(STP)/g",
        standard_temperature_k=temperature,
        standard_pressure_kpa=pressure_kpa,
    )
    result = fit_bet(source, _window(), cross_section_nm2=0.162)
    assert result.n_monolayer_mol_g == pytest.approx(n_monolayer_mol_g, rel=1e-11)


def test_mass_loading_requires_explicit_molar_mass_and_converts_when_supplied() -> None:
    molar_mass = 28.0134
    source = _prepared(n_monolayer=molar_mass, loading_unit="mg/g")
    with pytest.raises(BETError, match="molar_mass"):
        fit_bet(source, _window(), cross_section_nm2=0.162)
    result = fit_bet(
        source,
        _window(),
        cross_section_nm2=0.162,
        adsorbate_molar_mass_g_mol=molar_mass,
    )
    assert result.n_monolayer_mol_g == pytest.approx(1.0e-3, rel=1e-11)


def test_percent_pressure_requires_explicit_conversion_before_bet() -> None:
    percent = convert_relative_pressure(_prepared(), target_unit="percent")
    with pytest.raises(BETError, match="convert_relative_pressure"):
        fit_bet(percent, SorptionWindow(1.0, 18.0), cross_section_nm2=0.162)


def test_bet_requires_explicit_adsorption_branch_not_pressure_direction() -> None:
    desorption = _prepared(branch="desorption")
    with pytest.raises(BETError, match="adsorption branch"):
        fit_bet(desorption, _window(), cross_section_nm2=0.162)


def test_selected_bet_points_must_be_strictly_inside_relative_pressure_domain() -> None:
    pressure = np.array([0.0, 0.03, 0.05, 0.08])
    source = _prepared(pressure=pressure)
    with pytest.raises(BETError, match="0 < P/P0 < 1"):
        fit_bet(source, SorptionWindow(0.0, 0.08), cross_section_nm2=0.162)


def test_bet_window_uses_measured_points_only_and_requires_three() -> None:
    source = _prepared()
    evaluation = evaluate_bet_region(source, SorptionWindow(0.02, 0.13))
    assert evaluation.source_indices == (1, 2, 3, 4)
    np.testing.assert_array_equal(evaluation.pressure_fraction, (0.03, 0.05, 0.08, 0.12))
    with pytest.raises(BETError, match="at least three"):
        evaluate_bet_region(source, SorptionWindow(0.01, 0.03))


def test_ascending_and_descending_storage_are_physically_equivalent_and_retained() -> None:
    ascending = fit_bet(_prepared(), _window(), cross_section_nm2=0.162)
    descending = fit_bet(
        _prepared(descending=True),
        _window(),
        cross_section_nm2=0.162,
    )
    assert ascending.evaluation.source_direction == "ascending"
    assert descending.evaluation.source_direction == "descending"
    assert descending.evaluation.pressure_fraction[0] > descending.evaluation.pressure_fraction[-1]
    assert descending.c_constant == pytest.approx(ascending.c_constant, rel=1e-11)
    assert descending.n_monolayer_source == pytest.approx(
        ascending.n_monolayer_source,
        rel=1e-11,
    )
    assert descending.surface_area_m2_g == pytest.approx(
        ascending.surface_area_m2_g,
        rel=1e-11,
    )


def test_nonpositive_loading_fails_before_transform() -> None:
    source = _prepared()
    raw = Series(
        x=source.x,
        y=np.array([0.0, *source.y[1:]]),
        key="bad-loading",
        x_axis=source.x_axis,
        y_axis=source.y_axis,
    )
    prepared = prepare_sorption_series(
        raw,
        SorptionCondition("N2", 77.0, "adsorption"),
    )
    with pytest.raises(BETError, match="strictly positive"):
        evaluate_bet_region(prepared, _window())


def test_rouquerol_monotonicity_is_independent_visible_consistency_state() -> None:
    pressure = np.array([0.05, 0.10, 0.15, 0.20])
    loading = np.array([0.5, 0.8, 0.7, 1.2])
    source = prepare_sorption_series(
        Series(
            x=pressure,
            y=loading,
            key="roq-fail",
            x_axis=Axis("relative_pressure", unit="1"),
            y_axis=Axis("adsorbed_quantity", unit="mmol/g"),
        ),
        SorptionCondition("N2", 77.0, "adsorption"),
    )
    evaluation = evaluate_bet_region(source, SorptionWindow(0.05, 0.20))
    assert evaluation.consistency.positive_parameter_state
    assert not evaluation.consistency.rouquerol_transform_increasing
    assert evaluation.consistency.monolayer_loading_inside_region
    with pytest.raises(BETError, match="rouquerol_transform_increasing"):
        fit_bet(source, SorptionWindow(0.05, 0.20), cross_section_nm2=0.162)


def test_monolayer_loading_span_check_can_fail_independently() -> None:
    pressure = np.array([0.05, 0.10, 0.15, 0.20])
    loading = np.array([0.27299934, 0.59179781, 1.03470118, 1.51419170])
    source = prepare_sorption_series(
        Series(
            x=pressure,
            y=loading,
            key="nm-fail",
            x_axis=Axis("relative_pressure", unit="1"),
            y_axis=Axis("adsorbed_quantity", unit="mmol/g"),
        ),
        SorptionCondition("N2", 77.0, "adsorption"),
    )
    evaluation = evaluate_bet_region(source, SorptionWindow(0.05, 0.20))
    assert evaluation.consistency.positive_parameter_state
    assert evaluation.consistency.rouquerol_transform_increasing
    assert not evaluation.consistency.monolayer_loading_inside_region


def test_perfect_linearity_does_not_override_failed_physical_consistency() -> None:
    pressure = np.array([0.10, 0.15, 0.20, 0.25])
    bet_transform = -0.10 + 2.0 * pressure
    loading = pressure / (bet_transform * (1.0 - pressure))
    source = prepare_sorption_series(
        Series(
            x=pressure,
            y=loading,
            key="linear-but-invalid",
            x_axis=Axis("relative_pressure", unit="1"),
            y_axis=Axis("adsorbed_quantity", unit="mmol/g"),
        ),
        SorptionCondition("N2", 77.0, "adsorption"),
    )
    evaluation = evaluate_bet_region(source, SorptionWindow(0.10, 0.25))
    assert evaluation.r_squared == pytest.approx(1.0, abs=1e-14)
    assert not evaluation.consistency.all_passed
    with pytest.raises(BETError, match="consistency"):
        fit_bet(source, SorptionWindow(0.10, 0.25), cross_section_nm2=0.162)


def test_public_evaluation_reconstruction_rejects_contradictory_state() -> None:
    evaluation = evaluate_bet_region(_prepared(), _window())
    with pytest.raises(BETError, match="consistency state contradicts"):
        replace(
            evaluation,
            consistency=BETConsistencyResult(False, False, False),
        )
    with pytest.raises(BETError, match="OLS regression"):
        replace(evaluation, slope=evaluation.slope * 1.01)


def test_result_arrays_are_immutable_and_source_is_not_mutated() -> None:
    source = _prepared()
    source_x = np.array(source.x, copy=True)
    source_y = np.array(source.y, copy=True)
    result = fit_bet(source, _window(), cross_section_nm2=0.162)
    for array in (
        result.evaluation.pressure_fraction,
        result.evaluation.loading,
        result.evaluation.rouquerol_transform,
        result.evaluation.bet_transform,
        result.evaluation.best_fit_bet_transform,
    ):
        assert not array.flags.writeable
        with pytest.raises(ValueError):
            array[0] = 0.0
    np.testing.assert_array_equal(source.x, source_x)
    np.testing.assert_array_equal(source.y, source_y)


def test_bet_plot_uses_exact_retained_arrays_and_figure_styles() -> None:
    result = fit_bet(_prepared(), _window(), cross_section_nm2=0.162)
    spec = (
        FigureSpec(xlim=(0.0, 0.20), ylim=(0.0, 0.25))
        .with_series_style("bet_fit", line_width=2.5)
        .with_series_style("bet_observed", marker_size=5.0)
    )
    _, ax = plot_bet_fit(result, spec)
    observed = next(line for line in ax.lines if line.get_label() == "BET points")
    fitted = next(line for line in ax.lines if line.get_label() == "OLS fit")
    np.testing.assert_array_equal(observed.get_xdata(), result.evaluation.pressure_fraction)
    np.testing.assert_array_equal(observed.get_ydata(), result.evaluation.bet_transform)
    np.testing.assert_array_equal(fitted.get_ydata(), result.evaluation.best_fit_bet_transform)
    assert fitted.get_linewidth() == pytest.approx(2.5)
    assert observed.get_markersize() == pytest.approx(5.0)
    assert ax.get_xlim() == pytest.approx((0.0, 0.20))
    assert ax.get_ylim() == pytest.approx((0.0, 0.25))


def test_bet_diagnostics_mirror_accepted_fit() -> None:
    result = fit_bet(_prepared(), _window(), cross_section_nm2=0.162)
    diagnostics = summarize_bet_fit(result)
    assert diagnostics.source_key == result.evaluation.source_key
    assert diagnostics.n_points == 6
    assert diagnostics.c_constant == result.c_constant
    assert diagnostics.surface_area_m2_g == result.surface_area_m2_g
    assert diagnostics.consistency.all_passed


def test_importing_characterization_with_bet_public_api_keeps_matplotlib_lazy() -> None:
    code = r"""
import json
import sys
import catalysis_workbench.experimental.characterization as characterization
loaded = any(name == "matplotlib" or name.startswith("matplotlib.") for name in sys.modules)
payload = {
    "matplotlib": loaded,
    "fit": "fit_bet" in characterization.__all__,
    "plot": "plot_bet_fit" in characterization.__all__,
}
print(json.dumps(payload))
"""
    completed = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout.strip())
    assert payload == {"matplotlib": False, "fit": True, "plot": True}
