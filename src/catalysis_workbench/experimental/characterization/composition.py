"""Explicit ICP/composition scalar data integration and conservative summaries."""

from __future__ import annotations

import hashlib
import string
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field, replace
from math import isfinite
from numbers import Integral
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal

import numpy as np

CompositionBasis = Literal["bulk_mass_fraction", "solution_concentration"]
BulkMassFractionUnit = Literal["1", "wt%", "mg/g", "ug/g", "mg/kg"]
SolutionConcentrationUnit = Literal["g/L", "mg/L", "ug/L"]

_DETERMINISTIC_SCALAR = str | int | float | bool | None
_BULK_FACTORS_TO_FRACTION = {
    "1": 1.0,
    "wt%": 1.0e-2,
    "mg/g": 1.0e-3,
    "ug/g": 1.0e-6,
    "mg/kg": 1.0e-6,
}
_SOLUTION_FACTORS_TO_G_PER_L = {
    "g/L": 1.0,
    "mg/L": 1.0e-3,
    "ug/L": 1.0e-6,
}


class CompositionError(ValueError):
    """Raised when composition data violate the explicit scientific contract."""


def _finite_float(value: Any, *, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a real numeric value") from exc
    if not isfinite(number):
        raise CompositionError(f"{name} must be finite")
    return number


def _nonnegative_float(value: Any, *, name: str) -> float:
    number = _finite_float(value, name=name)
    if number < 0.0:
        raise CompositionError(f"{name} must be non-negative")
    return number


def _positive_float(value: Any, *, name: str) -> float:
    number = _finite_float(value, name=name)
    if number <= 0.0:
        raise CompositionError(f"{name} must be greater than zero")
    return number


def _required_text(value: Any, *, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise CompositionError(f"{name} must not be empty")
    return text


def _optional_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _compact_unit(unit: str) -> str:
    return (
        "".join(str(unit).strip().split())
        .replace("μ", "u")
        .replace("µ", "u")
        .replace("−", "-")
        .replace("⁻", "-")
        .replace("¹", "1")
        .replace("^", "")
        .casefold()
    )


def _canonical_unit(basis: CompositionBasis, unit: str) -> str:
    token = _compact_unit(unit)
    if basis == "bulk_mass_fraction":
        aliases = {
            "1": "1",
            "fraction": "1",
            "dimensionless": "1",
            "wt%": "wt%",
            "wt.%": "wt%",
            "weight%": "wt%",
            "weightpercent": "wt%",
            "mg/g": "mg/g",
            "mgg-1": "mg/g",
            "mgg1": "mg/g",
            "ug/g": "ug/g",
            "ugg-1": "ug/g",
            "ugg1": "ug/g",
            "mg/kg": "mg/kg",
            "mgkg-1": "mg/kg",
            "mgkg1": "mg/kg",
        }
        try:
            return aliases[token]
        except KeyError as exc:
            raise CompositionError(
                f"unsupported bulk-mass-fraction unit {unit!r}; use '1', 'wt%', "
                "'mg/g', 'ug/g', or 'mg/kg'. Bare 'ppm' is intentionally not accepted."
            ) from exc
    if basis == "solution_concentration":
        aliases = {
            "g/l": "g/L",
            "gl-1": "g/L",
            "gl1": "g/L",
            "mg/l": "mg/L",
            "mgl-1": "mg/L",
            "mgl1": "mg/L",
            "ug/l": "ug/L",
            "ugl-1": "ug/L",
            "ugl1": "ug/L",
        }
        try:
            return aliases[token]
        except KeyError as exc:
            raise CompositionError(
                f"unsupported solution-concentration unit {unit!r}; use 'g/L', "
                "'mg/L', or 'ug/L'. Bare 'ppm' is intentionally not accepted."
            ) from exc
    raise CompositionError(
        "basis must be 'bulk_mass_fraction' or 'solution_concentration'"
    )


def _freeze_metadata(
    metadata: Mapping[str, _DETERMINISTIC_SCALAR] | None,
) -> Mapping[str, _DETERMINISTIC_SCALAR]:
    if metadata is None:
        return MappingProxyType({})
    if not isinstance(metadata, Mapping):
        raise TypeError("metadata must be a mapping")
    frozen: dict[str, _DETERMINISTIC_SCALAR] = {}
    for raw_key, value in metadata.items():
        key = str(raw_key).strip()
        if not key:
            raise CompositionError("metadata keys must not be empty")
        if not isinstance(value, (str, int, float, bool, type(None))):
            raise TypeError("composition metadata values must be deterministic scalars")
        if isinstance(value, float) and not isfinite(value):
            raise CompositionError("composition metadata float values must be finite")
        frozen[key] = value
    return MappingProxyType(dict(sorted(frozen.items())))


def _measurement_digest(measurements: Sequence["CompositionMeasurement"]) -> str:
    digest = hashlib.sha256()
    for item in measurements:
        fields = (
            item.key,
            item.sample_key,
            item.element,
            item.basis,
            item.unit,
            float(item.value).hex(),
            item.replicate_key,
            item.analyte,
            item.source_id,
        )
        digest.update("\0".join(fields).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _validate_sha256(value: str) -> str:
    digest = _required_text(value, name="source_sha256")
    if len(digest) != 64 or any(char not in string.hexdigits for char in digest):
        raise CompositionError(
            "source_sha256 must be a 64-character hexadecimal SHA-256 digest"
        )
    return digest.casefold()


@dataclass(frozen=True, slots=True)
class CompositionMeasurement:
    """One explicit scalar elemental-analysis result."""

    key: str
    sample_key: str
    element: str
    value: float
    unit: str
    basis: CompositionBasis
    sample_label: str = ""
    analyte: str = ""
    replicate_key: str = ""
    source_id: str = ""
    metadata: Mapping[str, _DETERMINISTIC_SCALAR] = field(default_factory=dict)

    def __post_init__(self) -> None:
        key = _required_text(self.key, name="key")
        sample_key = _required_text(self.sample_key, name="sample_key")
        element = _required_text(self.element, name="element")
        if self.basis not in {"bulk_mass_fraction", "solution_concentration"}:
            raise CompositionError(
                "basis must be 'bulk_mass_fraction' or 'solution_concentration'"
            )
        object.__setattr__(self, "key", key)
        object.__setattr__(self, "sample_key", sample_key)
        object.__setattr__(self, "element", element)
        object.__setattr__(self, "value", _nonnegative_float(self.value, name="value"))
        object.__setattr__(self, "unit", _canonical_unit(self.basis, self.unit))
        object.__setattr__(self, "sample_label", _optional_text(self.sample_label))
        object.__setattr__(self, "analyte", _optional_text(self.analyte))
        object.__setattr__(self, "replicate_key", _optional_text(self.replicate_key))
        object.__setattr__(self, "source_id", _optional_text(self.source_id))
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))

    def metadata_dict(self) -> dict[str, _DETERMINISTIC_SCALAR]:
        """Return a mutable copy of deterministic metadata."""
        return dict(self.metadata)


@dataclass(frozen=True, slots=True)
class CompositionTable:
    """Ordered immutable collection of scalar composition measurements."""

    measurements: Sequence[CompositionMeasurement]
    name: str = ""
    source_id: str = ""
    metadata: Mapping[str, _DETERMINISTIC_SCALAR] = field(default_factory=dict)

    def __post_init__(self) -> None:
        measurements = tuple(self.measurements)
        if not measurements:
            raise CompositionError("CompositionTable requires at least one measurement")
        if not all(isinstance(item, CompositionMeasurement) for item in measurements):
            raise TypeError(
                "CompositionTable.measurements must contain CompositionMeasurement instances"
            )
        keys = [item.key for item in measurements]
        if len(keys) != len(set(keys)):
            raise CompositionError("CompositionMeasurement keys must be unique")
        object.__setattr__(self, "measurements", measurements)
        object.__setattr__(self, "name", _optional_text(self.name))
        object.__setattr__(self, "source_id", _optional_text(self.source_id))
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))

    def __len__(self) -> int:
        return len(self.measurements)

    def __iter__(self) -> Iterator[CompositionMeasurement]:
        return iter(self.measurements)

    def __getitem__(
        self, index: int | slice
    ) -> CompositionMeasurement | CompositionTable:
        if isinstance(index, slice):
            return CompositionTable(
                self.measurements[index],
                name=self.name,
                source_id=self.source_id,
                metadata=dict(self.metadata),
            )
        return self.measurements[index]

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(item.key for item in self.measurements)

    @property
    def sample_keys(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.sample_key for item in self.measurements))

    @property
    def elements(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.element for item in self.measurements))

    @property
    def source_sha256(self) -> str:
        return _measurement_digest(self.measurements)


