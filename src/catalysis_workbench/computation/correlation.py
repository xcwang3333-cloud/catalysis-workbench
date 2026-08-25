"""Explicit geometry–descriptor correlation state with no hidden matching."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType

import numpy as np
import pandas as pd

from .bonding import BondingError, ICOHPResult, select_icohp_bonds, sum_icohp_spins


class CorrelationError(ValueError):
    """Raised when correlation state is incomplete or scientifically ambiguous."""


def _text(value: object, *, name: str, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    text = str(value).strip()
    if not text:
        raise CorrelationError(f"{name} must not be blank")
    return text


def _finite(value: object, *, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a finite float") from exc
    if not np.isfinite(number):
        raise CorrelationError(f"{name} must be finite")
    return number


def _metadata(values: Mapping[object, object] | None) -> Mapping[str, str]:
    if values is None:
        return MappingProxyType({})
    try:
        items = tuple(dict(values).items())
    except (TypeError, ValueError) as exc:
        raise TypeError("metadata must be mapping-like") from exc
    parsed: dict[str, str] = {}
    for raw_key, raw_value in items:
        key = str(_text(raw_key, name="metadata key"))
        value = str(_text(raw_value, name=f"metadata[{key}]"))
        if key in parsed:
            raise CorrelationError(f"metadata contains duplicate key: {key}")
        parsed[key] = value
    return MappingProxyType(dict(sorted(parsed.items())))


def _digest_text(digest: object, value: str | None) -> None:
    if value is None:
        digest.update(b"none\0")
        return
    encoded = value.encode("utf-8")
    digest.update(len(encoded).to_bytes(8, "little", signed=False))
    digest.update(encoded)


def _digest_float(digest: object, value: float) -> None:
    digest.update(np.float64(value).tobytes())


@dataclass(frozen=True, slots=True, eq=False)
class CorrelationPoint:
    """One caller-declared x/y pair with explicit source and mapping provenance."""

    key: str
    x_value: float
    y_value: float
    x_source_key: str
    x_source_digest: str
    y_source_key: str
    y_source_digest: str
    mapping_key: str
    mapping_provenance: str
    metadata: Mapping[object, object] | None = None
    source_label: str | None = None
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        key = str(_text(self.key, name="key"))
        x_value = _finite(self.x_value, name="x_value")
        y_value = _finite(self.y_value, name="y_value")
        x_source_key = str(_text(self.x_source_key, name="x_source_key"))
        x_source_digest = str(_text(self.x_source_digest, name="x_source_digest"))
        y_source_key = str(_text(self.y_source_key, name="y_source_key"))
        y_source_digest = str(_text(self.y_source_digest, name="y_source_digest"))
        mapping_key = str(_text(self.mapping_key, name="mapping_key"))
        mapping_provenance = str(
            _text(self.mapping_provenance, name="mapping_provenance")
        )
        metadata = _metadata(self.metadata)
        source_label = _text(self.source_label, name="source_label", optional=True)

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.CorrelationPoint.v1\0")
        for value in (
            key,
            x_source_key,
            x_source_digest,
            y_source_key,
            y_source_digest,
            mapping_key,
            mapping_provenance,
        ):
            _digest_text(digest, value)
        _digest_float(digest, x_value)
        _digest_float(digest, y_value)
        for meta_key, meta_value in metadata.items():
            _digest_text(digest, meta_key)
            _digest_text(digest, meta_value)

        object.__setattr__(self, "key", key)
        object.__setattr__(self, "x_value", x_value)
        object.__setattr__(self, "y_value", y_value)
        object.__setattr__(self, "x_source_key", x_source_key)
        object.__setattr__(self, "x_source_digest", x_source_digest)
        object.__setattr__(self, "y_source_key", y_source_key)
        object.__setattr__(self, "y_source_digest", y_source_digest)
        object.__setattr__(self, "mapping_key", mapping_key)
        object.__setattr__(self, "mapping_provenance", mapping_provenance)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "source_label", source_label)
        object.__setattr__(self, "digest", digest.hexdigest())

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, CorrelationPoint)
            and self.digest == other.digest
            and self.source_label == other.source_label
        )


@dataclass(frozen=True, slots=True, eq=False)
class CorrelationExclusion:
    """One caller-declared excluded candidate kept outside retained numeric pairs."""

    key: str
    mapping_key: str
    reason: str
    x_source_key: str | None = None
    y_source_key: str | None = None
    metadata: Mapping[object, object] | None = None
    source_label: str | None = None
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        key = str(_text(self.key, name="key"))
        mapping_key = str(_text(self.mapping_key, name="mapping_key"))
        reason = str(_text(self.reason, name="reason"))
        x_source_key = _text(self.x_source_key, name="x_source_key", optional=True)
        y_source_key = _text(self.y_source_key, name="y_source_key", optional=True)
        if x_source_key is None and y_source_key is None:
            raise CorrelationError(
                "an exclusion must retain at least one x_source_key or y_source_key"
            )
        metadata = _metadata(self.metadata)
        source_label = _text(self.source_label, name="source_label", optional=True)

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.CorrelationExclusion.v1\0")
        for value in (key, mapping_key, reason, x_source_key, y_source_key):
            _digest_text(digest, value)
        for meta_key, meta_value in metadata.items():
            _digest_text(digest, meta_key)
            _digest_text(digest, meta_value)

        object.__setattr__(self, "key", key)
        object.__setattr__(self, "mapping_key", mapping_key)
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "x_source_key", x_source_key)
        object.__setattr__(self, "y_source_key", y_source_key)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "source_label", source_label)
        object.__setattr__(self, "digest", digest.hexdigest())

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, CorrelationExclusion)
            and self.digest == other.digest
            and self.source_label == other.source_label
        )


@dataclass(frozen=True, slots=True, eq=False)
class CorrelationDataset:
    """Ordered explicit x/y pairs plus separately retained exclusions."""

    x_definition: str
    x_unit: str
    y_definition: str
    y_unit: str
    provenance_id: str
    points: Sequence[CorrelationPoint]
    exclusions: Sequence[CorrelationExclusion] = ()
    source_label: str | None = None
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        x_definition = str(_text(self.x_definition, name="x_definition"))
        x_unit = str(_text(self.x_unit, name="x_unit"))
        y_definition = str(_text(self.y_definition, name="y_definition"))
        y_unit = str(_text(self.y_unit, name="y_unit"))
        provenance_id = str(_text(self.provenance_id, name="provenance_id"))
        points = tuple(self.points)
        exclusions = tuple(self.exclusions)
        if not points or not all(isinstance(item, CorrelationPoint) for item in points):
            raise CorrelationError("points must contain at least one CorrelationPoint")
        if not all(isinstance(item, CorrelationExclusion) for item in exclusions):
            raise TypeError("exclusions must contain only CorrelationExclusion instances")
        keys = [item.key for item in (*points, *exclusions)]
        if len(keys) != len(set(keys)):
            raise CorrelationError("point/exclusion keys must be unique within a dataset")
        source_label = _text(self.source_label, name="source_label", optional=True)

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.CorrelationDataset.v1\0")
        for value in (x_definition, x_unit, y_definition, y_unit, provenance_id):
            _digest_text(digest, value)
        for point in points:
            _digest_text(digest, point.digest)
        for exclusion in exclusions:
            _digest_text(digest, exclusion.digest)

        object.__setattr__(self, "x_definition", x_definition)
        object.__setattr__(self, "x_unit", x_unit)
        object.__setattr__(self, "y_definition", y_definition)
        object.__setattr__(self, "y_unit", y_unit)
        object.__setattr__(self, "provenance_id", provenance_id)
        object.__setattr__(self, "points", points)
        object.__setattr__(self, "exclusions", exclusions)
        object.__setattr__(self, "source_label", source_label)
        object.__setattr__(self, "digest", digest.hexdigest())

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, CorrelationDataset)
            and self.digest == other.digest
            and self.source_label == other.source_label
            and self.points == other.points
            and self.exclusions == other.exclusions
        )


def build_correlation_dataset(
    points: Sequence[CorrelationPoint],
    *,
    x_definition: str,
    x_unit: str,
    y_definition: str,
    y_unit: str,
    provenance_id: str,
    exclusions: Sequence[CorrelationExclusion] = (),
    source_label: str | None = None,
) -> CorrelationDataset:
    """Build a dataset only from caller-declared point and exclusion state."""
    return CorrelationDataset(
        x_definition=x_definition,
        x_unit=x_unit,
        y_definition=y_definition,
        y_unit=y_unit,
        provenance_id=provenance_id,
        points=points,
        exclusions=exclusions,
        source_label=source_label,
    )


def icohp_length_correlation(
    result: ICOHPResult,
    *,
    spins: Sequence[str],
    provenance_id: str,
    bond_keys: Sequence[str] | None = None,
    source_labels: Sequence[str] | None = None,
    source_label: str | None = None,
) -> CorrelationDataset:
    """Build source-sign bond-length versus explicitly selected ICOHP(E_F) pairs."""
    if not isinstance(result, ICOHPResult):
        raise TypeError("result must be an ICOHPResult")
    requested_spins = tuple(str(_text(spin, name="spin")).lower() for spin in spins)
    if not requested_spins or len(set(requested_spins)) != len(requested_spins):
        raise CorrelationError("spins must be a non-empty unique sequence")
    try:
        selected = select_icohp_bonds(
            result,
            bond_keys=bond_keys,
            source_labels=source_labels,
        )
        summed_values = tuple(
            (summary, sum_icohp_spins(summary, spins=requested_spins))
            for summary in selected
        )
    except BondingError as exc:
        raise CorrelationError(f"invalid ICOHP correlation request: {exc}") from exc

    points: list[CorrelationPoint] = []
    for summary, summed in summed_values:
        points.append(
            CorrelationPoint(
                key=summary.bond_key,
                x_value=summary.bond_length_angstrom,
                y_value=summed.value,
                x_source_key=f"{summary.bond_key}:bond_length_angstrom",
                x_source_digest=summary.digest,
                y_source_key=(
                    f"{summary.bond_key}:icohp_ef:{'+'.join(summed.contributing_spins)}"
                ),
                y_source_digest=summed.digest,
                mapping_key=summary.bond_key,
                mapping_provenance="same reviewed ICOHPBondSummary identity",
                metadata={
                    "number_of_bonds": str(summary.number_of_bonds),
                    "contributing_spins": ",".join(summed.contributing_spins),
                    "source_result_digest": result.digest,
                    "source_summary_digest": summary.digest,
                },
                source_label=summary.source_label,
            )
        )
    return CorrelationDataset(
        x_definition="LOBSTER ICOHP bond length",
        x_unit="angstrom",
        y_definition="source-sign ICOHP(E_F)",
        y_unit="eV",
        provenance_id=provenance_id,
        points=points,
        source_label=source_label,
    )


def correlation_points_frame(dataset: CorrelationDataset) -> pd.DataFrame:
    """Return a detached one-row-per-retained-point reporting table."""
    if not isinstance(dataset, CorrelationDataset):
        raise TypeError("dataset must be a CorrelationDataset")
    return pd.DataFrame(
        [
            {
                "dataset_digest": dataset.digest,
                "point_digest": point.digest,
                "point_key": point.key,
                "source_label": point.source_label,
                "x_definition": dataset.x_definition,
                "x_unit": dataset.x_unit,
                "x_value": point.x_value,
                "x_source_key": point.x_source_key,
                "x_source_digest": point.x_source_digest,
                "y_definition": dataset.y_definition,
                "y_unit": dataset.y_unit,
                "y_value": point.y_value,
                "y_source_key": point.y_source_key,
                "y_source_digest": point.y_source_digest,
                "mapping_key": point.mapping_key,
                "mapping_provenance": point.mapping_provenance,
                "metadata": dict(point.metadata),
                "provenance_id": dataset.provenance_id,
            }
            for point in dataset.points
        ]
    )


def correlation_exclusions_frame(dataset: CorrelationDataset) -> pd.DataFrame:
    """Return exclusions separately from retained numeric point rows."""
    if not isinstance(dataset, CorrelationDataset):
        raise TypeError("dataset must be a CorrelationDataset")
    return pd.DataFrame(
        [
            {
                "dataset_digest": dataset.digest,
                "exclusion_digest": item.digest,
                "exclusion_key": item.key,
                "source_label": item.source_label,
                "mapping_key": item.mapping_key,
                "reason": item.reason,
                "x_source_key": item.x_source_key,
                "y_source_key": item.y_source_key,
                "metadata": dict(item.metadata),
                "provenance_id": dataset.provenance_id,
            }
            for item in dataset.exclusions
        ]
    )


__all__ = [
    "CorrelationDataset",
    "CorrelationError",
    "CorrelationExclusion",
    "CorrelationPoint",
    "build_correlation_dataset",
    "correlation_exclusions_frame",
    "correlation_points_frame",
    "icohp_length_correlation",
]
