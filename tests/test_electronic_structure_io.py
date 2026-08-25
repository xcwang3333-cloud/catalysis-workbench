from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from catalysis_workbench.io.electronic_structure import (
    ElectronicStructureIOError,
    _convert_chgcar_result,
    _convert_vasprun_result,
)


@dataclass(frozen=True)
class _Element:
    symbol: str


@dataclass(frozen=True)
class _Specie:
    symbol: str

    @property
    def element(self) -> _Element:
        return _Element(self.symbol)

    def __str__(self) -> str:
        return self.symbol


@dataclass
class _Site:
    specie: _Specie
    coords: np.ndarray
    label: str | None = None
    is_ordered: bool = True


@dataclass
class _Lattice:
    matrix: np.ndarray


class _Structure(list[_Site]):
    def __init__(self, sites: list[_Site], *, cell: float = 2.0) -> None:
        super().__init__(sites)
        self.is_ordered = True
        self.lattice = _Lattice(np.eye(3) * cell)


@dataclass(frozen=True)
class _Spin:
    name: str
    value: int


UP = _Spin("up", 1)
DOWN = _Spin("down", -1)


@dataclass
class _Dos:
    energies: np.ndarray
    densities: dict[_Spin, np.ndarray]


class _Run:
    def __init__(
        self,
        *,
        ispin: int,
        pdos: list[dict[str, dict[_Spin, np.ndarray]]] | None = None,
        noncollinear: bool = False,
    ) -> None:
        self.parameters = {
            "ISPIN": ispin,
            "LNONCOLLINEAR": noncollinear,
            "LSORBIT": False,
        }
        energies = np.array([-1.0, 0.0, 1.0])
        if ispin == 1:
            densities = {UP: np.array([1.0, 2.0, 1.0])}
        else:
            densities = {
                UP: np.array([1.0, 2.0, 1.0]),
                DOWN: np.array([0.5, 1.0, 0.5]),
            }
        self.tdos = _Dos(energies, densities)
        self.efermi = 0.25
        self.final_structure = _Structure(
            [
                _Site(_Specie("Fe"), np.array([0.0, 0.0, 0.0]), "Fe1"),
                _Site(_Specie("O"), np.array([1.0, 1.0, 1.0]), "O1"),
            ]
        )
        self.pdos = [] if pdos is None else pdos


def test_vasprun_conversion_preserves_source_energy_and_nonspin_total() -> None:
    result = _convert_vasprun_result(
        _Run(ispin=1),
        path="vasprun.xml",
        source_id="sample-A",
    )
    np.testing.assert_allclose(result.energy.values_ev, [-1.0, 0.0, 1.0])
    assert result.energy.source_fermi_ev == pytest.approx(0.25)
    assert result.energy.applied_shift_ev == 0.0
    assert result.channels[0].spin == "total"
    assert result.channels[0].projection.kind == "total"
    assert result.metadata["source_id"] == "sample-A"


def test_vasprun_conversion_retains_collinear_site_orbital_pdos() -> None:
    pdos = [
        {
            "dxy": {
                UP: np.array([0.1, 0.2, 0.3]),
                DOWN: np.array([0.05, 0.1, 0.15]),
            }
        },
        {
            "p": {
                UP: np.array([0.2, 0.3, 0.4]),
                DOWN: np.array([0.1, 0.15, 0.2]),
            }
        },
    ]
    result = _convert_vasprun_result(
        _Run(ispin=2, pdos=pdos),
        path="vasprun.xml",
        source_id=None,
    )
    assert [(item.projection.key, item.spin) for item in result.channels[:2]] == [
        ("total", "up"),
        ("total", "down"),
    ]
    pdos_channels = result.channels[2:]
    assert len(pdos_channels) == 4
    assert pdos_channels[0].projection.site_index == 0
    assert pdos_channels[0].projection.element == "Fe"
    assert pdos_channels[0].projection.orbital == "dxy"
    assert pdos_channels[0].normalization_basis == "site"


def test_vasprun_noncollinear_and_pdos_site_mismatch_fail_closed() -> None:
    with pytest.raises(ElectronicStructureIOError, match="non-collinear"):
        _convert_vasprun_result(
            _Run(ispin=2, noncollinear=True),
            path="vasprun.xml",
            source_id=None,
        )
    with pytest.raises(ElectronicStructureIOError, match="site count"):
        _convert_vasprun_result(
            _Run(ispin=2, pdos=[{}]),
            path="vasprun.xml",
            source_id=None,
        )


class _Chgcar:
    def __init__(self, data: dict[str, np.ndarray]) -> None:
        self.structure = _Structure(
            [_Site(_Specie("H"), np.array([0.0, 0.0, 0.0]))]
        )
        self.data = data


def test_chgcar_conversion_divides_backend_grid_by_cell_volume_once() -> None:
    raw_total = np.array([[[8.0]], [[16.0]]])
    raw_diff = np.array([[[4.0]], [[-4.0]]])
    result = _convert_chgcar_result(
        _Chgcar({"total": raw_total, "diff": raw_diff}),
        path="CHGCAR",
        source_id="density-A",
    )
    np.testing.assert_allclose(
        result.components["total"].reshape(-1),
        [1.0, 2.0],
    )
    np.testing.assert_allclose(
        result.components["magnetization_z"].reshape(-1),
        [0.5, -0.5],
    )
    assert result.cell_volume_angstrom3 == pytest.approx(8.0)
    assert result.voxel_volume_angstrom3 == pytest.approx(4.0)
    assert result.component_integrals["total"] == pytest.approx(12.0)
    assert result.metadata["density_conversion"] == (
        "pymatgen-grid / cell_volume_angstrom3"
    )


def test_chgcar_unsupported_component_layout_fails_closed() -> None:
    with pytest.raises(ElectronicStructureIOError, match="unsupported"):
        _convert_chgcar_result(
            _Chgcar(
                {
                    "total": np.ones((1, 1, 1)),
                    "diff_x": np.ones((1, 1, 1)),
                }
            ),
            path="CHGCAR",
            source_id=None,
        )
