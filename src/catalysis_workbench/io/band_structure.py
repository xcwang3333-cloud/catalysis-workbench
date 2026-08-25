"""Lazy VASP band-structure adapter with explicit path/spin semantics."""

from __future__ import annotations

import hashlib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import numpy as np

from catalysis_workbench.computation import (
    BandEnergyChannel,
    BandPathSegment,
    BandStructureError,
    BandStructureState,
)

from .electronic_structure import (
    ElectronicStructureIOError,
    _backend_import_error,
    _physical_spin_items,
    _safe_parameters,
    _source_metadata,
)
from .structure import StructureIOError, _convert_site_collection

_KPOINT_ATOL = 1e-8


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


def _line_mode_name(style: object) -> str:
    name = getattr(style, "name", None)
    text = str(name if name is not None else style).strip().lower()
    return text.replace("-", "_").replace(" ", "_")


def _line_mode_path(
    kpoint_file: Any,
    *,
    actual_kpoints: np.ndarray,
) -> tuple[BandPathSegment, ...]:
    if _line_mode_name(getattr(kpoint_file, "style", None)) != "line_mode":
        raise ElectronicStructureIOError(
            "Block-3 VASP adapter requires an explicit line-mode KPOINTS source"
        )
    coordinate_type = str(getattr(kpoint_file, "coord_type", "")).strip().lower()
    if not coordinate_type.startswith("r"):
        raise ElectronicStructureIOError(
            "Block-3 minimum adapter supports reciprocal-coordinate line-mode KPOINTS only"
        )
    try:
        subdivisions = int(kpoint_file.num_kpts)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ElectronicStructureIOError(
            "line-mode KPOINTS must expose an integer subdivision count"
        ) from exc
    if subdivisions < 2:
        raise ElectronicStructureIOError(
            "line-mode KPOINTS subdivision count must be at least 2"
        )

    try:
        endpoints = np.asarray(kpoint_file.kpts, dtype=np.float64)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ElectronicStructureIOError(
            "line-mode KPOINTS must expose numeric endpoint coordinates"
        ) from exc
    if (
        endpoints.ndim != 2
        or endpoints.shape[1] != 3
        or endpoints.shape[0] < 2
        or endpoints.shape[0] % 2 != 0
        or not np.isfinite(endpoints).all()
    ):
        raise ElectronicStructureIOError(
            "line-mode KPOINTS endpoints must be a finite even-length (n, 3) array"
        )

    raw_labels = getattr(kpoint_file, "labels", None)
    if raw_labels is None:
        labels: tuple[str | None, ...] = (None,) * endpoints.shape[0]
    else:
        labels = tuple(
            None if label is None or not str(label).strip() else str(label)
            for label in raw_labels
        )
        if len(labels) != endpoints.shape[0]:
            raise ElectronicStructureIOError(
                "line-mode KPOINTS labels must align exactly with endpoint coordinates"
            )

    segment_count = endpoints.shape[0] // 2
    expected_count = segment_count * subdivisions
    if actual_kpoints.shape != (expected_count, 3):
        raise ElectronicStructureIOError(
            "vasprun actual k-point layout does not exactly match the supplied "
            "line-mode KPOINTS path; hybrid/uniform+line layouts are unsupported "
            "in the Block-3 minimum adapter"
        )

    segments: list[BandPathSegment] = []
    for segment_index in range(segment_count):
        source_start = segment_index * 2
        source_end = source_start + 1
        start_index = segment_index * subdivisions
        end_index = start_index + subdivisions - 1
        expected = np.linspace(
            endpoints[source_start],
            endpoints[source_end],
            subdivisions,
            dtype=np.float64,
        )
        actual = actual_kpoints[start_index : end_index + 1]
        if not np.allclose(actual, expected, rtol=0.0, atol=_KPOINT_ATOL):
            raise ElectronicStructureIOError(
                "vasprun actual k-points do not match the explicit line-mode "
                f"KPOINTS interpolation for segment {segment_index}"
            )
        segments.append(
            BandPathSegment(
                key=f"segment-{segment_index}",
                start_index=start_index,
                end_index=end_index,
                start_label=labels[source_start],
                end_label=labels[source_end],
            )
        )
    return tuple(segments)