@dataclass(frozen=True, slots=True)
class CompositionSummary:
    """Explicit replicate summary for one sample/element combination."""

    sample_key: str
    element: str
    basis: CompositionBasis
    unit: str
    n: int
    mean: float
    standard_deviation: float | None
    rsd_percent: float | None
    source_keys: Sequence[str]
    source_sha256: str
    sample_label: str = ""
    analyte: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.n, bool) or not isinstance(self.n, Integral):
            raise TypeError("n must be an integer")
        n = int(self.n)
        if n < 1:
            raise CompositionError("n must be at least 1")
        sample_key = _required_text(self.sample_key, name="sample_key")
        element = _required_text(self.element, name="element")
        if self.basis not in {"bulk_mass_fraction", "solution_concentration"}:
            raise CompositionError(
                "basis must be 'bulk_mass_fraction' or 'solution_concentration'"
            )
        unit = _canonical_unit(self.basis, self.unit)
        mean = _nonnegative_float(self.mean, name="mean")

        sd = self.standard_deviation
        if sd is not None:
            sd = _nonnegative_float(sd, name="standard_deviation")
            if n < 2:
                raise CompositionError(
                    "standard_deviation must be None when n is smaller than 2"
                )

        rsd = self.rsd_percent
        if rsd is not None:
            rsd = _nonnegative_float(rsd, name="rsd_percent")
            if sd is None or mean == 0.0:
                raise CompositionError(
                    "rsd_percent requires a defined standard deviation and non-zero mean"
                )

        source_keys = tuple(
            _required_text(key, name="source_key") for key in self.source_keys
        )
        if len(source_keys) != n:
            raise CompositionError("source_keys length must equal n")
        if len(source_keys) != len(set(source_keys)):
            raise CompositionError("source_keys must be unique within a summary")

        object.__setattr__(self, "sample_key", sample_key)
        object.__setattr__(self, "element", element)
        object.__setattr__(self, "unit", unit)
        object.__setattr__(self, "n", n)
        object.__setattr__(self, "mean", mean)
        object.__setattr__(self, "standard_deviation", sd)
        object.__setattr__(self, "rsd_percent", rsd)
        object.__setattr__(self, "source_keys", source_keys)
        object.__setattr__(self, "source_sha256", _validate_sha256(self.source_sha256))
        object.__setattr__(self, "sample_label", _optional_text(self.sample_label))
        object.__setattr__(self, "analyte", _optional_text(self.analyte))


