"""Scientific contract tests for explicit electrochemical activity normalization."""

from __future__ import annotations

import subprocess
import sys

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.experimental.echem import (
    ActivityNormalizationError,
    ActivityNormalizationResult,
    normalize_activity,
    normalize_activity_dataset,
    normalize_activity_series,
    partial_current_density_series,
    series_data_sha256,
)


def _potential_axis() -> Axis:
    return Axis("potential", unit="V", label="Potential", metadata={"reference": "RHE"})


def _current(
    key: str = "cat-a",
    *,
    values: tuple[float, ...] = (-2.0, -4.0),
    label: str = "Catalyst",
) -> Series:
    return Series(
        x=(-0.6, -0.7),
        y=values,
        key=key,
        label=label,
        x_axis=_potential_axis(),
        y_axis=Axis("current", unit="mA", label="Current"),
    )


def _density(
    key: str = "cat-a",
    *,
    values: tuple[float, ...] = (-10.0, -20.0),
    area_cm2: float = 0.2,
    normalization: str = "geometric_area",
) -> Series:
    return Series(
        x=(-0.6, -0.7),
        y=values,
        key=key,
        label="Catalyst",
        x_axis=_potential_axis(),
        y_axis=Axis(
            "current_density",
            unit="mA/cm^2",
            label="Current density",
            metadata={
                "normalization": normalization,
                "electrode_area_cm2": area_cm2,
            },
        ),
    )


def test_total_current_mass_activity_and_mass_output_units_are_hand_calculated():
    common = dict(
        current=[-2.0],
        current_unit="mA",
        current_basis="current",
        basis="catalyst_mass",
        denominator_value=2.0,
        denominator_unit="mg",
    )
    assert normalize_activity(**common, output_unit="A/g").values.tolist() == pytest.approx([-1.0])
    assert normalize_activity(
        **common, output_unit="mA/mg"
    ).values.tolist() == pytest.approx([-1.0])
    assert normalize_activity(
        **common, output_unit="A/mg"
    ).values.tolist() == pytest.approx([-0.001])
    assert normalize_activity(
        **common, output_unit="mA/g"
    ).values.tolist() == pytest.approx([-1000.0])


def test_one_a_per_g_equals_one_ma_per_mg():
    a_per_g = normalize_activity(
        [1.0],
        current_unit="A",
        current_basis="current",
        basis="catalyst_mass",
        denominator_value=1.0,
        denominator_unit="g",
        output_unit="A/g",
    )
    ma_per_mg = normalize_activity(
        [1.0],
        current_unit="A",
        current_basis="current",
        basis="catalyst_mass",
        denominator_value=1.0,
        denominator_unit="g",
        output_unit="mA/mg",
    )
    assert a_per_g.values.item() == pytest.approx(1.0)
    assert ma_per_mg.values.item() == pytest.approx(1.0)


def test_geometric_density_reconstruction_matches_direct_total_current():
    direct = normalize_activity(
        [-2.0],
        current_unit="mA",
        current_basis="current",
        basis="catalyst_mass",
        denominator_value=2.0,
        denominator_unit="mg",
    )
    reconstructed = normalize_activity(
        [-10.0],
        current_unit="mA/cm^2",
        current_basis="current_density",
        geometric_area_value=0.2,
        geometric_area_unit="cm^2",
        basis="catalyst_mass",
        denominator_value=2.0,
        denominator_unit="mg",
    )
    assert reconstructed.total_current_a.tolist() == pytest.approx([-0.002])
    assert reconstructed.values.tolist() == pytest.approx(direct.values.tolist())


def test_ecsa_activity_from_current_and_density_is_explicit_and_equivalent():
    direct = normalize_activity(
        [-2.0],
        current_unit="mA",
        current_basis="current",
        basis="ecsa",
        denominator_value=4.0,
        denominator_unit="cm^2",
        output_unit="mA/cm^2",
    )
    reconstructed = normalize_activity(
        [-10.0],
        current_unit="mA/cm^2",
        current_basis="current_density",
        geometric_area_value=0.2,
        geometric_area_unit="cm^2",
        basis="ecsa",
        denominator_value=4.0,
        denominator_unit="cm^2",
        output_unit="mA/cm^2",
    )
    assert direct.values.tolist() == pytest.approx([-0.5])
    assert reconstructed.values.tolist() == pytest.approx([-0.5])


