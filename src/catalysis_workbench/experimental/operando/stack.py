"""Immutable exact-grid foundation for operando/time-resolved data."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from catalysis_workbench.core import Axis, Series

Metadata = Mapping[str, Any]
FloatArray = NDArray[np.float64]


class OperandoStackError(ValueError):
    """Raised when retained operando state is scientifically inconsistent."""


def _nonblank(value: object, *, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise OperandoStackError(f"{name} must not be blank")
    return text


def _immutable_real_array(
    values: ArrayLike,
    *,
    name: str,
    ndim: int,
) -> FloatArray:
    try:
        source = np.asarray(values)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must contain real numeric values") from exc
    if source.dtype.kind not in "biuf":
        if np.iscomplexobj(source):
            raise OperandoStackError(f"{name} must contain real values")
        raise TypeError(f"{name} must contain real numeric values")
    if source.ndim != ndim or source.size == 0:
        raise OperandoStackError(
            f"{name} must be a non-empty {ndim}-dimensional array"
        )
    normalized = np.ascontiguousarray(source, dtype=np.float64)
    if not np.isfinite(normalized).all():
        raise OperandoStackError(f"{name} must contain only finite values")
    frozen = np.frombuffer(normalized.tobytes(order="C"), dtype=np.float64).reshape(
        normalized.shape
    )
    frozen.setflags(write=False)
    return frozen


def _freeze_value(value: Any, *, path: str) -> Any:
    if value is None or isinstance(value, (str, bytes, bool, int)):
        return value
    if isinstance(value, (float, np.floating)):
        number = float(value)
        if not np.isfinite(number):
            raise OperandoStackError(f"{path} must contain only finite numbers")
        return number
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, Mapping):
        return MappingProxyType(
            {
                str(key): _freeze_value(item, path=f"{path}.{key}")
                for key, item in value.items()
            }
        )
    if isinstance(value, (list, tuple)):
        return tuple(
            _freeze_value(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        )
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_value(item, path=path) for item in value)
    if isinstance(value, np.ndarray):
        source = np.asarray(value)
        if source.dtype.kind not in "biufSU":
            raise TypeError(f"{path} contains an unsupported ndarray dtype")
        if np.issubdtype(source.dtype, np.complexfloating):
            raise OperandoStackError(f"{path} must not contain complex arrays")
        if np.issubdtype(source.dtype, np.number) and not np.isfinite(source).all():
            raise OperandoStackError(f"{path} must contain only finite numbers")
        contiguous = np.ascontiguousarray(source)
        frozen = np.frombuffer(
            contiguous.tobytes(order="C"), dtype=contiguous.dtype
        ).reshape(contiguous.shape)
        frozen.setflags(write=False)
        return frozen
    raise TypeError(
        f"{path} contains unsupported metadata type {type(value).__name__!r}"
    )


def _freeze_metadata(metadata: Mapping[str, Any] | None, *, name: str) -> Metadata:
    source = {} if metadata is None else dict(metadata)
    return MappingProxyType(
        {
            str(key): _freeze_value(value, path=f"{name}.{key}")
            for key, value in source.items()
        }
    )


def _thaw_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_value(item) for item in value]
    if isinstance(value, frozenset):
        return {_thaw_value(item) for item in value}
    if isinstance(value, np.ndarray):
        return np.array(value, copy=True)
    return value


def _length_prefixed(payload: bytes) -> bytes:
    return len(payload).to_bytes(8, "little", signed=False) + payload


def _canonical_bytes(value: Any) -> bytes:
    if value is None:
        return b"N"
    if isinstance(value, bool):
        return b"B1" if value else b"B0"
    if isinstance(value, int) and not isinstance(value, bool):
        return b"I" + _length_prefixed(str(value).encode("ascii"))
    if isinstance(value, float):
        return b"F" + np.float64(value).tobytes()
    if isinstance(value, str):
        return b"S" + _length_prefixed(value.encode("utf-8"))
    if isinstance(value, bytes):
        return b"Y" + _length_prefixed(value)
    if isinstance(value, Mapping):
        items = []
        for key in sorted(value):
            key_bytes = _canonical_bytes(str(key))
            value_bytes = _canonical_bytes(value[key])
            items.append(_length_prefixed(key_bytes) + _length_prefixed(value_bytes))
        return b"M" + len(items).to_bytes(8, "little") + b"".join(items)
    if isinstance(value, tuple):
        payload = b"".join(_length_prefixed(_canonical_bytes(item)) for item in value)
        return b"T" + len(value).to_bytes(8, "little") + payload
    if isinstance(value, frozenset):
        encoded = sorted(_canonical_bytes(item) for item in value)
        payload = b"".join(_length_prefixed(item) for item in encoded)
        return b"R" + len(encoded).to_bytes(8, "little") + payload
    if isinstance(value, np.ndarray):
        dtype = value.dtype.str.encode("ascii")
        shape = tuple(int(item) for item in value.shape)
        return (
            b"A"
            + _length_prefixed(dtype)
            + _length_prefixed(_canonical_bytes(shape))
            + _length_prefixed(np.ascontiguousarray(value).tobytes(order="C"))
        )
    raise TypeError(f"unsupported canonical value type {type(value).__name__!r}")


def _digest_axis(axis: Axis) -> str:
    if not isinstance(axis, Axis):
        raise TypeError("axis must be an Axis")
    digest = hashlib.sha256()
    digest.update(b"CatalysisWorkbench.Operando.Axis.v1\0")
    digest.update(_canonical_bytes(axis.name))
    digest.update(_canonical_bytes(axis.unit))
    digest.update(_canonical_bytes(axis.label))
    digest.update(_canonical_bytes(axis.metadata))
    return digest.hexdigest()


def _digest_array(digest: Any, values: np.ndarray) -> None:
    contiguous = np.ascontiguousarray(values)
    digest.update(_length_prefixed(contiguous.dtype.str.encode("ascii")))
    digest.update(_length_prefixed(_canonical_bytes(tuple(contiguous.shape))))
    digest.update(_length_prefixed(contiguous.tobytes(order="C")))


def _source_array_digest(signal: np.ndarray, values: np.ndarray) -> str:
    digest = hashlib.sha256()
    digest.update(b"CatalysisWorkbench.Operando.SourceArrays.v1\0")
    _digest_array(digest, signal)
    _digest_array(digest, values)
    return digest.hexdigest()


def series_array_digest(series: Series) -> str:
    """Return the reconstructible digest of one finite real ``Series`` array pair."""
    if not isinstance(series, Series):
        raise TypeError("series must be a Series")
    signal = _immutable_real_array(series.x, name="series.x", ndim=1)
    values = _immutable_real_array(series.y, name="series.y", ndim=1)
    if signal.size != values.size:
        raise OperandoStackError("series.x and series.y lengths must match")
    return _source_array_digest(signal, values)


def _signal_direction(signal: np.ndarray) -> str:
    if signal.size < 2:
        raise OperandoStackError("signal coordinates must contain at least two points")
    differences = np.diff(signal)
    if np.all(differences > 0):
        return "increasing"
    if np.all(differences < 0):
        return "decreasing"
    raise OperandoStackError(
        "signal coordinates must be strictly monotonic without duplicates"
    )


def _axes_compatible(left: Axis, right: Axis) -> bool:
    return bool(
        left.name == right.name
        and left.unit == right.unit
        and _canonical_bytes(left.metadata) == _canonical_bytes(right.metadata)
    )


def _validated_digest(value: object, *, name: str) -> str:
    text = _nonblank(value, name=name).lower()
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise OperandoStackError(f"{name} must be a 64-character SHA-256 hex digest")
    return text


@dataclass(frozen=True, slots=True, eq=False)
class FrameCoordinate:
    """One immutable caller-defined coordinate over retained acquisition frames."""

    key: str
    axis: Axis
    values: ArrayLike
    metadata: Metadata = field(default_factory=dict)
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        key = _nonblank(self.key, name="FrameCoordinate.key")
        if not isinstance(self.axis, Axis):
            raise TypeError("FrameCoordinate.axis must be an Axis")
        values = _immutable_real_array(
            self.values,
            name=f"frame coordinate {key!r}",
            ndim=1,
        )
        metadata = _freeze_metadata(self.metadata, name="FrameCoordinate.metadata")

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.FrameCoordinate.v1\0")
        digest.update(_canonical_bytes(key))
        digest.update(_canonical_bytes(_digest_axis(self.axis)))
        _digest_array(digest, values)
        digest.update(_canonical_bytes(metadata))

        object.__setattr__(self, "key", key)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "digest", digest.hexdigest())

    def metadata_dict(self) -> dict[str, Any]:
        """Return an independent mutable copy of coordinate metadata."""
        return {key: _thaw_value(value) for key, value in self.metadata.items()}

    def __eq__(self, other: object) -> bool:
        return isinstance(other, FrameCoordinate) and self.digest == other.digest


@dataclass(frozen=True, slots=True, eq=False)
class OperandoStack:
    """Immutable exact-grid matrix plus explicit acquisition coordinates/provenance."""

    frame_keys: Sequence[str]
    signal: ArrayLike
    signal_axis: Axis
    value_axis: Axis
    values: ArrayLike
    frame_coordinates: Sequence[FrameCoordinate]
    primary_coordinate_key: str
    source_keys: Sequence[str]
    source_digests: Sequence[str]
    metadata: Metadata = field(default_factory=dict)
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        frame_keys = tuple(_nonblank(key, name="frame key") for key in self.frame_keys)
        if not frame_keys:
            raise OperandoStackError("frame_keys must contain at least one key")
        if len(frame_keys) != len(set(frame_keys)):
            raise OperandoStackError("frame_keys must be unique and retain source order")

        signal = _immutable_real_array(self.signal, name="signal", ndim=1)
        _signal_direction(signal)
        values = _immutable_real_array(self.values, name="values", ndim=2)
        if values.shape != (len(frame_keys), signal.size):
            raise OperandoStackError(
                "values shape must be exactly (n_frames, n_signal_points)"
            )
        if not isinstance(self.signal_axis, Axis) or not isinstance(self.value_axis, Axis):
            raise TypeError("signal_axis and value_axis must be Axis instances")
        _digest_axis(self.signal_axis)
        _digest_axis(self.value_axis)

        coordinates = tuple(self.frame_coordinates)
        if not coordinates or not all(
            isinstance(coordinate, FrameCoordinate) for coordinate in coordinates
        ):
            raise OperandoStackError(
                "frame_coordinates must contain at least one FrameCoordinate"
            )
        coordinate_keys = tuple(coordinate.key for coordinate in coordinates)
        if len(coordinate_keys) != len(set(coordinate_keys)):
            raise OperandoStackError("frame coordinate keys must be unique")
        for coordinate in coordinates:
            if coordinate.values.size != len(frame_keys):
                raise OperandoStackError(
                    f"frame coordinate {coordinate.key!r} length must equal n_frames"
                )

        primary = _nonblank(
            self.primary_coordinate_key,
            name="primary_coordinate_key",
        )
        if primary not in set(coordinate_keys):
            raise OperandoStackError(
                "primary_coordinate_key must name one retained frame coordinate"
            )

        source_keys = tuple(_nonblank(key, name="source key") for key in self.source_keys)
        if len(source_keys) != len(frame_keys):
            raise OperandoStackError("source_keys length must equal n_frames")
        if len(source_keys) != len(set(source_keys)):
            raise OperandoStackError("source_keys must be unique")

        source_digests = tuple(
            _validated_digest(value, name="source digest")
            for value in self.source_digests
        )
        if len(source_digests) != len(frame_keys):
            raise OperandoStackError("source_digests length must equal n_frames")
        reconstructed = tuple(
            _source_array_digest(signal, values[index])
            for index in range(len(frame_keys))
        )
        if source_digests != reconstructed:
            raise OperandoStackError(
                "source_digests contradict the retained signal/value arrays"
            )

        metadata = _freeze_metadata(self.metadata, name="OperandoStack.metadata")

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.OperandoStack.v1\0")
        digest.update(_canonical_bytes(frame_keys))
        _digest_array(digest, signal)
        digest.update(_canonical_bytes(_digest_axis(self.signal_axis)))
        digest.update(_canonical_bytes(_digest_axis(self.value_axis)))
        _digest_array(digest, values)
        digest.update(_canonical_bytes(tuple(item.digest for item in coordinates)))
        digest.update(_canonical_bytes(primary))
        digest.update(_canonical_bytes(source_keys))
        digest.update(_canonical_bytes(source_digests))
        digest.update(_canonical_bytes(metadata))

        object.__setattr__(self, "frame_keys", frame_keys)
        object.__setattr__(self, "signal", signal)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "frame_coordinates", coordinates)
        object.__setattr__(self, "primary_coordinate_key", primary)
        object.__setattr__(self, "source_keys", source_keys)
        object.__setattr__(self, "source_digests", source_digests)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "digest", digest.hexdigest())

    @property
    def n_frames(self) -> int:
        return len(self.frame_keys)

    @property
    def n_signal_points(self) -> int:
        return int(self.signal.size)

    @property
    def signal_direction(self) -> str:
        return _signal_direction(self.signal)

    @property
    def primary_coordinate(self) -> FrameCoordinate:
        for coordinate in self.frame_coordinates:
            if coordinate.key == self.primary_coordinate_key:
                return coordinate
        raise RuntimeError("retained primary coordinate disappeared")

    def reconstructed_source_digests(self) -> tuple[str, ...]:
        """Recompute per-frame source-array digests from retained stack state."""
        return tuple(
            _source_array_digest(self.signal, self.values[index])
            for index in range(self.n_frames)
        )

    def metadata_dict(self) -> dict[str, Any]:
        """Return an independent mutable copy of stack metadata."""
        return {key: _thaw_value(value) for key, value in self.metadata.items()}

    def __eq__(self, other: object) -> bool:
        return isinstance(other, OperandoStack) and self.digest == other.digest


def build_operando_stack(
    frames: Sequence[Series],
    *,
    frame_coordinates: Sequence[FrameCoordinate],
    primary_coordinate_key: str,
    expected_source_digests: Sequence[str] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> OperandoStack:
    """Build one shared stack using literal grids and explicit compatibility only."""
    retained = tuple(frames)
    if not retained or not all(isinstance(frame, Series) for frame in retained):
        raise OperandoStackError("frames must contain at least one Series")

    frame_keys = tuple(_nonblank(frame.key, name="Series.key") for frame in retained)
    if len(frame_keys) != len(set(frame_keys)):
        raise OperandoStackError("every frame requires a unique non-empty Series.key")

    first = retained[0]
    signal = _immutable_real_array(first.x, name="frames[0].x", ndim=1)
    first_values = _immutable_real_array(first.y, name="frames[0].y", ndim=1)
    if signal.size != first_values.size:
        raise OperandoStackError("frame x/y lengths must match")
    direction = _signal_direction(signal)
    _digest_axis(first.x_axis)
    _digest_axis(first.y_axis)

    rows: list[np.ndarray] = []
    computed_digests: list[str] = []
    for index, frame in enumerate(retained):
        frame_signal = _immutable_real_array(
            frame.x,
            name=f"frames[{index}].x",
            ndim=1,
        )
        frame_values = _immutable_real_array(
            frame.y,
            name=f"frames[{index}].y",
            ndim=1,
        )
        if frame_signal.size != frame_values.size:
            raise OperandoStackError(f"frames[{index}] x/y lengths must match")
        if not np.array_equal(frame_signal, signal):
            raise OperandoStackError(
                "all frames require literally identical retained signal coordinates"
            )
        if _signal_direction(frame_signal) != direction:
            raise OperandoStackError("all frames require the same signal direction")
        if not _axes_compatible(frame.x_axis, first.x_axis):
            raise OperandoStackError(
                "all frames require compatible signal-axis semantic key, unit, and metadata"
            )
        if not _axes_compatible(frame.y_axis, first.y_axis):
            raise OperandoStackError(
                "all frames require compatible value semantic, unit, and processing basis"
            )
        rows.append(frame_values)
        computed_digests.append(_source_array_digest(frame_signal, frame_values))

    computed = tuple(computed_digests)
    if expected_source_digests is not None:
        expected = tuple(
            _validated_digest(value, name="expected source digest")
            for value in expected_source_digests
        )
        if len(expected) != len(retained):
            raise OperandoStackError("expected_source_digests length must equal n_frames")
        if expected != computed:
            raise OperandoStackError(
                "expected_source_digests contradict the supplied Series arrays"
            )

    matrix = np.vstack(rows)
    return OperandoStack(
        frame_keys=frame_keys,
        signal=signal,
        signal_axis=first.x_axis,
        value_axis=first.y_axis,
        values=matrix,
        frame_coordinates=frame_coordinates,
        primary_coordinate_key=primary_coordinate_key,
        source_keys=frame_keys,
        source_digests=computed,
        metadata=metadata or {},
    )
