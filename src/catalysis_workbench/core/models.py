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


def _as_readonly_1d(values: ArrayLike, *, field_name: str) -> NDArray[np.float64]:
    try:
        array = np.array(values, dtype=np.float64, copy=True)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{field_name} must contain numeric values") from exc

    if array.ndim != 1:
        raise ValueError(f"{field_name} must be one-dimensional; got shape {array.shape}")
    if array.size == 0:
        raise ValueError(f"{field_name} must contain at least one point")
    if np.isinf(array).any():
        raise ValueError(f"{field_name} must not contain +/-inf")

    array.setflags(write=False)
    return array


@dataclass(frozen=True, slots=True)
class Axis:
    """Metadata describing one numerical axis."""

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

    @property
    def display_label(self) -> str:
        """Return a publication-friendly axis label."""
        base = self.label or self.name
        return f"{base} ({self.unit})" if self.unit else base

    def metadata_dict(self) -> dict[str, Any]:
        """Return an independent mutable copy of axis metadata."""
        return {key: _thaw_value(value) for key, value in self.metadata.items()}


@dataclass(frozen=True, slots=True)
class Series:
    """One numerical ``y(x)`` trace plus lightweight scientific metadata."""

    x: ArrayLike
    y: ArrayLike
    label: str = ""
    x_axis: Axis = field(default_factory=lambda: Axis("x"))
    y_axis: Axis = field(default_factory=lambda: Axis("y"))
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        x = _as_readonly_1d(self.x, field_name="x")
        y = _as_readonly_1d(self.y, field_name="y")
        if x.size != y.size:
            raise ValueError(
                f"x and y must contain the same number of points; got {x.size} and {y.size}"
            )
        if not isinstance(self.x_axis, Axis) or not isinstance(self.y_axis, Axis):
            raise TypeError("x_axis and y_axis must be Axis instances")

        object.__setattr__(self, "x", x)
        object.__setattr__(self, "y", y)
        object.__setattr__(self, "label", str(self.label).strip())
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))

    @property
    def n_points(self) -> int:
        return int(self.x.size)

    @property
    def has_missing(self) -> bool:
        """Whether either axis contains one or more NaN values."""
        return bool(np.isnan(self.x).any() or np.isnan(self.y).any())

    def metadata_dict(self) -> dict[str, Any]:
        """Return an independent mutable copy of series metadata."""
        return {key: _thaw_value(value) for key, value in self.metadata.items()}

    def copy(self) -> Series:
        """Return a detached copy with independent read-only numerical arrays."""
        return Series(
            x=self.x,
            y=self.y,
            label=self.label,
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
    ) -> Series:
        """Return a new series while preserving axis and scientific metadata."""
        return Series(
            x=self.x if x is None else x,
            y=self.y if y is None else y,
            label=self.label if label is None else label,
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
            x_axis=self.x_axis,
            y_axis=self.y_axis,
            metadata=metadata,
        )


@dataclass(frozen=True, slots=True)
class Dataset:
    """Ordered collection of scientific series for comparison or joint analysis."""

    series: Sequence[Series] = field(default_factory=tuple)
    name: str = ""
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        series = tuple(self.series)
        if not all(isinstance(item, Series) for item in series):
            raise TypeError("Dataset.series must contain only Series instances")

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

    def select(self, labels: Iterable[str]) -> Dataset:
        """Return series whose labels are requested, preserving dataset order."""
        wanted = set(labels)
        return Dataset(
            series=tuple(item for item in self.series if item.label in wanted),
            name=self.name,
            metadata=self.metadata_dict(),
        )
