from __future__ import annotations

import subprocess
import sys

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.experimental.echem import (
    TafelError,
    fit_tafel,
    fit_tafel_dataset,
    plot_tafel,
    series_data_sha256,
)
from catalysis_workbench.visualization import FigureSpec, VisualizationError


def _tafel_series(
    *,
    key: str = "cat-a",
    label: str = "Catalyst A",
    slope_v_dec: float = -0.060,
    intercept_v: float = 0.200,
    potential_unit: str = "V",
    current_unit: str = "A/cm^2",
    current_sign: str = "negative",
    reference: str | None = "RHE",
    normalization: str | None = "geometric_area",
) -> Series:
    current_a_cm2 = np.array([1e-4, 2e-4, 5e-4, 1e-3, 2e-3])
    if current_sign == "negative":
        current_a_cm2 *= -1.0
    potential_v = intercept_v + slope_v_dec * np.log10(np.abs(current_a_cm2))

    x = potential_v if potential_unit == "V" else potential_v * 1000.0
    if current_unit == "A/cm^2":
        y = current_a_cm2
    elif current_unit == "mA/cm^2":
        y = current_a_cm2 * 1000.0
    elif current_unit == "uA/cm^2":
        y = current_a_cm2 * 1e6
    else:
        y = current_a_cm2

    x_metadata = {} if reference is None else {"reference": reference}
    y_metadata = {} if normalization is None else {"normalization": normalization}
    return Series(
        x=x,
        y=y,
        key=key,
        label=label,
        x_axis=Axis(
            "potential",
            unit=potential_unit,
            label="Potential",
            metadata=x_metadata,
        ),
        y_axis=Axis(
            "current_density",
            unit=current_unit,
            label="Current density",
            metadata=y_metadata,
        ),
    )


def test_fit_tafel_recovers_signed_synthetic_slope_intercept_and_r_squared():
    source = _tafel_series()
    result = fit_tafel(
        source,
        (0.36, 0.44),
        fit_window_unit="V",
        branch="cathodic",
        current_sign="negative",
    )

    assert result.slope_v_dec == pytest.approx(-0.060, abs=1e-12)
    assert result.slope_mv_dec == pytest.approx(-60.0, abs=1e-9)
    assert result.slope_magnitude_mv_dec == pytest.approx(60.0, abs=1e-9)
    assert result.intercept_v == pytest.approx(0.200, abs=1e-12)
    assert result.r_squared == pytest.approx(1.0, abs=1e-12)
    assert result.n_points == 5
    assert result.branch == "cathodic"
    assert result.current_sign == "negative"
    assert result.current_basis == "geometric_area"
    assert result.potential_reference == "RHE"


def test_fit_tafel_converts_mv_and_ma_cm2_before_regression():
    source = _tafel_series(potential_unit="mV", current_unit="mA/cm^2")
    result = fit_tafel(
        source,
        (360.0, 440.0),
        fit_window_unit="mV",
        branch="cathodic",
        current_sign="negative",
    )

    assert result.slope_mv_dec == pytest.approx(-60.0, abs=1e-9)
    assert result.intercept_v == pytest.approx(0.200, abs=1e-12)
    assert result.fit_window.lower == pytest.approx(0.360)
    assert result.fit_window.upper == pytest.approx(0.440)
    assert result.fit_window.unit == "V"


def test_physical_branch_does_not_silently_define_numeric_current_sign():
    source = _tafel_series(current_sign="positive")
    result = fit_tafel(
        source,
        (0.36, 0.44),
        fit_window_unit="V",
        branch="cathodic",
        current_sign="positive",
    )
    assert result.branch == "cathodic"
    assert result.current_sign == "positive"
    assert result.slope_mv_dec == pytest.approx(-60.0)


def test_anodic_positive_current_preserves_positive_fitted_slope():
    source = _tafel_series(
        slope_v_dec=0.040,
        intercept_v=0.500,
        current_sign="positive",
    )
    result = fit_tafel(
        source,
        (0.33, 0.40),
        fit_window_unit="V",
        branch="anodic",
        current_sign="positive",
    )
    assert result.slope_mv_dec == pytest.approx(40.0, abs=1e-9)
    assert result.slope_magnitude_mv_dec == pytest.approx(40.0, abs=1e-9)


