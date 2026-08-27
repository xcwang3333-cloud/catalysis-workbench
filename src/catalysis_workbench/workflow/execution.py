"""Literal, fail-closed execution for reviewed workflow recipes."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from catalysis_workbench import __version__
from catalysis_workbench._canonical_json import (
    CanonicalJSONError,
    canonical_json_bytes,
    canonical_json_sha256,
    loads_strict_json,
)
from catalysis_workbench.core import Series

from .recipe import RecipeStep, WorkflowRecipe
from .registry import OperationDescriptor, get_operation_descriptor


@dataclass(frozen=True, slots=True)
class StepExecutionRecord:
    """Deterministic evidence for one successfully executed recipe step."""

    step_id: str
    operation_id: str
    contract_version: int
    input_identities: Mapping[str, str]
    effective_parameters: Mapping[str, Any]
    output_identities: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "input_identities",
            _freeze_string_mapping(self.input_identities, label="input_identities"),
        )
        object.__setattr__(
            self,
            "effective_parameters",
            _freeze_json_mapping(self.effective_parameters, label="effective_parameters"),
        )
        object.__setattr__(
            self,
            "output_identities",
            _freeze_string_mapping(self.output_identities, label="output_identities"),
        )

    def _identity_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "operation_id": self.operation_id,
            "contract_version": self.contract_version,
            "input_identities": dict(self.input_identities),
            "effective_parameters": _plain_json_value(self.effective_parameters),
            "output_identities": dict(self.output_identities),
        }


@dataclass(frozen=True, slots=True)
class WorkflowRun:
    """Immutable deterministic result of one successful recipe execution."""

    recipe_sha256: str
    content_sha256: str
    record_sha256: str
    outputs: Mapping[str, Series]
    output_identities: Mapping[str, str]
    steps: tuple[StepExecutionRecord, ...]
    environment_evidence: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "outputs", MappingProxyType(dict(self.outputs)))
        object.__setattr__(
            self,
            "output_identities",
            _freeze_string_mapping(self.output_identities, label="output_identities"),
        )
        object.__setattr__(self, "steps", tuple(self.steps))
        object.__setattr__(
            self,
            "environment_evidence",
            _freeze_string_mapping(
                self.environment_evidence,
                label="environment_evidence",
            ),
        )


@dataclass(frozen=True, slots=True)
class _PreparedStep:
    step: RecipeStep
    descriptor: OperationDescriptor
    effective_parameters: Mapping[str, Any]


def execute_recipe(
    recipe: WorkflowRecipe,
    inputs: Mapping[str, object],
    *,
    input_identities: Mapping[str, str],
) -> WorkflowRun:
    """Execute a recipe literally using only reviewed source-controlled adapters."""
    if not isinstance(recipe, WorkflowRecipe):
        raise TypeError("recipe must be a WorkflowRecipe")
    if not isinstance(inputs, Mapping):
        raise TypeError("inputs must be a mapping")
    if not isinstance(input_identities, Mapping):
        raise TypeError("input_identities must be a mapping")

    input_values = _exact_workflow_inputs(recipe, inputs, label="inputs")
    identities = _exact_workflow_inputs(
        recipe,
        input_identities,
        label="input_identities",
    )
    checked_identities = {
        name: _identity_string(identities[name], label=f"input identity {name!r}")
        for name in recipe.inputs
    }

    from . import _adapters

    prepared = _preflight(recipe, input_values, _adapters)
    bindings: dict[str, object] = {name: input_values[name] for name in recipe.inputs}
    binding_identities: dict[str, str] = dict(checked_identities)
    step_records: list[StepExecutionRecord] = []

    for item in prepared:
        step = item.step
        port_inputs = {
            port: bindings[binding_name]
            for port, binding_name in step.inputs.items()
        }
        port_input_identities = {
            port: binding_identities[binding_name]
            for port, binding_name in step.inputs.items()
        }
        outputs = _adapters.execute_operation(
            step.operation_id,
            port_inputs,
            item.effective_parameters,
        )
        if set(outputs) != set(item.descriptor.output_ports):
            raise TypeError(
                f"{step.operation_id!r} adapter returned unexpected output ports"
            )

        output_identities = {
            port: _derive_output_identity(
                operation_id=step.operation_id,
                contract_version=item.descriptor.contract_version,
                input_identities=port_input_identities,
                effective_parameters=item.effective_parameters,
                output_port=port,
            )
            for port in item.descriptor.output_ports
        }
        for port in item.descriptor.output_ports:
            binding_name = step.outputs[port]
            value = outputs[port]
            if not isinstance(value, Series):
                raise TypeError(f"{step.operation_id!r} output {port!r} is not a Series")
            bindings[binding_name] = value
            binding_identities[binding_name] = output_identities[port]

        step_records.append(
            StepExecutionRecord(
                step_id=step.step_id,
                operation_id=step.operation_id,
                contract_version=item.descriptor.contract_version,
                input_identities=port_input_identities,
                effective_parameters=item.effective_parameters,
                output_identities=output_identities,
            )
        )

    final_outputs = {
        output_name: bindings[binding_name]
        for output_name, binding_name in recipe.outputs.items()
    }
    if not all(isinstance(value, Series) for value in final_outputs.values()):
        raise TypeError("workflow outputs must be Series values in the Block 2 execution slice")
    final_identities = {
        output_name: binding_identities[binding_name]
        for output_name, binding_name in recipe.outputs.items()
    }
    records = tuple(step_records)
    content_sha256 = canonical_json_sha256(
        {
            "identity_schema_version": 1,
            "recipe_sha256": recipe.recipe_sha256,
            "inputs": checked_identities,
            "steps": [record._identity_dict() for record in records],
            "outputs": final_identities,
        }
    )
    environment = {"catalysis_workbench_version": __version__}
    record_sha256 = canonical_json_sha256(
        {
            "record_schema_version": 1,
            "content_sha256": content_sha256,
            "environment": environment,
            "status": "success",
        }
    )
    return WorkflowRun(
        recipe_sha256=recipe.recipe_sha256,
        content_sha256=content_sha256,
        record_sha256=record_sha256,
        outputs=final_outputs,
        output_identities=final_identities,
        steps=records,
        environment_evidence=environment,
    )


def _preflight(
    recipe: WorkflowRecipe,
    input_values: Mapping[str, object],
    adapters: Any,
) -> tuple[_PreparedStep, ...]:
    prepared: list[_PreparedStep] = []
    workflow_inputs = set(recipe.inputs)

    for step in recipe.steps:
        descriptor = get_operation_descriptor(step.operation_id)
        _validate_ports(step, descriptor)
        effective = adapters.validate_parameters(step.operation_id, step.parameters)
        for port, binding_name in step.inputs.items():
            if binding_name in workflow_inputs and not isinstance(input_values[binding_name], Series):
                raise TypeError(
                    f"step {step.step_id!r} input port {port!r} requires a Series"
                )
        prepared.append(
            _PreparedStep(
                step=step,
                descriptor=descriptor,
                effective_parameters=_freeze_json_mapping(
                    effective,
                    label=f"effective parameters for {step.step_id!r}",
                ),
            )
        )
    return tuple(prepared)


def _validate_ports(step: RecipeStep, descriptor: OperationDescriptor) -> None:
    input_ports = set(step.inputs)
    expected_inputs = set(descriptor.input_ports)
    output_ports = set(step.outputs)
    expected_outputs = set(descriptor.output_ports)
    if input_ports != expected_inputs or output_ports != expected_outputs:
        raise ValueError(
            f"step {step.step_id!r} ports do not match operation contract; "
            f"inputs={sorted(input_ports)!r}, expected_inputs={sorted(expected_inputs)!r}, "
            f"outputs={sorted(output_ports)!r}, expected_outputs={sorted(expected_outputs)!r}"
        )


def _exact_workflow_inputs(
    recipe: WorkflowRecipe,
    values: Mapping[str, Any],
    *,
    label: str,
) -> dict[str, Any]:
    keys = set(values)
    expected = set(recipe.inputs)
    missing = sorted(expected - keys)
    unknown = sorted(keys - expected)
    if missing or unknown:
        raise ValueError(
            f"{label} must match recipe inputs exactly; missing={missing!r}, unknown={unknown!r}"
        )
    return {name: values[name] for name in recipe.inputs}


def _identity_string(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value.strip() != value:
        raise ValueError(f"{label} must be a non-empty string without surrounding whitespace")
    try:
        canonical_json_bytes(value)
    except CanonicalJSONError as exc:
        raise ValueError(f"{label} must be valid UTF-8") from exc
    return value


def _derive_output_identity(
    *,
    operation_id: str,
    contract_version: int,
    input_identities: Mapping[str, str],
    effective_parameters: Mapping[str, Any],
    output_port: str,
) -> str:
    return canonical_json_sha256(
        {
            "identity_schema_version": 1,
            "operation_id": operation_id,
            "contract_version": contract_version,
            "inputs": dict(input_identities),
            "parameters": _plain_json_value(effective_parameters),
            "output_port": output_port,
        }
    )


def _freeze_string_mapping(
    value: Mapping[str, str],
    *,
    label: str,
) -> Mapping[str, str]:
    detached: dict[str, str] = {}
    for key, item in value.items():
        checked_key = _identity_string(key, label=f"{label} key")
        detached[checked_key] = _identity_string(
            item,
            label=f"{label}[{checked_key!r}]",
        )
    return MappingProxyType(detached)


def _freeze_json_mapping(
    value: Mapping[str, Any],
    *,
    label: str,
) -> Mapping[str, Any]:
    try:
        plain = loads_strict_json(canonical_json_bytes(dict(value)))
    except CanonicalJSONError as exc:
        raise ValueError(f"{label} must contain strict JSON values") from exc
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