@dataclass(frozen=True, slots=True)
class CompositionSummaryTable:
    """Ordered immutable collection of replicate summaries."""

    summaries: Sequence[CompositionSummary]
    name: str = ""

    def __post_init__(self) -> None:
        summaries = tuple(self.summaries)
        if not summaries:
            raise CompositionError(
                "CompositionSummaryTable requires at least one summary"
            )
        if not all(isinstance(item, CompositionSummary) for item in summaries):
            raise TypeError(
                "CompositionSummaryTable.summaries must contain CompositionSummary instances"
            )
        pairs = [(item.sample_key, item.element) for item in summaries]
        if len(pairs) != len(set(pairs)):
            raise CompositionError(
                "CompositionSummaryTable requires one summary per sample_key/element pair"
            )
        object.__setattr__(self, "summaries", summaries)
        object.__setattr__(self, "name", _optional_text(self.name))

    def __len__(self) -> int:
        return len(self.summaries)

    def __iter__(self) -> Iterator[CompositionSummary]:
        return iter(self.summaries)

    def __getitem__(
        self, index: int | slice
    ) -> CompositionSummary | CompositionSummaryTable:
        if isinstance(index, slice):
            return CompositionSummaryTable(self.summaries[index], name=self.name)
        return self.summaries[index]

    @property
    def sample_keys(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.sample_key for item in self.summaries))

    @property
    def elements(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.element for item in self.summaries))


