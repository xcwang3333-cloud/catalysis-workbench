"""Explicit continuous Cauchy WT-EXAFS transform with retained complex state."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from math import isfinite, lgamma, log, pi
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from catalysis_workbench.core import Series

from .exafs import EXAFSDirection, EXAFSError, _source_arrays, validate_exafs_series

EXAFSWTComponent = Literal["magnitude", "real", "imaginary", "phase"]


def _finite_float(value: Any, *, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a real numeric value") from exc
    if not isfinite(result):
        raise EXAFSError(f"{name} must be finite")
    return result


def _immutable_real_1d(values: Any, *, name: str) -> NDArray[np.float64]:
    array = np.asarray(values)
    if array.ndim != 1:
        raise EXAFSError(f"{name} must be one-dimensional")
    if np.iscomplexobj(array):
        raise EXAFSError(f"{name} must be real-valued")
    result = np.ascontiguousarray(array, dtype=np.float64)
    if result.size == 0 or not np.isfinite(result).all():
        raise EXAFSError(f"{name} must contain only finite values")
    frozen = np.frombuffer(result.tobytes(order="C"), dtype=np.float64)
    frozen.setflags(write=False)
    return frozen


def _immutable_real_2d(values: Any, *, name: str) -> NDArray[np.float64]:
    array = np.asarray(values)
    if array.ndim != 2:
        raise EXAFSError(f"{name} must be two-dimensional")
    if np.iscomplexobj(array):
        raise EXAFSError(f"{name} must be real-valued")
    result = np.ascontiguousarray(array, dtype=np.float64)
    if result.size == 0 or not np.isfinite(result).all():
        raise EXAFSError(f"{name} must contain only finite values")
    frozen = np.frombuffer(result.tobytes(order="C"), dtype=np.float64).reshape(
        result.shape
    )
    frozen.setflags(write=False)
    return frozen


def _immutable_complex_2d(values: Any, *, name: str) -> NDArray[np.complex128]:
    array = np.asarray(values)
    if array.ndim != 2:
        raise EXAFSError(f"{name} must be two-dimensional")
    result = np.ascontiguousarray(array, dtype=np.complex128)
    if result.size == 0:
        raise EXAFSError(f"{name} must contain at least one value")
    if not np.isfinite(result.real).all() or not np.isfinite(result.imag).all():
        raise EXAFSError(f"{name} must contain only finite values")
    frozen = np.frombuffer(result.tobytes(order="C"), dtype=np.complex128).reshape(
        result.shape
    )
    frozen.setflags(write=False)
    return frozen


def _source_digest(
    source_key: str,
    k: NDArray[np.float64],
    chi: NDArray[np.float64],
) -> str:
    digest = hashlib.sha256()
    digest.update(str(source_key).encode("utf-8"))
    digest.update(b"\0")
    digest.update(np.ascontiguousarray(k, dtype=np.float64).tobytes())
    digest.update(np.ascontiguousarray(chi, dtype=np.float64).tobytes())
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class EXAFSWTSpec:
    """Caller-visible Cauchy wavelet and k/R-grid specification."""

    order: int
    rmax_angstrom: float
    rmin_angstrom: float = 0.0
    rstep_angstrom: float = 0.05
    kweight: float = 0.0
    nfft: int = 2048
    family: str = "cauchy"
    frequency_mapping: str = "omega_peak=2R"
    normalization: str = "2pi_over_factorial"

    def __post_init__(self) -> None:
        if isinstance(self.order, bool) or not isinstance(self.order, int):
            raise TypeError("order must be an integer")
        if self.order < 1:
            raise EXAFSError("Cauchy order must be at least 1")
        if self.order > 1024:
            raise EXAFSError("Cauchy order must not exceed 1024")
        if isinstance(self.nfft, bool) or not isinstance(self.nfft, int):
            raise TypeError("nfft must be an integer")
        if self.nfft < 2 or self.nfft % 2:
            raise EXAFSError("nfft must be an even integer >= 2")

        rmin = _finite_float(self.rmin_angstrom, name="rmin_angstrom")
        rmax = _finite_float(self.rmax_angstrom, name="rmax_angstrom")
        rstep = _finite_float(self.rstep_angstrom, name="rstep_angstrom")
        kweight = _finite_float(self.kweight, name="kweight")
        if not 0.0 <= rmin < rmax:
            raise EXAFSError("WT-EXAFS requires 0 <= rmin_angstrom < rmax_angstrom")
        if rstep <= 0.0:
            raise EXAFSError("rstep_angstrom must be positive")
        if kweight < 0.0:
            raise EXAFSError("WT-EXAFS kweight must be non-negative")
        nsteps = (rmax - rmin) / rstep
        if not np.isclose(nsteps, round(nsteps), rtol=0.0, atol=1e-10):
            raise EXAFSError(
                "WT-EXAFS R range must be an integer multiple of rstep_angstrom"
            )

        family = str(self.family).strip().casefold()
        if family != "cauchy":
            raise EXAFSError("v0.5 WT-EXAFS currently supports only Cauchy wavelets")
        if self.frequency_mapping != "omega_peak=2R":
            raise EXAFSError("unsupported WT-EXAFS frequency-to-R mapping")
        if self.normalization != "2pi_over_factorial":
            raise EXAFSError("unsupported WT-EXAFS Cauchy normalization")

        object.__setattr__(self, "rmin_angstrom", rmin)
        object.__setattr__(self, "rmax_angstrom", rmax)
        object.__setattr__(self, "rstep_angstrom", rstep)
        object.__setattr__(self, "kweight", kweight)
        object.__setattr__(self, "family", "cauchy")


def _r_grid(spec: EXAFSWTSpec) -> NDArray[np.float64]:
    count = int(round((spec.rmax_angstrom - spec.rmin_angstrom) / spec.rstep_angstrom))
    return spec.rmin_angstrom + spec.rstep_angstrom * np.arange(
        count + 1,
        dtype=np.float64,
    )


def _ascending_zero_origin_source(
    source_k: NDArray[np.float64],
    source_chi: NDArray[np.float64],
) -> tuple[EXAFSDirection, float, NDArray[np.float64], NDArray[np.float64]]:
    k, chi, direction, k_step, tolerance = _source_arrays(source_k, source_chi)
    if direction == "ascending":
        k_grid = np.asarray(k, dtype=np.float64)
        chi_grid = np.asarray(chi, dtype=np.float64)
    else:
        k_grid = np.asarray(k[::-1], dtype=np.float64)
        chi_grid = np.asarray(chi[::-1], dtype=np.float64)

    if abs(float(k_grid[0])) > tolerance:
        raise EXAFSError("WT-EXAFS requires a zero-origin uniform k grid")
    expected_k = k_step * np.arange(k_grid.size, dtype=np.float64)
    if not np.allclose(k_grid, expected_k, rtol=0.0, atol=tolerance):
        raise EXAFSError("WT-EXAFS k values must align to the zero-origin Δk grid")
    return direction, k_step, k_grid, chi_grid


def _compute_cauchy_state(
    source_k: NDArray[np.float64],
    source_chi: NDArray[np.float64],
    spec: EXAFSWTSpec,
) -> tuple[
    EXAFSDirection,
    float,
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.complex128],
]:
    direction, k_step, k_grid, chi_grid = _ascending_zero_origin_source(
        source_k,
        source_chi,
    )
    if spec.nfft < k_grid.size:
        raise EXAFSError("WT-EXAFS nfft is shorter than the source k grid")

    weighted_chi = chi_grid * np.power(k_grid, spec.kweight)
    spectrum = np.fft.fft(weighted_chi, n=spec.nfft)
    omega = 2.0 * pi * np.fft.fftfreq(spec.nfft, d=k_step)
    positive = omega > 0.0
    positive_omega = omega[positive]
    r_grid = _r_grid(spec)

    filters = np.zeros((r_grid.size, spec.nfft), dtype=np.float64)
    log_norm = log(2.0 * pi) - lgamma(spec.order + 1.0)
    for index, r_value in enumerate(r_grid):
        if r_value == 0.0:
            continue
        scale = spec.order / (2.0 * r_value)
        scaled_omega = scale * positive_omega
        log_kernel = (
            log_norm
            + spec.order * np.log(scaled_omega)
            - scaled_omega
        )
        filters[index, positive] = np.exp(log_kernel)

    transform = np.fft.ifft(spectrum[np.newaxis, :] * filters, axis=1)
    transform = np.ascontiguousarray(transform[:, : k_grid.size], dtype=np.complex128)
    if not np.isfinite(transform.real).all() or not np.isfinite(transform.imag).all():
        raise EXAFSError("WT-EXAFS transform produced non-finite values")
    return direction, k_step, k_grid, r_grid, transform


@dataclass(frozen=True, slots=True, eq=False)
class EXAFSWTResult:
    """Immutable retained complex Cauchy WT-EXAFS k-R state."""

    source_key: str
    source_digest: str
    source_k: Any
    source_chi: Any
    source_direction: EXAFSDirection
    k_step: float
    spec: EXAFSWTSpec
    k_grid: Any
    r_grid: Any
    transform: Any
    magnitude: Any
    real: Any
    imaginary: Any
    phase: Any

    def __post_init__(self) -> None:
        if not isinstance(self.spec, EXAFSWTSpec):
            raise TypeError("spec must be an EXAFSWTSpec")
        source_key = str(self.source_key)
        source_k = _immutable_real_1d(self.source_k, name="source_k")
        source_chi = _immutable_real_1d(self.source_chi, name="source_chi")
        if source_k.size != source_chi.size:
            raise EXAFSError("retained WT-EXAFS source arrays must have equal lengths")
        expected_digest = _source_digest(source_key, source_k, source_chi)
        if str(self.source_digest) != expected_digest:
            raise EXAFSError("source_digest contradicts retained WT-EXAFS source data")

        (
            expected_direction,
            expected_step,
            expected_k,
            expected_r,
            expected_transform,
        ) = _compute_cauchy_state(source_k, source_chi, self.spec)
        if self.source_direction != expected_direction:
            raise EXAFSError("source_direction contradicts retained WT-EXAFS source order")
        if not np.isclose(float(self.k_step), expected_step, rtol=1e-10, atol=1e-12):
            raise EXAFSError("k_step contradicts retained WT-EXAFS source grid")

        k_grid = _immutable_real_1d(self.k_grid, name="k_grid")
        r_grid = _immutable_real_1d(self.r_grid, name="r_grid")
        transform = _immutable_complex_2d(self.transform, name="transform")
        if k_grid.size != expected_k.size or not np.allclose(
            k_grid,
            expected_k,
            rtol=0.0,
            atol=1e-12,
        ):
            raise EXAFSError("retained k_grid contradicts WT-EXAFS transform state")
        if r_grid.size != expected_r.size or not np.allclose(
            r_grid,
            expected_r,
            rtol=0.0,
            atol=1e-12,
        ):
            raise EXAFSError("retained r_grid contradicts WT-EXAFS transform state")
        if transform.shape != expected_transform.shape or not np.allclose(
            transform,
            expected_transform,
            rtol=1e-12,
            atol=1e-12,
        ):
            raise EXAFSError("retained transform contradicts declared Cauchy convention")

        expected_components = {
            "magnitude": np.abs(expected_transform),
            "real": expected_transform.real,
            "imaginary": expected_transform.imag,
            "phase": np.angle(expected_transform),
        }
        frozen_components: dict[str, NDArray[np.float64]] = {}
        for name, expected in expected_components.items():
            supplied = _immutable_real_2d(getattr(self, name), name=name)
            if supplied.shape != expected.shape or not np.allclose(
                supplied,
                expected,
                rtol=1e-12,
                atol=1e-12,
            ):
                raise EXAFSError(
                    f"retained {name} contradicts complex WT-EXAFS transform"
                )
            frozen_components[name] = supplied

        object.__setattr__(self, "source_key", source_key)
        object.__setattr__(self, "source_digest", expected_digest)
        object.__setattr__(self, "source_k", source_k)
        object.__setattr__(self, "source_chi", source_chi)
        object.__setattr__(self, "k_step", expected_step)
        object.__setattr__(self, "k_grid", k_grid)
        object.__setattr__(self, "r_grid", r_grid)
        object.__setattr__(self, "transform", transform)
        for name, array in frozen_components.items():
            object.__setattr__(self, name, array)

    def equals(self, other: object) -> bool:
        return (
            isinstance(other, EXAFSWTResult)
            and self.source_key == other.source_key
            and self.source_digest == other.source_digest
            and np.array_equal(self.source_k, other.source_k)
            and np.array_equal(self.source_chi, other.source_chi)
            and self.source_direction == other.source_direction
            and self.k_step == other.k_step
            and self.spec == other.spec
            and np.array_equal(self.k_grid, other.k_grid)
            and np.array_equal(self.r_grid, other.r_grid)
            and np.array_equal(self.transform, other.transform)
            and np.array_equal(self.magnitude, other.magnitude)
            and np.array_equal(self.real, other.real)
            and np.array_equal(self.imaginary, other.imaginary)
            and np.array_equal(self.phase, other.phase)
        )

    def __eq__(self, other: object) -> bool:
        return self.equals(other)


def cauchy_wt_exafs(series: Series, spec: EXAFSWTSpec) -> EXAFSWTResult:
    """Compute the explicit analytic Cauchy WT-EXAFS transform."""
    if not isinstance(spec, EXAFSWTSpec):
        raise TypeError("spec must be an EXAFSWTSpec")
    validate_exafs_series(series)
    source_k, source_chi, _, _, _ = _source_arrays(series.x, series.y)
    direction, k_step, k_grid, r_grid, transform = _compute_cauchy_state(
        source_k,
        source_chi,
        spec,
    )
    return EXAFSWTResult(
        source_key=series.key,
        source_digest=_source_digest(series.key, source_k, source_chi),
        source_k=source_k,
        source_chi=source_chi,
        source_direction=direction,
        k_step=k_step,
        spec=spec,
        k_grid=k_grid,
        r_grid=r_grid,
        transform=transform,
        magnitude=np.abs(transform),
        real=transform.real,
        imaginary=transform.imag,
        phase=np.angle(transform),
    )


__all__ = [
    "EXAFSWTComponent",
    "EXAFSWTResult",
    "EXAFSWTSpec",
    "cauchy_wt_exafs",
]
