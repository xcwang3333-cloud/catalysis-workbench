"""Traceable intrinsic TOF and apparent TOFapp calculations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from numbers import Real
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray

from catalysis_workbench.core import Axis, Dataset, Series

from .provenance import make_analysis_provenance, source_data_ref
from .quantities import (
    FARADAY_CONSTANT_C_MOL,
    EchemQuantityError,
    amount_to_mol,
    area_to_cm2,
    current_density_to_a_cm2,
    current_to_a,
    molar_rate_to_mol_s,
    normalize_unit,
)
from .quantities import (
    electron_number as validate_electron_number,
)

AVOGADRO_CONSTANT_MOL_INV = 6.02214076e23

TurnoverInventoryBasis = Literal["active_sites", "total_metal", "bulk_inventory"]
TurnoverCurrentMode = Literal["nonnegative", "magnitude"]
TurnoverSourceKind = Literal["molar_rate", "partial_current"]

_COUNT_UNITS = {
    "count",
    "site",
    "sites",
    "atom",
    "atoms",
}
_GEOMETRIC = {"geometric", "geometric_area", "geometric_area_cm2"}
_FREQUENCY_OUTPUT = {
    normalize_unit("s^-1"): (1.0, "s^-1"),
    normalize_unit("min^-1"): (60.0, "min^-1"),
    normalize_unit("h^-1"): (3600.0, "h^-1"),
}


class TurnoverFrequencyError(ValueError):
    """Raised when TOF/TOFapp inputs violate the scientific contract."""


def _basis(value: object) -> TurnoverInventoryBasis:
    if isinstance(value, str):
        if value == "active_sites":
            return "active_sites"
        if value == "total_metal":
            return "total_metal"
        if value == "bulk_inventory":
            return "bulk_inventory"
    raise TurnoverFrequencyError(
        "inventory_basis must be 'active_sites', 'total_metal', or 'bulk_inventory'"
    )


def _current_mode(value: object) -> TurnoverCurrentMode:
    if isinstance(value, str):
        if value == "nonnegative":
            return "nonnegative"
        if value == "magnitude":
            return "magnitude"
    raise TurnoverFrequencyError(
        "current_mode must be 'nonnegative' or 'magnitude'"
    )


def _immutable(values: ArrayLike, *, name: str) -> NDArray[np.float64]:
    try:
        source = np.asarray(values)
    except (TypeError, ValueError) as exc:
        raise TurnoverFrequencyError(f"{name} must contain real numeric values") from exc
    if source.size == 0 or np.iscomplexobj(source) or source.dtype.kind not in "iuf":
        raise TurnoverFrequencyError(f"{name} must contain real numeric values")
    normalized = np.ascontiguousarray(source, dtype=np.float64)
    if not np.isfinite(normalized).all():
        raise TurnoverFrequencyError(f"{name} must contain only finite values")
    result = np.frombuffer(normalized.tobytes(order="C"), dtype=np.float64)
    result = result.reshape(normalized.shape)
    result.setflags(write=False)
    return result


def _positive_scalar(value: object, *, name: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise TurnoverFrequencyError(f"{name} must be a real numeric scalar")
    numeric = float(value)
    if not isfinite(numeric) or numeric <= 0:
        raise TurnoverFrequencyError(f"{name} must be finite and greater than zero")
    return numeric


def _inventory_to_mol(value: object, unit: object) -> tuple[float, str]:
    numeric = _positive_scalar(value, name="inventory_value")
    if not isinstance(unit, str) or not unit.strip():
        raise TurnoverFrequencyError("inventory_unit must be a non-empty string")
    requested = unit.strip()
    token = requested.casefold().replace(" ", "")
    if token in _COUNT_UNITS:
        return numeric / AVOGADRO_CONSTANT_MOL_INV, requested
    try:
        converted = amount_to_mol(numeric, requested, allow_nan=False)
    except EchemQuantityError as exc:
        raise TurnoverFrequencyError(
            "inventory_unit must be an amount unit (mol/mmol/umol/nmol) "
            "or an explicit count unit (count/site/sites/atom/atoms)"
        ) from exc
    return _positive_scalar(float(np.asarray(converted).item()), name="inventory_mol"), requested


def _output_unit(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TurnoverFrequencyError("output_unit must be a non-empty string")
    try:
        return _FREQUENCY_OUTPUT[normalize_unit(value)][1]
    except (EchemQuantityError, KeyError) as exc:
        raise TurnoverFrequencyError(
            "output_unit must be s^-1, min^-1, or h^-1"
        ) from exc


def _frequency_from_s(values: ArrayLike, output_unit: str) -> NDArray[np.float64]:
    factor, _ = _FREQUENCY_OUTPUT[normalize_unit(output_unit)]
    return _immutable(np.asarray(values, dtype=np.float64) * factor, name="turnover frequency")


def _nonnegative(values: ArrayLike, *, name: str) -> NDArray[np.float64]:
    resolved = _immutable(values, name=name)
    if (resolved < 0).any():
        raise TurnoverFrequencyError(
            f"{name} must be non-negative; no absolute-value conversion is implicit"
        )
    return resolved


@dataclass(frozen=True, slots=True, eq=False)
class TurnoverFrequencyResult:
    """Immutable canonical state for one TOF or TOFapp calculation."""

    source_kind: TurnoverSourceKind
    product_rate_mol_s: ArrayLike
    inventory_basis: TurnoverInventoryBasis
    inventory_value: float
    inventory_unit: str
    inventory_mol: float
    output_unit: str = "s^-1"
    electron_number: int | None = None
    current_mode: TurnoverCurrentMode | None = None

    def __post_init__(self) -> None:
        if self.source_kind not in {"molar_rate", "partial_current"}:
            raise TurnoverFrequencyError(
                "source_kind must be 'molar_rate' or 'partial_current'"
            )
        rate = _nonnegative(self.product_rate_mol_s, name="product_rate_mol_s")
        basis = _basis(self.inventory_basis)
        inventory_value = _positive_scalar(self.inventory_value, name="inventory_value")
        expected_mol, inventory_unit = _inventory_to_mol(
            inventory_value,
            self.inventory_unit,
        )
        inventory_mol = _positive_scalar(self.inventory_mol, name="inventory_mol")
        if not np.isclose(inventory_mol, expected_mol, rtol=1e-12, atol=0.0):
            raise TurnoverFrequencyError(
                "inventory_mol is inconsistent with inventory_value/inventory_unit"
            )
        output_unit = _output_unit(self.output_unit)

        if self.source_kind == "molar_rate":
            if self.electron_number is not None or self.current_mode is not None:
                raise TurnoverFrequencyError(
                    "rate-based result must not declare electron_number or current_mode"
                )
            electron_count = None
            mode = None
        else:
            if self.electron_number is None:
                raise TurnoverFrequencyError(
                    "partial-current result requires electron_number"
                )
            try:
                electron_count = validate_electron_number(self.electron_number)
            except EchemQuantityError as exc:
                raise TurnoverFrequencyError(str(exc)) from exc
            if self.current_mode is None:
                raise TurnoverFrequencyError(
                    "partial-current result requires explicit current_mode"
                )
            mode = _current_mode(self.current_mode)

        object.__setattr__(self, "product_rate_mol_s", rate)
        object.__setattr__(self, "inventory_basis", basis)
        object.__setattr__(self, "inventory_value", inventory_value)
        object.__setattr__(self, "inventory_unit", inventory_unit)
        object.__setattr__(self, "inventory_mol", inventory_mol)
        object.__setattr__(self, "output_unit", output_unit)
        object.__setattr__(self, "electron_number", electron_count)
        object.__setattr__(self, "current_mode", mode)

    @property
    def metric_name(self) -> str:
        return "TOF" if self.inventory_basis == "active_sites" else "TOFapp"

    @property
    def axis_name(self) -> str:
        return (
            "turnover_frequency"
            if self.inventory_basis == "active_sites"
            else "apparent_turnover_frequency"
        )

    @property
    def values(self) -> NDArray[np.float64]:
        canonical = self.product_rate_mol_s / self.inventory_mol
        return _frequency_from_s(canonical, self.output_unit)


def turnover_frequency_from_rate(
    rate: ArrayLike | float,
    *,
    rate_unit: str,
    inventory_basis: TurnoverInventoryBasis,
    inventory_value: float,
    inventory_unit: str,
    output_unit: str = "s^-1",
) -> TurnoverFrequencyResult:
    """Calculate TOF/TOFapp from an explicit non-negative product molar rate."""
    try:
        canonical_rate = molar_rate_to_mol_s(rate, rate_unit, allow_nan=False)
    except EchemQuantityError as exc:
        raise TurnoverFrequencyError(str(exc)) from exc
    canonical_rate = _nonnegative(canonical_rate, name="product formation rate")
    inventory_mol, resolved_inventory_unit = _inventory_to_mol(
        inventory_value,
        inventory_unit,
    )
    return TurnoverFrequencyResult(
        source_kind="molar_rate",
        product_rate_mol_s=canonical_rate,
        inventory_basis=_basis(inventory_basis),
        inventory_value=inventory_value,
        inventory_unit=resolved_inventory_unit,
        inventory_mol=inventory_mol,
        output_unit=_output_unit(output_unit),
    )


def turnover_frequency_from_partial_current(
    partial_current: ArrayLike | float,
    *,
    current_unit: str,
    electron_number: int,
    inventory_basis: TurnoverInventoryBasis,
    inventory_value: float,
    inventory_unit: str,
    current_mode: TurnoverCurrentMode,
    output_unit: str = "s^-1",
) -> TurnoverFrequencyResult:
    """Calculate TOF/TOFapp from an explicit total product partial current."""
    mode = _current_mode(current_mode)
    try:
        current_a = current_to_a(partial_current, current_unit, allow_nan=False)
        electron_count = validate_electron_number(electron_number)
    except EchemQuantityError as exc:
        raise TurnoverFrequencyError(str(exc)) from exc
    current_a = _immutable(current_a, name="partial current")
    if mode == "nonnegative":
        current_for_rate = _nonnegative(current_a, name="partial current")
    else:
        current_for_rate = _immutable(np.abs(current_a), name="partial-current magnitude")
    rate = current_for_rate / (electron_count * FARADAY_CONSTANT_C_MOL)
    inventory_mol, resolved_inventory_unit = _inventory_to_mol(
        inventory_value,
        inventory_unit,
    )
    return TurnoverFrequencyResult(
        source_kind="partial_current",
        product_rate_mol_s=rate,
        inventory_basis=_basis(inventory_basis),
        inventory_value=inventory_value,
        inventory_unit=resolved_inventory_unit,
        inventory_mol=inventory_mol,
        output_unit=_output_unit(output_unit),
        electron_number=electron_count,
        current_mode=mode,
    )


def _normalization(series: Series) -> str | None:
    value = series.y_axis.metadata.get("normalization")
    if value is None:
        return None
    return str(value).strip().casefold().replace(" ", "_") or None


def _geometric_area_cm2(value: object, unit: object) -> float:
    numeric = _positive_scalar(value, name="geometric_area_value")
    if not isinstance(unit, str) or not unit.strip():
        raise TurnoverFrequencyError("geometric_area_unit must be a non-empty string")
    try:
        converted = area_to_cm2(numeric, unit, allow_nan=False)
    except EchemQuantityError as exc:
        raise TurnoverFrequencyError(str(exc)) from exc
    return _positive_scalar(float(np.asarray(converted).item()), name="geometric_area_cm2")


def _source_dict(series: Series) -> dict[str, object]:
    source = source_data_ref(series)
    return {
        "key": source.key,
        "label": source.label,
        "sha256": source.sha256,
        "x_name": source.x_name,
        "x_unit": source.x_unit,
        "y_name": source.y_name,
        "y_unit": source.y_unit,
    }


def _result_series(
    source: Series,
    result: TurnoverFrequencyResult,
    *,
    extra_metadata: Mapping[str, object] | None = None,
) -> Series:
    metadata = source.metadata_dict()
    metadata.update(
        {
            "analysis": "turnover_frequency",
            "metric": result.metric_name,
            "inventory_basis": result.inventory_basis,
            "inventory_value": result.inventory_value,
            "inventory_unit": result.inventory_unit,
            "inventory_mol": result.inventory_mol,
            "output_unit": result.output_unit,
            "source_kind": result.source_kind,
            "electron_number": result.electron_number,
            "current_mode": result.current_mode,
            "source": _source_dict(source),
        }
    )
    if extra_metadata:
        metadata.update(extra_metadata)
    return Series(
        x=source.x,
        y=result.values,
        key=source.key,
        label=source.label,
        x_axis=source.x_axis,
        y_axis=Axis(
            result.axis_name,
            unit=result.output_unit,
            label=result.metric_name,
            metadata={"normalization": result.inventory_basis},
        ),
        metadata=metadata,
    )


def turnover_frequency_from_rate_series(
    series: Series,
    *,
    inventory_basis: TurnoverInventoryBasis,
    inventory_value: float,
    inventory_unit: str,
    output_unit: str = "s^-1",
) -> Series:
    """Calculate TOF/TOFapp from a condition-resolved product-rate Series."""
    if not isinstance(series, Series):
        raise TypeError("series must be a Series")
    if series.y_axis.name.casefold() != "molar_rate":
        raise TurnoverFrequencyError("rate Series requires y_axis.name='molar_rate'")
    result = turnover_frequency_from_rate(
        series.y,
        rate_unit=series.y_axis.unit or "",
        inventory_basis=inventory_basis,
        inventory_value=inventory_value,
        inventory_unit=inventory_unit,
        output_unit=output_unit,
    )
    provenance = make_analysis_provenance(
        series,
        input_basis="turnover_frequency:molar_rate",
        units={
            "source_rate": series.y_axis.unit or "",
            "canonical_rate": "mol/s",
            "inventory": result.inventory_unit,
            "canonical_inventory": "mol",
            "output": result.output_unit,
        },
        parameters={
            "inventory_basis": result.inventory_basis,
            "inventory_value": result.inventory_value,
            "inventory_mol": result.inventory_mol,
        },
    )
    return _result_series(series, result, extra_metadata={"provenance": provenance})


def turnover_frequency_from_partial_current_series(
    series: Series,
    *,
    electron_number: int,
    inventory_basis: TurnoverInventoryBasis,
    inventory_value: float,
    inventory_unit: str,
    current_mode: TurnoverCurrentMode,
    geometric_area_value: float,
    geometric_area_unit: str,
    output_unit: str = "s^-1",
) -> Series:
    """Calculate TOF/TOFapp from Issue #23 geometric partial-current density."""
    if not isinstance(series, Series):
        raise TypeError("series must be a Series")
    if series.y_axis.name.casefold() != "partial_current_density":
        raise TurnoverFrequencyError(
            "partial-current Series requires y_axis.name='partial_current_density'"
        )
    if _normalization(series) not in _GEOMETRIC:
        raise TurnoverFrequencyError(
            "partial-current density must explicitly declare geometric-area normalization"
        )
    if (
        series.metadata.get("analysis") != "partial_current_density"
        or "current_source" not in series.metadata
        or "fe_source" not in series.metadata
    ):
        raise TurnoverFrequencyError(
            "partial-current density must carry compatible Issue #23 provenance"
        )

    area_cm2 = _geometric_area_cm2(geometric_area_value, geometric_area_unit)
    stored_area = series.y_axis.metadata.get("electrode_area_cm2")
    if stored_area is not None and not np.isclose(
        _positive_scalar(stored_area, name="stored electrode_area_cm2"),
        area_cm2,
        rtol=1e-12,
        atol=0.0,
    ):
        raise TurnoverFrequencyError(
            "geometric reconstruction area conflicts with source electrode_area_cm2"
        )
    try:
        density_a_cm2 = current_density_to_a_cm2(
            series.y,
            series.y_axis.unit,
            allow_nan=False,
        )
    except EchemQuantityError as exc:
        raise TurnoverFrequencyError(str(exc)) from exc
    total_current_a = density_a_cm2 * area_cm2
    result = turnover_frequency_from_partial_current(
        total_current_a,
        current_unit="A",
        electron_number=electron_number,
        inventory_basis=inventory_basis,
        inventory_value=inventory_value,
        inventory_unit=inventory_unit,
        current_mode=current_mode,
        output_unit=output_unit,
    )
    provenance = make_analysis_provenance(
        series,
        input_basis="turnover_frequency:partial_current_density",
        units={
            "source_partial_current_density": series.y_axis.unit or "",
            "canonical_partial_current_density": "A/cm^2",
            "total_partial_current": "A",
            "inventory": result.inventory_unit,
            "canonical_inventory": "mol",
            "output": result.output_unit,
        },
        parameters={
            "inventory_basis": result.inventory_basis,
            "inventory_value": result.inventory_value,
            "inventory_mol": result.inventory_mol,
            "electron_number": result.electron_number,
            "current_mode": result.current_mode,
            "geometric_area_cm2": area_cm2,
            "upstream_sign_mode": series.metadata.get("sign_mode"),
        },
    )
    return _result_series(
        series,
        result,
        extra_metadata={
            "geometric_area_cm2": area_cm2,
            "upstream_sign_mode": series.metadata.get("sign_mode"),
            "provenance": provenance,
        },
    )


