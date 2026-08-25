"""Lazy VASP LOCPOT adapter with exact source-potential semantics."""

from __future__ import annotations

import hashlib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import numpy as np

from catalysis_workbench.computation import ScalarField, ScalarFieldError

from .electronic_structure import (
    ElectronicStructureIOError,
    _backend_import_error,
    _source_metadata,
)
from .structure import StructureIOError, _convert_site_collection


def _backend_version() -> str:
    try:
        text = version("pymatgen-core").strip()
    except PackageNotFoundError as exc:
        raise ElectronicStructureIOError(
            "installed pymatgen-core distribution version is unavailable"
        ) from exc
    if not text:
        raise ElectronicStructureIOError("installed pymatgen-core version is blank")
    return text


def _locpot_grid(parsed: Any) -> tuple[str, np.ndarray, tuple[str, ...]]:
    try:
        raw = dict(parsed.data)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ElectronicStructureIOError(
            "LOCPOT backend result must expose a volumetric data mapping"
        ) from exc
    if len(raw) != 1:
        keys = tuple(sorted(str(key) for key in raw))
        raise ElectronicStructureIOError(
            "LOCPOT must expose exactly one unambiguous scalar potential grid; "
            f"got keys {keys}"
        )
    raw_key, raw_values = next(iter(raw.items()))
    key = str(raw_key).strip()
    if not key:
        raise ElectronicStructureIOError("LOCPOT backend returned a blank data key")
    try:
        values = np.asarray(raw_values, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ElectronicStructureIOError("LOCPOT potential grid must be numeric") from exc
    if values.ndim != 3 or any(size <= 0 for size in values.shape):
        raise ElectronicStructureIOError("LOCPOT potential must be a non-empty 3-D grid")
    if not np.isfinite(values).all():
        raise ElectronicStructureIOError("LOCPOT potential contains non-finite values")
    retained = np.array(values, dtype=np.float64, copy=True, order="C")
    return key, retained, (key,)


def _source_digest(
    *,
    structure_digest: str,
    backend_version: str,
    backend_key: str,
    values: np.ndarray,
) -> str:
    digest = hashlib.sha256()
    digest.update(b"CatalysisWorkbench.LOCPOTSource.v1\0")
    for text in (structure_digest, backend_version, backend_key):
        encoded = text.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "little", signed=False))
        digest.update(encoded)
    contiguous = np.ascontiguousarray(values, dtype=np.float64)
    for size in contiguous.shape:
        digest.update(int(size).to_bytes(8, "little", signed=False))
    digest.update(contiguous.tobytes(order="C"))
    return digest.hexdigest()


def _calculation_id(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        raise ElectronicStructureIOError("calculation_id must not be blank when supplied")
    return text


def _convert_locpot_result(
    parsed: Any,
    *,
    path: str | Path,
    source_id: str | None,
    calculation_id: str | None,
    backend_version: str,
) -> ScalarField:
    try:
        structure = _convert_site_collection(
            parsed.structure,
            periodic=True,
            source_format="LOCPOT",
            path=path,
            source_id=source_id,
        )
    except (AttributeError, StructureIOError) as exc:
        raise ElectronicStructureIOError(
            "LOCPOT result does not expose a supported periodic structure"
        ) from exc

    backend_key, values, backend_keys = _locpot_grid(parsed)
    source_digest = _source_digest(
        structure_digest=structure.digest,
        backend_version=backend_version,
        backend_key=backend_key,
        values=values,
    )
    metadata = _source_metadata(source_format="LOCPOT", path=path, source_id=source_id)
    retained_calculation_id = _calculation_id(calculation_id)
    metadata.update(
        {
            "pymatgen_core_version": backend_version,
            "backend_data_keys": backend_keys,
            "selected_backend_key": backend_key,
            "value_semantics": "vasp-local-potential-energy",
            "value_unit": "eV",
            "volume_normalized": False,
        }
    )
    if retained_calculation_id is not None:
        metadata["calculation_id"] = retained_calculation_id
    try:
        return ScalarField(
            structure=structure,
            values=values,
            field_kind="local-potential",
            value_unit="eV",
            source_type="LOCPOT",
            source_key=f"locpot:{backend_key}",
            source_digest=source_digest,
            metadata=metadata,
        )
    except (ScalarFieldError, TypeError, ValueError) as exc:
        raise ElectronicStructureIOError(
            "parsed LOCPOT violates the scalar-field contract"
        ) from exc


def read_locpot_field(
    path: str | Path,
    *,
    source_id: str | None = None,
    calculation_id: str | None = None,
) -> ScalarField:
    """Read one exact LOCPOT scalar potential grid without scaling or normalization."""
    try:
        from pymatgen.io.vasp.outputs import Locpot
    except ImportError as exc:
        raise _backend_import_error(exc) from exc

    backend_version = _backend_version()
    try:
        parsed = Locpot.from_file(path)
    except Exception as exc:
        raise ElectronicStructureIOError(
            "failed to parse LOCPOT with pymatgen-core"
        ) from exc
    return _convert_locpot_result(
        parsed,
        path=path,
        source_id=source_id,
        calculation_id=calculation_id,
        backend_version=backend_version,
    )


__all__ = ["read_locpot_field"]
