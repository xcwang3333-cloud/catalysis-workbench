from __future__ import annotations

import subprocess
import sys

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.experimental.echem import (
    FARADAY_CONSTANT_C_MOL,
    FaradaicEfficiencyError,
    FaradaicEfficiencyResult,
    faradaic_efficiency_closure,
    faradaic_efficiency_dataset,
    faradaic_efficiency_from_amount,
    faradaic_efficiency_from_rate,
    faradaic_efficiency_series,
    plot_faradaic_efficiency,
    series_data_sha256,
)
from catalysis_workbench.visualization import FigureSpec, ScatterError


def _condition_axis(*, reference: str = "RHE") -> Axis:
    return Axis(
        "potential",
        unit="V",
        label="Potential",
        metadata={"reference": reference},
    )


def _product_amount(
    *,
    key: str = "CO",
    label: str = "CO",
    values: tuple[float, ...] = (1.0, 1.5, 2.0),
    unit: str = "umol",
    reference: str = "RHE",
) -> Series:
    return Series(
        x=(-0.5, -0.6, -0.7),
        y=values,
        key=key,
        label=label,
        x_axis=_condition_axis(reference=reference),
        y_axis=Axis("amount", unit=unit, label="Product amount"),
    )


def _charge(
    *,
    values: tuple[float, ...] = (-0.50, -0.75, -1.00),
    unit: str = "C",
    reference: str = "RHE",
) -> Series:
    return Series(
        x=(-0.5, -0.6, -0.7),
        y=values,
        key="charge",
        x_axis=_condition_axis(reference=reference),
        y_axis=Axis("charge", unit=unit, label="Charge"),
    )


def _product_rate(
    *,
    key: str = "CO",
    values: tuple[float, ...] = (10.0, 15.0, 20.0),
    unit: str = "nmol/s",
) -> Series:
    return Series(
        x=(-0.5, -0.6, -0.7),
        y=values,
        key=key,
        label=key,
        x_axis=_condition_axis(),
        y_axis=Axis("molar_rate", unit=unit, label="Molar rate"),
    )


def _current(
    *,
    values: tuple[float, ...] = (-10.0, -15.0, -20.0),
    unit: str = "mA",
) -> Series:
    return Series(
        x=(-0.5, -0.6, -0.7),
        y=values,
        key="current",
        x_axis=_condition_axis(),
        y_axis=Axis("current", unit=unit, label="Current"),
    )


def _fe_series(
    key: str,
    values: tuple[float, ...],
    *,
    unit: str = "%",
) -> Series:
    return Series(
        x=(-0.5, -0.6, -0.7),
        y=values,
        key=key,
        label=key,
        x_axis=_condition_axis(),
        y_axis=Axis("faradaic_efficiency", unit=unit, label="Faradaic efficiency"),
    )


def test_amount_charge_formula_matches_hand_calculation_and_preserves_sign():
    result = faradaic_efficiency_from_amount(
        1.0,
        "umol",
        -0.5,
        "C",
        electron_number=2,
    )
    expected = 2.0 * FARADAY_CONSTANT_C_MOL * 1e-6 / 0.5

    assert result.mode == "amount_charge"
    assert result.fraction.item() == pytest.approx(expected)
    assert result.percent.item() == pytest.approx(expected * 100.0)
    assert result.denominator_canonical.item() == pytest.approx(-0.5)
    assert result.canonical_product_unit == "mol"
    assert result.canonical_denominator_unit == "C"


def test_rate_current_formula_matches_hand_calculation():
    result = faradaic_efficiency_from_rate(
        10.0,
        "nmol/s",
        -10.0,
        "mA",
        electron_number=2,
    )
    expected = 2.0 * FARADAY_CONSTANT_C_MOL * 10e-9 / 0.01

    assert result.mode == "rate_current"
    assert result.fraction.item() == pytest.approx(expected)
    assert result.canonical_product_unit == "mol/s"
    assert result.canonical_denominator_unit == "A"


def test_denominator_sign_does_not_change_fe_but_is_retained():
    negative = faradaic_efficiency_from_rate(
        10.0,
        "nmol/s",
        -10.0,
        "mA",
        electron_number=2,
    )
    positive = faradaic_efficiency_from_rate(
        10.0,
        "nmol/s",
        10.0,
        "mA",
        electron_number=2,
    )

    assert negative.fraction.item() == pytest.approx(positive.fraction.item())
    assert negative.denominator_canonical.item() == pytest.approx(-0.01)
    assert positive.denominator_canonical.item() == pytest.approx(0.01)


def test_supported_units_and_scalar_broadcasting_are_canonicalized():
    result = faradaic_efficiency_from_amount(
        np.array([1.0, 2.0]),
        "umol",
        -500.0,
        "mC",
        electron_number=2,
    )

    assert result.product_canonical.tolist() == pytest.approx([1e-6, 2e-6])
    assert result.denominator_canonical.tolist() == pytest.approx([-0.5, -0.5])
    assert result.fraction.shape == (2,)


