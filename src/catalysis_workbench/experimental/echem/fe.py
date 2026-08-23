"""Explicit Faradaic-efficiency calculations for already quantified products."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from numbers import Real
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray

from catalysis_workbench.core import Axis, Dataset, Series

from .provenance import SourceDataRef, source_data_ref
from .quantities import (
    FARADAY_CONSTANT_C_MOL,
    EchemQuantityError,
    amount_to_mol,
    charge_to_c,
    current_to_a,
    molar_rate_to_mol_s,
)
from .quantities import electron_number as validate_electron_number

FaradaicEfficiencyMode = Literal["amount_charge", "rate_current"]
FaradaicEfficiencyOutputUnit = Literal["fraction", "%"]
_COMPATIBILITY_METADATA_KEYS = ("reference", "normalization")


class FaradaicEfficiencyError(ValueError):
    """Raised when a Faradaic-efficiency calculation is scientifically invalid."""


def _immutable_float_array(values: ArrayLike, *, name: str) -> NDArray[np.float64]:
    try:
        source = np.asarray(values)
    except (TypeError, ValueError) as exc:
        raise FaradaicEfficiencyError(f"{name} must contain real numeric values") from exc
    if source.size == 0:
        raise FaradaicEfficiencyError(f"{name} must contain at least one value")
    if np.iscomplexobj(source) or source.dtype.kind not in "iuf":
        raise FaradaicEfficiencyError(f"{name} must contain real numeric values")
    normalized = np.ascontiguousarray(source, dtype=np.float64)
    if not np.isfinite(normalized).all():
        raise FaradaicEfficiencyError(f"{name} must contain only finite values")
    immutable_buffer = normalized.tobytes(order="C")
    result = np.frombuffer(immutable_buffer, dtype=np.float64, count=normalized.size)
    result = result.reshape(normalized.shape)
    result.setflags(write=False)
    return result


def _immutable_bool_array(values: ArrayLike, *, name: str) -> NDArray[np.bool_]:
    try:
        source = np.asarray(values)
    except (TypeError, ValueError) as exc:
        raise FaradaicEfficiencyError(f"{name} must contain boolean values") from exc
    if source.size == 0:
        raise FaradaicEfficiencyError(f"{name} must contain at least one value")
    if source.dtype.kind != "b":
        raise FaradaicEfficiencyError(f"{name} must contain boolean values")
    normalized = np.ascontiguousarray(source, dtype=np.bool_)
    immutable_buffer = normalized.tobytes(order="C")
    result = np.frombuffer(immutable_buffer, dtype=np.bool_, count=normalized.size)
    result = result.reshape(normalized.shape)
    result.setflags(write=False)
    return result


def _strict_real_scalar(value: object, *, name: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise FaradaicEfficiencyError(f"{name} must be a real numeric value")
    numeric = float(value)
    if not isfinite(numeric):
        raise FaradaicEfficiencyError(f"{name} must be finite")
    return numeric


def _validated_electron_number(value: object) -> int:
    try:
        return validate_electron_number(value)
    except EchemQuantityError as exc:
        raise FaradaicEfficiencyError(str(exc)) from exc


def _require_real_numeric_input(values: ArrayLike, *, name: str) -> None:
    """Reject strings, booleans, complex values, and object coercion at the FE boundary."""
    try:
        source = np.asarray(values)
    except (TypeError, ValueError) as exc:
        raise FaradaicEfficiencyError(f"{name} must contain real numeric values") from exc
    if source.dtype.kind not in "iuf" or np.iscomplexobj(source):
        raise FaradaicEfficiencyError(f"{name} must contain real numeric values")


def _broadcast_arrays(
    product: ArrayLike,
    denominator: ArrayLike,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    try:
        product_array, denominator_array = np.broadcast_arrays(product, denominator)
    except ValueError as exc:
        raise FaradaicEfficiencyError(
            "product and denominator values must have broadcast-compatible shapes"
        ) from exc
    return (
        np.asarray(product_array, dtype=np.float64),
        np.asarray(denominator_array, dtype=np.float64),
    )


@dataclass(frozen=True, slots=True, eq=False)
class FaradaicEfficiencyResult:
    """Immutable canonical FE inputs with derived fraction and percent values."""

    mode: FaradaicEfficiencyMode
    electron_number: int
    product_canonical: ArrayLike
    denominator_canonical: ArrayLike

    def __post_init__(self) -> None:
        if self.mode not in {"amount_charge", "rate_current"}:
            raise FaradaicEfficiencyError(
                "mode must be 'amount_charge' or 'rate_current'"
            )
        z = _validated_electron_number(self.electron_number)
        product = _immutable_float_array(
            self.product_canonical,
            name="canonical product values",
        )
        denominator = _immutable_float_array(
            self.denominator_canonical,
            name="canonical denominator values",
        )
        if product.shape != denominator.shape:
            raise FaradaicEfficiencyError(
                "canonical product and denominator values must have matching shapes"
            )
        if (product < 0.0).any():
            raise FaradaicEfficiencyError("product amount/rate must be non-negative")
        if (denominator == 0.0).any():
            raise FaradaicEfficiencyError("charge/current denominator must be non-zero")

        object.__setattr__(self, "electron_number", z)
        object.__setattr__(self, "product_canonical", product)
        object.__setattr__(self, "denominator_canonical", denominator)

    @property
    def fraction(self) -> NDArray[np.float64]:
        """Return FE as a non-negative dimensionless fraction without clipping."""
        values = (
            self.electron_number
            * FARADAY_CONSTANT_C_MOL
            * self.product_canonical
            / np.abs(self.denominator_canonical)
        )
        return _immutable_float_array(values, name="Faradaic efficiency fraction")

    @property
    def percent(self) -> NDArray[np.float64]:
        """Return FE in percent without clipping or renormalization."""
        return _immutable_float_array(
            self.fraction * 100.0,
            name="Faradaic efficiency percent",
        )

    @property
    def exceeds_unity(self) -> NDArray[np.bool_]:
        """Return a point-wise QA mask for FE values above 100%."""
        return _immutable_bool_array(self.fraction > 1.0, name="FE exceedance mask")

    @property
    def canonical_product_unit(self) -> str:
        return "mol" if self.mode == "amount_charge" else "mol/s"

    @property
    def canonical_denominator_unit(self) -> str:
        return "C" if self.mode == "amount_charge" else "A"


def faradaic_efficiency_from_amount(
    product_amount: ArrayLike | float,
    amount_unit: str,
    charge: ArrayLike | float,
    charge_unit: str,
    *,
    electron_number: int,
) -> FaradaicEfficiencyResult:
    """Calculate accumulated-product FE from amount and signed total charge."""
    _require_real_numeric_input(product_amount, name="product amount")
    _require_real_numeric_input(charge, name="charge")
    try:
        product_mol = amount_to_mol(product_amount, amount_unit, allow_nan=False)
        charge_c = charge_to_c(charge, charge_unit, allow_nan=False)
    except EchemQuantityError as exc:
        raise FaradaicEfficiencyError(str(exc)) from exc
    product_mol, charge_c = _broadcast_arrays(product_mol, charge_c)
    return FaradaicEfficiencyResult(
        mode="amount_charge",
        electron_number=electron_number,
        product_canonical=product_mol,
        denominator_canonical=charge_c,
    )


def faradaic_efficiency_from_rate(
    product_rate: ArrayLike | float,
    rate_unit: str,
    current: ArrayLike | float,
    current_unit: str,
    *,
    electron_number: int,
) -> FaradaicEfficiencyResult:
    """Calculate steady-state FE from molar production rate and signed current."""
    _require_real_numeric_input(product_rate, name="product rate")
    _require_real_numeric_input(current, name="current")
    try:
        rate_mol_s = molar_rate_to_mol_s(product_rate, rate_unit, allow_nan=False)
        current_a = current_to_a(current, current_unit, allow_nan=False)
    except EchemQuantityError as exc:
        raise FaradaicEfficiencyError(str(exc)) from exc
    rate_mol_s, current_a = _broadcast_arrays(rate_mol_s, current_a)
    return FaradaicEfficiencyResult(
        mode="rate_current",
        electron_number=electron_number,
        product_canonical=rate_mol_s,
        denominator_canonical=current_a,
    )


def _semantic_metadata_value(axis: Axis, key: str) -> object:
    value = axis.metadata.get(key)
    if isinstance(value, str):
        return value.strip().casefold()
    return value


def _validate_condition_compatibility(product: Series, denominator: Series) -> None:
    if np.iscomplexobj(product.x) or np.iscomplexobj(denominator.x):
        raise FaradaicEfficiencyError("condition axes must contain real values")
    if not np.isfinite(product.x).all() or not np.isfinite(denominator.x).all():
        raise FaradaicEfficiencyError("condition axes must contain only finite values")
    if product.x_axis.name.casefold() != denominator.x_axis.name.casefold():
        raise FaradaicEfficiencyError("product and denominator condition-axis names differ")
    if product.x_axis.unit != denominator.x_axis.unit:
        raise FaradaicEfficiencyError("product and denominator condition-axis units differ")
    if not np.array_equal(product.x, denominator.x):
        raise FaradaicEfficiencyError(
            "product and denominator condition values must match exactly"
        )
    for key in _COMPATIBILITY_METADATA_KEYS:
        product_value = _semantic_metadata_value(product.x_axis, key)
        denominator_value = _semantic_metadata_value(denominator.x_axis, key)
        if product_value != denominator_value:
            raise FaradaicEfficiencyError(
                f"product and denominator condition-axis {key!r} metadata differ"
            )


def _mode_from_series(product: Series, denominator: Series) -> FaradaicEfficiencyMode:
    product_name = product.y_axis.name.casefold()
    denominator_name = denominator.y_axis.name.casefold()
    if product_name == "amount" and denominator_name == "charge":
        return "amount_charge"
    if product_name == "molar_rate" and denominator_name == "current":
        return "rate_current"
    raise FaradaicEfficiencyError(
        "Series FE requires amount/charge or molar_rate/current y-axis semantics"
    )


def _source_ref_dict(source: SourceDataRef) -> dict[str, object]:
    return {
        "key": source.key,
        "label": source.label,
        "sha256": source.sha256,
        "x_name": source.x_name,
        "x_unit": source.x_unit,
        "y_name": source.y_name,
        "y_unit": source.y_unit,
    }


def _normalize_output_unit(unit: object) -> FaradaicEfficiencyOutputUnit:
    if unit == "fraction":
        return "fraction"
    if unit == "%":
        return "%"
    raise FaradaicEfficiencyError("output_unit must be 'fraction' or '%'")


def faradaic_efficiency_series(
    product: Series,
    denominator: Series,
    *,
    electron_number: int,
    output_unit: FaradaicEfficiencyOutputUnit = "%",
) -> Series:
    """Calculate one condition-resolved product FE Series with deterministic provenance."""
    if not isinstance(product, Series) or not isinstance(denominator, Series):
        raise TypeError("product and denominator must both be Series instances")
    _validate_condition_compatibility(product, denominator)
    mode = _mode_from_series(product, denominator)
    resolved_output_unit = _normalize_output_unit(output_unit)

    if mode == "amount_charge":
        result = faradaic_efficiency_from_amount(
            product.y,
            product.y_axis.unit or "",
            denominator.y,
            denominator.y_axis.unit or "",
            electron_number=electron_number,
        )
    else:
        result = faradaic_efficiency_from_rate(
            product.y,
            product.y_axis.unit or "",
            denominator.y,
            denominator.y_axis.unit or "",
            electron_number=electron_number,
        )

    values = result.fraction if resolved_output_unit == "fraction" else result.percent
    product_source = source_data_ref(product)
    denominator_source = source_data_ref(denominator)
    metadata = {
        "analysis": "faradaic_efficiency",
        "mode": mode,
        "electron_number": result.electron_number,
        "faraday_constant_c_mol": FARADAY_CONSTANT_C_MOL,
        "canonical_product_unit": result.canonical_product_unit,
        "canonical_denominator_unit": result.canonical_denominator_unit,
        "denominator_canonical_values": result.denominator_canonical,
        "output_unit": resolved_output_unit,
        "product_source": _source_ref_dict(product_source),
        "denominator_source": _source_ref_dict(denominator_source),
    }
    return Series(
        x=product.x,
        y=values,
        key=product.key,
        label=product.label,
        x_axis=product.x_axis,
        y_axis=Axis(
            "faradaic_efficiency",
            unit=resolved_output_unit,
            label="Faradaic efficiency",
        ),
        metadata=metadata,
    )


def _normalize_electron_mapping(
    mapping: Mapping[str, object],
    *,
    keys: tuple[str, ...],
) -> dict[str, int]:
    if not isinstance(mapping, Mapping):
        raise TypeError("electron_numbers must be a mapping addressed by Series.key")
    normalized: dict[str, int] = {}
    for raw_key, value in mapping.items():
        if not isinstance(raw_key, str):
            raise FaradaicEfficiencyError("electron_numbers keys must be strings")
        key = raw_key.strip()
        if not key:
            raise FaradaicEfficiencyError("electron_numbers keys must not be empty")
        if key in normalized:
            raise FaradaicEfficiencyError(
                "electron_numbers keys must be unique after normalization"
            )
        normalized[key] = _validated_electron_number(value)

    expected = set(keys)
    supplied = set(normalized)
    missing = expected - supplied
    unknown = supplied - expected
    if missing:
        raise FaradaicEfficiencyError(
            f"electron_numbers is missing Series.key values: {sorted(missing)!r}"
        )
    if unknown:
        raise FaradaicEfficiencyError(
            f"electron_numbers contains unknown Series.key values: {sorted(unknown)!r}"
        )
    return normalized


def faradaic_efficiency_dataset(
    products: Dataset,
    denominator: Series,
    electron_numbers: Mapping[str, object],
    *,
    output_unit: FaradaicEfficiencyOutputUnit = "%",
) -> Dataset:
    """Calculate ordered multi-product FE without renormalizing product fractions."""
    if not isinstance(products, Dataset):
        raise TypeError("products must be a Dataset")
    if not isinstance(denominator, Series):
        raise TypeError("denominator must be a Series")
    if len(products) == 0:
        raise FaradaicEfficiencyError("cannot calculate FE for an empty product Dataset")
    keys = tuple(product.key for product in products)
    if any(not key for key in keys):
        raise FaradaicEfficiencyError(
            "multi-product FE requires non-empty product Series.key values"
        )
    resolved = _normalize_electron_mapping(electron_numbers, keys=keys)
    output = [
        faradaic_efficiency_series(
            product,
            denominator,
            electron_number=resolved[product.key],
            output_unit=output_unit,
        )
        for product in products
    ]
    return Dataset(output)


def _fraction_from_fe_series(series: Series) -> NDArray[np.float64]:
    if series.y_axis.name.casefold() != "faradaic_efficiency":
        raise FaradaicEfficiencyError(
            "closure requires y_axis.name='faradaic_efficiency'"
        )
    if np.iscomplexobj(series.y) or not np.isfinite(series.y).all():
        raise FaradaicEfficiencyError("FE values must be finite and real")
    values = np.asarray(series.y, dtype=np.float64)
    if (values < 0.0).any():
        raise FaradaicEfficiencyError("FE values must be non-negative")
    if series.y_axis.unit == "fraction":
        fraction = values
    elif series.y_axis.unit == "%":
        fraction = values / 100.0
    else:
        raise FaradaicEfficiencyError("FE Series unit must be 'fraction' or '%'")
    return np.asarray(fraction, dtype=np.float64)


@dataclass(frozen=True, slots=True, eq=False)
class FaradaicEfficiencyClosure:
    """Explicit total-FE closure result without clipping or renormalization."""

    condition_values: ArrayLike
    condition_axis: Axis
    total_fraction: ArrayLike
    exceeds_limit: ArrayLike
    product_keys: tuple[str, ...]
    sources: tuple[SourceDataRef, ...]
    limit_fraction: float = 1.0
    tolerance_fraction: float = 1e-6

    def __post_init__(self) -> None:
        if not isinstance(self.condition_axis, Axis):
            raise TypeError("condition_axis must be an Axis")
        condition = _immutable_float_array(
            self.condition_values,
            name="closure condition values",
        )
        total = _immutable_float_array(self.total_fraction, name="total FE fraction")
        exceeds = _immutable_bool_array(self.exceeds_limit, name="closure exceedance mask")
        if condition.ndim != 1 or total.ndim != 1 or exceeds.ndim != 1:
            raise FaradaicEfficiencyError("closure arrays must be one-dimensional")
        if not (len(condition) == len(total) == len(exceeds)):
            raise FaradaicEfficiencyError("closure arrays must have matching lengths")
        if (total < 0.0).any():
            raise FaradaicEfficiencyError("total FE fraction must be non-negative")

        keys = tuple(self.product_keys)
        if not keys or any(not isinstance(key, str) or not key.strip() for key in keys):
            raise FaradaicEfficiencyError("product_keys must contain non-empty strings")
        keys = tuple(key.strip() for key in keys)
        if len(keys) != len(set(keys)):
            raise FaradaicEfficiencyError("product_keys must be unique")

        sources = tuple(self.sources)
        if not sources or not all(isinstance(source, SourceDataRef) for source in sources):
            raise TypeError("sources must contain only SourceDataRef instances")
        if len(sources) != len(keys):
            raise FaradaicEfficiencyError(
                "closure sources must contain one SourceDataRef per product key"
            )
        for key, source in zip(keys, sources, strict=True):
            if source.key and source.key != key:
                raise FaradaicEfficiencyError(
                    "closure source keys must match product_keys when source keys are present"
                )
            if source.x_name.casefold() != self.condition_axis.name.casefold():
                raise FaradaicEfficiencyError(
                    "closure source condition-axis names must match condition_axis"
                )
            if source.x_unit != self.condition_axis.unit:
                raise FaradaicEfficiencyError(
                    "closure source condition-axis units must match condition_axis"
                )
            if source.y_name.casefold() != "faradaic_efficiency":
                raise FaradaicEfficiencyError(
                    "closure sources must reference faradaic_efficiency Series"
                )
            if source.y_unit not in {"fraction", "%"}:
                raise FaradaicEfficiencyError(
                    "closure source FE units must be 'fraction' or '%'"
                )

        limit = _strict_real_scalar(self.limit_fraction, name="limit_fraction")
        tolerance = _strict_real_scalar(
            self.tolerance_fraction,
            name="tolerance_fraction",
        )
        if limit <= 0.0:
            raise FaradaicEfficiencyError("limit_fraction must be greater than zero")
        if tolerance < 0.0:
            raise FaradaicEfficiencyError("tolerance_fraction must be non-negative")
        expected = total > (limit + tolerance)
        if not np.array_equal(exceeds, expected):
            raise FaradaicEfficiencyError(
                "exceeds_limit mask must match total_fraction and QA threshold"
            )

        object.__setattr__(self, "condition_values", condition)
        object.__setattr__(self, "total_fraction", total)
        object.__setattr__(self, "exceeds_limit", exceeds)
        object.__setattr__(self, "product_keys", keys)
        object.__setattr__(self, "sources", sources)
        object.__setattr__(self, "limit_fraction", limit)
        object.__setattr__(self, "tolerance_fraction", tolerance)

    @property
    def total_percent(self) -> NDArray[np.float64]:
        return _immutable_float_array(self.total_fraction * 100.0, name="total FE percent")

    @property
    def any_exceeds_limit(self) -> bool:
        return bool(np.any(self.exceeds_limit))

    @property
    def max_fraction(self) -> float:
        return float(np.max(self.total_fraction))


def faradaic_efficiency_closure(
    data: Series | Dataset,
    *,
    limit_fraction: float = 1.0,
    tolerance_fraction: float = 1e-6,
    strict: bool = False,
) -> FaradaicEfficiencyClosure:
    """Sum product FE values and report QA exceedance without modifying the data."""
    if isinstance(data, Series):
        series = (data,)
    elif isinstance(data, Dataset):
        if len(data) == 0:
            raise FaradaicEfficiencyError("cannot summarize an empty FE Dataset")
        series = tuple(data)
    else:
        raise TypeError("data must be a Series or Dataset")
    if not isinstance(strict, (bool, np.bool_)):
        raise TypeError("strict must be a boolean")

    first = series[0]
    first_fraction = _fraction_from_fe_series(first)
    if np.iscomplexobj(first.x) or not np.isfinite(first.x).all():
        raise FaradaicEfficiencyError("condition axes must contain finite real values")
    fractions = [first_fraction]
    for item in series[1:]:
        _validate_condition_compatibility(first, item)
        fractions.append(_fraction_from_fe_series(item))

    total = np.sum(np.stack(fractions, axis=0), axis=0)
    limit = _strict_real_scalar(limit_fraction, name="limit_fraction")
    tolerance = _strict_real_scalar(tolerance_fraction, name="tolerance_fraction")
    if limit <= 0.0:
        raise FaradaicEfficiencyError("limit_fraction must be greater than zero")
    if tolerance < 0.0:
        raise FaradaicEfficiencyError("tolerance_fraction must be non-negative")
    exceeds = total > (limit + tolerance)
    if bool(strict) and np.any(exceeds):
        raise FaradaicEfficiencyError(
            "total Faradaic efficiency exceeds the configured closure limit"
        )

    keys: list[str] = []
    for index, item in enumerate(series):
        keys.append(item.key or f"series-{index}")
    return FaradaicEfficiencyClosure(
        condition_values=first.x,
        condition_axis=first.x_axis,
        total_fraction=total,
        exceeds_limit=exceeds,
        product_keys=tuple(keys),
        sources=tuple(source_data_ref(item) for item in series),
        limit_fraction=limit,
        tolerance_fraction=tolerance,
    )