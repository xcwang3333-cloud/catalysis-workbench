"""Lazy VASP PROCAR adapter bound to reviewed Block-3 band state."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np

from catalysis_workbench.computation.band_structure import BandStructureState
from catalysis_workbench.computation.projected_bands import (
    BandProjectionChannel,
    BandProjectionError,
    BandProjectionState,
)

from .band_structure import _backend_version
from .electronic_structure import (
    ElectronicStructureIOError,
    _backend_import_error,
    _source_metadata,
    _spin_token,
)

_DEFAULT_KPOINT_ATOL = 1e-5
_DEFAULT_ENERGY_ATOL_EV = 1e-4


def _finite_tolerance(value: object, *, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a finite non-negative float") from exc
    if not np.isfinite(result) or result < 0.0:
        raise ElectronicStructureIOError(f"{name} must be a finite non-negative float")
    return result


def _physical_mapping(
    raw_mapping: Any,
    *,
    expected_spins: tuple[str, ...],
    name: str,
) -> dict[str, Any]:
    try:
        items = tuple(dict(raw_mapping).items())
    except (TypeError, ValueError) as exc:
        raise ElectronicStructureIOError(f"PROCAR {name} must be a spin mapping") from exc

    if expected_spins == ("total",):
        if len(items) != 1:
            raise ElectronicStructureIOError(
                f"non-spin-polarized band state requires exactly one PROCAR {name} channel"
            )
        return {"total": items[0][1]}

    if set(expected_spins) == {"up", "down"}:
        mapped: dict[str, Any] = {}
        for backend_spin, values in items:
            token = _spin_token(backend_spin)
            if token in mapped:
                raise ElectronicStructureIOError(
                    f"PROCAR {name} contains duplicate physical spin {token!r}"
                )
            mapped[token] = values
        if set(mapped) != {"up", "down"}:
            raise ElectronicStructureIOError(
                f"spin-polarized band state requires complete PROCAR up/down {name} channels"
            )
        return {"up": mapped["up"], "down": mapped["down"]}

    raise ElectronicStructureIOError(
        "associated band state must contain exactly total or complete up/down physical spins"
    )


def _source_digest(
    *,
    backend_version: str,
    kpoints: np.ndarray,
    orbitals: tuple[str, ...],
    channels: tuple[BandProjectionChannel, ...],
    eigenvalues: dict[str, np.ndarray],
) -> str:
    digest = hashlib.sha256()
    digest.update(b"CatalysisWorkbench.PROCARSource.v1\0")
    encoded = backend_version.encode("utf-8")
    digest.update(len(encoded).to_bytes(8, "little", signed=False))
    digest.update(encoded)
    digest.update(np.ascontiguousarray(kpoints, dtype=np.float64).tobytes(order="C"))
    for orbital in orbitals:
        encoded = orbital.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "little", signed=False))
        digest.update(encoded)
    for channel in channels:
        digest.update(channel.digest.encode("ascii"))
        values = np.ascontiguousarray(eigenvalues[channel.spin], dtype=np.float64)
        digest.update(values.tobytes(order="C"))
    return digest.hexdigest()


def _convert_procar_result(
    parsed: Any,
    *,
    band_structure: BandStructureState,
    path: str | Path,
    source_id: str | None,
    kpoint_atol: float,
    energy_atol_ev: float,
    backend_version: str,
) -> BandProjectionState:
    if not isinstance(band_structure, BandStructureState):
        raise TypeError("band_structure must be a BandStructureState")
    kpoint_atol = _finite_tolerance(kpoint_atol, name="kpoint_atol")
    energy_atol_ev = _finite_tolerance(energy_atol_ev, name="energy_atol_ev")

    if bool(getattr(parsed, "is_soc", False)):
        raise ElectronicStructureIOError(
            "SOC/non-collinear PROCAR vector projection state is unsupported in v0.7 Block 4"
        )
    if getattr(parsed, "xyz_data", None) is not None:
        raise ElectronicStructureIOError(
            "PROCAR xyz/vector projection data cannot be collapsed into Block-4 scalar channels"
        )

    raw_orbitals = getattr(parsed, "orbitals", None)
    if raw_orbitals is None:
        raise ElectronicStructureIOError("PROCAR result does not expose orbital headers")
    orbitals = tuple(str(item).strip() for item in raw_orbitals)
    if not orbitals or any(not item for item in orbitals):
        raise ElectronicStructureIOError("PROCAR orbital headers must be non-empty")
    if len(set(orbitals)) != len(orbitals):
        raise ElectronicStructureIOError("PROCAR orbital headers must be unique")

    try:
        kpoints = np.asarray(parsed.kpoints, dtype=np.float64)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ElectronicStructureIOError("PROCAR result must expose numeric kpoints") from exc
    expected_kpoints = band_structure.kpoints_fractional
    if kpoints.shape != expected_kpoints.shape or not np.isfinite(kpoints).all():
        raise ElectronicStructureIOError(
            "PROCAR k-point count/shape must exactly match the associated band state"
        )
    if not np.allclose(kpoints, expected_kpoints, rtol=0.0, atol=kpoint_atol):
        raise ElectronicStructureIOError(
            "PROCAR k-point order/coordinates do not match the associated band state "
            "within caller-visible kpoint_atol"
        )

    expected_spins = tuple(channel.spin for channel in band_structure.channels)
    data_map = _physical_mapping(
        getattr(parsed, "data", None),
        expected_spins=expected_spins,
        name="projection",
    )
    eigen_map_raw = _physical_mapping(
        getattr(parsed, "eigenvalues", None),
        expected_spins=expected_spins,
        name="eigenvalue",
    )

    n_bands = band_structure.channels[0].energies_ev.shape[0]
    n_kpoints = expected_kpoints.shape[0]
    n_sites = band_structure.structure.site_count
    expected_source_shape = (n_kpoints, n_bands, n_sites, len(orbitals))

    channels: list[BandProjectionChannel] = []
    retained_eigenvalues: dict[str, np.ndarray] = {}
    for spin in expected_spins:
        source_projection = np.asarray(data_map[spin])
        if np.iscomplexobj(source_projection):
            raise ElectronicStructureIOError("PROCAR scalar projection weights must be real")
        try:
            projection = np.asarray(source_projection, dtype=np.float64)
        except (TypeError, ValueError) as exc:
            raise ElectronicStructureIOError(
                "PROCAR scalar projection weights must be numeric"
            ) from exc
        if projection.shape != expected_source_shape:
            raise ElectronicStructureIOError(
                "PROCAR projection tensor must exactly match "
                f"(n_kpoints, n_bands, n_sites, n_orbitals)={expected_source_shape}; "
                f"got {projection.shape}"
            )
        if not np.isfinite(projection).all() or np.any(projection < 0.0):
            raise ElectronicStructureIOError(
                "PROCAR scalar projection weights must be finite and non-negative"
            )

        source_eigen = np.asarray(eigen_map_raw[spin])
        if np.iscomplexobj(source_eigen):
            raise ElectronicStructureIOError("PROCAR eigenvalues must be real")
        try:
            eigenvalues = np.asarray(source_eigen, dtype=np.float64)
        except (TypeError, ValueError) as exc:
            raise ElectronicStructureIOError("PROCAR eigenvalues must be numeric") from exc
        if eigenvalues.shape != (n_kpoints, n_bands) or not np.isfinite(eigenvalues).all():
            raise ElectronicStructureIOError(
                "PROCAR eigenvalues must have exact shape (n_kpoints, n_bands)"
            )
        band_energies = band_structure.channel(spin).energies_ev.T
        if not np.allclose(
            eigenvalues,
            band_energies,
            rtol=0.0,
            atol=energy_atol_ev,
        ):
            raise ElectronicStructureIOError(
                "PROCAR eigenvalues do not match associated Block-3 band energies "
                "within caller-visible energy_atol_ev"
            )

        canonical = np.transpose(projection, (1, 0, 2, 3))
        try:
            channel = BandProjectionChannel(spin=spin, weights=canonical)
        except (BandProjectionError, TypeError, ValueError) as exc:
            raise ElectronicStructureIOError(
                "PROCAR projection channel violates the Block-4 retained-state contract"
            ) from exc
        channels.append(channel)
        retained_eigenvalues[spin] = np.array(eigenvalues, dtype=np.float64, copy=True)

    parsed_nions = getattr(parsed, "nions", None)
    if parsed_nions is not None:
        try:
            parsed_nions_value = int(parsed_nions)
        except (TypeError, ValueError) as exc:
            raise ElectronicStructureIOError("PROCAR nions must be integer-like") from exc
        if parsed_nions_value != n_sites:
            raise ElectronicStructureIOError(
                "PROCAR nions does not match the associated AtomicStructure site count"
            )

    source_digest = _source_digest(
        backend_version=backend_version,
        kpoints=kpoints,
        orbitals=orbitals,
        channels=tuple(channels),
        eigenvalues=retained_eigenvalues,
    )

    metadata = _source_metadata(
        source_format="PROCAR",
        path=path,
        source_id=source_id,
    )
    metadata.update(
        {
            "data_kind": "band-projection",
            "pymatgen_core_version": backend_version,
            "source_axis_order": "kpoint,band,site,orbital",
            "canonical_axis_order": "band,kpoint,site,orbital",
            "kpoint_atol": kpoint_atol,
            "energy_atol_ev": energy_atol_ev,
            "parser_kpoint_precision_note": "current pymatgen-core rounds PROCAR kpoints to 5 decimals",
            "band_state_digest": band_structure.digest,
            "band_source_digest": band_structure.source_digest,
            "occupancies_available": getattr(parsed, "occupancies", None) is not None,
        }
    )

    raw_weights = getattr(parsed, "weights", None)
    if raw_weights is not None:
        try:
            kpoint_weights = np.asarray(raw_weights, dtype=np.float64)
        except (TypeError, ValueError) as exc:
            raise ElectronicStructureIOError("PROCAR k-point weights must be numeric") from exc
        if (
            kpoint_weights.shape != (n_kpoints,)
            or not np.isfinite(kpoint_weights).all()
        ):
            raise ElectronicStructureIOError(
                "PROCAR k-point weights must be a finite vector aligned with kpoints"
            )
        metadata["source_kpoint_weights"] = tuple(float(value) for value in kpoint_weights)

    try:
        return BandProjectionState(
            band_structure=band_structure,
            orbitals=orbitals,
            channels=tuple(channels),
            source_digest=source_digest,
            projection_semantics="vasp-procar-projection-weight",
            projection_unit="dimensionless",
            metadata=metadata,
        )
    except (BandProjectionError, TypeError, ValueError) as exc:
        raise ElectronicStructureIOError(
            "parsed PROCAR violates the Block-4 projection-state contract"
        ) from exc


def read_procar_projection(
    path: str | Path,
    *,
    band_structure: BandStructureState,
    source_id: str | None = None,
    kpoint_atol: float = _DEFAULT_KPOINT_ATOL,
    energy_atol_ev: float = _DEFAULT_ENERGY_ATOL_EV,
) -> BandProjectionState:
    """Read one ordinary PROCAR and bind it to an exact reviewed band source."""
    if isinstance(path, (list, tuple)):
        raise ElectronicStructureIOError(
            "Block-4 public adapter accepts exactly one PROCAR path, not multiple files"
        )
    try:
        from pymatgen.io.vasp.outputs import Procar
    except ImportError as exc:
        raise _backend_import_error(exc) from exc

    backend_version = _backend_version()
    source_path = Path(path)
    try:
        parsed = Procar(source_path)
    except Exception as exc:
        raise ElectronicStructureIOError("failed to parse PROCAR with pymatgen-core") from exc
    return _convert_procar_result(
        parsed,
        band_structure=band_structure,
        path=source_path,
        source_id=source_id,
        kpoint_atol=kpoint_atol,
        energy_atol_ev=energy_atol_ev,
        backend_version=backend_version,
    )


__all__ = ["read_procar_projection"]
