from __future__ import annotations

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.characterization import (
    XANESNormalizationSpec,
    XASWindow,
    normalize_xanes,
)
from catalysis_workbench.experimental.operando import (
    FrameCoordinate,
    OperandoXASError,
    build_xanes_operando_stack,
    build_xas_operando_stack,
    xanes_edge_position_trace,
    xanes_white_line_intensity_trace,
    xas_window_integral_trace,
)


def _coordinate(n_frames: int) -> FrameCoordinate:
    return FrameCoordinate(
        "potential",
        Axis("potential", unit="V", metadata={"reference": "RHE"}),
        np.array([-0.40, -0.60, -0.40, -0.80], dtype=float)[:n_frames],
    )


def _raw_series(
    key: str,
    energy: np.ndarray,
    values: np.ndarray,
    *,
    reference: str | None = "caller-reference",
    y_name: str = "mu",
    y_unit: str | None = "a.u.",
) -> Series:
    metadata = {} if reference is None else {"energy_reference": reference}
    return Series(
        energy,
        values,
        key=key,
        x_axis=Axis("energy", unit="eV"),
        y_axis=Axis(y_name, unit=y_unit),
        metadata=metadata,
    )


def _transition(energy: np.ndarray, *, variant: int) -> np.ndarray:
    transition = np.zeros_like(energy, dtype=float)
    transition[energy >= 7.0] = 1.0
    if variant == 0:
        transition[energy == 4.0] = 0.10
        transition[energy == 5.0] = 0.60
        transition[energy == 6.0] = 0.90
    else:
        transition[energy == 4.0] = 0.05
        transition[energy == 5.0] = 0.30
        transition[energy == 6.0] = 1.20
    return transition


def _normalized_result(key: str, *, variant: int = 0, e0_ev: float = 5.0):
    energy = np.arange(0.0, 11.0, 1.0)
    mu = 0.02 * energy + _transition(energy, variant=variant)
    raw = _raw_series(key, energy, mu)
    return normalize_xanes(
        raw,
        XANESNormalizationSpec(
            e0_ev=e0_ev,
            pre_edge=XASWindow(0.0, 3.0),
            post_edge=XASWindow(7.0, 10.0),
            pre_edge_order=1,
            post_edge_order=1,
        ),
    )


def test_build_raw_xas_stack_preserves_exact_arrays_and_nonmonotonic_coordinate() -> None:
    energy = np.array([0.0, 1.0, 2.0, 3.0])
    first_values = np.array([0.0, 1.0, 2.0, 3.0])
    second_values = np.array([0.0, 2.0, 4.0, 6.0])
    energy_before = energy.copy()
    first_before = first_values.copy()

    stack = build_xas_operando_stack(
        [
            _raw_series("f0", energy, first_values, y_name="absorption"),
            _raw_series("f1", energy, second_values),
        ],
        frame_coordinates=[_coordinate(2)],
        primary_coordinate_key="potential",
    )

    assert stack.frame_keys == ("f0", "f1")
    assert stack.signal_axis.name == "energy"
    assert stack.signal_axis.unit == "eV"
    assert stack.value_axis.name == "mu"
    np.testing.assert_array_equal(stack.signal, energy_before)
    np.testing.assert_array_equal(stack.values[0], first_before)
    np.testing.assert_array_equal(stack.primary_coordinate.values, [-0.40, -0.60])
    assert stack.reconstructed_source_digests() == stack.source_digests
    assert not stack.signal.flags.writeable
    assert not stack.values.flags.writeable
    np.testing.assert_array_equal(energy, energy_before)
    np.testing.assert_array_equal(first_values, first_before)


