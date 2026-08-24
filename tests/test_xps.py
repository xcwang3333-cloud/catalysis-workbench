"""Scientific/API regressions for XPS semantics and background preparation."""

from __future__ import annotations

import json
import subprocess
import sys

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.characterization.xps import (
    XPSBackgroundResult,
    XPSError,
    linear_xps_background,
    prepare_xps_region,
    shift_xps_binding_energy,
    shirley_xps_background,
    validate_xps_series,
)


def _series(
    x: np.ndarray,
    y: np.ndarray,
    *,
    key: str = "xps-synthetic",
    x_name: str = "binding_energy",
    x_unit: str | None = "eV",
    y_name: str = "intensity",
) -> Series:
    return Series(
        x=x,
        y=y,
        key=key,
        label="Synthetic XPS",
        x_axis=Axis(x_name, unit=x_unit, label="Binding energy"),
        y_axis=Axis(y_name, unit="counts", label="Intensity"),
        metadata={"source": "synthetic"},
    )


def _gaussian(x: np.ndarray, center: float = 5.0, sigma: float = 0.8) -> np.ndarray:
    return 5.0 * np.exp(-((x - center) ** 2) / (2.0 * sigma**2))


def test_validate_xps_semantics_units_and_numeric_failures() -> None:
    x = np.linspace(0.0, 10.0, 11)
    y = np.ones_like(x)
    validate_xps_series(_series(x, y))
    validate_xps_series(_series(x[::-1], y[::-1], x_unit="electronvolt"))

    with pytest.raises(XPSError, match="x_axis.name"):
        validate_xps_series(_series(x, y, x_name="energy"))
    with pytest.raises(XPSError, match="explicit eV"):
        validate_xps_series(_series(x, y, x_unit=None))
    with pytest.raises(XPSError, match="unsupported XPS binding-energy unit"):
        validate_xps_series(_series(x, y, x_unit="keV"))
    with pytest.raises(XPSError, match="y_axis.name"):
        validate_xps_series(_series(x, y, y_name="signal"))
    with pytest.raises(XPSError, match="strictly monotonic"):
        validate_xps_series(_series(np.array([0.0, 1.0, 1.0, 2.0]), np.ones(4)))

    complex_series = Series(
        x=np.array([0.0, 1.0, 2.0]),
        y=np.array([1.0 + 1.0j, 2.0, 1.0]),
        x_axis=Axis("binding_energy", unit="eV"),
        y_axis=Axis("intensity", unit="counts"),
    )
    with pytest.raises(XPSError, match="must be real"):
        validate_xps_series(complex_series)


def test_energy_shift_is_additive_explicit_and_preserves_intensity_order() -> None:
    x = np.array([5.0, 4.0, 3.0, 2.0])
    y = np.array([10.0, 15.0, 12.0, 9.0])
    source = _series(x, y, key="energy-shift")

    corrected = shift_xps_binding_energy(
        source,
        0.35,
        reference="C 1s reference supplied by caller",
        rationale="explicit calibration example",
    )

    assert np.array_equal(corrected.x, x + 0.35)
    assert np.array_equal(corrected.y, y)
    assert corrected.x[0] > corrected.x[-1]
    assert corrected.key == source.key
    assert corrected.label == source.label
    assert corrected.x_axis.name == "binding_energy"
    assert corrected.x_axis.unit == "eV"
    assert corrected.x_axis.metadata["xps_energy_shift_ev"] == pytest.approx(0.35)
    history = corrected.metadata["processing_history"]
    assert history[-1]["operation"] == "xps.energy_shift"
    assert history[-1]["parameters"]["shift_ev"] == pytest.approx(0.35)
    assert source.metadata.get("processing_history") is None

    with pytest.raises(XPSError, match="already been explicitly corrected"):
        shift_xps_binding_energy(corrected, 0.1)


def test_zero_energy_shift_is_still_explicitly_recorded() -> None:
    x = np.array([1.0, 2.0, 3.0])
    source = _series(x, np.array([2.0, 3.0, 2.0]))
    corrected = shift_xps_binding_energy(source, 0.0, reference="explicit zero reference")
    assert np.array_equal(corrected.x, source.x)
    assert corrected.metadata["processing_history"][-1]["parameters"]["shift_ev"] == 0.0
    with pytest.raises(XPSError, match="already been explicitly corrected"):
        shift_xps_binding_energy(corrected, 0.0)


def test_prepare_region_uses_only_measured_points_and_preserves_direction() -> None:
    x = np.array([10.0, 8.0, 6.0, 4.0, 2.0, 0.0])
    y = np.array([1.0, 2.0, 4.0, 3.0, 2.0, 1.0])
    source = _series(x, y, key="region")

    region = prepare_xps_region(source, 1.0, 7.0)
    assert np.array_equal(region.x, np.array([6.0, 4.0, 2.0]))
    assert np.array_equal(region.y, np.array([4.0, 3.0, 2.0]))
    assert region.x[0] > region.x[-1]
    assert region.metadata["processing_history"][-1]["operation"] == "xps.prepare_region"

    with pytest.raises(XPSError, match="x_min_ev must be <="):
        prepare_xps_region(source, 7.0, 1.0)
    with pytest.raises(XPSError, match="at least 2"):
        prepare_xps_region(source, 5.9, 6.1)

    missing = _series(x, np.array([1.0, 2.0, np.nan, 3.0, 2.0, 1.0]))
    with pytest.raises(XPSError, match="missing/non-finite"):
        prepare_xps_region(missing, 1.0, 7.0)


