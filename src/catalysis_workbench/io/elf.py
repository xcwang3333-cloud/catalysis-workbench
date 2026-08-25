"""Lazy VASP ELFCAR adapter with explicit physical channel semantics."""

from __future__ import annotations

import hashlib
import re
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


_ELFCAR_DIRECT_SPIN_KEY_CHANGE = (2026, 8, 13)


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


def _version_tuple(text: str) -> tuple[int, int, int]:
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", text)
    if match is None:
        raise ElectronicStructureIOError(
            "pymatgen-core version must begin with a numeric YYYY.M.D triplet"
        )
    first, second, third = match.groups()
    return int(first), int(second), int(third)


def _spin_token(value: object) -> str:
    token = str(value).strip().lower().replace("spin_", "")
    aliases = {"unpolarized": "total", "none": "total"}
    token = aliases.get(token, token)
    if token not in {"total", "up", "down"}:
        raise ElectronicStructureIOError("spin must be 'total', 'up', or 'down'")
    return token


def _elf_data_mapping(parsed: Any) -> dict[str, np.ndarray]:
    try:
        raw = dict(parsed.data)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ElectronicStructureIOError(
            "ELFCAR backend result must expose a volumetric data mapping"
        ) from exc
    if not raw:
        raise ElectronicStructureIOError("ELFCAR data must contain at least one channel")

    data: dict[str, np.ndarray] = {}
    shape: tuple[int, int, int] | None = None
    for raw_key, values in raw.items():
        key = str(raw_key).strip()
        if not key:
            raise ElectronicStructureIOError("ELFCAR backend returned a blank data key")
        if key in data:
            raise ElectronicStructureIOError("ELFCAR data keys must be unique")
        try:
            array = np.asarray(values, dtype=np.float64)
        except (TypeError, ValueError) as exc:
            raise ElectronicStructureIOError(
                f"ELFCAR channel {key!r} must contain numeric values"
            ) from exc
        if array.ndim != 3 or any(size <= 0 for size in array.shape):
            raise ElectronicStructureIOError(
                f"ELFCAR channel {key!r} must be a non-empty 3-D grid"
            )
        if not np.isfinite(array).all():
            raise ElectronicStructureIOError(
                f"ELFCAR channel {key!r} contains non-finite values"
            )
        current_shape = tuple(int(size) for size in array.shape)
        if shape is None:
            shape = current_shape
        elif current_shape != shape:
            raise ElectronicStructureIOError(
                "all ELFCAR channels must have the same exact grid shape"
            )
        data[key] = np.array(array, dtype=np.float64, copy=True, order="C")
    return data


def _select_elf_channel(
    data: dict[str, np.ndarray],
    *,
    spin: object,
    backend_version: str,
) -> tuple[str, str, np.ndarray, str]:
    requested = _spin_token(spin)
    keys = set(data)
    version_triplet = _version_tuple(backend_version)

    if keys == {"total"}:
        if requested != "total":
            raise ElectronicStructureIOError(
                "one-channel ELFCAR is unpolarized and requires spin='total'"
            )
        return "total", "total", data["total"], "unpolarized-total"

    if keys == {"spin_up", "spin_down"}:
        if requested == "total":
            raise ElectronicStructureIOError(
                "spin-polarized ELFCAR requires explicit spin='up' or spin='down'"
            )
        backend_key = f"spin_{requested}"
        return requested, backend_key, data[backend_key], "direct-spin-channels"

    if keys == {"total", "diff"}:
        if version_triplet >= _ELFCAR_DIRECT_SPIN_KEY_CHANGE:
            raise ElectronicStructureIOError(
                "current pymatgen-core unexpectedly exposed legacy ELFCAR total/diff keys; "
                "refusing ambiguous channel interpretation"
            )
        if requested == "total":
            raise ElectronicStructureIOError(
                "legacy spin-polarized ELFCAR requires explicit spin='up' or spin='down'"
            )
        backend_key = "total" if requested == "up" else "diff"
        return (
            requested,
            backend_key,
            data[backend_key],
            "legacy-direct-spin-channels-version-guarded",
        )

    raise ElectronicStructureIOError(
        "unsupported ELFCAR channel layout: " + ", ".join(sorted(keys))
    )


def _source_digest(
    *,
    structure_digest: str,
    backend_version: str,
    data: dict[str, np.ndarray],
) -> str:
    digest = hashlib.sha256()
    digest.update(b"CatalysisWorkbench.ELFCARSource.v1\0")
    for text in (structure_digest, backend_version):
        encoded = text.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "little", signed=False))
        digest.update(encoded)
    for key in sorted(data):
        encoded = key.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "little", signed=False))
        digest.update(encoded)
        array = np.ascontiguousarray(data[key], dtype=np.float64)
        for size in array.shape:
            digest.update(int(size).to_bytes(8, "little", signed=False))
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _convert_elfcar_result(
    parsed: Any,
    *,
    path: str | Path,
    spin: object,
    source_id: str | None,
    registration_id: str | None,
    backend_version: str,
) -> ScalarField:
    try:
        structure = _convert_site_collection(
            parsed.structure,
            periodic=True,
            source_format="ELFCAR",
            path=path,
            source_id=source_id,
        )
    except (AttributeError, StructureIOError) as exc:
        raise ElectronicStructureIOError(
            "ELFCAR result does not expose a supported periodic structure"
        ) from exc

    data = _elf_data_mapping(parsed)
    channel, backend_key, values, semantics = _select_elf_channel(
        data,
        spin=spin,
        backend_version=backend_version,
    )
    source_digest = _source_digest(
        structure_digest=structure.digest,
        backend_version=backend_version,
        data=data,
    )
    metadata = _source_metadata(
        source_format="ELFCAR",
        path=path,
        source_id=source_id,
    )
    metadata.update(
        {
            "pymatgen_core_version": backend_version,
            "backend_data_keys": tuple(sorted(data)),
            "selected_backend_key": backend_key,
            "physical_channel": channel,
            "channel_semantics": semantics,
            "value_semantics": "electron-localization-function",
        }
    )
    field_kind = "elf" if channel == "total" else f"elf-spin-{channel}"
    try:
        return ScalarField(
            structure=structure,
            values=values,
            field_kind=field_kind,
            value_unit="dimensionless",
            source_type="ELFCAR",
            source_key=f"elfcar:{channel}",
            source_digest=source_digest,
            registration_id=registration_id,
            metadata=metadata,
        )
    except (ScalarFieldError, TypeError, ValueError) as exc:
        raise ElectronicStructureIOError(
            "parsed ELFCAR violates the scalar-field contract"
        ) from exc


def read_elfcar_field(
    path: str | Path,
    *,
    spin: str = "total",
    source_id: str | None = None,
    registration_id: str | None = None,
) -> ScalarField:
    """Read one explicit physical ELF channel without normalization or clipping."""
    try:
        from pymatgen.io.vasp.outputs import Elfcar
    except ImportError as exc:
        raise _backend_import_error(exc) from exc

    backend_version = _backend_version()
    try:
        parsed = Elfcar.from_file(path)
    except Exception as exc:
        raise ElectronicStructureIOError(
            "failed to parse ELFCAR with pymatgen-core"
        ) from exc
    return _convert_elfcar_result(
        parsed,
        path=path,
        spin=spin,
        source_id=source_id,
        registration_id=registration_id,
        backend_version=backend_version,
    )


__all__ = ["read_elfcar_field"]
