"""Strict co-registered volumetric electron-density difference arithmetic."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .electronic_structure import VolumetricGrid


class ChargeDensityDifferenceError(ValueError):
    """Raised when volumetric difference state is scientifically incompatible."""


def _text(value: object, *, name: str, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    text = str(value).strip()
    if not text:
        raise ChargeDensityDifferenceError(f"{name} must not be blank")
    return text


def _finite(value: object, *, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a finite float") from exc
    if not np.isfinite(number):
        raise ChargeDensityDifferenceError(f"{name} must be finite")
    return number


def _lattice_tolerance(value: object) -> float:
    tolerance = _finite(value, name="lattice_tolerance_angstrom")
    if tolerance < 0:
        raise ChargeDensityDifferenceError(
            "lattice_tolerance_angstrom must be non-negative"
        )
    return tolerance


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
class ChargeDensitySource:
    """One explicit volumetric source in a caller-asserted co-registration frame."""

    key: str
    grid: VolumetricGrid
    component: str
    registration_id: str
    source_label: str | None = None
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        key = str(_text(self.key, name="key"))
        if not isinstance(self.grid, VolumetricGrid):
            raise TypeError("grid must be a VolumetricGrid")
        component = str(_text(self.component, name="component"))
        if component not in self.grid.components:
            raise ChargeDensityDifferenceError(
                f"component {component!r} is not retained by source grid"
            )
        registration_id = str(_text(self.registration_id, name="registration_id"))
        source_label = _text(self.source_label, name="source_label", optional=True)

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.ChargeDensitySource.v1\0")
        for value in (
            key,
            self.grid.digest,
            self.grid.structure.digest,
            component,
            self.grid.density_unit,
            registration_id,
        ):
            _digest_text(digest, value)

        object.__setattr__(self, "key", key)
        object.__setattr__(self, "component", component)
        object.__setattr__(self, "registration_id", registration_id)
        object.__setattr__(self, "source_label", source_label)
        object.__setattr__(self, "digest", digest.hexdigest())

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, ChargeDensitySource)
            and self.digest == other.digest
            and self.source_label == other.source_label
        )


@dataclass(frozen=True, slots=True, eq=False)
class ChargeDensityReferenceTerm:
    """One ordered reference source with an explicit caller-supplied coefficient."""

    source: ChargeDensitySource
    coefficient: float
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.source, ChargeDensitySource):
            raise TypeError("source must be a ChargeDensitySource")
        coefficient = _finite(self.coefficient, name="coefficient")

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.ChargeDensityReferenceTerm.v1\0")
        _digest_text(digest, self.source.digest)
        _digest_float(digest, coefficient)

        object.__setattr__(self, "coefficient", coefficient)
        object.__setattr__(self, "digest", digest.hexdigest())

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, ChargeDensityReferenceTerm)
            and self.digest == other.digest
            and self.source == other.source
        )


def _validate_sources(
    combined: ChargeDensitySource,
    references: Sequence[ChargeDensityReferenceTerm],
    *,
    lattice_tolerance_angstrom: float,
) -> tuple[ChargeDensityReferenceTerm, ...]:
    if not isinstance(combined, ChargeDensitySource):
        raise TypeError("combined must be a ChargeDensitySource")
    retained = tuple(references)
    if not retained or not all(
        isinstance(term, ChargeDensityReferenceTerm) for term in retained
    ):
        raise ChargeDensityDifferenceError(
            "references must contain at least one ChargeDensityReferenceTerm"
        )
    source_keys = tuple(term.source.key for term in retained)
    if len(source_keys) != len(set(source_keys)):
        raise ChargeDensityDifferenceError("reference source keys must be unique")

    tolerance = _lattice_tolerance(lattice_tolerance_angstrom)
    combined_grid = combined.grid
    combined_lattice = combined_grid.structure.lattice_angstrom
    assert combined_lattice is not None

    for term in retained:
        source = term.source
        grid = source.grid
        if source.registration_id != combined.registration_id:
            raise ChargeDensityDifferenceError(
                "all sources require the same explicit registration_id"
            )
        if source.component != combined.component:
            raise ChargeDensityDifferenceError(
                "all sources require the same like-for-like volumetric component"
            )
        if grid.density_unit != combined_grid.density_unit:
            raise ChargeDensityDifferenceError(
                "all sources require the same physical density_unit"
            )
        if grid.grid_shape != combined_grid.grid_shape:
            raise ChargeDensityDifferenceError(
                "all sources require an identical volumetric grid shape"
            )
        lattice = grid.structure.lattice_angstrom
        assert lattice is not None
        if not np.allclose(
            lattice,
            combined_lattice,
            rtol=0.0,
            atol=tolerance,
        ):
            raise ChargeDensityDifferenceError(
                "source lattice exceeds the explicit lattice_tolerance_angstrom; "
                "no lattice transformation/alignment is performed"
            )
    return retained


def _difference_array(
    combined: ChargeDensitySource,
    references: Sequence[ChargeDensityReferenceTerm],
) -> np.ndarray:
    difference = np.array(
        combined.grid.components[combined.component],
        dtype=np.float64,
        copy=True,
        order="C",
    )
    for term in references:
        difference -= term.coefficient * term.source.grid.components[term.source.component]
    return difference


@dataclass(frozen=True, slots=True, eq=False)
class ChargeDensityDifferenceResult:
    """Immutable audited result of one explicit co-registered linear combination."""

    combined: ChargeDensitySource
    references: Sequence[ChargeDensityReferenceTerm]
    difference_grid: VolumetricGrid
    lattice_tolerance_angstrom: float
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        tolerance = _lattice_tolerance(self.lattice_tolerance_angstrom)
        references = _validate_sources(
            self.combined,
            self.references,
            lattice_tolerance_angstrom=tolerance,
        )
        if not isinstance(self.difference_grid, VolumetricGrid):
            raise TypeError("difference_grid must be a VolumetricGrid")
        if tuple(self.difference_grid.components) != ("difference",):
            raise ChargeDensityDifferenceError(
                "difference_grid must contain exactly one 'difference' component"
            )
        if self.difference_grid.structure != self.combined.grid.structure:
            raise ChargeDensityDifferenceError(
                "difference_grid must retain the exact combined-source structure"
            )
        if self.difference_grid.grid_shape != self.combined.grid.grid_shape:
            raise ChargeDensityDifferenceError(
                "difference_grid shape must match the combined source grid"
            )
        if self.difference_grid.density_unit != self.combined.grid.density_unit:
            raise ChargeDensityDifferenceError(
                "difference_grid density_unit must match source density_unit"
            )

        expected = _difference_array(self.combined, references)
        actual = self.difference_grid.components["difference"]
        if not np.array_equal(actual, expected):
            raise ChargeDensityDifferenceError(
                "difference_grid contradicts retained source grids/coefficients"
            )

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.ChargeDensityDifferenceResult.v1\0")
        _digest_text(digest, self.combined.digest)
        for term in references:
            _digest_text(digest, term.digest)
        _digest_text(digest, self.difference_grid.digest)
        _digest_float(digest, tolerance)

        object.__setattr__(self, "references", references)
        object.__setattr__(self, "lattice_tolerance_angstrom", tolerance)
        object.__setattr__(self, "digest", digest.hexdigest())

    @property
    def registration_id(self) -> str:
        return self.combined.registration_id

    @property
    def source_component(self) -> str:
        return self.combined.component

    @property
    def density_unit(self) -> str:
        return self.difference_grid.density_unit

    @property
    def grid_shape(self) -> tuple[int, int, int]:
        return self.difference_grid.grid_shape

    @property
    def cell_volume_angstrom3(self) -> float:
        return self.difference_grid.cell_volume_angstrom3

    @property
    def voxel_volume_angstrom3(self) -> float:
        return self.difference_grid.voxel_volume_angstrom3

    @property
    def integrated_difference_electrons(self) -> float:
        return self.difference_grid.component_integrals["difference"]

    @property
    def difference(self) -> np.ndarray:
        return self.difference_grid.components["difference"]

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, ChargeDensityDifferenceResult)
            and self.digest == other.digest
            and self.combined == other.combined
            and self.references == other.references
        )


def calculate_charge_density_difference(
    combined: ChargeDensitySource,
    references: Sequence[ChargeDensityReferenceTerm],
    *,
    lattice_tolerance_angstrom: float,
) -> ChargeDensityDifferenceResult:
    """Calculate an explicit difference without interpolation, alignment or renormalization."""
    tolerance = _lattice_tolerance(lattice_tolerance_angstrom)
    retained = _validate_sources(
        combined,
        references,
        lattice_tolerance_angstrom=tolerance,
    )
    difference = _difference_array(combined, retained)
    difference_grid = VolumetricGrid(
        structure=combined.grid.structure,
        components={"difference": difference},
        density_unit=combined.grid.density_unit,
        metadata={
            "operation": "charge-density-difference",
            "registration_id": combined.registration_id,
            "source_component": combined.component,
        },
    )
    return ChargeDensityDifferenceResult(
        combined=combined,
        references=retained,
        difference_grid=difference_grid,
        lattice_tolerance_angstrom=tolerance,
    )


def charge_density_difference_frame(
    result: ChargeDensityDifferenceResult,
) -> pd.DataFrame:
    """Return a detached one-row-per-source arithmetic/provenance table."""
    if not isinstance(result, ChargeDensityDifferenceResult):
        raise TypeError("result must be a ChargeDensityDifferenceResult")

    shared = {
        "result_digest": result.digest,
        "difference_grid_digest": result.difference_grid.digest,
        "registration_id": result.registration_id,
        "source_component": result.source_component,
        "density_unit": result.density_unit,
        "grid_shape": result.grid_shape,
        "cell_volume_angstrom3": result.cell_volume_angstrom3,
        "voxel_volume_angstrom3": result.voxel_volume_angstrom3,
        "integrated_difference_electrons": result.integrated_difference_electrons,
        "lattice_tolerance_angstrom": result.lattice_tolerance_angstrom,
    }
    rows = [
        {
            **shared,
            "role": "combined",
            "term_order": 0,
            "source_key": result.combined.key,
            "source_label": result.combined.source_label,
            "source_digest": result.combined.digest,
            "grid_digest": result.combined.grid.digest,
            "structure_digest": result.combined.grid.structure.digest,
            "reference_coefficient": None,
            "formula_coefficient": 1.0,
            "source_component_integral": result.combined.grid.component_integrals[
                result.source_component
            ],
        }
    ]
    for order, term in enumerate(result.references, start=1):
        rows.append(
            {
                **shared,
                "role": "reference",
                "term_order": order,
                "source_key": term.source.key,
                "source_label": term.source.source_label,
                "source_digest": term.source.digest,
                "grid_digest": term.source.grid.digest,
                "structure_digest": term.source.grid.structure.digest,
                "reference_coefficient": term.coefficient,
                "formula_coefficient": -term.coefficient,
                "source_component_integral": term.source.grid.component_integrals[
                    result.source_component
                ],
            }
        )
    return pd.DataFrame(rows)


__all__ = [
    "ChargeDensityDifferenceError",
    "ChargeDensityDifferenceResult",
    "ChargeDensityReferenceTerm",
    "ChargeDensitySource",
    "calculate_charge_density_difference",
    "charge_density_difference_frame",
]