def convert_composition_unit(
    measurement: CompositionMeasurement,
    *,
    target_unit: str,
) -> CompositionMeasurement:
    """Explicitly convert a measurement within its declared quantity basis."""
    if not isinstance(measurement, CompositionMeasurement):
        raise TypeError("measurement must be a CompositionMeasurement")
    target = _canonical_unit(measurement.basis, target_unit)
    if target == measurement.unit:
        value = measurement.value
    elif measurement.basis == "bulk_mass_fraction":
        fraction = measurement.value * _BULK_FACTORS_TO_FRACTION[measurement.unit]
        value = fraction / _BULK_FACTORS_TO_FRACTION[target]
    else:
        g_per_l = measurement.value * _SOLUTION_FACTORS_TO_G_PER_L[measurement.unit]
        value = g_per_l / _SOLUTION_FACTORS_TO_G_PER_L[target]

    metadata = measurement.metadata_dict()
    metadata.update(
        {
            "composition_unit_conversion": f"{measurement.unit}->{target}",
            "composition_source_value": measurement.value,
            "composition_source_unit": measurement.unit,
        }
    )
    return replace(measurement, value=float(value), unit=target, metadata=metadata)


def convert_composition_table(
    table: CompositionTable,
    *,
    target_unit: str,
) -> CompositionTable:
    """Explicitly convert all measurements in a single-basis table."""
    if not isinstance(table, CompositionTable):
        raise TypeError("table must be a CompositionTable")
    if len({item.basis for item in table}) != 1:
        raise CompositionError(
            "convert_composition_table requires one quantity basis; "
            "split mixed-basis data first"
        )
    return CompositionTable(
        tuple(convert_composition_unit(item, target_unit=target_unit) for item in table),
        name=table.name,
        source_id=table.source_id,
        metadata=dict(table.metadata),
    )


def _mass_to_g(value: float, unit: str) -> float:
    number = _positive_float(value, name="sample_mass")
    factors = {"g": 1.0, "mg": 1.0e-3, "ug": 1.0e-6}
    try:
        return number * factors[_compact_unit(unit)]
    except KeyError as exc:
        raise CompositionError("sample_mass_unit must be 'g', 'mg', or 'ug'") from exc


def _volume_to_l(value: float, unit: str) -> float:
    number = _positive_float(value, name="final_digest_volume")
    factors = {"l": 1.0, "ml": 1.0e-3, "ul": 1.0e-6}
    try:
        return number * factors[_compact_unit(unit)]
    except KeyError as exc:
        raise CompositionError(
            "final_digest_volume_unit must be 'L', 'mL', or 'uL'"
        ) from exc


