from __future__ import annotations

from math import lgamma, log, pi

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.characterization.exafs import EXAFSError
from catalysis_workbench.experimental.characterization.wt_exafs import (
    EXAFSWTResult,
    EXAFSWTSpec,
    cauchy_wt_exafs,
)


def _series(*, descending: bool = False, r0: float = 2.5) -> Series:
    k = np.arange(0.0, 15.0 + 0.025, 0.05)
    chi = np.cos(2.0 * r0 * k)
    if descending:
        k = k[::-1]
        chi = chi[::-1]
    return Series(
        x=k,
        y=chi,
        key="wt",
        label="synthetic WT",
        x_axis=Axis("k", unit="Å^-1"),
        y_axis=Axis("chi", unit="1"),
    )


def _spec() -> EXAFSWTSpec:
    return EXAFSWTSpec(
        order=20,
        rmin_angstrom=1.0,
        rmax_angstrom=4.0,
        rstep_angstrom=0.1,
        kweight=0.0,
        nfft=512,
    )


def test_single_frequency_ridge_recovers_target_r() -> None:
    target_r = 2.5
    result = cauchy_wt_exafs(_series(r0=target_r), _spec())
    k_index = int(np.argmin(np.abs(result.k_grid - 7.5)))
    ridge_index = int(np.argmax(result.magnitude[:, k_index]))
    ridge_r = float(result.r_grid[ridge_index])
    assert ridge_r == pytest.approx(target_r, abs=result.spec.rstep_angstrom)


def test_declared_cauchy_frequency_kernel_matches_one_retained_row() -> None:
    source = _series()
    spec = _spec()
    result = cauchy_wt_exafs(source, spec)
    target_r = 2.5
    row = int(np.argmin(np.abs(result.r_grid - target_r)))

    weighted = np.asarray(source.y) * np.power(np.asarray(source.x), spec.kweight)
    spectrum = np.fft.fft(weighted, n=spec.nfft)
    omega = 2.0 * pi * np.fft.fftfreq(spec.nfft, d=0.05)
    positive = omega > 0.0
    scale = spec.order / (2.0 * target_r)
    scaled_omega = scale * omega[positive]
    log_norm = log(2.0 * pi) - lgamma(spec.order + 1.0)
    kernel = np.zeros(spec.nfft)
    kernel[positive] = np.exp(
        log_norm
        + spec.order * np.log(scaled_omega)
        - scaled_omega
    )
    expected = np.fft.ifft(spectrum * kernel)[: source.n_points]
    np.testing.assert_allclose(result.transform[row], expected, rtol=1e-12, atol=1e-12)


def test_descending_source_retains_direction_and_same_transform() -> None:
    ascending = cauchy_wt_exafs(_series(), _spec())
    descending = cauchy_wt_exafs(_series(descending=True), _spec())
    assert ascending.source_direction == "ascending"
    assert descending.source_direction == "descending"
    assert np.all(np.diff(descending.source_k) < 0.0)
    np.testing.assert_allclose(descending.k_grid, ascending.k_grid)
    np.testing.assert_allclose(descending.r_grid, ascending.r_grid)
    np.testing.assert_allclose(descending.transform, ascending.transform)


def test_zero_r_row_is_explicitly_zero() -> None:
    spec = EXAFSWTSpec(
        order=20,
        rmin_angstrom=0.0,
        rmax_angstrom=3.0,
        rstep_angstrom=0.1,
        nfft=512,
    )
    result = cauchy_wt_exafs(_series(), spec)
    assert result.r_grid[0] == pytest.approx(0.0)
    np.testing.assert_allclose(result.transform[0], 0.0)
    np.testing.assert_allclose(result.magnitude[0], 0.0)


def test_component_arrays_cross_check_complex_transform() -> None:
    result = cauchy_wt_exafs(_series(), _spec())
    np.testing.assert_allclose(result.magnitude, np.abs(result.transform))
    np.testing.assert_allclose(result.real, result.transform.real)
    np.testing.assert_allclose(result.imaginary, result.transform.imag)
    np.testing.assert_allclose(result.phase, np.angle(result.transform))


def test_off_zero_origin_and_short_nfft_fail_explicitly() -> None:
    k = np.arange(0.05, 4.0 + 0.025, 0.05)
    offset = Series(
        k,
        np.cos(4.0 * k),
        x_axis=Axis("k", unit="Å^-1"),
        y_axis=Axis("chi", unit="1"),
    )
    with pytest.raises(EXAFSError, match="zero-origin"):
        cauchy_wt_exafs(
            offset,
            EXAFSWTSpec(order=10, rmax_angstrom=3.0, nfft=256),
        )

    with pytest.raises(EXAFSError, match="shorter"):
        cauchy_wt_exafs(
            _series(),
            EXAFSWTSpec(order=10, rmax_angstrom=3.0, nfft=128),
        )


def test_spec_rejects_implicit_or_incompatible_transform_state() -> None:
    with pytest.raises(EXAFSError, match="integer multiple"):
        EXAFSWTSpec(
            order=20,
            rmin_angstrom=0.0,
            rmax_angstrom=3.0,
            rstep_angstrom=0.07,
        )
    with pytest.raises(EXAFSError, match="only Cauchy"):
        EXAFSWTSpec(order=20, rmax_angstrom=3.0, family="morlet")
    with pytest.raises(EXAFSError, match="at least 1"):
        EXAFSWTSpec(order=0, rmax_angstrom=3.0)
    with pytest.raises(EXAFSError, match="frequency-to-R"):
        EXAFSWTSpec(
            order=20,
            rmax_angstrom=3.0,
            frequency_mapping="omega_peak=R",
        )


def test_result_reconstruction_fails_closed() -> None:
    result = cauchy_wt_exafs(_series(), _spec())
    bad = np.array(result.magnitude, copy=True)
    bad[5, 5] += 1.0
    with pytest.raises(EXAFSError, match="magnitude contradicts"):
        EXAFSWTResult(
            source_key=result.source_key,
            source_digest=result.source_digest,
            source_k=result.source_k,
            source_chi=result.source_chi,
            source_direction=result.source_direction,
            k_step=result.k_step,
            spec=result.spec,
            k_grid=result.k_grid,
            r_grid=result.r_grid,
            transform=result.transform,
            magnitude=bad,
            real=result.real,
            imaginary=result.imaginary,
            phase=result.phase,
        )


def test_plot_wt_exafs_is_passive() -> None:
    from catalysis_workbench.experimental.characterization.wt_exafs_plotting import (
        plot_wt_exafs,
    )

    result = cauchy_wt_exafs(_series(), _spec())
    before = np.array(result.magnitude, copy=True)
    figure, ax = plot_wt_exafs(result)
    np.testing.assert_array_equal(result.magnitude, before)
    assert len(ax.collections) == 1
    assert ax.get_xlabel() == "k (Å⁻¹)"
    assert ax.get_ylabel() == "R (Å)"
    figure.canvas.draw()
