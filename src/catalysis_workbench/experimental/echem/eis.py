"""Explicit EIS semantics, circuit evaluation, constrained fitting, and diagnostics."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from math import isfinite
from types import MappingProxyType
from typing import Literal, TypeAlias

import numpy as np
from numpy.typing import ArrayLike, NDArray

from catalysis_workbench.core import Series

from .provenance import series_data_sha256

EISDirection: TypeAlias = Literal["ascending", "descending"]
EISWeightingMode: TypeAlias = Literal["uniform", "explicit"]

_KEY_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
_PARAMETER_KEY_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_]*\.[A-Za-z][A-Za-z0-9_]*")
_POSITIVE_FLOOR = np.nextafter(0.0, 1.0)


class EISError(ValueError):
    """Raised when EIS scientific state is invalid or incompatible."""


def _finite_float(value: object, *, name: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise TypeError(f"{name} must be a real numeric value")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a real numeric value") from exc
    if not isfinite(number):
        raise EISError(f"{name} must be finite")
    return number


def _immutable_float_array(values: ArrayLike, *, name: str) -> NDArray[np.float64]:
    source = np.asarray(values)
    if source.ndim != 1 or source.size == 0:
        raise EISError(f"{name} must be a non-empty one-dimensional array")
    if np.iscomplexobj(source):
        raise EISError(f"{name} must be real-valued")
    array = np.ascontiguousarray(source, dtype=np.float64)
    if not np.isfinite(array).all():
        raise EISError(f"{name} must contain only finite values")
    output = np.frombuffer(array.tobytes(order="C"), dtype=np.float64)
    output.setflags(write=False)
    return output


def _immutable_complex_array(values: ArrayLike, *, name: str) -> NDArray[np.complex128]:
    source = np.asarray(values)
    if source.ndim != 1 or source.size == 0:
        raise EISError(f"{name} must be a non-empty one-dimensional array")
    if not np.iscomplexobj(source):
        raise EISError(f"{name} must be complex-valued")
    array = np.ascontiguousarray(source, dtype=np.complex128)
    if not np.isfinite(array.real).all() or not np.isfinite(array.imag).all():
        raise EISError(f"{name} must contain only finite complex values")
    output = np.frombuffer(array.tobytes(order="C"), dtype=np.complex128)
    output.setflags(write=False)
    return output


def _semantic_token(value: str) -> str:
    return "".join(character for character in value.strip().casefold() if character.isalnum())


def _is_frequency_unit(value: str | None) -> bool:
    if value is None:
        return False
    return _semantic_token(value) in {"hz", "hertz"}


def _is_impedance_unit(value: str | None) -> bool:
    if value is None:
        return False
    text = value.strip()
    return text in {"Ω", "Ω"} or _semantic_token(text) in {"ohm", "ohms"}


def _direction(frequency: NDArray[np.float64]) -> EISDirection:
    delta = np.diff(frequency)
    if np.all(delta > 0):
        return "ascending"
    if np.all(delta < 0):
        return "descending"
    raise EISError("EIS frequency must be strictly monotonic")


def _nonnegative_int(value: object, *, name: str) -> int:
    if isinstance(value, (bool, np.bool_)):
        raise TypeError(f"{name} must be a non-negative integer")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a non-negative integer") from exc
    if not isfinite(numeric) or not numeric.is_integer() or numeric < 0:
        raise EISError(f"{name} must be a non-negative integer")
    return int(numeric)


def _normalized_sha256(value: object) -> str:
    if not isinstance(value, str):
        raise EISError("EIS source_sha256 must be a 64-character hexadecimal string")
    sha256 = value.strip().lower()
    if len(sha256) != 64 or any(character not in "0123456789abcdef" for character in sha256):
        raise EISError("EIS source_sha256 must be a 64-character hexadecimal string")
    return sha256


def validate_eis_series(series: Series) -> EISDirection:
    """Validate literal complex impedance stored as ``Z = Z' + j Z''``."""
    if not isinstance(series, Series):
        raise TypeError("EIS data must be a core Series")
    if _semantic_token(series.x_axis.name) not in {"frequency", "freq"}:
        raise EISError("EIS x-axis semantic must be frequency")
    if not _is_frequency_unit(series.x_axis.unit):
        raise EISError("EIS frequency unit must be Hz")
    if _semantic_token(series.y_axis.name) not in {"impedance", "z"}:
        raise EISError("EIS y-axis semantic must be impedance")
    if not _is_impedance_unit(series.y_axis.unit):
        raise EISError("EIS impedance unit must be ohm")

    frequency_source = np.asarray(series.x)
    impedance_source = np.asarray(series.y)
    if np.iscomplexobj(frequency_source):
        raise EISError("EIS frequency must be real-valued")
    if not np.iscomplexobj(impedance_source):
        raise EISError(
            "EIS impedance must be explicitly complex-valued as Z = Z' + j Z''"
        )
    frequency = frequency_source.astype(np.float64, copy=False)
    impedance = impedance_source.astype(np.complex128, copy=False)
    if frequency.size < 2:
        raise EISError("EIS requires at least two measured frequency points")
    if not np.isfinite(frequency).all() or np.any(frequency <= 0):
        raise EISError("EIS frequency must contain only finite positive values")
    if not np.isfinite(impedance.real).all() or not np.isfinite(impedance.imag).all():
        raise EISError("EIS impedance must contain only finite complex values")
    return _direction(frequency)


