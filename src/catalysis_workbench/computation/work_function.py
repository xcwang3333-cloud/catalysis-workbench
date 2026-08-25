"""Explicit LOCPOT planar-potential and work-function arithmetic for v0.7."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .band_structure import BandStructureState
from .scalar_field import ScalarField


class WorkFunctionError(ValueError):
    """Raised when retained potential/work-function state is inconsistent."""


def _nonblank(value: object, *, name: str, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    text = str(value).strip()
    if not text:
        raise WorkFunctionError(f"{name} must not be blank")
    return text


def _finite(value: object, *, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a finite float") from exc
    if not np.isfinite(result):
        raise WorkFunctionError(f"{name} must be finite")
    return result


def _axis(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise TypeError("axis must be an integer")
    axis = int(value)
    if axis not in (0, 1, 2):
        raise WorkFunctionError("axis must be 0, 1, or 2")
    return axis


def _frozen_1d(values: Any, *, name: str) -> NDArray[np.float64]:
    try:
        source = np.asarray(values)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must contain real numeric values") from exc
    if np.iscomplexobj(source):
        raise WorkFunctionError(f"{name} must contain real values")
    try:
        array = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must contain real numeric values") from exc
    if array.ndim != 1 or array.size == 0:
        raise WorkFunctionError(f"{name} must be a non-empty 1-D array")
    if not np.isfinite(array).all():
        raise WorkFunctionError(f"{name} must contain only finite values")
    contiguous = np.ascontiguousarray(array, dtype=np.float64)
    frozen = np.frombuffer(contiguous.tobytes(order="C"), dtype=np.float64)
    frozen.setflags(write=False)
    return frozen


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_value(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_value(item) for item in value)
    if isinstance(value, np.ndarray):
        array = np.array(value, copy=True)
        array.setflags(write=False)
        return array
    return deepcopy(value)


def _freeze_metadata(metadata: Mapping[str, Any] | None) -> Mapping[str, Any]:
    source = {} if metadata is None else dict(metadata)
    return MappingProxyType({str(key): _freeze_value(value) for key, value in source.items()})


def _digest_text(digest: Any, value: str | None) -> None:
    if value is None:
        digest.update(b"\xff")
        return
    encoded = value.encode("utf-8")
    digest.update(len(encoded).to_bytes(8, "little", signed=False))
    digest.update(encoded)


def _calculation_id_from_field(field: ScalarField) -> str | None:
    value = field.metadata.get("calculation_id")
    if value is None:
        return None
    return _nonblank(value, name="calculation_id", optional=True)


@dataclass(frozen=True, slots=True, eq=False)
class PlanarPotentialProfile:
    """Exact source-grid planar average along one caller-selected lattice axis."""

    source_field_digest: str
    structure_digest: str
    calculation_id: str | None
    axis: int
    grid_shape: tuple[int, int, int]
    normal_height_angstrom: float
    fractional_coordinates: Any
    normal_coordinates_angstrom: Any
    potential_ev: Any
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        source = str(_nonblank(self.source_field_digest, name="source_field_digest"))
        structure = str(_nonblank(self.structure_digest, name="structure_digest"))
        calculation_id = _nonblank(
            self.calculation_id, name="calculation_id", optional=True
        )
        axis = _axis(self.axis)
        shape = tuple(self.grid_shape)
        if len(shape) != 3 or any(
            isinstance(size, bool) or not isinstance(size, int) or size <= 0 for size in shape
        ):
            raise WorkFunctionError("grid_shape must contain three positive integers")
        height = _finite(self.normal_height_angstrom, name="normal_height_angstrom")
        if height <= 0.0:
            raise WorkFunctionError("normal_height_angstrom must be positive")

        fractional = _frozen_1d(self.fractional_coordinates, name="fractional_coordinates")
        normal = _frozen_1d(
            self.normal_coordinates_angstrom, name="normal_coordinates_angstrom"
        )
        potential = _frozen_1d(self.potential_ev, name="potential_ev")
        expected_size = shape[axis]
        if not (fractional.size == normal.size == potential.size == expected_size):
            raise WorkFunctionError("profile arrays must match the selected source-grid axis size")
        expected_fractional = np.arange(expected_size, dtype=np.float64) / expected_size
        if not np.array_equal(fractional, expected_fractional):
            raise WorkFunctionError("fractional coordinates must equal exact source indices i/n")
        if not np.allclose(normal, fractional * height, rtol=0.0, atol=1e-14):
            raise WorkFunctionError(
                "normal coordinates must equal fractional coordinates times normal height"
            )

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.PlanarPotentialProfile.v1\0")
        for text in (source, structure, calculation_id):
            _digest_text(digest, text)
        digest.update(axis.to_bytes(1, "little", signed=False))
        for size in shape:
            digest.update(size.to_bytes(8, "little", signed=False))
        digest.update(np.float64(height).tobytes())
        digest.update(fractional.tobytes(order="C"))
        digest.update(normal.tobytes(order="C"))
        digest.update(potential.tobytes(order="C"))

        object.__setattr__(self, "source_field_digest", source)
        object.__setattr__(self, "structure_digest", structure)
        object.__setattr__(self, "calculation_id", calculation_id)
        object.__setattr__(self, "axis", axis)
        object.__setattr__(self, "grid_shape", shape)
        object.__setattr__(self, "normal_height_angstrom", height)
        object.__setattr__(self, "fractional_coordinates", fractional)
        object.__setattr__(self, "normal_coordinates_angstrom", normal)
        object.__setattr__(self, "potential_ev", potential)
        object.__setattr__(self, "digest", digest.hexdigest())

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, PlanarPotentialProfile)
            and self.digest == other.digest
            and np.array_equal(self.potential_ev, other.potential_ev)
        )


@dataclass(frozen=True, slots=True, eq=False)
class VacuumLevelResult:
    """Vacuum level from one explicit half-open retained profile window."""

    profile_digest: str
    source_field_digest: str
    calculation_id: str | None
    side_id: str | None
    start_index: int
    stop_index: int
    selected_indices: tuple[int, ...]
    fractional_start: float
    fractional_stop: float
    normal_start_angstrom: float
    normal_stop_angstrom: float
    statistic: str
    vacuum_ev: float
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        profile = str(_nonblank(self.profile_digest, name="profile_digest"))
        source = str(_nonblank(self.source_field_digest, name="source_field_digest"))
        calculation_id = _nonblank(
            self.calculation_id, name="calculation_id", optional=True
        )
        side_id = _nonblank(self.side_id, name="side_id", optional=True)
        for value, name in (
            (self.start_index, "start_index"),
            (self.stop_index, "stop_index"),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise WorkFunctionError(f"{name} must be a non-negative integer")
        if self.stop_index <= self.start_index:
            raise WorkFunctionError("stop_index must be greater than start_index")
        expected_indices = tuple(range(self.start_index, self.stop_index))
        if tuple(self.selected_indices) != expected_indices:
            raise WorkFunctionError("selected_indices must exactly match the half-open window")
        fractional_start = _finite(self.fractional_start, name="fractional_start")
        fractional_stop = _finite(self.fractional_stop, name="fractional_stop")
        normal_start = _finite(self.normal_start_angstrom, name="normal_start_angstrom")
        normal_stop = _finite(self.normal_stop_angstrom, name="normal_stop_angstrom")
        if not 0.0 <= fractional_start < fractional_stop <= 1.0:
            raise WorkFunctionError("fractional vacuum bounds must satisfy 0 <= start < stop <= 1")
        if normal_start < 0.0 or normal_stop <= normal_start:
            raise WorkFunctionError("normal vacuum bounds must be ordered and non-negative")
        statistic = str(_nonblank(self.statistic, name="statistic")).lower()
        if statistic != "mean":
            raise WorkFunctionError("Block-5 vacuum statistic must be explicit 'mean'")
        vacuum = _finite(self.vacuum_ev, name="vacuum_ev")

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.VacuumLevelResult.v1\0")
        for text in (profile, source, calculation_id, side_id, statistic):
            _digest_text(digest, text)
        for index in expected_indices:
            digest.update(index.to_bytes(8, "little", signed=False))
        for value in (
            fractional_start,
            fractional_stop,
            normal_start,
            normal_stop,
            vacuum,
        ):
            digest.update(np.float64(value).tobytes())

        object.__setattr__(self, "profile_digest", profile)
        object.__setattr__(self, "source_field_digest", source)
        object.__setattr__(self, "calculation_id", calculation_id)
        object.__setattr__(self, "side_id", side_id)
        object.__setattr__(self, "selected_indices", expected_indices)
        object.__setattr__(self, "fractional_start", fractional_start)
        object.__setattr__(self, "fractional_stop", fractional_stop)
        object.__setattr__(self, "normal_start_angstrom", normal_start)
        object.__setattr__(self, "normal_stop_angstrom", normal_stop)
        object.__setattr__(self, "statistic", statistic)
        object.__setattr__(self, "vacuum_ev", vacuum)
        object.__setattr__(self, "digest", digest.hexdigest())

    def __eq__(self, other: object) -> bool:
        return isinstance(other, VacuumLevelResult) and self.digest == other.digest


@dataclass(frozen=True, slots=True, eq=False)
class FermiLevelSource:
    """Explicit Fermi level bound to one caller-visible calculation identity."""

    fermi_ev: float
    source_digest: str
    calculation_id: str
    source_type: str = "explicit"
    metadata: Mapping[str, Any] = field(default_factory=dict)
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        fermi = _finite(self.fermi_ev, name="fermi_ev")
        source = str(_nonblank(self.source_digest, name="source_digest"))
        calculation_id = str(_nonblank(self.calculation_id, name="calculation_id"))
        source_type = str(_nonblank(self.source_type, name="source_type"))
        metadata = _freeze_metadata(self.metadata)

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.FermiLevelSource.v1\0")
        digest.update(np.float64(fermi).tobytes())
        for text in (source, calculation_id, source_type):
            _digest_text(digest, text)

        object.__setattr__(self, "fermi_ev", fermi)
        object.__setattr__(self, "source_digest", source)
        object.__setattr__(self, "calculation_id", calculation_id)
        object.__setattr__(self, "source_type", source_type)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "digest", digest.hexdigest())

    def __eq__(self, other: object) -> bool:
        return isinstance(other, FermiLevelSource) and self.digest == other.digest


@dataclass(frozen=True, slots=True, eq=False)
class WorkFunctionResult:
    """Transparent work-function arithmetic from retained vacuum and Fermi values."""

    vacuum_result_digest: str
    vacuum_profile_digest: str
    vacuum_field_digest: str
    fermi_source_digest: str
    calculation_id: str
    side_id: str | None
    vacuum_ev: float
    fermi_ev: float
    work_function_ev: float
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        vacuum_result = str(
            _nonblank(self.vacuum_result_digest, name="vacuum_result_digest")
        )
        vacuum_profile = str(
            _nonblank(self.vacuum_profile_digest, name="vacuum_profile_digest")
        )
        vacuum_field = str(
            _nonblank(self.vacuum_field_digest, name="vacuum_field_digest")
        )
        fermi_source = str(_nonblank(self.fermi_source_digest, name="fermi_source_digest"))
        calculation_id = str(_nonblank(self.calculation_id, name="calculation_id"))
        side_id = _nonblank(self.side_id, name="side_id", optional=True)
        vacuum = _finite(self.vacuum_ev, name="vacuum_ev")
        fermi = _finite(self.fermi_ev, name="fermi_ev")
        work_function = _finite(self.work_function_ev, name="work_function_ev")
        expected = vacuum - fermi
        if not np.isclose(work_function, expected, rtol=0.0, atol=1e-14):
            raise WorkFunctionError("work_function_ev must equal vacuum_ev - fermi_ev")

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.WorkFunctionResult.v1\0")
        for text in (
            vacuum_result,
            vacuum_profile,
            vacuum_field,
            fermi_source,
            calculation_id,
            side_id,
        ):
            _digest_text(digest, text)
        for value in (vacuum, fermi, work_function):
            digest.update(np.float64(value).tobytes())

        object.__setattr__(self, "vacuum_result_digest", vacuum_result)
        object.__setattr__(self, "vacuum_profile_digest", vacuum_profile)
        object.__setattr__(self, "vacuum_field_digest", vacuum_field)
        object.__setattr__(self, "fermi_source_digest", fermi_source)
        object.__setattr__(self, "calculation_id", calculation_id)
        object.__setattr__(self, "side_id", side_id)
        object.__setattr__(self, "vacuum_ev", vacuum)
        object.__setattr__(self, "fermi_ev", fermi)
        object.__setattr__(self, "work_function_ev", work_function)
        object.__setattr__(self, "digest", digest.hexdigest())

    def __eq__(self, other: object) -> bool:
        return isinstance(other, WorkFunctionResult) and self.digest == other.digest


def planar_average_potential(field: ScalarField, *, axis: int) -> PlanarPotentialProfile:
    """Average exact retained source-grid potential values over the other two axes."""
    if not isinstance(field, ScalarField):
        raise TypeError("field must be a ScalarField")
    if field.field_kind != "local-potential" or field.value_unit != "eV":
        raise WorkFunctionError(
            "planar potential requires ScalarField(field_kind='local-potential', value_unit='eV')"
        )
    retained_axis = _axis(axis)
    lattice = field.structure.lattice_angstrom
    if lattice is None:
        raise WorkFunctionError("local-potential field requires an explicit lattice")
    lattice_array = np.asarray(lattice, dtype=np.float64)
    other_axes = tuple(index for index in range(3) if index != retained_axis)
    face_area = float(
        np.linalg.norm(np.cross(lattice_array[other_axes[0]], lattice_array[other_axes[1]]))
    )
    volume = float(abs(np.linalg.det(lattice_array)))
    if not np.isfinite(face_area) or face_area <= 0.0 or not np.isfinite(volume) or volume <= 0.0:
        raise WorkFunctionError("lattice must define positive finite volume and face area")
    height = volume / face_area
    n_axis = field.grid_shape[retained_axis]
    fractional = np.arange(n_axis, dtype=np.float64) / n_axis
    normal = fractional * height
    potential = np.mean(field.values, axis=other_axes, dtype=np.float64)
    return PlanarPotentialProfile(
        source_field_digest=field.digest,
        structure_digest=field.structure.digest,
        calculation_id=_calculation_id_from_field(field),
        axis=retained_axis,
        grid_shape=field.grid_shape,
        normal_height_angstrom=height,
        fractional_coordinates=fractional,
        normal_coordinates_angstrom=normal,
        potential_ev=potential,
    )


def vacuum_level_from_profile(
    profile: PlanarPotentialProfile,
    *,
    start_index: int,
    stop_index: int,
    side_id: str | None = None,
    statistic: str = "mean",
) -> VacuumLevelResult:
    """Compute a vacuum level from one explicit half-open retained profile window."""
    if not isinstance(profile, PlanarPotentialProfile):
        raise TypeError("profile must be a PlanarPotentialProfile")
    for value, name in ((start_index, "start_index"), (stop_index, "stop_index")):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an integer")
    if start_index < 0 or stop_index > profile.potential_ev.size or stop_index <= start_index:
        raise WorkFunctionError(
            "vacuum window must be non-empty and within retained profile bounds"
        )
    retained_statistic = str(_nonblank(statistic, name="statistic")).lower()
    if retained_statistic != "mean":
        raise WorkFunctionError("Block-5 vacuum statistic must be explicit 'mean'")
    selected = profile.potential_ev[start_index:stop_index]
    vacuum = float(np.mean(selected, dtype=np.float64))
    size = profile.potential_ev.size
    return VacuumLevelResult(
        profile_digest=profile.digest,
        source_field_digest=profile.source_field_digest,
        calculation_id=profile.calculation_id,
        side_id=side_id,
        start_index=start_index,
        stop_index=stop_index,
        selected_indices=tuple(range(start_index, stop_index)),
        fractional_start=start_index / size,
        fractional_stop=stop_index / size,
        normal_start_angstrom=start_index / size * profile.normal_height_angstrom,
        normal_stop_angstrom=stop_index / size * profile.normal_height_angstrom,
        statistic=retained_statistic,
        vacuum_ev=vacuum,
    )


def fermi_source_from_band_structure(
    state: BandStructureState,
    *,
    calculation_id: str,
) -> FermiLevelSource:
    """Retain the source Fermi value from a reviewed Block-3 band state."""
    if not isinstance(state, BandStructureState):
        raise TypeError("state must be a BandStructureState")
    if state.source_fermi_ev is None:
        raise WorkFunctionError("band state does not retain source_fermi_ev")
    return FermiLevelSource(
        fermi_ev=state.source_fermi_ev,
        source_digest=state.source_digest,
        calculation_id=calculation_id,
        source_type="BandStructureState",
        metadata={
            "band_structure_digest": state.digest,
            "reference_kind": state.reference_kind,
            "applied_shift_ev": state.applied_shift_ev,
        },
    )


def calculate_work_function(
    vacuum_level: VacuumLevelResult,
    fermi_source: FermiLevelSource,
) -> WorkFunctionResult:
    """Calculate Phi = V_vacuum - E_F with explicit calculation compatibility."""
    if not isinstance(vacuum_level, VacuumLevelResult):
        raise TypeError("vacuum_level must be a VacuumLevelResult")
    if not isinstance(fermi_source, FermiLevelSource):
        raise TypeError("fermi_source must be a FermiLevelSource")
    if vacuum_level.calculation_id is None:
        raise WorkFunctionError("vacuum level requires nonblank calculation_id for work function")
    if vacuum_level.calculation_id != fermi_source.calculation_id:
        raise WorkFunctionError("vacuum and Fermi sources must share the same calculation_id")
    value = vacuum_level.vacuum_ev - fermi_source.fermi_ev
    return WorkFunctionResult(
        vacuum_result_digest=vacuum_level.digest,
        vacuum_profile_digest=vacuum_level.profile_digest,
        vacuum_field_digest=vacuum_level.source_field_digest,
        fermi_source_digest=fermi_source.digest,
        calculation_id=fermi_source.calculation_id,
        side_id=vacuum_level.side_id,
        vacuum_ev=vacuum_level.vacuum_ev,
        fermi_ev=fermi_source.fermi_ev,
        work_function_ev=value,
    )


__all__ = [
    "FermiLevelSource",
    "PlanarPotentialProfile",
    "VacuumLevelResult",
    "WorkFunctionError",
    "WorkFunctionResult",
    "calculate_work_function",
    "fermi_source_from_band_structure",
    "planar_average_potential",
    "vacuum_level_from_profile",
]