def _keyed_pairs(
    mapping: Mapping[str, object],
    *,
    expected: tuple[str, ...],
    name: str,
) -> dict[str, tuple[object, str]]:
    if not isinstance(mapping, Mapping):
        raise TypeError(f"{name} must be a mapping addressed by Series.key")
    output: dict[str, tuple[object, str]] = {}
    for raw_key, spec in mapping.items():
        if not isinstance(raw_key, str) or not raw_key.strip():
            raise TurnoverFrequencyError(f"{name} keys must be non-empty strings")
        key = raw_key.strip()
        if key in output:
            raise TurnoverFrequencyError(
                f"{name} keys must be unique after whitespace normalization"
            )
        if (
            not isinstance(spec, (tuple, list))
            or len(spec) != 2
            or not isinstance(spec[1], str)
            or not spec[1].strip()
        ):
            raise TurnoverFrequencyError(
                f"{name}[{key!r}] must be a (value, unit) pair"
            )
        output[key] = (spec[0], spec[1])
    missing = set(expected) - set(output)
    unknown = set(output) - set(expected)
    if missing:
        raise TurnoverFrequencyError(
            f"{name} is missing Series.key values: {sorted(missing)!r}"
        )
    if unknown:
        raise TurnoverFrequencyError(
            f"{name} contains unknown Series.key values: {sorted(unknown)!r}"
        )
    return output


