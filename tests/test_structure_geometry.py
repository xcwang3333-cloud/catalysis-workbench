from __future__ import annotations

import numpy as np
import pytest

from catalysis_workbench.computation import (
    AtomicStructure,
    GeometryError,
    PeriodicImage,
    SiteImage,
    SiteMapping,
    compare_structures,
    coordination_by_cutoff,
    site_angle,
    site_distance,
)


def _periodic() -> AtomicStructure:
    return AtomicStructure(
        species=("C", "O", "H"),
        elements=("C", "O", "H"),
        cartesian_coordinates=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        lattice_angstrom=((3.0, 0.0, 0.0), (0.5, 2.5, 0.0), (0.0, 0.0, 4.0)),
        pbc=(True, True, True),
        site_keys=("c", "o", "h"),
    )


def _molecule() -> AtomicStructure:
    return AtomicStructure(
        species=("O", "H", "H"),
        elements=("O", "H", "H"),
        cartesian_coordinates=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        site_keys=("o", "h1", "h2"),
    )


def test_exact_periodic_image_distance_and_triclinic_translation() -> None:
    structure = _periodic()
    result = site_distance(
        structure,
        SiteImage("c"),
        SiteImage("o", PeriodicImage(0, 1, 0)),
    )
    np.testing.assert_allclose(result.displacement_angstrom, [1.5, 2.5, 0.0])
    assert result.distance_angstrom == pytest.approx(np.hypot(1.5, 2.5))


def test_distance_does_not_apply_hidden_minimum_image() -> None:
    structure = AtomicStructure(
        species=("C", "O"),
        elements=("C", "O"),
        cartesian_coordinates=((0.1, 0.0, 0.0), (2.9, 0.0, 0.0)),
        lattice_angstrom=((3.0, 0.0, 0.0), (0.0, 3.0, 0.0), (0.0, 0.0, 3.0)),
        pbc=(True, True, True),
        site_keys=("a", "b"),
    )
    direct = site_distance(structure, SiteImage("a"), SiteImage("b"))
    image = site_distance(
        structure,
        SiteImage("a"),
        SiteImage("b", PeriodicImage(-1, 0, 0)),
    )
    assert direct.distance_angstrom == pytest.approx(2.8)
    assert image.distance_angstrom == pytest.approx(0.2)


def test_nonperiodic_distance_and_angle() -> None:
    structure = _molecule()
    assert site_distance(structure, SiteImage("o"), SiteImage("h1")).distance_angstrom == pytest.approx(1.0)
    result = site_angle(structure, SiteImage("h1"), SiteImage("o"), SiteImage("h2"))
    assert result.angle_degrees == pytest.approx(90.0)


def test_invalid_site_images_and_zero_length_angle_fail_closed() -> None:
    structure = _molecule()
    with pytest.raises(GeometryError, match="nonperiodic axis"):
        site_distance(
            structure,
            SiteImage("o"),
            SiteImage("h1", PeriodicImage(1, 0, 0)),
        )
    with pytest.raises(GeometryError, match="unknown site key"):
        site_distance(structure, SiteImage("missing"), SiteImage("h1"))
    with pytest.raises(GeometryError, match="nonzero vectors"):
        site_angle(structure, SiteImage("o"), SiteImage("o"), SiteImage("h1"))


def test_cutoff_coordination_is_image_bounded_and_deterministic() -> None:
    structure = AtomicStructure(
        species=("X",),
        elements=("C",),
        cartesian_coordinates=((0.0, 0.0, 0.0),),
        lattice_angstrom=((2.0, 0.0, 0.0), (0.0, 3.0, 0.0), (0.0, 0.0, 4.0)),
        pbc=(True, True, True),
        site_keys=("x",),
    )
    narrow = coordination_by_cutoff(structure, "x", 2.1, image_range=(0, 0, 0))
    assert narrow.coordination_number == 0
    expanded = coordination_by_cutoff(structure, "x", 2.1, image_range=(1, 0, 0))
    assert expanded.coordination_number == 2
    assert [neighbor.image.as_tuple() for neighbor in expanded.neighbors] == [
        (-1, 0, 0),
        (1, 0, 0),
    ]
    assert all(neighbor.site_key == "x" for neighbor in expanded.neighbors)


def test_coordination_rejects_nonperiodic_image_range() -> None:
    with pytest.raises(GeometryError, match="nonperiodic axis"):
        coordination_by_cutoff(_molecule(), "o", 2.0, image_range=(1, 0, 0))


def test_structure_comparison_identity_and_perturbation() -> None:
    reference = _molecule()
    identity = tuple(SiteMapping(key, key) for key in reference.site_keys)
    same = compare_structures(reference, reference, identity)
    np.testing.assert_allclose(same.distances_angstrom, 0.0)
    assert same.rmsd_angstrom == pytest.approx(0.0)
    assert same.max_displacement_angstrom == pytest.approx(0.0)

    candidate = AtomicStructure(
        species=reference.species,
        elements=reference.elements,
        cartesian_coordinates=((0.0, 0.0, 0.0), (1.1, 0.0, 0.0), (0.0, 1.2, 0.0)),
        site_keys=reference.site_keys,
    )
    changed = compare_structures(reference, candidate, identity)
    np.testing.assert_allclose(changed.distances_angstrom, [0.0, 0.1, 0.2])
    assert changed.rmsd_angstrom == pytest.approx(np.sqrt((0.0 + 0.01 + 0.04) / 3.0))
    assert changed.max_displacement_angstrom == pytest.approx(0.2)
    assert changed.displacement_vectors_angstrom.flags.writeable is False
    assert changed.distances_angstrom.flags.writeable is False


def test_structure_comparison_mapping_guards() -> None:
    structure = _molecule()
    with pytest.raises(GeometryError, match="reference site/image identities"):
        compare_structures(
            structure,
            structure,
            (SiteMapping("o", "o"), SiteMapping("o", "h1")),
        )
    with pytest.raises(GeometryError, match="candidate site/image identities"):
        compare_structures(
            structure,
            structure,
            (SiteMapping("o", "h1"), SiteMapping("h1", "h1")),
        )