@dataclass(frozen=True, slots=True)
class EISParameterSpec:
    """Explicit initial/fixed/bounded state for one EIS circuit parameter."""

    value: float
    vary: bool = True
    lower: float | None = None
    upper: float | None = None

    def __post_init__(self) -> None:
        value = _finite_float(self.value, name="EIS parameter value")
        lower = None if self.lower is None else _finite_float(self.lower, name="lower bound")
        upper = None if self.upper is None else _finite_float(self.upper, name="upper bound")
        if lower is not None and upper is not None and lower >= upper:
            raise EISError("EIS parameter lower bound must be smaller than upper bound")
        if lower is not None and value < lower:
            raise EISError("EIS parameter initial value is below its lower bound")
        if upper is not None and value > upper:
            raise EISError("EIS parameter initial value is above its upper bound")
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "vary", bool(self.vary))
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)


def _element_key(value: object) -> str:
    key = str(value).strip()
    if not _KEY_PATTERN.fullmatch(key):
        raise EISError("EIS element key must match [A-Za-z][A-Za-z0-9_]*")
    return key


def _positive_parameter(spec: EISParameterSpec, *, name: str) -> None:
    if not isinstance(spec, EISParameterSpec):
        raise TypeError(f"{name} must be an EISParameterSpec")
    if spec.value <= 0:
        raise EISError(f"{name} initial value must be > 0")
    if spec.lower is not None and spec.lower < 0:
        raise EISError(f"{name} lower bound must be >= 0")
    if spec.upper is not None and spec.upper <= 0:
        raise EISError(f"{name} upper bound must be > 0")


@dataclass(frozen=True, slots=True)
class EISResistor:
    """Ideal resistor, ``Z = R``."""

    key: str
    resistance: EISParameterSpec

    def __post_init__(self) -> None:
        object.__setattr__(self, "key", _element_key(self.key))
        _positive_parameter(self.resistance, name=f"{self.key}.R")


@dataclass(frozen=True, slots=True)
class EISCapacitor:
    """Ideal capacitor, ``Z = 1 / (j 2π f C)``."""

    key: str
    capacitance: EISParameterSpec

    def __post_init__(self) -> None:
        object.__setattr__(self, "key", _element_key(self.key))
        _positive_parameter(self.capacitance, name=f"{self.key}.C")


