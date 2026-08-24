"""Smoke representative reviewed workflows from an installed wheel.

This file is intentionally a plain Python program rather than a pytest module. CI runs it
inside a fresh virtual environment that installs the built wheel, proving that public
imports and package data/code layout work independently of the repository's editable
source-tree installation.
"""

from importlib import import_module
from importlib.metadata import version as distribution_version
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

import catalysis_workbench
from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.characterization import (
    RamanBand,
    RamanProcessingConfig,
    XRDProcessingConfig,
    id_ig_ratio,
    plot_raman,
    plot_xrd,
    process_raman,
    process_xrd,
)
from catalysis_workbench.experimental.echem import (
    FARADAY_CONSTANT_C_MOL,
    CVSweepPair,
    LSVProcessingConfig,
    StabilityAnalysisConfig,
    StabilityWindowSpec,
    analyze_stability,
    ecsa_from_cdl,
    faradaic_efficiency_from_amount,
    fit_cdl,
    fit_koutecky_levich,
    fit_tafel,
    kl_electron_number,
    normalize_activity,
    plot_lsv,
    process_lsv,
    rhe_offset_from_she,
    rotation_rate_to_rad_s,
    rrde_metrics,
    turnover_frequency_from_rate,
)
from catalysis_workbench.io import read_csv
from catalysis_workbench.visualization import export_figure, get_preset

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "data"
PUBLIC_MODULES = (
    "catalysis_workbench.core",
    "catalysis_workbench.io",
    "catalysis_workbench.processing",
    "catalysis_workbench.experimental.echem",
    "catalysis_workbench.experimental.characterization",
    "catalysis_workbench.visualization",
)


def _assert_close(actual: float, expected: float, *, tolerance: float = 1e-10) -> None:
    scale = max(1.0, abs(expected))
    assert abs(actual - expected) <= tolerance * scale, (actual, expected)


def _assert_installed_import() -> None:
    module_path = Path(catalysis_workbench.__file__).resolve()
    source_tree = (ROOT / "src").resolve()
    try:
        module_path.relative_to(source_tree)
    except ValueError:
        return
    raise AssertionError(f"smoke test imported repository source tree: {module_path}")


def _assert_version_consistency() -> None:
    installed = distribution_version("catalysis-workbench")
    assert installed == catalysis_workbench.__version__, (
        "distribution/package version mismatch: "
        f"metadata={installed!r}, __version__={catalysis_workbench.__version__!r}"
    )


def _assert_public_exports() -> None:
    for module_name in PUBLIC_MODULES:
        module = import_module(module_name)
        exports = tuple(getattr(module, "__all__", ()))
        assert exports, f"documented public module has empty __all__: {module_name}"
        assert len(exports) == len(set(exports)), f"duplicate __all__ names: {module_name}"
        for name in exports:
            assert isinstance(name, str) and name, f"invalid __all__ entry in {module_name}"
            getattr(module, name)


def _smoke_lsv(output: Path) -> None:
    raw = read_csv(
        EXAMPLES / "lsv_example.csv",
        x="Potential [V]",
        y="Current [mA]",
        source_id="smoke-lsv",
    )
    rhe_offset_v = rhe_offset_from_she(
        reference_potential_vs_she_v=0.210,
        ph=13.0,
        temperature_k=298.15,
    )
    processed = process_lsv(
        raw[0],
        LSVProcessingConfig(
            rhe_offset_v=rhe_offset_v,
            source_reference="Ag/AgCl",
            resistance_ohm=5.0,
            electrode_area_cm2=0.196,
            normalize_to_current_density=True,
        ),
    )
    assert processed.x_axis.metadata["reference"] == "RHE"
    assert processed.y_axis.name == "current_density"
    spec = get_preset("publication").with_export(dpi=120)
    fig, _ = plot_lsv(processed, spec)
    path = export_figure(fig, output / "lsv.png", spec=spec)
    assert path.is_file() and path.stat().st_size > 0


def _smoke_xrd(output: Path) -> None:
    raw = read_csv(
        EXAMPLES / "xrd_example.csv",
        x="2theta [deg]",
        y="Intensity [counts]",
        source_id="smoke-xrd",
    )
    processed = process_xrd(
        raw[0],
        XRDProcessingConfig(x_min_deg=20, x_max_deg=80, normalization="max"),
    )
    assert processed.y_axis.name == "normalized_intensity"
    spec = get_preset("publication")
    fig, _ = plot_xrd(processed, spec)
    path = export_figure(fig, output / "xrd.svg", spec=spec)
    assert path.is_file() and path.stat().st_size > 0


