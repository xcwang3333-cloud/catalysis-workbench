"""Scientific/API regressions for explicit EIS analysis and publication plotting."""

from __future__ import annotations

import json
import subprocess
import sys

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.echem import (
    EISCapacitor,
    EISCPE,
    EISError,
    EISParallelCircuit,
    EISParameterSpec,
    EISResistor,
    EISSeriesCircuit,
    eis_circuit_element_keys,
    eis_circuit_parameter_keys,
    evaluate_eis_circuit,
    fit_eis,
    plot_eis_bode,
    plot_eis_nyquist,
    summarize_eis_fit,
    validate_eis_series,
)
from catalysis_workbench.visualization import FigureSpec


def _series(
    frequency: np.ndarray,
    impedance: np.ndarray,
    *,
    key: str = "eis",
    label: str = "Synthetic EIS",
) -> Series:
    return Series(
        x=frequency,
        y=impedance,
        key=key,
        label=label,
        x_axis=Axis("frequency", unit="Hz", label="Frequency"),
        y_axis=Axis("impedance", unit="ohm", label="Impedance"),
    )


def _r(key: str, value: float, *, vary: bool = True) -> EISResistor:
    return EISResistor(
        key,
        EISParameterSpec(value, vary=vary, lower=0.0),
    )


def _c(key: str, value: float, *, vary: bool = True) -> EISCapacitor:
    return EISCapacitor(
        key,
        EISParameterSpec(value, vary=vary, lower=0.0),
    )


def _randles_rc(*, rs: float, rct: float, cdl: float, vary: bool = True):
    return EISSeriesCircuit(
        (
            _r("rs", rs, vary=vary),
            EISParallelCircuit(
                (
                    _r("rct", rct, vary=vary),
                    _c("cdl", cdl, vary=vary),
                )
            ),
        )
    )


def test_eis_series_accepts_ascending_and_descending_literal_complex_data() -> None:
    frequency = np.array([1.0, 10.0, 100.0])
    impedance = np.array([4.0 - 3.0j, 3.0 - 2.0j, 2.0 - 1.0j])
    assert validate_eis_series(_series(frequency, impedance)) == "ascending"
    assert validate_eis_series(_series(frequency[::-1], impedance[::-1])) == "descending"


def test_eis_series_fails_closed_on_frequency_semantics_units_and_values() -> None:
    impedance = np.array([2.0 - 1.0j, 3.0 - 2.0j, 4.0 - 3.0j])
    with pytest.raises(EISError, match="semantic"):
        validate_eis_series(
            Series(
                x=(1.0, 10.0, 100.0),
                y=impedance,
                x_axis=Axis("potential", unit="Hz"),
                y_axis=Axis("impedance", unit="ohm"),
            )
        )
    with pytest.raises(EISError, match="unit"):
        validate_eis_series(
            Series(
                x=(1.0, 10.0, 100.0),
                y=impedance,
                x_axis=Axis("frequency", unit="kHz"),
                y_axis=Axis("impedance", unit="ohm"),
            )
        )
    with pytest.raises(EISError, match="positive"):
        validate_eis_series(_series(np.array([0.0, 1.0, 10.0]), impedance))
    with pytest.raises(EISError, match="monotonic"):
        validate_eis_series(_series(np.array([1.0, 100.0, 10.0]), impedance))


def test_eis_series_requires_explicit_complex_impedance_and_ohm_unit() -> None:
    with pytest.raises(EISError, match="complex-valued"):
        validate_eis_series(
            _series(np.array([1.0, 10.0, 100.0]), np.array([1.0, 2.0, 3.0]))
        )
    with pytest.raises(EISError, match="impedance unit"):
        validate_eis_series(
            Series(
                x=(1.0, 10.0, 100.0),
                y=np.array([1.0 - 1.0j, 2.0 - 1.0j, 3.0 - 1.0j]),
                x_axis=Axis("frequency", unit="Hz"),
                y_axis=Axis("impedance", unit="kohm"),
            )
        )