def _band_energy_channels(
    eigenvalues: Any,
    *,
    ispin: int,
    kpoint_count: int,
) -> tuple[BandEnergyChannel, ...]:
    channels: list[BandEnergyChannel] = []
    for spin, raw_values in _physical_spin_items(eigenvalues, ispin=ispin):
        source = np.asarray(raw_values)
        if np.iscomplexobj(source):
            raise ElectronicStructureIOError(
                "vasprun band eigenvalues must contain real values"
            )
        try:
            values = np.asarray(raw_values, dtype=np.float64)
        except (TypeError, ValueError) as exc:
            raise ElectronicStructureIOError(
                "vasprun band eigenvalues must contain numeric values"
            ) from exc
        if (
            values.ndim != 3
            or values.shape[0] != kpoint_count
            or values.shape[1] <= 0
            or values.shape[2] < 1
        ):
            raise ElectronicStructureIOError(
                "vasprun eigenvalues must have shape (n_kpoints, n_bands, >=1)"
            )
        energies = values[:, :, 0].T
        if not np.isfinite(energies).all():
            raise ElectronicStructureIOError(
                "vasprun band energies contain non-finite values"
            )
        channels.append(
            BandEnergyChannel(
                spin=spin,
                energies_ev=energies,
                band_indices=tuple(range(energies.shape[0])),
            )
        )
    return tuple(channels)


def _source_digest(
    *,
    structure_digest: str,
    backend_version: str,
    kpoints: np.ndarray,
    reciprocal_lattice: np.ndarray,
    channels: tuple[BandEnergyChannel, ...],
    source_fermi_ev: float,
    segments: tuple[BandPathSegment, ...],
) -> str:
    digest = hashlib.sha256()
    digest.update(b"CatalysisWorkbench.VASPBandSource.v1\0")
    for text in (structure_digest, backend_version):
        encoded = text.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "little", signed=False))
        digest.update(encoded)
    digest.update(np.ascontiguousarray(kpoints, dtype=np.float64).tobytes(order="C"))
    digest.update(
        np.ascontiguousarray(reciprocal_lattice, dtype=np.float64).tobytes(order="C")
    )
    digest.update(repr(source_fermi_ev).encode("utf-8"))
    for channel in channels:
        digest.update(channel.digest.encode("ascii"))
    for segment in segments:
        digest.update(segment.key.encode("utf-8"))
        digest.update(segment.start_index.to_bytes(8, "little", signed=False))
        digest.update(segment.end_index.to_bytes(8, "little", signed=False))
        for label in (segment.start_label, segment.end_label):
            if label is None:
                digest.update(b"\xff")
            else:
                encoded = label.encode("utf-8")
                digest.update(len(encoded).to_bytes(8, "little", signed=False))
                digest.update(encoded)
    return digest.hexdigest()


