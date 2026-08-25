"""Lazy pymatgen-core adapters for reviewed atomistic structure formats."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from catalysis_workbench.computation import AtomicStructure, StructureError


class StructureIOError(ValueError):
    """Raised when a structure file cannot satisfy the reviewed adapter contract."""


def _backend_import_error(exc: ImportError) -> StructureIOError:
    return StructureIOError(
        "structure adapters require the optional dependency; install "
        "catalysis-workbench[structure]"
    )


def _source_metadata(
    *,
    source_format: str,
    path: str | Path,
    source_id: str | None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "structure_format": source_format,
        "structure_backend": "pymatgen-core",
        "source_path": str(Path(path)),
    }
    if source_id is not None:
        text = str(source_id).strip()
        if not text:
            raise StructureIOError("source_id must not be blank when supplied")
        metadata["source_id"] = text
    return metadata


def _element_symbol(specie: Any) -> str:
    element = getattr(specie, "element", specie)
    symbol = getattr(element, "symbol", None)
    if symbol is None:
        raise StructureIOError(
            f"cannot determine canonical element symbol from ordered species {specie!s}"
        )
    text = str(symbol).strip()
    if not text:
        raise StructureIOError("backend returned a blank canonical element symbol")
    return text


def _convert_site_collection(
    collection: Any,
    *,
    periodic: bool,
    source_format: str,
    path: str | Path,
    source_id: str | None,
) -> AtomicStructure:
    if not bool(getattr(collection, "is_ordered", False)):
        raise StructureIOError(
            "disordered or partial-occupancy structures are not supported in this block"
        )

    species: list[str] = []
    elements: list[str] = []
    coordinates: list[Sequence[float]] = []
    labels: list[str | None] = []
    for site in collection:
        if not bool(getattr(site, "is_ordered", False)):
            raise StructureIOError(
                "disordered or partial-occupancy sites are not supported in this block"
            )
        try:
            specie = site.specie
        except (AttributeError, ValueError) as exc:
            raise StructureIOError("backend site does not expose one ordered species") from exc
        species.append(str(specie).strip())
        elements.append(_element_symbol(specie))
        coordinates.append(np.asarray(site.coords, dtype=np.float64))
        label = getattr(site, "label", None)
        if label is None:
            labels.append(None)
        else:
            text = str(label).strip()
            labels.append(text or None)

    lattice = None
    pbc = (False, False, False)
    if periodic:
        try:
            lattice = np.asarray(collection.lattice.matrix, dtype=np.float64)
        except (AttributeError, TypeError, ValueError) as exc:
            raise StructureIOError(
                "periodic backend structure does not expose a valid lattice matrix"
            ) from exc
        pbc = (True, True, True)

    metadata = _source_metadata(
        source_format=source_format,
        path=path,
        source_id=source_id,
    )
    try:
        return AtomicStructure(
            species=species,
            elements=elements,
            cartesian_coordinates=coordinates,
            lattice_angstrom=lattice,
            pbc=pbc,
            site_labels=labels,
            metadata=metadata,
        )
    except (StructureError, TypeError, ValueError) as exc:
        raise StructureIOError(
            f"parsed {source_format} structure violates AtomicStructure contract"
        ) from exc


def _select_record(records: Sequence[Any], *, index: int | None, format_name: str) -> Any:
    count = len(records)
    if count == 0:
        raise StructureIOError(f"{format_name} parser returned no structures/frames")
    if index is None:
        if count != 1:
            raise StructureIOError(
                f"{format_name} contains {count} structures/frames; supply an explicit index"
            )
        return records[0]
    if isinstance(index, bool) or not isinstance(index, int):
        raise TypeError("index must be an integer or None")
    if index < 0 or index >= count:
        raise StructureIOError(
            f"{format_name} index {index} is outside the available range 0..{count - 1}"
        )
    return records[index]


def _read_vasp_structure(
    path: str | Path,
    *,
    source_format: str,
    source_id: str | None,
) -> AtomicStructure:
    try:
        from pymatgen.io.vasp.inputs import Poscar
    except ImportError as exc:
        raise _backend_import_error(exc) from exc

    try:
        parsed = Poscar.from_file(
            path,
            check_for_potcar=False,
            read_velocities=False,
        )
    except Exception as exc:
        raise StructureIOError(f"failed to parse {source_format} with pymatgen-core") from exc
    return _convert_site_collection(
        parsed.structure,
        periodic=True,
        source_format=source_format,
        path=path,
        source_id=source_id,
    )


def read_poscar(
    path: str | Path,
    *,
    source_id: str | None = None,
) -> AtomicStructure:
    """Parse a POSCAR into CatalysisWorkbench-owned immutable structure state."""
    return _read_vasp_structure(path, source_format="POSCAR", source_id=source_id)


def read_contcar(
    path: str | Path,
    *,
    source_id: str | None = None,
) -> AtomicStructure:
    """Parse a CONTCAR into CatalysisWorkbench-owned immutable structure state."""
    return _read_vasp_structure(path, source_format="CONTCAR", source_id=source_id)


def read_cif_structure(
    path: str | Path,
    *,
    index: int | None = None,
    source_id: str | None = None,
) -> AtomicStructure:
    """Parse one explicit CIF structure without primitive/conventional-cell conversion."""
    try:
        from pymatgen.io.cif import CifParser
    except ImportError as exc:
        raise _backend_import_error(exc) from exc

    try:
        parser = CifParser(path)
        records = parser.parse_structures(primitive=False)
    except Exception as exc:
        raise StructureIOError("failed to parse CIF with pymatgen-core") from exc
    selected = _select_record(records, index=index, format_name="CIF")
    return _convert_site_collection(
        selected,
        periodic=True,
        source_format="CIF",
        path=path,
        source_id=source_id,
    )


def read_xyz_structure(
    path: str | Path,
    *,
    index: int | None = None,
    source_id: str | None = None,
) -> AtomicStructure:
    """Parse one XYZ frame as explicitly non-periodic Cartesian structure state."""
    try:
        from pymatgen.io.xyz import XYZ
    except ImportError as exc:
        raise _backend_import_error(exc) from exc

    try:
        parsed = XYZ.from_file(path)
        records = parsed.all_molecules
    except Exception as exc:
        raise StructureIOError("failed to parse XYZ with pymatgen-core") from exc
    selected = _select_record(records, index=index, format_name="XYZ")
    return _convert_site_collection(
        selected,
        periodic=False,
        source_format="XYZ",
        path=path,
        source_id=source_id,
    )


__all__ = [
    "StructureIOError",
    "read_cif_structure",
    "read_contcar",
    "read_poscar",
    "read_xyz_structure",
]
