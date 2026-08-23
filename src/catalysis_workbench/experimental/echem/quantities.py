"""Shared electrochemistry quantity, unit, and reference conventions.

The v0.2 electrochemistry layer intentionally uses explicit string units rather than a
full unit registry. These helpers provide conservative conversions for the quantities
needed by the reviewed electrochemistry roadmap while refusing ambiguous or missing
units.
"""

from __future__ import annotations

from math import isfinite, pi
from typing import Any

import numpy as np
from numpy.typing import ArrayLike

FARADAY_CONSTANT_C_MOL = 96485.33212
GAS_CONSTANT_J_MOL_K = 8.31446261815324


class EchemQuantityError(ValueError):
    """Raised when an electrochemical quantity or unit is invalid or ambiguous."""


def normalize_unit(unit: str | None) -> str:
    """Return a conservative comparison token for an explicit unit string."""
    if unit is None or not str(unit).strip():
        raise EchemQuantityError("electrochemical unit is required")
    compact = str(unit).strip().casefold()
    compact = compact.replace("µ", "u").replace("μ", "u")
    compact = compact.replace("⁻²", "^-2").replace("⁻¹", "^-1")
    compact = compact.replace("−", "-").replace("⁻", "-")
    compact = compact.replace("²", "^2").replace("¹", "^1")
    compact = compact.replace("·", "").replace("*", "").replace(" ", "")
    compact = compact.replace("^-2", "-2").replace("^-1", "-1")
    compact = compact.replace("^2", "2").replace("^1", "1")
    return compact


def require_real(
    values: ArrayLike | float,
    *,
    quantity: str,
    allow_nan: bool = True,
) -> np.ndarray:
    """Return real float64 values after rejecting complex and infinite inputs."""
    array = np.asarray(values)
    if np.iscomplexobj(array):
        raise EchemQuantityError(f"{quantity} must be real-valued")
    real = array.astype(np.float64, copy=False)
    if np.isinf(real).any():
        raise EchemQuantityError(f"{quantity} must not contain +/-inf")
    if not allow_nan and np.isnan(real).any():
        raise EchemQuantityError(f"{quantity} must not contain missing values")
    return real


def positive_finite(value: Any, *, name: str) -> float:
    """Return a positive finite scalar."""
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise EchemQuantityError(f"{name} must be a real numeric value") from exc
    if not isfinite(numeric) or numeric <= 0:
        raise EchemQuantityError(f"{name} must be finite and greater than zero")
    return numeric


def nonnegative_finite(value: Any, *, name: str) -> float:
    """Return a non-negative finite scalar."""
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise EchemQuantityError(f"{name} must be a real numeric value") from exc
    if not isfinite(numeric) or numeric < 0:
        raise EchemQuantityError(f"{name} must be finite and non-negative")
    return numeric


def electron_number(value: Any) -> int:
    """Validate an explicit positive integer electron stoichiometry."""
    if isinstance(value, bool):
        raise EchemQuantityError("electron_number must be a positive integer")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise EchemQuantityError("electron_number must be a positive integer") from exc
    if not isfinite(numeric) or numeric <= 0 or not numeric.is_integer():
        raise EchemQuantityError("electron_number must be a positive integer")
    return int(numeric)


def normalize_reference_name(reference: str) -> str:
    """Normalize whitespace while preserving the caller's reference-electrode name."""
    name = " ".join(str(reference).split())
    if not name:
        raise EchemQuantityError("reference must not be empty")
    return name


def same_reference(left: str, right: str) -> bool:
    """Compare two explicit reference-electrode names case-insensitively."""
    left_name = normalize_reference_name(left).casefold()
    right_name = normalize_reference_name(right).casefold()
    return left_name == right_name


def _expanded_units(
    entries: dict[str, tuple[float, str]],
) -> dict[str, tuple[float, str]]:
    return {normalize_unit(unit): value for unit, value in entries.items()}


