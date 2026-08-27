"""Immutable, declarative workflow recipes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

from catalysis_workbench._canonical_json import (
    CanonicalJSONError,
    canonical_json_bytes,
    canonical_json_sha256,
    loads_strict_json,
)


class WorkflowRecipeError(ValueError):
    """Raised when a workflow recipe is invalid."""


def _identifier(value: object, *, label: str) -> str:
    if type(value) is not str or not value:
        raise WorkflowRecipeError(f"{label} must be a non-empty string")
    if value != value.strip():
        raise WorkflowRecipeError(f"{label} must not have surrounding whitespace")
    try:
        canonical_json_bytes(value)
    except CanonicalJSONError as exc:
        raise WorkflowRecipeError(f"{label} must be valid UTF-8") from exc
    return value


def _string_mapping(value: object, *, label: str) -> Mapping[str, str]:
    if not isinstance(value, Mapping):
        raise WorkflowRecipeError(f"{label} must be a mapping")
    detached: dict[str, str] = {}
    for key, item in value.items():
        checked_key = _identifier(key, label=f"{label} key")
        checked_item = _identifier(item, label=f"{label}[{checked_key!r}]")
        detached[checked_key] = checked_item
    return MappingProxyType(detached)


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


def _parameters(value: object) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise WorkflowRecipeError("parameters must be a strict JSON object")
    try:
        plain = loads_strict_json(canonical_json_bytes(value))
    except CanonicalJSONError as exc:
        raise WorkflowRecipeError("parameters must contain only strict JSON values") from exc
    return _freeze_json_value(plain)


@dataclass(frozen=True, slots=True)
class RecipeStep:
    """One declarative operation and its explicit bindings."""

    step_id: str
    operation_id: str
    inputs: Mapping[str, str]
    outputs: Mapping[str, str]
    parameters: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "step_id", _identifier(self.step_id, label="step_id"))
        object.__setattr__(
            self,
            "operation_id",
            _identifier(self.operation_id, label="operation_id"),
        )
        object.__setattr__(self, "inputs", _string_mapping(self.inputs, label="inputs"))
        object.__setattr__(self, "outputs", _string_mapping(self.outputs, label="outputs"))
        object.__setattr__(self, "parameters", _parameters(self.parameters))


@dataclass(frozen=True, slots=True)
class WorkflowRecipe:
    """An immutable sequential workflow recipe."""

    schema_version: int
    inputs: Sequence[str]
    steps: Sequence[RecipeStep]
    outputs: Mapping[str, str]
    recipe_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise WorkflowRecipeError("schema_version must be the integer 1")
        if isinstance(self.inputs, (str, bytes)) or not isinstance(
            self.inputs, Sequence
        ):
            raise WorkflowRecipeError("inputs must be an ordered sequence")
        checked_inputs = tuple(
            _identifier(value, label="workflow input") for value in self.inputs
        )
        if len(set(checked_inputs)) != len(checked_inputs):
            raise WorkflowRecipeError("workflow input binding keys must be unique")

        if isinstance(self.steps, (str, bytes)) or not isinstance(self.steps, Sequence):
            raise WorkflowRecipeError("steps must be an ordered sequence")
        checked_steps = tuple(self.steps)
        if not checked_steps:
            raise WorkflowRecipeError("a recipe must contain at least one step")
        if not all(isinstance(step, RecipeStep) for step in checked_steps):
            raise WorkflowRecipeError("every step must be a RecipeStep")

        checked_outputs = _string_mapping(self.outputs, label="recipe outputs")
        if not checked_outputs:
            raise WorkflowRecipeError("a recipe must declare at least one output")

        step_ids: set[str] = set()
        available = set(checked_inputs)
        for step in checked_steps:
            if step.step_id in step_ids:
                raise WorkflowRecipeError(f"duplicate step_id: {step.step_id!r}")
            step_ids.add(step.step_id)
            missing = sorted(set(step.inputs.values()) - available)
            if missing:
                raise WorkflowRecipeError(
                    f"step {step.step_id!r} references unavailable bindings: {missing!r}"
                )
            produced = tuple(step.outputs.values())
            if len(set(produced)) != len(produced):
                raise WorkflowRecipeError(
                    f"step {step.step_id!r} assigns one binding more than once"
                )
            collisions = sorted(set(produced) & available)
            if collisions:
                raise WorkflowRecipeError(
                    f"step {step.step_id!r} overwrites existing bindings: {collisions!r}"
                )
            available.update(produced)

        missing_outputs = sorted(set(checked_outputs.values()) - available)
        if missing_outputs:
            raise WorkflowRecipeError(
                f"recipe outputs reference unavailable bindings: {missing_outputs!r}"
            )

        object.__setattr__(self, "inputs", checked_inputs)
        object.__setattr__(self, "steps", checked_steps)
        object.__setattr__(self, "outputs", checked_outputs)
        try:
            recipe_sha256 = canonical_json_sha256(_recipe_to_plain_dict(self))
        except CanonicalJSONError as exc:
            raise WorkflowRecipeError(
                "recipe state must contain only strict canonical JSON values"
            ) from exc
        object.__setattr__(self, "recipe_sha256", recipe_sha256)


_RECIPE_FIELDS = frozenset({"schema_version", "inputs", "steps", "outputs"})
_STEP_FIELDS = frozenset(
    {"step_id", "operation_id", "inputs", "outputs", "parameters"}
)


def _required_fields(
    value: Mapping[object, object], *, required: frozenset[str], label: str
) -> None:
    if not all(type(key) is str for key in value):
        raise WorkflowRecipeError(f"{label} field names must be strings")
    fields = set(value)
    missing = sorted(required - fields)
    unknown = sorted(fields - required)
    if missing or unknown:
        raise WorkflowRecipeError(
            f"invalid {label} fields; missing={missing!r}, unknown={unknown!r}"
        )


def _recipe_to_plain_dict(recipe: WorkflowRecipe) -> dict[str, Any]:
    return {
        "schema_version": recipe.schema_version,
        "inputs": list(recipe.inputs),
        "steps": [
            {
                "step_id": step.step_id,
                "operation_id": step.operation_id,
                "inputs": dict(step.inputs),
                "outputs": dict(step.outputs),
                "parameters": _plain_json_value(step.parameters),
            }
            for step in recipe.steps
        ],
        "outputs": dict(recipe.outputs),
    }


def recipe_to_dict(recipe: WorkflowRecipe) -> dict[str, Any]:
    """Return a detached, plain JSON representation of a recipe."""

    if not isinstance(recipe, WorkflowRecipe):
        raise WorkflowRecipeError("recipe must be a WorkflowRecipe")
    return _recipe_to_plain_dict(recipe)


def recipe_from_dict(value: object) -> WorkflowRecipe:
    """Construct and validate a recipe from its serialized representation."""

    if not isinstance(value, Mapping):
        raise WorkflowRecipeError("serialized recipe must be an object")
    _required_fields(value, required=_RECIPE_FIELDS, label="recipe")
    inputs = value["inputs"]
    steps = value["steps"]
    if not isinstance(inputs, list):
        raise WorkflowRecipeError("serialized recipe inputs must be a list")
    if not isinstance(steps, list):
        raise WorkflowRecipeError("serialized recipe steps must be a list")

    parsed_steps: list[RecipeStep] = []
    for index, step in enumerate(steps):
        if not isinstance(step, Mapping):
            raise WorkflowRecipeError(f"serialized step {index} must be an object")
        _required_fields(step, required=_STEP_FIELDS, label=f"step {index}")
        parsed_steps.append(
            RecipeStep(
                step_id=step["step_id"],
                operation_id=step["operation_id"],
                inputs=step["inputs"],
                outputs=step["outputs"],
                parameters=step["parameters"],
            )
        )
    return WorkflowRecipe(
        schema_version=value["schema_version"],
        inputs=inputs,
        steps=parsed_steps,
        outputs=value["outputs"],
    )


def dump_recipe(
    recipe: WorkflowRecipe, path: str | Path, *, overwrite: bool = False
) -> None:
    """Write canonical UTF-8 JSON with one trailing newline."""

    try:
        payload = canonical_json_bytes(recipe_to_dict(recipe)) + b"\n"
    except CanonicalJSONError as exc:
        raise WorkflowRecipeError("recipe cannot be serialized") from exc
    mode = "wb" if overwrite else "xb"
    with Path(path).open(mode) as stream:
        stream.write(payload)


def load_recipe(path: str | Path) -> WorkflowRecipe:
    """Strictly load and validate a recipe from a UTF-8 JSON file."""

    try:
        text = Path(path).read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise WorkflowRecipeError(f"recipe file is not valid UTF-8: {path!s}") from exc
    try:
        value = loads_strict_json(text)
    except CanonicalJSONError as exc:
        raise WorkflowRecipeError(f"cannot load recipe from {path!s}") from exc
    return recipe_from_dict(value)
