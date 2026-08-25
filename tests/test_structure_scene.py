from __future__ import annotations

import numpy as np
import pytest

from catalysis_workbench.computation import (
    AtomicStructure,
    PeriodicImage,
    SiteImage,
    StructureAtomStyle,
    StructureBondSpec,
    StructureBondStyle,
    StructureCameraSpec,
    StructureSceneError,
    build_structure_scene,
    default_element_color,
    default_element_radius_angstrom,
)


def _periodic() -> AtomicStructure:
    return AtomicStructure(
        species=("C", "O"),
        elements=("C", "O"),
        cartesian_coordinates=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0)),
        lattice_angstrom=((3.0, 0.0, 0.0), (0.5, 2.5, 0.0), (0.0, 0.0, 4.0)),
        pbc=(True, True, True),
        site_keys=("c", "o"),
        metadata={"nested": {"source": "fixture"}},
    )


def test_default_visual_registry_is_deterministic_and_has_fallbacks() -> None:
    assert default_element_color("O") == default_element_color("O")
    assert default_element_color("Xx") == "#9A9A9A"
    assert default_element_radius_angstrom("C") == pytest.approx(0.40)
    assert default_element_radius_angstrom("Xx") == pytest.approx(0.42)


def test_scene_preserves_exact_sites_periodic_images_styles_and_bonds() -> None:
    structure = _periodic()
    oxygen_image = SiteImage("o", PeriodicImage(0, 1, 0))
    custom = StructureAtomStyle("#123456", 0.7, alpha=0.8)
    scene = build_structure_scene(
        structure,
        atom_images=(SiteImage("c"), oxygen_image),
        bonds=(
            StructureBondSpec(
                SiteImage("c"),
                oxygen_image,
                StructureBondStyle("#777777", linewidth=2.0),
            ),
        ),
        site_styles={"o": custom},
        labels={"o": "O*"},
        camera=StructureCameraSpec(projection="orthographic", elevation_degrees=25.0),
        metadata={"panel": {"name": "a"}},
    )

    assert scene.structure_digest == structure.digest
    assert [atom.site for atom in scene.atoms] == [SiteImage("c"), oxygen_image]
    np.testing.assert_allclose(scene.atoms[0].position_angstrom, [0.0, 0.0, 0.0])
    np.testing.assert_allclose(scene.atoms[1].position_angstrom, [1.5, 2.5, 0.0])
    assert scene.atoms[1].style == custom
    assert scene.atoms[1].label == "O*"
    assert scene.atoms[0].style.color == default_element_color("C")
    assert len(scene.bonds) == 1
    np.testing.assert_allclose(scene.bonds[0].first_position_angstrom, [0.0, 0.0, 0.0])
    np.testing.assert_allclose(scene.bonds[0].second_position_angstrom, [1.5, 2.5, 0.0])
    assert len(scene.cell_edges_angstrom) == 12
    assert scene.atoms[0].position_angstrom.flags.writeable is False
    assert scene.cell_edges_angstrom[0][0].flags.writeable is False
    with pytest.raises(TypeError):
        scene.metadata["new"] = 1  # type: ignore[index]


def test_triclinic_cell_edges_use_exact_lattice_vertices() -> None:
    scene = build_structure_scene(_periodic())
    endpoints = {
        tuple(np.round(point, 12))
        for edge in scene.cell_edges_angstrom
        for point in edge
    }
    expected = {
        tuple(np.asarray(bits, dtype=float) @ np.asarray(_periodic().lattice_angstrom))
        for bits in (
            (0, 0, 0),
            (0, 0, 1),
            (0, 1, 0),
            (0, 1, 1),
            (1, 0, 0),
            (1, 0, 1),
            (1, 1, 0),
            (1, 1, 1),
        )
    }
    assert endpoints == expected


def test_scene_does_not_add_periodic_images_or_bonds_implicitly() -> None:
    scene = build_structure_scene(_periodic())
    assert [atom.site.image for atom in scene.atoms] == [PeriodicImage(), PeriodicImage()]
    assert scene.bonds == ()


def test_invalid_visual_references_fail_closed() -> None:
    structure = _periodic()
    with pytest.raises(StructureSceneError, match="unknown site key"):
        build_structure_scene(structure, atom_images=(SiteImage("missing"),))
    with pytest.raises(StructureSceneError, match="explicitly present"):
        build_structure_scene(
            structure,
            atom_images=(SiteImage("c"),),
            bonds=(StructureBondSpec(SiteImage("c"), SiteImage("o")),),
        )


def test_style_overrides_do_not_mutate_source_structure() -> None:
    structure = _periodic()
    before = np.array(structure.cartesian_coordinates, copy=True)
    scene = build_structure_scene(
        structure,
        site_styles={"c": StructureAtomStyle("#FFFFFF", 1.1)},
    )
    np.testing.assert_array_equal(structure.cartesian_coordinates, before)
    assert scene.atoms[0].style.radius_angstrom == pytest.approx(1.1)


def test_static_renderer_consumes_scene_without_rebuilding_geometry() -> None:
    from catalysis_workbench.visualization import plot_structure

    scene = build_structure_scene(
        _periodic(),
        bonds=(StructureBondSpec(SiteImage("c"), SiteImage("o")),),
    )
    before = [np.array(atom.position_angstrom, copy=True) for atom in scene.atoms]
    figure, ax = plot_structure(scene)
    assert ax.name == "3d"
    assert len(ax.collections) == len(scene.atoms)
    assert len(ax.lines) == len(scene.cell_edges_angstrom) + len(scene.bonds)
    for atom, expected in zip(scene.atoms, before, strict=True):
        np.testing.assert_array_equal(atom.position_angstrom, expected)
    figure.canvas.draw()
