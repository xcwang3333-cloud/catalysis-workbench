import numpy as np
import pytest

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.experimental.echem import (
    LSVError,
    LSVProcessingConfig,
    convert_potential_to_rhe,
    correct_ir_drop,
    process_lsv,
    process_lsv_dataset,
    rhe_offset_from_she,
    to_current_density,
)


def _lsv(
    *,
    x=(-0.6, -0.5, -0.4),
    y=(-1.0, -2.0, -3.0),
    x_unit="V",
    y_unit="mA",
    key="sample",
    label="Sample",
):
    return Series(
        x=x,
        y=y,
        label=label,
        key=key,
        x_axis=Axis("potential", unit=x_unit, label="Potential"),
        y_axis=Axis("current", unit=y_unit, label="Current"),
        metadata={"source": {"file_name": "lsv.csv"}},
    )


def test_rhe_offset_from_she_uses_nernst_ph_term():
    offset = rhe_offset_from_she(0.197, 13.0, temperature_k=298.15)
    assert offset == pytest.approx(0.9659, abs=5e-4)


def test_rhe_offset_rejects_invalid_temperature_and_nonfinite_inputs():
    with pytest.raises(LSVError, match="temperature"):
        rhe_offset_from_she(0.197, 13.0, temperature_k=0)
    with pytest.raises(LSVError, match="finite"):
        rhe_offset_from_she(np.nan, 13.0)


def test_convert_potential_to_rhe_converts_mv_and_records_reference():
    source = _lsv(x=(-600, -500, -400), x_unit="mV")
    result = convert_potential_to_rhe(source, offset_v=0.9, source_reference="Ag/AgCl")

    np.testing.assert_allclose(result.x, [0.3, 0.4, 0.5])
    assert result.x_axis.name == "potential"
    assert result.x_axis.unit == "V"
    assert result.x_axis.metadata["reference"] == "RHE"
    assert result.x_axis.metadata["source_reference"] == "Ag/AgCl"
    assert result.metadata["source"]["file_name"] == "lsv.csv"
    assert result.key == source.key
    record = result.metadata["processing_history"][-1]
    assert record["operation"] == "echem.convert_potential_to_rhe"
    assert record["parameters"]["source_reference"] == "Ag/AgCl"


def test_convert_potential_to_rhe_rejects_missing_or_unsupported_units():
    with pytest.raises(LSVError, match="unit is required"):
        convert_potential_to_rhe(_lsv(x_unit=None), offset_v=0.9)
    with pytest.raises(LSVError, match="unsupported potential"):
        convert_potential_to_rhe(_lsv(x_unit="kV"), offset_v=0.9)


def test_convert_potential_to_rhe_rejects_repeated_conversion():
    first = convert_potential_to_rhe(_lsv(), offset_v=0.9, source_reference="Ag/AgCl")
    with pytest.raises(LSVError, match="already"):
        convert_potential_to_rhe(first, offset_v=0.1, source_reference="SCE")


def test_convert_potential_to_rhe_rejects_contradictory_reference_metadata():
    source = Series(
        x=(-0.6, -0.5),
        y=(-1.0, -2.0),
        x_axis=Axis(
            "potential",
            unit="V",
            label="Potential",
            metadata={"reference": "Ag/AgCl (3 M KCl)"},
        ),
        y_axis=Axis("current", unit="mA", label="Current"),
    )
    with pytest.raises(LSVError, match="contradicts"):
        convert_potential_to_rhe(source, offset_v=0.9, source_reference="SCE")


def test_convert_potential_to_rhe_uses_declared_source_reference_when_not_repeated():
    source = Series(
        x=(-0.6,),
        y=(-1.0,),
        x_axis=Axis(
            "potential",
            unit="V",
            label="Potential",
            metadata={"reference": "Ag/AgCl"},
        ),
        y_axis=Axis("current", unit="mA", label="Current"),
    )
    result = convert_potential_to_rhe(source, offset_v=0.9)
    record = result.metadata["processing_history"][-1]
    assert record["parameters"]["source_reference"] == "Ag/AgCl"


def test_ir_correction_uses_signed_current_for_cathodic_and_anodic_data():
    source = _lsv(x=(-0.5, -0.5), y=(-2.0, 2.0), y_unit="mA")
    result = correct_ir_drop(source, resistance_ohm=10.0)

    np.testing.assert_allclose(result.x, [-0.48, -0.52])
    np.testing.assert_allclose(result.y, source.y)
    assert result.x_axis.unit == "V"
    assert result.x_axis.metadata["ir_corrected"] is True


