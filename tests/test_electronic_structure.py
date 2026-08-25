from __future__ import annotations

import numpy as np
import pytest

from catalysis_workbench.computation import (
    AtomicStructure,
    DOSChannel,
    DOSProjection,
    ElectronicDOS,
    ElectronicEnergyAxis,
    ElectronicStructureError,
    VolumetricGrid,
)


def _structure() -> AtomicStructure:
    return AtomicStructure(
        species=["Fe", "O"],
        elements=["Fe", "O"],
        cartesian_coordinates=[[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]],
        lattice_angstrom=np.eye(3) * 2.0,
        pbc=(True, True, True),
    )


def test_energy_axis_requires_strict_source_order_and_is_immutable() -> None:
    axis = ElectronicEnergyAxis(
        [-2.0, 0.0, 1.0],
        source_fermi_ev=0.25,
        reference_kind="source-native",
    )
    assert axis.source_fermi_ev == pytest.approx(0.25)
    assert axis.applied_shift_ev == 0.0
    assert not axis.values_ev.flags.writeable
    with pytest.raises(ElectronicStructureError, match="strictly increasing"):
        ElectronicEnergyAxis([0.0, 0.0, 1.0])
    with pytest.raises(ElectronicStructureError, match="strictly increasing"):
        ElectronicEnergyAxis([0.0, -1.0, 1.0])


def test_dos_state_preserves_physical_spin_and_projection_identity() -> None:
    structure = _structure()
    axis = ElectronicEnergyAxis([-1.0, 0.0, 1.0], source_fermi_ev=0.2)
    total = DOSProjection(key="total", kind="total")
    site = DOSProjection(
        key=f"pdos:{structure.site_keys[0]}:dxy",
        kind="site-orbital",
        site_index=0,
        site_key=structure.site_keys[0],
        element="Fe",
        orbital="dxy",
    )
    result = ElectronicDOS(
        energy=axis,
        channels=[
            DOSChannel(total, "up", [1.0, 2.0, 3.0]),
            DOSChannel(total, "down", [0.5, 1.0, 1.5]),
            DOSChannel(
                site,
                "up",
                [0.2, 0.4, 0.6],
                normalization_basis="site",
            ),
        ],
        structure=structure,
        metadata={"source": ["vasprun.xml"]},
    )
    assert [channel.spin for channel in result.channels] == ["up", "down", "up"]
    assert result.channels[2].projection.orbital == "dxy"
    assert not result.channels[0].density.flags.writeable
    metadata = result.metadata_dict()
    metadata["source"].append("changed")
    assert tuple(result.metadata["source"]) == ("vasprun.xml",)


def test_negative_mirrored_dos_and_duplicate_channel_fail_closed() -> None:
    total = DOSProjection(key="total", kind="total")
    with pytest.raises(ElectronicStructureError, match="non-negative"):
        DOSChannel(total, "down", [1.0, -1.0])
    channel = DOSChannel(total, "total", [1.0, 2.0])
    with pytest.raises(ElectronicStructureError, match="unique"):
        ElectronicDOS(
            energy=ElectronicEnergyAxis([0.0, 1.0]),
            channels=[channel, channel],
        )


def test_projection_must_match_attached_structure() -> None:
    structure = _structure()
    wrong = DOSProjection(
        key="bad",
        kind="site-orbital",
        site_index=0,
        site_key=structure.site_keys[1],
        element="Fe",
        orbital="s",
    )
    with pytest.raises(ElectronicStructureError, match="site_key"):
        ElectronicDOS(
            energy=ElectronicEnergyAxis([0.0, 1.0]),
            channels=[
                DOSChannel(
                    wrong,
                    "total",
                    [1.0, 1.0],
                    normalization_basis="site",
                )
            ],
            structure=structure,
        )