def test_fit_window_is_inclusive_and_source_provenance_is_traceable():
    source = _tafel_series()
    lower = float(np.min(source.x))
    upper = float(np.max(source.x))
    result = fit_tafel(
        source,
        (lower, upper),
        fit_window_unit="V",
        branch="cathodic",
        current_sign="negative",
    )

    assert result.n_points == source.n_points
    assert result.fit_window.n_points == source.n_points
    assert result.provenance.source.sha256 == series_data_sha256(source)
    assert result.provenance.source.key == "cat-a"
    assert result.provenance.source.x_unit == "V"
    assert result.provenance.source.y_unit == "A/cm^2"
    assert dict(result.provenance.parameters)["branch"] == "cathodic"
    assert dict(result.provenance.parameters)["current_sign"] == "negative"
    assert dict(result.provenance.parameters)["potential_reference"] == "RHE"
    assert dict(result.provenance.parameters)["current_density_basis"] == "geometric_area"


def test_result_arrays_are_immutable_float64():
    result = fit_tafel(
        _tafel_series(),
        (0.36, 0.44),
        fit_window_unit="V",
        branch="cathodic",
        current_sign="negative",
    )
    for values in (
        result.log_current_density_a_cm2,
        result.potential_v,
        result.fitted_potential_v,
    ):
        assert values.dtype == np.float64
        assert values.flags.writeable is False
        with pytest.raises(ValueError):
            values[0] = 123.0


def test_nan_outside_window_is_allowed_but_selected_nan_current_fails():
    clean = _tafel_series()
    outside = Series(
        x=np.concatenate(([np.nan], clean.x)),
        y=np.concatenate(([np.nan], clean.y)),
        key=clean.key,
        label=clean.label,
        x_axis=clean.x_axis,
        y_axis=clean.y_axis,
    )
    result = fit_tafel(
        outside,
        (0.36, 0.44),
        fit_window_unit="V",
        branch="cathodic",
        current_sign="negative",
    )
    assert result.n_points == 5

    bad_y = np.array(clean.y, copy=True)
    bad_y[2] = np.nan
    inside = Series(
        x=clean.x,
        y=bad_y,
        key=clean.key,
        label=clean.label,
        x_axis=clean.x_axis,
        y_axis=clean.y_axis,
    )
    with pytest.raises(TafelError, match="must not contain NaN"):
        fit_tafel(
            inside,
            (0.36, 0.44),
            fit_window_unit="V",
            branch="cathodic",
            current_sign="negative",
        )


def test_zero_and_declared_sign_mismatch_fail_explicitly():
    source = _tafel_series()
    zero_y = np.array(source.y, copy=True)
    zero_y[2] = 0.0
    zero = Series(
        x=source.x,
        y=zero_y,
        key=source.key,
        x_axis=source.x_axis,
        y_axis=source.y_axis,
    )
    with pytest.raises(TafelError, match="non-zero"):
        fit_tafel(
            zero,
            (0.36, 0.44),
            fit_window_unit="V",
            branch="cathodic",
            current_sign="negative",
        )

    with pytest.raises(TafelError, match="contradict"):
        fit_tafel(
            source,
            (0.36, 0.44),
            fit_window_unit="V",
            branch="cathodic",
            current_sign="positive",
        )


def test_fit_requires_three_points_and_non_degenerate_log_current():
    source = _tafel_series()
    with pytest.raises(TafelError, match="at least three"):
        fit_tafel(
            source,
            (0.419, 0.441),
            fit_window_unit="V",
            branch="cathodic",
            current_sign="negative",
        )

    constant_current = Series(
        x=(0.36, 0.38, 0.40),
        y=(-1e-3, -1e-3, -1e-3),
        key="constant",
        x_axis=source.x_axis,
        y_axis=source.y_axis,
    )
    with pytest.raises(TafelError, match="distinct current"):
        fit_tafel(
            constant_current,
            (0.35, 0.41),
            fit_window_unit="V",
            branch="cathodic",
            current_sign="negative",
        )


def test_wrong_axes_units_reference_and_normalization_fail():
    source = _tafel_series()
    wrong_axis = Series(
        x=source.x,
        y=source.y,
        key="wrong",
        x_axis=Axis("time", unit="s"),
        y_axis=source.y_axis,
    )
    with pytest.raises(TafelError, match="x_axis.name"):
        fit_tafel(
            wrong_axis,
            (0.36, 0.44),
            fit_window_unit="V",
            branch="cathodic",
            current_sign="negative",
        )

    with pytest.raises(TafelError, match="unsupported potential unit"):
        fit_tafel(
            _tafel_series(potential_unit="s"),
            (0.36, 0.44),
            fit_window_unit="V",
            branch="cathodic",
            current_sign="negative",
        )
    with pytest.raises(TafelError, match="reference"):
        fit_tafel(
            _tafel_series(reference=None),
            (0.36, 0.44),
            fit_window_unit="V",
            branch="cathodic",
            current_sign="negative",
        )
    with pytest.raises(TafelError, match="normalization"):
        fit_tafel(
            _tafel_series(normalization=None),
            (0.36, 0.44),
            fit_window_unit="V",
            branch="cathodic",
            current_sign="negative",
        )


