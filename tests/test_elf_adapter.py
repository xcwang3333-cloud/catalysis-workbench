from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from catalysis_workbench.io.electronic_structure import ElectronicStructureIOError
from catalysis_workbench.io.elf import _convert_elfcar_result


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


class _Lattice:
    def __init__(self) -> None:
        self.matrix = np.diag([2.0, 2.0, 2.0])


class _Structure:
    is_ordered = True

    def __init__(self) -> None:
        self.lattice = _Lattice()
        self._sites = (_Site(np.zeros(3)),)

    def __iter__(self):
        return iter(self._sites)


class _Parsed:
    def __init__(self, data: dict[str, np.ndarray]) -> None:
        self.structure = _Structure()
        self.data = data


def _convert(
    data: dict[str, np.ndarray],
    *,
    spin: str,
    backend_version: str = "2026.8.20",
):
    return _convert_elfcar_result(
        _Parsed(data),
        path="ELFCAR",
        spin=spin,
        source_id="calc-A",
        registration_id="frame-A",
        backend_version=backend_version,
    )


def test_unpolarized_elf_retains_exact_dimensionless_values() -> None:
    values = np.arange(8.0).reshape(2, 2, 2) / 10.0
    field = _convert({"total": values}, spin="total")

    assert field.field_kind == "elf"
    assert field.value_unit == "dimensionless"
    assert field.registration_id == "frame-A"
    assert field.source_type == "ELFCAR"
    assert field.source_key == "elfcar:total"
    assert np.array_equal(field.values, values)
    assert field.metadata["selected_backend_key"] == "total"
    assert field.metadata["channel_semantics"] == "unpolarized-total"
    assert field.metadata["pymatgen_core_version"] == "2026.8.20"


def test_current_direct_spin_channels_require_explicit_physical_spin() -> None:
    up = np.full((2, 2, 2), 0.8)
    down = np.full((2, 2, 2), 0.3)
    data = {"spin_up": up, "spin_down": down}

    up_field = _convert(data, spin="up")
    down_field = _convert(data, spin="down")
    assert up_field.field_kind == "elf-spin-up"
    assert down_field.field_kind == "elf-spin-down"
    assert np.array_equal(up_field.values, up)
    assert np.array_equal(down_field.values, down)
    assert up_field.metadata["selected_backend_key"] == "spin_up"
    assert down_field.metadata["selected_backend_key"] == "spin_down"
    assert up_field.source_digest == down_field.source_digest
    assert up_field.digest != down_field.digest

    with pytest.raises(ElectronicStructureIOError, match="explicit spin"):
        _convert(data, spin="total")


def test_legacy_total_diff_is_version_guarded_as_direct_spin_not_chgcar_semantics() -> None:
    first_spin = np.full((2, 2, 2), 0.9)
    second_spin = np.full((2, 2, 2), 0.2)
    legacy = {"total": first_spin, "diff": second_spin}

    up = _convert(legacy, spin="up", backend_version="2026.7.16")
    down = _convert(legacy, spin="down", backend_version="2026.7.16")
    assert np.array_equal(up.values, first_spin)
    assert np.array_equal(down.values, second_spin)
    assert up.metadata["selected_backend_key"] == "total"
    assert down.metadata["selected_backend_key"] == "diff"
    assert up.metadata["channel_semantics"] == (
        "legacy-direct-spin-channels-version-guarded"
    )

    with pytest.raises(ElectronicStructureIOError, match="legacy ELFCAR total/diff"):
        _convert(legacy, spin="up", backend_version="2026.8.13")


def test_unpolarized_and_polarized_selection_fail_closed() -> None:
    total = {"total": np.ones((2, 2, 2))}
    with pytest.raises(ElectronicStructureIOError, match="unpolarized"):
        _convert(total, spin="up")

    with pytest.raises(ElectronicStructureIOError, match="spin must"):
        _convert(total, spin="magnetization")


def test_unexpected_nonfinite_and_shape_mismatched_elf_state_fails() -> None:
    with pytest.raises(ElectronicStructureIOError, match="unsupported ELFCAR"):
        _convert({"mystery": np.ones((2, 2, 2))}, spin="total")

    nonfinite = np.ones((2, 2, 2))
    nonfinite[0, 0, 0] = np.nan
    with pytest.raises(ElectronicStructureIOError, match="non-finite"):
        _convert({"total": nonfinite}, spin="total")

    with pytest.raises(ElectronicStructureIOError, match="same exact grid shape"):
        _convert(
            {
                "spin_up": np.ones((2, 2, 2)),
                "spin_down": np.ones((2, 2, 3)),
            },
            spin="up",
        )


def test_source_digest_tracks_all_channels_and_backend_version() -> None:
    first = _convert(
        {
            "spin_up": np.full((2, 2, 2), 0.8),
            "spin_down": np.full((2, 2, 2), 0.3),
        },
        spin="up",
    )
    changed_other_channel = _convert(
        {
            "spin_up": np.full((2, 2, 2), 0.8),
            "spin_down": np.full((2, 2, 2), 0.4),
        },
        spin="up",
    )
    changed_version = _convert(
        {
            "spin_up": np.full((2, 2, 2), 0.8),
            "spin_down": np.full((2, 2, 2), 0.3),
        },
        spin="up",
        backend_version="2026.8.21",
    )

    assert first.source_digest != changed_other_channel.source_digest
    assert first.source_digest != changed_version.source_digest