def test_resistor_capacitor_and_cpe_equations_are_hand_verifiable() -> None:
    frequency = np.array([1.0, 10.0])
    resistor = _r("r", 5.0, vary=False)
    np.testing.assert_array_equal(
        evaluate_eis_circuit(resistor, frequency),
        np.array([5.0 + 0.0j, 5.0 + 0.0j]),
    )

    capacitor = _c("c", 2.0e-3, vary=False)
    expected_c = 1.0 / (1j * 2.0 * np.pi * frequency * 2.0e-3)
    np.testing.assert_allclose(evaluate_eis_circuit(capacitor, frequency), expected_c)

    cpe = EISCPE(
        "q",
        EISParameterSpec(2.0e-3, vary=False, lower=0.0),
        EISParameterSpec(1.0, vary=False, lower=0.0, upper=1.0),
    )
    np.testing.assert_allclose(evaluate_eis_circuit(cpe, frequency), expected_c)


def test_series_and_parallel_composition_are_exact() -> None:
    frequency = np.array([10.0, 100.0])
    r1 = _r("r1", 5.0, vary=False)
    r2 = _r("r2", 20.0, vary=False)
    series = EISSeriesCircuit((r1, r2))
    np.testing.assert_array_equal(
        evaluate_eis_circuit(series, frequency),
        np.array([25.0 + 0.0j, 25.0 + 0.0j]),
    )
    parallel = EISParallelCircuit((r1, r2))
    np.testing.assert_allclose(evaluate_eis_circuit(parallel, frequency), 4.0 + 0.0j)


def test_circuit_keys_domains_and_parameter_bounds_fail_explicitly() -> None:
    duplicate = EISSeriesCircuit((_r("same", 1.0), _r("same", 2.0)))
    with pytest.raises(EISError, match="globally unique"):
        eis_circuit_element_keys(duplicate)
    with pytest.raises(EISError, match="> 0"):
        _r("bad", 0.0)
    with pytest.raises(EISError, match="\(0, 1\]"):
        EISCPE(
            "cpe",
            EISParameterSpec(1e-3, lower=0.0),
            EISParameterSpec(1.2),
        )
    with pytest.raises(EISError, match="below"):
        EISParameterSpec(1.0, lower=2.0)


def test_public_parameter_keys_are_stable_and_topology_ordered() -> None:
    circuit = EISSeriesCircuit(
        (
            _r("rs", 4.0),
            EISParallelCircuit(
                (
                    _r("rct", 20.0),
                    EISCPE(
                        "cpe",
                        EISParameterSpec(2e-3, lower=0.0),
                        EISParameterSpec(0.85, lower=0.0, upper=1.0),
                    ),
                )
            ),
        )
    )
    assert eis_circuit_element_keys(circuit) == ("rs", "rct", "cpe")
    assert eis_circuit_parameter_keys(circuit) == (
        "rs.R",
        "rct.R",
        "cpe.Q",
        "cpe.n",
    )


def test_resistor_only_fit_recovers_exact_value_and_physical_residual() -> None:
    frequency = np.logspace(0, 4, 30)
    source = _series(frequency, np.full(frequency.shape, 12.0 + 0.0j))
    result = fit_eis(source, _r("r", 8.0))
    assert result.success
    assert result.parameters["r.R"].value == pytest.approx(12.0, rel=1e-10)
    np.testing.assert_allclose(result.best_fit_impedance, source.y, atol=1e-9)
    np.testing.assert_array_equal(
        result.residual_impedance,
        np.asarray(source.y) - result.best_fit_impedance,
    )
    assert result.objective_sum_squares == pytest.approx(0.0, abs=1e-16)


def test_randles_rc_fit_recovers_explicit_parameters() -> None:
    frequency = np.logspace(5, 0, 80)
    true_circuit = _randles_rc(rs=4.0, rct=22.0, cdl=8.0e-4, vary=False)
    impedance = evaluate_eis_circuit(true_circuit, frequency)
    source = _series(frequency, impedance)
    fit_circuit = _randles_rc(rs=5.0, rct=18.0, cdl=1.0e-3)
    result = fit_eis(source, fit_circuit)
    assert result.success
    assert result.parameters["rs.R"].value == pytest.approx(4.0, rel=1e-5)
    assert result.parameters["rct.R"].value == pytest.approx(22.0, rel=1e-5)
    assert result.parameters["cdl.C"].value == pytest.approx(8.0e-4, rel=1e-5)
    np.testing.assert_allclose(result.best_fit_impedance, impedance, rtol=1e-6, atol=1e-8)


