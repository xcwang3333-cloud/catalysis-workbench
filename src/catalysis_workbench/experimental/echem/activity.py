"""Explicit catalyst-mass, metal-mass, and ECSA activity normalization."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from numbers import Real
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray

from catalysis_workbench.core import Axis, Dataset, Series

from .partial_current import SignMode
from .provenance import make_analysis_provenance, source_data_ref
from .quantities import (
    EchemQuantityError,
    area_to_cm2,
    canonical_current_density_unit,
    current_density_from_a_cm2,
    current_density_to_a_cm2,
    current_to_a,
    is_current_density_unit,
    is_current_unit,
    mass_to_g,
    normalize_unit,
)

ActivityBasis = Literal["catalyst_mass", "metal_mass", "ecsa"]
ActivityCurrentBasis = Literal["current", "current_density"]

_GEOMETRIC = {"geometric", "geometric_area", "geometric_area_cm2"}
_MASS_OUTPUT = {
    normalize_unit("A/g"): (1.0, "A/g"),
    normalize_unit("mA/g"): (1e-3, "mA/g"),
    normalize_unit("A/mg"): (1e3, "A/mg"),
    normalize_unit("mA/mg"): (1.0, "mA/mg"),
}
_LABEL = {
    "catalyst_mass": "Catalyst-mass activity",
    "metal_mass": "Metal-mass activity",
    "ecsa": "ECSA-specific activity",
}


class ActivityNormalizationError(ValueError):
    """Raised when an activity normalization violates the scientific contract."""


def _immutable(values: ArrayLike, *, name: str) -> NDArray[np.float64]:
    try:
        source = np.asarray(values)
    except (TypeError, ValueError) as exc:
        raise ActivityNormalizationError(f"{name} must contain real numeric values") from exc
    if source.size == 0 or np.iscomplexobj(source) or source.dtype.kind not in "iuf":
        raise ActivityNormalizationError(f"{name} must contain real numeric values")
    normalized = np.ascontiguousarray(source, dtype=np.float64)
    if not np.isfinite(normalized).all():
        raise ActivityNormalizationError(f"{name} must contain only finite values")
    result = np.frombuffer(normalized.tobytes(order="C"), dtype=np.float64)
    result = result.reshape(normalized.shape)
    result.setflags(write=False)
    return result


def _basis(value: object) -> ActivityBasis:
    if isinstance(value, str):
        if value == "catalyst_mass":
            return "catalyst_mass"
        if value == "metal_mass":
            return "metal_mass"
        if value == "ecsa":
            return "ecsa"
    raise ActivityNormalizationError(
        "basis must be 'catalyst_mass', 'metal_mass', or 'ecsa'"
    )


def _current_basis(value: object) -> ActivityCurrentBasis:
    if isinstance(value, str):
        if value == "current":
            return "current"
        if value == "current_density":
            return "current_density"
    raise ActivityNormalizationError(
        "current_basis must be 'current' or 'current_density'; "
        "'current_density' declares geometric-area normalization"
    )


def _sign(value: object) -> SignMode:
    if isinstance(value, str):
        if value == "signed":
            return "signed"
        if value == "magnitude":
            return "magnitude"
    raise ActivityNormalizationError("sign_mode must be 'signed' or 'magnitude'")


def _require_numeric(values: ArrayLike | float, *, name: str) -> None:
    try:
        source = np.asarray(values)
    except (TypeError, ValueError) as exc:
        raise ActivityNormalizationError(f"{name} must contain real numeric values") from exc
    if source.size == 0 or np.iscomplexobj(source) or source.dtype.kind not in "iuf":
        raise ActivityNormalizationError(f"{name} must contain real numeric values")


def _positive(value: object, *, name: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ActivityNormalizationError(f"{name} must be a real numeric value")
    numeric = float(value)
    if not isfinite(numeric) or numeric <= 0:
        raise ActivityNormalizationError(f"{name} must be finite and greater than zero")
    return numeric


def _output_unit(basis: ActivityBasis, unit: str | None) -> str:
    if basis in {"catalyst_mass", "metal_mass"}:
        requested = "A/g" if unit is None else unit
        try:
            return _MASS_OUTPUT[normalize_unit(requested)][1]
        except (EchemQuantityError, KeyError) as exc:
            raise ActivityNormalizationError(
                "mass-activity output_unit must be A/g, mA/g, A/mg, or mA/mg"
            ) from exc
    requested = "A/cm^2" if unit is None else unit
    try:
        return canonical_current_density_unit(requested)
    except EchemQuantityError as exc:
        raise ActivityNormalizationError(
            "ECSA activity output_unit must be A/cm^2, mA/cm^2, or uA/cm^2"
        ) from exc


def _denominator(
    basis: ActivityBasis,
    value: object,
    unit: str,
) -> tuple[float, str]:
    _positive(value, name="denominator_value")
    try:
        converted = (
            mass_to_g(value, unit, allow_nan=False)
            if basis in {"catalyst_mass", "metal_mass"}
            else area_to_cm2(value, unit, allow_nan=False)
        )
    except EchemQuantityError as exc:
        raise ActivityNormalizationError(str(exc)) from exc
    canonical = _positive(float(np.asarray(converted).item()), name="denominator")
    return canonical, "g" if basis in {"catalyst_mass", "metal_mass"} else "cm^2"


def _area(value: object | None, unit: str | None) -> float:
    if value is None or unit is None:
        raise ActivityNormalizationError(
            "geometric_area_value and geometric_area_unit are required "
            "for current-density input"
        )
    _positive(value, name="geometric_area_value")
    try:
        converted = area_to_cm2(value, unit, allow_nan=False)
    except EchemQuantityError as exc:
        raise ActivityNormalizationError(str(exc)) from exc
    return _positive(float(np.asarray(converted).item()), name="geometric area")


@dataclass(frozen=True, slots=True, eq=False)
class ActivityNormalizationResult:
    """Immutable canonical state for one activity normalization."""

    source_current_basis: ActivityCurrentBasis
    source_current_unit: str
    source_current_canonical: ArrayLike
    total_current_a: ArrayLike
    basis: ActivityBasis
    denominator_value: float
    denominator_unit: str
    denominator_canonical_value: float
    output_unit: str
    sign_mode: SignMode = "signed"
    geometric_area_cm2: float | None = None

    def __post_init__(self) -> None:
        current_basis = _current_basis(self.source_current_basis)
        basis = _basis(self.basis)
        sign_mode = _sign(self.sign_mode)

        if not isinstance(self.source_current_unit, str) or not self.source_current_unit.strip():
            raise ActivityNormalizationError("source_current_unit must be a non-empty string")
        source_unit = self.source_current_unit.strip()
        source_unit_valid = (
            is_current_unit(source_unit)
            if current_basis == "current"
            else is_current_density_unit(source_unit)
        )
        if not source_unit_valid:
            kind = "current" if current_basis == "current" else "current-density"
            raise ActivityNormalizationError(
                f"source_current_unit {source_unit!r} is not a supported {kind} unit"
            )

        if not isinstance(self.denominator_unit, str) or not self.denominator_unit.strip():
            raise ActivityNormalizationError("denominator_unit must be a non-empty string")
        denominator_unit = self.denominator_unit.strip()

        source = _immutable(self.source_current_canonical, name="canonical source current")
        total = _immutable(self.total_current_a, name="total current")
        if source.shape != total.shape:
            raise ActivityNormalizationError(
                "canonical source current and total current must have matching shapes"
            )

        denominator_value = _positive(self.denominator_value, name="denominator_value")
        denominator_canonical = _positive(
            self.denominator_canonical_value,
            name="denominator_canonical_value",
        )
        expected_denominator, _ = _denominator(basis, denominator_value, denominator_unit)
        if not np.isclose(
            denominator_canonical,
            expected_denominator,
            rtol=1e-12,
            atol=0.0,
        ):
            raise ActivityNormalizationError(
                "denominator_canonical_value is inconsistent with denominator_value/unit"
            )

        area = self.geometric_area_cm2
        if current_basis == "current_density":
            area = _positive(area, name="geometric_area_cm2")
            expected_total = source * area
        else:
            if area is not None:
                raise ActivityNormalizationError(
                    "geometric_area_cm2 must be None for total-current input"
                )
            expected_total = source
        if not np.allclose(total, expected_total, rtol=1e-12, atol=0.0):
            raise ActivityNormalizationError(
                "total_current_a is inconsistent with canonical source current and area"
            )

        object.__setattr__(self, "source_current_basis", current_basis)
        object.__setattr__(self, "source_current_unit", source_unit)
        object.__setattr__(self, "source_current_canonical", source)
        object.__setattr__(self, "total_current_a", total)
        object.__setattr__(self, "basis", basis)
        object.__setattr__(self, "denominator_value", denominator_value)
        object.__setattr__(self, "denominator_unit", denominator_unit)
        object.__setattr__(self, "denominator_canonical_value", denominator_canonical)
        object.__setattr__(self, "output_unit", _output_unit(basis, self.output_unit))
        object.__setattr__(self, "sign_mode", sign_mode)
        object.__setattr__(self, "geometric_area_cm2", area)

    @property
    def canonical_denominator_unit(self) -> str:
        return "g" if self.basis in {"catalyst_mass", "metal_mass"} else "cm^2"

    @property
    def canonical_activity_unit(self) -> str:
        return "A/g" if self.basis in {"catalyst_mass", "metal_mass"} else "A/cm^2"

    @property
    def values(self) -> NDArray[np.float64]:
        canonical = self.total_current_a / self.denominator_canonical_value
        if self.sign_mode == "magnitude":
            canonical = np.abs(canonical)
        if self.basis in {"catalyst_mass", "metal_mass"}:
            factor, _ = _MASS_OUTPUT[normalize_unit(self.output_unit)]
            values = canonical / factor
        else:
            values = current_density_from_a_cm2(canonical, self.output_unit)
        return _immutable(values, name="activity")


def normalize_activity(
    current: ArrayLike | float,
    *,
    current_unit: str,
    current_basis: ActivityCurrentBasis,
    basis: ActivityBasis,
    denominator_value: float,
    denominator_unit: str,
    output_unit: str | None = None,
    sign_mode: SignMode = "signed",
    geometric_area_value: float | None = None,
    geometric_area_unit: str | None = None,
) -> ActivityNormalizationResult:
    """Normalize an explicitly declared total current or geometric current density.

    ``current_basis='current_density'`` is an explicit scientific declaration that the
    supplied raw array is geometrically normalized current density. Raw arrays carry no
    axis metadata, so an ECSA-, mass-, or otherwise non-geometrically normalized density
    must not be passed under this basis. A geometric area is always required to recover
    the canonical total-current numerator.
    """
    current_basis_resolved = _current_basis(current_basis)
    _require_numeric(current, name="current")
    basis_resolved = _basis(basis)
    output = _output_unit(basis_resolved, output_unit)

    try:
        if current_basis_resolved == "current":
            if geometric_area_value is not None or geometric_area_unit is not None:
                raise ActivityNormalizationError(
                    "geometric area must not be supplied for total-current input"
                )
            source = current_to_a(current, current_unit, allow_nan=False)
            total = source
            area_cm2 = None
        else:
            area_cm2 = _area(geometric_area_value, geometric_area_unit)
            source = current_density_to_a_cm2(current, current_unit, allow_nan=False)
            total = source * area_cm2
    except EchemQuantityError as exc:
        raise ActivityNormalizationError(str(exc)) from exc

    denominator, _ = _denominator(
        basis_resolved,
        denominator_value,
        denominator_unit,
    )
    return ActivityNormalizationResult(
        source_current_basis=current_basis_resolved,
        source_current_unit=current_unit,
        source_current_canonical=source,
        total_current_a=total,
        basis=basis_resolved,
        denominator_value=denominator_value,
        denominator_unit=denominator_unit,
        denominator_canonical_value=denominator,
        output_unit=output,
        sign_mode=_sign(sign_mode),
        geometric_area_cm2=area_cm2,
    )


def _normalization(series: Series) -> str | None:
    value = series.y_axis.metadata.get("normalization")
    if value is None:
        return None
    return str(value).strip().casefold().replace(" ", "_") or None


def _series_basis(
    series: Series,
    *,
    geometric_area_value: float | None,
    geometric_area_unit: str | None,
) -> ActivityCurrentBasis:
    name = series.y_axis.name.casefold()
    normalization = _normalization(series)

    if name == "current":
        if normalization is not None:
            raise ActivityNormalizationError(
                "total-current source already declares normalization "
                f"{normalization!r}; refusing double normalization"
            )
        return "current"

    if name not in {"current_density", "partial_current_density"}:
        raise ActivityNormalizationError(
            "activity normalization requires y_axis.name='current', "
            "'current_density', or 'partial_current_density'"
        )
    if normalization not in _GEOMETRIC:
        raise ActivityNormalizationError(
            "current-density source must explicitly declare geometric-area "
            f"normalization; found {series.y_axis.metadata.get('normalization')!r}"
        )
    if name == "partial_current_density" and (
        series.metadata.get("analysis") != "partial_current_density"
        or "current_source" not in series.metadata
        or "fe_source" not in series.metadata
    ):
        raise ActivityNormalizationError(
            "partial_current_density input must carry Issue #23 source provenance"
        )

    supplied_area = _area(geometric_area_value, geometric_area_unit)
    stored_area = series.y_axis.metadata.get("electrode_area_cm2")
    if stored_area is not None and not np.isclose(
        _positive(stored_area, name="stored electrode_area_cm2"),
        supplied_area,
        rtol=1e-12,
        atol=0.0,
    ):
        raise ActivityNormalizationError(
            "geometric reconstruction area conflicts with source electrode_area_cm2"
        )
    return "current_density"


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


def normalize_activity_series(
    series: Series,
    *,
    basis: ActivityBasis,
    denominator_value: float,
    denominator_unit: str,
    output_unit: str | None = None,
    sign_mode: SignMode = "signed",
    geometric_area_value: float | None = None,
    geometric_area_unit: str | None = None,
) -> Series:
    """Normalize one current Series and retain deterministic source provenance."""
    if not isinstance(series, Series):
        raise TypeError("series must be a Series")

    current_basis = _series_basis(
        series,
        geometric_area_value=geometric_area_value,
        geometric_area_unit=geometric_area_unit,
    )
    result = normalize_activity(
        series.y,
        current_unit=series.y_axis.unit or "",
        current_basis=current_basis,
        basis=basis,
        denominator_value=denominator_value,
        denominator_unit=denominator_unit,
        output_unit=output_unit,
        sign_mode=sign_mode,
        geometric_area_value=geometric_area_value,
        geometric_area_unit=geometric_area_unit,
    )

    source_normalization = _normalization(series)
    provenance = make_analysis_provenance(
        series,
        input_basis=f"activity_normalization:{current_basis}",
        units={
            "source_current": result.source_current_unit,
            "canonical_source_current": (
                "A" if result.source_current_basis == "current" else "A/cm^2"
            ),
            "total_current": "A",
            "denominator": result.denominator_unit,
            "canonical_denominator": result.canonical_denominator_unit,
            "output": result.output_unit,
        },
        parameters={
            "basis": result.basis,
            "source_current_basis": result.source_current_basis,
            "source_normalization": source_normalization,
            "sign_mode": result.sign_mode,
            "denominator_value": result.denominator_value,
            "denominator_canonical_value": result.denominator_canonical_value,
            "geometric_area_cm2": result.geometric_area_cm2,
        },
    )

    metadata = series.metadata_dict()
    metadata.update(
        {
            "analysis": "activity_normalization",
            "equation": "activity = total_current / denominator",
            "basis": result.basis,
            "sign_mode": result.sign_mode,
            "source_current_basis": result.source_current_basis,
            "source_current_unit": result.source_current_unit,
            "source_normalization": source_normalization,
            "geometric_area_cm2": result.geometric_area_cm2,
            "denominator_value": result.denominator_value,
            "denominator_unit": result.denominator_unit,
            "denominator_canonical_value": result.denominator_canonical_value,
            "denominator_canonical_unit": result.canonical_denominator_unit,
            "output_unit": result.output_unit,
            "source": _source_dict(series),
            "provenance": provenance,
        }
    )

    return Series(
        x=series.x,
        y=result.values,
        key=series.key,
        label=series.label,
        x_axis=series.x_axis,
        y_axis=Axis(
            "activity",
            unit=result.output_unit,
            label=_LABEL[result.basis],
            metadata={"normalization": result.basis},
        ),
        metadata=metadata,
    )


def _keyed(
    mapping: Mapping[str, object],
    *,
    expected: tuple[str, ...],
    name: str,
) -> dict[str, tuple[object, str]]:
    if not isinstance(mapping, Mapping):
        raise TypeError(f"{name} must be a mapping addressed by Series.key")

    normalized: dict[str, tuple[object, str]] = {}
    for raw_key, spec in mapping.items():
        if not isinstance(raw_key, str) or not raw_key.strip():
            raise ActivityNormalizationError(f"{name} keys must be non-empty strings")
        key = raw_key.strip()
        if key in normalized:
            raise ActivityNormalizationError(
                f"{name} keys must be unique after normalization"
            )
        if (
            not isinstance(spec, (tuple, list))
            or len(spec) != 2
            or not isinstance(spec[1], str)
            or not spec[1].strip()
        ):
            raise ActivityNormalizationError(
                f"{name}[{key!r}] must be a (value, unit) pair"
            )
        normalized[key] = (spec[0], spec[1])

    missing = set(expected) - set(normalized)
    unknown = set(normalized) - set(expected)
    if missing:
        raise ActivityNormalizationError(
            f"{name} is missing Series.key values: {sorted(missing)!r}"
        )
    if unknown:
        raise ActivityNormalizationError(
            f"{name} contains unknown Series.key values: {sorted(unknown)!r}"
        )
    return normalized


def normalize_activity_dataset(
    dataset: Dataset,
    denominators: Mapping[str, object],
    *,
    basis: ActivityBasis,
    output_unit: str | None = None,
    sign_mode: SignMode = "signed",
    geometric_areas: Mapping[str, object] | None = None,
) -> Dataset:
    """Normalize multiple catalysts with denominator mappings keyed by stable Series.key."""
    if not isinstance(dataset, Dataset):
        raise TypeError("dataset must be a Dataset")
    if len(dataset) == 0:
        raise ActivityNormalizationError("cannot normalize an empty Dataset")

    keys = tuple(item.key for item in dataset)
    if any(not key for key in keys):
        raise ActivityNormalizationError(
            "activity Dataset normalization requires non-empty Series.key values"
        )
    denominator_map = _keyed(denominators, expected=keys, name="denominators")

    density_keys = tuple(
        item.key
        for item in dataset
        if item.y_axis.name.casefold() in {"current_density", "partial_current_density"}
    )
    if density_keys:
        if geometric_areas is None:
            raise ActivityNormalizationError(
                "geometric_areas is required for current-density Dataset members"
            )
        area_map = _keyed(
            geometric_areas,
            expected=density_keys,
            name="geometric_areas",
        )
    else:
        if geometric_areas is not None:
            raise ActivityNormalizationError(
                "geometric_areas must be omitted for total-current-only Dataset"
            )
        area_map = {}

    output: list[Series] = []
    for item in dataset:
        denominator_value, denominator_unit = denominator_map[item.key]
        area_value, area_unit = area_map.get(item.key, (None, None))
        output.append(
            normalize_activity_series(
                item,
                basis=basis,
                denominator_value=denominator_value,
                denominator_unit=denominator_unit,
                output_unit=output_unit,
                sign_mode=sign_mode,
                geometric_area_value=area_value,
                geometric_area_unit=area_unit,
            )
        )

    resolved_basis = _basis(basis)
    return Dataset(
        series=tuple(output),
        name=dataset.name or "activity",
        metadata={
            "analysis": "activity_normalization",
            "basis": resolved_basis,
            "sign_mode": _sign(sign_mode),
            "output_unit": _output_unit(resolved_basis, output_unit),
            "series_keys": keys,
        },
    )


__all__ = [
    "ActivityBasis",
    "ActivityCurrentBasis",
    "ActivityNormalizationError",
    "ActivityNormalizationResult",
    "normalize_activity",
    "normalize_activity_dataset",
    "normalize_activity_series",
]
