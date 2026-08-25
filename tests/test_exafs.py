from __future__ import annotations

from math import pi, sqrt

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.experimental.characterization.exafs import (
    EXAFSError,
    EXAFSFTResult,
    EXAFSFTSpec,
    EXAFSKSpaceSpec,
    forward_ft_exafs,
    ft_exafs_component,
    prepare_exafs_kspace,
    validate_exafs_series,
)


def _series(*, descending: bool = False, start: float = 0.0) -> Series:
    k = np.arange(start, 8.0 + 0.25, 0.5)
    chi = np.cos(k) * np.exp(-0.08 * k)
    if descending:
        k = k[::-1]
        chi = chi[::-1]
    return Series(
        x=k,
        y=chi,
        label="synthetic EXAFS",
        key="exafs",
        x_axis=Axis("k", unit="Å^-1"),
        y_axis=Axis("chi", unit="1"),
    )


def _kspace_spec() -> EXAFSKSpaceSpec:
    return EXAFSKSpaceSpec(
        kmin=2.0,
        kmax=6.0,
        kweight=2.0,
        dk=1.0,
        dk2=1.0,
        window="hanning",
    )


def _ft_spec() -> EXAFSFTSpec:
    return EXAFSFTSpec(nfft=64, rmax_angstrom=2.0)


def test_validate_exafs_and_hanning_weighting() -> None:
    source = _series()
    validate_exafs_series(source)
    prepared = prepare_exafs_kspace(source, _kspace_spec())
    assert prepared.source_direction == "ascending"
    assert prepared.k_step == pytest.approx(0.5)
    np.testing.assert_allclose(prepared.k_grid, source.x)
    np.testing.assert_allclose(prepared.chi_grid, source.y)

    index = {float(k): i for i, k in enumerate(prepared.k_grid)}
    assert prepared.window[index[1.5]] == pytest.approx(0.0, abs=1e-14)
    assert prepared.window[index[2.0]] == pytest.approx(0.5)
    assert prepared.window[index[2.5]] == pytest.approx(1.0)
    assert prepared.window[index[5.5]] == pytest.approx(1.0)
    assert prepared.window[index[6.0]] == pytest.approx(0.5)
    assert prepared.window[index[6.5]] == pytest.approx(0.0, abs=1e-14)
    i2 = index[2.0]
    assert prepared.weighted_chi[i2] == pytest.approx(source.y[i2] * 4.0)
    assert prepared.windowed_weighted_chi[i2] == pytest.approx(
        source.y[i2] * 4.0 * 0.5
    )


def test_descending_source_retains_direction_but_prepares_equivalent_grid() -> None:
    ascending = prepare_exafs_kspace(_series(), _kspace_spec())
    descending = prepare_exafs_kspace(_series(descending=True), _kspace_spec())
    assert descending.source_direction == "descending"
    assert np.all(np.diff(descending.source_k) < 0.0)
    np.testing.assert_allclose(descending.k_grid, ascending.k_grid)
    np.testing.assert_allclose(descending.chi_grid, ascending.chi_grid)
    np.testing.assert_allclose(descending.window, ascending.window)
    np.testing.assert_allclose(
        descending.windowed_weighted_chi,
        ascending.windowed_weighted_chi,
    )


def test_zero_origin_grid_can_zero_fill_only_below_inactive_window() -> None:
    source = _series(start=1.0)
    prepared = prepare_exafs_kspace(source, _kspace_spec())
    np.testing.assert_allclose(prepared.k_grid[:2], [0.0, 0.5])
    np.testing.assert_allclose(prepared.chi_grid[:2], 0.0)
    np.testing.assert_allclose(prepared.window[:3], 0.0)

    with pytest.raises(EXAFSError, match="unmeasured active-window"):
        prepare_exafs_kspace(
            _series(start=2.0),
            EXAFSKSpaceSpec(2.0, 6.0, dk=1.0, dk2=1.0),
        )


def test_offgrid_and_nonuniform_k_fail_without_interpolation() -> None:
    offgrid = Series(
        [0.05, 0.15, 0.25, 0.35, 0.45],
        [1.0, 0.8, 0.4, 0.1, -0.2],
        x_axis=Axis("k", unit="Å^-1"),
        y_axis=Axis("chi", unit="1"),
    )
    with pytest.raises(EXAFSError, match="zero-origin"):
        prepare_exafs_kspace(
            offgrid,
            EXAFSKSpaceSpec(0.15, 0.35, dk=0.0, dk2=0.0),
        )

    nonuniform = Series(
        [0.0, 0.1, 0.21, 0.3],
        [1.0, 0.5, 0.2, -0.1],
        x_axis=Axis("k", unit="Å^-1"),
        y_axis=Axis("chi", unit="1"),
    )
    with pytest.raises(EXAFSError, match="uniformly spaced"):
        validate_exafs_series(nonuniform)