def test_randles_cpe_fit_respects_cpe_domain() -> None:
    frequency = np.logspace(5, -1, 90)
    true = EISSeriesCircuit(
        (
            _r("rs", 3.0, vary=False),
            EISParallelCircuit(
                (
                    _r("rct", 30.0, vary=False),
                    EISCPE(
                        "cpe",
                        EISParameterSpec(1.5e-3, vary=False, lower=0.0),
                        EISParameterSpec(0.82, vary=False, lower=0.0, upper=1.0),
                    ),
                )
            ),
        )
    )
    source = _series(frequency, evaluate_eis_circuit(true, frequency))
    fit_circuit = EISSeriesCircuit(
        (
            _r("rs", 4.0),
            EISParallelCircuit(
                (
                    _r("rct", 25.0),
                    EISCPE(
                        "cpe",
                        EISParameterSpec(1.2e-3, lower=0.0),
                        EISParameterSpec(0.88, lower=0.0, upper=1.0),
                    ),
                )
            ),
        )
    )
    result = fit_eis(source, fit_circuit)
    assert result.success
    assert result.parameters["cpe.Q"].value > 0
    assert 0 < result.parameters["cpe.n"].value <= 1
    assert result.parameters["cpe.n"].value == pytest.approx(0.82, rel=1e-4)


def test_fixed_parameters_remain_fixed() -> None:
    frequency = np.logspace(4, 0, 50)
    true = _randles_rc(rs=4.0, rct=20.0, cdl=1e-3, vary=False)
    source = _series(frequency, evaluate_eis_circuit(true, frequency))
    circuit = EISSeriesCircuit(
        (
            _r("rs", 4.0, vary=False),
            EISParallelCircuit((_r("rct", 15.0), _c("cdl", 8e-4))),
        )
    )
    result = fit_eis(source, circuit)
    assert result.parameters["rs.R"].vary is False
    assert result.parameters["rs.R"].value == pytest.approx(4.0)


def test_ascending_descending_frequency_fit_is_physically_equivalent() -> None:
    frequency = np.logspace(0, 5, 70)
    true = _randles_rc(rs=5.0, rct=18.0, cdl=9e-4, vary=False)
    impedance = evaluate_eis_circuit(true, frequency)
    ascending = fit_eis(_series(frequency, impedance, key="up"), _randles_rc(rs=4, rct=15, cdl=1e-3))
    descending = fit_eis(
        _series(frequency[::-1], impedance[::-1], key="down"),
        _randles_rc(rs=4, rct=15, cdl=1e-3),
    )
    for key in ("rs.R", "rct.R", "cdl.C"):
        assert descending.parameters[key].value == pytest.approx(
            ascending.parameters[key].value,
            rel=1e-6,
        )
    assert ascending.frequency_direction == "ascending"
    assert descending.frequency_direction == "descending"
    assert descending.frequency_hz[0] > descending.frequency_hz[-1]


def test_explicit_weights_affect_objective_only_not_physical_residual_definition() -> None:
    frequency = np.array([1.0, 10.0, 100.0])
    observed = np.array([10.0 + 1.0j, 10.0 + 2.0j, 10.0 + 3.0j])
    source = _series(frequency, observed)
    fixed = _r("r", 10.0, vary=False)
    weights = np.array([1.0, 2.0, 3.0])
    result = fit_eis(source, fixed, weights=weights)
    expected_residual = observed - 10.0
    np.testing.assert_array_equal(result.residual_impedance, expected_residual)
    expected_objective = np.concatenate(
        (expected_residual.real * weights, expected_residual.imag * weights)
    )
    assert result.objective_sum_squares == pytest.approx(
        float(np.dot(expected_objective, expected_objective))
    )
    assert result.weighting_mode == "explicit"
    with pytest.raises(EISError, match="exactly one"):
        fit_eis(source, fixed, weights=np.array([1.0, 2.0]))
    with pytest.raises(EISError, match="strictly positive"):
        fit_eis(source, fixed, weights=np.array([1.0, 0.0, 1.0]))