_POTENTIAL = _expanded_units(
    {
        "V": (1.0, "V"),
        "mV": (1e-3, "mV"),
    }
)
_CURRENT = _expanded_units(
    {
        "A": (1.0, "A"),
        "mA": (1e-3, "mA"),
        "uA": (1e-6, "uA"),
    }
)
_CURRENT_DENSITY = _expanded_units(
    {
        "A/cm^2": (1.0, "A/cm^2"),
        "A/cm2": (1.0, "A/cm^2"),
        "A cm^-2": (1.0, "A/cm^2"),
        "A cm-2": (1.0, "A/cm^2"),
        "mA/cm^2": (1e-3, "mA/cm^2"),
        "mA/cm2": (1e-3, "mA/cm^2"),
        "mA cm^-2": (1e-3, "mA/cm^2"),
        "mA cm-2": (1e-3, "mA/cm^2"),
        "uA/cm^2": (1e-6, "uA/cm^2"),
        "uA/cm2": (1e-6, "uA/cm^2"),
        "uA cm^-2": (1e-6, "uA/cm^2"),
        "uA cm-2": (1e-6, "uA/cm^2"),
    }
)
_CHARGE = _expanded_units(
    {
        "C": (1.0, "C"),
        "mC": (1e-3, "mC"),
        "uC": (1e-6, "uC"),
        "Ah": (3600.0, "Ah"),
        "mAh": (3.6, "mAh"),
        "uAh": (3.6e-3, "uAh"),
    }
)
_TIME = _expanded_units(
    {
        "s": (1.0, "s"),
        "min": (60.0, "min"),
        "h": (3600.0, "h"),
    }
)
_SCAN_RATE = _expanded_units(
    {
        "V/s": (1.0, "V/s"),
        "mV/s": (1e-3, "mV/s"),
        "V/min": (1.0 / 60.0, "V/min"),
        "mV/min": (1e-3 / 60.0, "mV/min"),
    }
)
_AREA = _expanded_units(
    {
        "cm^2": (1.0, "cm^2"),
        "cm2": (1.0, "cm^2"),
        "mm^2": (1e-2, "mm^2"),
        "mm2": (1e-2, "mm^2"),
        "m^2": (1e4, "m^2"),
        "m2": (1e4, "m^2"),
    }
)
_MASS = _expanded_units(
    {
        "kg": (1e3, "kg"),
        "g": (1.0, "g"),
        "mg": (1e-3, "mg"),
        "ug": (1e-6, "ug"),
    }
)
_LOADING = _expanded_units(
    {
        "g/cm^2": (1.0, "g/cm^2"),
        "g/cm2": (1.0, "g/cm^2"),
        "g cm^-2": (1.0, "g/cm^2"),
        "mg/cm^2": (1e-3, "mg/cm^2"),
        "mg/cm2": (1e-3, "mg/cm^2"),
        "mg cm^-2": (1e-3, "mg/cm^2"),
        "ug/cm^2": (1e-6, "ug/cm^2"),
        "ug/cm2": (1e-6, "ug/cm^2"),
        "ug cm^-2": (1e-6, "ug/cm^2"),
    }
)
_AMOUNT = _expanded_units(
    {
        "mol": (1.0, "mol"),
        "mmol": (1e-3, "mmol"),
        "umol": (1e-6, "umol"),
        "nmol": (1e-9, "nmol"),
    }
)
_MOLAR_RATE = _expanded_units(
    {
        "mol/s": (1.0, "mol/s"),
        "mmol/s": (1e-3, "mmol/s"),
        "umol/s": (1e-6, "umol/s"),
        "nmol/s": (1e-9, "nmol/s"),
        "mol/min": (1.0 / 60.0, "mol/min"),
        "mmol/min": (1e-3 / 60.0, "mmol/min"),
        "umol/min": (1e-6 / 60.0, "umol/min"),
        "nmol/min": (1e-9 / 60.0, "nmol/min"),
    }
)
_ROTATION_RATE = _expanded_units(
    {
        "rad/s": (1.0, "rad/s"),
        "rpm": (2.0 * pi / 60.0, "rpm"),
        "rps": (2.0 * pi, "rps"),
    }
)


def _convert(
    values: ArrayLike | float,
    unit: str | None,
    table: dict[str, tuple[float, str]],
    *,
    quantity: str,
    allow_nan: bool,
) -> np.ndarray:
    token = normalize_unit(unit)
    try:
        factor, _ = table[token]
    except KeyError as exc:
        supported = ", ".join(dict.fromkeys(entry[1] for entry in table.values()))
        raise EchemQuantityError(
            f"unsupported {quantity} unit {unit!r}; supported units: {supported}"
        ) from exc
    return require_real(values, quantity=quantity, allow_nan=allow_nan) * factor


def _canonical(
    unit: str | None,
    table: dict[str, tuple[float, str]],
    *,
    quantity: str,
) -> str:
    token = normalize_unit(unit)
    try:
        return table[token][1]
    except KeyError as exc:
        supported = ", ".join(dict.fromkeys(entry[1] for entry in table.values()))
        raise EchemQuantityError(
            f"unsupported {quantity} unit {unit!r}; supported units: {supported}"
        ) from exc


def _is_unit(unit: str | None, table: dict[str, tuple[float, str]]) -> bool:
    try:
        token = normalize_unit(unit)
    except EchemQuantityError:
        return False
    return token in table


