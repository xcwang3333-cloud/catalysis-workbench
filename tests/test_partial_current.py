"""Scientific contract tests for product partial current density."""

from __future__ import annotations

import subprocess
import sys

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.experimental.echem import (
    PartialCurrentClosureError,
    PartialCurrentClosureResult,
    PartialCurrentDensityError,
    PartialCurrentDensityResult,
    partial_current_closure,
    partial_current_closure_dataset,
    partial_current_density,
    partial_current_density_dataset,
    partial_current_density_series,
    series_data_sha256,
)


def _condition_axis(*, reference: str = "RHE", normalization: str | None = None) -> Axis:
    metadata = {"reference": reference}
    if normalization is not None:
        metadata["normalization"] = normalization
    return Axis("potential", unit="V", label="Potential", metadata=metadata)


def _total_current(
    *,
    values: tuple[float, ...] = (-20.0, -50.0, -80.0),
    unit: str = "mA cm^-2",
    reference: str = "RHE",
    normalization: str = "geometric_area",
) -> Series:
    return Series(
        x=(-0.5, -0.6, -0.7),
        y=values,
        key="total",
        label="Total",
        x_axis=_condition_axis(reference=reference),
        y_axis=Axis(
            "current_density",
            unit=unit,
            label="Current density",
            metadata={"normalization": normalization},
        ),
    )


def _fe(
    key: str = "CO",
    values: tuple[float, ...] = (80.0, 90.0, 95.0),
    *,
    unit: str = "%",
    reference: str = "RHE",
) -> Series:
    return Series(
        x=(-0.5, -0.6, -0.7),
        y=values,
        key=key,
        label=key,
        x_axis=_condition_axis(reference=reference),
        y_axis=Axis("faradaic_efficiency", unit=unit, label="Faradaic efficiency"),
    )


def test_signed_partial_current_preserves_cathodic_sign():
    result = partial_current_density([-100.0], [0.95])
    assert result.values.tolist() == pytest.approx([-95.0])
    assert result.sign_mode == "signed"


def test_magnitude_partial_current_returns_absolute_value():
    result = partial_current_density([-100.0, 50.0], [0.95, 0.5], sign_mode="magnitude")
    assert result.values.tolist() == pytest.approx([95.0, 25.0])


def test_percent_fe_is_explicitly_converted_and_above_100_is_visible():
    result = partial_current_density([-100.0, -100.0], [95.0, 105.0], fe_unit="%")
    assert result.fe_fraction.tolist() == pytest.approx([0.95, 1.05])
    assert result.values.tolist() == pytest.approx([-95.0, -105.0])
    assert result.fe_exceeds_unity.tolist() == [False, True]


def test_scalar_broadcasting_is_supported_but_incompatible_shapes_fail():
    result = partial_current_density([-10.0, -20.0], 0.5)
    assert result.values.tolist() == pytest.approx([-5.0, -10.0])
    with pytest.raises(PartialCurrentDensityError, match="broadcast-compatible"):
        partial_current_density([1.0, 2.0], [0.5, 0.5, 0.5])


@pytest.mark.parametrize("bad", ["0.5", True, 1 + 2j, np.nan, np.inf])
def test_low_level_boundary_rejects_non_real_or_nonfinite_fe(bad):
    with pytest.raises(PartialCurrentDensityError, match="real numeric|finite"):
        partial_current_density([-1.0], [bad])


def test_negative_fe_and_invalid_modes_fail_explicitly():
    with pytest.raises(PartialCurrentDensityError, match="cannot be negative"):
        partial_current_density([1.0], [-0.1])
    with pytest.raises(PartialCurrentDensityError, match="fe_unit"):
        partial_current_density([1.0], [50.0], fe_unit="percent")  # type: ignore[arg-type]
    with pytest.raises(PartialCurrentDensityError, match="sign_mode"):
        partial_current_density([1.0], [0.5], sign_mode="auto")  # type: ignore[arg-type]