def _convert_vasprun_band_result(
    run: Any,
    kpoint_file: Any,
    *,
    path: str | Path,
    kpoints_path: str | Path,
    source_id: str | None,
    backend_version: str,
) -> BandStructureState:
    parameters = _safe_parameters(run)
    if bool(parameters.get("LNONCOLLINEAR", False)) or bool(
        parameters.get("LSORBIT", False)
    ):
        raise ElectronicStructureIOError(
            "non-collinear/SOC band structures are unsupported in v0.7 Block 3"
        )
    try:
        ispin = int(parameters.get("ISPIN", 1))
    except (TypeError, ValueError) as exc:
        raise ElectronicStructureIOError("ISPIN must be an integer") from exc
    if ispin not in {1, 2}:
        raise ElectronicStructureIOError(
            "Block-3 VASP adapter supports only collinear ISPIN=1 or ISPIN=2"
        )

    try:
        actual_kpoints = np.asarray(run.actual_kpoints, dtype=np.float64)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ElectronicStructureIOError(
            "vasprun result must expose numeric actual_kpoints"
        ) from exc
    if (
        actual_kpoints.ndim != 2
        or actual_kpoints.shape[1] != 3
        or actual_kpoints.shape[0] < 2
        or not np.isfinite(actual_kpoints).all()
    ):
        raise ElectronicStructureIOError(
            "vasprun actual_kpoints must be a finite (n, 3) array"
        )

    segments = _line_mode_path(kpoint_file, actual_kpoints=actual_kpoints)
    eigenvalues = getattr(run, "eigenvalues", None)
    if eigenvalues is None:
        raise ElectronicStructureIOError(
            "vasprun result does not contain parsed band eigenvalues"
        )
    channels = _band_energy_channels(
        eigenvalues,
        ispin=ispin,
        kpoint_count=actual_kpoints.shape[0],
    )

    source_fermi = getattr(run, "efermi", None)
    try:
        fermi = float(source_fermi)
    except (TypeError, ValueError) as exc:
        raise ElectronicStructureIOError(
            "vasprun result must expose a finite source Fermi energy"
        ) from exc
    if not np.isfinite(fermi):
        raise ElectronicStructureIOError(
            "vasprun result must expose a finite source Fermi energy"
        )

    try:
        backend_structure = run.final_structure
        reciprocal = np.asarray(
            backend_structure.lattice.reciprocal_lattice.matrix,
            dtype=np.float64,
        )
        structure = _convert_site_collection(
            backend_structure,
            periodic=True,
            source_format="vasprun.xml",
            path=path,
            source_id=source_id,
        )
    except (AttributeError, TypeError, ValueError, StructureIOError) as exc:
        raise ElectronicStructureIOError(
            "vasprun result does not expose a supported final structure/reciprocal lattice"
        ) from exc
    if reciprocal.shape != (3, 3) or not np.isfinite(reciprocal).all():
        raise ElectronicStructureIOError(
            "backend reciprocal lattice must be a finite 3x3 matrix"
        )

    source_digest = _source_digest(
        structure_digest=structure.digest,
        backend_version=backend_version,
        kpoints=actual_kpoints,
        reciprocal_lattice=reciprocal,
        channels=channels,
        source_fermi_ev=fermi,
        segments=segments,
    )
    metadata = _source_metadata(
        source_format="vasprun.xml",
        path=path,
        source_id=source_id,
    )
    metadata.update(
        {
            "data_kind": "band-structure",
            "kpoints_path": str(Path(kpoints_path)),
            "pymatgen_core_version": backend_version,
            "ispin": ispin,
            "reciprocal_coordinate_convention": "fractional",
            "reciprocal_cartesian_convention": "physics-2pi",
            "kpoint_reconciliation_atol": _KPOINT_ATOL,
            "projection_state": "not-parsed-block3",
        }
    )
    try:
        return BandStructureState(
            structure=structure,
            kpoints_fractional=actual_kpoints,
            reciprocal_lattice_cartesian=reciprocal,
            reciprocal_unit="1/angstrom",
            reciprocal_cartesian_includes_2pi=True,
            channels=channels,
            path_segments=segments,
            source_digest=source_digest,
            source_fermi_ev=fermi,
            reference_kind="source-native",
            applied_shift_ev=0.0,
            reciprocal_coordinate_convention="fractional",
            metadata=metadata,
        )
    except (BandStructureError, TypeError, ValueError) as exc:
        raise ElectronicStructureIOError(
            "parsed vasprun/KPOINTS state violates the Block-3 band contract"
        ) from exc


def read_vasprun_band_structure(
    path: str | Path,
    *,
    kpoints_path: str | Path | None = None,
    source_id: str | None = None,
) -> BandStructureState:
    """Read a standard reciprocal line-mode VASP band structure without inference."""
    try:
        from pymatgen.io.vasp.inputs import Kpoints
        from pymatgen.io.vasp.outputs import Vasprun
    except ImportError as exc:
        raise _backend_import_error(exc) from exc

    backend_version = _backend_version()
    source_path = Path(path)
    resolved_kpoints = (
        source_path.with_name("KPOINTS")
        if kpoints_path is None
        else Path(kpoints_path)
    )
    try:
        kpoint_file = Kpoints.from_file(resolved_kpoints)
    except Exception as exc:
        raise ElectronicStructureIOError(
            "failed to parse the explicit line-mode KPOINTS source with pymatgen-core"
        ) from exc
    try:
        run = Vasprun(
            source_path,
            parse_dos=False,
            parse_eigen=True,
            parse_projected_eigen=False,
            parse_potcar_file=False,
        )
    except Exception as exc:
        raise ElectronicStructureIOError(
            "failed to parse vasprun.xml band data with pymatgen-core"
        ) from exc
    return _convert_vasprun_band_result(
        run,
        kpoint_file,
        path=source_path,
        kpoints_path=resolved_kpoints,
        source_id=source_id,
        backend_version=backend_version,
    )


__all__ = ["read_vasprun_band_structure"]
