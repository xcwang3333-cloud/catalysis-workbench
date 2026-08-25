from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import numpy as np
import pytest

from catalysis_workbench.computation import AtomicStructure
from catalysis_workbench.computation.bader import (
    BaderChargeResult,
    BaderChargeSiteResult,
    BaderError,
    BaderResult,
    BaderSiteResult,
    account_bader_charges,
    bader_charge_frame,
    bader_result_frame,
)
from catalysis_workbench.io.bader import BaderIOError, read_bader_acf


STANDARD_ACF = """#         X           Y           Z       CHARGE      MIN DIST   ATOMIC VOL
--------------------------------------------------------------------------------
    1    0.000000    0.000000    0.000000    5.500000     0.750000    12.000000
    2    1.000000    2.000000    3.000000    7.200000     0.800000    14.000000
--------------------------------------------------------------------------------
VACUUM CHARGE:               0.1000
VACUUM VOLUME:               1.2500
NUMBER OF ELECTRONS:        12.8000
"""


def _write(tmp_path: Path, text: str = STANDARD_ACF) -> Path:
    path = tmp_path / "ACF.dat"
    path.write_text(text, encoding="utf-8")
    return path


def _structure(*, swapped: bool = False) -> AtomicStructure:
    coordinates = [(0.0, 0.0, 0.0), (1.0, 2.0, 3.0)]
    if swapped:
        coordinates = coordinates[::-1]
    return AtomicStructure(
        species=("C", "O"),
        elements=("C", "O"),
        cartesian_coordinates=coordinates,
        site_keys=("carbon-site", "oxygen-site"),
    )


def test_read_standard_acf_retains_raw_rows_and_footer(tmp_path: Path) -> None:
    result = read_bader_acf(_write(tmp_path), source_id="hand-fixture")

    assert isinstance(result, BaderResult)
    assert not result.mapped
    assert result.source_format == "ACF.dat"
    assert result.source_id == "hand-fixture"
    assert [site.source_atom_index for site in result.sites] == [1, 2]
    np.testing.assert_allclose(result.sites[0].cartesian_position_angstrom, [0.0, 0.0, 0.0])
    assert result.sites[0].bader_electrons == pytest.approx(5.5)
    assert result.sites[0].min_distance_angstrom == pytest.approx(0.75)
    assert result.sites[0].atomic_volume_angstrom3 == pytest.approx(12.0)
    assert result.vacuum_charge_electrons == pytest.approx(0.1)
    assert result.vacuum_volume_angstrom3 == pytest.approx(1.25)
    assert result.number_of_electrons == pytest.approx(12.8)


def test_acf_footer_fields_are_optional_but_not_invented(tmp_path: Path) -> None:
    text = """# X Y Z CHARGE MIN DIST ATOMIC VOL
---
1 0 0 0 4.0 0.5 10.0
---
"""
    result = read_bader_acf(_write(tmp_path, text))
    assert result.vacuum_charge_electrons is None
    assert result.vacuum_volume_angstrom3 is None
    assert result.number_of_electrons is None


def test_acf_fortran_d_exponent_is_parsed(tmp_path: Path) -> None:
    text = """# X Y Z CHARGE MIN DIST ATOMIC VOL
---
1 0 0 0 4.0D+00 5.0D-01 1.0D+01
---
NUMBER OF ELECTRONS: 4.0D+00
"""
    result = read_bader_acf(_write(tmp_path, text))
    assert result.sites[0].bader_electrons == pytest.approx(4.0)
    assert result.number_of_electrons == pytest.approx(4.0)


@pytest.mark.parametrize(
    "text",
    [
        "# X Y Z CHARGE MIN DIST\n1 0 0 0 4 0.5 10\n",
        "# X Y Z CHARGE MIN DIST ATOMIC VOL\n1 0 0 0 4 0.5\n",
        (
            "# X Y Z CHARGE MIN DIST ATOMIC VOL\n"
            "1 0 0 0 4 0.5 10\nVACUUM CHARGE: 0\nVACUUM CHARGE: 0\n"
        ),
        (
            "# X Y Z CHARGE MIN DIST ATOMIC VOL\n"
            "1 0 0 0 4 0.5 10\nVACUUM CHARGE: 0\n2 1 1 1 4 0.5 10\n"
        ),
    ],
)
def test_malformed_acf_state_fails_closed(tmp_path: Path, text: str) -> None:
    with pytest.raises(BaderIOError):
        read_bader_acf(_write(tmp_path, text))


