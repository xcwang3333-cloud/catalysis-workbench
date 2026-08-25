"""Explicit EXAFS k-space preparation and retained forward Fourier transform."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from math import isfinite, pi, sqrt
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from catalysis_workbench.core import Axis, Series

EXAFSDirection = Literal["ascending", "descending"]
EXAFSFTComponent = Literal["magnitude", "real", "imaginary", "phase"]

_K_NAMES = {"k", "wavenumber", "photoelectronwavenumber"}
_CHI_NAMES = {"chi", "exafschi"}
_INV_ANGSTROM_UNITS = {
    "1/angstrom",
    "angstrom^-1",
    "angstrom-1",
    "a^-1",
    "a-1",
    "1/a",
}
_DIMENSIONLESS_UNITS = {"", "1", "dimensionless", "a.u.", "a.u", "au"}
_R_UNITS = {"angstrom", "a"}


class EXAFSError(ValueError):
    """Raised when EXAFS state or a requested transform is invalid."""


def _semantic_token(value: str) -> str:
    token = str(value).strip().casefold()
    return "".join(character for character in token if character.isalnum())


def _compact_unit(unit: str | None) -> str:
    if unit is None:
        return ""
    token = "".join(str(unit).strip().casefold().split())
    token = token.replace("Å", "angstrom").replace("å", "angstrom")
    token = token.replace("⁻", "-").replace("¹", "1")
    return token


def _finite_float(value: Any, *, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a real numeric value") from exc
    if not isfinite(result):
        raise EXAFSError(f"{name} must be finite")
    return result


def _immutable_real(values: Any, *, name: str) -> NDArray[np.float64]:
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


def _immutable_complex(values: Any, *, name: str) -> NDArray[np.complex128]:
    array = np.asarray(values)
    if array.ndim != 1:
        raise EXAFSError(f"{name} must be one-dimensional")
    result = np.ascontiguousarray(array, dtype=np.complex128)
    if result.size == 0:
        raise EXAFSError(f"{name} must contain at least one value")
    if not np.isfinite(result.real).all() or not np.isfinite(result.imag).all():
        raise EXAFSError(f"{name} must contain only finite values")
    frozen = np.frombuffer(result.tobytes(order="C"), dtype=np.complex128)
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


def _source_arrays(
    k_values: Any,
    chi_values: Any,
) -> tuple[
    NDArray[np.float64],
    NDArray[np.float64],
    EXAFSDirection,
    float,
    float,
]:
    k = _immutable_real(k_values, name="k")
    chi = _immutable_real(chi_values, name="chi")
    if k.size != chi.size:
        raise EXAFSError("k and chi must have identical lengths")
    if k.size < 2:
        raise EXAFSError("EXAFS data require at least two k points")
    if np.any(k < 0.0):
        raise EXAFSError("EXAFS k values must be non-negative")

    differences = np.diff(k)
    if np.all(differences > 0.0):
        direction: EXAFSDirection = "ascending"
        positive_differences = differences
    elif np.all(differences < 0.0):
        direction = "descending"
        positive_differences = -differences
    else:
        raise EXAFSError("EXAFS k must be strictly monotonic with no duplicates")

    k_step = float(np.mean(positive_differences))
    tolerance = max(1e-10, abs(k_step) * 1e-8)
    if not np.allclose(
        positive_differences,
        k_step,
        rtol=1e-8,
        atol=tolerance,
    ):
        raise EXAFSError(
            "EXAFS k must be uniformly spaced; resample explicitly before this transform"
        )
    return k, chi, direction, k_step, tolerance


def validate_exafs_series(series: Series) -> None:
    """Validate explicit one-dimensional χ(k) EXAFS semantics."""
    if not isinstance(series, Series):
        raise TypeError("series must be a Series")
    _source_arrays(series.x, series.y)
    if _semantic_token(series.x_axis.name) not in _K_NAMES:
        raise EXAFSError("EXAFS x axis must identify k/photoelectron wavenumber")
    if _compact_unit(series.x_axis.unit) not in _INV_ANGSTROM_UNITS:
        raise EXAFSError("EXAFS k requires an explicit inverse-angstrom unit")
    if _semantic_token(series.y_axis.name) not in _CHI_NAMES:
        raise EXAFSError("EXAFS y axis must identify chi")
    if _compact_unit(series.y_axis.unit) not in _DIMENSIONLESS_UNITS:
        raise EXAFSError("EXAFS chi must be dimensionless")


@dataclass(frozen=True, slots=True)
class EXAFSKSpaceSpec:
    """Caller-visible k weighting and Hanning-window specification."""

    kmin: float
    kmax: float
    kweight: float = 2.0
    dk: float = 1.0
    dk2: float | None = None
    window: str = "hanning"

    def __post_init__(self) -> None:
        kmin = _finite_float(self.kmin, name="kmin")
        kmax = _finite_float(self.kmax, name="kmax")
        kweight = _finite_float(self.kweight, name="kweight")
        dk = _finite_float(self.dk, name="dk")
        dk2 = dk if self.dk2 is None else _finite_float(self.dk2, name="dk2")
        window = str(self.window).strip().casefold()
        if not 0.0 <= kmin < kmax:
            raise EXAFSError("EXAFS k-space spec requires 0 <= kmin < kmax")
        if kweight < 0.0:
            raise EXAFSError("EXAFS kweight must be non-negative")
        if dk < 0.0 or dk2 < 0.0:
            raise EXAFSError("EXAFS Hanning taper widths must be non-negative")
        if window not in {"hanning", "hann"}:
            raise EXAFSError("v0.5 EXAFS currently supports only the Hanning window")
        if kmin + dk / 2.0 > kmax - dk2 / 2.0:
            raise EXAFSError("EXAFS Hanning low/high tapers must not overlap")
        object.__setattr__(self, "kmin", kmin)
        object.__setattr__(self, "kmax", kmax)
        object.__setattr__(self, "kweight", kweight)
        object.__setattr__(self, "dk", dk)
        object.__setattr__(self, "dk2", dk2)
        object.__setattr__(self, "window", "hanning")


def _hanning_window(
    k_grid: NDArray[np.float64],
    spec: EXAFSKSpaceSpec,
) -> NDArray[np.float64]:
    window = np.zeros(k_grid.size, dtype=np.float64)
    low_start = spec.kmin - spec.dk / 2.0
    low_end = spec.kmin + spec.dk / 2.0
    high_start = spec.kmax - float(spec.dk2) / 2.0
    high_end = spec.kmax + float(spec.dk2) / 2.0

    if spec.dk > 0.0:
        mask = (k_grid >= low_start) & (k_grid < low_end)
        phase = (k_grid[mask] - low_start) / spec.dk
        window[mask] = np.sin((pi / 2.0) * phase) ** 2
    plateau_start = low_end if spec.dk > 0.0 else spec.kmin
    plateau_end = high_start if float(spec.dk2) > 0.0 else spec.kmax
    plateau = (k_grid >= plateau_start) & (k_grid <= plateau_end)
    window[plateau] = 1.0
    if float(spec.dk2) > 0.0:
        mask = (k_grid > high_start) & (k_grid <= high_end)
        phase = (k_grid[mask] - high_start) / float(spec.dk2)
        window[mask] = np.cos((pi / 2.0) * phase) ** 2
    return window


def _prepare_state(
    source_k: NDArray[np.float64],
    source_chi: NDArray[np.float64],
    spec: EXAFSKSpaceSpec,
) -> tuple[
    EXAFSDirection,
    float,
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
]:
    k, chi, direction, k_step, tolerance = _source_arrays(source_k, source_chi)
    if direction == "ascending":
        k_ascending = np.asarray(k, dtype=np.float64)
        chi_ascending = np.asarray(chi, dtype=np.float64)
    else:
        k_ascending = np.asarray(k[::-1], dtype=np.float64)
        chi_ascending = np.asarray(chi[::-1], dtype=np.float64)

    indices = np.rint(k_ascending / k_step).astype(np.int64)
    reconstructed_k = indices.astype(np.float64) * k_step
    if not np.allclose(k_ascending, reconstructed_k, rtol=0.0, atol=tolerance):
        raise EXAFSError(
            "EXAFS k points are not aligned to a zero-origin Δk grid; "
            "resample explicitly before this transform"
        )
    if np.any(np.diff(indices) != 1):
        raise EXAFSError("EXAFS zero-origin grid contains an internal k gap")

    source_min = float(k_ascending[0])
    source_max = float(k_ascending[-1])
    low_support = spec.kmin - spec.dk / 2.0
    high_support = spec.kmax + float(spec.dk2) / 2.0
    if low_support < source_min - tolerance:
        raise EXAFSError(
            "EXAFS Hanning low-k taper requires unmeasured active-window data"
        )
    if high_support > source_max + tolerance:
        raise EXAFSError(
            "EXAFS Hanning high-k taper requires data beyond the measured range"
        )

    last_index = int(indices[-1])
    k_grid = k_step * np.arange(last_index + 1, dtype=np.float64)
    chi_grid = np.zeros(last_index + 1, dtype=np.float64)
    chi_grid[indices] = chi_ascending
    window = _hanning_window(k_grid, spec)
    first_index = int(indices[0])
    if first_index > 0 and np.any(window[:first_index] > 1e-14):
        raise EXAFSError("EXAFS preparation would zero-fill inside the active FT window")
    weighted = chi_grid * np.power(k_grid, spec.kweight)
    windowed = weighted * window
    return direction, k_step, k_grid, chi_grid, window, weighted, windowed


@dataclass(frozen=True, slots=True, eq=False)
class EXAFSKSpaceResult:
    """Immutable retained state for explicit EXAFS k-space preparation."""

    source_key: str
    source_digest: str
    source_k: Any
    source_chi: Any
    source_direction: EXAFSDirection
    k_step: float
    spec: EXAFSKSpaceSpec
    k_grid: Any
    chi_grid: Any
    window: Any
    weighted_chi: Any
    windowed_weighted_chi: Any

    def __post_init__(self) -> None:
        if not isinstance(self.spec, EXAFSKSpaceSpec):
            raise TypeError("spec must be an EXAFSKSpaceSpec")
        source_key = str(self.source_key)
        source_k = _immutable_real(self.source_k, name="source_k")
        source_chi = _immutable_real(self.source_chi, name="source_chi")
        expected_digest = _source_digest(source_key, source_k, source_chi)
        if str(self.source_digest) != expected_digest:
            raise EXAFSError("source_digest contradicts retained EXAFS source data")
        (
            expected_direction,
            expected_step,
            expected_grid,
            expected_chi_grid,
            expected_window,
            expected_weighted,
            expected_windowed,
        ) = _prepare_state(source_k, source_chi, self.spec)
        if self.source_direction != expected_direction:
            raise EXAFSError("source_direction contradicts retained EXAFS source order")
        if not np.isclose(float(self.k_step), expected_step, rtol=1e-10, atol=1e-12):
            raise EXAFSError("k_step contradicts retained EXAFS source grid")

        comparisons = (
            ("k_grid", self.k_grid, expected_grid),
            ("chi_grid", self.chi_grid, expected_chi_grid),
            ("window", self.window, expected_window),
            ("weighted_chi", self.weighted_chi, expected_weighted),
            (
                "windowed_weighted_chi",
                self.windowed_weighted_chi,
                expected_windowed,
            ),
        )
        frozen: dict[str, NDArray[np.float64]] = {}
        for name, supplied, expected in comparisons:
            array = _immutable_real(supplied, name=name)
            if array.size != expected.size or not np.allclose(
                array,
                expected,
                rtol=1e-12,
                atol=1e-12,
            ):
                raise EXAFSError(f"retained {name} contradicts EXAFS preparation state")
            frozen[name] = array

        object.__setattr__(self, "source_key", source_key)
        object.__setattr__(self, "source_digest", expected_digest)
        object.__setattr__(self, "source_k", source_k)
        object.__setattr__(self, "source_chi", source_chi)
        object.__setattr__(self, "k_step", expected_step)
        for name, array in frozen.items():
            object.__setattr__(self, name, array)

    def equals(self, other: object) -> bool:
        return (
            isinstance(other, EXAFSKSpaceResult)
            and self.source_key == other.source_key
            and self.source_digest == other.source_digest
            and np.array_equal(self.source_k, other.source_k)
            and np.array_equal(self.source_chi, other.source_chi)
            and self.source_direction == other.source_direction
            and self.k_step == other.k_step
            and self.spec == other.spec
            and np.array_equal(self.k_grid, other.k_grid)
            and np.array_equal(self.chi_grid, other.chi_grid)
            and np.array_equal(self.window, other.window)
            and np.array_equal(self.weighted_chi, other.weighted_chi)
            and np.array_equal(
                self.windowed_weighted_chi,
                other.windowed_weighted_chi,
            )
        )

    def __eq__(self, other: object) -> bool:
        return self.equals(other)


def prepare_exafs_kspace(
    series: Series,
    spec: EXAFSKSpaceSpec,
) -> EXAFSKSpaceResult:
    """Prepare χ(k) for FT with explicit weighting/windowing and no interpolation."""
    if not isinstance(spec, EXAFSKSpaceSpec):
        raise TypeError("spec must be an EXAFSKSpaceSpec")
    validate_exafs_series(series)
    source_k, source_chi, _, _, _ = _source_arrays(series.x, series.y)
    direction, step, grid, chi_grid, window, weighted, windowed = _prepare_state(
        source_k,
        source_chi,
        spec,
    )
    return EXAFSKSpaceResult(
        source_key=series.key,
        source_digest=_source_digest(series.key, source_k, source_chi),
        source_k=source_k,
        source_chi=source_chi,
        source_direction=direction,
        k_step=step,
        spec=spec,
        k_grid=grid,
        chi_grid=chi_grid,
        window=window,
        weighted_chi=weighted,
        windowed_weighted_chi=windowed,
    )


@dataclass(frozen=True, slots=True)
class EXAFSFTSpec:
    """Forward-FT padding and output-range specification."""

    nfft: int = 2048
    rmax_angstrom: float = 10.0

    def __post_init__(self) -> None:
        if isinstance(self.nfft, bool) or not isinstance(self.nfft, int):
            raise TypeError("nfft must be an integer")
        if self.nfft < 2 or self.nfft % 2:
            raise EXAFSError("nfft must be an even integer >= 2")
        rmax = _finite_float(self.rmax_angstrom, name="rmax_angstrom")
        if rmax <= 0.0:
            raise EXAFSError("rmax_angstrom must be positive")
        object.__setattr__(self, "rmax_angstrom", rmax)


@dataclass(frozen=True, slots=True, eq=False)
class EXAFSFTResult:
    """Immutable retained complex χ(R) state for one forward EXAFS FT."""

    preparation: EXAFSKSpaceResult
    spec: EXAFSFTSpec
    r_step: float
    r: Any
    chi_r: Any
    magnitude: Any
    real: Any
    imaginary: Any
    phase: Any

    def __post_init__(self) -> None:
        if not isinstance(self.preparation, EXAFSKSpaceResult):
            raise TypeError("preparation must be an EXAFSKSpaceResult")
        if not isinstance(self.spec, EXAFSFTSpec):
            raise TypeError("spec must be an EXAFSFTSpec")
        prepared = self.preparation
        if self.spec.nfft < prepared.k_grid.size:
            raise EXAFSError("nfft is shorter than the prepared zero-origin k grid")
        padded = np.zeros(self.spec.nfft, dtype=np.complex128)
        padded[: prepared.k_grid.size] = prepared.windowed_weighted_chi
        full_chi_r = (prepared.k_step / sqrt(pi)) * np.fft.fft(padded)[: self.spec.nfft // 2]
        expected_r_step = pi / (prepared.k_step * self.spec.nfft)
        full_r = expected_r_step * np.arange(self.spec.nfft // 2, dtype=np.float64)
        if self.spec.rmax_angstrom > float(full_r[-1]) + 1e-12:
            raise EXAFSError("rmax_angstrom exceeds the representable forward-FT R range")
        keep = full_r <= self.spec.rmax_angstrom + 1e-12
        expected_r = full_r[keep]
        expected_chi_r = full_chi_r[keep]
        expected_magnitude = np.abs(expected_chi_r)
        expected_real = expected_chi_r.real
        expected_imaginary = expected_chi_r.imag
        expected_phase = np.angle(expected_chi_r)

        if not np.isclose(float(self.r_step), expected_r_step, rtol=1e-12, atol=1e-14):
            raise EXAFSError("r_step contradicts k_step/nfft transform convention")
        supplied_r = _immutable_real(self.r, name="r")
        supplied_chi_r = _immutable_complex(self.chi_r, name="chi_r")
        expected_real_arrays = (
            ("r", supplied_r, expected_r),
            ("magnitude", _immutable_real(self.magnitude, name="magnitude"), expected_magnitude),
            ("real", _immutable_real(self.real, name="real"), expected_real),
            (
                "imaginary",
                _immutable_real(self.imaginary, name="imaginary"),
                expected_imaginary,
            ),
            ("phase", _immutable_real(self.phase, name="phase"), expected_phase),
        )
        if supplied_chi_r.size != expected_chi_r.size or not np.allclose(
            supplied_chi_r,
            expected_chi_r,
            rtol=1e-12,
            atol=1e-12,
        ):
            raise EXAFSError("retained chi_r contradicts the declared forward-FT convention")
        frozen_real: dict[str, NDArray[np.float64]] = {}
        for name, supplied, expected in expected_real_arrays:
            if supplied.size != expected.size or not np.allclose(
                supplied,
                expected,
                rtol=1e-12,
                atol=1e-12,
            ):
                raise EXAFSError(f"retained {name} contradicts complex forward-FT state")
            frozen_real[name] = supplied

        object.__setattr__(self, "r_step", expected_r_step)
        object.__setattr__(self, "r", frozen_real["r"])
        object.__setattr__(self, "chi_r", supplied_chi_r)
        object.__setattr__(self, "magnitude", frozen_real["magnitude"])
        object.__setattr__(self, "real", frozen_real["real"])
        object.__setattr__(self, "imaginary", frozen_real["imaginary"])
        object.__setattr__(self, "phase", frozen_real["phase"])

    def equals(self, other: object) -> bool:
        return (
            isinstance(other, EXAFSFTResult)
            and self.preparation.equals(other.preparation)
            and self.spec == other.spec
            and self.r_step == other.r_step
            and np.array_equal(self.r, other.r)
            and np.array_equal(self.chi_r, other.chi_r)
            and np.array_equal(self.magnitude, other.magnitude)
            and np.array_equal(self.real, other.real)
            and np.array_equal(self.imaginary, other.imaginary)
            and np.array_equal(self.phase, other.phase)
        )

    def __eq__(self, other: object) -> bool:
        return self.equals(other)


def forward_ft_exafs(
    preparation: EXAFSKSpaceResult,
    spec: EXAFSFTSpec | None = None,
) -> EXAFSFTResult:
    """Apply the declared XAFS forward-FT convention to prepared χ(k)."""
    if not isinstance(preparation, EXAFSKSpaceResult):
        raise TypeError("preparation must be an EXAFSKSpaceResult")
    resolved = EXAFSFTSpec() if spec is None else spec
    if not isinstance(resolved, EXAFSFTSpec):
        raise TypeError("spec must be an EXAFSFTSpec")
    if resolved.nfft < preparation.k_grid.size:
        raise EXAFSError("nfft is shorter than the prepared zero-origin k grid")
    padded = np.zeros(resolved.nfft, dtype=np.complex128)
    padded[: preparation.k_grid.size] = preparation.windowed_weighted_chi
    full_chi_r = (preparation.k_step / sqrt(pi)) * np.fft.fft(padded)[: resolved.nfft // 2]
    r_step = pi / (preparation.k_step * resolved.nfft)
    full_r = r_step * np.arange(resolved.nfft // 2, dtype=np.float64)
    if resolved.rmax_angstrom > float(full_r[-1]) + 1e-12:
        raise EXAFSError("rmax_angstrom exceeds the representable forward-FT R range")
    keep = full_r <= resolved.rmax_angstrom + 1e-12
    chi_r = full_chi_r[keep]
    return EXAFSFTResult(
        preparation=preparation,
        spec=resolved,
        r_step=r_step,
        r=full_r[keep],
        chi_r=chi_r,
        magnitude=np.abs(chi_r),
        real=chi_r.real,
        imaginary=chi_r.imag,
        phase=np.angle(chi_r),
    )


def ft_exafs_component(
    result: EXAFSFTResult,
    component: EXAFSFTComponent = "magnitude",
) -> Series:
    """Materialize one retained real-valued χ(R) component as a core Series."""
    if not isinstance(result, EXAFSFTResult):
        raise TypeError("result must be an EXAFSFTResult")
    if component not in {"magnitude", "real", "imaginary", "phase"}:
        raise EXAFSError("component must be magnitude, real, imaginary, or phase")
    if component == "magnitude":
        values = result.magnitude
        axis_name = "chi_r_magnitude"
    elif component == "real":
        values = result.real
        axis_name = "chi_r_real"
    elif component == "imaginary":
        values = result.imaginary
        axis_name = "chi_r_imaginary"
    else:
        values = result.phase
        axis_name = "chi_r_phase"

    if component == "phase":
        unit = "rad"
    else:
        exponent = result.preparation.spec.kweight + 1.0
        unit = f"angstrom^-{exponent:g}"
    metadata = {
        "exafs_source_digest": result.preparation.source_digest,
        "kmin": result.preparation.spec.kmin,
        "kmax": result.preparation.spec.kmax,
        "kweight": result.preparation.spec.kweight,
        "dk": result.preparation.spec.dk,
        "dk2": result.preparation.spec.dk2,
        "window": result.preparation.spec.window,
        "nfft": result.spec.nfft,
        "rmax_angstrom": result.spec.rmax_angstrom,
        "phase_corrected": False,
        "ft_normalization": "delta_k_over_sqrt_pi",
    }
    return Series(
        x=result.r,
        y=values,
        label=result.preparation.source_key,
        key=result.preparation.source_key,
        x_axis=Axis(
            "r",
            unit="angstrom",
            label="R",
            metadata={"phase_corrected": False},
        ),
        y_axis=Axis(axis_name, unit=unit),
        metadata=metadata,
    )


__all__ = [
    "EXAFSDirection",
    "EXAFSError",
    "EXAFSFTComponent",
    "EXAFSFTResult",
    "EXAFSFTSpec",
    "EXAFSKSpaceResult",
    "EXAFSKSpaceSpec",
    "forward_ft_exafs",
    "ft_exafs_component",
    "prepare_exafs_kspace",
    "validate_exafs_series",
]
