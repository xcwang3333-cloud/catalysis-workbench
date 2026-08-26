"""Exact measured-point operations and trace comparison for v0.8 Block 2."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.stats import pearsonr

from catalysis_workbench.core import Axis, Series

from .stack import (
    FrameCoordinate,
    OperandoStack,
    OperandoStackError,
    _canonical_bytes,
    _digest_array,
    _digest_axis,
    _freeze_metadata,
    _immutable_real_array,
    _source_array_digest,
    _thaw_value,
    _validated_digest,
)

Metadata = Mapping[str, Any]
FloatArray = NDArray[np.float64]


class OperandoOperationError(OperandoStackError):
    """Raised when an exact operando operation cannot satisfy its contract."""


def _coordinate_by_key(stack: OperandoStack, key: str) -> FrameCoordinate:
    text = str(key).strip()
    if not text:
        raise OperandoOperationError("coordinate_key must not be blank")
    for coordinate in stack.frame_coordinates:
        if coordinate.key == text:
            return coordinate
    raise OperandoOperationError(f"unknown frame coordinate {text!r}")


def _selected_indices(
    stack: OperandoStack,
    *,
    frame_keys: Sequence[str] | None,
    indices: Sequence[int] | None,
) -> tuple[int, ...]:
    if (frame_keys is None) == (indices is None):
        raise OperandoOperationError(
            "select exactly one of frame_keys or indices"
        )

    if frame_keys is not None:
        keys = tuple(str(key).strip() for key in frame_keys)
        if not keys or any(not key for key in keys):
            raise OperandoOperationError("frame_keys must contain non-empty keys")
        if len(keys) != len(set(keys)):
            raise OperandoOperationError("frame_keys selection must not contain duplicates")
        lookup = {key: index for index, key in enumerate(stack.frame_keys)}
        unknown = [key for key in keys if key not in lookup]
        if unknown:
            raise OperandoOperationError(f"unknown frame key {unknown[0]!r}")
        return tuple(lookup[key] for key in keys)

    assert indices is not None
    retained: list[int] = []
    for value in indices:
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
            raise TypeError("indices must contain integers")
        index = int(value)
        if index < 0 or index >= stack.n_frames:
            raise OperandoOperationError(
                f"frame index {index} is out of range for {stack.n_frames} frames"
            )
        retained.append(index)
    selected = tuple(retained)
    if not selected:
        raise OperandoOperationError("indices must contain at least one retained index")
    if len(selected) != len(set(selected)):
        raise OperandoOperationError("indices selection must not contain duplicates")
    return selected


def _operation_metadata(
    stack: OperandoStack,
    *,
    operation: str,
    parameters: Mapping[str, Any],
) -> dict[str, Any]:
    metadata = stack.metadata_dict()
    metadata["catalysis_workbench.operando_operation"] = {
        "parent_stack_digest": stack.digest,
        "operation": operation,
        "parameters": dict(parameters),
        "parent_source_digests": tuple(stack.source_digests),
    }
    return metadata


def _rebuild_stack_from_indices(
    stack: OperandoStack,
    indices: Sequence[int],
    *,
    operation: str,
    parameters: Mapping[str, Any],
) -> OperandoStack:
    selected = np.asarray(tuple(indices), dtype=int)
    coordinates = tuple(
        FrameCoordinate(
            coordinate.key,
            coordinate.axis,
            coordinate.values[selected],
            metadata=coordinate.metadata_dict(),
        )
        for coordinate in stack.frame_coordinates
    )
    return OperandoStack(
        frame_keys=tuple(stack.frame_keys[index] for index in selected),
        signal=stack.signal,
        signal_axis=stack.signal_axis,
        value_axis=stack.value_axis,
        values=stack.values[selected],
        frame_coordinates=coordinates,
        primary_coordinate_key=stack.primary_coordinate_key,
        source_keys=tuple(stack.source_keys[index] for index in selected),
        source_digests=tuple(stack.source_digests[index] for index in selected),
        metadata=_operation_metadata(stack, operation=operation, parameters=parameters),
    )


def select_frames(
    stack: OperandoStack,
    *,
    frame_keys: Sequence[str] | None = None,
    indices: Sequence[int] | None = None,
) -> OperandoStack:
    """Select retained frames by exact key or integer index in caller-selected order."""
    if not isinstance(stack, OperandoStack):
        raise TypeError("stack must be an OperandoStack")
    selected = _selected_indices(stack, frame_keys=frame_keys, indices=indices)
    parameters: dict[str, Any]
    if frame_keys is not None:
        parameters = {"frame_keys": tuple(str(key).strip() for key in frame_keys)}
    else:
        parameters = {"indices": selected}
    return _rebuild_stack_from_indices(
        stack,
        selected,
        operation="select_frames",
        parameters=parameters,
    )


def _finite_scalar(value: object, *, name: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise TypeError(f"{name} must be a finite real scalar")
    try:
        array = np.asarray(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a finite real scalar") from exc
    if array.ndim != 0 or array.dtype.kind not in "biuf" or np.iscomplexobj(array):
        raise TypeError(f"{name} must be a finite real scalar")
    scalar = float(array)
    if not np.isfinite(scalar):
        raise OperandoOperationError(f"{name} must be finite")
    return scalar


def select_frames_by_coordinate(
    stack: OperandoStack,
    *,
    coordinate_key: str,
    comparison: str,
    value: float,
) -> OperandoStack:
    """Select frames by an explicit exact coordinate comparison without sorting."""
    if not isinstance(stack, OperandoStack):
        raise TypeError("stack must be an OperandoStack")
    coordinate = _coordinate_by_key(stack, coordinate_key)
    threshold = _finite_scalar(value, name="value")
    token = str(comparison).strip()
    comparisons = {
        "==": np.equal,
        "!=": np.not_equal,
        "<": np.less,
        "<=": np.less_equal,
        ">": np.greater,
        ">=": np.greater_equal,
    }
    if token not in comparisons:
        raise OperandoOperationError(
            "comparison must be one of '==', '!=', '<', '<=', '>', '>='"
        )
    selected = tuple(
        int(index)
        for index in np.flatnonzero(comparisons[token](coordinate.values, threshold))
    )
    if not selected:
        raise OperandoOperationError(
            "coordinate comparison selected no retained frames"
        )
    return _rebuild_stack_from_indices(
        stack,
        selected,
        operation="select_frames_by_coordinate",
        parameters={
            "coordinate_key": coordinate.key,
            "comparison": token,
            "value": threshold,
        },
    )


def crop_signal(
    stack: OperandoStack,
    *,
    lower: float,
    upper: float,
) -> OperandoStack:
    """Crop to measured signal points inside inclusive caller-supplied bounds."""
    if not isinstance(stack, OperandoStack):
        raise TypeError("stack must be an OperandoStack")
    low = _finite_scalar(lower, name="lower")
    high = _finite_scalar(upper, name="upper")
    if low > high:
        raise OperandoOperationError("lower must be less than or equal to upper")
    retained = np.flatnonzero((stack.signal >= low) & (stack.signal <= high))
    if retained.size == 0:
        raise OperandoOperationError("signal crop retained no measured points")
    if retained.size < 2:
        raise OperandoOperationError(
            "signal crop must retain at least two points for an OperandoStack; "
            "use signal_position_cut for one retained point"
        )

    signal = stack.signal[retained]
    values = stack.values[:, retained]
    source_digests = tuple(
        _source_array_digest(signal, values[index])
        for index in range(stack.n_frames)
    )
    return OperandoStack(
        frame_keys=stack.frame_keys,
        signal=signal,
        signal_axis=stack.signal_axis,
        value_axis=stack.value_axis,
        values=values,
        frame_coordinates=stack.frame_coordinates,
        primary_coordinate_key=stack.primary_coordinate_key,
        source_keys=stack.source_keys,
        source_digests=source_digests,
        metadata=_operation_metadata(
            stack,
            operation="crop_signal",
            parameters={"lower": low, "upper": high},
        ),
    )


def _one_frame_index(
    stack: OperandoStack,
    *,
    frame_key: str | None,
    index: int | None,
) -> int:
    if (frame_key is None) == (index is None):
        raise OperandoOperationError("select exactly one of frame_key or index")
    if frame_key is not None:
        key = str(frame_key).strip()
        if not key:
            raise OperandoOperationError("frame_key must not be blank")
        try:
            return stack.frame_keys.index(key)
        except ValueError as exc:
            raise OperandoOperationError(f"unknown frame key {key!r}") from exc
    assert index is not None
    if isinstance(index, (bool, np.bool_)) or not isinstance(index, (int, np.integer)):
        raise TypeError("index must be an integer")
    resolved = int(index)
    if resolved < 0 or resolved >= stack.n_frames:
        raise OperandoOperationError(
            f"frame index {resolved} is out of range for {stack.n_frames} frames"
        )
    return resolved


def frame_cut(
    stack: OperandoStack,
    *,
    frame_key: str | None = None,
    index: int | None = None,
) -> Series:
    """Return one exact retained spectrum/pattern as the released ``Series`` type."""
    if not isinstance(stack, OperandoStack):
        raise TypeError("stack must be an OperandoStack")
    resolved = _one_frame_index(stack, frame_key=frame_key, index=index)
    key = stack.frame_keys[resolved]
    return Series(
        stack.signal,
        stack.values[resolved],
        label=key,
        key=key,
        x_axis=stack.signal_axis,
        y_axis=stack.value_axis,
        metadata={
            "catalysis_workbench.operando_cut": {
                "source_stack_digest": stack.digest,
                "frame_key": key,
                "frame_index": resolved,
                "source_digest": stack.source_digests[resolved],
            }
        },
    )


def _result_digest(
    *,
    source_frame_digest: str,
    method: str,
    parameters: Mapping[str, Any],
    value: float,
) -> str:
    digest = hashlib.sha256()
    digest.update(b"CatalysisWorkbench.OperandoTrace.Result.v1\0")
    digest.update(_canonical_bytes(source_frame_digest))
    digest.update(_canonical_bytes(method))
    digest.update(_canonical_bytes(parameters))
    digest.update(np.float64(value).tobytes())
    return digest.hexdigest()


@dataclass(frozen=True, slots=True, eq=False)
class OperandoTrace:
    """Immutable one-scalar-per-frame derived operando state with provenance."""

    frame_keys: Sequence[str]
    coordinate: FrameCoordinate
    value_axis: Axis
    values: ArrayLike
    method: str
    parameters: Metadata
    source_stack_digest: str
    source_frame_digests: Sequence[str]
    source_result_digests: Sequence[str] | None = None
    metadata: Metadata = field(default_factory=dict)
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        frame_keys = tuple(str(key).strip() for key in self.frame_keys)
        if not frame_keys or any(not key for key in frame_keys):
            raise OperandoOperationError("trace frame_keys must contain non-empty keys")
        if len(frame_keys) != len(set(frame_keys)):
            raise OperandoOperationError("trace frame_keys must be unique")
        if not isinstance(self.coordinate, FrameCoordinate):
            raise TypeError("coordinate must be a FrameCoordinate")
        if self.coordinate.values.size != len(frame_keys):
            raise OperandoOperationError("trace coordinate length must equal n_frames")
        if not isinstance(self.value_axis, Axis):
            raise TypeError("value_axis must be an Axis")
        _digest_axis(self.value_axis)
        values = _immutable_real_array(self.values, name="trace values", ndim=1)
        if values.size != len(frame_keys):
            raise OperandoOperationError("trace values length must equal n_frames")
        method = str(self.method).strip()
        if not method:
            raise OperandoOperationError("trace method must not be blank")
        parameters = _freeze_metadata(self.parameters, name="OperandoTrace.parameters")
        metadata = _freeze_metadata(self.metadata, name="OperandoTrace.metadata")
        source_stack_digest = _validated_digest(
            self.source_stack_digest,
            name="source_stack_digest",
        )
        source_frame_digests = tuple(
            _validated_digest(value, name="source frame digest")
            for value in self.source_frame_digests
        )
        if len(source_frame_digests) != len(frame_keys):
            raise OperandoOperationError(
                "source_frame_digests length must equal n_frames"
            )
        reconstructed = tuple(
            _result_digest(
                source_frame_digest=source_frame_digests[index],
                method=method,
                parameters=parameters,
                value=float(values[index]),
            )
            for index in range(len(frame_keys))
        )
        if self.source_result_digests is None:
            source_result_digests = reconstructed
        else:
            source_result_digests = tuple(
                _validated_digest(value, name="source result digest")
                for value in self.source_result_digests
            )
            if len(source_result_digests) != len(frame_keys):
                raise OperandoOperationError(
                    "source_result_digests length must equal n_frames"
                )
            if source_result_digests != reconstructed:
                raise OperandoOperationError(
                    "source_result_digests contradict retained trace state"
                )

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.OperandoTrace.v1\0")
        digest.update(_canonical_bytes(frame_keys))
        digest.update(_canonical_bytes(self.coordinate.digest))
        digest.update(_canonical_bytes(_digest_axis(self.value_axis)))
        _digest_array(digest, values)
        digest.update(_canonical_bytes(method))
        digest.update(_canonical_bytes(parameters))
        digest.update(_canonical_bytes(source_stack_digest))
        digest.update(_canonical_bytes(source_frame_digests))
        digest.update(_canonical_bytes(source_result_digests))
        digest.update(_canonical_bytes(metadata))

        object.__setattr__(self, "frame_keys", frame_keys)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "method", method)
        object.__setattr__(self, "parameters", parameters)
        object.__setattr__(self, "source_stack_digest", source_stack_digest)
        object.__setattr__(self, "source_frame_digests", source_frame_digests)
        object.__setattr__(self, "source_result_digests", source_result_digests)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "digest", digest.hexdigest())

    @property
    def n_frames(self) -> int:
        return len(self.frame_keys)

    def reconstructed_result_digests(self) -> tuple[str, ...]:
        """Recompute per-frame result digests from retained trace state."""
        return tuple(
            _result_digest(
                source_frame_digest=self.source_frame_digests[index],
                method=self.method,
                parameters=self.parameters,
                value=float(self.values[index]),
            )
            for index in range(self.n_frames)
        )

    def parameters_dict(self) -> dict[str, Any]:
        return {key: _thaw_value(value) for key, value in self.parameters.items()}

    def metadata_dict(self) -> dict[str, Any]:
        return {key: _thaw_value(value) for key, value in self.metadata.items()}

    def __eq__(self, other: object) -> bool:
        return isinstance(other, OperandoTrace) and self.digest == other.digest


def build_operando_trace(
    stack: OperandoStack,
    *,
    coordinate_key: str,
    values: ArrayLike,
    value_axis: Axis,
    method: str,
    parameters: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> OperandoTrace:
    """Build a derived trace over one explicitly selected retained frame coordinate."""
    if not isinstance(stack, OperandoStack):
        raise TypeError("stack must be an OperandoStack")
    coordinate = _coordinate_by_key(stack, coordinate_key)
    return OperandoTrace(
        frame_keys=stack.frame_keys,
        coordinate=coordinate,
        value_axis=value_axis,
        values=values,
        method=method,
        parameters=parameters or {},
        source_stack_digest=stack.digest,
        source_frame_digests=stack.source_digests,
        metadata=metadata or {},
    )


def signal_position_cut(
    stack: OperandoStack,
    *,
    position: float,
    coordinate_key: str,
) -> OperandoTrace:
    """Return exact retained values at one explicitly retained signal position."""
    if not isinstance(stack, OperandoStack):
        raise TypeError("stack must be an OperandoStack")
    requested = _finite_scalar(position, name="position")
    matches = np.flatnonzero(stack.signal == requested)
    if matches.size != 1:
        raise OperandoOperationError(
            "position must equal exactly one retained signal coordinate; "
            "nearest-neighbor matching is not performed"
        )
    signal_index = int(matches[0])
    return build_operando_trace(
        stack,
        coordinate_key=coordinate_key,
        values=stack.values[:, signal_index],
        value_axis=stack.value_axis,
        method="signal_position_cut",
        parameters={
            "signal_position": requested,
            "signal_index": signal_index,
            "signal_axis_name": stack.signal_axis.name,
            "signal_axis_unit": stack.signal_axis.unit,
        },
    )


def _coordinates_compatible(left: FrameCoordinate, right: FrameCoordinate) -> bool:
    return bool(
        left.key == right.key
        and left.axis.name == right.axis.name
        and left.axis.unit == right.axis.unit
        and _canonical_bytes(left.axis.metadata) == _canonical_bytes(right.axis.metadata)
        and np.array_equal(left.values, right.values)
    )


@dataclass(frozen=True, slots=True, eq=False)
class TracePair:
    """Exact pairing of two already compatible derived operando traces."""

    frame_keys: Sequence[str]
    coordinate: FrameCoordinate
    left_values: ArrayLike
    right_values: ArrayLike
    left_trace_digest: str
    right_trace_digest: str
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        frame_keys = tuple(str(key).strip() for key in self.frame_keys)
        if not frame_keys or any(not key for key in frame_keys):
            raise OperandoOperationError("pair frame_keys must contain non-empty keys")
        if len(frame_keys) != len(set(frame_keys)):
            raise OperandoOperationError("pair frame_keys must be unique")
        if not isinstance(self.coordinate, FrameCoordinate):
            raise TypeError("coordinate must be a FrameCoordinate")
        if self.coordinate.values.size != len(frame_keys):
            raise OperandoOperationError("pair coordinate length must equal sample count")
        left = _immutable_real_array(self.left_values, name="left paired values", ndim=1)
        right = _immutable_real_array(self.right_values, name="right paired values", ndim=1)
        if left.size != len(frame_keys) or right.size != len(frame_keys):
            raise OperandoOperationError("paired value lengths must equal sample count")
        left_digest = _validated_digest(self.left_trace_digest, name="left_trace_digest")
        right_digest = _validated_digest(self.right_trace_digest, name="right_trace_digest")

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.OperandoTrace.Pair.v1\0")
        digest.update(_canonical_bytes(frame_keys))
        digest.update(_canonical_bytes(self.coordinate.digest))
        _digest_array(digest, left)
        _digest_array(digest, right)
        digest.update(_canonical_bytes(left_digest))
        digest.update(_canonical_bytes(right_digest))

        object.__setattr__(self, "frame_keys", frame_keys)
        object.__setattr__(self, "left_values", left)
        object.__setattr__(self, "right_values", right)
        object.__setattr__(self, "left_trace_digest", left_digest)
        object.__setattr__(self, "right_trace_digest", right_digest)
        object.__setattr__(self, "digest", digest.hexdigest())

    @property
    def sample_count(self) -> int:
        return len(self.frame_keys)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, TracePair) and self.digest == other.digest


def pair_traces(left: OperandoTrace, right: OperandoTrace) -> TracePair:
    """Pair two traces only under exact ordered frame/coordinate compatibility."""
    if not isinstance(left, OperandoTrace) or not isinstance(right, OperandoTrace):
        raise TypeError("left and right must be OperandoTrace instances")
    if left.frame_keys != right.frame_keys:
        raise OperandoOperationError(
            "trace frame keys must match exactly in retained order; "
            "automatic intersection or alignment is not performed"
        )
    if not _coordinates_compatible(left.coordinate, right.coordinate):
        raise OperandoOperationError(
            "trace coordinates must match exactly in selected key, values, axis semantic, "
            "unit, and metadata"
        )
    return TracePair(
        frame_keys=left.frame_keys,
        coordinate=left.coordinate,
        left_values=left.values,
        right_values=right.values,
        left_trace_digest=left.digest,
        right_trace_digest=right.digest,
    )


@dataclass(frozen=True, slots=True, eq=False)
class PearsonCorrelationResult:
    """Explicit two-sided ordinary Pearson association over one exact trace pair."""

    pair: TracePair
    coefficient: float
    p_value: float
    method: str = "pearson"
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.pair, TracePair):
            raise TypeError("pair must be a TracePair")
        coefficient = _finite_scalar(self.coefficient, name="coefficient")
        p_value = _finite_scalar(self.p_value, name="p_value")
        method = str(self.method).strip()
        if method != "pearson":
            raise OperandoOperationError("method must be 'pearson'")
        if coefficient < -1.0 or coefficient > 1.0:
            raise OperandoOperationError("Pearson coefficient must lie in [-1, 1]")
        if p_value < 0.0 or p_value > 1.0:
            raise OperandoOperationError("Pearson p_value must lie in [0, 1]")

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.OperandoTrace.Pearson.v1\0")
        digest.update(_canonical_bytes(self.pair.digest))
        digest.update(np.float64(coefficient).tobytes())
        digest.update(np.float64(p_value).tobytes())
        digest.update(_canonical_bytes(method))

        object.__setattr__(self, "coefficient", coefficient)
        object.__setattr__(self, "p_value", p_value)
        object.__setattr__(self, "method", method)
        object.__setattr__(self, "digest", digest.hexdigest())

    @property
    def sample_count(self) -> int:
        return self.pair.sample_count

    @property
    def frame_keys(self) -> tuple[str, ...]:
        return self.pair.frame_keys

    @property
    def coordinate(self) -> FrameCoordinate:
        return self.pair.coordinate

    @property
    def left_values(self) -> FloatArray:
        return self.pair.left_values

    @property
    def right_values(self) -> FloatArray:
        return self.pair.right_values

    @property
    def source_digests(self) -> tuple[str, str]:
        return (self.pair.left_trace_digest, self.pair.right_trace_digest)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, PearsonCorrelationResult) and self.digest == other.digest


def pearson_correlation(
    left: OperandoTrace,
    right: OperandoTrace,
) -> PearsonCorrelationResult:
    """Compute ordinary two-sided Pearson correlation over one exact trace pairing."""
    pair = pair_traces(left, right)
    if pair.sample_count < 2:
        raise OperandoOperationError(
            "Pearson correlation requires at least two paired observations"
        )
    if np.all(pair.left_values == pair.left_values[0]) or np.all(
        pair.right_values == pair.right_values[0]
    ):
        raise OperandoOperationError("Pearson correlation is undefined for constant traces")
    result = pearsonr(pair.left_values, pair.right_values)
    coefficient = float(result.statistic)
    p_value = float(result.pvalue)
    if not np.isfinite(coefficient) or not np.isfinite(p_value):
        raise OperandoOperationError("Pearson correlation returned a non-finite result")
    return PearsonCorrelationResult(
        pair=pair,
        coefficient=coefficient,
        p_value=p_value,
    )
