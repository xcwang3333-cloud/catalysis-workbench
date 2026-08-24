"""Scientific-contract regressions for quantitative stability analysis."""

from __future__ import annotations

import subprocess
import sys

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.experimental.echem import (
    StabilityAnalysisConfig,
    StabilityError,
    StabilityWindowSpec,
    analyze_stability,
    analyze_stability_dataset,
    series_data_sha256,
    validate_stability_series,
)


def _series(
    values,
    *,
    times=(0.0, 1.0, 2.0, 3.0, 4.0),
    time_unit="h",
    key="cat",
    label="Catalyst",
    kind="current_density",
    unit="mA/cm^2",
    reference=None,
    normalization="geometric_area",
) -> Series:
    metadata = {}
    if reference is not None:
        metadata["reference"] = reference
    if normalization is not None:
        metadata["normalization"] = normalization
    return Series(
        x=times,
        y=values,
        key=key,
        label=label,
        x_axis=Axis("time", unit=time_unit, metadata={"time_basis": "running_only"}),
        y_axis=Axis(kind, unit=unit, metadata=metadata),
    )


def _config(
    *,
    analysis=(0.0, 4.0),
    baseline=(0.0, 1.0),
    final=(3.0, 4.0),
    unit="h",
    retention_mode="signed",
    missing_policy="reject",
) -> StabilityAnalysisConfig:
    return StabilityAnalysisConfig(
        analysis_window=StabilityWindowSpec(*analysis, unit),
        baseline_window=StabilityWindowSpec(*baseline, unit),
        final_window=StabilityWindowSpec(*final, unit),
        retention_mode=retention_mode,
        missing_policy=missing_policy,
    )


def test_constant_trace_has_zero_drift_and_perfect_retention():
    result = analyze_stability(_series([10.0] * 5), _config())
    assert result.initial_value == pytest.approx(10.0)
    assert result.final_value == pytest.approx(10.0)
    assert result.baseline_mean == pytest.approx(10.0)
    assert result.final_mean == pytest.approx(10.0)
    assert result.absolute_change == pytest.approx(0.0)
    assert result.retention_fraction == pytest.approx(1.0)
    assert result.retention_percent == pytest.approx(100.0)
    assert result.relative_change_percent == pytest.approx(0.0)
    assert result.drift_slope_per_s == pytest.approx(0.0, abs=1e-15)
    assert result.drift_r_squared == pytest.approx(1.0)


def test_linear_drift_uses_canonical_seconds_and_free_intercept():
    # y = 2 + 0.5 * t_hours -> slope = 0.5 / 3600 y/s
    values = [2.0, 2.5, 3.0, 3.5, 4.0]
    result = analyze_stability(_series(values), _config())
    assert result.drift_slope_per_s == pytest.approx(0.5 / 3600.0)
    assert result.drift_intercept == pytest.approx(2.0)
    assert result.drift_r_squared == pytest.approx(1.0)
    assert result.drift_unit == "mA/cm^2/s"


def test_noisy_window_means_not_single_endpoints_define_retention():
    source = _series([9.0, 11.0, 10.0, 8.0, 10.0])
    result = analyze_stability(source, _config())
    assert result.initial_value == pytest.approx(9.0)
    assert result.final_value == pytest.approx(10.0)
    assert result.baseline_mean == pytest.approx(10.0)
    assert result.final_mean == pytest.approx(9.0)
    assert result.retention_percent == pytest.approx(90.0)
    assert result.absolute_change == pytest.approx(-1.0)


def test_signed_cathodic_current_preserved_and_magnitude_mode_explicit():
    source = _series([-10.0, -10.0, -9.0, -8.0, -8.0])
    signed = analyze_stability(source, _config(retention_mode="signed"))
    magnitude = analyze_stability(source, _config(retention_mode="magnitude"))
    assert signed.baseline_mean == pytest.approx(-10.0)
    assert signed.final_mean == pytest.approx(-8.0)
    assert signed.absolute_change == pytest.approx(2.0)
    assert signed.retention_percent == pytest.approx(80.0)
    assert magnitude.retention_percent == pytest.approx(80.0)
    assert signed.config.retention_mode == "signed"
    assert magnitude.config.retention_mode == "magnitude"