def potential_to_v(
    values: ArrayLike | float,
    unit: str | None,
    *,
    allow_nan: bool = False,
) -> np.ndarray:
    """Convert explicit potential values to volts."""
    return _convert(values, unit, _POTENTIAL, quantity="potential", allow_nan=allow_nan)


def current_to_a(
    values: ArrayLike | float,
    unit: str | None,
    *,
    allow_nan: bool = True,
) -> np.ndarray:
    """Convert explicit total-current values to amperes."""
    return _convert(values, unit, _CURRENT, quantity="current", allow_nan=allow_nan)


def current_density_to_a_cm2(
    values: ArrayLike | float,
    unit: str | None,
    *,
    allow_nan: bool = True,
) -> np.ndarray:
    """Convert explicit current-density values to A/cm^2."""
    return _convert(
        values,
        unit,
        _CURRENT_DENSITY,
        quantity="current density",
        allow_nan=allow_nan,
    )


def current_density_from_a_cm2(
    values: ArrayLike | float,
    output_unit: str,
) -> np.ndarray:
    """Convert A/cm^2 values to one supported current-density display unit."""
    token = normalize_unit(output_unit)
    try:
        factor, _ = _CURRENT_DENSITY[token]
    except KeyError as exc:
        raise EchemQuantityError(
            "output_unit must be A/cm^2, mA/cm^2, or uA/cm^2"
        ) from exc
    return require_real(values, quantity="current density", allow_nan=True) / factor


def canonical_current_density_unit(unit: str | None) -> str:
    """Return the canonical spelling of a supported current-density unit."""
    return _canonical(unit, _CURRENT_DENSITY, quantity="current density")


def is_current_unit(unit: str | None) -> bool:
    """Return whether a unit is an explicitly supported total-current unit."""
    return _is_unit(unit, _CURRENT)


def is_current_density_unit(unit: str | None) -> bool:
    """Return whether a unit is an explicitly supported current-density unit."""
    return _is_unit(unit, _CURRENT_DENSITY)


def charge_to_c(
    values: ArrayLike | float,
    unit: str | None,
    *,
    allow_nan: bool = False,
) -> np.ndarray:
    """Convert charge to coulombs."""
    return _convert(values, unit, _CHARGE, quantity="charge", allow_nan=allow_nan)


def time_to_s(
    values: ArrayLike | float,
    unit: str | None,
    *,
    allow_nan: bool = False,
) -> np.ndarray:
    """Convert time to seconds."""
    return _convert(values, unit, _TIME, quantity="time", allow_nan=allow_nan)


def scan_rate_to_v_s(
    values: ArrayLike | float,
    unit: str | None,
    *,
    allow_nan: bool = False,
) -> np.ndarray:
    """Convert potential scan rate to V/s."""
    return _convert(
        values,
        unit,
        _SCAN_RATE,
        quantity="scan rate",
        allow_nan=allow_nan,
    )


def area_to_cm2(
    values: ArrayLike | float,
    unit: str | None,
    *,
    allow_nan: bool = False,
) -> np.ndarray:
    """Convert electrode/surface area to cm^2."""
    return _convert(values, unit, _AREA, quantity="area", allow_nan=allow_nan)


def mass_to_g(
    values: ArrayLike | float,
    unit: str | None,
    *,
    allow_nan: bool = False,
) -> np.ndarray:
    """Convert catalyst/metal mass to grams."""
    return _convert(values, unit, _MASS, quantity="mass", allow_nan=allow_nan)


def loading_to_g_cm2(
    values: ArrayLike | float,
    unit: str | None,
    *,
    allow_nan: bool = False,
) -> np.ndarray:
    """Convert catalyst/metal areal loading to g/cm^2."""
    return _convert(values, unit, _LOADING, quantity="loading", allow_nan=allow_nan)


def amount_to_mol(
    values: ArrayLike | float,
    unit: str | None,
    *,
    allow_nan: bool = False,
) -> np.ndarray:
    """Convert amount of substance to moles."""
    return _convert(values, unit, _AMOUNT, quantity="amount", allow_nan=allow_nan)


def molar_rate_to_mol_s(
    values: ArrayLike | float,
    unit: str | None,
    *,
    allow_nan: bool = False,
) -> np.ndarray:
    """Convert molar production/consumption rate to mol/s."""
    return _convert(
        values,
        unit,
        _MOLAR_RATE,
        quantity="molar rate",
        allow_nan=allow_nan,
    )


def rotation_rate_to_rad_s(
    values: ArrayLike | float,
    unit: str | None,
    *,
    allow_nan: bool = False,
) -> np.ndarray:
    """Convert rotation rate to angular velocity in rad/s."""
    return _convert(
        values,
        unit,
        _ROTATION_RATE,
        quantity="rotation rate",
        allow_nan=allow_nan,
    )
