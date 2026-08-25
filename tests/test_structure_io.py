from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from catalysis_workbench.io.structure import (
    StructureIOError,
    _convert_site_collection,
    _select_record,
)


@dataclass
class _Element:
    symbol: str


@dataclass
class _Specie:
    text: str
    symbol: str

    @property
    def element(self) -> _Element:
        return _Element(self.symbol)

    def __str__(self) -> str:
        return self.text


@dataclass
class _Site:
    specie: _Specie
    coords: np.ndarray
    label: str | None = None
    is_ordered: bool = True


@dataclass
class _Lattice:
    matrix: np.ndarray


class _Collection(list[_Site]):
    def __init__(self, sites: list[_Site], *, ordered: bool = True) -> None:
        super().__init__(sites)
        self.is_ordered = ordered
        self.lattice = _Lattice(np.eye(3) * 5.0)


def _sites() -> list[_Site]:
    return [
        _Site(_Specie("Fe2+", "Fe"), np.array([0.0, 0.0, 0.0]), "Fe1"),
        _Site(_Specie("O2-", "O"), np.array([1.0, 2.0, 3.0]), "O1"),
    ]


def test_backend_conversion_preserves_order_and_species_state() -> None:
    result = _convert_site_collection(
        _Collection(_sites()),
        periodic=True,
        source_format="CIF",
        path="fixture.cif",
        source_id="sample-A",
    )
    assert result.species == ("Fe2+", "O2-")
    assert result.elements == ("Fe", "O")
    assert result.site_labels == ("Fe1", "O1")
    np.testing.assert_allclose(result.cartesian_coordinates[1], [1.0, 2.0, 3.0])
    np.testing.assert_allclose(result.lattice_angstrom, np.eye(3) * 5.0)
    assert result.pbc == (True, True, True)
    assert result.metadata["structure_format"] == "CIF"
    assert result.metadata["source_id"] == "sample-A"


def test_nonperiodic_conversion_does_not_fabricate_lattice() -> None:
    result = _convert_site_collection(
        _Collection(_sites()),
        periodic=False,
        source_format="XYZ",
        path="fixture.xyz",
        source_id=None,
    )
    assert result.lattice_angstrom is None
    assert result.pbc == (False, False, False)


def test_disordered_collection_and_site_fail_closed() -> None:
    with pytest.raises(StructureIOError, match="disordered"):
        _convert_site_collection(
            _Collection(_sites(), ordered=False),
            periodic=True,
            source_format="CIF",
            path="x.cif",
            source_id=None,
        )
    sites = _sites()
    sites[1].is_ordered = False
    with pytest.raises(StructureIOError, match="disordered"):
        _convert_site_collection(
            _Collection(sites),
            periodic=True,
            source_format="CIF",
            path="x.cif",
            source_id=None,
        )


def test_record_selection_requires_explicit_index_for_ambiguity() -> None:
    records = ["first", "second"]
    with pytest.raises(StructureIOError, match="explicit index"):
        _select_record(records, index=None, format_name="XYZ")
    assert _select_record(records, index=1, format_name="XYZ") == "second"
    with pytest.raises(StructureIOError, match="outside"):
        _select_record(records, index=2, format_name="XYZ")
    with pytest.raises(TypeError, match="integer"):
        _select_record(records, index=True, format_name="XYZ")


def test_blank_source_id_is_rejected() -> None:
    with pytest.raises(StructureIOError, match="source_id"):
        _convert_site_collection(
            _Collection(_sites()),
            periodic=True,
            source_format="POSCAR",
            path="POSCAR",
            source_id="   ",
        )
