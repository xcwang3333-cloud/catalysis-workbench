from __future__ import annotations

from dataclasses import FrozenInstanceError
from types import MappingProxyType

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.workflow.qa import (
    QAFinding,
    QAReport,
    QAStatus,
    check_digest,
    check_finite_values,
    check_stable_keys,
    check_units,
    run_qa,
)


def _series(
    *,
    key: str = "sample",
    y: np.ndarray | None = None,
    x_unit: str | None = "V",
    y_unit: str | None = "mA cm^-2",
) -> Series:
    return Series(
        x=np.array([0.0, 0.5, 1.0]),
        y=np.array([1.0, 2.0, 3.0]) if y is None else y,
        key=key,
        label=key,
        x_axis=Axis("potential", unit=x_unit),
        y_axis=Axis("current", unit=y_unit),
    )


def test_qa_status_values_are_stable() -> None:
    assert QAStatus.PASS.value == "pass"
    assert QAStatus.FAIL.value == "fail"


def test_finding_is_frozen_deeply_and_digest_is_deterministic() -> None:
    first = QAFinding(
        check_id="example",
        status=QAStatus.PASS,
        code="ok",
        evidence={"nested": [{"value": 1}]},
    )
    second = QAFinding(
        check_id="example",
        status=QAStatus.PASS,
        code="ok",
        evidence={"nested": [{"value": 1}]},
    )

    assert first.finding_sha256 == second.finding_sha256
    assert len(first.finding_sha256) == 64
    assert isinstance(first.evidence, MappingProxyType)
    assert isinstance(first.evidence["nested"], tuple)
    assert isinstance(first.evidence["nested"][0], MappingProxyType)
    with pytest.raises(TypeError):
        first.evidence["other"] = 2  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        first.code = "changed"  # type: ignore[misc]


def test_finding_rejects_noncanonical_evidence() -> None:
    with pytest.raises(ValueError, match="strict JSON"):
        QAFinding(
            check_id="example",
            status=QAStatus.PASS,
            code="ok",
            evidence={"bad": np.int64(1)},
        )


def test_digest_check_passes_and_fails_without_normalizing() -> None:
    expected = "a" * 64
    matching = check_digest(expected, expected, subject="input")
    mismatching = check_digest("b" * 64, expected, subject="input")

    assert matching.status is QAStatus.PASS
    assert matching.code == "match"
    assert mismatching.status is QAStatus.FAIL
    assert mismatching.code == "mismatch"
    assert mismatching.evidence["observed_digest"] == "b" * 64
    assert mismatching.evidence["expected_digest"] == expected
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        check_digest("A" * 64, expected)


def test_finite_values_check_is_explicit_per_component_and_non_mutating() -> None:
    source = _series(y=np.array([1.0, np.nan, 3.0]))
    original_x = np.array(source.x, copy=True)
    original_y = np.array(source.y, copy=True)

    x_only = check_finite_values(source, components=("x",))
    y_only = check_finite_values(source, components=("y",))

    assert x_only.status is QAStatus.PASS
    assert x_only.code == "finite"
    assert y_only.status is QAStatus.FAIL
    assert y_only.code == "nonfinite"
    assert y_only.evidence["violations"] == (
        {
            "series_index": 0,
            "series_key": "sample",
            "component": "y",
            "nonfinite_count": 1,
        },
    )
    assert np.array_equal(source.x, original_x)
    assert np.array_equal(source.y, original_y, equal_nan=True)


def test_finite_values_preserves_dataset_and_component_order() -> None:
    first = _series(key="first", y=np.array([np.nan, 2.0, 3.0]))
    second = _series(key="second", y=np.array([1.0, np.nan, 3.0]))
    finding = check_finite_values(
        Dataset((first, second)),
        components=("y", "x"),
    )

    assert finding.status is QAStatus.FAIL
    assert finding.evidence["components"] == ("y", "x")
    assert tuple(item["series_key"] for item in finding.evidence["violations"]) == (
        "first",
        "second",
    )


@pytest.mark.parametrize(
    "components",
    [(), ("x", "x"), ("z",)],
)
def test_finite_values_rejects_invalid_component_contract(
    components: tuple[str, ...],
) -> None:
    with pytest.raises(ValueError):
        check_finite_values(_series(), components=components)