def _smoke_raman(output: Path) -> None:
    raw = read_csv(
        EXAMPLES / "raman_example.csv",
        x="Raman shift [cm^-1]",
        y="Intensity [counts]",
        source_id="smoke-raman",
    )
    processed = process_raman(
        raw[0],
        RamanProcessingConfig(
            shift_min_cm1=1000,
            shift_max_cm1=1800,
            normalization="max",
        ),
    )
    ratio = id_ig_ratio(
        processed,
        RamanBand(1250, 1450, "D"),
        RamanBand(1550, 1650, "G"),
        metric="height",
    )
    assert ratio.value > 0
    spec = get_preset("publication")
    fig, _ = plot_raman(processed, spec)
    path = export_figure(fig, output / "raman.pdf", spec=spec)
    assert path.is_file() and path.stat().st_size > 0


def _smoke_tafel() -> None:
    current = -np.array([1e-4, 2e-4, 5e-4, 1e-3, 2e-3])
    potential = 0.200 - 0.060 * np.log10(np.abs(current))
    source = Series(
        x=potential,
        y=current,
        key="smoke-tafel",
        x_axis=Axis("potential", unit="V", metadata={"reference": "RHE"}),
        y_axis=Axis(
            "current_density",
            unit="A/cm^2",
            metadata={"normalization": "geometric_area"},
        ),
    )
    result = fit_tafel(
        source,
        (0.36, 0.44),
        fit_window_unit="V",
        branch="cathodic",
        current_sign="negative",
    )
    _assert_close(result.slope_v_dec, -0.060)
    _assert_close(result.intercept_v, 0.200)
    _assert_close(result.r_squared, 1.0)


def _smoke_fe_activity_tof() -> None:
    fe = faradaic_efficiency_from_amount(
        1.0,
        "umol",
        -0.5,
        "C",
        electron_number=2,
    )
    expected_fe = 2.0 * FARADAY_CONSTANT_C_MOL * 1e-6 / 0.5
    _assert_close(fe.fraction.item(), expected_fe)
    _assert_close(fe.denominator_canonical.item(), -0.5)

    activity = normalize_activity(
        [-2.0],
        current_unit="mA",
        current_basis="current",
        basis="catalyst_mass",
        denominator_value=2.0,
        denominator_unit="mg",
        output_unit="mA/mg",
    )
    _assert_close(activity.values.item(), -1.0)

    tof = turnover_frequency_from_rate(
        [2.0],
        rate_unit="umol/s",
        inventory_basis="active_sites",
        inventory_value=1.0,
        inventory_unit="umol",
    )
    assert tof.metric_name == "TOF"
    _assert_close(tof.values.item(), 2.0)

    tofapp = turnover_frequency_from_rate(
        [1.0],
        rate_unit="umol/s",
        inventory_basis="total_metal",
        inventory_value=1.0,
        inventory_unit="umol",
    )
    assert tofapp.metric_name == "TOFapp"


def _smoke_cdl_ecsa() -> None:
    potential_axis = Axis("potential", unit="V", metadata={"reference": "RHE"})
    pairs = []
    for scan_rate_mv_s in (10.0, 20.0, 50.0, 100.0):
        scan_rate_v_s = scan_rate_mv_s * 1e-3
        delta_a = 0.02 * scan_rate_v_s + 1e-4
        anodic = Series(
            x=(0.4, 0.5, 0.6),
            y=(delta_a * 1e3,) * 3,
            key=f"smoke-cdl-{scan_rate_mv_s:g}-a",
            x_axis=potential_axis,
            y_axis=Axis("current", unit="mA"),
        )
        cathodic = Series(
            x=(0.6, 0.5, 0.4),
            y=(-delta_a * 1e3,) * 3,
            key=f"smoke-cdl-{scan_rate_mv_s:g}-c",
            x_axis=potential_axis,
            y_axis=Axis("current", unit="mA"),
        )
        pairs.append(
            CVSweepPair(
                key=f"scan-{scan_rate_mv_s:g}",
                anodic=anodic,
                cathodic=cathodic,
                scan_rate_value=scan_rate_mv_s,
                scan_rate_unit="mV/s",
            )
        )
    cdl = fit_cdl(tuple(pairs), potential_value=0.5, sampling_method="exact")
    _assert_close(cdl.slope, 0.02)
    _assert_close(cdl.intercept, 1e-4)
    ecsa = ecsa_from_cdl(
        cdl,
        specific_capacitance_value=40.0,
        specific_capacitance_unit="uF/cm^2",
        specific_capacitance_basis="installed-wheel synthetic smoke value",
    )
    _assert_close(ecsa.ecsa_cm2, 500.0)


