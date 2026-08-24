"""Scientific/API regressions for constrained XPS fitting integration."""

from __future__ import annotations

import json
import subprocess
import sys

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.characterization.xps import (
    XPSError,
    linear_xps_background,
    prepare_xps_region,
    shift_xps_binding_energy,
    shirley_xps_background,
)
from catalysis_workbench.experimental.characterization.xps_fitting import (
    XPSDoubletSpec,
    fit_xps_peaks,
)
from catalysis_workbench.processing import FitParameterSpec, PeakComponentSpec


def _series(x: np.ndarray, y: np.ndarray, *, key: str = "xps-fit") -> Series:
    return Series(
        x=x,
        y=y,
        key=key,
        label="Synthetic XPS fit",
        x_axis=Axis("binding_energy", unit="eV", label="Binding energy"),
        y_axis=Axis("intensity", unit="counts", label="Intensity"),
    )


def _gaussian(
    x: np.ndarray,
    *,
    amplitude: float,
    center: float,
    sigma: float,
) -> np.ndarray:
    return amplitude / (sigma * np.sqrt(2.0 * np.pi)) * np.exp(
        -((x - center) ** 2) / (2.0 * sigma**2)
    )


def _gaussian_component(
    key: str,
    *,
    amplitude: float,
    center: float,
    sigma: float,
    label: str = "",
) -> PeakComponentSpec:
    return PeakComponentSpec(
        key=key,
        model="gaussian",
        parameters={
            "amplitude": FitParameterSpec(amplitude, lower=0.0),
            "center": FitParameterSpec(center),
            "sigma": FitParameterSpec(sigma, lower=0.05),
        },
        label=label,
    )


def test_single_xps_component_delegates_to_shared_fitter() -> None:
    x = np.linspace(280.0, 290.0, 401)
    y = _gaussian(x, amplitude=12.0, center=285.2, sigma=0.7)
    component = _gaussian_component(
        "c1s",
        amplitude=10.0,
        center=285.0,
        sigma=0.9,
    )

    result = fit_xps_peaks(
        _series(x, y),
        x_min_ev=280.0,
        x_max_ev=290.0,
        components=(component,),
    )

    assert result.fit.success
    assert result.background_method == "zero"
    assert result.component_keys == ("c1s",)
    assert result.source_direction == "ascending"
    assert result.fit.parameters["c1s.amplitude"].value == pytest.approx(12.0, rel=1e-6)
    assert result.fit.parameters["c1s.center"].value == pytest.approx(285.2, abs=1e-7)
    assert result.fit.parameters["c1s.sigma"].value == pytest.approx(0.7, rel=1e-6)


def test_doublet_links_signed_separation_amplitude_and_sigma_ratios() -> None:
    x = np.linspace(280.0, 292.0, 601)
    primary_y = _gaussian(x, amplitude=12.0, center=284.0, sigma=0.6)
    secondary_y = _gaussian(x, amplitude=6.0, center=287.2, sigma=0.6)
    primary = _gaussian_component(
        "p_main",
        amplitude=10.0,
        center=283.8,
        sigma=0.7,
    )
    doublet = XPSDoubletSpec(
        primary=primary,
        secondary_key="p_partner",
        separation_ev=3.2,
        amplitude_ratio=0.5,
        parameter_ratios={"sigma": 1.0},
    )

    result = fit_xps_peaks(
        _series(x, primary_y + secondary_y),
        x_min_ev=280.0,
        x_max_ev=292.0,
        doublets=(doublet,),
    )

    assert result.fit.success
    primary_fit = result.fit.parameters
    assert primary_fit["p_main.center"].value == pytest.approx(284.0, abs=1e-6)
    assert primary_fit["p_partner.center"].value == pytest.approx(
        primary_fit["p_main.center"].value + 3.2,
        abs=1e-10,
    )
    assert primary_fit["p_partner.amplitude"].value == pytest.approx(
        primary_fit["p_main.amplitude"].value * 0.5,
        rel=1e-10,
    )
    assert primary_fit["p_partner.sigma"].value == pytest.approx(
        primary_fit["p_main.sigma"].value,
        rel=1e-10,
    )
    assert primary_fit["p_partner.center"].expr == "{p_main.center} + (3.2)"
    assert primary_fit["p_partner.amplitude"].expr == "{p_main.amplitude} * 0.5"
    assert primary_fit["p_partner.sigma"].expr == "{p_main.sigma} * 1.0"


