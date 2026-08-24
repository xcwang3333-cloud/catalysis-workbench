"""Explicit constrained XPS fitting as a thin adapter over shared peak fitting."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from math import isfinite
from types import MappingProxyType
from typing import Any, TypeAlias

import numpy as np
from numpy.typing import ArrayLike

from catalysis_workbench.core import Series

from .xps import (
    XPSBackgroundResult,
    XPSDirection,
    XPSError,
    _direction,
    _series_data_digest,
    validate_xps_series,
)

ScalarMetadata: TypeAlias = str | int | float | bool | None
_RESERVED_SECONDARY_METADATA = frozenset(
    {"xps_doublet_role", "xps_doublet_primary_key", "xps_doublet_separation_ev"}
)


def _finite_float(value: object, *, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a real numeric value") from exc
    if not isfinite(result):
        raise XPSError(f"{name} must be finite")
    return result


def _freeze_scalar_metadata(
    metadata: Mapping[str, ScalarMetadata] | None,
    *,
    name: str,
) -> Mapping[str, ScalarMetadata]:
    if metadata is None:
        return MappingProxyType({})
    frozen: dict[str, ScalarMetadata] = {}
    for raw_key, value in metadata.items():
        key = str(raw_key).strip()
        if not key:
            raise XPSError(f"{name} keys must not be empty")
        if value is not None and not isinstance(value, (str, int, float, bool)):
            raise TypeError(f"{name} values must be deterministic scalar values")
        if isinstance(value, float) and not np.isfinite(value):
            raise XPSError(f"{name} float values must be finite")
        frozen[key] = value
    return MappingProxyType(dict(sorted(frozen.items())))


@dataclass(frozen=True, slots=True)
class XPSProcessingStep:
    """One deterministic XPS preparation step retained by a fit result."""

    operation: str
    parameters: Mapping[str, ScalarMetadata] = field(default_factory=dict)

    def __post_init__(self) -> None:
        operation = str(self.operation).strip()
        if not operation.startswith("xps."):
            raise XPSError("XPS processing-step operation must start with 'xps.'")
        object.__setattr__(self, "operation", operation)
        object.__setattr__(
            self,
            "parameters",
            _freeze_scalar_metadata(self.parameters, name="processing-step parameters"),
        )


def _xps_processing_steps(series: Series) -> tuple[XPSProcessingStep, ...]:
    output: list[XPSProcessingStep] = []
    for item in series.metadata.get("processing_history", ()):
        if not isinstance(item, Mapping):
            continue
        operation = str(item.get("operation", "")).strip()
        if not operation.startswith("xps."):
            continue
        raw_parameters = item.get("parameters", {})
        if not isinstance(raw_parameters, Mapping):
            raise XPSError("XPS processing history contains invalid parameters")
        output.append(XPSProcessingStep(operation=operation, parameters=raw_parameters))
    return tuple(output)


@dataclass(frozen=True, slots=True)
class XPSDoubletSpec:
    """Explicitly link a primary shared peak component to one secondary XPS component.

    Every mathematical doublet relation is caller supplied. ``separation_ev`` is signed,
    so ``secondary.center = primary.center + separation_ev``. ``amplitude_ratio`` and
    every model-specific parameter in ``parameter_ratios`` are positive multiplicative
    relations to the corresponding primary parameter.
    """

    primary: Any
    secondary_key: str
    separation_ev: float
    amplitude_ratio: float
    parameter_ratios: Mapping[str, float]
    secondary_label: str = ""
    secondary_metadata: Mapping[str, ScalarMetadata] = field(default_factory=dict)
    secondary: Any = field(init=False, repr=False)

    def __post_init__(self) -> None:
        # Importing the shared fitting surface is deliberately deferred until an XPS
        # doublet is actually constructed. Merely importing the XPS numerical module
        # therefore remains independent from lmfit/Matplotlib import side effects.
        from catalysis_workbench.processing import (
            FitParameterSpec,
            PeakComponentSpec,
        )

        if not isinstance(self.primary, PeakComponentSpec):
            raise TypeError("primary must be a PeakComponentSpec")

        secondary_key = str(self.secondary_key).strip()
        if secondary_key == self.primary.key:
            raise XPSError("XPS doublet primary and secondary component keys must differ")

        separation = _finite_float(self.separation_ev, name="separation_ev")
        if separation == 0.0:
            raise XPSError("XPS doublet separation_ev must be non-zero")
        amplitude_ratio = _finite_float(self.amplitude_ratio, name="amplitude_ratio")
        if amplitude_ratio <= 0:
            raise XPSError("XPS doublet amplitude_ratio must be > 0")

        required_relations = set(self.primary.parameters) - {"amplitude", "center"}
        raw_ratios = dict(self.parameter_ratios)
        actual_relations = {str(name).strip() for name in raw_ratios}
        if actual_relations != required_relations:
            missing = sorted(required_relations - actual_relations)
            extra = sorted(actual_relations - required_relations)
            details: list[str] = []
            if missing:
                details.append(f"missing {missing}")
            if extra:
                details.append(f"unexpected {extra}")
            raise XPSError(
                "XPS doublet parameter_ratios must explicitly cover every "
                "non-amplitude/non-center model parameter; " + "; ".join(details)
            )

        ratios: dict[str, float] = {}
        for raw_name, raw_ratio in raw_ratios.items():
            name = str(raw_name).strip()
            ratio = _finite_float(raw_ratio, name=f"parameter ratio {name!r}")
            if ratio <= 0:
                raise XPSError(f"XPS doublet parameter ratio {name!r} must be > 0")
            ratios[name] = ratio

        metadata = dict(
            _freeze_scalar_metadata(
                self.secondary_metadata,
                name="secondary metadata",
            )
        )
        conflicts = sorted(_RESERVED_SECONDARY_METADATA.intersection(metadata))
        if conflicts:
            raise XPSError(
                f"secondary metadata uses reserved XPS doublet keys: {conflicts}"
            )
        metadata.update(
            {
                "xps_doublet_role": "secondary",
                "xps_doublet_primary_key": self.primary.key,
                "xps_doublet_separation_ev": separation,
            }
        )

        primary_amplitude = self.primary.parameters["amplitude"]
        primary_center = self.primary.parameters["center"]
        parameters: dict[str, Any] = {
            "amplitude": FitParameterSpec(
                value=primary_amplitude.value * amplitude_ratio,
                vary=False,
                expr=f"{{{self.primary.key}.amplitude}} * {amplitude_ratio!r}",
            ),
            "center": FitParameterSpec(
                value=primary_center.value + separation,
                vary=False,
                expr=f"{{{self.primary.key}.center}} + ({separation!r})",
            ),
        }
        for name in sorted(required_relations):
            primary_parameter = self.primary.parameters[name]
            ratio = ratios[name]
            parameters[name] = FitParameterSpec(
                value=primary_parameter.value * ratio,
                vary=False,
                expr=f"{{{self.primary.key}.{name}}} * {ratio!r}",
            )

        secondary = PeakComponentSpec(
            key=secondary_key,
            model=self.primary.model,
            parameters=parameters,
            label=str(self.secondary_label).strip(),
            metadata=metadata,
        )

        object.__setattr__(self, "secondary_key", secondary_key)
        object.__setattr__(self, "separation_ev", separation)
        object.__setattr__(self, "amplitude_ratio", amplitude_ratio)
        object.__setattr__(
            self,
            "parameter_ratios",
            MappingProxyType(dict(sorted(ratios.items()))),
        )
        object.__setattr__(
            self,
            "secondary_metadata",
            _freeze_scalar_metadata(self.secondary_metadata, name="secondary metadata"),
        )
        object.__setattr__(self, "secondary_label", str(self.secondary_label).strip())
        object.__setattr__(self, "secondary", secondary)

    @property
    def components(self) -> tuple[Any, Any]:
        """Return the stable primary/secondary shared peak components."""
        return self.primary, self.secondary


@dataclass(frozen=True, slots=True)
class XPSPeakFitResult:
    """Traceable composition of XPS preparation state and a shared fit result."""

    fit: Any
    source_sha256: str
    source_direction: XPSDirection
    processing_steps: tuple[XPSProcessingStep, ...]
    background: XPSBackgroundResult | None
    doublets: tuple[XPSDoubletSpec, ...]

    def __post_init__(self) -> None:
        from catalysis_workbench.processing import PeakFitResult

        if not isinstance(self.fit, PeakFitResult):
            raise TypeError("fit must be a PeakFitResult")
        if self.fit.source_sha256 != self.source_sha256:
            raise XPSError("XPS fit result source digest does not match XPS source state")
        object.__setattr__(self, "processing_steps", tuple(self.processing_steps))
        object.__setattr__(self, "doublets", tuple(self.doublets))

    @property
    def background_method(self) -> str:
        return "zero" if self.background is None else self.background.method

    @property
    def component_keys(self) -> tuple[str, ...]:
        return tuple(component.key for component in self.fit.spec.components)


def _validate_background_alignment(
    series: Series,
    background: XPSBackgroundResult,
    *,
    x_min_ev: float,
    x_max_ev: float,
) -> None:
    source_digest = _series_data_digest(series)
    x = np.asarray(series.x, dtype=np.float64)
    y = np.asarray(series.y, dtype=np.float64)
    source_direction = _direction(x)

    if background.source_key != series.key:
        raise XPSError("XPS background source key does not match fit Series")
    if background.source_sha256 != source_digest:
        raise XPSError("XPS background source digest does not match fit Series")
    if background.x_unit != "eV":
        raise XPSError("XPS background binding-energy unit must be eV")
    if background.y_unit != series.y_axis.unit:
        raise XPSError("XPS background intensity unit does not match fit Series")
    if background.source_direction != source_direction:
        raise XPSError("XPS background source direction does not match fit Series")
    if not np.array_equal(background.x, x):
        raise XPSError("XPS background x grid/order does not exactly match fit Series")
    if not np.array_equal(background.observed_y, y):
        raise XPSError("XPS background observed intensity does not exactly match fit Series")
    if background.background_y.size != x.size:
        raise XPSError("XPS background length does not match fit Series")
    if not np.isfinite(background.background_y).all():
        raise XPSError("XPS background contains non-finite values")

    mask = (x >= x_min_ev) & (x <= x_max_ev)
    if int(np.count_nonzero(mask)) != x.size:
        raise XPSError(
            "XPSBackgroundResult must be produced from the exact prepared region being fitted; "
            "the explicit fit window must include every background source point"
        )


def fit_xps_peaks(
    series: Series,
    *,
    x_min_ev: float,
    x_max_ev: float,
    components: Sequence[Any] = (),
    doublets: Sequence[XPSDoubletSpec] = (),
    background: XPSBackgroundResult | None = None,
    weights: ArrayLike | None = None,
    method: str = "leastsq",
) -> XPSPeakFitResult:
    """Fit explicit XPS components by delegating to the reviewed shared fitter."""
    from catalysis_workbench.processing import (
        PeakComponentSpec,
        PeakFitSpec,
        fit_peaks,
    )

    validate_xps_series(series)
    low = _finite_float(x_min_ev, name="x_min_ev")
    high = _finite_float(x_max_ev, name="x_max_ev")
    if low > high:
        raise XPSError("x_min_ev must be <= x_max_ev")

    singles = tuple(components)
    if not all(isinstance(component, PeakComponentSpec) for component in singles):
        raise TypeError("components must contain only PeakComponentSpec objects")
    linked = tuple(doublets)
    if not all(isinstance(doublet, XPSDoubletSpec) for doublet in linked):
        raise TypeError("doublets must contain only XPSDoubletSpec objects")

    flattened: list[Any] = list(singles)
    for doublet in linked:
        flattened.extend(doublet.components)
    if not flattened:
        raise XPSError("XPS fitting requires at least one explicit component or doublet")

    keys = [component.key for component in flattened]
    if len(set(keys)) != len(keys):
        raise XPSError("XPS fitting component keys must be unique across singles and doublets")

    background_values: ArrayLike | None = None
    if background is not None:
        if not isinstance(background, XPSBackgroundResult):
            raise TypeError("background must be an XPSBackgroundResult or None")
        _validate_background_alignment(
            series,
            background,
            x_min_ev=low,
            x_max_ev=high,
        )
        background_values = background.background_y

    shared_spec = PeakFitSpec(
        x_min=low,
        x_max=high,
        components=tuple(flattened),
        background=background_values,
        weights=weights,
        method=method,
    )
    shared_result = fit_peaks(series, shared_spec)
    source_sha256 = _series_data_digest(series)
    source_direction = _direction(np.asarray(series.x, dtype=np.float64))

    return XPSPeakFitResult(
        fit=shared_result,
        source_sha256=source_sha256,
        source_direction=source_direction,
        processing_steps=_xps_processing_steps(series),
        background=background,
        doublets=linked,
    )


__all__ = [
    "XPSDoubletSpec",
    "XPSPeakFitResult",
    "XPSProcessingStep",
    "fit_xps_peaks",
]
