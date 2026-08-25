from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from catalysis_workbench.io.band_structure import _convert_vasprun_band_result
from catalysis_workbench.io.electronic_structure import ElectronicStructureIOError


class _Element:
    symbol = "H"


class _Specie:
    element = _Element()

    def __str__(self) -> str:
        return "H"


@dataclass
class _Site:
    coords: np.ndarray
    label: str = "H1"
    is_ordered: bool = True
    specie: _Specie = _Specie()


class _ReciprocalLattice:
    def __init__(self) -> None:
        self.matrix = np.diag([np.pi, np.pi, np.pi])


class _Lattice:
    def __init__(self) -> None:
        self.matrix = np.diag([2.0, 2.0, 2.0])
        self.reciprocal_lattice = _ReciprocalLattice()


class _Structure:
    is_ordered = True

    def __init__(self) -> None:
        self.lattice = _Lattice()
        self._sites = (_Site(np.zeros(3)),)

    def __iter__(self):
        return iter(self._sites)


class _Style:
    name = "Line_mode"


class _Kpoints:
    style = _Style()
    coord_type = "Reciprocal"
    num_kpts = 3
    kpts = (
        (0.0, 0.0, 0.0),
        (0.5, 0.0, 0.0),
        (0.0, 0.5, 0.0),
        (0.0, 1.0, 0.0),
    )
    labels = ("G", "X", "M", "Y")


def _actual_kpoints() -> np.ndarray:
    return np.array(
        [
            [0.0, 0.0, 0.0],
            [0.25, 0.0, 0.0],
            [0.5, 0.0, 0.0],
            [0.0, 0.5, 0.0],
            [0.0, 0.75, 0.0],
            [0.0, 1.0, 0.0],
        ]
    )


def _eigenvalues(offset: float) -> np.ndarray:
    values = np.zeros((6, 2, 2), dtype=np.float64)
    values[:, 0, 0] = np.arange(6.0) + offset
    values[:, 1, 0] = np.arange(6.0) + offset + 10.0
    values[:, :, 1] = 0.5
    return values


class _Run:
    def __init__(
        self,
        *,
        ispin: int = 1,
        eigenvalues: dict[object, np.ndarray] | None = None,
        actual_kpoints: np.ndarray | None = None,
        lsorbit: bool = False,
        lnoncollinear: bool = False,
    ) -> None:
        self.parameters = {
            "ISPIN": ispin,
            "LSORBIT": lsorbit,
            "LNONCOLLINEAR": lnoncollinear,
        }
        self.actual_kpoints = (
            _actual_kpoints() if actual_kpoints is None else actual_kpoints
        )
        self.eigenvalues = (
            {1: _eigenvalues(1.0)} if eigenvalues is None else eigenvalues
        )
        self.efermi = 5.25
        self.final_structure = _Structure()


def _convert(run: _Run, kpoints: object = _Kpoints()):
    return _convert_vasprun_band_result(
        run,
        kpoints,
        path="vasprun.xml",
        kpoints_path="KPOINTS",
        source_id="calc-A",
        backend_version="2026.8.20",
    )


def test_ispin1_backend_spin_up_container_maps_to_physical_total() -> None:
    state = _convert(_Run())

    assert [channel.spin for channel in state.channels] == ["total"]
    assert state.channels[0].band_indices == (0, 1)
    assert np.array_equal(
        state.channels[0].energies_ev,
        _eigenvalues(1.0)[:, :, 0].T,
    )
    assert state.reciprocal_cartesian_includes_2pi is True
    assert np.array_equal(
        state.reciprocal_lattice_cartesian,
        np.diag([np.pi, np.pi, np.pi]),
    )
    assert [segment.start_label for segment in state.path_segments] == ["G", "M"]
    assert state.metadata["ispin"] == 1
    assert state.metadata["reciprocal_cartesian_convention"] == "physics-2pi"


def test_ispin2_requires_and_preserves_complete_physical_spin_pair() -> None:
    up = _eigenvalues(2.0)
    down = _eigenvalues(3.0)
    state = _convert(_Run(ispin=2, eigenvalues={1: up, -1: down}))

    assert [channel.spin for channel in state.channels] == ["up", "down"]
    assert np.array_equal(state.channel("up").energies_ev, up[:, :, 0].T)
    assert np.array_equal(state.channel("down").energies_ev, down[:, :, 0].T)

    with pytest.raises(ElectronicStructureIOError, match="both up and down"):
        _convert(_Run(ispin=2, eigenvalues={1: up}))


def test_soc_and_noncollinear_sources_fail_closed() -> None:
    with pytest.raises(ElectronicStructureIOError, match="non-collinear/SOC"):
        _convert(_Run(lsorbit=True))
    with pytest.raises(ElectronicStructureIOError, match="non-collinear/SOC"):
        _convert(_Run(lnoncollinear=True))


def test_line_mode_actual_kpoints_must_match_every_interpolated_point() -> None:
    mismatched = _actual_kpoints()
    mismatched[1, 0] = 0.2
    with pytest.raises(ElectronicStructureIOError, match="do not match"):
        _convert(_Run(actual_kpoints=mismatched))

    too_many = np.vstack((_actual_kpoints(), [[0.2, 0.2, 0.2]]))
    with pytest.raises(ElectronicStructureIOError, match="hybrid/uniform\+line"):
        _convert(_Run(actual_kpoints=too_many))


def test_minimum_adapter_rejects_nonreciprocal_or_non_line_mode_path() -> None:
    class CartesianKpoints(_Kpoints):
        coord_type = "Cartesian"

    with pytest.raises(ElectronicStructureIOError, match="reciprocal-coordinate"):
        _convert(_Run(), CartesianKpoints())

    class ExplicitStyle:
        name = "Reciprocal"

    class ExplicitKpoints(_Kpoints):
        style = ExplicitStyle()

    with pytest.raises(ElectronicStructureIOError, match="line-mode"):
        _convert(_Run(), ExplicitKpoints())


def test_occupancy_column_is_not_used_to_change_band_energies() -> None:
    source = _eigenvalues(4.0)
    source[:, :, 1] = np.linspace(0.0, 1.0, 12).reshape(6, 2)
    state = _convert(_Run(eigenvalues={1: source}))
    assert np.array_equal(state.channels[0].energies_ev, source[:, :, 0].T)
