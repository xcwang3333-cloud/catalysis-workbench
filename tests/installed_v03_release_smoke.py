"""Unified Gate-A smoke for reviewed v0.3 APIs from an installed wheel.

CI runs this plain Python program inside a fresh virtual environment containing only
the built wheel and its dependencies. The checks are intentionally hand-verifiable and
cover the four scientific modules frozen into the v0.3 release scope without adding new
analysis algorithms.
"""

from __future__ import annotations

import os
import sys
from importlib import import_module
from importlib.metadata import version as distribution_version

import numpy as np

import catalysis_workbench
import catalysis_workbench.experimental.characterization as characterization
from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.characterization import (
    CompositionMeasurement,
    CompositionTable,
    FTIRBand,
    FTIRProcessingConfig,
    SorptionCondition,
    SorptionWindow,
    ThermalWindow,
    convert_composition_unit,
    convert_relative_pressure,
    derive_dtg,
    fit_ftir_baseline,
    measure_ftir_band,
    measure_thermal_window,
    normalize_tga_mass,
    prepare_sorption_series,
    process_ftir,
    solution_concentration_to_bulk_mass_fraction,
    summarize_composition_replicates,
    summarize_sorption_window,
    transmittance_to_absorbance,
)

PUBLIC_MODULES = (
    "catalysis_workbench.core",
    "catalysis_workbench.io",
    "catalysis_workbench.processing",
    "catalysis_workbench.experimental.echem",
    "catalysis_workbench.experimental.characterization",
    "catalysis_workbench.visualization",
)


def _close(actual: float, expected: float, tolerance: float = 1e-10) -> None:
    scale = max(1.0, abs(expected))
    assert abs(actual - expected) <= tolerance * scale, (actual, expected)


def _assert_gate_version() -> None:
    runtime = catalysis_workbench.__version__
    installed = distribution_version("catalysis-workbench")
    assert runtime == installed, (runtime, installed)
    expected = os.environ.get("CATALYSIS_WORKBENCH_EXPECTED_VERSION")
    assert expected, "CATALYSIS_WORKBENCH_EXPECTED_VERSION must be set by the release gate"
    assert runtime == expected, (runtime, expected)


def _assert_characterization_import_is_matplotlib_lazy() -> None:
    assert characterization.__name__.endswith("experimental.characterization")
    loaded = [
        name
        for name in sys.modules
        if name == "matplotlib" or name.startswith("matplotlib.")
    ]
    assert not loaded, f"numerical characterization import loaded Matplotlib: {loaded!r}"


def _assert_public_exports() -> None:
    for module_name in PUBLIC_MODULES:
        module = import_module(module_name)
        exports = tuple(getattr(module, "__all__", ()))
        assert exports, f"documented public module has empty __all__: {module_name}"
        assert len(exports) == len(set(exports)), f"duplicate __all__ names: {module_name}"
        for name in exports:
            assert isinstance(name, str) and name, f"invalid __all__ entry: {module_name}"
            getattr(module, name)


def _smoke_ftir() -> None:
    transmittance = Series(
        x=(1200.0, 1100.0, 1000.0),
        y=(100.0, 50.0, 10.0),
        key="release-ftir-transmittance",
        x_axis=Axis("wavenumber", unit="cm^-1"),
        y_axis=Axis("transmittance", unit="%"),
    )
    absorbance = transmittance_to_absorbance(transmittance, input_scale="percent")
    _close(float(absorbance.y[0]), 0.0)
    _close(float(absorbance.y[1]), np.log10(2.0))
    _close(float(absorbance.y[2]), 1.0)

    wavenumber = np.array([2000.0, 1800.0, 1600.0, 1400.0, 1200.0, 1000.0])
    linear_baseline = 0.001 * wavenumber + 0.2
    source = Series(
        x=wavenumber,
        y=linear_baseline + np.array([0.0, 0.0, 2.0, 1.0, 0.0, 0.0]),
        key="release-ftir-band",
        x_axis=Axis("wavenumber", unit="cm^-1"),
        y_axis=Axis("absorbance"),
    )
    baseline = fit_ftir_baseline(
        source,
        ((1000.0, 1200.0), (1800.0, 2000.0)),
        degree=1,
    )
    corrected = process_ftir(
        source,
        FTIRProcessingConfig(wavenumber_min_cm1=1200.0, wavenumber_max_cm1=1800.0),
        baseline=baseline,
    )
    band = measure_ftir_band(corrected, FTIRBand(1200.0, 1800.0, "release"))
    _close(band.area, 600.0)
    assert band.source_direction == "descending"
    assert band.integration_direction == "low_to_high_wavenumber"


