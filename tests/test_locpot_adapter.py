from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from catalysis_workbench.io.electronic_structure import ElectronicStructureIOError
from catalysis_workbench.io.locpot import _convert_locpot_result


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
        self.matrix = np.array(
            [
                [2.0, 0.0, 0.0],
                [0.0, 3.0, 0.0],
                [1.0, 0.0, 4.0],
            ]
        )


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


def _convert(data: dict[str, np.ndarray], *, calculation_id: str | None = "calc-A"):
    return _convert_locpot_result(
        _Parsed(data),
        path="LOCPOT",
        source_id="source-A",
        calculation_id=calculation_id,
        backend_version="2026.8.20",
    )


def test_locpot_preserves_exact_eV_values_without_volume_normalization() -> None:
    values = np.arange(24.0).reshape(2, 3, 4)
    field = _convert({"total": values})

    assert field.field_kind == "local-potential"
    assert field.value_unit == "eV"
    assert field.source_type == "LOCPOT"
    assert field.source_key == "locpot:total"
    assert np.array_equal(field.values, values)
    assert field.metadata["selected_backend_key"] == "total"
    assert field.metadata["volume_normalized"] is False
    assert field.metadata["calculation_id"] == "calc-A"
    assert field.metadata["pymatgen_core_version"] == "2026.8.20"
    assert field.values[1, 2, 3] == 23.0


def test_locpot_rejects_multiple_empty_nonfinite_and_non3d_components() -> None:
    with pytest.raises(ElectronicStructureIOError, match="exactly one"):
        _convert(
            {
                "total": np.ones((2, 2, 2)),
                "diff": np.ones((2, 2, 2)),
            }
        )

    with pytest.raises(ElectronicStructureIOError, match="exactly one"):
        _convert({})

    nonfinite = np.ones((2, 2, 2))
    nonfinite[0, 0, 0] = np.nan
    with pytest.raises(ElectronicStructureIOError, match="non-finite"):
        _convert({"total": nonfinite})

    with pytest.raises(ElectronicStructureIOError, match="3-D"):
        _convert({"total": np.ones((2, 2))})


def test_blank_component_and_calculation_identity_fail_closed() -> None:
    with pytest.raises(ElectronicStructureIOError, match="blank data key"):
        _convert({"   ": np.ones((2, 2, 2))})

    with pytest.raises(ElectronicStructureIOError, match="calculation_id"):
        _convert({"total": np.ones((2, 2, 2))}, calculation_id="   ")


def test_calculation_identity_is_optional_until_work_function_binding() -> None:
    field = _convert({"total": np.ones((2, 2, 2))}, calculation_id=None)
    assert "calculation_id" not in field.metadata


def test_source_digest_tracks_exact_values_and_backend_version() -> None:
    first = _convert_locpot_result(
        _Parsed({"total": np.ones((2, 2, 2))}),
        path="LOCPOT",
        source_id="source-A",
        calculation_id="calc-A",
        backend_version="2026.8.20",
    )
    changed_values = _convert_locpot_result(
        _Parsed({"total": np.full((2, 2, 2), 2.0)}),
        path="LOCPOT",
        source_id="source-A",
        calculation_id="calc-A",
        backend_version="2026.8.20",
    )
    changed_version = _convert_locpot_result(
        _Parsed({"total": np.ones((2, 2, 2))}),
        path="LOCPOT",
        source_id="source-A",
        calculation_id="calc-A",
        backend_version="2026.8.21",
    )
    assert first.source_digest != changed_values.source_digest
    assert first.source_digest != changed_version.source_digest
