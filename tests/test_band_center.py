from __future__ import annotations

import subprocess
import sys
from dataclasses import FrozenInstanceError

import pytest

from catalysis_workbench.computation import (
    BandCenterError,
    BandCenterResult,
    DOSChannel,
    DOSProjection,
    DOSTrace,
    ElectronicDOS,
    ElectronicEnergyAxis,
    aggregate_dos,
    calculate_band_center,
    dos_channel_trace,
    reference_dos_to_fermi,
    select_dos_channels,
)


def _trace(
    energies: tuple[float, ...],
    density: tuple[float, ...],
    *,
    key: str = "trace",
    source_digest: str = "dos-source",
    channel_digests: tuple[str, ...] = ("channel-up",),
    projection_keys: tuple[str, ...] = ("site:fe-0:d",),
    spins: tuple[str, ...] = ("up",),
    reference_kind: str = "source-native",
    source_fermi_ev: float | None = 1.0,
    applied_shift_ev: float = 0.0,
    normalization_basis: str = "site",
) -> DOSTrace:
    return DOSTrace(
        key=key,
        label=key,
        energy=ElectronicEnergyAxis(
            energies,
            reference_kind=reference_kind,
            source_fermi_ev=source_fermi_ev,
            applied_shift_ev=applied_shift_ev,
        ),
        density=density,
        source_dos_digest=source_digest,
        source_channel_digests=channel_digests,
        source_projection_keys=projection_keys,
        source_spins=spins,
        density_unit="states/eV",
        normalization_basis=normalization_basis,
        operations=("select-channel",),
    )


def test_uniform_grid_first_moment_is_hand_verifiable() -> None:
    trace = _trace((-2.0, -1.0, 0.0, 1.0, 2.0), (1.0, 1.0, 1.0, 1.0, 1.0))
    result = calculate_band_center(
        trace,
        -2.0,
        0.0,
        denominator_tolerance=1e-12,
    )

    assert result.integration_method == "trapezoid"
    assert result.requested_window_ev == (-2.0, 0.0)
    assert result.integrated_window_ev == (-2.0, 0.0)
    assert result.point_count == 3
    assert result.denominator == pytest.approx(2.0)
    assert result.numerator == pytest.approx(-2.0)
    assert result.center_ev == pytest.approx(-1.0)


def test_nonuniform_grid_uses_explicit_x_trapezoid() -> None:
    trace = _trace((0.0, 1.0, 3.0), (1.0, 2.0, 1.0), source_fermi_ev=None)
    result = calculate_band_center(
        trace,
        0.0,
        3.0,
        denominator_tolerance=1e-12,
    )

    assert result.denominator == pytest.approx(4.5)
    assert result.numerator == pytest.approx(6.0)
    assert result.center_ev == pytest.approx(4.0 / 3.0)


def test_energy_reference_shift_moves_center_exactly_without_hidden_rereference() -> None:
    dos = ElectronicDOS(
        energy=ElectronicEnergyAxis(
            (-2.0, 0.0, 2.0, 4.0),
            source_fermi_ev=1.0,
        ),
        channels=(
            DOSChannel(DOSProjection("total", "total"), "up", (1.0, 1.0, 1.0, 1.0)),
        ),
    )
    native = dos_channel_trace(dos, projection_key="total", spin="up")
    fermi = reference_dos_to_fermi(native)

    native_result = calculate_band_center(
        native,
        -2.0,
        4.0,
        denominator_tolerance=1e-12,
    )
    fermi_result = calculate_band_center(
        fermi,
        -3.0,
        3.0,
        denominator_tolerance=1e-12,
    )

    assert native_result.energy_reference_kind == "source-native"
    assert fermi_result.energy_reference_kind == "fermi"
    assert native_result.center_ev == pytest.approx(1.0)
    assert fermi_result.center_ev == pytest.approx(0.0)
    assert fermi_result.center_ev == pytest.approx(native_result.center_ev - 1.0)


def test_window_uses_only_retained_points_and_records_actual_integrated_endpoints() -> None:
    trace = _trace((-2.0, 0.0, 2.0, 4.0), (1.0, 2.0, 3.0, 4.0))
    result = calculate_band_center(
        trace,
        -1.0,
        3.0,
        denominator_tolerance=1e-12,
    )

    assert result.requested_window_ev == (-1.0, 3.0)
    assert result.integrated_window_ev == (0.0, 2.0)
    assert result.point_count == 2
    assert result.denominator == pytest.approx(5.0)
    assert result.numerator == pytest.approx(6.0)
    assert result.center_ev == pytest.approx(1.2)


def test_window_fails_when_outside_axis_or_retaining_fewer_than_two_points() -> None:
    trace = _trace((-2.0, 0.0, 2.0, 4.0), (1.0, 2.0, 3.0, 4.0))

    with pytest.raises(BandCenterError, match="inside the retained energy axis"):
        calculate_band_center(trace, -3.0, 2.0, denominator_tolerance=1e-12)
    with pytest.raises(BandCenterError, match="at least two"):
        calculate_band_center(trace, -1.0, 1.0, denominator_tolerance=1e-12)
    with pytest.raises(BandCenterError, match="energy_min_ev < energy_max_ev"):
        calculate_band_center(trace, 1.0, 1.0, denominator_tolerance=1e-12)


