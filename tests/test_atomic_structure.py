from __future__ import annotations

import numpy as np
import pytest

from catalysis_workbench.computation import AtomicStructure, StructureError


def _periodic(**changes: object) -> AtomicStructure:
    kwargs: dict[str, object] = {
        "species": ("Fe2+", "O2-"),
        "elements": ("Fe", "O"),
        "cartesian_coordinates": ((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)),
        "lattice_angstrom": ((4.0, 0.0, 0.0), (0.0, 4.0, 0.0), (0.0, 0.0, 4.0)),
        "pbc": (True, True, True),
        "site_labels": ("Fe1", "O1"),
        "metadata": {"source": {"name": "synthetic"}},
    }
    kwargs.update(changes)
    return AtomicStructure(**kwargs)


def test_periodic_structure_is_immutable_and_deterministic() -> None:
    coords = np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]])
    lattice = np.eye(3) * 4.0
    structure = _periodic(cartesian_coordinates=coords, lattice_angstrom=lattice)
    coords[0, 0] = 99.0
    lattice[0, 0] = 99.0

    assert structure.site_count == 2
    assert structure.is_periodic
    assert structure.site_keys == ("site-0000", "site-0001")
    assert structure.cartesian_coordinates[0, 0] == 0.0
    assert structure.lattice_angstrom is not None
    assert structure.lattice_angstrom[0, 0] == 4.0
    assert not structure.cartesian_coordinates.flags.writeable
    assert not structure.lattice_angstrom.flags.writeable

    same_science = _periodic(metadata={"different": "provenance"})
    assert structure.digest == same_science.digest
    assert structure == same_science


def test_metadata_is_deeply_immutable_and_detached() -> None:
    source = {"nested": {"values": [1, 2]}, "array": np.array([3.0, 4.0])}
    structure = _periodic(metadata=source)
    source["nested"]["values"].append(3)
    source["array"][0] = 99.0

    with pytest.raises(TypeError):
        structure.metadata["new"] = "x"  # type: ignore[index]
    frozen_array = structure.metadata["array"]
    with pytest.raises(ValueError):
        frozen_array[0] = 10.0

    detached = structure.metadata_dict()
    assert detached["nested"]["values"] == [1, 2]
    np.testing.assert_array_equal(detached["array"], [3.0, 4.0])
    detached["nested"]["values"].append(9)
    assert structure.metadata_dict()["nested"]["values"] == [1, 2]


def test_nonperiodic_structure_needs_no_lattice() -> None:
    structure = AtomicStructure(
        species=("H", "H"),
        elements=("H", "H"),
        cartesian_coordinates=((0.0, 0.0, 0.0), (0.74, 0.0, 0.0)),
    )
    assert structure.pbc == (False, False, False)
    assert structure.lattice_angstrom is None
    assert not structure.is_periodic


def test_site_order_and_explicit_keys_are_retained() -> None:
    structure = _periodic(site_keys=("iron", "oxygen"))
    assert structure.species == ("Fe2+", "O2-")
    assert structure.elements == ("Fe", "O")
    assert structure.site_keys == ("iron", "oxygen")
    assert structure.site_labels == ("Fe1", "O1")


@pytest.mark.parametrize(
    ("changes", "match"),
    [
        ({"species": ("Fe",)}, "lengths"),
        ({"elements": ("Fe",)}, "lengths"),
        ({"elements": ("FE", "O")}, "canonical"),
        ({"elements": ("Xx", "O")}, "canonical"),
        ({"site_keys": ("same", "same")}, "unique"),
        ({"site_keys": ("", "o")}, "nonblank"),
        ({"pbc": (True, False, False), "lattice_angstrom": None}, "require"),
        (
            {"lattice_angstrom": ((1.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 0.0, 1.0))},
            "nonsingular",
        ),
        ({"cartesian_coordinates": ((0.0, 0.0, np.nan), (1.0, 1.0, 1.0))}, "finite"),
    ],
)
def test_invalid_structure_state_fails_closed(changes: dict[str, object], match: str) -> None:
    with pytest.raises(StructureError, match=match):
        _periodic(**changes)


def test_complex_coordinates_are_rejected() -> None:
    with pytest.raises(StructureError, match="real"):
        _periodic(
            cartesian_coordinates=np.array(
                [[0.0 + 1.0j, 0.0, 0.0], [1.0, 1.0, 1.0]],
                dtype=np.complex128,
            )
        )


def test_pbc_requires_actual_boolean_flags() -> None:
    with pytest.raises(TypeError, match="booleans"):
        _periodic(pbc=(1, True, True))