def test_result_arrays_are_immutable_and_above_100_percent_is_not_clipped():
    result = faradaic_efficiency_from_amount(
        10.0,
        "umol",
        -0.5,
        "C",
        electron_number=2,
    )

    assert result.fraction.item() > 1.0
    assert result.percent.item() > 100.0
    assert result.exceeds_unity.item() is True
    for values in (result.product_canonical, result.denominator_canonical, result.fraction):
        assert values.flags.writeable is False
        with pytest.raises(ValueError):
            values.flat[0] = 0.0


def test_invalid_low_level_inputs_fail_explicitly():
    with pytest.raises(FaradaicEfficiencyError, match="non-negative"):
        faradaic_efficiency_from_amount(
            -1.0,
            "umol",
            -1.0,
            "C",
            electron_number=2,
        )
    with pytest.raises(FaradaicEfficiencyError, match="non-zero"):
        faradaic_efficiency_from_rate(
            1.0,
            "nmol/s",
            0.0,
            "mA",
            electron_number=2,
        )
    with pytest.raises(FaradaicEfficiencyError, match="electron_number"):
        faradaic_efficiency_from_rate(
            1.0,
            "nmol/s",
            1.0,
            "mA",
            electron_number=True,  # type: ignore[arg-type]
        )
    with pytest.raises(FaradaicEfficiencyError, match="real numeric"):
        faradaic_efficiency_from_amount(
            True,
            "umol",
            1.0,
            "C",
            electron_number=2,
        )
    with pytest.raises(FaradaicEfficiencyError, match="unsupported amount unit"):
        faradaic_efficiency_from_amount(
            1.0,
            "g",
            1.0,
            "C",
            electron_number=2,
        )


def test_incompatible_broadcast_shapes_fail():
    with pytest.raises(FaradaicEfficiencyError, match="broadcast-compatible"):
        faradaic_efficiency_from_rate(
            np.ones((2, 2)),
            "nmol/s",
            np.ones(3),
            "mA",
            electron_number=2,
        )


def test_public_result_constructor_rejects_invalid_scientific_state():
    with pytest.raises(FaradaicEfficiencyError, match="mode"):
        FaradaicEfficiencyResult(
            mode="bad",  # type: ignore[arg-type]
            electron_number=2,
            product_canonical=[1e-6],
            denominator_canonical=[1.0],
        )
    with pytest.raises(FaradaicEfficiencyError, match="matching shapes"):
        FaradaicEfficiencyResult(
            mode="amount_charge",
            electron_number=2,
            product_canonical=[1e-6, 2e-6],
            denominator_canonical=[1.0],
        )


def test_series_amount_charge_preserves_condition_axis_identity_and_provenance():
    product = _product_amount()
    denominator = _charge()
    output = faradaic_efficiency_series(
        product,
        denominator,
        electron_number=2,
    )

    assert output.key == "CO"
    assert output.label == "CO"
    assert output.x_axis.equals(product.x_axis)
    assert output.y_axis.name == "faradaic_efficiency"
    assert output.y_axis.unit == "%"
    assert output.metadata["mode"] == "amount_charge"
    assert output.metadata["electron_number"] == 2
    assert output.metadata["product_source"]["sha256"] == series_data_sha256(product)
    assert output.metadata["denominator_source"]["sha256"] == series_data_sha256(
        denominator
    )
    denominator_values = output.metadata["denominator_canonical_values"]
    assert np.asarray(denominator_values).tolist() == pytest.approx([-0.5, -0.75, -1.0])


def test_series_rate_current_supports_fraction_output():
    output = faradaic_efficiency_series(
        _product_rate(),
        _current(),
        electron_number=2,
        output_unit="fraction",
    )

    assert output.y_axis.unit == "fraction"
    assert output.y.tolist() == pytest.approx(
        [2 * FARADAY_CONSTANT_C_MOL * 10e-9 / 0.01] * 3
    )


def test_series_semantics_and_condition_mismatch_fail_explicitly():
    wrong_product = Series(
        x=(-0.5, -0.6, -0.7),
        y=(1.0, 1.0, 1.0),
        key="CO",
        x_axis=_condition_axis(),
        y_axis=Axis("concentration", unit="umol"),
    )
    with pytest.raises(FaradaicEfficiencyError, match="semantics"):
        faradaic_efficiency_series(
            wrong_product,
            _charge(),
            electron_number=2,
        )

    mismatched_x = Series(
        x=(-0.5, -0.6, -0.8),
        y=(-0.5, -0.75, -1.0),
        key="charge",
        x_axis=_condition_axis(),
        y_axis=Axis("charge", unit="C"),
    )
    with pytest.raises(FaradaicEfficiencyError, match="condition values"):
        faradaic_efficiency_series(
            _product_amount(),
            mismatched_x,
            electron_number=2,
        )

    with pytest.raises(FaradaicEfficiencyError, match="reference"):
        faradaic_efficiency_series(
            _product_amount(reference="RHE"),
            _charge(reference="SHE"),
            electron_number=2,
        )