@dataclass(frozen=True, slots=True)
class EISCPE:
    """Constant-phase element, ``Z = 1 / [Q (j 2π f)^n]``."""

    key: str
    q: EISParameterSpec
    n: EISParameterSpec

    def __post_init__(self) -> None:
        object.__setattr__(self, "key", _element_key(self.key))
        _positive_parameter(self.q, name=f"{self.key}.Q")
        if not isinstance(self.n, EISParameterSpec):
            raise TypeError(f"{self.key}.n must be an EISParameterSpec")
        if not 0 < self.n.value <= 1:
            raise EISError(f"{self.key}.n initial value must be in (0, 1]")
        if self.n.lower is not None and self.n.lower < 0:
            raise EISError(f"{self.key}.n lower bound must be >= 0")
        if self.n.upper is not None and self.n.upper > 1:
            raise EISError(f"{self.key}.n upper bound must be <= 1")


@dataclass(frozen=True, slots=True)
class EISSeriesCircuit:
    """Explicit series composition of two or more circuit nodes."""

    children: tuple[object, ...]

    def __post_init__(self) -> None:
        children = tuple(self.children)
        if len(children) < 2:
            raise EISError("EIS series circuit requires at least two children")
        object.__setattr__(self, "children", children)


@dataclass(frozen=True, slots=True)
class EISParallelCircuit:
    """Explicit parallel composition of two or more circuit nodes."""

    children: tuple[object, ...]

    def __post_init__(self) -> None:
        children = tuple(self.children)
        if len(children) < 2:
            raise EISError("EIS parallel circuit requires at least two children")
        object.__setattr__(self, "children", children)


EISCircuit: TypeAlias = (
    EISResistor | EISCapacitor | EISCPE | EISSeriesCircuit | EISParallelCircuit
)


def _require_circuit(value: object) -> EISCircuit:
    if not isinstance(
        value,
        (EISResistor, EISCapacitor, EISCPE, EISSeriesCircuit, EISParallelCircuit),
    ):
        raise TypeError("circuit children must be EIS circuit nodes")
    return value


def _element_keys(circuit: EISCircuit) -> tuple[str, ...]:
    node = _require_circuit(circuit)
    if isinstance(node, (EISResistor, EISCapacitor, EISCPE)):
        return (node.key,)
    output: list[str] = []
    for child in node.children:
        output.extend(_element_keys(_require_circuit(child)))
    return tuple(output)


def validate_eis_circuit(circuit: EISCircuit) -> tuple[str, ...]:
    """Validate circuit node types and globally unique stable element keys."""
    keys = _element_keys(_require_circuit(circuit))
    if len(set(keys)) != len(keys):
        raise EISError("EIS circuit element keys must be globally unique")
    return keys


@dataclass(frozen=True, slots=True)
class _ParameterDefinition:
    key: str
    spec: EISParameterSpec
    domain_lower: float
    domain_upper: float


def _parameter_definitions(circuit: EISCircuit) -> tuple[_ParameterDefinition, ...]:
    node = _require_circuit(circuit)
    if isinstance(node, EISResistor):
        return (_ParameterDefinition(f"{node.key}.R", node.resistance, _POSITIVE_FLOOR, np.inf),)
    if isinstance(node, EISCapacitor):
        return (
            _ParameterDefinition(f"{node.key}.C", node.capacitance, _POSITIVE_FLOOR, np.inf),
        )
    if isinstance(node, EISCPE):
        return (
            _ParameterDefinition(f"{node.key}.Q", node.q, _POSITIVE_FLOOR, np.inf),
            _ParameterDefinition(f"{node.key}.n", node.n, _POSITIVE_FLOOR, 1.0),
        )
    output: list[_ParameterDefinition] = []
    for child in node.children:
        output.extend(_parameter_definitions(_require_circuit(child)))
    return tuple(output)


def eis_circuit_parameter_keys(circuit: EISCircuit) -> tuple[str, ...]:
    """Return deterministic public ``element.parameter`` keys in circuit order."""
    validate_eis_circuit(circuit)
    return tuple(item.key for item in _parameter_definitions(circuit))


def eis_circuit_element_keys(circuit: EISCircuit) -> tuple[str, ...]:
    """Return deterministic leaf element keys in circuit order."""
    return validate_eis_circuit(circuit)