def solution_concentration_to_bulk_mass_fraction(
    measurement: CompositionMeasurement,
    *,
    sample_mass: float,
    sample_mass_unit: str = "g",
    final_digest_volume: float,
    final_digest_volume_unit: str = "mL",
    dilution_factor: float = 1.0,
    target_unit: str = "wt%",
) -> CompositionMeasurement:
    """Convert measured solution concentration to bulk sample mass fraction explicitly."""
    if not isinstance(measurement, CompositionMeasurement):
        raise TypeError("measurement must be a CompositionMeasurement")
    if measurement.basis != "solution_concentration":
        raise CompositionError(
            "solution_concentration_to_bulk_mass_fraction requires "
            "basis='solution_concentration'"
        )

    sample_mass_g = _mass_to_g(sample_mass, sample_mass_unit)
    digest_volume_l = _volume_to_l(final_digest_volume, final_digest_volume_unit)
    dilution = _positive_float(dilution_factor, name="dilution_factor")
    target = _canonical_unit("bulk_mass_fraction", target_unit)

    concentration_g_l = (
        measurement.value * _SOLUTION_FACTORS_TO_G_PER_L[measurement.unit]
    )
    fraction = concentration_g_l * dilution * digest_volume_l / sample_mass_g
    target_value = fraction / _BULK_FACTORS_TO_FRACTION[target]

    metadata = measurement.metadata_dict()
    metadata.update(
        {
            "composition_conversion": "solution_concentration_to_bulk_mass_fraction",
            "composition_source_value": measurement.value,
            "composition_source_unit": measurement.unit,
            "composition_sample_mass_g": sample_mass_g,
            "composition_final_digest_volume_l": digest_volume_l,
            "composition_dilution_factor": dilution,
        }
    )
    return replace(
        measurement,
        value=float(target_value),
        unit=target,
        basis="bulk_mass_fraction",
        metadata=metadata,
    )


def summarize_composition_replicates(
    table: CompositionTable,
) -> CompositionSummaryTable:
    """Summarize explicit replicates without outlier removal or hidden conversion."""
    if not isinstance(table, CompositionTable):
        raise TypeError("table must be a CompositionTable")

    groups: dict[tuple[str, str], list[CompositionMeasurement]] = {}
    order: list[tuple[str, str]] = []
    for item in table:
        pair = (item.sample_key, item.element)
        if pair not in groups:
            groups[pair] = []
            order.append(pair)
        groups[pair].append(item)

    summaries: list[CompositionSummary] = []
    for pair in order:
        items = groups[pair]
        if len({item.basis for item in items}) != 1 or len(
            {item.unit for item in items}
        ) != 1:
            raise CompositionError(
                f"replicate group {pair!r} has incompatible basis/unit; "
                "convert explicitly before summarizing"
            )
        if len({item.analyte for item in items}) != 1:
            raise CompositionError(
                f"replicate group {pair!r} contains different analyte declarations"
            )
        labels = {item.sample_label for item in items if item.sample_label}
        if len(labels) > 1:
            raise CompositionError(
                f"replicate group {pair!r} contains conflicting sample labels"
            )
        replicate_keys = [item.replicate_key for item in items if item.replicate_key]
        if len(replicate_keys) != len(set(replicate_keys)):
            raise CompositionError(
                f"replicate group {pair!r} contains duplicate replicate_key values"
            )

        values = np.asarray([item.value for item in items], dtype=np.float64)
        n = int(values.size)
        mean = float(np.mean(values))
        sd = None if n < 2 else float(np.std(values, ddof=1))
        rsd = None if sd is None or mean == 0.0 else float(100.0 * sd / mean)
        summaries.append(
            CompositionSummary(
                sample_key=pair[0],
                sample_label=next(iter(labels), ""),
                element=pair[1],
                analyte=items[0].analyte,
                basis=items[0].basis,
                unit=items[0].unit,
                n=n,
                mean=mean,
                standard_deviation=sd,
                rsd_percent=rsd,
                source_keys=tuple(item.key for item in items),
                source_sha256=_measurement_digest(items),
            )
        )
    return CompositionSummaryTable(tuple(summaries), name=table.name)