def test_validation_failures_are_explicit() -> None:
    with pytest.raises(EXAFSError, match="non-negative"):
        validate_exafs_series(
            Series(
                [-0.5, 0.0, 0.5],
                [0.0, 1.0, 0.0],
                x_axis=Axis("k", unit="Å^-1"),
                y_axis=Axis("chi", unit="1"),
            )
        )
    with pytest.raises(EXAFSError, match="strictly monotonic"):
        validate_exafs_series(
            Series(
                [0.0, 0.5, 0.5],
                [0.0, 1.0, 0.5],
                x_axis=Axis("k", unit="Å^-1"),
                y_axis=Axis("chi", unit="1"),
            )
        )
    with pytest.raises(EXAFSError, match="real-valued"):
        validate_exafs_series(
            Series(
                [0.0, 0.5, 1.0],
                [0.0 + 0j, 1.0 + 1j, 0.0 + 0j],
                x_axis=Axis("k", unit="Å^-1"),
                y_axis=Axis("chi", unit="1"),
            )
        )
    with pytest.raises(EXAFSError, match="finite"):
        validate_exafs_series(
            Series(
                [0.0, 0.5, 1.0],
                [0.0, np.nan, 0.0],
                x_axis=Axis("k", unit="Å^-1"),
                y_axis=Axis("chi", unit="1"),
            )
        )
    with pytest.raises(EXAFSError, match="inverse-angstrom"):
        validate_exafs_series(
            Series(
                [0.0, 0.5, 1.0],
                [0.0, 1.0, 0.0],
                x_axis=Axis("k", unit="nm^-1"),
                y_axis=Axis("chi", unit="1"),
            )
        )


def test_forward_ft_matches_declared_numpy_equation_and_r_step() -> None:
    prepared = prepare_exafs_kspace(_series(), _kspace_spec())
    result = forward_ft_exafs(prepared, _ft_spec())
    padded = np.zeros(64, dtype=np.complex128)
    padded[: prepared.k_grid.size] = prepared.windowed_weighted_chi
    expected_full = (prepared.k_step / sqrt(pi)) * np.fft.fft(padded)[:32]
    expected_r_step = pi / (prepared.k_step * 64)
    full_r = expected_r_step * np.arange(32)
    keep = full_r <= 2.0 + 1e-12
    np.testing.assert_allclose(result.r, full_r[keep])
    np.testing.assert_allclose(result.chi_r, expected_full[keep])
    assert result.r_step == pytest.approx(expected_r_step)
    np.testing.assert_allclose(result.magnitude, np.abs(result.chi_r))
    np.testing.assert_allclose(result.real, result.chi_r.real)
    np.testing.assert_allclose(result.imaginary, result.chi_r.imag)
    np.testing.assert_allclose(result.phase, np.angle(result.chi_r))


def test_ft_specs_reject_insufficient_nfft_or_unrepresentable_rmax() -> None:
    prepared = prepare_exafs_kspace(_series(), _kspace_spec())
    with pytest.raises(EXAFSError, match="shorter"):
        forward_ft_exafs(prepared, EXAFSFTSpec(nfft=16, rmax_angstrom=1.0))
    with pytest.raises(EXAFSError, match="representable"):
        forward_ft_exafs(prepared, EXAFSFTSpec(nfft=64, rmax_angstrom=4.0))


def test_retained_ft_reconstruction_fails_closed() -> None:
    result = forward_ft_exafs(
        prepare_exafs_kspace(_series(), _kspace_spec()),
        _ft_spec(),
    )
    bad_magnitude = np.array(result.magnitude, copy=True)
    bad_magnitude[1] += 0.5
    with pytest.raises(EXAFSError, match="magnitude contradicts"):
        EXAFSFTResult(
            preparation=result.preparation,
            spec=result.spec,
            r_step=result.r_step,
            r=result.r,
            chi_r=result.chi_r,
            magnitude=bad_magnitude,
            real=result.real,
            imaginary=result.imaginary,
            phase=result.phase,
        )


def test_component_materialization_is_explicit_and_real() -> None:
    result = forward_ft_exafs(
        prepare_exafs_kspace(_series(), _kspace_spec()),
        _ft_spec(),
    )
    magnitude = ft_exafs_component(result, "magnitude")
    real = ft_exafs_component(result, "real")
    phase = ft_exafs_component(result, "phase")
    np.testing.assert_allclose(magnitude.y, result.magnitude)
    np.testing.assert_allclose(real.y, result.real)
    np.testing.assert_allclose(phase.y, result.phase)
    assert magnitude.x_axis.name == "r"
    assert magnitude.x_axis.metadata["phase_corrected"] is False
    assert magnitude.y_axis.unit == "angstrom^-3"
    assert phase.y_axis.unit == "rad"


def test_plot_ft_exafs_is_passive_and_rejects_mixed_components() -> None:
    from catalysis_workbench.experimental.characterization.exafs_plotting import (
        plot_ft_exafs,
    )

    result = forward_ft_exafs(
        prepare_exafs_kspace(_series(), _kspace_spec()),
        _ft_spec(),
    )
    magnitude = ft_exafs_component(result, "magnitude")
    before_x = np.array(magnitude.x, copy=True)
    before_y = np.array(magnitude.y, copy=True)
    figure, ax = plot_ft_exafs(magnitude)
    np.testing.assert_array_equal(magnitude.x, before_x)
    np.testing.assert_array_equal(magnitude.y, before_y)
    np.testing.assert_array_equal(ax.lines[0].get_xdata(), before_x)
    np.testing.assert_array_equal(ax.lines[0].get_ydata(), before_y)
    figure.canvas.draw()

    real = ft_exafs_component(result, "real")
    real_other_key = Series(
        real.x,
        real.y,
        key="real",
        x_axis=real.x_axis,
        y_axis=real.y_axis,
        metadata=real.metadata_dict(),
    )
    with pytest.raises(EXAFSError, match="cannot mix"):
        plot_ft_exafs(Dataset((magnitude, real_other_key)))