def test_raw_xas_stack_accepts_decreasing_energy_and_integral_is_direction_invariant() -> None:
    increasing = _raw_series(
        "inc",
        np.array([0.0, 1.0, 2.0, 3.0]),
        np.array([0.0, 1.0, 2.0, 3.0]),
    )
    decreasing = _raw_series(
        "dec",
        np.array([3.0, 2.0, 1.0, 0.0]),
        np.array([3.0, 2.0, 1.0, 0.0]),
    )
    coordinate = FrameCoordinate("time", Axis("time", unit="s"), [0.0])

    inc_stack = build_xas_operando_stack(
        [increasing],
        frame_coordinates=[coordinate],
        primary_coordinate_key="time",
    )
    dec_stack = build_xas_operando_stack(
        [decreasing],
        frame_coordinates=[coordinate],
        primary_coordinate_key="time",
    )
    inc = xas_window_integral_trace(
        inc_stack,
        XASWindow(0.0, 3.0),
        coordinate_key="time",
    )
    dec = xas_window_integral_trace(
        dec_stack,
        XASWindow(0.0, 3.0),
        coordinate_key="time",
    )

    assert inc.values[0] == pytest.approx(4.5)
    assert dec.values[0] == pytest.approx(4.5)
    assert inc.parameters_dict()["boundary_interpolation"] == "none"
    assert inc.parameters_dict()["integration_direction"] == "increasing_physical_energy"


def test_raw_mode_rejects_normalized_series_and_reference_or_grid_mismatch() -> None:
    result = _normalized_result("norm")
    with pytest.raises(OperandoXASError, match="raw XAS mode"):
        build_xas_operando_stack(
            [result.normalized],
            frame_coordinates=[FrameCoordinate("time", Axis("time", unit="s"), [0.0])],
            primary_coordinate_key="time",
        )

    energy = np.array([0.0, 1.0, 2.0, 3.0])
    with pytest.raises(OperandoXASError, match="energy_reference"):
        build_xas_operando_stack(
            [
                _raw_series("a", energy, energy, reference="A"),
                _raw_series("b", energy, energy + 1.0, reference="B"),
            ],
            frame_coordinates=[_coordinate(2)],
            primary_coordinate_key="potential",
        )

    with pytest.raises(OperandoXASError, match="signal coordinates"):
        build_xas_operando_stack(
            [
                _raw_series("a", energy, energy),
                _raw_series("b", np.array([0.0, 1.0, 2.1, 3.0]), energy),
            ],
            frame_coordinates=[_coordinate(2)],
            primary_coordinate_key="potential",
        )


def test_normalized_xanes_stack_requires_reviewed_results_and_common_normalization_state() -> None:
    first = _normalized_result("n0", variant=0)
    second = _normalized_result("n1", variant=1)
    stack = build_xanes_operando_stack(
        [first, second],
        frame_coordinates=[_coordinate(2)],
        primary_coordinate_key="potential",
    )

    record = stack.metadata_dict()["catalysis_workbench.operando_domain"]
    assert record["mode"] == "normalized"
    assert tuple(record["normalization_source_digests"]) == (
        first.source_digest,
        second.source_digest,
    )
    assert record["normalization_signature"]["e0_ev"] == 5.0

    with pytest.raises(OperandoXASError, match="XANESNormalizationResult"):
        build_xanes_operando_stack(
            [first.normalized],  # type: ignore[list-item]
            frame_coordinates=[FrameCoordinate("time", Axis("time", unit="s"), [0.0])],
            primary_coordinate_key="time",
        )

    different_e0 = _normalized_result("n2", variant=0, e0_ev=5.5)
    with pytest.raises(OperandoXASError, match="identical E0"):
        build_xanes_operando_stack(
            [first, different_e0],
            frame_coordinates=[_coordinate(2)],
            primary_coordinate_key="potential",
        )