def test_nyquist_uses_exact_real_and_caller_selected_imaginary_view() -> None:
    frequency = np.logspace(3, 0, 20)
    impedance = np.linspace(5.0, 20.0, 20) - 1j * np.linspace(1.0, 8.0, 20)
    source = _series(frequency, impedance)
    before = np.array(source.y, copy=True)

    _, ax_negative = plot_eis_nyquist(source)
    observed_negative = ax_negative.lines[0]
    np.testing.assert_array_equal(observed_negative.get_xdata(), impedance.real)
    np.testing.assert_array_equal(observed_negative.get_ydata(), -impedance.imag)

    _, ax_raw = plot_eis_nyquist(source, imaginary_display="raw")
    np.testing.assert_array_equal(ax_raw.lines[0].get_ydata(), impedance.imag)
    np.testing.assert_array_equal(source.y, before)


def test_nyquist_fit_overlay_uses_exact_retained_best_fit_and_styles() -> None:
    frequency = np.logspace(4, 0, 40)
    true = _randles_rc(rs=4.0, rct=20.0, cdl=1e-3, vary=False)
    source = _series(frequency, evaluate_eis_circuit(true, frequency))
    fit = fit_eis(source, _randles_rc(rs=5.0, rct=18.0, cdl=8e-4))
    spec = FigureSpec().with_series_style("eis_best_fit", line_width=2.5)
    _, ax = plot_eis_nyquist(source, spec, fit=fit)
    best_line = next(line for line in ax.lines if line.get_label() == "Best fit")
    np.testing.assert_array_equal(best_line.get_xdata(), fit.best_fit_impedance.real)
    np.testing.assert_array_equal(best_line.get_ydata(), -fit.best_fit_impedance.imag)
    assert best_line.get_linewidth() == pytest.approx(2.5)


def test_bode_uses_exact_magnitude_and_principal_phase_without_reordering() -> None:
    frequency = np.array([1000.0, 100.0, 10.0, 1.0])
    impedance = np.array([4.0 - 1.0j, 5.0 - 2.0j, 7.0 - 5.0j, 10.0 - 8.0j])
    source = _series(frequency, impedance)
    _, (ax_magnitude, ax_phase) = plot_eis_bode(source)
    np.testing.assert_array_equal(ax_magnitude.lines[0].get_xdata(), frequency)
    np.testing.assert_allclose(ax_magnitude.lines[0].get_ydata(), np.abs(impedance))
    np.testing.assert_array_equal(ax_phase.lines[0].get_xdata(), frequency)
    np.testing.assert_allclose(ax_phase.lines[0].get_ydata(), np.angle(impedance, deg=True))
    assert ax_magnitude.get_xscale() == "log"
    assert ax_phase.get_xscale() == "log"


def test_fit_overlay_rejects_different_source_state() -> None:
    frequency = np.logspace(3, 0, 20)
    impedance = np.full(frequency.shape, 5.0 + 1.0j)
    source = _series(frequency, impedance, key="one")
    fit = fit_eis(source, _r("r", 4.0))
    modified = _series(frequency, impedance + 0.01j, key="one")
    with pytest.raises(EISError, match="digest"):
        plot_eis_nyquist(modified, fit=fit)


def test_diagnostics_mirror_existing_fit_state() -> None:
    frequency = np.logspace(3, 0, 20)
    source = _series(frequency, np.full(frequency.shape, 7.0 + 0.0j))
    result = fit_eis(source, _r("r", 6.0))
    diagnostics = summarize_eis_fit(result)
    assert diagnostics.success == result.success
    assert diagnostics.nfev == result.nfev
    assert diagnostics.parameter_keys == ("r.R",)
    assert diagnostics.element_keys == ("r",)
    assert diagnostics.objective_sum_squares == result.objective_sum_squares


def test_importing_echem_public_api_keeps_matplotlib_lazy() -> None:
    code = r"""
import json
import sys
import catalysis_workbench.experimental.echem as echem
loaded = any(name == "matplotlib" or name.startswith("matplotlib.") for name in sys.modules)
print(json.dumps({"matplotlib": loaded, "eis": "fit_eis" in echem.__all__, "plot": "plot_eis_nyquist" in echem.__all__}))
"""
    completed = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout.strip())
    assert payload == {"matplotlib": False, "eis": True, "plot": True}