def test_zero_or_near_zero_denominator_uses_caller_visible_tolerance() -> None:
    zero = _trace((0.0, 1.0, 2.0), (0.0, 0.0, 0.0), source_fermi_ev=None)
    tiny = _trace(
        (0.0, 1.0, 2.0),
        (1e-15, 1e-15, 1e-15),
        key="tiny",
        source_fermi_ev=None,
    )

    with pytest.raises(BandCenterError, match="caller-supplied tolerance"):
        calculate_band_center(zero, 0.0, 2.0, denominator_tolerance=1e-12)
    with pytest.raises(BandCenterError, match="caller-supplied tolerance"):
        calculate_band_center(tiny, 0.0, 2.0, denominator_tolerance=1e-12)

    accepted = calculate_band_center(tiny, 0.0, 2.0, denominator_tolerance=1e-18)
    assert accepted.denominator_tolerance == pytest.approx(1e-18)
    assert accepted.center_ev == pytest.approx(1.0)


@pytest.mark.parametrize("tolerance", [0.0, -1.0, float("nan"), float("inf")])
def test_invalid_denominator_tolerance_fails(tolerance: float) -> None:
    trace = _trace((0.0, 1.0, 2.0), (1.0, 1.0, 1.0), source_fermi_ev=None)
    with pytest.raises(BandCenterError):
        calculate_band_center(trace, 0.0, 2.0, denominator_tolerance=tolerance)


def test_result_is_immutable_deterministic_and_retains_source_provenance() -> None:
    trace = _trace((-1.0, 0.0, 1.0), (1.0, 2.0, 1.0))
    first = calculate_band_center(trace, -1.0, 1.0, denominator_tolerance=1e-12)
    second = calculate_band_center(trace, -1.0, 1.0, denominator_tolerance=1e-12)

    assert isinstance(first, BandCenterResult)
    assert first.digest == second.digest
    assert first.source_trace_digest == trace.digest
    assert first.source_dos_digest == trace.source_dos_digest
    assert first.source_channel_digests == trace.source_channel_digests
    assert first.source_projection_keys == trace.source_projection_keys
    assert first.source_spins == trace.source_spins
    assert first.source_operations == trace.operations
    assert first.density_unit == trace.density_unit
    assert first.normalization_basis == trace.normalization_basis
    with pytest.raises(FrozenInstanceError):
        first.center_ev = 99.0  # type: ignore[misc]


def test_preaggregated_spin_trace_is_integrated_without_hidden_recombination() -> None:
    dos = ElectronicDOS(
        energy=ElectronicEnergyAxis((-1.0, 0.0, 1.0), source_fermi_ev=0.0),
        channels=(
            DOSChannel(DOSProjection("total", "total"), "up", (1.0, 2.0, 1.0)),
            DOSChannel(DOSProjection("total", "total"), "down", (0.5, 1.0, 0.5)),
        ),
    )
    channels = select_dos_channels(dos, projection_kind="total", spins=("up", "down"))
    summed = aggregate_dos(dos, channels, key="sum-spin")
    result = calculate_band_center(summed, -1.0, 1.0, denominator_tolerance=1e-12)

    assert result.source_spins == ("up", "down")
    assert result.source_channel_digests == summed.source_channel_digests
    assert result.center_ev == pytest.approx(0.0)


def test_density_scaling_changes_integrals_but_not_center() -> None:
    base = _trace((-1.0, 0.0, 2.0), (1.0, 2.0, 1.0), source_fermi_ev=None)
    scaled = _trace(
        (-1.0, 0.0, 2.0),
        (10.0, 20.0, 10.0),
        key="scaled",
        source_digest="dos-scaled",
        channel_digests=("channel-scaled",),
        source_fermi_ev=None,
    )
    first = calculate_band_center(base, -1.0, 2.0, denominator_tolerance=1e-12)
    second = calculate_band_center(scaled, -1.0, 2.0, denominator_tolerance=1e-12)

    assert second.denominator == pytest.approx(first.denominator * 10.0)
    assert second.numerator == pytest.approx(first.numerator * 10.0)
    assert second.center_ev == pytest.approx(first.center_ev)
    assert second.digest != first.digest


def test_direct_result_reconstruction_rejects_inconsistent_center() -> None:
    trace = _trace((-1.0, 0.0, 1.0), (1.0, 2.0, 1.0))
    result = calculate_band_center(trace, -1.0, 1.0, denominator_tolerance=1e-12)
    kwargs = {
        field: getattr(result, field)
        for field in (
            "source_trace_key",
            "source_trace_digest",
            "source_dos_digest",
            "source_channel_digests",
            "source_projection_keys",
            "source_spins",
            "source_operations",
            "energy_reference_kind",
            "source_fermi_ev",
            "applied_shift_ev",
            "density_unit",
            "normalization_basis",
            "requested_window_ev",
            "integrated_window_ev",
            "point_count",
            "numerator",
            "denominator",
            "denominator_tolerance",
        )
    }
    with pytest.raises(BandCenterError, match="numerator / denominator"):
        BandCenterResult(**kwargs, center_ev=result.center_ev + 1.0)


def test_band_center_module_remains_matplotlib_lazy_in_fresh_interpreter() -> None:
    code = (
        "import sys; "
        "import catalysis_workbench.computation.band_center; "
        "assert 'matplotlib.pyplot' not in sys.modules"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