def test_ir_correction_supports_partial_compensation():
    source = _lsv(x=(-0.5,), y=(-2.0,), y_unit="mA")
    result = correct_ir_drop(
        source,
        resistance_ohm=10.0,
        correction_fraction=0.5,
    )

    np.testing.assert_allclose(result.x, [-0.49])
    record = result.metadata["processing_history"][-1]
    assert record["parameters"]["correction_fraction"] == pytest.approx(0.5)


def test_ir_correction_reconstructs_current_from_current_density_and_area():
    source = _lsv(x=(-0.5,), y=(-10.0,), y_unit="mA/cm^2")
    result = correct_ir_drop(
        source,
        resistance_ohm=10.0,
        electrode_area_cm2=0.2,
    )

    np.testing.assert_allclose(result.x, [-0.48])
    record = result.metadata["processing_history"][-1]
    assert record["parameters"]["current_kind"] == "current_density"
    assert record["parameters"]["electrode_area_cm2"] == pytest.approx(0.2)
    assert record["parameters"]["density_area_basis"] == "geometric_area_explicit_assumption"


def test_ir_correction_accepts_declared_geometric_density_basis():
    source = Series(
        x=(-0.5,),
        y=(-10.0,),
        x_axis=Axis("potential", unit="V", label="Potential"),
        y_axis=Axis(
            "current_density",
            unit="mA/cm^2",
            label="Current density",
            metadata={"normalization": "geometric_area"},
        ),
    )
    result = correct_ir_drop(source, resistance_ohm=10.0, electrode_area_cm2=0.2)
    record = result.metadata["processing_history"][-1]
    assert record["parameters"]["density_area_basis"] == "geometric_area_declared"


def test_ir_correction_rejects_non_geometric_density_basis():
    source = Series(
        x=(-0.5,),
        y=(-10.0,),
        x_axis=Axis("potential", unit="V", label="Potential"),
        y_axis=Axis(
            "current_density",
            unit="mA/cm^2",
            label="Current density",
            metadata={"normalization": "ECSA"},
        ),
    )
    with pytest.raises(LSVError, match="geometric-area"):
        correct_ir_drop(source, resistance_ohm=10.0, electrode_area_cm2=0.2)


def test_ir_correction_rejects_density_without_area_and_invalid_parameters():
    density = _lsv(y_unit="mA/cm^2")
    with pytest.raises(LSVError, match="electrode_area_cm2"):
        correct_ir_drop(density, resistance_ohm=5)
    with pytest.raises(LSVError, match="non-negative"):
        correct_ir_drop(_lsv(), resistance_ohm=-1)
    with pytest.raises(LSVError, match="between 0 and 1"):
        correct_ir_drop(_lsv(), resistance_ohm=5, correction_fraction=1.1)


def test_ir_correction_rejects_missing_current_values():
    source = _lsv(y=(-1.0, np.nan, -3.0))
    with pytest.raises(LSVError, match="missing"):
        correct_ir_drop(source, resistance_ohm=5)


def test_ir_correction_rejects_repeated_correction():
    first = correct_ir_drop(_lsv(x=(-0.5,), y=(-2.0,)), resistance_ohm=10.0)
    with pytest.raises(LSVError, match="already"):
        correct_ir_drop(first, resistance_ohm=5.0)


def test_ir_correction_supports_unicode_superscript_area_unit():
    source = _lsv(x=(-0.5,), y=(-10.0,), y_unit="mA cm⁻²")
    result = correct_ir_drop(source, resistance_ohm=10.0, electrode_area_cm2=0.2)
    np.testing.assert_allclose(result.x, [-0.48])


def test_current_density_conversion_preserves_sign_and_units():
    source = _lsv(y=(-2.0, 1.0, 4.0), y_unit="mA")
    result = to_current_density(source, electrode_area_cm2=0.2)

    np.testing.assert_allclose(result.y, [-10.0, 5.0, 20.0])
    assert result.y_axis.name == "current_density"
    assert result.y_axis.label == "Current density"
    assert result.y_axis.unit == "mA/cm^2"
    assert result.y_axis.metadata["normalization"] == "geometric_area"
    assert result.y_axis.metadata["electrode_area_cm2"] == pytest.approx(0.2)


def test_ir_correction_round_trip_from_library_current_density_uses_stored_area():
    density = to_current_density(
        _lsv(x=(-0.5,), y=(-2.0,), y_unit="mA"),
        electrode_area_cm2=0.2,
    )
    result = correct_ir_drop(density, resistance_ohm=10.0, electrode_area_cm2=0.2)

    np.testing.assert_allclose(result.x, [-0.48])
    record = result.metadata["processing_history"][-1]
    assert record["parameters"]["density_area_basis"] == "geometric_area_declared_matched"


