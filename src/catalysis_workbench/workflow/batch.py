"""Deterministic sequential batch workflows over reviewed recipe execution."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from catalysis_workbench import __version__
from catalysis_workbench._canonical_json import CanonicalJSONError, canonical_json_bytes, canonical_json_sha256

from .execution import WorkflowRun, execute_recipe
from .recipe import WorkflowRecipe

_ERROR_POLICIES = {"raise", "record"}
_STATUSES = {"success", "failure"}


@dataclass(frozen=True, slots=True)
class BatchItem:
    """One explicit batch item with stable identity evidence for every input."""

    key: str
    inputs: Mapping[str, object]
    input_identities: Mapping[str, str]

    def __post_init__(self) -> None:
        checked_key = _stable_string(self.key, label="batch item key")
        if not isinstance(self.inputs, Mapping):
            raise TypeError("inputs must be a mapping")
        if not isinstance(self.input_identities, Mapping):
            raise TypeError("input_identities must be a mapping")

        detached_inputs: dict[str, object] = {}
        for name, value in self.inputs.items():
            checked_name = _stable_string(name, label="batch input name")
            detached_inputs[checked_name] = value
        checked_identities = _freeze_string_mapping(
            self.input_identities,
            label="input_identities",
        )
        if set(detached_inputs) != set(checked_identities):
            missing = sorted(set(detached_inputs) - set(checked_identities))
            unknown = sorted(set(checked_identities) - set(detached_inputs))
            raise ValueError(
                "inputs and input_identities must use the same names; "
                f"missing_identities={missing!r}, unknown_identities={unknown!r}"
            )

        object.__setattr__(self, "key", checked_key)
        object.__setattr__(self, "inputs", MappingProxyType(detached_inputs))
        object.__setattr__(self, "input_identities", checked_identities)


@dataclass(frozen=True, slots=True)
class BatchItemRecord:
    """Deterministic result evidence for one batch item."""

    key: str
    status: str
    input_identities: Mapping[str, str]
    workflow_run: WorkflowRun | None
    failure_code: str | None
    record_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "key", _stable_string(self.key, label="batch item key"))
        if self.status not in _STATUSES:
            raise ValueError("status must be 'success' or 'failure'")
        object.__setattr__(
            self,
            "input_identities",
            _freeze_string_mapping(self.input_identities, label="input_identities"),
        )
        _validate_sha256(self.record_sha256, label="record_sha256")

        if self.status == "success":
            if not isinstance(self.workflow_run, WorkflowRun):
                raise TypeError("successful batch item record requires a WorkflowRun")
            if self.failure_code is not None:
                raise ValueError("successful batch item record cannot define failure_code")
        else:
            if self.workflow_run is not None:
                raise ValueError("failed batch item record cannot retain a WorkflowRun")
            if self.failure_code is None:
                raise ValueError("failed batch item record requires failure_code")
            object.__setattr__(
                self,
                "failure_code",
                _stable_string(self.failure_code, label="failure_code"),
            )


@dataclass(frozen=True, slots=True)
class BatchRunRecord:
    """Immutable deterministic evidence for one sequential batch run."""

    recipe_sha256: str
    error_policy: str
    items: tuple[BatchItemRecord, ...]
    record_sha256: str
    environment_evidence: Mapping[str, str]

    def __post_init__(self) -> None:
        _validate_sha256(self.recipe_sha256, label="recipe_sha256")
        _validate_error_policy(self.error_policy)
        records = tuple(self.items)
        if any(not isinstance(item, BatchItemRecord) for item in records):
            raise TypeError("items must contain only BatchItemRecord values")
        keys = tuple(item.key for item in records)
        if len(keys) != len(set(keys)):
            raise ValueError("batch item record keys must be unique")
        _validate_sha256(self.record_sha256, label="record_sha256")
        object.__setattr__(self, "items", records)
        object.__setattr__(
            self,
            "environment_evidence",
            _freeze_string_mapping(
                self.environment_evidence,
                label="environment_evidence",
            ),
        )


def run_batch(
    recipe: WorkflowRecipe,
    items: Iterable[BatchItem],
    *,
    error_policy: str = "raise",
) -> BatchRunRecord:
    """Run one recipe over batch items in literal caller-provided order."""
    if not isinstance(recipe, WorkflowRecipe):
        raise TypeError("recipe must be a WorkflowRecipe")
    _validate_error_policy(error_policy)

    try:
        batch_items = tuple(items)
    except TypeError as exc:
        raise TypeError("items must be an iterable of BatchItem values") from exc

    if any(not isinstance(item, BatchItem) for item in batch_items):
        raise TypeError("items must contain only BatchItem values")
    keys = tuple(item.key for item in batch_items)
    if len(keys) != len(set(keys)):
        raise ValueError("batch item keys must be unique")

    environment = {"catalysis_workbench_version": __version__}
    records: list[BatchItemRecord] = []

    for item in batch_items:
        try:
            workflow_run = execute_recipe(
                recipe,
                item.inputs,
                input_identities=item.input_identities,
            )
        except Exception as exc:
            if error_policy == "raise":
                raise
            failure_code = _failure_code(exc)
            record_sha256 = _item_record_sha256(
                recipe_sha256=recipe.recipe_sha256,
                key=item.key,
                input_identities=item.input_identities,
                status="failure",
                workflow_record_sha256=None,
                failure_code=failure_code,
                environment=environment,
            )
            records.append(
                BatchItemRecord(
                    key=item.key,
                    status="failure",
                    input_identities=item.input_identities,
                    workflow_run=None,
                    failure_code=failure_code,
                    record_sha256=record_sha256,
                )
            )
            continue

        record_sha256 = _item_record_sha256(
            recipe_sha256=recipe.recipe_sha256,
            key=item.key,
            input_identities=item.input_identities,
            status="success",
            workflow_record_sha256=workflow_run.record_sha256,
            failure_code=None,
            environment=environment,
        )
        records.append(
            BatchItemRecord(
                key=item.key,
                status="success",
                input_identities=item.input_identities,
                workflow_run=workflow_run,
                failure_code=None,
                record_sha256=record_sha256,
            )
        )

    frozen_records = tuple(records)
    batch_record_sha256 = canonical_json_sha256(
        {
            "batch_record_schema_version": 1,
            "recipe_sha256": recipe.recipe_sha256,
            "error_policy": error_policy,
            "items": [
                {"key": item.key, "record_sha256": item.record_sha256}
                for item in frozen_records
            ],
            "environment": environment,
        }
    )
    return BatchRunRecord(
        recipe_sha256=recipe.recipe_sha256,
        error_policy=error_policy,
        items=frozen_records,
        record_sha256=batch_record_sha256,
        environment_evidence=environment,
    )


def _item_record_sha256(
    *,
    recipe_sha256: str,
    key: str,
    input_identities: Mapping[str, str],
    status: str,
    workflow_record_sha256: str | None,
    failure_code: str | None,
    environment: Mapping[str, str],
) -> str:
    return canonical_json_sha256(
        {
            "batch_item_record_schema_version": 1,
            "recipe_sha256": recipe_sha256,
            "key": key,
            "input_identities": dict(input_identities),
            "status": status,
            "workflow_record_sha256": workflow_record_sha256,
            "failure_code": failure_code,
            "environment": dict(environment),
        }
    )


def _failure_code(exc: Exception) -> str:
    cls = type(exc)
    return _stable_string(
        f"{cls.__module__}.{cls.__qualname__}",
        label="failure_code",
    )


def _validate_error_policy(error_policy: str) -> None:
    if type(error_policy) is not str or error_policy not in _ERROR_POLICIES:
        raise ValueError("error_policy must be 'raise' or 'record'")


def _stable_string(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value.strip() != value:
        raise ValueError(f"{label} must be a non-empty string without surrounding whitespace")
    try:
        canonical_json_bytes(value)
    except CanonicalJSONError as exc:
        raise ValueError(f"{label} must be valid UTF-8") from exc
    return value


def _freeze_string_mapping(
    value: Mapping[str, str],
    *,
    label: str,
) -> Mapping[str, str]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    detached: dict[str, str] = {}
    for key, item in value.items():
        checked_key = _stable_string(key, label=f"{label} key")
        detached[checked_key] = _stable_string(
            item,
            label=f"{label}[{checked_key!r}]",
        )
    return MappingProxyType(detached)


def _validate_sha256(value: object, *, label: str) -> None:
    if (
        type(value) is not str
        or len(value) != 64
        or value.lower() != value
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 hex digest")