def test_channel_digest_includes_full_projection_identity() -> None:
    structure = _structure()
    projection_a = DOSProjection(
        key="shared-display-key",
        kind="site-orbital",
        site_index=0,
        site_key=structure.site_keys[0],
        element="Fe",
        orbital="dxy",
    )
    projection_b = DOSProjection(
        key="shared-display-key",
        kind="site-orbital",
        site_index=1,
        site_key=structure.site_keys[1],
        element="O",
        orbital="dxy",
    )
    channel_a = DOSChannel(
        projection_a,
        "total",
        [1.0, 2.0],
        normalization_basis="site",
    )
    channel_b = DOSChannel(
        projection_b,
        "total",
        [1.0, 2.0],
        normalization_basis="site",
    )
    assert channel_a.digest != channel_b.digest


def test_volumetric_grid_retains_physical_units_and_exact_integrals() -> None:
    structure = _structure()
    grid = VolumetricGrid(
        structure=structure,
        components={
            "total": np.array([[[1.0]], [[2.0]]]),
            "magnetization_z": np.array([[[0.25]], [[-0.25]]]),
        },
        metadata={"producer": {"name": "VASP"}},
    )
    assert grid.grid_shape == (2, 1, 1)
    assert grid.cell_volume_angstrom3 == pytest.approx(8.0)
    assert grid.voxel_volume_angstrom3 == pytest.approx(4.0)
    assert grid.component_integrals["total"] == pytest.approx(12.0)
    assert grid.component_integrals["magnetization_z"] == pytest.approx(0.0)
    assert grid.density_unit == "1/angstrom^3"
    assert not grid.components["total"].flags.writeable
    detached = grid.metadata_dict()
    detached["producer"]["name"] = "changed"
    assert grid.metadata["producer"]["name"] == "VASP"


def test_volumetric_mapping_order_does_not_change_scientific_identity() -> None:
    structure = _structure()
    total = np.array([[[1.0]], [[2.0]]])
    magnetization = np.array([[[0.25]], [[-0.25]]])
    grid_a = VolumetricGrid(
        structure=structure,
        components={"total": total, "magnetization_z": magnetization},
    )
    grid_b = VolumetricGrid(
        structure=structure,
        components={"magnetization_z": magnetization, "total": total},
    )
    assert tuple(grid_a.components) == ("magnetization_z", "total")
    assert tuple(grid_b.components) == ("magnetization_z", "total")
    assert grid_a == grid_b
    assert grid_a.digest == grid_b.digest


def test_volumetric_grid_shape_and_periodicity_fail_closed() -> None:
    structure = _structure()
    with pytest.raises(ElectronicStructureError, match="identical"):
        VolumetricGrid(
            structure=structure,
            components={
                "total": np.zeros((2, 1, 1)),
                "magnetization_z": np.zeros((1, 1, 1)),
            },
        )
    nonperiodic = AtomicStructure(
        species=["H"],
        elements=["H"],
        cartesian_coordinates=[[0.0, 0.0, 0.0]],
    )
    with pytest.raises(ElectronicStructureError, match="fully periodic"):
        VolumetricGrid(
            structure=nonperiodic,
            components={"total": np.ones((1, 1, 1))},
        )


def test_digests_are_deterministic_for_same_scientific_state() -> None:
    axis_a = ElectronicEnergyAxis([-1.0, 0.0, 1.0], source_fermi_ev=0.0)
    axis_b = ElectronicEnergyAxis([-1.0, 0.0, 1.0], source_fermi_ev=0.0)
    assert axis_a.digest == axis_b.digest
    total = DOSProjection(key="total", kind="total")
    dos_a = ElectronicDOS(
        energy=axis_a,
        channels=[DOSChannel(total, "total", [1.0, 2.0, 1.0])],
        metadata={"label": "A"},
    )
    dos_b = ElectronicDOS(
        energy=axis_b,
        channels=[DOSChannel(total, "total", [1.0, 2.0, 1.0])],
        metadata={"label": "B"},
    )
    assert dos_a.digest == dos_b.digest