def test_series_output_unit_is_explicit():
    with pytest.raises(FaradaicEfficiencyError, match="output_unit"):
        faradaic_efficiency_series(
            _product_amount(),
            _charge(),
            electron_number=2,
            output_unit="percent",  # type: ignore[arg-type]
        )


def test_multi_product_dataset_preserves_order_keys_labels_and_stoichiometry():
    products = Dataset(
        [
            _product_rate(key="CO", values=(10.0, 10.0, 10.0)),
            _product_rate(key="CH4", values=(2.0, 2.0, 2.0)),
        ]
    )
    output = faradaic_efficiency_dataset(
        products,
        _current(values=(-20.0, -20.0, -20.0)),
        {"CO": 2, "CH4": 8},
    )

    assert [item.key for item in output] == ["CO", "CH4"]
    assert [item.label for item in output] == ["CO", "CH4"]
    assert [item.metadata["electron_number"] for item in output] == [2, 8]
    assert output[0].y[0] == pytest.approx(
        100.0 * 2 * FARADAY_CONSTANT_C_MOL * 10e-9 / 0.02
    )
    assert output[1].y[0] == pytest.approx(
        100.0 * 8 * FARADAY_CONSTANT_C_MOL * 2e-9 / 0.02
    )


def test_multi_product_dataset_requires_complete_stable_key_mapping():
    products = Dataset([_product_rate(key="CO"), _product_rate(key="CH4")])
    with pytest.raises(FaradaicEfficiencyError, match="missing"):
        faradaic_efficiency_dataset(products, _current(), {"CO": 2})
    with pytest.raises(FaradaicEfficiencyError, match="unknown"):
        faradaic_efficiency_dataset(
            products,
            _current(),
            {"CO": 2, "CH4": 8, "H2": 2},
        )
    with pytest.raises(FaradaicEfficiencyError, match="non-empty"):
        faradaic_efficiency_dataset(
            Dataset([_product_rate(key="")]),
            _current(),
            {"CO": 2},
        )


def test_closure_reports_total_without_clipping_or_renormalization():
    data = Dataset(
        [
            _fe_series("CO", (60.0, 80.0, 30.0)),
            _fe_series("H2", (50.0, 25.0, 70.0)),
        ]
    )
    closure = faradaic_efficiency_closure(data)

    assert closure.total_fraction.tolist() == pytest.approx([1.10, 1.05, 1.00])
    assert closure.total_percent.tolist() == pytest.approx([110.0, 105.0, 100.0])
    assert closure.exceeds_limit.tolist() == [True, True, False]
    assert closure.any_exceeds_limit is True
    assert closure.max_fraction == pytest.approx(1.10)
    assert closure.product_keys == ("CO", "H2")


def test_closure_tolerance_and_strict_policy_are_explicit():
    data = Dataset(
        [
            _fe_series("CO", (100.00005, 100.0002, 99.0)),
        ]
    )
    report = faradaic_efficiency_closure(data, tolerance_fraction=1e-6)
    assert report.exceeds_limit.tolist() == [False, True, False]

    with pytest.raises(FaradaicEfficiencyError, match="closure limit"):
        faradaic_efficiency_closure(
            data,
            tolerance_fraction=1e-6,
            strict=True,
        )


def test_closure_accepts_fraction_and_rejects_bad_fe_data():
    fraction = _fe_series("CO", (0.5, 0.6, 0.7), unit="fraction")
    closure = faradaic_efficiency_closure(fraction)
    assert closure.total_fraction.tolist() == pytest.approx([0.5, 0.6, 0.7])

    wrong = Series(
        x=(-0.5, -0.6, -0.7),
        y=(50.0, 50.0, 50.0),
        key="x",
        x_axis=_condition_axis(),
        y_axis=Axis("selectivity", unit="%"),
    )
    with pytest.raises(FaradaicEfficiencyError, match="faradaic_efficiency"):
        faradaic_efficiency_closure(wrong)

    with pytest.raises(FaradaicEfficiencyError, match="non-negative"):
        faradaic_efficiency_closure(_fe_series("CO", (-1.0, 2.0, 3.0)))


def test_plot_fe_reuses_shared_scatter_and_curve_renderers():
    data = _fe_series("CO", (20.0, 40.0, 60.0))
    spec = FigureSpec().with_series_style("CO", marker="s")
    _, scatter_ax = plot_faradaic_efficiency(
        data,
        spec,
        errors=ScatterError(yerr=(1.0, 1.0, 1.0)),
    )
    assert len(scatter_ax.collections) >= 1
    assert scatter_ax.get_ylabel() == "Faradaic efficiency (%)"

    _, curve_ax = plot_faradaic_efficiency(data, kind="curve")
    assert len(curve_ax.lines) == 1
    with pytest.raises(FaradaicEfficiencyError, match="only with kind='scatter'"):
        plot_faradaic_efficiency(
            data,
            kind="curve",
            errors=ScatterError(yerr=(1.0, 1.0, 1.0)),
        )


def test_numerical_echem_import_remains_matplotlib_lazy_in_fresh_interpreter():
    code = (
        "import sys; import catalysis_workbench.experimental.echem; "
        "assert 'matplotlib' not in sys.modules"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
