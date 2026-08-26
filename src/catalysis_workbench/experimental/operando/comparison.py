"""Fail-closed exact trace pairing and Pearson result state."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray
from scipy.stats import pearsonr

from .operations import OperandoOperationError, OperandoTrace
from .stack import FrameCoordinate, _canonical_bytes, _digest_array

FloatArray = NDArray[np.float64]


def _validate_trace_compatibility(left: OperandoTrace, right: OperandoTrace) -> None:
    if not isinstance(left, OperandoTrace) or not isinstance(right, OperandoTrace):
        raise TypeError("left and right must be OperandoTrace instances")
    if left.frame_keys != right.frame_keys:
        raise OperandoOperationError(
            "trace frame keys must match exactly in retained order; "
            "automatic intersection or alignment is not performed"
        )
    left_coordinate = left.coordinate
    right_coordinate = right.coordinate
    compatible = bool(
        left_coordinate.key == right_coordinate.key
        and left_coordinate.axis.name == right_coordinate.axis.name
        and left_coordinate.axis.unit == right_coordinate.axis.unit
        and _canonical_bytes(left_coordinate.axis.metadata)
        == _canonical_bytes(right_coordinate.axis.metadata)
        and np.array_equal(left_coordinate.values, right_coordinate.values)
    )
    if not compatible:
        raise OperandoOperationError(
            "trace coordinates must match exactly in selected key, values, axis semantic, "
            "unit, and metadata"
        )


@dataclass(frozen=True, slots=True, eq=False)
class TracePair:
    """Exact pairing whose constructor itself enforces trace compatibility."""

    left: OperandoTrace
    right: OperandoTrace
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        _validate_trace_compatibility(self.left, self.right)

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.OperandoTrace.Pair.v2\0")
        digest.update(_canonical_bytes(self.frame_keys))
        digest.update(_canonical_bytes(self.coordinate.digest))
        _digest_array(digest, self.left_values)
        _digest_array(digest, self.right_values)
        digest.update(_canonical_bytes(self.left_trace_digest))
        digest.update(_canonical_bytes(self.right_trace_digest))
        object.__setattr__(self, "digest", digest.hexdigest())

    @property
    def frame_keys(self) -> tuple[str, ...]:
        return self.left.frame_keys

    @property
    def coordinate(self) -> FrameCoordinate:
        return self.left.coordinate

    @property
    def left_values(self) -> FloatArray:
        return self.left.values

    @property
    def right_values(self) -> FloatArray:
        return self.right.values

    @property
    def left_trace_digest(self) -> str:
        return self.left.digest

    @property
    def right_trace_digest(self) -> str:
        return self.right.digest

    @property
    def sample_count(self) -> int:
        return self.left.n_frames

    def __eq__(self, other: object) -> bool:
        return isinstance(other, TracePair) and self.digest == other.digest


def pair_traces(left: OperandoTrace, right: OperandoTrace) -> TracePair:
    """Pair two traces only under exact ordered frame/coordinate compatibility."""
    return TracePair(left=left, right=right)


@dataclass(frozen=True, slots=True, eq=False)
class PearsonCorrelationResult:
    """Verified two-sided ordinary Pearson association over one exact trace pair."""

    pair: TracePair
    coefficient: float = field(init=False)
    p_value: float = field(init=False)
    method: str = field(default="pearson", init=False)
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.pair, TracePair):
            raise TypeError("pair must be a TracePair")
        if self.pair.sample_count < 2:
            raise OperandoOperationError(
                "Pearson correlation requires at least two paired observations"
            )
        if np.all(self.left_values == self.left_values[0]) or np.all(
            self.right_values == self.right_values[0]
        ):
            raise OperandoOperationError(
                "Pearson correlation is undefined for constant traces"
            )

        result = pearsonr(self.left_values, self.right_values)
        coefficient = float(result.statistic)
        p_value = float(result.pvalue)
        if not np.isfinite(coefficient) or not np.isfinite(p_value):
            raise OperandoOperationError(
                "Pearson correlation returned a non-finite result"
            )

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.OperandoTrace.Pearson.v2\0")
        digest.update(_canonical_bytes(self.pair.digest))
        digest.update(np.float64(coefficient).tobytes())
        digest.update(np.float64(p_value).tobytes())
        digest.update(_canonical_bytes(self.method))

        object.__setattr__(self, "coefficient", coefficient)
        object.__setattr__(self, "p_value", p_value)
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
    """Compute verified ordinary two-sided Pearson association for exact traces."""
    return PearsonCorrelationResult(pair=pair_traces(left, right))
