"""Parser for already-generated standard Henkelman-style Bader ACF.dat results."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from catalysis_workbench.computation import (
    AtomicStructure,
    BaderError,
    BaderResult,
    BaderSiteResult,
)


class BaderIOError(ValueError):
    """Raised when an ACF.dat file violates the reviewed Bader parser contract."""


_FOOTER_PATTERN = re.compile(
    r"^(VACUUM\s+CHARGE|VACUUM\s+VOLUME|NUMBER\s+OF\s+ELECTRONS)\s*:\s*(\S+)\s*$",
    flags=re.IGNORECASE,
)
_EXPECTED_HEADER = ("X", "Y", "Z", "CHARGE", "MIN", "DIST", "ATOMIC", "VOL")


def _parse_float(token: str, *, line_number: int, field: str) -> float:
    try:
        value = float(token.replace("D", "E").replace("d", "e"))
    except ValueError as exc:
        raise BaderIOError(
            f"line {line_number}: {field} must be a finite numeric value"
        ) from exc
    if not np.isfinite(value):
        raise BaderIOError(f"line {line_number}: {field} must be finite")
    return value


def _parse_source_index(token: str, *, line_number: int) -> int:
    try:
        value = int(token)
    except ValueError as exc:
        raise BaderIOError(f"line {line_number}: source atom index must be an integer") from exc
    if value <= 0:
        raise BaderIOError(f"line {line_number}: source atom index must be positive")
    return value


def _parse_header(line: str, *, line_number: int) -> None:
    tokens = tuple(line.lstrip("#").strip().upper().split())
    if tokens != _EXPECTED_HEADER:
        raise BaderIOError(
            f"line {line_number}: expected standard ACF header "
            "'# X Y Z CHARGE MIN DIST ATOMIC VOL'"
        )


def _validated_mapping_tolerance(value: object | None) -> float:
    if value is None:
        raise BaderIOError(
            "position_tolerance_angstrom is required when structure mapping is requested"
        )
    try:
        tolerance = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError("position_tolerance_angstrom must be a finite positive float") from exc
    if not np.isfinite(tolerance) or tolerance <= 0:
        raise BaderIOError("position_tolerance_angstrom must be finite and greater than zero")
    return tolerance


def read_bader_acf(
    path: str | Path,
    *,
    structure: AtomicStructure | None = None,
    position_tolerance_angstrom: float | None = None,
    source_id: str | None = None,
) -> BaderResult:
    """Parse standard ACF.dat state without running or discovering a Bader executable."""
    source_path = Path(path)
    try:
        lines = source_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise BaderIOError(f"could not read Bader ACF file: {source_path}") from exc

    if structure is not None and not isinstance(structure, AtomicStructure):
        raise TypeError("structure must be an AtomicStructure when supplied")
    if structure is None and position_tolerance_angstrom is not None:
        raise BaderIOError(
            "position_tolerance_angstrom has no meaning without an AtomicStructure"
        )
    tolerance = (
        _validated_mapping_tolerance(position_tolerance_angstrom)
        if structure is not None
        else None
    )

    header_seen = False
    raw_sites: list[BaderSiteResult] = []
    footer_values: dict[str, float] = {}
    footer_started = False

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue
        if set(line) == {"-"}:
            continue
        if line.startswith("#"):
            if header_seen:
                raise BaderIOError(f"line {line_number}: duplicate ACF header/comment")
            _parse_header(line, line_number=line_number)
            header_seen = True
            continue

        footer_match = _FOOTER_PATTERN.match(line)
        if footer_match:
            if not header_seen or not raw_sites:
                raise BaderIOError(f"line {line_number}: footer appears before atom rows")
            footer_started = True
            key = " ".join(footer_match.group(1).upper().split())
            if key in footer_values:
                raise BaderIOError(f"line {line_number}: duplicate footer field {key}")
            footer_values[key] = _parse_float(
                footer_match.group(2),
                line_number=line_number,
                field=key,
            )
            continue

        if not header_seen:
            raise BaderIOError(f"line {line_number}: atom data appears before standard header")
        if footer_started:
            raise BaderIOError(f"line {line_number}: atom row appears after ACF footer")

        tokens = line.split()
        if len(tokens) != 7:
            raise BaderIOError(
                f"line {line_number}: standard ACF atom row must contain exactly 7 columns"
            )
        source_index = _parse_source_index(tokens[0], line_number=line_number)
        values = [
            _parse_float(token, line_number=line_number, field=field)
            for token, field in zip(
                tokens[1:],
                ("X", "Y", "Z", "CHARGE", "MIN DIST", "ATOMIC VOL"),
                strict=True,
            )
        ]
        try:
            raw_sites.append(
                BaderSiteResult(
                    source_atom_index=source_index,
                    cartesian_position_angstrom=values[:3],
                    bader_electrons=values[3],
                    min_distance_angstrom=values[4],
                    atomic_volume_angstrom3=values[5],
                )
            )
        except (BaderError, TypeError) as exc:
            raise BaderIOError(f"line {line_number}: invalid Bader atom row") from exc

    if not header_seen:
        raise BaderIOError("standard ACF header was not found")
    if not raw_sites:
        raise BaderIOError("ACF file contains no atom rows")
    expected_indices = tuple(range(1, len(raw_sites) + 1))
    actual_indices = tuple(site.source_atom_index for site in raw_sites)
    if actual_indices != expected_indices:
        raise BaderIOError("ACF source atom indices must be the ordered standard sequence 1..N")

    sites: tuple[BaderSiteResult, ...]
    structure_digest = None
    if structure is None:
        sites = tuple(raw_sites)
    else:
        if structure.site_count != len(raw_sites):
            raise BaderIOError("ACF atom count does not match AtomicStructure site count")
        mapped: list[BaderSiteResult] = []
        for site_index, (raw_site, structure_position) in enumerate(
            zip(raw_sites, structure.cartesian_coordinates, strict=True)
        ):
            if not np.allclose(
                raw_site.cartesian_position_angstrom,
                structure_position,
                rtol=0.0,
                atol=tolerance,
            ):
                raise BaderIOError(
                    "ACF Cartesian positions do not match AtomicStructure in direct site order "
                    f"within {tolerance:g} angstrom at source atom {raw_site.source_atom_index}"
                )
            mapped.append(
                BaderSiteResult(
                    source_atom_index=raw_site.source_atom_index,
                    cartesian_position_angstrom=raw_site.cartesian_position_angstrom,
                    bader_electrons=raw_site.bader_electrons,
                    min_distance_angstrom=raw_site.min_distance_angstrom,
                    atomic_volume_angstrom3=raw_site.atomic_volume_angstrom3,
                    site_index=site_index,
                    site_key=structure.site_keys[site_index],
                )
            )
        sites = tuple(mapped)
        structure_digest = structure.digest

    try:
        return BaderResult(
            sites=sites,
            vacuum_charge_electrons=footer_values.get("VACUUM CHARGE"),
            vacuum_volume_angstrom3=footer_values.get("VACUUM VOLUME"),
            number_of_electrons=footer_values.get("NUMBER OF ELECTRONS"),
            structure_digest=structure_digest,
            position_tolerance_angstrom=tolerance,
            source_format="ACF.dat",
            source_path=str(source_path),
            source_id=source_id,
        )
    except (BaderError, TypeError) as exc:
        raise BaderIOError("parsed ACF state violates the Bader result contract") from exc


__all__ = ["BaderIOError", "read_bader_acf"]