def test_doublet_supports_explicit_negative_signed_separation() -> None:
    primary = _gaussian_component(
        "high",
        amplitude=10.0,
        center=288.0,
        sigma=0.7,
    )
    doublet = XPSDoubletSpec(
        primary=primary,
        secondary_key="low",
        separation_ev=-3.0,
        amplitude_ratio=0.5,
        parameter_ratios={"sigma": 1.0},
    )
    assert doublet.secondary.parameters["center"].value == pytest.approx(285.0)
    assert doublet.secondary.parameters["center"].expr == "{high.center} + (-3.0)"


def test_ascending_descending_xps_fit_is_physically_equivalent() -> None:
    x = np.linspace(280.0, 292.0, 601)
    y = _gaussian(x, amplitude=12.0, center=284.0, sigma=0.6) + _gaussian(
        x,
        amplitude=6.0,
        center=287.2,
        sigma=0.6,
    )

    def make_doublet() -> XPSDoubletSpec:
        return XPSDoubletSpec(
            primary=_gaussian_component(
                "main",
                amplitude=10.0,
                center=283.8,
                sigma=0.7,
            ),
            secondary_key="partner",
            separation_ev=3.2,
            amplitude_ratio=0.5,
            parameter_ratios={"sigma": 1.0},
        )

    ascending = fit_xps_peaks(
        _series(x, y, key="up"),
        x_min_ev=280.0,
        x_max_ev=292.0,
        doublets=(make_doublet(),),
    )
    descending = fit_xps_peaks(
        _series(x[::-1], y[::-1], key="down"),
        x_min_ev=280.0,
        x_max_ev=292.0,
        doublets=(make_doublet(),),
    )

    for name in ("main.amplitude", "main.center", "main.sigma"):
        assert descending.fit.parameters[name].value == pytest.approx(
            ascending.fit.parameters[name].value,
            rel=1e-7,
            abs=1e-8,
        )
    assert ascending.source_direction == "ascending"
    assert descending.source_direction == "descending"
    assert ascending.fit.x[0] < ascending.fit.x[-1]
    assert descending.fit.x[0] > descending.fit.x[-1]


def test_linear_background_must_align_exactly_and_is_used_by_shared_fit() -> None:
    x = np.linspace(280.0, 290.0, 401)
    baseline = 2.0 + 0.1 * (x - 280.0)
    peak = _gaussian(x, amplitude=9.0, center=285.0, sigma=0.6)
    y = baseline + peak
    y[0] = baseline[0]
    y[-1] = baseline[-1]
    source = _series(x, y, key="linear-fit")
    background = linear_xps_background(source)
    component = _gaussian_component(
        "peak",
        amplitude=8.0,
        center=284.8,
        sigma=0.8,
    )

    result = fit_xps_peaks(
        source,
        x_min_ev=280.0,
        x_max_ev=290.0,
        components=(component,),
        background=background,
    )

    assert result.background is background
    assert result.background_method == "linear"
    assert np.array_equal(result.fit.background, background.background_y)
    assert result.fit.parameters["peak.center"].value == pytest.approx(285.0, abs=1e-6)


def test_shirley_background_exact_region_integrates_with_shared_fit() -> None:
    x = np.linspace(280.0, 290.0, 401)
    peak = _gaussian(x, amplitude=9.0, center=285.0, sigma=0.6)
    y = 2.0 + peak
    y[0] = 2.0
    y[-1] = 2.0
    source = _series(x, y, key="shirley-fit")
    background = shirley_xps_background(source)
    component = _gaussian_component(
        "peak",
        amplitude=8.0,
        center=284.8,
        sigma=0.8,
    )

    result = fit_xps_peaks(
        source,
        x_min_ev=280.0,
        x_max_ev=290.0,
        components=(component,),
        background=background,
    )

    assert result.background_method == "shirley"
    assert np.allclose(background.background_y, 2.0)
    assert result.fit.parameters["peak.center"].value == pytest.approx(285.0, abs=1e-6)