def test_linear_background_is_endpoint_line_and_direction_equivalent() -> None:
    x = np.linspace(0.0, 10.0, 11)
    y = 2.0 + 0.2 * x + _gaussian(x)
    # Make the endpoint values exactly hand-verifiable.
    y[0] = 2.0
    y[-1] = 4.0

    ascending = linear_xps_background(_series(x, y, key="linear-up"))
    descending = linear_xps_background(_series(x[::-1], y[::-1], key="linear-down"))
    expected = 2.0 + 0.2 * x

    assert np.allclose(ascending.background_y, expected)
    assert np.allclose(descending.background_y[::-1], expected)
    assert ascending.source_direction == "ascending"
    assert descending.source_direction == "descending"
    assert ascending.low_endpoint_intensity == pytest.approx(2.0)
    assert ascending.high_endpoint_intensity == pytest.approx(4.0)
    assert ascending.background_y[0] == pytest.approx(y[0])
    assert ascending.background_y[-1] == pytest.approx(y[-1])


def test_shirley_equal_endpoints_reduce_to_constant_background() -> None:
    x = np.linspace(0.0, 10.0, 501)
    peak = _gaussian(x)
    y = 2.0 + peak
    # Gaussian tails are nonzero numerically; force equal measured endpoints exactly.
    y[0] = 2.0
    y[-1] = 2.0

    result = shirley_xps_background(_series(x, y, key="shirley-constant"))

    assert result.converged
    assert result.iterations == 1
    assert np.allclose(result.background_y, 2.0, atol=1e-12)
    assert result.low_endpoint_intensity == pytest.approx(2.0)
    assert result.high_endpoint_intensity == pytest.approx(2.0)
    assert result.settings["integration"] == "measured_grid_trapezoid"


def test_shirley_ascending_descending_equivalence_and_fixed_point() -> None:
    x = np.linspace(0.0, 10.0, 501)
    y = 2.0 + 0.2 * x + _gaussian(x)
    y[0] = 2.0
    y[-1] = 4.0

    up = shirley_xps_background(_series(x, y, key="shirley-up"))
    down = shirley_xps_background(_series(x[::-1], y[::-1], key="shirley-down"))

    assert up.converged and down.converged
    assert np.allclose(down.background_y[::-1], up.background_y, rtol=1e-9, atol=1e-10)
    assert down.x[0] > down.x[-1]
    assert up.x[0] < up.x[-1]

    # One explicit fixed-point update from the converged result must reproduce it.
    excess = y - up.background_y
    increments = 0.5 * (excess[:-1] + excess[1:]) * np.diff(x)
    cumulative = np.empty_like(y)
    cumulative[-1] = 0.0
    cumulative[:-1] = np.cumsum(increments[::-1])[::-1]
    expected = 4.0 + (2.0 - 4.0) * cumulative / cumulative[0]
    expected[0] = 2.0
    expected[-1] = 4.0
    threshold = (up.absolute_tolerance or 0.0) + (up.relative_tolerance or 0.0) * max(
        1.0, float(np.max(np.abs(expected)))
    )
    assert np.max(np.abs(expected - up.background_y)) <= threshold * 1.05


def test_shirley_zero_integral_and_nonconvergence_fail_explicitly() -> None:
    x = np.linspace(0.0, 10.0, 101)
    pure_line = 2.0 + 0.2 * x
    with pytest.raises(XPSError, match="integral is numerically zero/invalid"):
        shirley_xps_background(_series(x, pure_line))

    y = pure_line + _gaussian(x)
    y[0] = 2.0
    y[-1] = 4.0
    with pytest.raises(XPSError, match="did not converge within 1 iterations"):
        shirley_xps_background(
            _series(x, y),
            relative_tolerance=1e-14,
            absolute_tolerance=1e-14,
            max_iterations=1,
        )


def test_background_result_arrays_are_immutable_and_source_identity_deterministic() -> None:
    x = np.linspace(0.0, 10.0, 101)
    y = 2.0 + _gaussian(x)
    y[0] = y[-1] = 2.0
    source = _series(x, y, key="deterministic")

    first = shirley_xps_background(source)
    second = shirley_xps_background(source)

    assert isinstance(first, XPSBackgroundResult)
    assert first.source_sha256 == second.source_sha256
    assert np.array_equal(first.background_y, second.background_y)
    assert not first.x.flags.writeable
    assert not first.observed_y.flags.writeable
    assert not first.background_y.flags.writeable
    with pytest.raises(ValueError):
        first.background_y[0] = 99.0


def test_numerical_xps_module_import_keeps_matplotlib_lazy() -> None:
    code = r"""
import json
import sys
import catalysis_workbench.experimental.characterization.xps as xps
loaded_matplotlib = any(
    name == "matplotlib" or name.startswith("matplotlib.")
    for name in sys.modules
)
payload = {
    "matplotlib": loaded_matplotlib,
    "exports": sorted(xps.__all__),
}
print(json.dumps(payload))
"""
    completed = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout.strip())
    assert payload["matplotlib"] is False
    assert "shirley_xps_background" in payload["exports"]
