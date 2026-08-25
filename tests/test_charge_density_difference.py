from __future__ import annotations

import numpy as np
import pytest

from catalysis_workbench.computation import AtomicStructure
from catalysis_workbench.computation.charge_density_difference import (
    ChargeDensityDifferenceError,
    ChargeDensityDifferenceResult,
    ChargeDensityReferenceTerm,
    ChargeDensitySource,
    calculate_charge_density_difference,
    charge_density_difference_frame,
)
from catalysis_workbench.computation.electronic_structure import (
    ElectronicStructureError,
    VolumetricGrid,
)


def _structure(
    *,
    lattice_x: float = 2.0,
    species: tuple[str, ...] = ("H",),
    elements: tuple[str, ...] = ("H",),
    coordinates: tuple[tuple[float, float, float], ...] = ((0.0, 0.0, 0.0),),
    site_keys: tuple[str, ...] = ("site-H",),
) -> AtomicStructure:
    return AtomicStructure(
        species=species,
        elements=elements,
        cartesian_coordinates=coordinates,
        lattice_angstrom=np.array(
            [[lattice_x, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 2.0]]
        ),
        pbc=(True, True, True),
        site_keys=site_keys,
    )


def _grid(
    values: np.ndarray,
    *,
    structure: AtomicStructure | None = None,
    component: str = "total",
    extra_components: dict[str, np.ndarray] | None = None,
) -> VolumetricGrid:
    components = {component: np.asarray(values, dtype=float)}
    if extra_components:
        components.update(extra_components)
    return VolumetricGrid(
        structure=_structure() if structure is None else structure,
        components=components,
    )


def _source(
    key: str,
    values: np.ndarray,
    *,
    registration_id: str = "frame-A",
    structure: AtomicStructure | None = None,
    component: str = "total",
    extra_components: dict[str, np.ndarray] | None = None,
    source_label: str | None = None,
) -> ChargeDensitySource:
    return ChargeDensitySource(
        key=key,
        grid=_grid(
            values,
            structure=structure,
            component=component,
            extra_components=extra_components,
        ),
        component=component,
        registration_id=registration_id,
        source_label=source_label,
    )


def test_hand_verifiable_2x2x2_difference_and_integral() -> None:
    combined_values = np.arange(10.0, 18.0).reshape(2, 2, 2)
    reference_values = np.full((2, 2, 2), 2.0)
    combined = _source("combined", combined_values)
    reference = ChargeDensityReferenceTerm(
        _source("fragment", reference_values),
        coefficient=2.0,
    )

    result = calculate_charge_density_difference(
        combined,
        (reference,),
        lattice_tolerance_angstrom=0.0,
    )

    expected = combined_values - 2.0 * reference_values
    assert np.array_equal(result.difference, expected)
    assert result.grid_shape == (2, 2, 2)
    assert result.cell_volume_angstrom3 == pytest.approx(8.0)
    assert result.voxel_volume_angstrom3 == pytest.approx(1.0)
    assert result.integrated_difference_electrons == pytest.approx(float(expected.sum()))
    assert result.density_unit == "1/angstrom^3"
    assert result.source_component == "total"


def test_multiple_ordered_reference_terms_use_explicit_coefficients() -> None:
    combined = _source("combined", np.full((2, 2, 2), 10.0))
    first = ChargeDensityReferenceTerm(
        _source("first", np.full((2, 2, 2), 2.0)),
        coefficient=0.5,
    )
    second = ChargeDensityReferenceTerm(
        _source("second", np.full((2, 2, 2), 3.0)),
        coefficient=2.0,
    )

    result = calculate_charge_density_difference(
        combined,
        (first, second),
        lattice_tolerance_angstrom=0.0,
    )
    reversed_result = calculate_charge_density_difference(
        combined,
        (second, first),
        lattice_tolerance_angstrom=0.0,
    )

    assert np.array_equal(result.difference, np.full((2, 2, 2), 3.0))
    assert np.array_equal(reversed_result.difference, result.difference)
    assert tuple(term.source.key for term in result.references) == ("first", "second")
    assert result.digest != reversed_result.digest


def test_source_and_result_arrays_are_immutable_and_frame_is_detached() -> None:
    combined = _source("combined", np.full((2, 2, 2), 5.0), source_label="Combined")
    reference = ChargeDensityReferenceTerm(
        _source("reference", np.ones((2, 2, 2)), source_label="Reference"),
        coefficient=1.0,
    )
    result = calculate_charge_density_difference(
        combined,
        (reference,),
        lattice_tolerance_angstrom=1e-8,
    )

    with pytest.raises(ValueError):
        combined.grid.components["total"][0, 0, 0] = 99.0
    with pytest.raises(ValueError):
        result.difference[0, 0, 0] = 99.0

    frame = charge_density_difference_frame(result)
    assert list(frame["role"]) == ["combined", "reference"]
    assert list(frame["formula_coefficient"]) == [1.0, -1.0]
    assert frame.loc[1, "reference_coefficient"] == pytest.approx(1.0)
    assert frame.loc[0, "grid_digest"] == combined.grid.digest
    assert frame.loc[1, "structure_digest"] == reference.source.grid.structure.digest
    frame.loc[0, "source_key"] = "mutated"
    assert result.combined.key == "combined"