def _smoke_stability() -> None:
    source = Series(
        x=(0.0, 1.0, 2.0, 3.0, 4.0),
        y=(-10.0, -10.0, -10.0, -10.0, -10.0),
        key="smoke-stability",
        x_axis=Axis("time", unit="h", metadata={"time_basis": "running_only"}),
        y_axis=Axis(
            "current_density",
            unit="mA/cm^2",
            metadata={"normalization": "geometric_area"},
        ),
    )
    config = StabilityAnalysisConfig(
        analysis_window=StabilityWindowSpec(0.0, 4.0, "h"),
        baseline_window=StabilityWindowSpec(0.0, 1.0, "h"),
        final_window=StabilityWindowSpec(3.0, 4.0, "h"),
        retention_mode="signed",
        missing_policy="reject",
    )
    result = analyze_stability(source, config)
    _assert_close(result.retention_percent, 100.0)
    _assert_close(result.drift_slope_per_s, 0.0)


def _smoke_rrde() -> None:
    axis = Axis("potential", unit="V", metadata={"reference": "RHE"})
    disk = Series(
        x=(0.8, 0.7),
        y=(-1.0, -2.0),
        key="smoke-disk",
        x_axis=axis,
        y_axis=Axis("current", unit="mA"),
    )
    ring = Series(
        x=(0.8, 0.7),
        y=(100.0, 200.0),
        key="smoke-ring",
        x_axis=axis,
        y_axis=Axis("current", unit="uA"),
    )
    result = rrde_metrics(
        disk,
        ring,
        collection_efficiency=0.5,
        current_mode="magnitude",
    )
    _assert_close(result.electron_number[0], 10.0 / 3.0)
    _assert_close(result.peroxide_percent[0], 100.0 / 3.0)


def _smoke_koutecky_levich() -> None:
    rotation = np.array([400.0, 900.0, 1600.0, 2500.0])
    omega = rotation_rate_to_rad_s(rotation, "rpm", allow_nan=False)
    diffusion = 1.9e-5
    viscosity = 0.01
    concentration = 1.2e-6
    n_true = 4.0
    transport = (
        0.62
        * FARADAY_CONSTANT_C_MOL
        * diffusion ** (2.0 / 3.0)
        * viscosity ** (-1.0 / 6.0)
        * concentration
    )
    slope = 1.0 / (n_true * transport)
    reciprocal_current = 10.0 + slope * omega ** -0.5
    source = Series(
        x=rotation,
        y=1.0 / reciprocal_current,
        key="smoke-kl",
        x_axis=Axis("rotation_rate", unit="rpm"),
        y_axis=Axis(
            "current_density",
            unit="A/cm^2",
            metadata={"normalization": "geometric_area"},
        ),
    )
    fit = fit_koutecky_levich(
        source,
        (400.0, 2500.0),
        fit_window_unit="rpm",
        current_mode="nonnegative",
    )
    derived = kl_electron_number(
        fit,
        diffusion_coefficient_cm2_s=diffusion,
        kinematic_viscosity_cm2_s=viscosity,
        concentration_mol_cm3=concentration,
    )
    _assert_close(fit.r_squared, 1.0)
    _assert_close(derived.electron_number, n_true)


def _smoke_v0_2_echem() -> None:
    _smoke_tafel()
    _smoke_fe_activity_tof()
    _smoke_cdl_ecsa()
    _smoke_stability()
    _smoke_rrde()
    _smoke_koutecky_levich()


def main() -> None:
    _assert_installed_import()
    _assert_version_consistency()
    _assert_public_exports()
    _smoke_v0_2_echem()
    with TemporaryDirectory() as directory:
        output = Path(directory)
        _smoke_lsv(output)
        _smoke_xrd(output)
        _smoke_raman(output)


if __name__ == "__main__":
    main()