def select_composition(
    table: CompositionTable,
    *,
    sample_keys: Sequence[str] | None = None,
    elements: Sequence[str] | None = None,
) -> CompositionTable:
    """Select measurements by explicit stable sample keys and element identities."""
    if not isinstance(table, CompositionTable):
        raise TypeError("table must be a CompositionTable")
    sample_filter = (
        None
        if sample_keys is None
        else {_required_text(item, name="sample_key") for item in sample_keys}
    )
    element_filter = (
        None
        if elements is None
        else {_required_text(item, name="element") for item in elements}
    )
    if sample_filter is not None:
        unknown = sample_filter - set(table.sample_keys)
        if unknown:
            raise CompositionError(
                f"sample_keys not present in CompositionTable: {sorted(unknown)!r}"
            )
    if element_filter is not None:
        unknown = element_filter - set(table.elements)
        if unknown:
            raise CompositionError(
                f"elements not present in CompositionTable: {sorted(unknown)!r}"
            )
    selected = tuple(
        item
        for item in table
        if (sample_filter is None or item.sample_key in sample_filter)
        and (element_filter is None or item.element in element_filter)
    )
    if not selected:
        raise CompositionError("composition selection is empty")
    return CompositionTable(
        selected,
        name=table.name,
        source_id=table.source_id,
        metadata=dict(table.metadata),
    )


def _resolve_column(frame: Any, selector: str | int, *, name: str) -> Any:
    columns = list(frame.columns)
    if isinstance(selector, int) and not isinstance(selector, bool):
        if selector < 0 or selector >= len(columns):
            raise CompositionError(
                f"{name} column index {selector} is outside the available columns"
            )
        return columns[selector]
    if isinstance(selector, str):
        if selector not in frame.columns:
            raise CompositionError(f"{name} column {selector!r} was not found")
        return selector
    raise TypeError(
        f"{name} column selector must be a header string or integer position"
    )


def _source_identity(path: Path, source_id: str | None) -> str:
    if source_id is not None:
        return _required_text(source_id, name="source_id")
    return str(path.expanduser().resolve())


def _is_missing(value: Any) -> bool:
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("pandas is required for composition table readers") from exc
    return bool(pd.isna(value))


def _column_signature(frame: Any, columns: Sequence[Any | None]) -> str:
    available = list(frame.columns)
    positions: list[str] = []
    for column in columns:
        if column is None:
            positions.append("-")
        else:
            positions.append(str(available.index(column)))
    return ",".join(positions)


def _read_composition_frame(
    frame: Any,
    *,
    source_identity: str,
    sample: str | int,
    element: str | int,
    value: str | int,
    basis: CompositionBasis,
    unit: str,
    replicate: str | int | None,
    analyte: str | int | None,
    sample_label: str | int | None,
    source_display: str,
) -> CompositionTable:
    sample_col = _resolve_column(frame, sample, name="sample")
    element_col = _resolve_column(frame, element, name="element")
    value_col = _resolve_column(frame, value, name="value")
    replicate_col = (
        None
        if replicate is None
        else _resolve_column(frame, replicate, name="replicate")
    )
    analyte_col = (
        None if analyte is None else _resolve_column(frame, analyte, name="analyte")
    )
    label_col = (
        None
        if sample_label is None
        else _resolve_column(frame, sample_label, name="sample_label")
    )
    canonical_unit = _canonical_unit(basis, unit)
    column_signature = _column_signature(
        frame,
        (sample_col, element_col, value_col, replicate_col, analyte_col, label_col),
    )

    measurements: list[CompositionMeasurement] = []
    for row_position, (_, row) in enumerate(frame.iterrows()):
        sample_value = row[sample_col]
        element_value = row[element_col]
        numeric_value = row[value_col]
        if _is_missing(sample_value):
            raise CompositionError(
                f"sample value is missing at selected row position {row_position}"
            )
        if _is_missing(element_value):
            raise CompositionError(
                f"element value is missing at selected row position {row_position}"
            )
        if _is_missing(numeric_value):
            raise CompositionError(
                f"composition value is missing at selected row position {row_position}"
            )
        try:
            resolved_value = float(numeric_value)
        except (TypeError, ValueError) as exc:
            raise CompositionError(
                f"composition value at selected row position {row_position} is not numeric"
            ) from exc

        optional_values: dict[str, str] = {}
        for name, column in (
            ("replicate", replicate_col),
            ("analyte", analyte_col),
            ("sample_label", label_col),
        ):
            if column is None:
                optional_values[name] = ""
                continue
            cell = row[column]
            if _is_missing(cell):
                raise CompositionError(
                    f"{name} value is missing at selected row position {row_position}"
                )
            optional_values[name] = str(cell).strip()

        key_seed = f"{source_identity}\0{column_signature}\0{row_position}"
        key_digest = hashlib.sha256(key_seed.encode("utf-8")).hexdigest()[:20]
        measurements.append(
            CompositionMeasurement(
                key=f"composition:{key_digest}",
                sample_key=str(sample_value).strip(),
                sample_label=optional_values["sample_label"],
                element=str(element_value).strip(),
                analyte=optional_values["analyte"],
                replicate_key=optional_values["replicate"],
                value=resolved_value,
                unit=canonical_unit,
                basis=basis,
                source_id=source_identity,
                metadata={
                    "composition_source": source_display,
                    "composition_row_position": row_position,
                    "composition_column_signature": column_signature,
                },
            )
        )
    if not measurements:
        raise CompositionError("composition input table contains no data rows")
    return CompositionTable(
        tuple(measurements),
        name=Path(source_display.split("::", maxsplit=1)[0]).stem,
        source_id=source_identity,
        metadata={"composition_source": source_display},
    )