def test_background_digest_grid_order_and_observed_y_are_fail_closed() -> None:
    x = np.linspace(280.0, 290.0, 101)
    y = 2.0 + _gaussian(x, amplitude=5.0, center=285.0, sigma=0.8)
    y[0] = y[-1] = 2.0
    source = _series(x, y, key="background-source")
    background = shirley_xps_background(source)
    component = _gaussian_component(
        "peak",
        amplitude=4.0,
        center=285.0,
        sigma=0.9,
    )

    modified = _series(x, y + 0.01, key="background-source")
    with pytest.raises(XPSError, match="source digest"):
        fit_xps_peaks(
            modified,
            x_min_ev=280.0,
            x_max_ev=290.0,
            components=(component,),
            background=background,
        )

    reversed_source = _series(x[::-1], y[::-1], key="background-source")
    with pytest.raises(XPSError, match="source digest"):
        fit_xps_peaks(
            reversed_source,
            x_min_ev=280.0,
            x_max_ev=290.0,
            components=(component,),
            background=background,
        )

    with pytest.raises(XPSError, match="exact prepared region"):
        fit_xps_peaks(
            source,
            x_min_ev=282.0,
            x_max_ev=288.0,
            components=(component,),
            background=background,
        )


def test_doublet_ratios_keys_and_shape_relations_fail_explicitly() -> None:
    primary = _gaussian_component(
        "main",
        amplitude=10.0,
        center=285.0,
        sigma=0.7,
    )
    with pytest.raises(XPSError, match="non-zero"):
        XPSDoubletSpec(
            primary=primary,
            secondary_key="partner",
            separation_ev=0.0,
            amplitude_ratio=0.5,
            parameter_ratios={"sigma": 1.0},
        )
    with pytest.raises(XPSError, match="amplitude_ratio"):
        XPSDoubletSpec(
            primary=primary,
            secondary_key="partner",
            separation_ev=3.0,
            amplitude_ratio=0.0,
            parameter_ratios={"sigma": 1.0},
        )
    with pytest.raises(XPSError, match="parameter ratio 'sigma'"):
        XPSDoubletSpec(
            primary=primary,
            secondary_key="partner",
            separation_ev=3.0,
            amplitude_ratio=0.5,
            parameter_ratios={"sigma": -1.0},
        )
    with pytest.raises(XPSError, match="must explicitly cover"):
        XPSDoubletSpec(
            primary=primary,
            secondary_key="partner",
            separation_ev=3.0,
            amplitude_ratio=0.5,
            parameter_ratios={},
        )
    with pytest.raises(XPSError, match="keys must differ"):
        XPSDoubletSpec(
            primary=primary,
            secondary_key="main",
            separation_ev=3.0,
            amplitude_ratio=0.5,
            parameter_ratios={"sigma": 1.0},
        )


def test_pseudo_voigt_requires_explicit_fraction_relation() -> None:
    primary = PeakComponentSpec(
        key="pv_main",
        model="pseudo_voigt",
        parameters={
            "amplitude": FitParameterSpec(10.0, lower=0.0),
            "center": FitParameterSpec(285.0),
            "sigma": FitParameterSpec(0.7, lower=0.05),
            "fraction": FitParameterSpec(0.5, lower=0.0, upper=1.0),
        },
    )
    with pytest.raises(XPSError, match="missing \['fraction'\]"):
        XPSDoubletSpec(
            primary=primary,
            secondary_key="pv_partner",
            separation_ev=3.0,
            amplitude_ratio=0.5,
            parameter_ratios={"sigma": 1.0},
        )

    explicit = XPSDoubletSpec(
        primary=primary,
        secondary_key="pv_partner",
        separation_ev=3.0,
        amplitude_ratio=0.5,
        parameter_ratios={"sigma": 1.0, "fraction": 1.0},
    )
    assert explicit.secondary.parameters["fraction"].expr == "{pv_main.fraction} * 1.0"


