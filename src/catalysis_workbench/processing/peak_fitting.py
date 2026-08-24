"""Shared constrained peak fitting backed by lmfit.

This module owns CatalysisWorkbench's value-oriented scientific/API contract around
constrained one-dimensional peak fitting. It deliberately does not implement
technique-specific background estimation, peak detection, chemical assignment,
smoothing, normalization, or plotting.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal, TypeAlias

import numpy as np
from lmfit.model import Model
from lmfit.models import (
    DoniachModel,
    GaussianModel,
    LorentzianModel,
    PseudoVoigtModel,
    VoigtModel,
)
from numpy.typing import ArrayLike, NDArray

from catalysis_workbench.core import Series

PeakModelFamily: TypeAlias = Literal[
    "gaussian",
    "lorentzian",
    "voigt",
    "pseudo_voigt",
    "doniach",
]
FitMethod: TypeAlias = Literal["leastsq", "least_squares"]
ScalarMetadata: TypeAlias = str | int | float | bool | None

_ALLOWED_METHODS = frozenset({"leastsq", "least_squares"})
_KEY_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_REFERENCE_PATTERN = re.compile(
    r"\{([A-Za-z][A-Za-z0-9_]*)\.([A-Za-z][A-Za-z0-9_]*)\}"
)
_MODEL_CLASSES: dict[PeakModelFamily, type[Model]] = {
    "gaussian": GaussianModel,
    "lorentzian": LorentzianModel,
    "voigt": VoigtModel,
    "pseudo_voigt": PseudoVoigtModel,
    "doniach": DoniachModel,
}
_MODEL_PARAMETERS: dict[PeakModelFamily, frozenset[str]] = {
    "gaussian": frozenset({"amplitude", "center", "sigma"}),
    "lorentzian": frozenset({"amplitude", "center", "sigma"}),
    "voigt": frozenset({"amplitude", "center", "sigma", "gamma"}),
    "pseudo_voigt": frozenset({"amplitude", "center", "sigma", "fraction"}),
    "doniach": frozenset({"amplitude", "center", "sigma", "gamma"}),
}


class PeakFittingError(ValueError):
    """Raised when a peak-fitting request is scientifically or numerically invalid."""


def _finite_float(value: object, *, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a real numeric scalar") from exc
    if not np.isfinite(number):
        raise PeakFittingError(f"{name} must be finite")
    return number


def _immutable_array(values: ArrayLike, *, name: str, ndim: int = 1) -> NDArray[np.float64]:
    try:
        array = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must contain real numeric values") from exc
    if array.ndim != ndim:
        raise PeakFittingError(f"{name} must be {ndim}-dimensional; got shape {array.shape}")
    if ndim == 1 and array.size == 0:
        raise PeakFittingError(f"{name} must not be empty")
    if not np.isfinite(array).all():
        raise PeakFittingError(f"{name} must contain only finite values")
    normalized = np.ascontiguousarray(array, dtype=np.float64)
    immutable_buffer = normalized.tobytes(order="C")
    frozen = np.frombuffer(immutable_buffer, dtype=np.float64).reshape(normalized.shape)
    frozen.setflags(write=False)
    return frozen


def _freeze_scalar_metadata(
    metadata: Mapping[str, ScalarMetadata] | None,
) -> Mapping[str, ScalarMetadata]:
    if metadata is None:
        return MappingProxyType({})
    frozen: dict[str, ScalarMetadata] = {}
    for raw_key, value in metadata.items():
        key = str(raw_key).strip()
        if not key:
            raise PeakFittingError("component metadata keys must not be empty")
        if value is not None and not isinstance(value, (str, int, float, bool)):
            raise TypeError("component metadata values must be deterministic scalar values")
        if isinstance(value, float) and not np.isfinite(value):
            raise PeakFittingError("component metadata float values must be finite")
        frozen[key] = value
    return MappingProxyType(dict(sorted(frozen.items())))


def _array_digest(values: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(values)
    digest = hashlib.sha256()
    digest.update(str(contiguous.dtype).encode("ascii"))
    digest.update(str(contiguous.shape).encode("ascii"))
    digest.update(contiguous.tobytes(order="C"))
    return digest.hexdigest()


def _series_data_digest(series: Series) -> str:
    digest = hashlib.sha256()
    digest.update(_array_digest(np.asarray(series.x)).encode("ascii"))
    digest.update(_array_digest(np.asarray(series.y)).encode("ascii"))
    return digest.hexdigest()


def _component_prefix(key: str) -> str:
    return f"cw_{key}__"


@dataclass(frozen=True, slots=True)
class FitParameterSpec:
    """Explicit value/bounds/vary/tie state for one model parameter.

    Public ties use references such as ``{peak_a.center}``. A tied parameter must set
    ``vary=False``; the expression is translated to backend parameter names internally.
    """

    value: float
    vary: bool = True
    lower: float | None = None
    upper: float | None = None
    expr: str | None = None

    def __post_init__(self) -> None:
        value = _finite_float(self.value, name="parameter value")
        lower = None if self.lower is None else _finite_float(self.lower, name="lower bound")
        upper = None if self.upper is None else _finite_float(self.upper, name="upper bound")
        if lower is not None and upper is not None and lower > upper:
            raise PeakFittingError("parameter lower bound must be <= upper bound")
        if lower is not None and value < lower:
            raise PeakFittingError("parameter initial value is below its lower bound")
        if upper is not None and value > upper:
            raise PeakFittingError("parameter initial value is above its upper bound")

        expr = None if self.expr is None else self.expr.strip()
        if expr == "":
            expr = None
        if expr is not None and self.vary:
            raise PeakFittingError("a tied parameter expression requires vary=False")

        object.__setattr__(self, "value", value)
        object.__setattr__(self, "vary", bool(self.vary))
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)
        object.__setattr__(self, "expr", expr)


@dataclass(frozen=True, slots=True)
class PeakComponentSpec:
    """One stable-key peak component and its explicit model parameters."""

    key: str
    model: PeakModelFamily
    parameters: Mapping[str, FitParameterSpec]
    label: str = ""
    metadata: Mapping[str, ScalarMetadata] = field(default_factory=dict)

    def __post_init__(self) -> None:
        key = str(self.key).strip()
        if not _KEY_PATTERN.fullmatch(key):
            raise PeakFittingError(
                "component key must match [A-Za-z][A-Za-z0-9_]* for stable expressions"
            )
        model = str(self.model).strip().lower()
        if model not in _MODEL_CLASSES:
            raise PeakFittingError(f"unsupported peak model family: {self.model!r}")

        normalized_parameters: dict[str, FitParameterSpec] = {}
        for raw_name, spec in self.parameters.items():
            name = str(raw_name).strip()
            if not _KEY_PATTERN.fullmatch(name):
                raise PeakFittingError(f"invalid parameter name: {raw_name!r}")
            if not isinstance(spec, FitParameterSpec):
                raise TypeError("component parameters must be FitParameterSpec instances")
            if name in normalized_parameters:
                raise PeakFittingError(f"duplicate component parameter: {name!r}")
            normalized_parameters[name] = spec

        required = _MODEL_PARAMETERS[model]  # type: ignore[index]
        actual = frozenset(normalized_parameters)
        if actual != required:
            missing = sorted(required - actual)
            extra = sorted(actual - required)
            details: list[str] = []
            if missing:
                details.append(f"missing {missing}")
            if extra:
                details.append(f"unexpected {extra}")
            raise PeakFittingError(
                f"{model} parameters must be exactly {sorted(required)}; " + "; ".join(details)
            )

        object.__setattr__(self, "key", key)
        object.__setattr__(self, "model", model)
        object.__setattr__(self, "parameters", MappingProxyType(normalized_parameters))
        object.__setattr__(self, "label", str(self.label).strip())
        object.__setattr__(self, "metadata", _freeze_scalar_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class PeakFitSpec:
    """Complete explicit recipe for fitting one measured Series."""

    x_min: float
    x_max: float
    components: tuple[PeakComponentSpec, ...]
    background: ArrayLike | None = field(default=None, repr=False)
    weights: ArrayLike | None = field(default=None, repr=False)
    method: FitMethod = "leastsq"

    def __post_init__(self) -> None:
        x_min = _finite_float(self.x_min, name="x_min")
        x_max = _finite_float(self.x_max, name="x_max")
        if x_min > x_max:
            raise PeakFittingError("x_min must be <= x_max")

        components = tuple(self.components)
        if not components:
            raise PeakFittingError("peak fitting requires at least one component")
        if not all(isinstance(component, PeakComponentSpec) for component in components):
            raise TypeError("components must contain only PeakComponentSpec objects")
        keys = [component.key for component in components]
        if len(set(keys)) != len(keys):
            raise PeakFittingError("component keys must be unique within a fit")

        method = str(self.method).strip()
        if method not in _ALLOWED_METHODS:
            raise PeakFittingError(
                f"unsupported fitting method {method!r}; choose one of {sorted(_ALLOWED_METHODS)}"
            )

        background = (
            None
            if self.background is None
            else _immutable_array(self.background, name="background", ndim=1)
        )
        weights = (
            None
            if self.weights is None
            else _immutable_array(self.weights, name="weights", ndim=1)
        )
        if weights is not None:
            if np.any(weights < 0):
                raise PeakFittingError("weights must be non-negative residual multipliers")
            if not np.any(weights > 0):
                raise PeakFittingError("weights must contain at least one positive value")

        object.__setattr__(self, "x_min", x_min)
        object.__setattr__(self, "x_max", x_max)
        object.__setattr__(self, "components", components)
        object.__setattr__(self, "background", background)
        object.__setattr__(self, "weights", weights)
        object.__setattr__(self, "method", method)


@dataclass(frozen=True, slots=True)
class FittedParameter:
    """Backend-independent fitted state for one public component parameter."""

    component_key: str
    parameter_name: str
    value: float
    stderr: float | None
    vary: bool
    lower: float | None
    upper: float | None
    expr: str | None
    correlations: Mapping[str, float] = field(default_factory=dict)

    @property
    def key(self) -> str:
        return f"{self.component_key}.{self.parameter_name}"

    def __post_init__(self) -> None:
        correlations = {
            str(key): float(value) for key, value in sorted(self.correlations.items())
        }
        object.__setattr__(self, "correlations", MappingProxyType(correlations))


@dataclass(frozen=True, slots=True)
class PeakFitResult:
    """Traceable immutable result of one constrained peak fit."""

    source_key: str
    source_label: str
    source_sha256: str
    x_axis_name: str
    y_axis_name: str
    x_unit: str | None
    y_unit: str | None
    spec: PeakFitSpec
    n_points: int
    x: NDArray[np.float64] = field(repr=False)
    observed_y: NDArray[np.float64] = field(repr=False)
    background: NDArray[np.float64] = field(repr=False)
    best_fit_y: NDArray[np.float64] = field(repr=False)
    residual: NDArray[np.float64] = field(repr=False)
    component_curves: Mapping[str, NDArray[np.float64]] = field(repr=False)
    parameters: Mapping[str, FittedParameter]
    covariance: NDArray[np.float64] | None = field(default=None, repr=False)
    covariance_parameter_order: tuple[str, ...] = ()
    chi_square: float = float("nan")
    reduced_chi_square: float = float("nan")
    aic: float = float("nan")
    bic: float = float("nan")
    n_varying_parameters: int = 0
    success: bool = False
    message: str = ""
    method: str = ""
    backend: str = "lmfit"

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", _immutable_array(self.x, name="result x"))
        object.__setattr__(
            self, "observed_y", _immutable_array(self.observed_y, name="result observed_y")
        )
        object.__setattr__(
            self, "background", _immutable_array(self.background, name="result background")
        )
        object.__setattr__(
            self, "best_fit_y", _immutable_array(self.best_fit_y, name="result best_fit_y")
        )
        object.__setattr__(
            self, "residual", _immutable_array(self.residual, name="result residual")
        )
        curves = {
            str(key): _immutable_array(curve, name=f"component curve {key!r}")
            for key, curve in self.component_curves.items()
        }
        object.__setattr__(self, "component_curves", MappingProxyType(curves))
        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))
        if self.covariance is not None:
            object.__setattr__(
                self,
                "covariance",
                _immutable_array(self.covariance, name="covariance", ndim=2),
            )


def _validate_series_for_fit(series: Series) -> tuple[np.ndarray, np.ndarray]:
    if not isinstance(series, Series):
        raise TypeError("fit_peaks requires a core Series")
    x = np.asarray(series.x)
    y = np.asarray(series.y)
    if np.iscomplexobj(x) or np.iscomplexobj(y):
        raise PeakFittingError("peak fitting requires real-valued x and y data")
    x_real = x.astype(np.float64, copy=False)
    y_real = y.astype(np.float64, copy=False)
    if not np.isfinite(x_real).all():
        raise PeakFittingError("peak fitting requires a finite x axis without NaN")
    if x_real.size < 2:
        raise PeakFittingError("peak fitting requires at least two x points")
    delta = np.diff(x_real)
    if not (np.all(delta > 0) or np.all(delta < 0)):
        raise PeakFittingError("peak fitting requires strictly monotonic x values")
    return x_real, y_real


def _public_parameter_map(
    components: tuple[PeakComponentSpec, ...],
) -> tuple[dict[str, str], dict[str, str]]:
    public_to_internal: dict[str, str] = {}
    internal_to_public: dict[str, str] = {}
    for component in components:
        prefix = _component_prefix(component.key)
        for parameter_name in component.parameters:
            public = f"{component.key}.{parameter_name}"
            internal = f"{prefix}{parameter_name}"
            public_to_internal[public] = internal
            internal_to_public[internal] = public
    return public_to_internal, internal_to_public


def _expression_dependencies(expr: str) -> tuple[str, ...]:
    references = tuple(
        f"{component}.{parameter}" for component, parameter in _REFERENCE_PATTERN.findall(expr)
    )
    if "{" in _REFERENCE_PATTERN.sub("", expr) or "}" in _REFERENCE_PATTERN.sub("", expr):
        raise PeakFittingError(
            "parameter expressions must reference parameters with {component.parameter} syntax"
        )
    return references


def _validate_expression_graph(
    components: tuple[PeakComponentSpec, ...], public_to_internal: Mapping[str, str]
) -> None:
    graph: dict[str, tuple[str, ...]] = {}
    for component in components:
        for name, parameter in component.parameters.items():
            public = f"{component.key}.{name}"
            if parameter.expr is None:
                graph[public] = ()
                continue
            references = _expression_dependencies(parameter.expr)
            unknown = [reference for reference in references if reference not in public_to_internal]
            if unknown:
                raise PeakFittingError(
                    f"parameter expression for {public!r} references unknown parameters: {unknown}"
                )
            graph[public] = references

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visited:
            return
        if node in visiting:
            raise PeakFittingError("parameter expressions contain a circular dependency")
        visiting.add(node)
        for dependency in graph[node]:
            visit(dependency)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)


def _translate_expression(expr: str, public_to_internal: Mapping[str, str]) -> str:
    _expression_dependencies(expr)

    def replace(match: re.Match[str]) -> str:
        public = f"{match.group(1)}.{match.group(2)}"
        try:
            return public_to_internal[public]
        except KeyError as exc:
            raise PeakFittingError(
                f"parameter expression references unknown parameter {public!r}"
            ) from exc

    return _REFERENCE_PATTERN.sub(replace, expr)


def _build_model_and_parameters(
    spec: PeakFitSpec,
) -> tuple[Model, object, dict[str, Model], dict[str, str], dict[str, str]]:
    public_to_internal, internal_to_public = _public_parameter_map(spec.components)
    _validate_expression_graph(spec.components, public_to_internal)

    combined_model: Model | None = None
    component_models: dict[str, Model] = {}
    for component in spec.components:
        model_class = _MODEL_CLASSES[component.model]
        model = model_class(prefix=_component_prefix(component.key), nan_policy="raise")
        component_models[component.key] = model
        combined_model = model if combined_model is None else combined_model + model

    if combined_model is None:  # defensive; PeakFitSpec already rejects this state
        raise PeakFittingError("peak fitting requires at least one model component")

    params = combined_model.make_params()
    for component in spec.components:
        prefix = _component_prefix(component.key)
        for name, parameter_spec in component.parameters.items():
            internal = f"{prefix}{name}"
            if internal not in params:
                raise PeakFittingError(
                    f"backend model {component.model!r} does not provide parameter {name!r}"
                )

            # Clear built-in expression defaults for explicitly public parameters (for
            # example Voigt gamma) before applying caller state. Derived parameters such
            # as height/fwhm remain backend-internal and are not exposed as public inputs.
            params[internal].set(expr="")
            set_kwargs: dict[str, object] = {
                "value": parameter_spec.value,
                "vary": parameter_spec.vary,
            }
            if parameter_spec.lower is not None:
                set_kwargs["min"] = parameter_spec.lower
            if parameter_spec.upper is not None:
                set_kwargs["max"] = parameter_spec.upper
            params[internal].set(**set_kwargs)
            if parameter_spec.expr is not None:
                params[internal].set(
                    vary=False,
                    expr=_translate_expression(parameter_spec.expr, public_to_internal),
                )

    try:
        params.update_constraints()
    except Exception as exc:
        raise PeakFittingError(f"invalid parameter expression: {exc}") from exc
    return combined_model, params, component_models, public_to_internal, internal_to_public


def _optional_finite(value: object | None) -> float | None:
    if value is None:
        return None
    number = float(value)
    return number if np.isfinite(number) else None


def fit_peaks(series: Series, spec: PeakFitSpec) -> PeakFitResult:
    """Fit explicit constrained peak components to one real-valued Series.

    The measured source order is preserved. The model is fitted to
    ``observed_y - background``; the returned ``best_fit_y`` adds the exact caller
    background back, and ``residual`` is always the unweighted physical residual
    ``observed_y - best_fit_y``. If weights are provided, lmfit uses them only as
    residual multipliers for the objective/statistics.
    """
    if not isinstance(spec, PeakFitSpec):
        raise TypeError("spec must be a PeakFitSpec")
    x_source, y_source = _validate_series_for_fit(series)
    mask = (x_source >= spec.x_min) & (x_source <= spec.x_max)
    selected = int(np.count_nonzero(mask))
    if selected < 3:
        raise PeakFittingError("fit window must contain at least three measured points")

    x_fit = x_source[mask]
    observed = y_source[mask]
    if not np.isfinite(observed).all():
        raise PeakFittingError(
            "fit window contains missing/non-finite y values; clean them explicitly first"
        )

    if spec.background is None:
        background = np.zeros_like(observed, dtype=np.float64)
    else:
        full_background = np.asarray(spec.background, dtype=np.float64)
        if full_background.size != series.n_points:
            raise PeakFittingError(
                "background must contain exactly one value for every source Series point"
            )
        background = full_background[mask]

    weights: np.ndarray | None = None
    if spec.weights is not None:
        weights = np.asarray(spec.weights, dtype=np.float64)
        if weights.size != selected:
            raise PeakFittingError(
                "weights must contain exactly one residual multiplier per fit-window point"
            )

    model, params, component_models, _, internal_to_public = _build_model_and_parameters(spec)
    varying = sum(bool(parameter.vary) and parameter.expr is None for parameter in params.values())
    if selected <= varying:
        raise PeakFittingError(
            f"fit window has {selected} points but {varying} independently varying parameters"
        )

    target = observed - background
    try:
        backend_result = model.fit(
            target,
            params=params,
            x=x_fit,
            weights=weights,
            method=spec.method,
        )
    except Exception as exc:
        raise PeakFittingError(f"lmfit optimization failed: {exc}") from exc

    component_curves = {
        key: np.asarray(component_model.eval(params=backend_result.params, x=x_fit), dtype=float)
        for key, component_model in component_models.items()
    }
    best_fit_y = background + np.asarray(backend_result.best_fit, dtype=float)
    residual = observed - best_fit_y

    parameter_results: dict[str, FittedParameter] = {}
    for component in spec.components:
        prefix = _component_prefix(component.key)
        for name, parameter_spec in component.parameters.items():
            internal = f"{prefix}{name}"
            parameter = backend_result.params[internal]
            correlations: dict[str, float] = {}
            for other_internal, correlation in (parameter.correl or {}).items():
                other_public = internal_to_public.get(other_internal)
                if other_public is not None and np.isfinite(correlation):
                    correlations[other_public] = float(correlation)
            public = f"{component.key}.{name}"
            parameter_results[public] = FittedParameter(
                component_key=component.key,
                parameter_name=name,
                value=float(parameter.value),
                stderr=_optional_finite(parameter.stderr),
                vary=bool(parameter.vary),
                lower=None if not np.isfinite(parameter.min) else float(parameter.min),
                upper=None if not np.isfinite(parameter.max) else float(parameter.max),
                expr=parameter_spec.expr,
                correlations=correlations,
            )

    covariance: np.ndarray | None = None
    covariance_parameter_order: tuple[str, ...] = ()
    if backend_result.covar is not None:
        candidate = np.asarray(backend_result.covar, dtype=np.float64)
        if candidate.ndim == 2 and np.isfinite(candidate).all():
            covariance = candidate
            covariance_parameter_order = tuple(
                internal_to_public.get(name, name) for name in (backend_result.var_names or [])
            )

    return PeakFitResult(
        source_key=series.key,
        source_label=series.label,
        source_sha256=_series_data_digest(series),
        x_axis_name=series.x_axis.name,
        y_axis_name=series.y_axis.name,
        x_unit=series.x_axis.unit,
        y_unit=series.y_axis.unit,
        spec=spec,
        n_points=selected,
        x=x_fit,
        observed_y=observed,
        background=background,
        best_fit_y=best_fit_y,
        residual=residual,
        component_curves=component_curves,
        parameters=parameter_results,
        covariance=covariance,
        covariance_parameter_order=covariance_parameter_order,
        chi_square=float(backend_result.chisqr),
        reduced_chi_square=float(backend_result.redchi),
        aic=float(backend_result.aic),
        bic=float(backend_result.bic),
        n_varying_parameters=int(backend_result.nvarys),
        success=bool(backend_result.success),
        message=str(backend_result.message),
        method=str(backend_result.method),
        backend="lmfit",
    )