def test_malformed_window_branch_and_sign_fail():
    source = _tafel_series()
    with pytest.raises(TafelError, match="lower bound"):
        fit_tafel(
            source,
            (0.44, 0.36),
            fit_window_unit="V",
            branch="cathodic",
            current_sign="negative",
        )
    with pytest.raises(TafelError, match="branch"):
        fit_tafel(
            source,
            (0.36, 0.44),
            fit_window_unit="V",
            branch="unknown",  # type: ignore[arg-type]
            current_sign="negative",
        )
    with pytest.raises(TafelError, match="current_sign"):
        fit_tafel(
            source,
            (0.36, 0.44),
            fit_window_unit="V",
            branch="cathodic",
            current_sign="auto",  # type: ignore[arg-type]
        )


def test_fit_tafel_dataset_preserves_order_and_supports_key_mapped_parameters():
    first = _tafel_series(key="a", label="A")
    second = _tafel_series(
        key="b",
        label="B",
        slope_v_dec=-0.080,
        intercept_v=0.100,
        current_sign="positive",
    )
    dataset = Dataset([first, second])
    results = fit_tafel_dataset(
        dataset,
        {"a": (0.36, 0.44), "b": (0.31, 0.43)},
        fit_window_unit={"a": "V", "b": "V"},
        branch={"a": "cathodic", "b": "cathodic"},
        current_sign={"a": "negative", "b": "positive"},
    )

    assert [item.provenance.source.key for item in results] == ["a", "b"]
    assert results[0].slope_mv_dec == pytest.approx(-60.0)
    assert results[1].slope_mv_dec == pytest.approx(-80.0)
    assert results[1].current_sign == "positive"


def test_fit_tafel_dataset_requires_complete_stable_key_mappings():
    first = _tafel_series(key="a")
    second = _tafel_series(key="b")
    dataset = Dataset([first, second])
    with pytest.raises(TafelError, match="missing"):
        fit_tafel_dataset(
            dataset,
            {"a": (0.36, 0.44)},
            fit_window_unit="V",
            branch="cathodic",
            current_sign="negative",
        )
    with pytest.raises(TafelError, match="unknown"):
        fit_tafel_dataset(
            dataset,
            {"a": (0.36, 0.44), "b": (0.36, 0.44), "c": (0.36, 0.44)},
            fit_window_unit="V",
            branch="cathodic",
            current_sign="negative",
        )

    no_key = Dataset([_tafel_series(key="")])
    with pytest.raises(TafelError, match="non-empty Series.key"):
        fit_tafel_dataset(
            no_key,
            {"x": (0.36, 0.44)},
            fit_window_unit="V",
            branch="cathodic",
            current_sign="negative",
        )


def test_plot_tafel_uses_marker_points_and_line_fit_with_reference_label():
    result = fit_tafel(
        _tafel_series(),
        (0.36, 0.44),
        fit_window_unit="V",
        branch="cathodic",
        current_sign="negative",
    )
    _, ax = plot_tafel(result)

    assert len(ax.lines) == 2
    assert ax.lines[0].get_marker() == "o"
    assert ax.lines[0].get_linestyle() == "None"
    assert ax.lines[1].get_marker() in {"", "None", "none", " "}
    assert ax.lines[1].get_linestyle() == "-"
    assert ax.get_xlabel() == "log10(|j| / A cm^-2)"
    assert ax.get_ylabel() == "Potential (V vs RHE)"


def test_plot_tafel_multi_result_inherits_reference_and_basis_compatibility_guards():
    first = fit_tafel(
        _tafel_series(key="a", normalization="geometric_area"),
        (0.36, 0.44),
        fit_window_unit="V",
        branch="cathodic",
        current_sign="negative",
    )
    second = fit_tafel(
        _tafel_series(key="b", normalization="ECSA"),
        (0.36, 0.44),
        fit_window_unit="V",
        branch="cathodic",
        current_sign="negative",
    )
    with pytest.raises(VisualizationError, match="normalization"):
        plot_tafel((first, second), FigureSpec())


def test_numerical_echem_import_remains_matplotlib_lazy_in_fresh_interpreter():
    code = (
        "import sys; import catalysis_workbench.experimental.echem; "
        "assert 'matplotlib' not in sys.modules"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