def test_units_check_only_evaluates_explicit_expectations() -> None:
    source = _series(y_unit=None)

    x_only = check_units(source, expected={"x": "V"})
    missing_is_expected = check_units(source, expected={"y": None})
    missing_is_failure = check_units(source, expected={"y": "A"})

    assert x_only.status is QAStatus.PASS
    assert missing_is_expected.status is QAStatus.PASS
    assert missing_is_failure.status is QAStatus.FAIL
    assert missing_is_failure.evidence["violations"] == (
        {
            "series_index": 0,
            "series_key": "sample",
            "component": "y",
            "expected_unit": "A",
            "observed_unit": None,
        },
    )


def test_units_check_is_mapping_order_invariant() -> None:
    source = _series(x_unit="V", y_unit="mA")
    x_first = check_units(source, expected={"x": "mV", "y": "A"})
    y_first = check_units(source, expected={"y": "A", "x": "mV"})

    assert x_first.finding_sha256 == y_first.finding_sha256
    assert tuple(item["component"] for item in x_first.evidence["violations"]) == (
        "x",
        "y",
    )


def test_units_check_is_exact_and_never_converts_units() -> None:
    source = _series(y_unit="mA")
    finding = check_units(source, expected={"y": "A"})

    assert finding.status is QAStatus.FAIL
    assert finding.evidence["violations"][0]["observed_unit"] == "mA"
    assert finding.evidence["violations"][0]["expected_unit"] == "A"
    with pytest.raises(ValueError, match="surrounding whitespace"):
        check_units(source, expected={"y": " A "})


def test_units_check_rejects_implicit_or_unknown_expectations() -> None:
    with pytest.raises(ValueError, match="at least one"):
        check_units(_series(), expected={})
    with pytest.raises(ValueError, match="unsupported unit component"):
        check_units(_series(), expected={"z": "V"})


def test_stable_keys_check_is_context_sensitive() -> None:
    dataset = Dataset((_series(key="first"), _series(key="")))

    required = check_stable_keys(dataset)
    optional = check_stable_keys(dataset, require_nonempty=False)

    assert required.status is QAStatus.FAIL
    assert required.evidence["empty_key_indices"] == (1,)
    assert optional.status is QAStatus.PASS
    assert optional.evidence["empty_key_indices"] == ()


def test_checks_accept_only_core_series_or_dataset_values() -> None:
    with pytest.raises(TypeError, match="Series or Dataset"):
        check_finite_values(object())
    with pytest.raises(TypeError, match="Series or Dataset"):
        check_units(object(), expected={"x": "V"})
    with pytest.raises(TypeError, match="Series or Dataset"):
        check_stable_keys(object())


def test_run_qa_preserves_explicit_finding_order_and_aggregates_status() -> None:
    passing = check_digest("a" * 64, "a" * 64, subject="first")
    failing = check_digest("b" * 64, "a" * 64, subject="second")

    report = run_qa((passing, failing))
    reversed_report = run_qa((failing, passing))

    assert isinstance(report, QAReport)
    assert report.findings == (passing, failing)
    assert report.status is QAStatus.FAIL
    assert len(report.report_sha256) == 64
    assert report.report_sha256 != reversed_report.report_sha256


def test_run_qa_requires_explicit_findings_and_never_executes_callables() -> None:
    called = False

    def hidden_check() -> QAFinding:
        nonlocal called
        called = True
        return check_digest("a" * 64, "a" * 64)

    with pytest.raises(TypeError, match="QAFinding"):
        run_qa((hidden_check,))
    assert called is False

    with pytest.raises(ValueError, match="at least one"):
        run_qa(())


def test_report_is_frozen_and_rejects_invalid_manual_state() -> None:
    finding = check_digest("a" * 64, "a" * 64)
    report = QAReport((finding,))

    with pytest.raises(FrozenInstanceError):
        report.status = QAStatus.FAIL  # type: ignore[misc]
    with pytest.raises(TypeError, match="QAStatus"):
        QAFinding(
            check_id="example",
            status="pass",  # type: ignore[arg-type]
            code="ok",
        )