def _effective_bounds(definition: _ParameterDefinition) -> tuple[float, float]:
    lower = definition.domain_lower
    upper = definition.domain_upper
    if definition.spec.lower is not None:
        lower = max(lower, definition.spec.lower)
    if definition.spec.upper is not None:
        upper = min(upper, definition.spec.upper)
    if lower > upper:
        raise EISError(f"bounds for {definition.key} do not intersect its physical domain")
    if not lower <= definition.spec.value <= upper:
        raise EISError(f"initial value for {definition.key} violates its physical domain")
    return float(lower), float(upper)


def _parameter_values(
    circuit: EISCircuit,
    overrides: Mapping[str, float] | None,
) -> dict[str, float]:
    definitions = _parameter_definitions(circuit)
    values = {item.key: item.spec.value for item in definitions}
    if overrides is None:
        return values
    unknown = set(overrides) - set(values)
    if unknown:
        raise EISError(f"unknown EIS circuit parameter keys: {sorted(unknown)!r}")
    definition_map = {item.key: item for item in definitions}
    for key, raw_value in overrides.items():
        value = _finite_float(raw_value, name=f"parameter {key}")
        definition = definition_map[key]
        lower, upper = _effective_bounds(definition)
        if not lower <= value <= upper:
            raise EISError(f"parameter {key} violates its physical/caller bounds")
        values[key] = value
    return values


def _frequency_vector(values: ArrayLike) -> NDArray[np.float64]:
    source = np.asarray(values)
    if source.ndim != 1 or source.size == 0 or np.iscomplexobj(source):
        raise EISError("circuit evaluation frequency must be a non-empty real 1-D vector")
    frequency = source.astype(np.float64, copy=False)
    if not np.isfinite(frequency).all() or np.any(frequency <= 0):
        raise EISError("circuit evaluation frequency must be finite and > 0 Hz")
    return frequency


def _evaluate_node(
    circuit: EISCircuit,
    frequency: NDArray[np.float64],
    values: Mapping[str, float],
) -> NDArray[np.complex128]:
    node = _require_circuit(circuit)
    omega = 2.0 * np.pi * frequency
    if isinstance(node, EISResistor):
        return np.full(frequency.shape, values[f"{node.key}.R"], dtype=np.complex128)
    if isinstance(node, EISCapacitor):
        capacitance = values[f"{node.key}.C"]
        return np.asarray(1.0 / (1j * omega * capacitance), dtype=np.complex128)
    if isinstance(node, EISCPE):
        q = values[f"{node.key}.Q"]
        exponent = values[f"{node.key}.n"]
        return np.asarray(1.0 / (q * (1j * omega) ** exponent), dtype=np.complex128)
    child_impedances = [
        _evaluate_node(_require_circuit(child), frequency, values) for child in node.children
    ]
    if isinstance(node, EISSeriesCircuit):
        return np.sum(np.stack(child_impedances, axis=0), axis=0, dtype=np.complex128)

    admittance = np.zeros(frequency.shape, dtype=np.complex128)
    for child_impedance in child_impedances:
        if np.any(child_impedance == 0):
            raise EISError("EIS parallel circuit contains zero child impedance")
        candidate = 1.0 / child_impedance
        if not np.isfinite(candidate.real).all() or not np.isfinite(candidate.imag).all():
            raise EISError("EIS parallel circuit produced non-finite admittance")
        admittance += candidate
    if np.any(admittance == 0):
        raise EISError("EIS parallel circuit total admittance is zero")
    result = 1.0 / admittance
    if not np.isfinite(result.real).all() or not np.isfinite(result.imag).all():
        raise EISError("EIS circuit evaluation produced non-finite impedance")
    return result


def evaluate_eis_circuit(
    circuit: EISCircuit,
    frequency_hz: ArrayLike,
    *,
    parameter_values: Mapping[str, float] | None = None,
) -> NDArray[np.complex128]:
    """Evaluate an explicit circuit on the caller frequency vector."""
    validate_eis_circuit(circuit)
    frequency = _frequency_vector(frequency_hz)
    values = _parameter_values(circuit, parameter_values)
    result = _evaluate_node(circuit, frequency, values)
    return _immutable_complex_array(result, name="evaluated EIS impedance")