def test_registration_mismatch_fails_before_arithmetic() -> None:
    combined = _source("combined", np.ones((2, 2, 2)), registration_id="frame-A")
    reference = ChargeDensityReferenceTerm(
        _source("reference", np.ones((2, 2, 2)), registration_id="frame-B"),
        coefficient=1.0,
    )

    with pytest.raises(ChargeDensityDifferenceError, match="registration_id"):
        calculate_charge_density_difference(
            combined,
            (reference,),
            lattice_tolerance_angstrom=0.0,
        )


def test_grid_shape_mismatch_fails() -> None:
    combined = _source("combined", np.ones((2, 2, 2)))
    reference = ChargeDensityReferenceTerm(
        _source("reference", np.ones((2, 2, 3))),
        coefficient=1.0,
    )

    with pytest.raises(ChargeDensityDifferenceError, match="grid shape"):
        calculate_charge_density_difference(
            combined,
            (reference,),
            lattice_tolerance_angstrom=0.0,
        )


def test_lattice_mismatch_respects_explicit_absolute_tolerance() -> None:
    combined = _source("combined", np.ones((2, 2, 2)))
    near_structure = _structure(lattice_x=2.0 + 5e-7)
    far_structure = _structure(lattice_x=2.0 + 2e-5)
    near = ChargeDensityReferenceTerm(
        _source("near", np.ones((2, 2, 2)), structure=near_structure),
        coefficient=1.0,
    )
    far = ChargeDensityReferenceTerm(
        _source("far", np.ones((2, 2, 2)), structure=far_structure),
        coefficient=1.0,
    )

    result = calculate_charge_density_difference(
        combined,
        (near,),
        lattice_tolerance_angstrom=1e-6,
    )
    assert result.lattice_tolerance_angstrom == pytest.approx(1e-6)
    assert result.difference_grid.structure == combined.grid.structure
    assert near.source.grid.structure.lattice_angstrom[0, 0] == pytest.approx(2.0 + 5e-7)

    with pytest.raises(ChargeDensityDifferenceError, match="lattice_tolerance"):
        calculate_charge_density_difference(
            combined,
            (far,),
            lattice_tolerance_angstrom=1e-6,
        )


def test_invalid_lattice_tolerance_fails() -> None:
    combined = _source("combined", np.ones((2, 2, 2)))
    reference = ChargeDensityReferenceTerm(
        _source("reference", np.ones((2, 2, 2))),
        coefficient=1.0,
    )

    for tolerance in (-1.0, np.nan, np.inf):
        with pytest.raises((ChargeDensityDifferenceError, TypeError)):
            calculate_charge_density_difference(
                combined,
                (reference,),
                lattice_tolerance_angstrom=tolerance,
            )


def test_component_mismatch_and_missing_component_fail_closed() -> None:
    combined = _source(
        "combined",
        np.ones((2, 2, 2)),
        extra_components={"magnetization_z": np.zeros((2, 2, 2))},
    )
    magnetic_source = ChargeDensitySource(
        key="magnetic",
        grid=combined.grid,
        component="magnetization_z",
        registration_id="frame-A",
    )
    magnetic = ChargeDensityReferenceTerm(magnetic_source, coefficient=1.0)

    with pytest.raises(ChargeDensityDifferenceError, match="like-for-like"):
        calculate_charge_density_difference(
            combined,
            (magnetic,),
            lattice_tolerance_angstrom=0.0,
        )

    with pytest.raises(ChargeDensityDifferenceError, match="not retained"):
        ChargeDensitySource(
            key="missing",
            grid=combined.grid,
            component="not-a-component",
            registration_id="frame-A",
        )


def test_canonical_density_unit_rejects_incompatible_unit_at_foundation() -> None:
    with pytest.raises(ElectronicStructureError, match="density_unit"):
        VolumetricGrid(
            structure=_structure(),
            components={"total": np.ones((2, 2, 2))},
            density_unit="electron/bohr^3",
        )


def test_nonfinite_reference_coefficient_fails() -> None:
    source = _source("reference", np.ones((2, 2, 2)))
    for coefficient in (np.nan, np.inf, -np.inf):
        with pytest.raises(ChargeDensityDifferenceError, match="finite"):
            ChargeDensityReferenceTerm(source, coefficient=coefficient)


