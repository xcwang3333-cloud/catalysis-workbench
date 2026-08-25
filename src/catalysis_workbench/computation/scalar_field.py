"""Immutable scalar-field state and exact source-grid geometry for v0.7."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .charge_density_difference import ChargeDensityDifferenceResult
from .electronic_structure import VolumetricGrid
from .structure import AtomicStructure


class ScalarFieldError(ValueError):
    """Raised when scalar-field state or grid geometry is invalid."""


def _nonblank(
    value: object,
    *,
    name: str,
    optional: bool = False,
) -> str | None:
    if value is None and optional:
        return None
    text = str(value).strip()
    if not text:
        raise ScalarFieldError(f"{name} must not be blank")
    return text


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _freeze_value(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, np.ndarray):
        array = np.array(value, copy=True)
        array.setflags(write=False)
        return array
    return deepcopy(value)


def _freeze_metadata(metadata: Mapping[str, Any] | None) -> Mapping[str, Any]:
    source = {} if metadata is None else dict(metadata)
    return MappingProxyType(
        {str(key): _freeze_value(value) for key, value in source.items()}
    )


def _thaw_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_value(item) for item in value]
    if isinstance(value, np.ndarray):
        return np.array(value, copy=True)
    return deepcopy(value)


def _frozen_float_array(
    values: Any,
    *,
    name: str,
    ndim: int,
) -> NDArray[np.float64]:
    try:
        source = np.asarray(values)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must contain real numeric values") from exc
    if np.iscomplexobj(source):
        raise ScalarFieldError(f"{name} must contain real values")
    try:
        array = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must contain real numeric values") from exc
    if array.ndim != ndim or any(size <= 0 for size in array.shape):
        raise ScalarFieldError(f"{name} must be a non-empty {ndim}-D array")
    if not np.isfinite(array).all():
        raise ScalarFieldError(f"{name} must contain only finite values")
    contiguous = np.ascontiguousarray(array, dtype=np.float64)
    frozen = np.frombuffer(
        contiguous.tobytes(order="C"),
        dtype=np.float64,
    ).reshape(contiguous.shape)
    frozen.setflags(write=False)
    return frozen


def _frozen_lattice(values: Any) -> NDArray[np.float64]:
    lattice = _frozen_float_array(values, name="lattice_angstrom", ndim=2)
    if lattice.shape != (3, 3):
        raise ScalarFieldError("lattice_angstrom must have shape (3, 3)")
    if np.linalg.matrix_rank(lattice) != 3:
        raise ScalarFieldError("lattice_angstrom must be nonsingular")
    return lattice


def _digest_text(digest: Any, value: str | None) -> None:
    if value is None:
        digest.update(b"\xff")
        return
    encoded = value.encode("utf-8")
    digest.update(len(encoded).to_bytes(8, "little", signed=False))
    digest.update(encoded)


def _digest_shape(digest: Any, shape: Sequence[int]) -> None:
    for value in shape:
        digest.update(int(value).to_bytes(8, "little", signed=False))


def _grid_index(
    index: Sequence[int],
    *,
    grid_shape: tuple[int, int, int],
) -> tuple[int, int, int]:
    if len(index) != 3:
        raise ScalarFieldError("grid index must contain exactly three integers")
    retained: list[int] = []
    for axis, (raw, size) in enumerate(zip(index, grid_shape, strict=True)):
        if isinstance(raw, (bool, np.bool_)) or not isinstance(
            raw,
            (int, np.integer),
        ):
            raise TypeError(f"grid index axis {axis} must be an integer")
        value = int(raw)
        if value < 0 or value >= size:
            raise ScalarFieldError(
                f"grid index axis {axis}={value} is outside [0, {size})"
            )
        retained.append(value)
    return retained[0], retained[1], retained[2]


@dataclass(frozen=True, slots=True, eq=False)
class ScalarField:
    """One immutable finite scalar quantity on a fully periodic source grid."""

    structure: AtomicStructure
    values: Any
    field_kind: str
    value_unit: str
    source_type: str
    source_key: str
    source_digest: str
    registration_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    grid_shape: tuple[int, int, int] = field(init=False)
    cell_volume_angstrom3: float = field(init=False)
    voxel_volume_angstrom3: float = field(init=False)
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.structure, AtomicStructure):
            raise TypeError("structure must be an AtomicStructure")
        if self.structure.lattice_angstrom is None or not all(self.structure.pbc):
            raise ScalarFieldError(
                "scalar fields require a fully periodic structure with an explicit lattice"
            )
        values = _frozen_float_array(self.values, name="values", ndim=3)
        field_kind = str(_nonblank(self.field_kind, name="field_kind"))
        value_unit = str(_nonblank(self.value_unit, name="value_unit"))
        source_type = str(_nonblank(self.source_type, name="source_type"))
        source_key = str(_nonblank(self.source_key, name="source_key"))
        source_digest = str(_nonblank(self.source_digest, name="source_digest"))
        registration_id = _nonblank(
            self.registration_id,
            name="registration_id",
            optional=True,
        )
        shape = tuple(int(value) for value in values.shape)
        lattice = np.asarray(self.structure.lattice_angstrom, dtype=np.float64)
        volume = float(abs(np.linalg.det(lattice)))
        if not np.isfinite(volume) or volume <= 0.0:
            raise ScalarFieldError("structure lattice must have positive finite volume")
        voxel = volume / int(np.prod(shape))
        metadata = _freeze_metadata(self.metadata)

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.ScalarField.v1\0")
        identity = (
            self.structure.digest,
            field_kind,
            value_unit,
            source_type,
            source_key,
            source_digest,
            registration_id,
        )
        for text in identity:
            _digest_text(digest, text)
        _digest_shape(digest, shape)
        digest.update(values.tobytes(order="C"))

        object.__setattr__(self, "values", values)
        object.__setattr__(self, "field_kind", field_kind)
        object.__setattr__(self, "value_unit", value_unit)
        object.__setattr__(self, "source_type", source_type)
        object.__setattr__(self, "source_key", source_key)
        object.__setattr__(self, "source_digest", source_digest)
        object.__setattr__(self, "registration_id", registration_id)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "grid_shape", shape)
        object.__setattr__(self, "cell_volume_angstrom3", volume)
        object.__setattr__(self, "voxel_volume_angstrom3", voxel)
        object.__setattr__(self, "digest", digest.hexdigest())

    def metadata_dict(self) -> dict[str, Any]:
        """Return an independent mutable copy of provenance metadata."""
        return {
            key: _thaw_value(value)
            for key, value in self.metadata.items()
        }

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, ScalarField)
            and self.digest == other.digest
            and self.structure == other.structure
            and np.array_equal(self.values, other.values)
        )


@dataclass(frozen=True, slots=True, eq=False)
class ScalarFieldSlice:
    """Exact retained source-grid plane with no interpolation or averaging."""

    source_field_digest: str
    structure_digest: str
    lattice_angstrom: Any
    grid_shape: tuple[int, int, int]
    field_kind: str
    value_unit: str
    registration_id: str | None
    axis: int
    index: int
    fractional_coordinate: float
    values: Any
    in_plane_axes: tuple[int, int]
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        source_field_digest = str(
            _nonblank(self.source_field_digest, name="source_field_digest")
        )
        structure_digest = str(
            _nonblank(self.structure_digest, name="structure_digest")
        )
        lattice = _frozen_lattice(self.lattice_angstrom)
        shape = tuple(int(value) for value in self.grid_shape)
        if len(shape) != 3 or any(value <= 0 for value in shape):
            raise ScalarFieldError(
                "grid_shape must contain three positive integers"
            )
        field_kind = str(_nonblank(self.field_kind, name="field_kind"))
        value_unit = str(_nonblank(self.value_unit, name="value_unit"))
        registration_id = _nonblank(
            self.registration_id,
            name="registration_id",
            optional=True,
        )
        if isinstance(self.axis, bool) or not isinstance(
            self.axis,
            (int, np.integer),
        ):
            raise TypeError("axis must be an integer")
        axis = int(self.axis)
        if axis not in (0, 1, 2):
            raise ScalarFieldError("axis must be 0, 1, or 2")
        if isinstance(self.index, bool) or not isinstance(
            self.index,
            (int, np.integer),
        ):
            raise TypeError("index must be an integer")
        index = int(self.index)
        if index < 0 or index >= shape[axis]:
            raise ScalarFieldError(
                f"slice index {index} is outside source axis size {shape[axis]}"
            )
        expected_fractional = index / shape[axis]
        fractional = float(self.fractional_coordinate)
        if not np.isfinite(fractional) or fractional != expected_fractional:
            raise ScalarFieldError(
                "fractional_coordinate must equal index / source axis size"
            )
        axes = tuple(int(value) for value in self.in_plane_axes)
        expected_axes = tuple(value for value in range(3) if value != axis)
        if axes != expected_axes:
            raise ScalarFieldError(
                "in_plane_axes must preserve the remaining source-axis order"
            )
        values = _frozen_float_array(self.values, name="values", ndim=2)
        expected_shape = tuple(shape[value] for value in axes)
        if values.shape != expected_shape:
            raise ScalarFieldError(
                "slice values shape must match the exact retained source-grid plane"
            )

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.ScalarFieldSlice.v1\0")
        identity = (
            source_field_digest,
            structure_digest,
            field_kind,
            value_unit,
            registration_id,
        )
        for text in identity:
            _digest_text(digest, text)
        digest.update(lattice.tobytes(order="C"))
        _digest_shape(digest, shape)
        digest.update(axis.to_bytes(1, "little", signed=False))
        digest.update(index.to_bytes(8, "little", signed=False))
        digest.update(np.float64(fractional).tobytes())
        digest.update(values.tobytes(order="C"))

        object.__setattr__(self, "source_field_digest", source_field_digest)
        object.__setattr__(self, "structure_digest", structure_digest)
        object.__setattr__(self, "lattice_angstrom", lattice)
        object.__setattr__(self, "grid_shape", shape)
        object.__setattr__(self, "field_kind", field_kind)
        object.__setattr__(self, "value_unit", value_unit)
        object.__setattr__(self, "registration_id", registration_id)
        object.__setattr__(self, "axis", axis)
        object.__setattr__(self, "index", index)
        object.__setattr__(self, "fractional_coordinate", fractional)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "in_plane_axes", axes)
        object.__setattr__(self, "digest", digest.hexdigest())

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, ScalarFieldSlice)
            and self.digest == other.digest
            and np.array_equal(self.values, other.values)
        )


def scalar_field_from_volumetric_grid(
    grid: VolumetricGrid,
    component: str,
    *,
    field_kind: str,
    registration_id: str | None = None,
    source_key: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> ScalarField:
    """Adapt exactly one released-v0.6 density component without conversion."""
    if not isinstance(grid, VolumetricGrid):
        raise TypeError("grid must be a VolumetricGrid")
    retained_component = str(_nonblank(component, name="component"))
    if retained_component not in grid.components:
        raise ScalarFieldError(
            f"component {retained_component!r} is not retained by VolumetricGrid"
        )
    if source_key is None:
        key = f"volumetric:{retained_component}"
    else:
        key = str(_nonblank(source_key, name="source_key"))
    provenance: dict[str, Any] = {
        "volumetric_grid_digest": grid.digest,
        "component": retained_component,
    }
    if metadata is not None:
        provenance["adapter_metadata"] = dict(metadata)
    return ScalarField(
        structure=grid.structure,
        values=grid.components[retained_component],
        field_kind=field_kind,
        value_unit=grid.density_unit,
        source_type="VolumetricGrid",
        source_key=key,
        source_digest=grid.digest,
        registration_id=registration_id,
        metadata=provenance,
    )


def scalar_field_from_charge_density_difference(
    result: ChargeDensityDifferenceResult,
    *,
    field_kind: str = "charge-density-difference",
    source_key: str = "charge-density-difference",
    metadata: Mapping[str, Any] | None = None,
) -> ScalarField:
    """Expose the already-computed signed difference as an immutable field."""
    if not isinstance(result, ChargeDensityDifferenceResult):
        raise TypeError("result must be a ChargeDensityDifferenceResult")
    provenance: dict[str, Any] = {
        "result_digest": result.digest,
        "difference_grid_digest": result.difference_grid.digest,
        "source_component": result.source_component,
    }
    if metadata is not None:
        provenance["adapter_metadata"] = dict(metadata)
    return ScalarField(
        structure=result.difference_grid.structure,
        values=result.difference,
        field_kind=field_kind,
        value_unit=result.density_unit,
        source_type="ChargeDensityDifferenceResult",
        source_key=source_key,
        source_digest=result.digest,
        registration_id=result.registration_id,
        metadata=provenance,
    )


def slice_scalar_field(
    scalar_field: ScalarField,
    *,
    axis: int,
    index: int,
) -> ScalarFieldSlice:
    """Select one exact retained source-grid plane."""
    if not isinstance(scalar_field, ScalarField):
        raise TypeError("scalar_field must be a ScalarField")
    if isinstance(axis, bool) or not isinstance(axis, (int, np.integer)):
        raise TypeError("axis must be an integer")
    retained_axis = int(axis)
    if retained_axis not in (0, 1, 2):
        raise ScalarFieldError("axis must be 0, 1, or 2")
    if isinstance(index, bool) or not isinstance(index, (int, np.integer)):
        raise TypeError("index must be an integer")
    retained_index = int(index)
    size = scalar_field.grid_shape[retained_axis]
    if retained_index < 0 or retained_index >= size:
        raise ScalarFieldError(
            f"slice index {retained_index} is outside source axis size {size}"
        )
    lattice = scalar_field.structure.lattice_angstrom
    assert lattice is not None
    axes = tuple(value for value in range(3) if value != retained_axis)
    values = np.take(scalar_field.values, retained_index, axis=retained_axis)
    return ScalarFieldSlice(
        source_field_digest=scalar_field.digest,
        structure_digest=scalar_field.structure.digest,
        lattice_angstrom=lattice,
        grid_shape=scalar_field.grid_shape,
        field_kind=scalar_field.field_kind,
        value_unit=scalar_field.value_unit,
        registration_id=scalar_field.registration_id,
        axis=retained_axis,
        index=retained_index,
        fractional_coordinate=retained_index / size,
        values=values,
        in_plane_axes=(axes[0], axes[1]),
    )


def fractional_grid_coordinate(
    scalar_field: ScalarField,
    index: Sequence[int],
) -> NDArray[np.float64]:
    """Return one retained source-grid point in fractional lattice coordinates."""
    if not isinstance(scalar_field, ScalarField):
        raise TypeError("scalar_field must be a ScalarField")
    retained = _grid_index(index, grid_shape=scalar_field.grid_shape)
    result = np.asarray(
        [
            retained[axis] / scalar_field.grid_shape[axis]
            for axis in range(3)
        ],
        dtype=np.float64,
    )
    result.setflags(write=False)
    return result


def cartesian_grid_coordinate(
    scalar_field: ScalarField,
    index: Sequence[int],
) -> NDArray[np.float64]:
    """Map one retained source-grid point through the full lattice matrix."""
    fractional = fractional_grid_coordinate(scalar_field, index)
    lattice = scalar_field.structure.lattice_angstrom
    assert lattice is not None
    result = np.asarray(fractional @ lattice, dtype=np.float64)
    result.setflags(write=False)
    return result


def slice_fractional_coordinate_grid(
    scalar_slice: ScalarFieldSlice,
) -> NDArray[np.float64]:
    """Construct fractional coordinates for an exact retained source slice."""
    if not isinstance(scalar_slice, ScalarFieldSlice):
        raise TypeError("scalar_slice must be a ScalarFieldSlice")
    coordinate = np.empty((*scalar_slice.values.shape, 3), dtype=np.float64)
    coordinate[..., scalar_slice.axis] = scalar_slice.fractional_coordinate
    first_axis, second_axis = scalar_slice.in_plane_axes
    first_indices, second_indices = np.indices(scalar_slice.values.shape)
    coordinate[..., first_axis] = (
        first_indices / scalar_slice.grid_shape[first_axis]
    )
    coordinate[..., second_axis] = (
        second_indices / scalar_slice.grid_shape[second_axis]
    )
    coordinate.setflags(write=False)
    return coordinate


def slice_cartesian_coordinate_grid(
    scalar_slice: ScalarFieldSlice,
) -> NDArray[np.float64]:
    """Map exact slice coordinates through the full retained lattice matrix."""
    fractional = slice_fractional_coordinate_grid(scalar_slice)
    result = np.asarray(
        fractional @ scalar_slice.lattice_angstrom,
        dtype=np.float64,
    )
    result.setflags(write=False)
    return result


__all__ = [
    "ScalarField",
    "ScalarFieldError",
    "ScalarFieldSlice",
    "cartesian_grid_coordinate",
    "fractional_grid_coordinate",
    "scalar_field_from_charge_density_difference",
    "scalar_field_from_volumetric_grid",
    "slice_cartesian_coordinate_grid",
    "slice_fractional_coordinate_grid",
    "slice_scalar_field",
]