def test_public_result_constructor_enforces_scientific_state_and_immutability():
    result = PartialCurrentDensityResult(
        total_current_density=[-2.0, -4.0],
        fe_fraction=[0.5, 0.25],
        sign_mode="signed",
    )
    assert result.values.tolist() == pytest.approx([-1.0, -1.0])
    assert result.total_current_density.flags.writeable is False
    assert result.fe_fraction.flags.writeable is False
    assert result.values.flags.writeable is False
    with pytest.raises(PartialCurrentDensityError, match="matching shapes"):
        PartialCurrentDensityResult([-1.0, -2.0], [0.5])


def test_series_adapter_preserves_product_identity_axis_basis_and_provenance():
    current = _total_current()
    fe = _fe()
    output = partial_current_density_series(current, fe)

    assert output.key == "CO"
    assert output.label == "CO"
    assert output.x_axis.equals(current.x_axis)
    assert output.y_axis.name == "partial_current_density"
    assert output.y_axis.unit == current.y_axis.unit
    assert output.y_axis.metadata["normalization"] == "geometric_area"
    assert output.y.tolist() == pytest.approx([-16.0, -45.0, -76.0])
    assert output.metadata["sign_mode"] == "signed"
    assert output.metadata["current_source"]["sha256"] == series_data_sha256(current)
    assert output.metadata["fe_source"]["sha256"] == series_data_sha256(fe)


def test_series_adapter_magnitude_mode_is_explicit_in_values_and_provenance():
    output = partial_current_density_series(_total_current(), _fe(), sign_mode="magnitude")
    assert output.y.tolist() == pytest.approx([16.0, 45.0, 76.0])
    assert output.metadata["sign_mode"] == "magnitude"


def test_series_adapter_rejects_wrong_semantics_or_unsupported_units():
    wrong_current = _total_current()
    wrong_current = Series(
        x=wrong_current.x,
        y=wrong_current.y,
        x_axis=wrong_current.x_axis,
        y_axis=Axis("current", unit="mA"),
    )
    with pytest.raises(PartialCurrentDensityError, match="current_density"):
        partial_current_density_series(wrong_current, _fe())

    with pytest.raises(PartialCurrentDensityError, match="unsupported current density unit"):
        partial_current_density_series(_total_current(unit="A/m^2"), _fe())

    wrong_fe = Series(
        x=_fe().x,
        y=_fe().y,
        key="CO",
        x_axis=_fe().x_axis,
        y_axis=Axis("selectivity", unit="%"),
    )
    with pytest.raises(PartialCurrentDensityError, match="faradaic_efficiency"):
        partial_current_density_series(_total_current(), wrong_fe)


def test_series_condition_mismatch_and_reference_mismatch_fail_without_alignment():
    fe = _fe()
    shifted = Series(
        x=(-0.5, -0.61, -0.7),
        y=fe.y,
        key=fe.key,
        label=fe.label,
        x_axis=fe.x_axis,
        y_axis=fe.y_axis,
    )
    with pytest.raises(PartialCurrentDensityError, match="match exactly"):
        partial_current_density_series(_total_current(), shifted)
    with pytest.raises(PartialCurrentDensityError, match="reference"):
        partial_current_density_series(_total_current(reference="RHE"), _fe(reference="SHE"))


def test_multi_product_dataset_preserves_order_keys_labels_and_per_series_fe_units():
    data = Dataset(
        [
            _fe("CO", (80.0, 90.0, 95.0), unit="%"),
            _fe("H2", (0.20, 0.10, 0.05), unit="fraction"),
        ],
        name="products",
    )
    output = partial_current_density_dataset(_total_current(), data)
    assert output.keys == ("CO", "H2")
    assert output.labels == ("CO", "H2")
    assert output[0].y.tolist() == pytest.approx([-16.0, -45.0, -76.0])
    assert output[1].y.tolist() == pytest.approx([-4.0, -5.0, -4.0])
    assert output.metadata["product_keys"] == ("CO", "H2")


def test_multi_product_dataset_requires_nonempty_stable_keys():
    fe = _fe(key="")
    with pytest.raises(PartialCurrentDensityError, match="non-empty"):
        partial_current_density_dataset(_total_current(), Dataset([fe]))