@pytest.mark.parametrize(
    "rows",
    [
        "2 0 0 0 4 0.5 10\n",
        "1 0 0 0 4 0.5 10\n1 1 1 1 4 0.5 10\n",
        "1 0 0 0 4 0.5 10\n3 1 1 1 4 0.5 10\n",
        "0 0 0 0 4 0.5 10\n",
    ],
)
def test_source_atom_indices_must_be_ordered_standard_sequence(
    tmp_path: Path,
    rows: str,
) -> None:
    text = "# X Y Z CHARGE MIN DIST ATOMIC VOL\n---\n" + rows
    with pytest.raises(BaderIOError):
        read_bader_acf(_write(tmp_path, text))


@pytest.mark.parametrize(
    ("charge", "min_dist", "volume"),
    [
        (-0.1, 0.5, 10.0),
        (4.0, -0.1, 10.0),
        (4.0, 0.5, 0.0),
        (4.0, 0.5, -1.0),
    ],
)
def test_raw_physical_constraints_fail_closed(
    tmp_path: Path,
    charge: float,
    min_dist: float,
    volume: float,
) -> None:
    text = (
        "# X Y Z CHARGE MIN DIST ATOMIC VOL\n---\n"
        f"1 0 0 0 {charge} {min_dist} {volume}\n"
    )
    with pytest.raises(BaderIOError):
        read_bader_acf(_write(tmp_path, text))


def test_raw_result_is_immutable_deterministic_and_detached(tmp_path: Path) -> None:
    path = _write(tmp_path)
    first = read_bader_acf(path, source_id="same")
    second = read_bader_acf(path, source_id="same")

    assert first == second
    assert first.digest == second.digest
    assert first.sites[0].digest == second.sites[0].digest
    assert not first.sites[0].cartesian_position_angstrom.flags.writeable
    with pytest.raises(ValueError):
        first.sites[0].cartesian_position_angstrom[0] = 99.0
    with pytest.raises(FrozenInstanceError):
        first.number_of_electrons = 99.0  # type: ignore[misc]


def test_descriptive_source_path_and_id_do_not_change_scientific_digest(
    tmp_path: Path,
) -> None:
    first_path = tmp_path / "first.dat"
    second_path = tmp_path / "second.dat"
    first_path.write_text(STANDARD_ACF, encoding="utf-8")
    second_path.write_text(STANDARD_ACF, encoding="utf-8")

    first = read_bader_acf(first_path, source_id="first-label")
    second = read_bader_acf(second_path, source_id="second-label")
    assert first.digest == second.digest
    assert first != second


def test_structure_mapping_is_direct_ordered_and_tolerance_bearing(tmp_path: Path) -> None:
    structure = _structure()
    result = read_bader_acf(
        _write(tmp_path),
        structure=structure,
        position_tolerance_angstrom=1e-8,
    )

    assert result.mapped
    assert result.structure_digest == structure.digest
    assert result.position_tolerance_angstrom == pytest.approx(1e-8)
    assert [site.site_index for site in result.sites] == [0, 1]
    assert [site.site_key for site in result.sites] == ["carbon-site", "oxygen-site"]
    assert [site.source_atom_index for site in result.sites] == [1, 2]


def test_structure_mapping_requires_explicit_tolerance(tmp_path: Path) -> None:
    with pytest.raises(BaderIOError, match="position_tolerance_angstrom is required"):
        read_bader_acf(_write(tmp_path), structure=_structure())


def test_tolerance_without_structure_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(BaderIOError, match="has no meaning"):
        read_bader_acf(_write(tmp_path), position_tolerance_angstrom=1e-4)


def test_structure_count_and_direct_position_mismatch_fail_closed(tmp_path: Path) -> None:
    one_site = AtomicStructure(
        species=("C",),
        elements=("C",),
        cartesian_coordinates=[(0.0, 0.0, 0.0)],
    )
    with pytest.raises(BaderIOError, match="atom count"):
        read_bader_acf(
            _write(tmp_path),
            structure=one_site,
            position_tolerance_angstrom=1e-6,
        )

    with pytest.raises(BaderIOError, match="direct site order"):
        read_bader_acf(
            _write(tmp_path),
            structure=_structure(swapped=True),
            position_tolerance_angstrom=1e-6,
        )