def test_sign_mode_preserves_direction_unless_magnitude_is_explicit():
    signed = normalize_activity(
        [-2.0, 2.0],
        current_unit="mA",
        current_basis="current",
        basis="metal_mass",
        denominator_value=2.0,
        denominator_unit="mg",
    )
    magnitude = normalize_activity(
        [-2.0, 2.0],
        current_unit="mA",
        current_basis="current",
        basis="metal_mass",
        denominator_value=2.0,
        denominator_unit="mg",
        sign_mode="magnitude",
    )
    assert signed.values.tolist() == pytest.approx([-1.0, 1.0])
    assert magnitude.values.tolist() == pytest.approx([1.0, 1.0])


@pytest.mark.parametrize("bad", [0.0, -1.0, np.nan, np.inf, True, "2"])
def test_invalid_denominators_fail_explicitly(bad):
    with pytest.raises(ActivityNormalizationError, match="denominator_value"):
        normalize_activity(
            [-2.0],
            current_unit="mA",
            current_basis="current",
            basis="catalyst_mass",
            denominator_value=bad,  # type: ignore[arg-type]
            denominator_unit="mg",
        )


def test_units_current_basis_and_geometry_misuse_fail_explicitly():
    with pytest.raises(ActivityNormalizationError, match="unsupported mass unit"):
        normalize_activity(
            [-2.0],
            current_unit="mA",
            current_basis="current",
            basis="catalyst_mass",
            denominator_value=2.0,
            denominator_unit="cm^2",
        )
    with pytest.raises(ActivityNormalizationError, match="output_unit"):
        normalize_activity(
            [-2.0],
            current_unit="mA",
            current_basis="current",
            basis="catalyst_mass",
            denominator_value=2.0,
            denominator_unit="mg",
            output_unit="A/cm^2",
        )
    with pytest.raises(ActivityNormalizationError, match="required for current-density"):
        normalize_activity(
            [-10.0],
            current_unit="mA/cm^2",
            current_basis="current_density",
            basis="catalyst_mass",
            denominator_value=2.0,
            denominator_unit="mg",
        )
    with pytest.raises(ActivityNormalizationError, match="must not be supplied"):
        normalize_activity(
            [-2.0],
            current_unit="mA",
            current_basis="current",
            geometric_area_value=0.2,
            geometric_area_unit="cm^2",
            basis="catalyst_mass",
            denominator_value=2.0,
            denominator_unit="mg",
        )
    with pytest.raises(ActivityNormalizationError, match="real numeric"):
        normalize_activity(
            ["-2"],
            current_unit="mA",
            current_basis="current",
            basis="catalyst_mass",
            denominator_value=2.0,
            denominator_unit="mg",
        )


def test_public_result_is_immutable_and_rejects_inconsistent_canonical_state():
    result = ActivityNormalizationResult(
        source_current_basis="current",
        source_current_unit="mA",
        source_current_canonical=[-0.002],
        total_current_a=[-0.002],
        basis="catalyst_mass",
        denominator_value=2.0,
        denominator_unit="mg",
        denominator_canonical_value=0.002,
        output_unit="A/g",
    )
    assert result.source_current_canonical.flags.writeable is False
    assert result.total_current_a.flags.writeable is False
    assert result.values.flags.writeable is False
    with pytest.raises(ActivityNormalizationError, match="denominator_canonical_value"):
        ActivityNormalizationResult(
            source_current_basis="current",
            source_current_unit="mA",
            source_current_canonical=[-0.002],
            total_current_a=[-0.002],
            basis="catalyst_mass",
            denominator_value=2.0,
            denominator_unit="mg",
            denominator_canonical_value=2.0,
            output_unit="A/g",
        )
    with pytest.raises(ActivityNormalizationError, match="total_current_a"):
        ActivityNormalizationResult(
            source_current_basis="current_density",
            source_current_unit="mA/cm^2",
            source_current_canonical=[-0.010],
            total_current_a=[-0.003],
            geometric_area_cm2=0.2,
            basis="catalyst_mass",
            denominator_value=2.0,
            denominator_unit="mg",
            denominator_canonical_value=0.002,
            output_unit="A/g",
        )


def test_series_adapter_records_basis_axis_metadata_and_source_provenance():
    source = _current()
    output = normalize_activity_series(
        source,
        basis="catalyst_mass",
        denominator_value=2.0,
        denominator_unit="mg",
    )
    assert output.key == source.key
    assert output.label == source.label
    assert output.x_axis.equals(source.x_axis)
    assert output.y_axis.name == "activity"
    assert output.y_axis.unit == "A/g"
    assert output.y_axis.metadata["normalization"] == "catalyst_mass"
    assert output.y.tolist() == pytest.approx([-1.0, -2.0])
    assert output.metadata["source"]["sha256"] == series_data_sha256(source)
    assert output.metadata["basis"] == "catalyst_mass"
    assert output.metadata["denominator_canonical_unit"] == "g"
    assert output.metadata["provenance"].parameters