def _smoke_thermal() -> None:
    tga = Series(
        x=(100.0, 200.0, 300.0, 400.0),
        y=(10.0, 9.0, 8.0, 7.0),
        key="release-tga",
        x_axis=Axis("temperature", unit="°C"),
        y_axis=Axis("mass", unit="mg"),
    )
    normalized = normalize_tga_mass(tga, output="percent", reference="first_point")
    np.testing.assert_allclose(normalized.y, (100.0, 90.0, 80.0, 70.0))

    dtg = derive_dtg(tga, sign_mode="mass_loss_positive")
    np.testing.assert_allclose(dtg.y, 0.01)
    assert dtg.y_axis.unit == "mg/°C"

    tpr = Series(
        x=(100.0, 200.0, 300.0, 400.0, 500.0),
        y=(0.0, 1.0, 3.0, 1.0, 0.0),
        key="release-tpr",
        x_axis=Axis("temperature", unit="°C"),
        y_axis=Axis("detector_signal", unit="a.u."),
    )
    window = measure_thermal_window(
        tpr,
        ThermalWindow(150.0, 450.0),
        technique="tpr",
        extremum_mode="maximum",
        area_mode="net",
    )
    _close(window.extremum_temperature, 300.0)
    _close(window.extremum_value, 3.0)
    _close(window.area, 475.0)


def _smoke_sorption() -> None:
    adsorption = prepare_sorption_series(
        Series(
            x=(0.01, 0.10, 0.50, 0.90),
            y=(0.2, 1.0, 3.0, 5.0),
            key="release-sorption",
            x_axis=Axis("relative_pressure", unit="1"),
            y_axis=Axis("adsorbed_quantity", unit="mmol/g"),
        ),
        SorptionCondition("N2", 77.0, "adsorption"),
    )
    assert adsorption.metadata["sorption_branch"] == "adsorption"
    assert adsorption.metadata["sorption_source_direction"] == "ascending"

    percent = convert_relative_pressure(adsorption, target_unit="percent")
    np.testing.assert_allclose(percent.x, (1.0, 10.0, 50.0, 90.0))
    assert percent.x_axis.unit == "%"

    summary = summarize_sorption_window(adsorption, SorptionWindow(0.05, 0.80))
    assert summary.n_measured_points == 2
    _close(summary.minimum_loading, 1.0)
    _close(summary.maximum_loading, 3.0)


def _smoke_composition() -> None:
    solution = CompositionMeasurement(
        key="release-solution",
        sample_key="sample-a",
        element="Pb",
        analyte="208Pb",
        value=10.0,
        unit="mg/L",
        basis="solution_concentration",
    )
    bulk = solution_concentration_to_bulk_mass_fraction(
        solution,
        sample_mass=50.0,
        sample_mass_unit="mg",
        final_digest_volume=25.0,
        final_digest_volume_unit="mL",
        dilution_factor=2.0,
        target_unit="wt%",
    )
    _close(bulk.value, 1.0)
    _close(convert_composition_unit(bulk, target_unit="mg/g").value, 10.0)

    replicates = CompositionTable(
        (
            CompositionMeasurement(
                key="release-pb-1",
                sample_key="sample-a",
                element="Pb",
                analyte="208Pb",
                replicate_key="1",
                value=0.9,
                unit="wt%",
                basis="bulk_mass_fraction",
            ),
            CompositionMeasurement(
                key="release-pb-2",
                sample_key="sample-a",
                element="Pb",
                analyte="208Pb",
                replicate_key="2",
                value=1.1,
                unit="wt%",
                basis="bulk_mass_fraction",
            ),
        )
    )
    summary = summarize_composition_replicates(replicates)[0]
    _close(summary.mean, 1.0)
    _close(summary.standard_deviation or 0.0, np.sqrt(0.02))
    _close(summary.rsd_percent or 0.0, 100.0 * np.sqrt(0.02))
    assert summary.n == 2


def main() -> None:
    _assert_characterization_import_is_matplotlib_lazy()
    _assert_gate_version()
    _assert_public_exports()
    _smoke_ftir()
    _smoke_thermal()
    _smoke_sorption()
    _smoke_composition()


if __name__ == "__main__":
    main()
