from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np

from catalysis_workbench.computation import AtomicStructure
from catalysis_workbench.io import (
    StructureIOError,
    read_cif_structure,
    read_contcar,
    read_poscar,
    read_xyz_structure,
)

POSCAR = """SiO test
1.0
5.0 0.0 0.0
0.0 5.0 0.0
0.0 0.0 5.0
Si O
1 1
Direct
0.0 0.0 0.0
0.5 0.5 0.5
"""

CONTCAR = """SiO test
1.0
5.0 0.0 0.0
0.0 5.0 0.0
0.0 0.0 5.0
Si O
1 1
Cartesian
0.0 0.0 0.0
2.5 2.5 2.5
"""

CIF_ONE = """data_one
_symmetry_space_group_name_H-M 'P 1'
_symmetry_Int_Tables_number 1
_cell_length_a 5
_cell_length_b 5
_cell_length_c 5
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
loop_
_symmetry_equiv_pos_as_xyz
'x,y,z'
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
_atom_site_occupancy
Si1 Si 0 0 0 1
O1 O 0.5 0.5 0.5 1
"""

CIF_TWO = CIF_ONE + """
data_two
_symmetry_space_group_name_H-M 'P 1'
_symmetry_Int_Tables_number 1
_cell_length_a 4
_cell_length_b 4
_cell_length_c 4
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
loop_
_symmetry_equiv_pos_as_xyz
'x,y,z'
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
_atom_site_occupancy
C1 C 0 0 0 1
"""

CIF_DISORDERED = """data_disordered
_symmetry_space_group_name_H-M 'P 1'
_symmetry_Int_Tables_number 1
_cell_length_a 5
_cell_length_b 5
_cell_length_c 5
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
loop_
_symmetry_equiv_pos_as_xyz
'x,y,z'
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
_atom_site_occupancy
M1 Si 0 0 0 0.5
M1 Ge 0 0 0 0.5
"""

XYZ_MULTI = """2
frame one
H 0.0 0.0 0.0
H 0.74 0.0 0.0
2
frame two
He 0.0 0.0 0.0
He 1.0 0.0 0.0
"""


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        poscar_path = root / "POSCAR"
        contcar_path = root / "CONTCAR"
        cif_path = root / "one.cif"
        cif_multi_path = root / "multi.cif"
        cif_disordered_path = root / "disordered.cif"
        xyz_path = root / "multi.xyz"
        _write(poscar_path, POSCAR)
        _write(contcar_path, CONTCAR)
        _write(cif_path, CIF_ONE)
        _write(cif_multi_path, CIF_TWO)
        _write(cif_disordered_path, CIF_DISORDERED)
        _write(xyz_path, XYZ_MULTI)

        poscar = read_poscar(poscar_path, source_id="poscar-smoke")
        assert isinstance(poscar, AtomicStructure)
        assert poscar.elements == ("Si", "O")
        assert poscar.pbc == (True, True, True)
        np.testing.assert_allclose(poscar.lattice_angstrom, np.eye(3) * 5.0)
        np.testing.assert_allclose(poscar.cartesian_coordinates[1], [2.5, 2.5, 2.5])

        contcar = read_contcar(contcar_path)
        assert contcar.elements == ("Si", "O")
        np.testing.assert_allclose(contcar.cartesian_coordinates, poscar.cartesian_coordinates)

        cif = read_cif_structure(cif_path)
        assert cif.elements == ("Si", "O")
        assert cif.pbc == (True, True, True)
        np.testing.assert_allclose(cif.lattice_angstrom, np.eye(3) * 5.0, atol=1e-12)

        try:
            read_cif_structure(cif_multi_path)
        except StructureIOError as exc:
            assert "explicit index" in str(exc)
        else:
            raise AssertionError("multi-structure CIF must require an explicit index")
        second_cif = read_cif_structure(cif_multi_path, index=1)
        assert second_cif.elements == ("C",)

        try:
            read_cif_structure(cif_disordered_path)
        except StructureIOError as exc:
            assert "disordered" in str(exc)
        else:
            raise AssertionError("disordered CIF must fail closed")

        try:
            read_xyz_structure(xyz_path)
        except StructureIOError as exc:
            assert "explicit index" in str(exc)
        else:
            raise AssertionError("multi-frame XYZ must require an explicit index")
        xyz0 = read_xyz_structure(xyz_path, index=0)
        xyz1 = read_xyz_structure(xyz_path, index=1)
        assert xyz0.elements == ("H", "H")
        assert xyz1.elements == ("He", "He")
        assert xyz0.lattice_angstrom is None
        assert xyz0.pbc == (False, False, False)
        np.testing.assert_allclose(xyz0.cartesian_coordinates[1], [0.74, 0.0, 0.0])


if __name__ == "__main__":
    main()
