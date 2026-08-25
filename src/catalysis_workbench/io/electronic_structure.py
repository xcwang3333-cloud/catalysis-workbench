"""Lazy pymatgen-core adapters for reviewed VASP electronic/volumetric results."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from catalysis_workbench.computation import (
    DOSChannel,
    DOSProjection,
    ElectronicDOS,
    ElectronicEnergyAxis,
    ElectronicStructureError,
    VolumetricGrid,
)

from .structure import StructureIOError, _convert_site_collection


class ElectronicStructureIOError(ValueError):
    """Raised when electronic/volumetric output violates the reviewed adapter contract."""


def _backend_import_error(exc: ImportError) -> ElectronicStructureIOError:
    return ElectronicStructureIOError(
        "electronic-structure adapters require the optional dependency; install "
        "catalysis-workbench[structure]"
    )


def _source_metadata(
    *,
    source_format: str,
    path: str | Path,
    source_id: str | None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "electronic_format": source_format,
        "electronic_backend": "pymatgen-core",
        "source_path": str(Path(path)),
    }
    if source_id is not None:
        text = str(source_id).strip()
        if not text:
            raise ElectronicStructureIOError(
                "source_id must not be blank when supplied"
            )
        metadata["source_id"] = text
    return metadata


def _spin_token(spin: Any) -> str:
    name = getattr(spin, "name", None)
    if name is not None:
        text = str(name).strip().lower()
        if text in {"up", "down"}:
            return text
    value = getattr(spin, "value", None)
    if value == 1:
        return "up"
    if value == -1:
        return "down"
    text = str(spin).strip().lower()
    if text in {"1", "spin.up", "up"}:
        return "up"
    if text in {"-1", "spin.down", "down"}:
        return "down"
    raise ElectronicStructureIOError(f"unsupported spin identity {spin!r}")


def _physical_spin_items(
    densities: Any,
    *,
    ispin: int,
) -> tuple[tuple[str, Any], ...]:
    try:
        items = tuple(dict(densities).items())
    except (TypeError, ValueError) as exc:
        raise ElectronicStructureIOError(
            "backend DOS densities must be a spin-to-array mapping"
        ) from exc
    if ispin == 1:
        if len(items) != 1:
            raise ElectronicStructureIOError(
                "ISPIN=1 DOS must expose exactly one backend density channel"
            )
        return (("total", items[0][1]),)
    if ispin == 2:
        mapped: dict[str, Any] = {}
        for spin, values in items:
            token = _spin_token(spin)
            if token in mapped:
                raise ElectronicStructureIOError(
                    "ISPIN=2 DOS contains duplicate physical spin channels"
                )
            mapped[token] = values
        if set(mapped) != {"up", "down"}:
            raise ElectronicStructureIOError(
                "ISPIN=2 DOS must expose both up and down channels"
            )
        return (("up", mapped["up"]), ("down", mapped["down"]))
    raise ElectronicStructureIOError("only collinear ISPIN=1 or ISPIN=2 is supported")


def _safe_parameters(run: Any) -> dict[str, Any]:
    parameters = getattr(run, "parameters", None)
    if parameters is None:
        return {}
    try:
        return dict(parameters)
    except (TypeError, ValueError) as exc:
        raise ElectronicStructureIOError(
            "backend run parameters must be mapping-like"
        ) from exc


def _orbital_label(orbital: Any) -> str:
    text = str(orbital).strip()
    if not text:
        raise ElectronicStructureIOError("backend returned a blank orbital label")
    return text


def _convert_vasprun_result(
    run: Any,
    *,
    path: str | Path,
    source_id: str | None,
) -> ElectronicDOS:
    parameters = _safe_parameters(run)
    if bool(parameters.get("LNONCOLLINEAR", False)) or bool(
        parameters.get("LSORBIT", False)
    ):
        raise ElectronicStructureIOError(
            "non-collinear/SOC DOS projections are not supported in v0.6 block 1"
        )
    try:
        ispin = int(parameters.get("ISPIN", 1))
    except (TypeError, ValueError) as exc:
        raise ElectronicStructureIOError("ISPIN must be an integer") from exc

    tdos = getattr(run, "tdos", None)
    if tdos is None:
        raise ElectronicStructureIOError("vasprun result does not contain total DOS")
    try:
        energies = np.asarray(tdos.energies, dtype=np.float64)
        densities = tdos.densities
    except (AttributeError, TypeError, ValueError) as exc:
        raise ElectronicStructureIOError(
            "backend total DOS does not expose energies/densities"
        ) from exc
    fermi = getattr(run, "efermi", getattr(tdos, "efermi", None))
    if fermi is None:
        raise ElectronicStructureIOError("vasprun result does not expose E_F")

    try:
        structure = _convert_site_collection(
            run.final_structure,
            periodic=True,
            source_format="vasprun.xml",
            path=path,
            source_id=source_id,
        )
    except (AttributeError, StructureIOError) as exc:
        raise ElectronicStructureIOError(
            "vasprun result does not expose a supported final structure"
        ) from exc

    channels: list[DOSChannel] = []
    total_projection = DOSProjection(key="total", kind="total")
    for spin, values in _physical_spin_items(densities, ispin=ispin):
        channels.append(
            DOSChannel(
                projection=total_projection,
                spin=spin,
                density=values,
                density_unit="states/eV",
                normalization_basis="cell",
            )
        )

    pdos = getattr(run, "pdos", None)
    if pdos:
        if len(pdos) != structure.site_count:
            raise ElectronicStructureIOError(
                "vasprun PDOS site count does not match final structure"
            )
        for site_index, orbital_map in enumerate(pdos):
            try:
                orbital_items = tuple(dict(orbital_map).items())
            except (TypeError, ValueError) as exc:
                raise ElectronicStructureIOError(
                    "vasprun PDOS site state must map orbitals to spin densities"
                ) from exc
            for orbital, spin_densities in orbital_items:
                orbital_label = _orbital_label(orbital)
                site_key = structure.site_keys[site_index]
                projection = DOSProjection(
                    key=f"pdos:{site_key}:{orbital_label}",
                    kind="site-orbital",
                    site_index=site_index,
                    site_key=site_key,
                    element=structure.elements[site_index],
                    orbital=orbital_label,
                )
                for spin, values in _physical_spin_items(
                    spin_densities,
                    ispin=ispin,
                ):
                    channels.append(
                        DOSChannel(
                            projection=projection,
                            spin=spin,
                            density=values,
                            density_unit="states/eV",
                            normalization_basis="site",
                        )
                    )

    metadata = _source_metadata(
        source_format="vasprun.xml",
        path=path,
        source_id=source_id,
    )
    metadata["ispin"] = ispin
    try:
        return ElectronicDOS(
            energy=ElectronicEnergyAxis(
                energies,
                reference_kind="source-native",
                source_fermi_ev=float(fermi),
                applied_shift_ev=0.0,
            ),
            channels=channels,
            structure=structure,
            metadata=metadata,
        )
    except (ElectronicStructureError, TypeError, ValueError) as exc:
        raise ElectronicStructureIOError(
            "parsed vasprun DOS violates the electronic-state contract"
        ) from exc


def read_vasprun_dos(
    path: str | Path,
    *,
    source_id: str | None = None,
) -> ElectronicDOS:
    """Parse source-native VASP DOS/PDOS without hidden Fermi shifting."""
    try:
        from pymatgen.io.vasp.outputs import Vasprun
    except ImportError as exc:
        raise _backend_import_error(exc) from exc

    try:
        parsed = Vasprun(
            path,
            parse_dos=True,
            parse_eigen=False,
            parse_projected_eigen=False,
            parse_potcar_file=False,
        )
    except Exception as exc:
        raise ElectronicStructureIOError(
            "failed to parse vasprun.xml with pymatgen-core"
        ) from exc
    return _convert_vasprun_result(parsed, path=path, source_id=source_id)


def _convert_chgcar_result(
    parsed: Any,
    *,
    path: str | Path,
    source_id: str | None,
) -> VolumetricGrid:
    try:
        structure = _convert_site_collection(
            parsed.structure,
            periodic=True,
            source_format="CHGCAR",
            path=path,
            source_id=source_id,
        )
    except (AttributeError, StructureIOError) as exc:
        raise ElectronicStructureIOError(
            "CHGCAR result does not expose a supported periodic structure"
        ) from exc
    assert structure.lattice_angstrom is not None
    cell_volume = float(abs(np.linalg.det(structure.lattice_angstrom)))
    if not np.isfinite(cell_volume) or cell_volume <= 0:
        raise ElectronicStructureIOError(
            "CHGCAR structure must have a positive finite cell volume"
        )

    try:
        data = dict(parsed.data)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ElectronicStructureIOError(
            "CHGCAR backend result must expose a volumetric data mapping"
        ) from exc
    if "total" not in data:
        raise ElectronicStructureIOError("CHGCAR data must contain a total component")
    unsupported = set(data) - {"total", "diff"}
    if unsupported:
        raise ElectronicStructureIOError(
            "non-collinear/unknown CHGCAR components are unsupported: "
            + ", ".join(sorted(str(key) for key in unsupported))
        )

    components: dict[str, np.ndarray] = {
        "total": np.asarray(data["total"], dtype=np.float64) / cell_volume
    }
    if "diff" in data:
        components["magnetization_z"] = (
            np.asarray(data["diff"], dtype=np.float64) / cell_volume
        )

    metadata = _source_metadata(
        source_format="CHGCAR",
        path=path,
        source_id=source_id,
    )
    metadata["backend_grid_semantics"] = "vasp-file-grid-preserved"
    metadata["density_conversion"] = "pymatgen-grid / cell_volume_angstrom3"
    try:
        return VolumetricGrid(
            structure=structure,
            components=components,
            density_unit="1/angstrom^3",
            metadata=metadata,
        )
    except (ElectronicStructureError, TypeError, ValueError) as exc:
        raise ElectronicStructureIOError(
            "parsed CHGCAR violates the volumetric-state contract"
        ) from exc


def read_chgcar_density(
    path: str | Path,
    *,
    source_id: str | None = None,
) -> VolumetricGrid:
    """Parse CHGCAR into canonical electron-number-density grid state."""
    try:
        from pymatgen.io.vasp.outputs import Chgcar
    except ImportError as exc:
        raise _backend_import_error(exc) from exc

    try:
        parsed = Chgcar.from_file(path)
    except Exception as exc:
        raise ElectronicStructureIOError(
            "failed to parse CHGCAR with pymatgen-core"
        ) from exc
    return _convert_chgcar_result(parsed, path=path, source_id=source_id)


__all__ = [
    "ElectronicStructureIOError",
    "read_chgcar_density",
    "read_vasprun_dos",
]
