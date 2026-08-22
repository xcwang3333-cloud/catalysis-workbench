"""Core one-dimensional scientific data models.

The v0.1 core intentionally stays small: a :class:`Series` represents one numerical
``y(x)`` trace, while a :class:`Dataset` is an ordered collection of series. The
objects are independent of file formats, scientific analysis, and plotting.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

Metadata = Mapping[str, Any]
NumericArray = NDArray[np.float64] | NDArray[np.complex128]


def _freeze_value(value: Any) -> Any:
    """Return a detached, read-only-friendly copy of metadata values."""
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _freeze_value(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_value(item) for item in value)
    if isinstance(value, np.ndarray):
        array = np.array(value, copy=True)
        array.setflags(write=False)
        return array
    return deepcopy(value)


def _freeze_metadata(metadata: Mapping[str, Any] | None) -> Metadata:
    source = {} if metadata is None else dict(metadata)
    return MappingProxyType(
        {str(key): _freeze_value(value) for key, value in source.items()}
    )


def _thaw_value(value: Any) -> Any:
    """Convert frozen metadata into an independent mutable representation."""
    if isinstance(value, Mapping):
        return {key: _thaw_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_value(item) for item in value]
    if isinstance(value, frozenset):
        return {_thaw_value(item) for item in value}
    if isinstance(value, np.ndarray):
        return np.array(value, copy=True)
    return deepcopy(value)


def _metadata_equal(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    if left.keys() != right.keys():
        return False
    return all(_value_equal(left[key], right[key]) for key in left)


def _value_equal(left: Any, right: Any) -> bool:
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        return _metadata_equal(left, right)
    if isinstance(left, np.ndarray) or isinstance(right, np.ndarray):
        try:
            return bool(np.array_equal(np.asarray(left), np.asarray(right), equal_nan=True))
        except TypeError:
            return bool(np.array_equal(np.asarray(left), np.asarray(right)))
    if isinstance(left, tuple) and isinstance(right, tuple):
        return len(left) == len(right) and all(
            _value_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    if isinstance(left, frozenset) and isinstance(right, frozenset):
        return left == right
    try:
        result = left == right
    except Exception:
        return False
    if isinstance(result, np.ndarray):
        return bool(np.all(result))
    return bool(result)


def _as_immutable_numeric_1d(values: ArrayLike, *, field_name: str) -> NumericArray:
    """Normalize one numeric vector and store it on immutable byte-backed memory.

    Real-valued input is normalized to float64 and complex-valued input to complex128.
    The returned ndarray is backed by a Python ``bytes`` object, so callers cannot
    re-enable NumPy's WRITEABLE flag and mutate the stored scientific data in place.
    """
    try:
        source = np.asarray(values)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{field_name} must contain numeric values") from exc

    if source.ndim != 1:
        raise ValueError(
            f"{field_name} must be one-dimensional; got shape {source.shape}"
        )
    if source.size == 0:
        raise ValueError(f"{field_name} must contain at least one point")
    if source.dtype.kind not in "biufc":
        raise TypeError(f"{field_name} must contain numeric values")

    dtype = (
        np.complex128
        if np.issubdtype(source.dtype, np.complexfloating)
        else np.float64
    )
    normalized = np.ascontiguousarray(source, dtype=dtype)

    if np.isinf(normalized).any():
        raise ValueError(f"{field_name} must not contain +/-inf")

    immutable_buffer = normalized.tobytes(order="C")
    array = np.frombuffer(
        immutable_buffer,
        dtype=normalized.dtype,
        count=normalized.size,
    )
    array.setflags(write=False)
    return array


@dataclass(frozen=True, slots=True, eq=False)
class Axis:
    """Semantic metadata describing one numerical axis.

    ``label`` and ``unit`` are stored separately. Final rendered strings such as
    ``Potential (V)`` or ``Potential / V`` are the responsibility of visualization.
    """

    name: str
    unit: str | None = None
    label: str | None = None
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        name = self.name.strip()
        if not name:
            raise ValueError("Axis.name must not be empty")

        unit = self.unit.strip() if self.unit is not None else None
        label = self.label.strip() if self.label is not None else None

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "unit", unit or None)
        object.__setattr__(self, "label", label or None)
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))

    def equals(self, other: object) -> bool:
        """Return whether another axis has the same scientific content."""
        return (
            isinstance(other, Axis)
            and self.name == other.name
            and self.unit == other.unit
            and self.label == other.label
            and _metadata_equal(self.metadata, other.metadata)
        )

    def __eq__(self, other: object) -> bool:
        return self.equals(other)

    def metadata_dict(self) -> dict[str, Any]:
        """Return an independent mutable copy of axis metadata."""
        return {key: _thaw_value(value) for key, value in self.metadata.items()}


@dataclass(frozen=True, slots=True, eq=False)
class Series:
    """One numerical ``y(x)`` trace plus lightweight scientific metadata.

    ``label`` is presentation-facing and may be duplicated for replicate measurements.
    ``key`` is an optional keyword-only non-display identifier intended for stable
    addressing by readers, processing pipelines, and later GUI/style controls.
    """

    x: ArrayLike
    y: ArrayLike
    label: str = ""
    x_axis: Axis = field(default_factory=lambda: Axis("x"))
    y_axis: Axis = field(default_factory=lambda: Axis("y"))
    metadata: Metadata = field(default_factory=dict)
    key: str = field(default="", kw_only=True)

    def __post_init__(self) -> None:
        x = _as_immutable_numeric_1d(self.x, field_name="x")
        y = _as_immutable_numeric_1d(self.y, field_name="y")
        if x.size != y.size:
            raise ValueError(
                f"x and y must contain the same number of points; got {x.size} and {y.size}"
            )
        if not isinstance(self.x_axis, Axis) or not isinstance(self.y_axis, Axis):
            raise TypeError("x_axis and y_axis must be Axis instances")

        object.__setattr__(self, "x", x)
        object.__setattr__(self, "y", y)
        object.__setattr__(self, "label", str(self.label).strip())
        object.__setattr__(self, "key", str(self.key).strip())
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))

    @property
    def n_points(self) -> int:
        return int(self.x.size)

    @property
    def has_missing(self) -> bool:
        """Whether either numerical vector contains one or more NaN values."""
        return bool(np.isnan(self.x).any() or np.isnan(self.y).any())

    def equals(self, other: object) -> bool:
        """Return whether another series has the same values and metadata."""
        if not isinstance(other, Series):
            return False
        try:
            x_equal = np.array_equal(self.x, other.x, equal_nan=True)
            y_equal = np.array_equal(self.y, other.y, equal_nan=True)
        except TypeError:
            x_equal = np.array_equal(self.x, other.x)
            y_equal = np.array_equal(self.y, other.y)
        return bool(
            x_equal
            and y_equal
            and self.label == other.label
            and self.key == other.key
            and self.x_axis.equals(other.x_axis)
            and self.y_axis.equals(other.y_axis)
            and _metadata_equal(self.metadata, other.metadata)
        )

    def __eq__(self, other: object) -> bool:
        return self.equals(other)

    def metadata_dict(self) -> dict[str, Any]:
        """Return an independent mutable copy of series metadata."""
        return {key: _thaw_value(value) for key, value in self.metadata.items()}

    def copy(self) -> Series:
        """Return a detached copy with independently normalized numerical arrays."""
        return Series(
            x=self.x,
            y=self.y,
            label=self.label,
            key=self.key,
            x_axis=self.x_axis,
            y_axis=self.y_axis,
            metadata=self.metadata_dict(),
        )

    def with_data(
        self,
        *,
        x: ArrayLike | None = None,
        y: ArrayLike | None = None,
        label: str | None = None,
        key: str | None = None,
    ) -> Series:
        """Return a new series while preserving axis and scientific metadata."""
        return Series(
            x=self.x if x is None else x,
            y=self.y if y is None else y,
            label=self.label if label is None else label,
            key=self.key if key is None else key,
            x_axis=self.x_axis,
            y_axis=self.y_axis,
            metadata=self.metadata_dict(),
        )

    def with_metadata(self, **updates: Any) -> Series:
        """Return a new series with updated metadata."""
        metadata = self.metadata_dict()
        metadata.update(updates)
        return Series(
            x=self.x,
            y=self.y,
            label=self.label,
            key=self.key,
            x_axis=self.x_axis,
            y_axis=self.y_axis,
            metadata=metadata,
        )


@dataclass(frozen=True, slots=True, eq=False)
class Dataset:
    """Ordered collection of scientific series for comparison or joint analysis."""

    series: Sequence[Series] = field(default_factory=tuple)
    name: str = ""
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        series = tuple(self.series)
        if not all(isinstance(item, Series) for item in series):
            raise TypeError("Dataset.series must contain only Series instances")

        nonempty_keys = [item.key for item in series if item.key]
        if len(nonempty_keys) != len(set(nonempty_keys)):
            raise ValueError("Non-empty Series.key values must be unique within a Dataset")

        object.__setattr__(self, "series", series)
        object.__setattr__(self, "name", str(self.name).strip())
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))

    def __len__(self) -> int:
        return len(self.series)

    def __iter__(self) -> Iterator[Series]:
        return iter(self.series)

    def __getitem__(self, index: int | slice) -> Series | Dataset:
        if isinstance(index, slice):
            return Dataset(
                series=self.series[index],
                name=self.name,
                metadata=self.metadata_dict(),
            )
        return self.series[index]

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(item.label for item in self.series)

    @property
    def keys(self) -> tuple[str, ...]:
        """Return series keys in dataset order, including empty keys."""
        return tuple(item.key for item in self.series)

    def equals(self, other: object) -> bool:
        """Return whether another dataset has the same ordered scientific content."""
        return (
            isinstance(other, Dataset)
            and self.name == other.name
            and len(self.series) == len(other.series)
            and all(
                a.equals(b)
                for a, b in zip(self.series, other.series, strict=True)
            )
            and _metadata_equal(self.metadata, other.metadata)
        )

    def __eq__(self, other: object) -> bool:
        return self.equals(other)

    def metadata_dict(self) -> dict[str, Any]:
        """Return an independent mutable copy of dataset metadata."""
        return {key: _thaw_value(value) for key, value in self.metadata.items()}

    def append(self, item: Series) -> Dataset:
        """Return a new dataset with one series appended."""
        if not isinstance(item, Series):
            raise TypeError("item must be a Series")
        return Dataset(
            series=(*self.series, item),
            name=self.name,
            metadata=self.metadata_dict(),
        )

    def extend(self, items: Iterable[Series]) -> Dataset:
        """Return a new dataset with several series appended."""
        items_tuple = tuple(items)
        if not all(isinstance(item, Series) for item in items_tuple):
            raise TypeError("items must contain only Series instances")
        return Dataset(
            series=(*self.series, *items_tuple),
            name=self.name,
            metadata=self.metadata_dict(),
        )

    def by_label(self, label: str) -> tuple[Series, ...]:
        """Return all series whose display label exactly matches ``label``."""
        return tuple(item for item in self.series if item.label == label)

    def by_key(self, key: str) -> Series:
        """Return the uniquely addressed series matching a non-empty key."""
        wanted = str(key).strip()
        if not wanted:
            raise ValueError("key must not be empty")
        for item in self.series:
            if item.key == wanted:
                return item
        raise KeyError(wanted)

    def select(self, labels: Iterable[str]) -> Dataset:
        """Return series whose labels are requested, preserving dataset order."""
        wanted = set(labels)
        return Dataset(
            series=tuple(item for item in self.series if item.label in wanted),
            name=self.name,
            metadata=self.metadata_dict(),
        )
