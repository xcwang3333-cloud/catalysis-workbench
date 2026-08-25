"""Lazy pymatgen-core adapters for reviewed LOBSTER COHP/ICOHP results."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from catalysis_workbench.computation.bonding import (
    COHPChannel,
    COHPResult,
    ICOHPBondSummary,
    ICOHPResult,
    BondingError,
)
from catalysis_workbench.computation.electronic_structure import (
    ElectronicEnergyAxis,
    ElectronicStructureError,
)


class LobsterIOError(ValueError):
    """Raised when LOBSTER output violates the reviewed adapter contract."""


def _backend_import_error(exc: ImportError) -> LobsterIOError:
    return LobsterIOError(
        "LOBSTER adapters require the optional dependency; install "
        "catalysis-workbench[structure]"
    )


def _required_text(value: object, *, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise LobsterIOError(f"{name} must not be blank")
    return text


def _source_id(value: str | None) -> str | None:
    if value is None:
        return None
    return _required_text(value, name="source_id")


def _reject_non_cohp_variant(parsed: Any) -> None:
    flags = {
        "COOP": bool(getattr(parsed, "are_coops", False)),
        "COBI": bool(getattr(parsed, "are_cobis", False)),
        "multi-center COBI": bool(getattr(parsed, "are_multi_center_cobis", False)),
        "LCFO": bool(getattr(parsed, "is_lcfo", False)),
    }
    rejected = [name for name, enabled in flags.items() if enabled]
    if rejected:
        raise LobsterIOError(
            "v0.6 block 5 accepts only standard COHP/ICOHP output; unsupported variant: "
            + ", ".join(rejected)
        )


def _spin_token(value: object) -> str:
    name = getattr(value, "name", None)
    if name is not None:
        text = str(name).strip().lower()
        if text in {"up", "down"}:
            return text
    raw_value = getattr(value, "value", None)
    if raw_value == 1:
        return "up"
    if raw_value == -1:
        return "down"
    text = str(value).strip().lower()
    if text in {"1", "spin.up", "up"}:
        return "up"
    if text in {"-1", "spin.down", "down"}:
        return "down"
    raise LobsterIOError(f"unsupported LOBSTER spin identity {value!r}")


def _physical_spin_items(
    values: object,
    *,
    spin_polarized: bool,
    name: str,
) -> tuple[tuple[str, object], ...]:
    try:
        items = tuple(dict(values).items())
    except (TypeError, ValueError) as exc:
        raise LobsterIOError(f"{name} must be a spin-to-value mapping") from exc
    if not items:
        raise LobsterIOError(f"{name} must not be empty")
    if not spin_polarized:
        if len(items) != 1:
            raise LobsterIOError(f"non-spin {name} must contain exactly one backend channel")
        return (("total", items[0][1]),)
    mapped: dict[str, object] = {}
    for raw_spin, raw_values in items:
        spin = _spin_token(raw_spin)
        if spin in mapped:
            raise LobsterIOError(f"{name} contains duplicate {spin} state")
        mapped[spin] = raw_values
    if set(mapped) != {"up", "down"}:
        raise LobsterIOError(f"spin-polarized {name} must contain both up and down")
    return (("up", mapped["up"]), ("down", mapped["down"]))


def _site_indices(values: object | None) -> tuple[int, ...]:
    if values is None:
        return ()
    try:
        items = tuple(values)  # type: ignore[arg-type]
    except TypeError as exc:
        raise LobsterIOError("LOBSTER bond sites must be iterable") from exc
    result: list[int] = []
    for value in items:
        raw = getattr(value, "index", value)
        if isinstance(raw, bool):
            raise LobsterIOError("LOBSTER bond site indices must be integers")
        try:
            index = int(raw)
        except (TypeError, ValueError) as exc:
            raise LobsterIOError("LOBSTER bond site indices must be integers") from exc
        if index < 0:
            raise LobsterIOError("LOBSTER bond site indices must be non-negative")
        result.append(index)
    if result and len(result) != 2:
        raise LobsterIOError("standard two-center COHP bonds must expose exactly two sites")
    return tuple(result)


def _orbital_descriptors(values: object) -> tuple[str, ...]:
    if isinstance(values, str):
        return (_required_text(values, name="orbital descriptor"),)
    try:
        items = tuple(values)  # type: ignore[arg-type]
    except TypeError:
        items = (values,)
    descriptors = tuple(_required_text(item, name="orbital descriptor") for item in items)
    if not descriptors:
        raise LobsterIOError("orbital descriptors must not be empty")
    return descriptors


def _bond_length(data: Mapping[str, object]) -> float | None:
    value = data.get("length")
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise LobsterIOError("LOBSTER bond length must be numeric") from exc
    if not np.isfinite(result) or result <= 0:
        raise LobsterIOError("LOBSTER bond length must be finite and greater than zero")
    return result


def _bond_data_mapping(parsed: Any) -> tuple[tuple[str, Mapping[str, object]], ...]:
    raw = getattr(parsed, "cohp_data", None)
    try:
        items = tuple(dict(raw).items())
    except (TypeError, ValueError) as exc:
        raise LobsterIOError("Cohpcar backend does not expose cohp_data mapping") from exc
    concrete: list[tuple[str, Mapping[str, object]]] = []
    for raw_label, raw_data in items:
        label = _required_text(raw_label, name="COHP source label")
        if label.lower() == "average":
            continue
        if not isinstance(raw_data, Mapping):
            raise LobsterIOError("COHP bond data must be mapping-like")
        concrete.append((label, raw_data))
    if not concrete:
        raise LobsterIOError("COHPCAR contains no concrete bond entries")
    labels = tuple(label for label, _ in concrete)
    if len(set(labels)) != len(labels):
        raise LobsterIOError("COHP source labels must be unique")
    return tuple(concrete)


def _channel_pairs(
    data: Mapping[str, object],
    *,
    spin_polarized: bool,
) -> tuple[tuple[str, object, object], ...]:
    cohp_items = _physical_spin_items(
        data.get("COHP"),
        spin_polarized=spin_polarized,
        name="COHP",
    )
    icohp_items = _physical_spin_items(
        data.get("ICOHP"),
        spin_polarized=spin_polarized,
        name="integrated COHP",
    )
    icohp_map = dict(icohp_items)
    if tuple(spin for spin, _ in cohp_items) != tuple(spin for spin, _ in icohp_items):
        raise LobsterIOError("COHP and integrated COHP spin identities must match")
    return tuple((spin, values, icohp_map[spin]) for spin, values in cohp_items)


def _convert_cohpcar(
    parsed: Any,
    *,
    path: str | Path,
    source_id: str | None,
) -> COHPResult:
    _reject_non_cohp_variant(parsed)
    try:
        energies = np.asarray(parsed.energies, dtype=np.float64)
        producer_fermi = float(parsed.efermi)
        spin_polarized = bool(parsed.is_spin_polarized)
    except (AttributeError, TypeError, ValueError) as exc:
        raise LobsterIOError("Cohpcar backend does not expose valid energy/Fermi/spin state") from exc
    if not np.isfinite(producer_fermi):
        raise LobsterIOError("LOBSTER producer Fermi value must be finite")

    channels: list[COHPChannel] = []
    concrete = _bond_data_mapping(parsed)
    for label, data in concrete:
        bond_key = f"bond:{label}"
        length = _bond_length(data)
        sites = _site_indices(data.get("sites"))
        for spin, cohp, integrated in _channel_pairs(data, spin_polarized=spin_polarized):
            channels.append(
                COHPChannel(
                    key=f"{bond_key}:spin:{spin}",
                    bond_key=bond_key,
                    source_label=label,
                    spin=spin,
                    cohp=cohp,
                    integrated_cohp=integrated,
                    bond_length_angstrom=length,
                    source_site_indices=sites,
                )
            )

    orbital_state = getattr(parsed, "orb_res_cohp", None)
    if orbital_state:
        try:
            orbital_bonds = dict(orbital_state)
        except (TypeError, ValueError) as exc:
            raise LobsterIOError("orb_res_cohp must be mapping-like") from exc
        concrete_labels = {label for label, _ in concrete}
        for raw_label, raw_orbitals in orbital_bonds.items():
            label = _required_text(raw_label, name="orbital-resolved bond label")
            if label not in concrete_labels:
                raise LobsterIOError(
                    "orbital-resolved COHP label does not match a concrete bond entry"
                )
            try:
                orbital_items = tuple(dict(raw_orbitals).items())
            except (TypeError, ValueError) as exc:
                raise LobsterIOError("orbital-resolved COHP state must be mapping-like") from exc
            bond_key = f"bond:{label}"
            for raw_orbital_label, raw_data in orbital_items:
                orbital_label = _required_text(raw_orbital_label, name="orbital label")
                if not isinstance(raw_data, Mapping):
                    raise LobsterIOError("orbital-resolved COHP data must be mapping-like")
                descriptors = _orbital_descriptors(raw_data.get("orbitals"))
                orbital_key = f"orbital:{orbital_label}"
                length = _bond_length(raw_data)
                sites = _site_indices(raw_data.get("sites"))
                for spin, cohp, integrated in _channel_pairs(
                    raw_data,
                    spin_polarized=spin_polarized,
                ):
                    channels.append(
                        COHPChannel(
                            key=f"{bond_key}:{orbital_key}:spin:{spin}",
                            bond_key=bond_key,
                            source_label=label,
                            spin=spin,
                            cohp=cohp,
                            integrated_cohp=integrated,
                            bond_length_angstrom=length,
                            source_site_indices=sites,
                            orbital_key=orbital_key,
                            orbital_label=orbital_label,
                            orbital_descriptors=descriptors,
                        )
                    )

    try:
        return COHPResult(
            energy=ElectronicEnergyAxis(
                energies,
                reference_kind="fermi",
                source_fermi_ev=0.0,
                applied_shift_ev=0.0,
            ),
            channels=channels,
            producer_fermi_ev=producer_fermi,
            source_format="COHPCAR.lobster",
            source_path=str(Path(path)),
            source_id=_source_id(source_id),
        )
    except (BondingError, ElectronicStructureError, TypeError, ValueError) as exc:
        raise LobsterIOError("parsed COHPCAR violates the bonding-state contract") from exc


def read_lobster_cohp(
    path: str | Path,
    *,
    source_id: str | None = None,
) -> COHPResult:
    """Parse standard LOBSTER COHPCAR without changing source sign or Fermi reference."""
    try:
        from pymatgen.io.lobster import Cohpcar
    except ImportError as exc:
        raise _backend_import_error(exc) from exc
    try:
        parsed = Cohpcar(filename=path)
    except Exception as exc:
        raise LobsterIOError(f"failed to parse COHPCAR: {exc}") from exc
    return _convert_cohpcar(parsed, path=path, source_id=source_id)


def _icohp_mapping(parsed: Any) -> tuple[tuple[str, Mapping[str, object]], ...]:
    raw = getattr(parsed, "icohplist", None)
    try:
        items = tuple(dict(raw).items())
    except (TypeError, ValueError) as exc:
        raise LobsterIOError("Icohplist backend does not expose icohplist mapping") from exc
    result: list[tuple[str, Mapping[str, object]]] = []
    for raw_label, raw_data in items:
        label = _required_text(raw_label, name="ICOHP source label")
        if not isinstance(raw_data, Mapping):
            raise LobsterIOError("ICOHP bond data must be mapping-like")
        result.append((label, raw_data))
    if not result:
        raise LobsterIOError("ICOHPLIST contains no bond entries")
    labels = tuple(label for label, _ in result)
    if len(set(labels)) != len(labels):
        raise LobsterIOError("ICOHP source labels must be unique")
    return tuple(result)


def _convert_icohplist(
    parsed: Any,
    *,
    path: str | Path,
    source_id: str | None,
) -> ICOHPResult:
    _reject_non_cohp_variant(parsed)
    spin_polarized = bool(getattr(parsed, "is_spin_polarized", False))
    bonds: list[ICOHPBondSummary] = []
    for label, data in _icohp_mapping(parsed):
        length = _bond_length(data)
        if length is None:
            raise LobsterIOError("ICOHP bond length is required for standard ICOHPLIST")
        raw_count = data.get("number_of_bonds")
        if isinstance(raw_count, bool):
            raise LobsterIOError("number_of_bonds must be an integer")
        try:
            number_of_bonds = int(raw_count)  # type: ignore[arg-type]
        except (TypeError, ValueError) as exc:
            raise LobsterIOError("number_of_bonds must be an integer") from exc
        if number_of_bonds <= 0:
            raise LobsterIOError("number_of_bonds must be greater than zero")
        spin_items = _physical_spin_items(
            data.get("icohp"),
            spin_polarized=spin_polarized,
            name="ICOHP(E_F)",
        )
        values: dict[str, float] = {}
        for spin, raw_value in spin_items:
            try:
                value = float(raw_value)
            except (TypeError, ValueError) as exc:
                raise LobsterIOError("ICOHP(E_F) values must be numeric") from exc
            if not np.isfinite(value):
                raise LobsterIOError("ICOHP(E_F) values must be finite")
            values[spin] = value
        bonds.append(
            ICOHPBondSummary(
                bond_key=f"bond:{label}",
                source_label=label,
                bond_length_angstrom=length,
                number_of_bonds=number_of_bonds,
                icohp_by_spin=values,
            )
        )
    try:
        return ICOHPResult(
            bonds=bonds,
            source_format="ICOHPLIST.lobster",
            source_path=str(Path(path)),
            source_id=_source_id(source_id),
        )
    except (BondingError, TypeError, ValueError) as exc:
        raise LobsterIOError("parsed ICOHPLIST violates the bonding-state contract") from exc


def read_lobster_icohp(
    path: str | Path,
    *,
    source_id: str | None = None,
) -> ICOHPResult:
    """Parse standard LOBSTER ICOHPLIST with source-sign spin-resolved values."""
    try:
        from pymatgen.io.lobster import Icohplist
    except ImportError as exc:
        raise _backend_import_error(exc) from exc
    try:
        parsed = Icohplist(filename=path)
    except Exception as exc:
        raise LobsterIOError(f"failed to parse ICOHPLIST: {exc}") from exc
    return _convert_icohplist(parsed, path=path, source_id=source_id)