def test_normalized_descriptors_are_explicit_and_reconstructible() -> None:
    first = _normalized_result("n0", variant=0)
    second = _normalized_result("n1", variant=1)
    stack = build_xanes_operando_stack(
        [first, second],
        frame_coordinates=[_coordinate(2)],
        primary_coordinate_key="potential",
    )
    digest_before = stack.digest
    values_before = np.array(stack.values, copy=True)

    white_line = xanes_white_line_intensity_trace(
        stack,
        XASWindow(4.0, 6.0),
        coordinate_key="potential",
    )
    edge = xanes_edge_position_trace(
        stack,
        XASWindow(3.0, 7.0),
        coordinate_key="potential",
    )
    integral = xas_window_integral_trace(
        stack,
        XASWindow(4.0, 6.0),
        coordinate_key="potential",
    )

    np.testing.assert_allclose(white_line.values, [0.9, 1.2], atol=1e-12)
    np.testing.assert_allclose(edge.values, [4.5, 5.5], atol=1e-12)
    assert white_line.method == "xanes_white_line_intensity"
    assert edge.parameters_dict()["energy_alignment"] == "none"
    assert integral.parameters_dict()["boundary_policy"] == "measured_points_only"
    assert integral.value_axis.unit == "eV"
    assert white_line.source_stack_digest == stack.digest
    assert white_line.reconstructed_result_digests() == white_line.source_result_digests
    assert not white_line.values.flags.writeable
    assert stack.digest == digest_before
    np.testing.assert_array_equal(stack.values, values_before)


def test_descriptor_mode_method_and_window_failures_are_explicit() -> None:
    energy = np.array([0.0, 1.0, 2.0, 3.0])
    raw_stack = build_xas_operando_stack(
        [_raw_series("raw", energy, energy)],
        frame_coordinates=[FrameCoordinate("time", Axis("time", unit="s"), [0.0])],
        primary_coordinate_key="time",
    )
    with pytest.raises(OperandoXASError, match="normalized"):
        xanes_white_line_intensity_trace(
            raw_stack,
            XASWindow(0.0, 2.0),
            coordinate_key="time",
        )
    with pytest.raises(OperandoXASError, match="trapezoid_measured_points"):
        xas_window_integral_trace(
            raw_stack,
            XASWindow(0.0, 2.0),
            coordinate_key="time",
            method="hidden-spline",  # type: ignore[arg-type]
        )
    with pytest.raises(OperandoXASError, match="fewer than 2"):
        xas_window_integral_trace(
            raw_stack,
            XASWindow(0.9, 1.1),
            coordinate_key="time",
        )


def test_edge_position_fails_on_nonrising_or_ambiguous_secants() -> None:
    energy = np.array([0.0, 1.0, 2.0, 3.0])
    coordinate = FrameCoordinate("time", Axis("time", unit="s"), [0.0])

    def normalized_result_for(values: np.ndarray, key: str):
        raw_energy = np.arange(0.0, 11.0, 1.0)
        mu = 0.02 * raw_energy
        mu[raw_energy >= 7.0] += 1.0
        mu[3:7] += values
        return normalize_xanes(
            _raw_series(key, raw_energy, mu),
            XANESNormalizationSpec(
                5.0,
                XASWindow(0.0, 2.0),
                XASWindow(7.0, 10.0),
                1,
                1,
            ),
        )

    flat = normalized_result_for(np.array([0.5, 0.5, 0.5, 0.5]), "flat")
    flat_stack = build_xanes_operando_stack(
        [flat],
        frame_coordinates=[coordinate],
        primary_coordinate_key="time",
    )
    with pytest.raises(OperandoXASError, match="no positive secant"):
        xanes_edge_position_trace(
            flat_stack,
            XASWindow(3.0, 6.0),
            coordinate_key="time",
        )

    tied = normalized_result_for(np.array([0.0, 0.5, 1.0, 1.5]), "tied")
    tied_stack = build_xanes_operando_stack(
        [tied],
        frame_coordinates=[coordinate],
        primary_coordinate_key="time",
    )
    with pytest.raises(OperandoXASError, match="ambiguous"):
        xanes_edge_position_trace(
            tied_stack,
            XASWindow(3.0, 6.0),
            coordinate_key="time",
        )