def read_composition_csv(
    path: str | Path,
    *,
    sample: str | int,
    element: str | int,
    value: str | int,
    basis: CompositionBasis,
    unit: str,
    replicate: str | int | None = None,
    analyte: str | int | None = None,
    sample_label: str | int | None = None,
    source_id: str | None = None,
    **read_csv_kwargs: Any,
) -> CompositionTable:
    """Read a caller-mapped tidy CSV into explicit scalar composition measurements."""
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("pandas is required for composition CSV import") from exc
    source = Path(path)
    frame = pd.read_csv(source, **read_csv_kwargs)
    return _read_composition_frame(
        frame,
        source_identity=_source_identity(source, source_id),
        sample=sample,
        element=element,
        value=value,
        basis=basis,
        unit=unit,
        replicate=replicate,
        analyte=analyte,
        sample_label=sample_label,
        source_display=str(source),
    )


def read_composition_excel(
    path: str | Path,
    *,
    sample: str | int,
    element: str | int,
    value: str | int,
    basis: CompositionBasis,
    unit: str,
    sheet_name: str | int = 0,
    replicate: str | int | None = None,
    analyte: str | int | None = None,
    sample_label: str | int | None = None,
    source_id: str | None = None,
    **read_excel_kwargs: Any,
) -> CompositionTable:
    """Read a caller-mapped tidy Excel sheet into composition measurements."""
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("pandas is required for composition Excel import") from exc
    source = Path(path)
    with pd.ExcelFile(source) as workbook:
        if isinstance(sheet_name, int) and not isinstance(sheet_name, bool):
            if sheet_name < 0 or sheet_name >= len(workbook.sheet_names):
                raise CompositionError(
                    f"sheet index {sheet_name} is outside the available Excel sheets"
                )
            canonical_sheet = workbook.sheet_names[sheet_name]
        elif isinstance(sheet_name, str):
            if sheet_name not in workbook.sheet_names:
                raise CompositionError(f"sheet {sheet_name!r} was not found")
            canonical_sheet = sheet_name
        else:
            raise TypeError("sheet_name must be a sheet name or zero-based integer")
        frame = pd.read_excel(
            workbook, sheet_name=canonical_sheet, **read_excel_kwargs
        )

    identity = f"{_source_identity(source, source_id)}::sheet={canonical_sheet}"
    return _read_composition_frame(
        frame,
        source_identity=identity,
        sample=sample,
        element=element,
        value=value,
        basis=basis,
        unit=unit,
        replicate=replicate,
        analyte=analyte,
        sample_label=sample_label,
        source_display=f"{source}::{canonical_sheet}",
    )
