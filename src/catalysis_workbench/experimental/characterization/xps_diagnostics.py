"""Value-oriented diagnostic summaries for reviewed constrained XPS fits."""

from __future__ import annotations

from dataclasses import dataclass

from .xps import XPSDirection
from .xps_fitting import XPSPeakFitResult


@dataclass(frozen=True, slots=True)
class XPSFitDiagnostics:
    """Already-computed fit/uncertainty state suitable for reporting and QA."""

    success: bool
    message: str
    method: str
    backend: str
    background_method: str
    source_direction: XPSDirection
    component_keys: tuple[str, ...]
    n_points: int
    n_varying_parameters: int
    chi_square: float
    reduced_chi_square: float
    aic: float
    bic: float
    covariance_available: bool
    fitted_parameter_count: int
    parameters_with_stderr: tuple[str, ...]
    parameters_without_stderr: tuple[str, ...]


def summarize_xps_fit(result: XPSPeakFitResult) -> XPSFitDiagnostics:
    """Mirror existing XPS/shared-fit diagnostic state without recomputation."""
    if not isinstance(result, XPSPeakFitResult):
        raise TypeError("result must be an XPSPeakFitResult")

    fit = result.fit
    with_stderr = tuple(
        key for key, parameter in fit.parameters.items() if parameter.stderr is not None
    )
    without_stderr = tuple(
        key for key, parameter in fit.parameters.items() if parameter.stderr is None
    )
    return XPSFitDiagnostics(
        success=bool(fit.success),
        message=str(fit.message),
        method=str(fit.method),
        backend=str(fit.backend),
        background_method=result.background_method,
        source_direction=result.source_direction,
        component_keys=result.component_keys,
        n_points=int(fit.n_points),
        n_varying_parameters=int(fit.n_varying_parameters),
        chi_square=float(fit.chi_square),
        reduced_chi_square=float(fit.reduced_chi_square),
        aic=float(fit.aic),
        bic=float(fit.bic),
        covariance_available=fit.covariance is not None,
        fitted_parameter_count=len(fit.parameters),
        parameters_with_stderr=with_stderr,
        parameters_without_stderr=without_stderr,
    )


__all__ = ["XPSFitDiagnostics", "summarize_xps_fit"]