def test_structure_mapping_respects_caller_tolerance(tmp_path: Path) -> None:
    structure = AtomicStructure(
        species=("C", "O"),
        elements=("C", "O"),
        cartesian_coordinates=[(1e-5, 0.0, 0.0), (1.0, 2.0, 3.0)],
    )
    result = read_bader_acf(
        _write(tmp_path),
        structure=structure,
        position_tolerance_angstrom=2e-5,
    )
    assert result.mapped

    with pytest.raises(BaderIOError):
        read_bader_acf(
            _write(tmp_path),
            structure=structure,
            position_tolerance_angstrom=5e-6,
        )


def test_charge_accounting_uses_explicit_opposite_sign_conventions(tmp_path: Path) -> None:
    raw = read_bader_acf(_write(tmp_path), source_id="acf")
    result = account_bader_charges(
        raw,
        (6.0, 7.0),
        reference_id="manual-pseudopotential-valence",
    )

    assert isinstance(result, BaderChargeResult)
    assert result.source_bader_result_digest == raw.digest
    assert result.reference_id == "manual-pseudopotential-valence"
    assert result.sites[0].bader_electrons == pytest.approx(5.5)
    assert result.sites[0].reference_electrons == pytest.approx(6.0)
    assert result.sites[0].electron_transfer == pytest.approx(-0.5)
    assert result.sites[0].partial_charge == pytest.approx(0.5)
    assert result.sites[1].electron_transfer == pytest.approx(0.2)
    assert result.sites[1].partial_charge == pytest.approx(-0.2)
    for site in result.sites:
        assert site.partial_charge == pytest.approx(-site.electron_transfer)


@pytest.mark.parametrize(
    ("references", "reference_id"),
    [
        ((6.0,), "manual"),
        ((6.0, -1.0), "manual"),
        ((6.0, float("nan")), "manual"),
        ((6.0, 7.0), " "),
    ],
)
def test_invalid_reference_accounting_fails_closed(
    tmp_path: Path,
    references: tuple[float, ...],
    reference_id: str,
) -> None:
    raw = read_bader_acf(_write(tmp_path))
    with pytest.raises((BaderError, TypeError)):
        account_bader_charges(raw, references, reference_id=reference_id)


def test_charge_result_retains_mapped_site_and_reference_provenance(tmp_path: Path) -> None:
    raw = read_bader_acf(
        _write(tmp_path),
        structure=_structure(),
        position_tolerance_angstrom=1e-8,
    )
    first = account_bader_charges(raw, (6.0, 7.0), reference_id="manual")
    second = account_bader_charges(raw, (6.0, 7.0), reference_id="manual")

    assert first == second
    assert first.digest == second.digest
    assert first.sites[0].site_index == 0
    assert first.sites[0].site_key == "carbon-site"
    assert first.sites[0].source_site_digest == raw.sites[0].digest
    assert not first.sites[0].cartesian_position_angstrom.flags.writeable


def test_invalid_charge_site_reconstruction_fails() -> None:
    with pytest.raises(BaderError, match="electron_transfer"):
        BaderChargeSiteResult(
            source_atom_index=1,
            cartesian_position_angstrom=(0.0, 0.0, 0.0),
            bader_electrons=5.5,
            reference_electrons=6.0,
            electron_transfer=0.5,
            partial_charge=0.5,
            source_site_digest="source-site",
        )


def test_raw_and_charge_frames_are_detached_and_non_ambiguous(tmp_path: Path) -> None:
    raw = read_bader_acf(_write(tmp_path))
    charge = account_bader_charges(raw, (6.0, 7.0), reference_id="manual")

    raw_frame = bader_result_frame(raw)
    charge_frame = bader_charge_frame(charge)
    assert "charge" not in raw_frame.columns
    assert "charge" not in charge_frame.columns
    assert {"bader_electrons", "electron_transfer", "partial_charge"}.issubset(
        charge_frame.columns
    )
    raw_frame.loc[0, "bader_electrons"] = 999.0
    charge_frame.loc[0, "partial_charge"] = 999.0
    assert raw.sites[0].bader_electrons == pytest.approx(5.5)
    assert charge.sites[0].partial_charge == pytest.approx(0.5)


def test_raw_result_reconstruction_rejects_nonstandard_index_order() -> None:
    site = BaderSiteResult(
        source_atom_index=2,
        cartesian_position_angstrom=(0.0, 0.0, 0.0),
        bader_electrons=4.0,
        min_distance_angstrom=0.5,
        atomic_volume_angstrom3=10.0,
    )
    with pytest.raises(BaderError, match="ordered standard sequence"):
        BaderResult(sites=(site,))
