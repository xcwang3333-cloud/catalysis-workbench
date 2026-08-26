"""Regression tests for v0.8 Block-4 Raman/FTIR operando consumers."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.characterization import FTIRBand, RamanBand
from catalysis_workbench.experimental.operando import (
    FrameCoordinate,
    OperandoSpectroscopyError,
    build_ftir_operando_stack,
    build_raman_operando_stack,
    fit_component_center_trace,
    fit_component_fwhm_trace,
    frame_cut,
    ftir_band_area_trace,
    ftir_peak_position_trace,
    raman_band_area_trace,
    raman_peak_position_trace,
    series_array_digest,
)
from catalysis_workbench.processing import (
    FitParameterSpec,
    PeakComponentSpec,
    PeakFitSpec,
    fit_peaks,
)


def _coordinates() -> tuple[FrameCoordinate, ...]:
    return (
        FrameCoordinate("time", Axis("time", unit="s"), [0.0, 10.0, 20.0]),
        FrameCoordinate(
            "potential",
            Axis("potential", unit="V", metadata={"reference": "RHE"}),
            [-0.5, -0.7, -0.5],
        ),
    )


def _raman_frames() -> tuple[Series, ...]:
    x = np.array([1000.0, 1100.0, 1200.0, 1300.0, 1400.0])
    rows = (
        [0.0, 2.0, 5.0, 2.0, 0.0],
        [0.0, 1.0, 3.0, 6.0, 1.0],
        [0.0, 3.0, 7.0, 2.0, 0.0],
    )
    return tuple(
        Series(
            x,
            row,
            key=f"r-{index}",
            x_axis=Axis("shift" if index == 0 else "raman_shift", unit="1/cm"),
            y_axis=Axis(
                "intensity",
                unit="a.u.",
                metadata={"processing_basis": "raw"},
            ),
        )
        for index, row in enumerate(rows)
    )


def _ftir_frames(*, kind: str = "absorbance") -> tuple[Series, ...]:
    x = np.array([1800.0, 1700.0, 1600.0, 1500.0, 1400.0])
    rows = (
        [0.0, 1.0, 5.0, 2.0, 0.0],
        [0.0, 2.0, 4.0, 6.0, 1.0],
        [0.0, 3.0, 7.0, 1.0, 0.0],
    )
    if kind == "transmittance":
        rows = tuple([90.0 - value for value in row] for row in rows)
        unit = "%"
    else:
        unit = None
    return tuple(
        Series(
            x,
            row,
            key=f"f-{index}",
            x_axis=Axis("wn" if index == 0 else "wavenumber", unit="cm-1"),
            y_axis=Axis(kind, unit=unit, metadata={"processing_basis": "raw"}),
        )
        for index, row in enumerate(rows)
    )


def _gaussian(x: np.ndarray, *, amplitude: float, center: float, sigma: float) -> np.ndarray:
    return amplitude / (sigma * np.sqrt(2.0 * np.pi)) * np.exp(
        -((x - center) ** 2) / (2.0 * sigma**2)
    )


def _gaussian_raman_frames() -> tuple[Series, ...]:
    x = np.linspace(900.0, 1300.0, 201)
    centers = (1080.0, 1100.0, 1120.0)
    sigmas = (20.0, 24.0, 28.0)
    return tuple(
        Series(
            x,
            _gaussian(x, amplitude=500.0, center=center, sigma=sigma),
            key=f"g-{index}",
            x_axis=Axis("raman_shift", unit="cm^-1"),
            y_axis=Axis(
                "intensity",
                unit="counts",
                metadata={"processing_basis": "raw"},
            ),
        )
        for index, (center, sigma) in enumerate(zip(centers, sigmas, strict=True))
    )


def _fit_gaussian(frame: Series):
    component = PeakComponentSpec(
        key="band",
        model="gaussian",
        parameters={
            "amplitude": FitParameterSpec(450.0, lower=0.0),
            "center": FitParameterSpec(1100.0, lower=1000.0, upper=1200.0),
            "sigma": FitParameterSpec(25.0, lower=5.0, upper=60.0),
        },
    )
    return fit_peaks(frame, PeakFitSpec(980.0, 1220.0, (component,)))


def test_raman_adapter_canonicalizes_semantics_without_changing_arrays() -> None:
    frames = _raman_frames()
    before = tuple(series_array_digest(frame) for frame in frames)
    stack = build_raman_operando_stack(
        frames,
        frame_coordinates=_coordinates(),
        primary_coordinate_key="time",
    )

    assert stack.signal_axis.name == "raman_shift"
    assert stack.signal_axis.unit == "cm^-1"
    assert stack.value_axis.name == "intensity"
    assert stack.signal_direction == "increasing"
    assert stack.frame_keys == ("r-0", "r-1", "r-2")
    assert stack.source_digests == before
    np.testing.assert_array_equal(stack.signal, frames[0].x)
    np.testing.assert_array_equal(stack.values[1], frames[1].y)
    np.testing.assert_array_equal(stack.primary_coordinate.values, [0.0, 10.0, 20.0])


def test_raman_adapter_rejects_mixed_basis_and_grid() -> None:
    frames = list(_raman_frames())
    frames[1] = Series(
        frames[1].x,
        frames[1].y,
        key=frames[1].key,
        x_axis=frames[1].x_axis,
        y_axis=Axis(
            "normalized_intensity",
            unit="a.u.",
            metadata={"processing_basis": "normalized"},
        ),
    )
    with pytest.raises(OperandoSpectroscopyError):
        build_raman_operando_stack(
            frames,
            frame_coordinates=_coordinates(),
            primary_coordinate_key="time",
        )

    frames = list(_raman_frames())
    shifted = np.array(frames[1].x, copy=True)
    shifted[2] += 1.0
    frames[1] = Series(
        shifted,
        frames[1].y,
        key=frames[1].key,
        x_axis=frames[1].x_axis,
        y_axis=frames[1].y_axis,
    )
    with pytest.raises(OperandoSpectroscopyError):
        build_raman_operando_stack(
            frames,
            frame_coordinates=_coordinates(),
            primary_coordinate_key="time",
        )


def test_ftir_adapter_preserves_descending_grid_and_rejects_mixed_state() -> None:
    frames = _ftir_frames()
    before = tuple(series_array_digest(frame) for frame in frames)
    stack = build_ftir_operando_stack(
        frames,
        frame_coordinates=_coordinates(),
        primary_coordinate_key="potential",
    )
    assert stack.signal_axis.name == "wavenumber"
    assert stack.signal_axis.unit == "cm^-1"
    assert stack.value_axis.name == "absorbance"
    assert stack.signal_direction == "decreasing"
    assert stack.source_digests == before
    np.testing.assert_array_equal(stack.signal, frames[0].x)
    np.testing.assert_array_equal(stack.primary_coordinate.values, [-0.5, -0.7, -0.5])

    mixed = list(frames)
    transmittance = _ftir_frames(kind="transmittance")[1]
    mixed[1] = replace(transmittance, key="f-1")
    with pytest.raises(OperandoSpectroscopyError):
        build_ftir_operando_stack(
            mixed,
            frame_coordinates=_coordinates(),
            primary_coordinate_key="time",
        )


def test_direct_raman_band_traces_match_reviewed_domain_measurements() -> None:
    stack = build_raman_operando_stack(
        _raman_frames(),
        frame_coordinates=_coordinates(),
        primary_coordinate_key="time",
    )
    original_digest = stack.digest
    band = RamanBand(1050.0, 1350.0, label="caller band")

    area = raman_band_area_trace(
        stack,
        band,
        coordinate_key="potential",
        area_mode="net",
    )
    position = raman_peak_position_trace(stack, band, coordinate_key="potential")

    expected_area = []
    expected_position = []
    from catalysis_workbench.experimental.characterization import measure_raman_band

    for index in range(stack.n_frames):
        measurement = measure_raman_band(frame_cut(stack, index=index), band, area_mode="net")
        expected_area.append(measurement.area)
        expected_position.append(measurement.peak_position_cm1)
    np.testing.assert_allclose(area.values, expected_area)
    np.testing.assert_array_equal(position.values, expected_position)
    np.testing.assert_array_equal(area.coordinate.values, [-0.5, -0.7, -0.5])
    assert area.parameters_dict()["boundary_interpolation"] == "reviewed_domain_function_only"
    assert area.source_stack_digest == stack.digest
    assert not area.values.flags.writeable
    assert stack.digest == original_digest


def test_direct_ftir_band_traces_and_transmittance_fail_closed() -> None:
    stack = build_ftir_operando_stack(
        _ftir_frames(),
        frame_coordinates=_coordinates(),
        primary_coordinate_key="time",
    )
    band = FTIRBand(1450.0, 1750.0, label="caller band")
    area = ftir_band_area_trace(stack, band, coordinate_key="time", area_mode="absolute")
    position = ftir_peak_position_trace(stack, band, coordinate_key="potential")
    assert area.n_frames == 3
    assert position.value_axis.unit == "cm^-1"
    np.testing.assert_array_equal(position.coordinate.values, [-0.5, -0.7, -0.5])

    transmittance_stack = build_ftir_operando_stack(
        _ftir_frames(kind="transmittance"),
        frame_coordinates=_coordinates(),
        primary_coordinate_key="time",
    )
    with pytest.raises(OperandoSpectroscopyError, match="reviewed domain measurement"):
        ftir_band_area_trace(
            transmittance_stack,
            band,
            coordinate_key="time",
        )


def test_fit_center_and_gaussian_fwhm_traces_use_exact_reviewed_results() -> None:
    frames = _gaussian_raman_frames()
    stack = build_raman_operando_stack(
        frames,
        frame_coordinates=_coordinates(),
        primary_coordinate_key="time",
    )
    results = tuple(_fit_gaussian(frame) for frame in frames)
    assert all(result.success for result in results)

    centers = fit_component_center_trace(
        stack,
        results,
        coordinate_key="potential",
        component_key="band",
        technique="raman",
    )
    widths = fit_component_fwhm_trace(
        stack,
        results,
        coordinate_key="time",
        component_key="band",
        technique="raman",
    )

    expected_centers = [result.parameters["band.center"].value for result in results]
    expected_widths = [
        2.0 * np.sqrt(2.0 * np.log(2.0)) * result.parameters["band.sigma"].value
        for result in results
    ]
    np.testing.assert_allclose(centers.values, expected_centers, rtol=1e-10, atol=1e-10)
    np.testing.assert_allclose(widths.values, expected_widths, rtol=1e-10, atol=1e-10)
    np.testing.assert_allclose(centers.values, [1080.0, 1100.0, 1120.0], atol=1e-5)
    assert widths.parameters_dict()["formula_convention"] == "lmfit_builtin_model"
    assert centers.parameters_dict()["source_state"] == "PeakFitResult"


def test_fit_trajectory_rejects_reordered_foreign_and_unknown_state() -> None:
    frames = _gaussian_raman_frames()
    stack = build_raman_operando_stack(
        frames,
        frame_coordinates=_coordinates(),
        primary_coordinate_key="time",
    )
    results = tuple(_fit_gaussian(frame) for frame in frames)

    with pytest.raises(OperandoSpectroscopyError, match="source keys/order"):
        fit_component_center_trace(
            stack,
            (results[1], results[0], results[2]),
            coordinate_key="time",
            component_key="band",
            technique="raman",
        )
    with pytest.raises(OperandoSpectroscopyError, match="does not contain component"):
        fit_component_center_trace(
            stack,
            results,
            coordinate_key="time",
            component_key="missing",
            technique="raman",
        )

    foreign = replace(results[0], source_sha256="0" * 64)
    with pytest.raises(OperandoSpectroscopyError, match="does not match source arrays"):
        fit_component_center_trace(
            stack,
            (foreign, results[1], results[2]),
            coordinate_key="time",
            component_key="band",
            technique="raman",
        )


def test_doniach_fwhm_is_explicitly_unsupported() -> None:
    frames = _gaussian_raman_frames()
    stack = build_raman_operando_stack(
        frames,
        frame_coordinates=_coordinates(),
        primary_coordinate_key="time",
    )
    results = tuple(_fit_gaussian(frame) for frame in frames)
    doniach_component = PeakComponentSpec(
        key="band",
        model="doniach",
        parameters={
            "amplitude": FitParameterSpec(500.0, lower=0.0),
            "center": FitParameterSpec(1100.0),
            "sigma": FitParameterSpec(25.0, lower=1.0),
            "gamma": FitParameterSpec(0.1, lower=0.0),
        },
    )
    doniach_spec = PeakFitSpec(980.0, 1220.0, (doniach_component,))
    doniach_results = tuple(replace(result, spec=doniach_spec) for result in results)

    with pytest.raises(OperandoSpectroscopyError, match="intentionally fail-closed"):
        fit_component_fwhm_trace(
            stack,
            doniach_results,
            coordinate_key="time",
            component_key="band",
            technique="raman",
        )