def test_signed_mode_can_expose_sign_reversal_without_hidden_absolute_value():
    source = _series([-10.0, -10.0, 0.0, 5.0, 5.0])
    signed = analyze_stability(source, _config())
    magnitude = analyze_stability(source, _config(retention_mode="magnitude"))
    assert signed.retention_percent == pytest.approx(-50.0)
    assert magnitude.retention_percent == pytest.approx(50.0)


def test_time_units_convert_consistently():
    hours = analyze_stability(_series([1, 2, 3, 4, 5]), _config())
    minutes = analyze_stability(
        _series(
            [1, 2, 3, 4, 5],
            times=(0, 60, 120, 180, 240),
            time_unit="min",
        ),
        _config(
            analysis=(0, 240), baseline=(0, 60), final=(180, 240), unit="min"
        ),
    )
    seconds = analyze_stability(
        _series(
            [1, 2, 3, 4, 5],
            times=(0, 3600, 7200, 10800, 14400),
            time_unit="s",
        ),
        _config(
            analysis=(0, 14400),
            baseline=(0, 3600),
            final=(10800, 14400),
            unit="s",
        ),
    )
    assert hours.drift_slope_per_s == pytest.approx(minutes.drift_slope_per_s)
    assert hours.drift_slope_per_s == pytest.approx(seconds.drift_slope_per_s)
    assert hours.retention_fraction == pytest.approx(minutes.retention_fraction)
    assert hours.retention_fraction == pytest.approx(seconds.retention_fraction)


def test_default_missing_policy_rejects_and_explicit_omit_records_count():
    source = _series([10.0, np.nan, 9.0, 8.0, 8.0])
    with pytest.raises(StabilityError, match="missing y values"):
        analyze_stability(source, _config())
    result = analyze_stability(source, _config(missing_policy="omit"))
    assert result.n_missing_omitted == 1
    assert result.analysis_window.n_missing == 1
    assert result.analysis_window.n_points == 4
    assert result.baseline_mean == pytest.approx(10.0)


def test_nan_outside_analysis_interval_does_not_affect_declared_metrics():
    source = _series([np.nan, 10.0, 9.0, 8.0, 8.0])
    config = _config(analysis=(1, 4), baseline=(1, 1), final=(3, 4))
    result = analyze_stability(source, config)
    assert result.n_missing_omitted == 0
    assert result.initial_value == pytest.approx(10.0)


def test_zero_retention_denominator_fails_explicitly():
    source = _series([0.0, 0.0, 1.0, 2.0, 2.0])
    with pytest.raises(StabilityError, match="baseline denominator"):
        analyze_stability(source, _config())


def test_time_axis_must_be_supported_finite_and_strictly_increasing():
    with pytest.raises(StabilityError, match="strictly increasing"):
        analyze_stability(
            _series([1, 2, 3, 4, 5], times=(0, 1, 1, 3, 4)),
            _config(),
        )
    with pytest.raises(StabilityError):
        validate_stability_series(
            _series([1, 2, 3, 4, 5], time_unit="fortnight")
        )


def test_windows_must_be_inside_data_and_contain_measured_points():
    source = _series([1, 2, 3, 4, 5])
    with pytest.raises(StabilityError, match="outside the measured time range"):
        analyze_stability(
            source,
            _config(analysis=(-1, 4), baseline=(-1, 0), final=(3, 4)),
        )
    config = _config(baseline=(0.25, 0.5), final=(3, 4))
    with pytest.raises(StabilityError, match="no usable measured points"):
        analyze_stability(source, config)


def test_window_chronology_is_explicit():
    with pytest.raises(StabilityError, match="baseline_window"):
        _config(baseline=(2, 3), final=(2.5, 4))
    with pytest.raises(StabilityError, match="inside analysis_window"):
        _config(analysis=(1, 4), baseline=(0, 1), final=(3, 4))