def turnover_frequency_from_partial_current_dataset(
    dataset: Dataset,
    inventories: Mapping[str, object],
    geometric_areas: Mapping[str, object],
    *,
    electron_number: int,
    inventory_basis: TurnoverInventoryBasis,
    current_mode: TurnoverCurrentMode,
    output_unit: str = "s^-1",
) -> Dataset:
    """Calculate condition-resolved TOF/TOFapp with exact stable-key mappings."""
    if not isinstance(dataset, Dataset):
        raise TypeError("dataset must be a Dataset")
    if len(dataset) == 0:
        raise TurnoverFrequencyError("cannot calculate TOF for an empty Dataset")
    keys = tuple(item.key for item in dataset)
    if any(not key for key in keys):
        raise TurnoverFrequencyError(
            "TOF Dataset analysis requires non-empty Series.key values"
        )
    inventory_map = _keyed_pairs(inventories, expected=keys, name="inventories")
    area_map = _keyed_pairs(geometric_areas, expected=keys, name="geometric_areas")
    output: list[Series] = []
    for item in dataset:
        inventory_value, inventory_unit = inventory_map[item.key]
        area_value, area_unit = area_map[item.key]
        output.append(
            turnover_frequency_from_partial_current_series(
                item,
                electron_number=electron_number,
                inventory_basis=inventory_basis,
                inventory_value=inventory_value,
                inventory_unit=inventory_unit,
                current_mode=current_mode,
                geometric_area_value=area_value,
                geometric_area_unit=area_unit,
                output_unit=output_unit,
            )
        )
    basis = _basis(inventory_basis)
    return Dataset(
        series=tuple(output),
        name=dataset.name or ("TOF" if basis == "active_sites" else "TOFapp"),
        metadata={
            "analysis": "turnover_frequency",
            "metric": "TOF" if basis == "active_sites" else "TOFapp",
            "inventory_basis": basis,
            "electron_number": validate_electron_number(electron_number),
            "current_mode": _current_mode(current_mode),
            "output_unit": _output_unit(output_unit),
            "series_keys": keys,
        },
    )