@dataclass(frozen=True, slots=True)
class EISFitConfig:
    """Explicit deterministic controls for SciPy trust-region least squares."""

    xtol: float = 1e-10
    ftol: float = 1e-10
    gtol: float = 1e-10
    max_nfev: int = 2000

    def __post_init__(self) -> None:
        for name in ("xtol", "ftol", "gtol"):
            value = _finite_float(getattr(self, name), name=name)
            if value <= 0:
                raise EISError(f"{name} must be > 0")
            object.__setattr__(self, name, value)
        if isinstance(self.max_nfev, (bool, np.bool_)):
            raise TypeError("max_nfev must be a positive integer")
        max_nfev = int(self.max_nfev)
        if max_nfev <= 0 or float(self.max_nfev) != max_nfev:
            raise EISError("max_nfev must be a positive integer")
        object.__setattr__(self, "max_nfev", max_nfev)


@dataclass(frozen=True, slots=True)
class EISFittedParameter:
    """Backend-independent fitted state for one public EIS circuit parameter."""

    key: str
    value: float
    vary: bool
    lower: float | None
    upper: float | None

    def __post_init__(self) -> None:
        if not isinstance(self.key, str) or not _PARAMETER_KEY_PATTERN.fullmatch(self.key.strip()):
            raise EISError("EIS fitted-parameter key must use element.parameter syntax")
        key = self.key.strip()
        value = _finite_float(self.value, name=f"fitted parameter {key}")
        lower = None if self.lower is None else _finite_float(self.lower, name=f"{key} lower")
        upper = None if self.upper is None else _finite_float(self.upper, name=f"{key} upper")
        if lower is not None and upper is not None and lower >= upper:
            raise EISError(f"fitted parameter {key} lower bound must be smaller than upper")
        if lower is not None and value < lower:
            raise EISError(f"fitted parameter {key} value is below its lower bound")
        if upper is not None and value > upper:
            raise EISError(f"fitted parameter {key} value is above its upper bound")
        object.__setattr__(self, "key", key)
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "vary", bool(self.vary))
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)