def test_analysis_window_requires_at_least_two_usable_points():
    source = _series([1, 2, 3, 4, 5])
    config = _config(analysis=(1, 1.5), baseline=(1, 1), final=(1, 1))
    # Config itself rejects zero-duration analysis if exact same bounds are used;
    # this interval has positive duration but contains only one measured point.
    with pytest.raises(StabilityError, match="at least two"):
        analyze_stability(source, config)


def test_supported_y_semantics_and_required_metadata():
    current = _series(
        [1, 2, 3, 4, 5],
        kind="current",
        unit="mA",
        normalization=None,
    )
    validate_stability_series(current)

    potential = _series(
        [0.5] * 5,
        kind="potential",
        unit="V",
        reference="RHE",
        normalization=None,
    )
    validate_stability_series(potential)

    fe = _series(
        [90, 91, 92, 93, 94],
        kind="faradaic_efficiency",
        unit="%",
        normalization=None,
    )
    validate_stability_series(fe)

    activity = _series(
        [1, 1, 1, 1, 1],
        kind="activity",
        unit="A/g",
        normalization="catalyst_mass",
    )
    validate_stability_series(activity)

    with pytest.raises(StabilityError, match="reference"):
        validate_stability_series(
            _series(
                [0.5] * 5,
                kind="potential",
                unit="V",
                normalization=None,
            )
        )
    with pytest.raises(StabilityError, match="normalization"):
        validate_stability_series(
            _series(
                [1] * 5,
                kind="current_density",
                unit="mA/cm^2",
                normalization=None,
            )
        )
    with pytest.raises(StabilityError, match="activity stability"):
        validate_stability_series(
            _series(
                [1] * 5,
                kind="activity",
                unit="A/g",
                normalization="bet",
            )
        )
    with pytest.raises(StabilityError, match="fraction"):
        validate_stability_series(
            _series(
                [1] * 5,
                kind="faradaic_efficiency",
                unit="mA",
                normalization=None,
            )
        )


def test_total_current_rejects_normalization_metadata():
    with pytest.raises(StabilityError, match="must not declare normalization"):
        validate_stability_series(
            _series([1] * 5, kind="current", unit="mA", normalization="geometric")
        )


def test_stable_key_and_provenance_digest_are_required_and_deterministic():
    source = _series([1, 2, 3, 4, 5])
    result = analyze_stability(source, _config())
    assert result.source.key == "cat"
    assert result.source.sha256 == series_data_sha256(source)
    assert result.provenance.fit_window is not None
    assert result.provenance.fit_window.unit == "s"
    assert result.provenance.fit_window.n_points == 5

    no_key = _series([1, 2, 3, 4, 5], key="")
    with pytest.raises(StabilityError, match="stable Series.key"):
        validate_stability_series(no_key)


def test_dataset_uses_exact_stable_key_config_mapping_and_allows_duplicate_labels():
    a = _series([1, 2, 3, 4, 5], key="a", label="same")
    b = _series([2, 3, 4, 5, 6], key="b", label="same")
    dataset = Dataset([a, b])
    results = analyze_stability_dataset(dataset, {"b": _config(), "a": _config()})
    assert results.keys == ("a", "b")
    assert results["a"].source.label == "same"
    assert results["b"].source.label == "same"
    with pytest.raises(StabilityError, match="exactly match"):
        analyze_stability_dataset(dataset, {"a": _config()})
    with pytest.raises(StabilityError, match="unknown"):
        analyze_stability_dataset(
            dataset,
            {"a": _config(), "b": _config(), "c": _config()},
        )


def test_numerical_echem_import_remains_matplotlib_lazy_with_stability_api():
    code = (
        "import sys; "
        "import catalysis_workbench.experimental.echem as e; "
        "assert hasattr(e, 'analyze_stability'); "
        "assert hasattr(e, 'StabilityAnalysisConfig'); "
        "assert 'matplotlib' not in sys.modules"
    )
    subprocess.run([sys.executable, "-c", code], check=True)