def test_density_series_requires_geometric_basis_and_matching_area():
    output = normalize_activity_series(
        _density(),
        basis="catalyst_mass",
        denominator_value=2.0,
        denominator_unit="mg",
        geometric_area_value=0.2,
        geometric_area_unit="cm^2",
    )
    assert output.y.tolist() == pytest.approx([-1.0, -2.0])
    assert output.metadata["geometric_area_cm2"] == pytest.approx(0.2)

    with pytest.raises(ActivityNormalizationError, match="conflicts"):
        normalize_activity_series(
            _density(),
            basis="catalyst_mass",
            denominator_value=2.0,
            denominator_unit="mg",
            geometric_area_value=0.3,
            geometric_area_unit="cm^2",
        )
    with pytest.raises(ActivityNormalizationError, match="geometric-area normalization"):
        normalize_activity_series(
            _density(normalization="ecsa"),
            basis="catalyst_mass",
            denominator_value=2.0,
            denominator_unit="mg",
            geometric_area_value=0.2,
            geometric_area_unit="cm^2",
        )


def test_partial_current_density_requires_issue_23_provenance_before_normalization():
    total = _density(key="total")
    fe = Series(
        x=total.x,
        y=(50.0, 25.0),
        key="CO",
        label="CO",
        x_axis=total.x_axis,
        y_axis=Axis("faradaic_efficiency", unit="%"),
    )
    partial = partial_current_density_series(total, fe)
    output = normalize_activity_series(
        partial,
        basis="metal_mass",
        denominator_value=1.0,
        denominator_unit="mg",
        geometric_area_value=0.2,
        geometric_area_unit="cm^2",
    )
    assert output.y.tolist() == pytest.approx([-1.0, -1.0])
    assert output.metadata["current_source"]
    assert output.metadata["fe_source"]

    fake = Series(
        x=partial.x,
        y=partial.y,
        key="fake",
        x_axis=partial.x_axis,
        y_axis=partial.y_axis,
    )
    with pytest.raises(ActivityNormalizationError, match="Issue #23"):
        normalize_activity_series(
            fake,
            basis="metal_mass",
            denominator_value=1.0,
            denominator_unit="mg",
            geometric_area_value=0.2,
            geometric_area_unit="cm^2",
        )


def test_dataset_denominators_are_exactly_keyed_not_label_keyed():
    dataset = Dataset(
        [
            _current("a", values=(-1.0, -2.0), label="Same label"),
            _current("b", values=(-2.0, -4.0), label="Same label"),
        ]
    )
    output = normalize_activity_dataset(
        dataset,
        {"a": (1.0, "mg"), "b": (2.0, "mg")},
        basis="catalyst_mass",
    )
    assert output.keys == ("a", "b")
    assert output.labels == ("Same label", "Same label")
    assert output[0].y.tolist() == pytest.approx([-1.0, -2.0])
    assert output[1].y.tolist() == pytest.approx([-1.0, -2.0])

    with pytest.raises(ActivityNormalizationError, match="missing Series.key"):
        normalize_activity_dataset(
            dataset,
            {"a": (1.0, "mg")},
            basis="catalyst_mass",
        )
    with pytest.raises(ActivityNormalizationError, match="unknown Series.key"):
        normalize_activity_dataset(
            dataset,
            {"a": (1.0, "mg"), "b": (2.0, "mg"), "c": (3.0, "mg")},
            basis="catalyst_mass",
        )


def test_density_dataset_requires_exact_keyed_geometric_areas():
    dataset = Dataset([_density("a"), _density("b", area_cm2=0.4)])
    output = normalize_activity_dataset(
        dataset,
        {"a": (2.0, "mg"), "b": (4.0, "mg")},
        basis="catalyst_mass",
        geometric_areas={"a": (0.2, "cm^2"), "b": (0.4, "cm^2")},
    )
    assert output[0].y.tolist() == pytest.approx([-1.0, -2.0])
    assert output[1].y.tolist() == pytest.approx([-1.0, -2.0])

    with pytest.raises(ActivityNormalizationError, match="geometric_areas is required"):
        normalize_activity_dataset(
            dataset,
            {"a": (2.0, "mg"), "b": (4.0, "mg")},
            basis="catalyst_mass",
        )


def test_numerical_echem_import_remains_matplotlib_lazy():
    code = (
        "import sys; "
        "import catalysis_workbench.experimental.echem as e; "
        "assert hasattr(e, 'normalize_activity'); "
        "assert 'matplotlib' not in sys.modules"
    )
    subprocess.run([sys.executable, "-c", code], check=True)