def turnover_frequency_from_rate_dataset(
    dataset: Dataset,
    inventories: Mapping[str, object],
    *,
    inventory_basis: TurnoverInventoryBasis,
    output_unit: str = "s^-1",
) -> Dataset:
    """Calculate rate-based TOF/TOFapp with inventories keyed by stable Series.key."""
    if not isinstance(dataset, Dataset):
        raise TypeError("dataset must be a Dataset")
    if len(dataset) == 0:
        raise TurnoverFrequencyError("cannot calculate TOF for an empty Dataset")
    keys = tuple(item.key for item in dataset)
    if any(not key for key in keys):
        raise TurnoverFrequencyError(
            "TOF Dataset analysis requires non-empty Series.key values"
        )
    inventory_map = _keyed_pairs(inventories, expected=keys, name="inventories")
    output: list[Series] = []
    for item in dataset:
        inventory_value, inventory_unit = inventory_map[item.key]
        output.append(
            turnover_frequency_from_rate_series(
                item,
                inventory_basis=inventory_basis,
                inventory_value=inventory_value,
                inventory_unit=inventory_unit,
                output_unit=output_unit,
            )
        )
    basis = _basis(inventory_basis)
    return Dataset(
        series=tuple(output),
        name=dataset.name or ("TOF" if basis == "active_sites" else "TOFapp"),
        metadata={
            "analysis": "turnover_frequency",
            "metric": "TOF" if basis == "active_sites" else "TOFapp",
            "inventory_basis": basis,
            "output_unit": _output_unit(output_unit),
            "series_keys": keys,
        },
    )


__all__ = [
    "AVOGADRO_CONSTANT_MOL_INV",
    "TurnoverCurrentMode",
    "TurnoverFrequencyError",
    "TurnoverFrequencyResult",
    "TurnoverInventoryBasis",
    "TurnoverSourceKind",
    "turnover_frequency_from_partial_current",
    "turnover_frequency_from_partial_current_dataset",
    "turnover_frequency_from_partial_current_series",
    "turnover_frequency_from_rate",
    "turnover_frequency_from_rate_dataset",
    "turnover_frequency_from_rate_series",
]