@dataclass(frozen=True, slots=True)
class EISFitResult:
    """Immutable, auditable result of fitting one explicit EIS circuit."""

    source_key: str
    source_label: str
    source_sha256: str
    frequency_direction: EISDirection
    frequency_unit: str
    impedance_unit: str
    circuit: EISCircuit
    config: EISFitConfig
    n_points: int
    frequency_hz: NDArray[np.float64] = field(repr=False)
    observed_impedance: NDArray[np.complex128] = field(repr=False)
    best_fit_impedance: NDArray[np.complex128] = field(repr=False)
    residual_impedance: NDArray[np.complex128] = field(repr=False)
    parameters: Mapping[str, EISFittedParameter]
    weights: NDArray[np.float64] | None = field(default=None, repr=False)
    success: bool = False
    message: str = ""
    status: int = 0
    nfev: int = 0
    objective_sum_squares: float = float("nan")
    n_varying_parameters: int = 0
    backend: str = "scipy.optimize.least_squares"
    method: str = "trf"

    def __post_init__(self) -> None:
        if not isinstance(self.source_key, str) or not isinstance(self.source_label, str):
            raise EISError("EIS fit source key and label must be strings")
        source_sha256 = _normalized_sha256(self.source_sha256)
        if self.frequency_direction not in {"ascending", "descending"}:
            raise EISError("EIS fit frequency_direction must be ascending or descending")
        if self.frequency_unit != "Hz":
            raise EISError("EIS fit frequency_unit must be canonical 'Hz'")
        if self.impedance_unit != "ohm":
            raise EISError("EIS fit impedance_unit must be canonical 'ohm'")
        circuit = _require_circuit(self.circuit)
        validate_eis_circuit(circuit)
        if not isinstance(self.config, EISFitConfig):
            raise TypeError("EIS fit config must be an EISFitConfig")
        n_points = _nonnegative_int(self.n_points, name="EIS fit n_points")
        if n_points < 2:
            raise EISError("EIS fit n_points must be at least 2")

        frequency = _immutable_float_array(self.frequency_hz, name="fit frequency")
        observed = _immutable_complex_array(self.observed_impedance, name="observed impedance")
        best = _immutable_complex_array(self.best_fit_impedance, name="best-fit impedance")
        residual = _immutable_complex_array(self.residual_impedance, name="residual impedance")
        if not (frequency.size == observed.size == best.size == residual.size == n_points):
            raise EISError("EIS fit-result arrays and n_points must align exactly")
        if np.any(frequency <= 0):
            raise EISError("EIS fit frequency must contain only positive values")
        if _direction(frequency) != self.frequency_direction:
            raise EISError("EIS fit frequency_direction contradicts retained frequency order")
        if not np.array_equal(residual, observed - best):
            raise EISError("EIS physical residual must equal observed - best_fit exactly")

        definitions = _parameter_definitions(circuit)
        expected_keys = tuple(definition.key for definition in definitions)
        if not isinstance(self.parameters, Mapping):
            raise TypeError("EIS fit parameters must be a mapping")
        supplied = dict(self.parameters)
        if set(supplied) != set(expected_keys):
            raise EISError("EIS fit parameter keys must match the circuit exactly")
        normalized_parameters: dict[str, EISFittedParameter] = {}
        fitted_values: dict[str, float] = {}
        for definition in definitions:
            parameter = supplied[definition.key]
            if not isinstance(parameter, EISFittedParameter):
                raise TypeError("EIS fit parameter values must be EISFittedParameter instances")
            if parameter.key != definition.key:
                raise EISError("EIS fitted-parameter mapping key contradicts parameter.key")
            if parameter.vary != definition.spec.vary:
                raise EISError(f"EIS fitted parameter {definition.key} vary state contradicts circuit")
            if parameter.lower != definition.spec.lower or parameter.upper != definition.spec.upper:
                raise EISError(f"EIS fitted parameter {definition.key} bounds contradict circuit")
            lower, upper = _effective_bounds(definition)
            if not lower <= parameter.value <= upper:
                raise EISError(
                    f"EIS fitted parameter {definition.key} violates physical/caller bounds"
                )
            normalized_parameters[definition.key] = parameter
            fitted_values[definition.key] = parameter.value

        evaluated = _evaluate_node(circuit, frequency, fitted_values)
        if not np.array_equal(best, evaluated):
            raise EISError("EIS best-fit impedance contradicts circuit and fitted parameters")

        weights: NDArray[np.float64] | None = None
        if self.weights is not None:
            weights = _immutable_float_array(self.weights, name="EIS fit weights")
            if weights.size != n_points or np.any(weights <= 0):
                raise EISError("EIS fit weights must be positive and align with all points")

        objective_sum_squares = _finite_float(
            self.objective_sum_squares,
            name="EIS objective_sum_squares",
        )
        if objective_sum_squares < 0:
            raise EISError("EIS objective_sum_squares must be non-negative")
        objective = _objective_vector(observed, best, weights)
        expected_objective_sum_squares = float(np.dot(objective, objective))
        if not np.isclose(
            objective_sum_squares,
            expected_objective_sum_squares,
            rtol=1e-12,
            atol=1e-15,
        ):
            raise EISError("EIS objective_sum_squares contradicts retained fit arrays/weights")

        n_varying_parameters = _nonnegative_int(
            self.n_varying_parameters,
            name="EIS n_varying_parameters",
        )
        expected_varying = sum(parameter.vary for parameter in normalized_parameters.values())
        if n_varying_parameters != expected_varying:
            raise EISError("EIS n_varying_parameters contradicts fitted parameter state")
        status = _nonnegative_int(self.status, name="EIS fit status")
        nfev = _nonnegative_int(self.nfev, name="EIS fit nfev")
        if not isinstance(self.success, (bool, np.bool_)):
            raise TypeError("EIS fit success must be boolean")
        if not isinstance(self.message, str):
            raise TypeError("EIS fit message must be a string")
        if self.backend != "scipy.optimize.least_squares":
            raise EISError("EIS fit backend must be scipy.optimize.least_squares")
        if self.method != "trf":
            raise EISError("EIS fit method must be 'trf'")

        object.__setattr__(self, "source_key", self.source_key.strip())
        object.__setattr__(self, "source_label", self.source_label.strip())
        object.__setattr__(self, "source_sha256", source_sha256)
        object.__setattr__(self, "circuit", circuit)
        object.__setattr__(self, "n_points", n_points)
        object.__setattr__(self, "frequency_hz", frequency)
        object.__setattr__(self, "observed_impedance", observed)
        object.__setattr__(self, "best_fit_impedance", best)
        object.__setattr__(self, "residual_impedance", residual)
        object.__setattr__(self, "parameters", MappingProxyType(normalized_parameters))
        object.__setattr__(self, "weights", weights)
        object.__setattr__(self, "success", bool(self.success))
        object.__setattr__(self, "message", self.message.strip())
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "nfev", nfev)
        object.__setattr__(self, "objective_sum_squares", objective_sum_squares)
        object.__setattr__(self, "n_varying_parameters", n_varying_parameters)

    @property
    def weighting_mode(self) -> EISWeightingMode:
        return "uniform" if self.weights is None else "explicit"

    @property
    def parameter_keys(self) -> tuple[str, ...]:
        return tuple(self.parameters)

    @property
    def element_keys(self) -> tuple[str, ...]:
        return eis_circuit_element_keys(self.circuit)


