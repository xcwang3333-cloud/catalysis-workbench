"""Explicit, immutable scientific QA checks for workflow evidence."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any

import numpy as np

from catalysis_workbench._canonical_json import (
    CanonicalJSONError,
    canonical_json_bytes,
    canonical_json_sha256,
    loads_strict_json,
)
from catalysis_workbench.core import Dataset, Series


class QAStatus(StrEnum):
    """Outcome of one explicit scientific QA check."""

    PASS = "pass"
    FAIL = "fail"


@dataclass(frozen=True, slots=True)
class QAFinding:
    """Immutable deterministic evidence from one explicit QA check."""

    check_id: str
    status: QAStatus
    code: str
    evidence: Mapping[str, Any] = field(default_factory=dict)
    finding_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        check_id = _stable_string(self.check_id, label="check_id")
        code = _stable_string(self.code, label="code")
        if not isinstance(self.status, QAStatus):
            raise TypeError("status must be a QAStatus")
        evidence = _freeze_json_object(self.evidence, label="evidence")
        digest = canonical_json_sha256(
            {
                "qa_finding_schema_version": 1,
                "check_id": check_id,
                "status": self.status.value,
                "code": code,
                "evidence": _plain_json_value(evidence),
            }
        )
        object.__setattr__(self, "check_id", check_id)
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(self, "finding_sha256", digest)


@dataclass(frozen=True, slots=True)
class QAReport:
    """Ordered immutable collection of explicitly requested QA findings."""

    findings: Sequence[QAFinding]
    status: QAStatus = field(init=False)
    report_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        if isinstance(self.findings, (str, bytes)) or not isinstance(
            self.findings, Sequence
        ):
            raise TypeError("findings must be an ordered sequence of QAFinding values")
        findings = tuple(self.findings)
        if not findings:
            raise ValueError("QAReport requires at least one finding")
        if any(not isinstance(item, QAFinding) for item in findings):
            raise TypeError("findings must contain only QAFinding values")
        status = (
            QAStatus.FAIL
            if any(item.status is QAStatus.FAIL for item in findings)
            else QAStatus.PASS
        )
        digest = canonical_json_sha256(
            {
                "qa_report_schema_version": 1,
                "findings": [
                    {"finding_sha256": item.finding_sha256} for item in findings
                ],
                "status": status.value,
            }
        )
        object.__setattr__(self, "findings", findings)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "report_sha256", digest)


def check_digest(
    observed_digest: str,
    expected_digest: str,
    *,
    subject: str = "digest",
) -> QAFinding:
    """Check one explicit lowercase SHA-256 identity against an expected identity."""

    observed = _sha256(observed_digest, label="observed_digest")
    expected = _sha256(expected_digest, label="expected_digest")
    checked_subject = _stable_string(subject, label="subject")
    matches = observed == expected
    return QAFinding(
        check_id="digest",
        status=QAStatus.PASS if matches else QAStatus.FAIL,
        code="match" if matches else "mismatch",
        evidence={
            "subject": checked_subject,
            "observed_digest": observed,
            "expected_digest": expected,
        },
    )


def check_finite_values(
    value: Series | Dataset,
    *,
    components: Sequence[str] = ("x", "y"),
    subject: str = "data",
) -> QAFinding:
    """Check finiteness only for the explicitly selected numerical components."""

    series_values = _series_values(value)
    checked_components = _components(components)
    checked_subject = _stable_string(subject, label="subject")
    violations: list[dict[str, object]] = []
    for series_index, series in enumerate(series_values):
        for component in checked_components:
            array = series.x if component == "x" else series.y
            count = int(np.count_nonzero(~np.isfinite(array)))
            if count:
                violations.append(
                    {
                        "series_index": series_index,
                        "series_key": series.key,
                        "component": component,
                        "nonfinite_count": count,
                    }
                )
    return QAFinding(
        check_id="finite_values",
        status=QAStatus.FAIL if violations else QAStatus.PASS,
        code="nonfinite" if violations else "finite",
        evidence={
            "subject": checked_subject,
            "components": list(checked_components),
            "series_count": len(series_values),
            "violations": violations,
        },
    )


def check_units(
    value: Series | Dataset,
    *,
    expected: Mapping[str, str | None],
    subject: str = "data",
) -> QAFinding:
    """Compare explicitly requested axis units without conversion or normalization."""

    series_values = _series_values(value)
    expectations = _unit_expectations(expected)
    checked_subject = _stable_string(subject, label="subject")
    violations: list[dict[str, object]] = []
    for series_index, series in enumerate(series_values):
        for component in ("x", "y"):
            if component not in expectations:
                continue
            expected_unit = expectations[component]
            observed_unit = (
                series.x_axis.unit if component == "x" else series.y_axis.unit
            )
            if observed_unit != expected_unit:
                violations.append(
                    {
                        "series_index": series_index,
                        "series_key": series.key,
                        "component": component,
                        "expected_unit": expected_unit,
                        "observed_unit": observed_unit,
                    }
                )
    return QAFinding(
        check_id="units",
        status=QAStatus.FAIL if violations else QAStatus.PASS,
        code="mismatch" if violations else "match",
        evidence={
            "subject": checked_subject,
            "expected": dict(expectations),
            "series_count": len(series_values),
            "violations": violations,
        },
    )


def check_stable_keys(
    value: Series | Dataset,
    *,
    require_nonempty: bool = True,
    subject: str = "data",
) -> QAFinding:
    """Check stable-key evidence only when explicitly requested by the caller."""

    if type(require_nonempty) is not bool:
        raise TypeError("require_nonempty must be a bool")
    series_values = _series_values(value)
    checked_subject = _stable_string(subject, label="subject")
    empty_indices = [
        index
        for index, series in enumerate(series_values)
        if require_nonempty and not series.key
    ]

    positions: dict[str, list[int]] = {}
    for index, series in enumerate(series_values):
        if series.key:
            positions.setdefault(series.key, []).append(index)
    duplicates = [
        {"key": key, "series_indices": indices}
        for key, indices in positions.items()
        if len(indices) > 1
    ]
    failed = bool(empty_indices or duplicates)
    return QAFinding(
        check_id="stable_keys",
        status=QAStatus.FAIL if failed else QAStatus.PASS,
        code="unstable" if failed else "stable",
        evidence={
            "subject": checked_subject,
            "require_nonempty": require_nonempty,
            "series_count": len(series_values),
            "empty_key_indices": empty_indices,
            "duplicate_keys": duplicates,
        },
    )


def run_qa(findings: Iterable[QAFinding]) -> QAReport:
    """Aggregate explicitly executed QA findings without discovering or calling checks."""

    try:
        collected = tuple(findings)
    except TypeError as exc:
        raise TypeError("findings must be an iterable of QAFinding values") from exc
    return QAReport(collected)


def _series_values(value: Series | Dataset) -> tuple[Series, ...]:
    if isinstance(value, Series):
        return (value,)
    if isinstance(value, Dataset):
        return tuple(value.series)
    raise TypeError("value must be a Series or Dataset")


def _components(value: Sequence[str]) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError("components must be an ordered sequence")
    checked = tuple(_stable_string(item, label="component") for item in value)
    if not checked:
        raise ValueError("components must contain at least one component")
    if len(checked) != len(set(checked)):
        raise ValueError("components must be unique")
    unknown = [item for item in checked if item not in {"x", "y"}]
    if unknown:
        raise ValueError(f"unsupported components: {unknown!r}")
    return checked


def _unit_expectations(
    value: Mapping[str, str | None],
) -> Mapping[str, str | None]:
    if not isinstance(value, Mapping):
        raise TypeError("expected must be a mapping")
    if not value:
        raise ValueError("expected must contain at least one axis unit expectation")
    detached: dict[str, str | None] = {}
    for key, unit in value.items():
        component = _stable_string(key, label="expected unit component")
        if component not in {"x", "y"}:
            raise ValueError(f"unsupported unit component: {component!r}")
        if unit is not None:
            unit = _stable_string(unit, label=f"expected[{component!r}]")
        detached[component] = unit
    return MappingProxyType(detached)


def _stable_string(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value.strip() != value:
        raise ValueError(
            f"{label} must be a non-empty string without surrounding whitespace"
        )
    try:
        canonical_json_bytes(value)
    except CanonicalJSONError as exc:
        raise ValueError(f"{label} must be valid UTF-8") from exc
    return value


def _sha256(value: object, *, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or value.lower() != value
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 hex digest")
    return value


def _freeze_json_object(value: object, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a strict JSON object")
    try:
        plain = loads_strict_json(canonical_json_bytes(value))
    except CanonicalJSONError as exc:
        raise ValueError(f"{label} must contain only strict JSON values") from exc
    return _freeze_json_value(plain)


def _freeze_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType(
            {key: _freeze_json_value(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return tuple(_freeze_json_value(item) for item in value)
    return value


def _plain_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain_json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain_json_value(item) for item in value]
    return value