def test_duplicate_keys_across_single_and_doublet_fail() -> None:
    x = np.linspace(280.0, 290.0, 101)
    source = _series(x, _gaussian(x, amplitude=5.0, center=285.0, sigma=0.8))
    primary = _gaussian_component(
        "main",
        amplitude=5.0,
        center=285.0,
        sigma=0.8,
    )
    doublet = XPSDoubletSpec(
        primary=primary,
        secondary_key="partner",
        separation_ev=2.0,
        amplitude_ratio=0.5,
        parameter_ratios={"sigma": 1.0},
    )
    with pytest.raises(XPSError, match="component keys must be unique"):
        fit_xps_peaks(
            source,
            x_min_ev=280.0,
            x_max_ev=290.0,
            components=(primary,),
            doublets=(doublet,),
        )


def test_assignment_labels_do_not_change_fitting_mathematics() -> None:
    x = np.linspace(280.0, 290.0, 401)
    y = _gaussian(x, amplitude=8.0, center=285.0, sigma=0.7)
    first = _gaussian_component(
        "peak",
        amplitude=7.0,
        center=284.8,
        sigma=0.8,
        label="Assignment A",
    )
    second = _gaussian_component(
        "peak",
        amplitude=7.0,
        center=284.8,
        sigma=0.8,
        label="Completely different display text",
    )

    fit_a = fit_xps_peaks(
        _series(x, y, key="labels-a"),
        x_min_ev=280.0,
        x_max_ev=290.0,
        components=(first,),
    )
    fit_b = fit_xps_peaks(
        _series(x, y, key="labels-b"),
        x_min_ev=280.0,
        x_max_ev=290.0,
        components=(second,),
    )
    for name in ("amplitude", "center", "sigma"):
        assert fit_a.fit.parameters[f"peak.{name}"].value == pytest.approx(
            fit_b.fit.parameters[f"peak.{name}"].value,
            rel=1e-12,
            abs=1e-12,
        )


def test_xps_processing_history_and_result_are_deterministic() -> None:
    x = np.linspace(280.0, 290.0, 401)
    y = _gaussian(x, amplitude=8.0, center=285.0, sigma=0.7)
    raw = _series(x, y, key="provenance")
    shifted = shift_xps_binding_energy(raw, 0.2, reference="explicit reference")
    region = prepare_xps_region(shifted, 281.0, 289.0)
    component = _gaussian_component(
        "peak",
        amplitude=7.0,
        center=285.2,
        sigma=0.8,
    )

    first = fit_xps_peaks(
        region,
        x_min_ev=float(np.min(region.x)),
        x_max_ev=float(np.max(region.x)),
        components=(component,),
    )
    second = fit_xps_peaks(
        region,
        x_min_ev=float(np.min(region.x)),
        x_max_ev=float(np.max(region.x)),
        components=(component,),
    )

    assert first.source_sha256 == second.source_sha256
    assert tuple(step.operation for step in first.processing_steps) == (
        "xps.energy_shift",
        "xps.prepare_region",
    )
    assert first.processing_steps[0].parameters["shift_ev"] == pytest.approx(0.2)
    assert np.array_equal(first.fit.best_fit_y, second.fit.best_fit_y)


def test_importing_xps_fitting_module_keeps_matplotlib_lazy() -> None:
    code = r"""
import json
import sys
import catalysis_workbench.experimental.characterization.xps_fitting as xps_fitting
loaded = any(
    name == "matplotlib" or name.startswith("matplotlib.")
    for name in sys.modules
)
print(json.dumps({"matplotlib": loaded, "exports": sorted(xps_fitting.__all__)}))
"""
    completed = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout.strip())
    assert payload["matplotlib"] is False
    assert "fit_xps_peaks" in payload["exports"]