def _validated_weights(weights: ArrayLike | None, *, n_points: int) -> NDArray[np.float64] | None:
    if weights is None:
        return None
    array = _immutable_float_array(weights, name="EIS residual weights")
    if array.size != n_points:
        raise EISError("EIS weights must contain exactly one multiplier per frequency point")
    if np.any(array <= 0):
        raise EISError("EIS weights must be strictly positive")
    return array


def _objective_vector(
    observed: NDArray[np.complex128],
    modeled: NDArray[np.complex128],
    weights: NDArray[np.float64] | None,
) -> NDArray[np.float64]:
    residual = observed - modeled
    real = residual.real
    imag = residual.imag
    if weights is not None:
        real = real * weights
        imag = imag * weights
    return np.concatenate((real, imag)).astype(np.float64, copy=False)


def fit_eis(
    series: Series,
    circuit: EISCircuit,
    *,
    weights: ArrayLike | None = None,
    config: EISFitConfig | None = None,
) -> EISFitResult:
    """Fit one explicit circuit to literal complex EIS data on the measured grid."""
    from scipy.optimize import least_squares

    direction = validate_eis_series(series)
    validate_eis_circuit(circuit)
    resolved_config = EISFitConfig() if config is None else config
    if not isinstance(resolved_config, EISFitConfig):
        raise TypeError("config must be an EISFitConfig")

    frequency = np.asarray(series.x, dtype=np.float64)
    observed = np.asarray(series.y, dtype=np.complex128)
    resolved_weights = _validated_weights(weights, n_points=series.n_points)
    definitions = _parameter_definitions(circuit)
    varying = tuple(item for item in definitions if item.spec.vary)
    fixed_values = {item.key: item.spec.value for item in definitions}
    if 2 * series.n_points <= len(varying):
        raise EISError(
            "EIS fit has insufficient real+imag observations for varying parameters"
        )

    x0 = np.asarray([item.spec.value for item in varying], dtype=np.float64)
    lower = np.asarray([_effective_bounds(item)[0] for item in varying], dtype=np.float64)
    upper = np.asarray([_effective_bounds(item)[1] for item in varying], dtype=np.float64)

    def values_from_vector(vector: NDArray[np.float64]) -> dict[str, float]:
        values = dict(fixed_values)
        for definition, value in zip(varying, vector, strict=True):
            values[definition.key] = float(value)
        return values

    def residual_function(vector: NDArray[np.float64]) -> NDArray[np.float64]:
        values = values_from_vector(vector)
        modeled = _evaluate_node(circuit, frequency, values)
        return _objective_vector(observed, modeled, resolved_weights)

    if varying:
        try:
            backend = least_squares(
                residual_function,
                x0,
                bounds=(lower, upper),
                method="trf",
                xtol=resolved_config.xtol,
                ftol=resolved_config.ftol,
                gtol=resolved_config.gtol,
                max_nfev=resolved_config.max_nfev,
            )
        except Exception as exc:
            raise EISError(f"EIS least-squares optimization failed: {exc}") from exc
        fitted_values = values_from_vector(np.asarray(backend.x, dtype=np.float64))
        success = bool(backend.success)
        message = str(backend.message)
        status = int(backend.status)
        nfev = int(backend.nfev)
    else:
        fitted_values = dict(fixed_values)
        success = True
        message = "all EIS circuit parameters are fixed; circuit evaluated without optimization"
        status = 0
        nfev = 0

    best = _evaluate_node(circuit, frequency, fitted_values)
    physical_residual = observed - best
    objective = _objective_vector(observed, best, resolved_weights)
    objective_sum_squares = float(np.dot(objective, objective))

    fitted_parameters: dict[str, EISFittedParameter] = {}
    for definition in definitions:
        fitted_parameters[definition.key] = EISFittedParameter(
            key=definition.key,
            value=float(fitted_values[definition.key]),
            vary=definition.spec.vary,
            lower=definition.spec.lower,
            upper=definition.spec.upper,
        )

    return EISFitResult(
        source_key=series.key,
        source_label=series.label,
        source_sha256=series_data_sha256(series),
        frequency_direction=direction,
        frequency_unit="Hz",
        impedance_unit="ohm",
        circuit=circuit,
        config=resolved_config,
        n_points=series.n_points,
        frequency_hz=frequency,
        observed_impedance=observed,
        best_fit_impedance=best,
        residual_impedance=physical_residual,
        parameters=fitted_parameters,
        weights=resolved_weights,
        success=success,
        message=message,
        status=status,
        nfev=nfev,
        objective_sum_squares=objective_sum_squares,
        n_varying_parameters=len(varying),
    )


