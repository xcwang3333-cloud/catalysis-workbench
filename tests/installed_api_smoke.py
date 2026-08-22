"""Smoke representative v0.1 workflows from an installed wheel.

This file is intentionally a plain Python program rather than a pytest module. CI runs it
inside a fresh virtual environment that installs the built wheel, proving that public
imports and package data/code layout work independently of the repository's editable
source-tree installation.
"""

from importlib import import_module
from importlib.metadata import version as distribution_version
from pathlib import Path
from tempfile import TemporaryDirectory

import catalysis_workbench
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
    LSVProcessingConfig,
    plot_lsv,
    process_lsv,
    rhe_offset_from_she,
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


def main() -> None:
    _assert_installed_import()
    _assert_version_consistency()
    _assert_public_exports()
    with TemporaryDirectory() as directory:
        output = Path(directory)
        _smoke_lsv(output)
        _smoke_xrd(output)
        _smoke_raman(output)


if __name__ == "__main__":
    main()