def test_different_atomic_subsystems_are_allowed_with_common_registration() -> None:
    combined_structure = _structure(
        species=("H", "He"),
        elements=("H", "He"),
        coordinates=((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)),
        site_keys=("site-H", "site-He"),
    )
    reference_structure = _structure(
        species=("He",),
        elements=("He",),
        coordinates=((1.0, 1.0, 1.0),),
        site_keys=("site-He",),
    )
    combined = _source(
        "combined",
        np.full((2, 2, 2), 4.0),
        structure=combined_structure,
    )
    reference = ChargeDensityReferenceTerm(
        _source(
            "helium-subsystem",
            np.ones((2, 2, 2)),
            structure=reference_structure,
        ),
        coefficient=1.0,
    )

    result = calculate_charge_density_difference(
        combined,
        (reference,),
        lattice_tolerance_angstrom=0.0,
    )

    assert combined.grid.structure.digest != reference.source.grid.structure.digest
    assert np.array_equal(result.difference, np.full((2, 2, 2), 3.0))
    assert result.difference_grid.structure.digest == combined.grid.structure.digest


def test_duplicate_reference_source_keys_fail_instead_of_hidden_aggregation() -> None:
    combined = _source("combined", np.full((2, 2, 2), 3.0))
    source = _source("same", np.ones((2, 2, 2)))
    first = ChargeDensityReferenceTerm(source, coefficient=1.0)
    second = ChargeDensityReferenceTerm(source, coefficient=2.0)

    with pytest.raises(ChargeDensityDifferenceError, match="unique"):
        calculate_charge_density_difference(
            combined,
            (first, second),
            lattice_tolerance_angstrom=0.0,
        )


def test_direct_result_reconstruction_rejects_inconsistent_difference_grid() -> None:
    combined = _source("combined", np.full((2, 2, 2), 4.0))
    reference = ChargeDensityReferenceTerm(
        _source("reference", np.ones((2, 2, 2))),
        coefficient=1.0,
    )
    wrong = VolumetricGrid(
        structure=combined.grid.structure,
        components={"difference": np.zeros((2, 2, 2))},
    )

    with pytest.raises(ChargeDensityDifferenceError, match="contradicts"):
        ChargeDensityDifferenceResult(
            combined=combined,
            references=(reference,),
            difference_grid=wrong,
            lattice_tolerance_angstrom=0.0,
        )


def test_digest_retains_registration_coefficient_source_and_tolerance() -> None:
    combined = _source("combined", np.full((2, 2, 2), 5.0))
    reference_source = _source("reference", np.ones((2, 2, 2)))
    one = ChargeDensityReferenceTerm(reference_source, coefficient=1.0)
    two = ChargeDensityReferenceTerm(reference_source, coefficient=2.0)

    base = calculate_charge_density_difference(
        combined,
        (one,),
        lattice_tolerance_angstrom=0.0,
    )
    changed_coefficient = calculate_charge_density_difference(
        combined,
        (two,),
        lattice_tolerance_angstrom=0.0,
    )
    changed_tolerance = calculate_charge_density_difference(
        combined,
        (one,),
        lattice_tolerance_angstrom=1e-8,
    )
    changed_registration_combined = _source(
        "combined",
        np.full((2, 2, 2), 5.0),
        registration_id="frame-B",
    )
    changed_registration_reference = ChargeDensityReferenceTerm(
        _source(
            "reference",
            np.ones((2, 2, 2)),
            registration_id="frame-B",
        ),
        coefficient=1.0,
    )
    changed_registration = calculate_charge_density_difference(
        changed_registration_combined,
        (changed_registration_reference,),
        lattice_tolerance_angstrom=0.0,
    )

    assert len({
        base.digest,
        changed_coefficient.digest,
        changed_tolerance.digest,
        changed_registration.digest,
    }) == 4


def test_source_label_does_not_change_scientific_digest() -> None:
    grid = _grid(np.ones((2, 2, 2)))
    first = ChargeDensitySource(
        key="source",
        grid=grid,
        component="total",
        registration_id="frame-A",
        source_label="Display A",
    )
    second = ChargeDensitySource(
        key="source",
        grid=grid,
        component="total",
        registration_id="frame-A",
        source_label="Display B",
    )

    assert first.digest == second.digest
    assert first != second


def test_calculation_does_not_invoke_numpy_interpolation(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("interpolation must not be invoked")

    monkeypatch.setattr(np, "interp", forbidden)
    combined = _source("combined", np.full((2, 2, 2), 2.0))
    reference = ChargeDensityReferenceTerm(
        _source("reference", np.ones((2, 2, 2))),
        coefficient=1.0,
    )

    result = calculate_charge_density_difference(
        combined,
        (reference,),
        lattice_tolerance_angstrom=0.0,
    )
    assert np.array_equal(result.difference, np.ones((2, 2, 2)))