@dataclass(frozen=True, slots=True)
class EISFitDiagnostics:
    """Already-computed EIS fit state suitable for reporting and QA."""

    success: bool
    message: str
    status: int
    nfev: int
    backend: str
    method: str
    weighting_mode: EISWeightingMode
    frequency_direction: EISDirection
    element_keys: tuple[str, ...]
    parameter_keys: tuple[str, ...]
    n_points: int
    n_varying_parameters: int
    objective_sum_squares: float


def summarize_eis_fit(result: EISFitResult) -> EISFitDiagnostics:
    """Mirror existing EIS fit state without recomputation or interpretation."""
    if not isinstance(result, EISFitResult):
        raise TypeError("result must be an EISFitResult")
    return EISFitDiagnostics(
        success=result.success,
        message=result.message,
        status=result.status,
        nfev=result.nfev,
        backend=result.backend,
        method=result.method,
        weighting_mode=result.weighting_mode,
        frequency_direction=result.frequency_direction,
        element_keys=result.element_keys,
        parameter_keys=result.parameter_keys,
        n_points=result.n_points,
        n_varying_parameters=result.n_varying_parameters,
        objective_sum_squares=result.objective_sum_squares,
    )


__all__ = [
    "EISCapacitor",
    "EISCPE",
    "EISCircuit",
    "EISDirection",
    "EISError",
    "EISFitConfig",
    "EISFitDiagnostics",
    "EISFitResult",
    "EISFittedParameter",
    "EISParallelCircuit",
    "EISParameterSpec",
    "EISResistor",
    "EISSeriesCircuit",
    "EISWeightingMode",
    "eis_circuit_element_keys",
    "eis_circuit_parameter_keys",
    "evaluate_eis_circuit",
    "fit_eis",
    "summarize_eis_fit",
    "validate_eis_circuit",
    "validate_eis_series",
]