def test_signed_closure_reports_error_without_renormalizing():
    result = partial_current_closure(
        [-100.0, -100.0],
        [[-60.0, -60.0], [-50.0, -40.0]],
        tolerance_fraction=0.05,
    )
    assert result.summed_partial_current_density.tolist() == pytest.approx([-110.0, -100.0])
    assert result.residual.tolist() == pytest.approx([-10.0, 0.0])
    assert result.absolute_error.tolist() == pytest.approx([10.0, 0.0])
    assert result.relative_error.tolist() == pytest.approx([0.10, 0.0])
    assert result.passed.tolist() == [False, True]
    assert result.all_passed is False


def test_magnitude_closure_is_explicit_and_handles_zero_total_deterministically():
    result = partial_current_closure(
        [-100.0, 0.0],
        [[-60.0, 0.0], [-40.0, 1.0]],
        comparison_mode="magnitude",
    )
    assert result.total_current_density.tolist() == pytest.approx([100.0, 0.0])
    assert result.summed_partial_current_density.tolist() == pytest.approx([100.0, 1.0])
    assert result.relative_error[0] == pytest.approx(0.0)
    assert np.isinf(result.relative_error[1])
    assert result.passed.tolist() == [True, False]


def test_public_closure_result_rejects_inconsistent_relative_error():
    with pytest.raises(PartialCurrentClosureError, match="relative_error"):
        PartialCurrentClosureResult(
            total_current_density=[-100.0],
            summed_partial_current_density=[-90.0],
            residual=[10.0],
            absolute_error=[10.0],
            relative_error=[0.01],
            tolerance_fraction=0.05,
            passed=[True],
        )


def test_dataset_closure_retains_source_digests_and_validates_units():
    current = _total_current()
    partial = partial_current_density_dataset(
        current,
        Dataset([_fe("CO", (80.0, 90.0, 95.0)), _fe("H2", (20.0, 10.0, 5.0))]),
    )
    closure = partial_current_closure_dataset(current, partial)
    assert closure.all_passed is True
    assert closure.total_source is not None
    assert closure.total_source.sha256 == series_data_sha256(current)
    assert tuple(source.key for source in closure.partial_sources) == ("CO", "H2")

    bad = partial[0]
    bad = Series(
        x=bad.x,
        y=bad.y,
        key=bad.key,
        x_axis=bad.x_axis,
        y_axis=Axis("partial_current_density", unit="A cm^-2"),
    )
    with pytest.raises(PartialCurrentClosureError, match="units must match"):
        partial_current_closure_dataset(current, Dataset([bad]))


def test_dataset_closure_rejects_mismatched_total_current_provenance():
    source_current = _total_current()
    partial = partial_current_density_dataset(
        source_current,
        Dataset([_fe("CO", (100.0, 100.0, 100.0))]),
    )
    other_current = _total_current(values=(-10.0, -25.0, -40.0))

    with pytest.raises(PartialCurrentClosureError, match="current_source provenance"):
        partial_current_closure_dataset(other_current, partial)


def test_dataset_closure_rejects_current_density_normalization_mismatch():
    current = _total_current()
    partial = partial_current_density_series(current, _fe(values=(100.0, 100.0, 100.0)))
    mismatched = Series(
        x=partial.x,
        y=partial.y,
        key=partial.key,
        label=partial.label,
        x_axis=partial.x_axis,
        y_axis=Axis(
            "partial_current_density",
            unit=partial.y_axis.unit,
            label=partial.y_axis.label,
            metadata={"normalization": "ecsa"},
        ),
        metadata=partial.metadata_dict(),
    )

    with pytest.raises(PartialCurrentClosureError, match="normalization metadata differ"):
        partial_current_closure_dataset(current, Dataset([mismatched]))


def test_numerical_echem_import_remains_matplotlib_lazy():
    code = (
        "import sys; "
        "import catalysis_workbench.experimental.echem as e; "
        "assert hasattr(e, 'partial_current_density'); "
        "assert 'matplotlib' not in sys.modules"
    )
    subprocess.run([sys.executable, "-c", code], check=True)