def test_ir_correction_rejects_area_mismatch_for_library_current_density():
    density = to_current_density(
        _lsv(x=(-0.5,), y=(-2.0,), y_unit="mA"),
        electrode_area_cm2=0.2,
    )
    with pytest.raises(LSVError, match="does not match"):
        correct_ir_drop(density, resistance_ohm=10.0, electrode_area_cm2=0.5)


def test_current_density_conversion_supports_microamp_and_output_unit():
    source = _lsv(y=(1000.0, -500.0, 0.0), y_unit="µA")
    result = to_current_density(
        source,
        electrode_area_cm2=0.5,
        output_unit="A/cm^2",
    )

    np.testing.assert_allclose(result.y, [0.002, -0.001, 0.0])
    assert result.y_axis.unit == "A/cm^2"


def test_current_density_conversion_rejects_invalid_area_and_double_normalization():
    with pytest.raises(LSVError, match="greater than zero"):
        to_current_density(_lsv(), electrode_area_cm2=0)
    with pytest.raises(LSVError, match="already current density"):
        to_current_density(_lsv(y_unit="mA cm^-2"), electrode_area_cm2=0.2)


def test_current_density_conversion_rejects_unsupported_current_unit():
    with pytest.raises(LSVError, match="unsupported current"):
        to_current_density(_lsv(y_unit="C/s"), electrode_area_cm2=0.2)


def test_process_lsv_applies_rhe_then_ir_then_area_normalization():
    source = _lsv(x=(-0.5,), y=(-2.0,), y_unit="mA")
    config = LSVProcessingConfig(
        rhe_offset_v=0.9,
        source_reference="Ag/AgCl",
        resistance_ohm=10.0,
        electrode_area_cm2=0.2,
        normalize_to_current_density=True,
    )
    result = process_lsv(source, config)

    np.testing.assert_allclose(result.x, [0.42])
    np.testing.assert_allclose(result.y, [-10.0])
    operations = [item["operation"] for item in result.metadata["processing_history"]]
    assert operations == [
        "echem.convert_potential_to_rhe",
        "echem.correct_ir_drop",
        "echem.to_current_density",
    ]
    np.testing.assert_allclose(source.x, [-0.5])
    np.testing.assert_allclose(source.y, [-2.0])


def test_lsv_config_requires_area_for_requested_normalization():
    with pytest.raises(LSVError, match="electrode_area_cm2"):
        LSVProcessingConfig(normalize_to_current_density=True)


def test_lsv_config_rejects_orphan_or_empty_source_reference():
    with pytest.raises(LSVError, match="requires rhe_offset_v"):
        LSVProcessingConfig(source_reference="Ag/AgCl")
    with pytest.raises(LSVError, match="must not be empty"):
        LSVProcessingConfig(rhe_offset_v=0.9, source_reference="   ")


def test_lsv_config_rejects_rhe_as_source_for_rhe_conversion():
    with pytest.raises(LSVError, match="must not be RHE"):
        LSVProcessingConfig(rhe_offset_v=0.1, source_reference="RHE")


def test_process_lsv_dataset_preserves_order_metadata_and_supports_key_overrides():
    first = _lsv(key="a", label="Cat A", y=(-1.0, -2.0, -3.0))
    second = _lsv(key="b", label="Cat B", y=(-1.0, -2.0, -3.0))
    dataset = Dataset(
        [first, second],
        name="LSV comparison",
        metadata={"electrolyte": "0.1 M KOH"},
    )
    shared = LSVProcessingConfig(rhe_offset_v=0.8)
    overrides = {"b": LSVProcessingConfig(rhe_offset_v=0.9)}

    result = process_lsv_dataset(dataset, shared, overrides=overrides)

    assert result.name == dataset.name
    assert result.metadata["electrolyte"] == "0.1 M KOH"
    assert result.labels == ("Cat A", "Cat B")
    assert result.keys == ("a", "b")
    np.testing.assert_allclose(result[0].x, [0.2, 0.3, 0.4])
    np.testing.assert_allclose(result[1].x, [0.3, 0.4, 0.5])


def test_process_lsv_dataset_rejects_unknown_override_key():
    dataset = Dataset([_lsv(key="a")])
    with pytest.raises(LSVError, match="not present"):
        process_lsv_dataset(
            dataset,
            LSVProcessingConfig(),
            overrides={"missing": LSVProcessingConfig(rhe_offset_v=0.1)},
        )
